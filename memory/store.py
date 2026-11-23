"""SQLite schema and the role authorizer for the memory database.

Schema creation runs before the authorizer is installed, so no role holds CREATE.
The authorizer is the permission check. A code that is not granted here is denied.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

MAX_PENDING_FACTS = 50

_ROLES = frozenset({"bridge", "ingest", "review"})

# External-content FTS5. No UPDATE triggers: chunks and facts are inserted and
# deleted, never updated, and the authorizer refuses UPDATE on both.
# DDL only. user_version is set after these, as the last statement of the create.
_SCHEMA = (
    "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE pending_facts ("
    "id INTEGER PRIMARY KEY, text TEXT NOT NULL, proposed TEXT NOT NULL)",
    "CREATE TABLE facts ("
    "id INTEGER PRIMARY KEY, text TEXT NOT NULL, embedding BLOB NOT NULL, "
    "approved TEXT NOT NULL, pending_id INTEGER)",
    "CREATE TABLE documents ("
    "id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE, size INTEGER NOT NULL, "
    "mtime_ns INTEGER NOT NULL, ingested TEXT NOT NULL)",
    "CREATE TABLE chunks ("
    "id INTEGER PRIMARY KEY, "
    "document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE, "
    "seq INTEGER NOT NULL, text TEXT NOT NULL, embedding BLOB NOT NULL, "
    "UNIQUE (document_id, seq))",
    "CREATE TABLE task_history ("
    "id INTEGER PRIMARY KEY, task_id TEXT NOT NULL, said TEXT NOT NULL, "
    "answer TEXT NOT NULL, started TEXT NOT NULL)",
    "CREATE VIRTUAL TABLE chunks_fts USING fts5("
    "text, content='chunks', content_rowid='id')",
    "CREATE VIRTUAL TABLE facts_fts USING fts5("
    "text, content='facts', content_rowid='id')",
    "CREATE TRIGGER chunks_ai AFTER INSERT ON chunks BEGIN "
    "INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text); END",
    "CREATE TRIGGER chunks_ad AFTER DELETE ON chunks BEGIN "
    "INSERT INTO chunks_fts(chunks_fts, rowid, text) "
    "VALUES ('delete', old.id, old.text); END",
    "CREATE TRIGGER facts_ai AFTER INSERT ON facts BEGIN "
    "INSERT INTO facts_fts(rowid, text) VALUES (new.id, new.text); END",
    "CREATE TRIGGER facts_ad AFTER DELETE ON facts BEGIN "
    "INSERT INTO facts_fts(facts_fts, rowid, text) "
    "VALUES ('delete', old.id, old.text); END",
)


class Full(Exception):
    """pending_facts is already at MAX_PENDING_FACTS."""


def connect(path: Path, role: str) -> sqlite3.Connection:
    """Open memory.db as one role. Unknown roles and unknown schema versions raise."""
    if role not in _ROLES:
        raise ValueError(f"unknown role: {role}")
    # Routes run in a thread pool. The bridge holds the one lock; this connection
    # only allows that sharing. The CLIs stay single-threaded.
    conn = sqlite3.connect(path, check_same_thread=role != "bridge")
    try:
        # ponytail: SQLite refuses one of two first WAL switches at once (deadlock avoidance,
        # no busy wait); bounded retry, 5 s.
        for attempt in range(100):
            try:
                conn.execute("PRAGMA journal_mode = WAL")
                break
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc) or attempt == 99:
                    raise
                time.sleep(0.05)
        # Per connection. Without it, ON DELETE CASCADE does not run.
        conn.execute("PRAGMA foreign_keys = ON")
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            try:
                conn.execute("BEGIN IMMEDIATE")
                # The other opener may have committed while this one waited.
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    for statement in _SCHEMA:
                        conn.execute(statement)
                    conn.execute("PRAGMA user_version = 1")
                    version = 1
                conn.execute("COMMIT")
            except Exception:
                conn.rollback()
                raise
        if version != 1:
            raise ValueError(f"unknown user_version: {version}")
        conn.set_authorizer(_authorizer(role))
    except Exception:
        conn.close()
        raise
    return conn


def propose(conn: sqlite3.Connection, text: str) -> None:
    """Insert one pending fact. The only write helper the bridge imports."""
    count = conn.execute("SELECT count(*) FROM pending_facts").fetchone()[0]
    if count >= MAX_PENDING_FACTS:
        raise Full("pending_facts is full")
    proposed = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO pending_facts (text, proposed) VALUES (?, ?)",
        (text, proposed),
    )


def _authorizer(role: str):
    def authorizer(
        action: int,
        arg1: str | None,
        arg2: str | None,
        _db_name: str | None,
        _source: str | None,
    ) -> int:
        if action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION):
            return sqlite3.SQLITE_OK
        # FTS5 reads this inside every search. Setting it is not a read.
        if action == sqlite3.SQLITE_PRAGMA and arg1 == "data_version" and not arg2:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_TRANSACTION:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_INSERT and _insert_allowed(role, arg1):
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_DELETE and _delete_allowed(role, arg1):
            return sqlite3.SQLITE_OK
        # meta is the only table any role may update. documents, chunks, and facts
        # are replaced by delete plus insert, so their FTS rows cannot drift.
        if action == sqlite3.SQLITE_UPDATE and role == "ingest" and arg1 == "meta":
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY

    return authorizer


def _insert_allowed(role: str, table: str | None) -> bool:
    if role == "bridge":
        return table == "pending_facts"
    if role == "ingest":
        return table in {"documents", "chunks", "meta"} or _fts(table, "chunks_fts")
    if role == "review":
        return table in {"facts", "pending_facts"} or _fts(table, "facts_fts")
    return False


def _delete_allowed(role: str, table: str | None) -> bool:
    if role == "bridge":
        return False
    if role == "ingest":
        return table in {"documents", "chunks", "meta"} or _fts(table, "chunks_fts")
    if role == "review":
        return table in {"facts", "pending_facts"} or _fts(table, "facts_fts")
    return False


def _fts(table: str | None, name: str) -> bool:
    """The virtual table and the shadow tables FTS5 writes beside it."""
    return isinstance(table, str) and (table == name or table.startswith(name + "_"))
