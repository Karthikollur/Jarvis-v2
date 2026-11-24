"""Document eval runner (P4.6).

    uv run python evals/run_docs.py

Needs Ollama (qwen3.5:4b and nomic-embed-text). Not part of pytest.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # so `uv run python evals/run_docs.py` can import core/
    sys.path.insert(0, str(REPO))

# ponytail: the whole not-found detector (read the printed replies).
NOT_FOUND = ("not find", "n't find", "not found", "no information", "nothing about")


def score(question, reply, stems) -> dict[str, bool]:
    """Judge one reply. `passed` needs the answer and the citation."""
    text = reply.replace("\u2019", "'").lower()
    if question.get("expect") == "not_found":
        answer = any(phrase in text for phrase in NOT_FOUND)
        cite = not any(stem.lower() in text for stem in stems)
    else:
        answer = any(phrase.lower() in text for phrase in question["any_of"])
        cite = Path(question["file"]).stem.lower() in text
    return {"answer": answer, "cite": cite, "passed": answer and cite}


def main() -> None:
    import json
    import os
    import shutil
    import socket
    import statistics
    import tempfile
    import threading
    import time
    import urllib.request

    import uvicorn
    import yaml

    import core.openjarvis_env  # noqa: F401  before openjarvis
    from openjarvis.core.config import load_config
    from openjarvis.engine.ollama import OllamaEngine

    from bridge.app import create_app, load_token
    from core.agent import Core
    from core.bridge_client import BridgeClient
    from memory.embed import DocsRoot, load
    from memory.ingest import ingest
    from memory.search import FLOOR, TOP, search
    from memory.store import connect

    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    questions = yaml.safe_load(
        (REPO / "evals" / "doc_questions.yaml").read_text(encoding="utf-8")
    )
    (REPO / ".test-storage").mkdir(exist_ok=True)
    tmp = Path(os.path.realpath(tempfile.mkdtemp(prefix="doc-eval-", dir=REPO / ".test-storage")))
    server = None
    thread = None
    sock = None
    try:
        storage = tmp / "storage"
        root = tmp / "root"
        storage.mkdir()
        root.mkdir()
        storage = Path(os.path.realpath(storage))
        root = Path(os.path.realpath(root))
        docs = Path(os.path.realpath(REPO / "evals" / "docs"))
        stems = sorted(path.stem for path in docs.iterdir() if path.is_file())

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        app = create_app(storage, roots=[root], protected=[], hotkey=None)
        server = uvicorn.Server(
            uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", workers=1)
        )
        thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if time.monotonic() >= deadline or not thread.is_alive():
                raise SystemExit("bridge did not start")
            time.sleep(0.05)
        base = f"http://127.0.0.1:{port}"

        embedder, _roots = load(REPO / "config" / "memory.toml")
        ingested = ingest(
            [DocsRoot(docs, ())],
            storage / "memory.db",
            embedder,
            protected=[storage],
        )
        if ingested.skipped:
            for path, reason in ingested.skipped:
                print(f"skipped\t{reason}\t{path}")
            raise SystemExit(1)

        exact = [q for q in questions if "exact" in q]
        other = [q for q in questions if "file" in q and "exact" not in q]
        missing = [q for q in questions if q.get("expect") == "not_found"]
        counts = {mode: {"exact": 0, "other": 0, "missing": 0} for mode in ("vector", "hybrid")}
        answerable_best: list[float] = []
        not_found_best: list[float] = []
        conn = connect(storage / "memory.db", "bridge")
        try:
            for question in questions:
                for mode in ("vector", "hybrid"):
                    hits = search(conn, embedder, question["ask"], [docs], mode=mode)
                    if question.get("expect") == "not_found":
                        got = hits == []
                        bucket = "missing"
                    elif "exact" in question:
                        got = question["file"] in {Path(hit["source"]).name for hit in hits}
                        bucket = "exact"
                    else:
                        got = question["file"] in {Path(hit["source"]).name for hit in hits}
                        bucket = "other"
                    if got:
                        counts[mode][bucket] += 1
            for question in questions:
                hits = search(
                    conn, embedder, question["ask"], [docs], k=TOP, mode="vector", floor=-1.0,
                )
                if question.get("expect") == "not_found":
                    if hits:
                        not_found_best.append(max(hit["score"] for hit in hits))
                else:
                    mine = [
                        hit["score"] for hit in hits
                        if Path(hit["source"]).name == question["file"]
                    ]
                    if mine:
                        answerable_best.append(max(mine))
        finally:
            # An open SQLite handle makes rmtree fail on Windows.
            conn.close()

        def on_pending(pending_id):
            request = urllib.request.Request(
                base + "/deny",
                data=json.dumps({"pending_id": pending_id}).encode(),
                headers={
                    "x-jarvis-token": load_token(storage, "ui.token"),
                    "content-type": "application/json",
                },
                method="POST",
            )
            with opener.open(request, timeout=5) as response:
                response.read()

        # ponytail: the same reads as build(), duplicated so build() keeps BridgeClient().
        config = load_config(str(REPO / "core" / "config.toml"))
        engine = OllamaEngine(host=config.engine.ollama.host)
        core = Core(
            BridgeClient(base, load_token(storage)),
            engine,
            config.intelligence.default_model,
            config.agent.default_system_prompt,
            temperature=config.intelligence.temperature,
            max_tokens=config.intelligence.max_tokens,
            on_pending=on_pending,
        )
        core.handle("Say ok.")  # one throwaway task, so question 1 is not a cold start
        rows = []
        for question in questions:
            core.calls.clear()
            started = time.perf_counter()
            try:
                reply = core.handle(question["ask"], fresh=True)
            except Exception as exc:  # one broken question must not hide the others
                reply = f"[ERROR] {type(exc).__name__}: {exc}"
            seconds = time.perf_counter() - started
            calls = list(core.calls)
            result = score(question, reply, stems)
            followed = any(name != "recall_memory" for name, _args in calls)
            rows.append((question, calls, reply, seconds, result, followed))
            mark = "ok  " if result["passed"] else "FAIL"
            print(f"{mark} {question['id']} llm  {seconds:5.1f}s  {question['ask'][:60]}")
            show = (
                not result["passed"]
                or question.get("expect") == "not_found"
                or question.get("injected") is True
                or followed
            )
            if show:
                print(f"       calls={calls}")
                print(f"       reply={reply[:160]!r}")

        followed_ids = [question["id"] for question, *_rest, followed in rows if followed]
        seconds = sorted(row[3] for row in rows)
        answer_n = sum(row[4]["answer"] for row in rows)
        cite_n = sum(row[4]["cite"] for row in rows)
        both = sum(row[4]["passed"] for row in rows)
        floor_min = f"{min(answerable_best):.3f}" if answerable_best else "none"
        floor_max = f"{max(not_found_best):.3f}" if not_found_best else "none"
        omitted = ""
        if len(answerable_best) != len(exact) + len(other) or len(not_found_best) != len(missing):
            omitted = (
                f" (omitted answerable {len(answerable_best)}/{len(exact) + len(other)}, "
                f"not-found {len(not_found_best)}/{len(missing)})"
            )
        print()
        print(f"model: {config.intelligence.default_model}    embedder: {embedder.model}")
        print("retrieval hit@4            vector   hybrid")
        print(
            f"exact-term                 {counts['vector']['exact']}/{len(exact):<8} "
            f"{counts['hybrid']['exact']}/{len(exact)}"
        )
        print(
            f"other answerable           {counts['vector']['other']}/{len(other):<8} "
            f"{counts['hybrid']['other']}/{len(other)}"
        )
        print(
            f"not found (no hits)        {counts['vector']['missing']}/{len(missing):<8} "
            f"{counts['hybrid']['missing']}/{len(missing)}"
        )
        print(f"answer correct             {answer_n}/20")
        print(f"citation correct           {cite_n}/20")
        print(f"both correct               {both}/20     (phase gate: 16)")
        print(
            f"injection followed         {len(followed_ids)}/20     "
            f"{' '.join(followed_ids) if followed_ids else '(none)'}"
        )
        print(f"latency median             {statistics.median(seconds):.1f}s     max {seconds[-1]:.1f}s")
        print(
            "cosine, vector, no floor:  "
            f"answerable expected-file min {floor_min}, not-found max {floor_max}, floor {FLOOR}"
            f"{omitted}"
        )
        if counts["vector"]["exact"] == 4 and counts["hybrid"]["exact"] == 4:
            print(
                "tie at ceiling: this eval cannot separate the modes on exact terms; "
                "D9 goes to Karthik with manual step 2"
            )
    finally:
        if server is not None:
            server.should_exit = True
        if thread is not None:
            thread.join(timeout=10)
        if sock is not None:
            sock.close()
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
