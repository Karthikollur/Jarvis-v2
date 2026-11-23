"""memory.embed: prefixes, batches, loopback, and config/memory.toml."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import threading
import urllib.request
from pathlib import Path

import numpy as np
import pytest

from memory.embed import DocsRoot, Embedder, load

_PREFIXES = ("search_document: ", "search_query: ")


@pytest.fixture
def fake_ollama():
    """One loopback Ollama. The script dict picks the vectors and the failing batch."""
    script = {"fail": None, "make": None}
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
            seen.append({"path": self.path, "body": body})
            inputs = body["input"]
            status, raw = 200, None
            if script["fail"] is not None and len(seen) == 2:
                status, raw = _failure(script["fail"], inputs)
            if raw is None:
                make = script["make"] or (lambda texts: [[3.0, 4.0, 0.0] for _ in texts])
                raw = json.dumps({"embeddings": make(inputs)}).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, seen, script
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _failure(kind: str, inputs: list) -> tuple[int, bytes]:
    if kind == "500":
        return 500, b'{"error":"down"}'
    if kind == "400":
        # A real embeddings body, so treating HTTP 400 as success would return vectors.
        vectors = [[1.0, 0.0, 0.0] for _ in inputs]
        return 400, json.dumps({"embeddings": vectors}).encode()
    short = [[1.0, 0.0, 0.0] for _ in inputs[:-1]]
    return 200, json.dumps({"embeddings": short}).encode()


def _embedder(base: str) -> Embedder:
    return Embedder(base, "nomic-embed-text", *_PREFIXES)


def _unit() -> np.ndarray:
    raw = np.array([3.0, 4.0, 0.0], dtype=np.float32)
    return raw / np.linalg.norm(raw)


def test_prefixes_and_unit_vectors(fake_ollama) -> None:
    base, seen, _script = fake_ollama
    embedder = _embedder(base)
    documents = embedder.documents(["alpha"])
    query = embedder.query("beta")
    assert [item["path"] for item in seen] == ["/api/embed", "/api/embed"]
    assert seen[0]["body"]["input"] == ["search_document: alpha"]
    assert seen[1]["body"]["input"] == ["search_query: beta"]
    for item in seen:
        body = item["body"]
        assert set(body) == {"model", "input", "options", "truncate"}
        assert body["model"] == "nomic-embed-text"
        assert body["options"] == {"num_gpu": 0}
        assert body["truncate"] is False
    assert documents.dtype == np.float32 and documents.shape == (1, 3)
    assert query.dtype == np.float32 and query.shape == (3,)
    np.testing.assert_allclose(documents[0], _unit(), rtol=1e-6)
    np.testing.assert_allclose(query, _unit(), rtol=1e-6)
    assert np.linalg.norm(documents[0]) == pytest.approx(1.0)
    assert np.linalg.norm(query) == pytest.approx(1.0)


def test_batches_of_32_keep_order(fake_ollama) -> None:
    base, seen, script = fake_ollama

    def make(inputs: list[str]) -> list[list[float]]:
        rows = []
        for text in inputs:
            index = int(text.split(": ", 1)[1])
            row = [0.0] * 70
            row[index] = 3.0
            rows.append(row)
        return rows

    script["make"] = make
    got = _embedder(base).documents([str(i) for i in range(70)])
    assert [len(item["body"]["input"]) for item in seen] == [32, 32, 6]
    assert got.shape == (70, 70)
    for index, row in enumerate(got):
        assert int(row.argmax()) == index


def test_refuses_non_loopback_and_ignores_proxy(fake_ollama, monkeypatch) -> None:
    with pytest.raises(ValueError):
        Embedder("http://192.168.1.5:11434", "nomic-embed-text", *_PREFIXES)
    base, seen, _script = fake_ollama
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    # urlopen builds one process-wide opener on first use. Clear it so a mutant that
    # calls urlopen, or builds an opener from the environment, honours HTTP_PROXY.
    cached = urllib.request._opener
    urllib.request._opener = None
    try:
        _embedder(base).query("ping")
        assert seen[-1]["body"]["input"] == ["search_query: ping"]
    finally:
        urllib.request._opener = cached


@pytest.mark.parametrize("kind", ["500", "count", "400"])
def test_second_batch_failure_returns_nothing(fake_ollama, kind: str) -> None:
    base, seen, script = fake_ollama
    script["fail"] = kind
    match = {"500": "500", "400": "400", "count": "31 vectors for 32"}[kind]
    with pytest.raises(RuntimeError, match=match):
        _embedder(base).documents([str(i) for i in range(70)])
    assert [len(item["body"]["input"]) for item in seen] == [32, 32]


def test_load_rejects_a_bad_config(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load(tmp_path / "missing.toml")
    with pytest.raises(ValueError):
        load(_write(tmp_path / "relative.toml", "Learning"))
    with pytest.raises(ValueError):
        load(_write(tmp_path / "drive.toml", "C:\\"))
    with pytest.raises(ValueError):
        load(_write(tmp_path / "unknown.toml", r"C:\Mainframe\Second_Brain\Learning", extra=True))


def test_load_returns_docs_roots_and_rejects_bad_exclude(tmp_path: Path) -> None:
    """Test 15: DocsRoot plus the exclude shapes a bare string would misread."""
    learning = r"C:\Mainframe\Second_Brain\Learning"
    embedder, roots = load(_raw(
        tmp_path / "good.toml",
        '[[docs_root]]\n'
        'path = "C:\\\\Mainframe\\\\Second_Brain\\\\Learning"\n'
        'exclude = ["secret"]\n',
    ))
    assert embedder.model == "nomic-embed-text"
    assert roots == [DocsRoot(Path(os.path.realpath(learning)), ("secret",))]
    for name, docs in {
        "dotdot.toml": 'exclude = [".."]\n',
        "dot.toml": 'exclude = ["."]\n',
        "emptyname.toml": 'exclude = [""]\n',
        "slash.toml": 'exclude = ["a/b"]\n',
        "backslash.toml": 'exclude = ["a\\\\b"]\n',
        "archive.toml": 'exclude = "Archive"\n',
        "number.toml": "exclude = [1]\n",
    }.items():
        with pytest.raises(ValueError):
            load(_raw(
                tmp_path / name,
                "[[docs_root]]\n"
                'path = "C:\\\\Mainframe\\\\Second_Brain\\\\Learning"\n'
                + docs,
            ))
    with pytest.raises(ValueError):
        load(_raw(tmp_path / "empty.toml", "docs_root = []\n"))


def _raw(path: Path, docs: str) -> Path:
    path.write_text(
        "[embedding]\n"
        'model = "nomic-embed-text"\n'
        'document_prefix = "search_document: "\n'
        'query_prefix = "search_query: "\n'
        "\n"
        + docs,
        encoding="utf-8",
    )
    return path


def _write(path: Path, root: str, *, extra: bool = False) -> Path:
    extra_line = 'extra = "no"\n' if extra else ""
    escaped = root.replace("\\", "\\\\")
    path.write_text(
        "[embedding]\n"
        'model = "nomic-embed-text"\n'
        'document_prefix = "search_document: "\n'
        'query_prefix = "search_query: "\n'
        f"{extra_line}"
        "\n"
        "[[docs_root]]\n"
        f'path = "{escaped}"\n'
        "exclude = []\n",
        encoding="utf-8",
    )
    return path
