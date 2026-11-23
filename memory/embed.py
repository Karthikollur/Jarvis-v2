"""Ollama embedding client. The only socket in memory/."""

from __future__ import annotations

import json
import os
import re
import tomllib
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

# Same address as `host` in core/config.toml. memory/ does not import core.
OLLAMA = "http://127.0.0.1:11434"

_BATCH = 32
_TIMEOUT = 60
_TOP_KEYS = frozenset({"embedding", "docs_root"})
_EMBED_KEYS = frozenset({"model", "document_prefix", "query_prefix"})
_ROOT_KEYS = frozenset({"path", "exclude"})
# Absolute folder below a drive. `C:\` fails: a drive root is not a folder below it.
_FOLDER = re.compile(r"[A-Za-z]:\\[^\\].*")


class Embedder:
    def __init__(self, base: str, model: str, document_prefix: str, query_prefix: str):
        if not base.startswith("http://127.0.0.1:"):
            raise ValueError("ollama must be loopback")  # rule 22
        self._base = base.rstrip("/")
        self._model = model
        self._document_prefix = document_prefix
        self._query_prefix = query_prefix
        # No proxies: urlopen would honour HTTP_PROXY and could send a loopback call off the box.
        # Per instance, so this opener is built when the client is, under the proxy env then.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def documents(self, texts: list[str]) -> np.ndarray:
        return self._embed(self._document_prefix, texts)

    def query(self, text: str) -> np.ndarray:
        return self._embed(self._query_prefix, [text])[0]

    def _embed(self, prefix: str, texts: list[str]) -> np.ndarray:
        rows: list[list[float]] = []
        for start in range(0, len(texts), _BATCH):
            batch = [prefix + text for text in texts[start : start + _BATCH]]
            rows.extend(self._post(batch))
        matrix = np.asarray(rows, dtype=np.float32)
        return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)

    def _post(self, inputs: list[str]) -> list:
        # ponytail: CPU keeps the chat model's VRAM; about 0.17 s per 1000-character chunk. GPU
        # only after a new measurement.
        body = {
            "model": self._model,
            "input": inputs,
            "options": {"num_gpu": 0},
            "truncate": False,
        }
        request = urllib.request.Request(
            self._base + "/api/embed",
            data=json.dumps(body).encode(),
            headers={"content-type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=_TIMEOUT) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw = error.code, error.read()
        if status != 200:
            detail = raw.decode("utf-8", "replace")
            raise RuntimeError(f"ollama embed failed ({status}): {detail}")
        vectors = json.loads(raw)["embeddings"]
        if len(vectors) != len(inputs):
            raise RuntimeError(
                f"ollama embed returned {len(vectors)} vectors for {len(inputs)} inputs"
            )
        return vectors


def load(config_path: Path) -> tuple[Embedder, list[Path]]:
    """Read config/memory.toml. A missing file raises FileNotFoundError."""
    data = tomllib.loads(Path(config_path).read_text(encoding="utf-8"))
    _exact(data, _TOP_KEYS, "memory.toml")
    embedding = _exact(data["embedding"], _EMBED_KEYS, "embedding")
    roots = []
    entries = data["docs_root"]
    if not isinstance(entries, list):
        raise ValueError("docs_root must be a list of tables")
    for entry in entries:
        table = _exact(entry, _ROOT_KEYS, "docs_root")
        raw = table["path"]
        if not isinstance(raw, str) or _FOLDER.fullmatch(raw) is None:
            raise ValueError(f"docs root must be an absolute folder below a drive: {raw!r}")
        roots.append(Path(os.path.realpath(raw)))
    return (
        Embedder(
            OLLAMA,
            embedding["model"],
            embedding["document_prefix"],
            embedding["query_prefix"],
        ),
        roots,
    )


def _exact(table: object, keys: frozenset[str], label: str) -> dict:
    if not isinstance(table, dict) or set(table) != keys:
        raise ValueError(f"{label} keys must be {sorted(keys)}")
    return table
