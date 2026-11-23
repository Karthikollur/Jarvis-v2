"""memory.search: ranking, floor, FTS query. Tests 1-9."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from memory.search import fts_query, rrf, search
from memory.store import connect

QUERY = np.array([1.0, 0.0], dtype=np.float32)
ROOT = Path(r"C:\vault")
INSIDE = ROOT / "notes" / "a.md"
OUTSIDE = Path(r"D:\other\note.md")
ROOTS = [ROOT, ROOT / "notes"]

_SYNTAX = [
    "NOT working",
    "AND OR",
    '"',
    "*",
    "text:foo",
    "NEAR(a b)",
    '"; DROP TABLE chunks; --',
    '""',
    "   ",
]


class FakeEmbedder:
    model = "nomic-embed-text"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def query(self, text: str) -> np.ndarray:
        self.calls.append(text)
        return QUERY


def _blob(cosine: float) -> bytes:
    width = np.sqrt(np.float32(1.0) - np.float32(cosine) ** 2)
    vector = np.array([cosine, width], dtype=np.float32)
    vector /= np.linalg.norm(vector)
    return np.ascontiguousarray(vector, dtype=np.float32).tobytes()


def _score(cosine: float) -> float:
    vector = np.frombuffer(_blob(cosine), dtype=np.float32)
    return round(float(vector @ QUERY), 3)


def _chunks(path: Path, chunks: list[tuple[str, str, float, int]]) -> None:
    if not chunks:
        return
    ingest = connect(path, "ingest")
    try:
        for doc_path, text, cosine, seq in chunks:
            cursor = ingest.execute(
                "INSERT INTO documents (path, size, mtime_ns, ingested) "
                "VALUES (?, 1, 1, 't')",
                (doc_path,),
            )
            document_id = cursor.lastrowid
            ingest.execute(
                "INSERT INTO chunks (document_id, seq, text, embedding) "
                "VALUES (?, ?, ?, ?)",
                (document_id, seq, text, _blob(cosine)),
            )
        ingest.commit()
    finally:
        ingest.close()


def _facts(path: Path, facts: list[tuple[str, float]]) -> None:
    if not facts:
        return
    review = connect(path, "review")
    try:
        for text, cosine in facts:
            review.execute(
                "INSERT INTO facts (text, embedding, approved) VALUES (?, ?, 't')",
                (text, _blob(cosine)),
            )
        review.commit()
    finally:
        review.close()


def _hits(path: Path, query: str, embedder: FakeEmbedder | None = None, **kwargs):
    chosen = FakeEmbedder() if embedder is None else embedder
    bridge = connect(path, "bridge")
    try:
        return search(bridge, chosen, query, ROOTS, **kwargs)
    finally:
        bridge.close()


def test_1_vector_ranking(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    _chunks(
        path,
        [
            (str(OUTSIDE), "outside chunk", 0.6, 0),
            (str(INSIDE), "inside chunk", 0.8, 2),
        ],
    )
    _facts(path, [("alpha fact", 0.95)])
    hits = _hits(path, "question", mode="vector")
    assert [hit["kind"] for hit in hits] == ["fact", "document", "document"]
    assert [hit["source"] for hit in hits] == [
        1,
        str(INSIDE.relative_to(ROOT)),
        OUTSIDE.name,
    ]
    assert [hit["chunk"] for hit in hits] == [None, 2, 0]
    assert [hit["text"] for hit in hits] == [
        "alpha fact",
        "inside chunk",
        "outside chunk",
    ]
    assert [hit["score"] for hit in hits] == [_score(0.95), _score(0.8), _score(0.6)]


def test_2_same_id_is_two_hits(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    _chunks(path, [(str(INSIDE), "chunk one", 0.7, 0)])
    _facts(path, [("fact one", 0.9)])
    hits = _hits(path, "question", mode="vector")
    assert len(hits) == 2
    assert {hit["kind"] for hit in hits} == {"fact", "document"}
    fact = next(hit for hit in hits if hit["kind"] == "fact")
    chunk = next(hit for hit in hits if hit["kind"] == "document")
    assert fact["source"] == 1
    assert fact["chunk"] is None
    assert chunk["chunk"] == 0


def test_3_floor(tmp_path: Path) -> None:
    mixed = tmp_path / "mixed.db"
    _chunks(
        mixed,
        [
            (str(ROOT / "high.md"), "high", 0.9, 0),
            (str(ROOT / "low.md"), "low", 0.2, 0),
        ],
    )
    assert [hit["text"] for hit in _hits(mixed, "question", mode="vector")] == ["high"]

    missing = tmp_path / "missing.db"
    _chunks(
        missing,
        [
            (str(ROOT / "a.md"), "what is my alpha", 0.4, 0),
            (str(ROOT / "b.md"), "what is my beta", 0.2, 0),
        ],
    )
    for mode in ("vector", "hybrid"):
        assert _hits(missing, "what is my", mode=mode) == []


def test_4_empty_database(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    connect(path, "bridge").close()
    embedder = FakeEmbedder()
    assert _hits(path, "anything", embedder) == []
    assert embedder.calls == []


def test_5_cut_at_1000(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    text = "a" * 1500
    _chunks(path, [(str(INSIDE), text, 0.9, 0)])
    hits = _hits(path, "question", mode="vector")
    assert hits[0]["text"] == text[:1000]
    assert len(hits[0]["text"]) == 1000


def test_6_rrf() -> None:
    assert rrf([["a", "b"]]) == {"a": 1 / 61, "b": 1 / 62}
    scores = rrf([["only", "both"], ["other", "both"]])
    assert scores["both"] > scores["only"]


def test_7_exact_term(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    pieces = [("alpha", 0.95), ("beta", 0.9), ("gamma", 0.85), ("delta", 0.8), ("SVIT", 0.7)]
    _chunks(
        path,
        [(str(ROOT / f"{seq}.md"), text, cosine, seq) for seq, (text, cosine) in enumerate(pieces)],
    )
    vector = _hits(path, "SVIT", mode="vector")
    hybrid = _hits(path, "SVIT", mode="hybrid")
    assert [hit["text"] for hit in vector] == ["alpha", "beta", "gamma", "delta"]
    assert len(hybrid) == 4
    assert "SVIT" in [hit["text"] for hit in hybrid]


@pytest.mark.parametrize("text", _SYNTAX)
def test_8_fts_syntax(tmp_path: Path, text: str) -> None:
    if text == "NOT working":
        assert fts_query(text) == '"NOT" OR "working"'
    if text == '"':
        assert fts_query(text) is None
    path = tmp_path / "memory.db"
    _chunks(path, [(str(INSIDE), "ordinary", 0.9, 0)])
    assert isinstance(_hits(path, text), list)


def test_9_model_and_mode(tmp_path: Path) -> None:
    path = tmp_path / "memory.db"
    ingest = connect(path, "ingest")
    try:
        ingest.execute(
            "INSERT INTO meta (key, value) VALUES ('embedding_model', 'other')"
        )
        ingest.commit()
    finally:
        ingest.close()
    with pytest.raises(RuntimeError):
        _hits(path, "question")
    with pytest.raises(ValueError):
        _hits(path, "question", mode="boolean")
