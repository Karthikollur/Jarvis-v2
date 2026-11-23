"""Search approved facts and ingested chunks. stdlib and numpy only."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

# ponytail: floor 0.5. Measured 2026-11-23, nomic-embed-text, 4 short notes:
# matches 0.73 to 0.75, unrelated questions at most 0.47. Section G re-measures.
FLOOR = 0.5
TOP = 20
CUT = 1000

_CHUNKS = (
    "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
    "ORDER BY bm25(chunks_fts) LIMIT ?"
)
_FACTS = (
    "SELECT rowid FROM facts_fts WHERE facts_fts MATCH ? "
    "ORDER BY bm25(facts_fts) LIMIT ?"
)


def fts_query(text: str) -> str | None:
    """Quote each word and OR them. FTS syntax in the raw text never reaches MATCH."""
    words = re.findall(r"\w+", text)
    if not words:
        return None
    return " OR ".join(f'"{word}"' for word in words)


def rrf(rankings: list[list], c: int = 60) -> dict:
    """Sum 1 / (c + rank) for each key. Rank starts at 1. A missing ranking adds nothing."""
    scores: dict = {}
    for ranking in rankings:
        for rank, key in enumerate(ranking, start=1):
            scores[key] = scores.get(key, 0.0) + 1 / (c + rank)
    return scores


def search(
    conn,
    embedder,
    query: str,
    roots,
    k: int = 4,
    mode: str = "hybrid",
    floor: float = FLOOR,
) -> list[dict]:
    """Hybrid or vector search. An empty memory returns [] without calling the embedder."""
    if mode not in ("hybrid", "vector"):
        raise ValueError(f"unknown mode: {mode}")
    stored = conn.execute(
        "SELECT value FROM meta WHERE key = ?", ("embedding_model",)
    ).fetchone()
    if stored is not None and stored[0] != embedder.model:
        raise RuntimeError(
            f"embedding model is {stored[0]!r}, not {embedder.model!r}"
        )
    rows = _rows(conn, roots)
    if not rows:
        return []
    query_vector = embedder.query(query)
    matrix = np.vstack([row["vector"] for row in rows])
    cosines = matrix @ query_vector
    cosine_of = {
        row["key"]: float(cosines[index]) for index, row in enumerate(rows)
    }
    order = sorted(
        range(len(rows)), key=lambda index: cosines[index], reverse=True
    )[:TOP]
    rankings: list[list] = [[rows[index]["key"] for index in order]]
    keyword = fts_query(query)
    if mode == "hybrid" and keyword is not None:
        rankings.append(_keyword(conn, _CHUNKS, "chunk", keyword))
        rankings.append(_keyword(conn, _FACTS, "fact", keyword))
    merged = rrf(rankings)
    ordered = sorted(merged, key=lambda key: merged[key], reverse=True)
    kept = [key for key in ordered if cosine_of[key] >= floor][:k]
    by_key = {row["key"]: row for row in rows}
    return [_hit(by_key[key], cosine_of[key]) for key in kept]


def _rows(conn, roots) -> list[dict]:
    rows = []
    for fact_id, text, embedding in conn.execute(
        "SELECT id, text, embedding FROM facts"
    ):
        rows.append(
            {
                "key": ("fact", fact_id),
                "kind": "fact",
                "source": fact_id,
                "chunk": None,
                "text": text,
                "vector": _vector(embedding),
            }
        )
    for chunk_id, seq, text, embedding, path in conn.execute(
        "SELECT chunks.id, chunks.seq, chunks.text, chunks.embedding, documents.path "
        "FROM chunks JOIN documents ON documents.id = chunks.document_id"
    ):
        rows.append(
            {
                "key": ("chunk", chunk_id),
                "kind": "document",
                "source": _source(path, roots),
                "chunk": seq,
                "text": text,
                "vector": _vector(embedding),
            }
        )
    return rows


def _vector(embedding: bytes) -> np.ndarray:
    return np.frombuffer(embedding, dtype=np.float32).copy()


def _source(path: str, roots) -> str:
    """Path relative to the first configured root that contains it, else the file name."""
    document = Path(path)
    for root in roots:
        root_path = Path(root)
        if document.is_relative_to(root_path):
            return str(document.relative_to(root_path))
    return document.name


def _keyword(conn, sql: str, kind: str, keyword: str) -> list[tuple[str, int]]:
    found = conn.execute(sql, (keyword, TOP)).fetchall()
    return [(kind, rowid) for (rowid,) in found]


def _hit(row: dict, cosine: float) -> dict:
    text = row["text"]
    return {
        "kind": row["kind"],
        "source": row["source"],
        "chunk": row["chunk"],
        "text": text[:CUT],
        "score": round(cosine, 3),
    }
