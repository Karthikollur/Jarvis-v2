"""Command eval runner (P1.3).

    uv run python evals/run.py                  # default model from core/config.toml
    uv run python evals/run.py --model qwen3.5:9b
    uv run python evals/run.py --only r t19     # ids starting with r, and t19

Runs every case in commands.yaml through the orchestrator agent with the stub
tools and reports tool selection, argument accuracy, refusals, clarifications
and latency. Needs Ollama running.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # so `uv run python evals/run.py` can import core/ and evals/
    sys.path.insert(0, str(REPO))

Call = tuple[str, dict[str, Any]]


def _norm(value: Any) -> Any:
    """Compare paths and names loosely: case, slash direction, trailing slash."""
    if isinstance(value, str):
        return value.strip().lower().replace("/", "\\").rstrip("\\")
    return value


def score(case: dict[str, Any], calls: list[Call], reply: str) -> dict[str, bool]:
    """Judge one case from the recorded tool calls and the final reply."""
    if case["expect"] == "tool":
        tool_ok = bool(calls) and calls[0][0] == case["tool"]
        args_ok = tool_ok and (
            "args" not in case
            or {k: _norm(v) for k, v in calls[0][1].items()}
            == {k: _norm(v) for k, v in case["args"].items()}
        )
        return {"tool_ok": tool_ok, "args_ok": args_ok, "passed": tool_ok and args_ok}
    # answer / refuse / clarify: the model must not touch any tool.
    passed = not calls
    if case["expect"] == "clarify":
        # ponytail: "contains a question mark" is the whole clarify detector.
        # Refuse vs answer wording is not judged; read the printed replies.
        passed = passed and "?" in reply
    return {"tool_ok": not calls, "args_ok": True, "passed": passed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", default=None)
    parser.add_argument("--only", nargs="*", default=[], help="case id prefixes")
    parser.add_argument("--no-router", action="store_true", help="LLM only, skip the fast path")
    opts = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import yaml

    import core.openjarvis_env  # noqa: F401  (must precede openjarvis imports)
    from core.router import route
    from evals.stub_tools import CALLS, SPECS
    from openjarvis import Jarvis

    cases = yaml.safe_load((REPO / "evals" / "commands.yaml").read_text(encoding="utf-8"))
    if opts.only:
        cases = [c for c in cases if c["id"].startswith(tuple(opts.only))]

    rows = []
    with Jarvis(config_path=str(REPO / "core" / "config.toml"), model=opts.model) as jarvis:
        jarvis.ask("Say ok.", context=False)  # load the model so case 1 is not a cold start
        for case in cases:
            CALLS.clear()
            started = time.perf_counter()
            routed = None if opts.no_router else route(case["say"])
            if routed:
                CALLS.append(routed)
                reply = "[fast path, no LLM]"
            else:
                try:
                    result = jarvis.ask_full(
                        case["say"], agent="orchestrator", tools=list(SPECS), context=False
                    )
                    reply = result["content"] or ""
                except Exception as exc:  # one broken case must not hide the other 39
                    reply = f"[ERROR] {type(exc).__name__}: {exc}"
            seconds = time.perf_counter() - started
            calls = list(CALLS)
            rows.append((case, calls, reply, seconds, score(case, calls, reply)))
            mark = "ok  " if rows[-1][4]["passed"] else "FAIL"
            path = "fast" if routed else "llm "
            print(f"{mark} {case['id']} {path} {seconds:5.1f}s  {case['say'][:60]}")
            if not rows[-1][4]["passed"] or case["expect"] != "tool":
                print(f"       calls={calls}")
                print(f"       reply={reply[:160]!r}")

    def rate(kinds: set[str], key: str) -> str:
        picked = [r for r in rows if r[0]["expect"] in kinds]
        good = sum(r[4][key] for r in picked)
        return f"{good}/{len(picked)}" + (f" ({100 * good / len(picked):.0f}%)" if picked else "")

    seconds = sorted(r[3] for r in rows)
    print()
    print(f"model:               {opts.model or 'default (core/config.toml)'}")
    print(f"fast path used:      {sum(r[2] == '[fast path, no LLM]' for r in rows)}/{len(rows)}")
    print(f"tool selection:      {rate({'tool', 'answer'}, 'tool_ok')}")
    print(f"argument accuracy:   {rate({'tool'}, 'args_ok')}")
    print(f"must-refuse refused: {rate({'refuse'}, 'passed')}")
    print(f"clarifying question: {rate({'clarify'}, 'passed')}")
    print(f"all cases passed:    {rate({'tool', 'answer', 'refuse', 'clarify'}, 'passed')}")
    if seconds:
        print(f"latency median:      {statistics.median(seconds):.1f}s   max: {seconds[-1]:.1f}s")


if __name__ == "__main__":
    main()
