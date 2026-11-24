"""Review pending facts, list approved facts, and forget one.

Every connection uses the review role. input() and print() are called directly.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from memory.embed import load
from memory.ingest import ModelMismatch, default_db
from memory.store import connect

_MODEL_KEY = "embedding_model"
_USAGE = "usage: python -m memory review | facts | forget <id>"


def review(db: Path, embedder: Any) -> None:
    """Walk pending facts in id order. Anything other than a, e, or d skips."""
    conn = connect(db, "review")
    try:
        rows = conn.execute(
            "SELECT id, proposed, text FROM pending_facts ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    for fact_id, proposed, text in rows:
        print(f"{fact_id}  {proposed}  {text!r}")
        choice = input("a)pprove e)dit d)elete s)kip: ")
        if choice == "a":
            _approve(db, embedder, fact_id, text)
        elif choice == "e":
            edited = input("text: ")
            if edited == "":
                continue
            _approve(db, embedder, fact_id, edited)
        elif choice == "d":
            _delete_pending(db, fact_id)


def facts(db: Path) -> None:
    conn = connect(db, "review")
    try:
        rows = conn.execute(
            "SELECT id, approved, text FROM facts ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    for fact_id, approved, text in rows:
        print(f"{fact_id}  {approved}  {text!r}")


def forget(db: Path, fact_id: int) -> None:
    """Print an unknown id and leave it. Delete a known fact only on exact yes."""
    conn = connect(db, "review")
    try:
        row = conn.execute(
            "SELECT id, approved, text FROM facts WHERE id = ?",
            (fact_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        print(f"no fact {fact_id}")
        return
    print(f"{row[0]}  {row[1]}  {row[2]!r}")
    if input("Type yes to delete this fact: ") != "yes":
        return
    conn = connect(db, "review")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(
    argv: list[str] | None = None,
    *,
    db: Path | None = None,
    config: Path | None = None,
    embedder: Any = None,
) -> None:
    command, fact_id = _command(list(sys.argv[1:] if argv is None else argv))
    if db is None:
        db = default_db()
    if not db.exists():
        if command == "review":
            print("no pending facts")
        elif command == "facts":
            print("no facts")
        else:
            print(f"no fact {fact_id}")
        return
    if command == "facts":
        facts(db)
    elif command == "forget":
        forget(db, fact_id)
    else:
        if embedder is None:
            if config is None:
                config = Path(__file__).resolve().parent.parent / "config" / "memory.toml"
            embedder, _roots = load(config)
        review(db, embedder)


def _command(args: list[str]) -> tuple[str, int]:
    if not args or args[0] not in {"review", "facts", "forget"}:
        raise SystemExit(_USAGE)
    if args[0] == "forget":
        if len(args) != 2:
            raise SystemExit(_USAGE)
        return "forget", _parse_id(args[1])
    if len(args) != 1:
        raise SystemExit(_USAGE)
    return args[0], 0


def _approve(db: Path, embedder: Any, pending_id: int, text: str) -> None:
    """Embed first. A down Ollama raises before any write.

    The model key is checked inside the write transaction: missing, or not the
    embedder's model, rolls back and raises. The message names ingest, not
    reset-documents: with facts present, reset-documents keeps the key.
    """
    vector = embedder.documents([text])[0]
    blob = np.ascontiguousarray(vector, dtype=np.float32).tobytes()
    approved = datetime.now(timezone.utc).isoformat()
    conn = connect(db, "review")
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_MODEL_KEY,)
        ).fetchone()
        if row is None:
            raise ModelMismatch(
                "no embedding model yet. Run python -m memory ingest first"
            )
        stored = row[0]
        if stored != embedder.model:
            raise ModelMismatch(
                f"embedding model is {stored!r}, not {embedder.model!r}"
            )
        conn.execute(
            "INSERT INTO facts (text, embedding, approved, pending_id) "
            "VALUES (?, ?, ?, ?)",
            (text, blob, approved, pending_id),
        )
        conn.execute("DELETE FROM pending_facts WHERE id = ?", (pending_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _delete_pending(db: Path, fact_id: int) -> None:
    conn = connect(db, "review")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM pending_facts WHERE id = ?", (fact_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _parse_id(token: str) -> int:
    try:
        value = int(token)
    except ValueError:
        raise SystemExit(_USAGE) from None
    if str(value) != token:
        raise SystemExit(_USAGE)
    return value
