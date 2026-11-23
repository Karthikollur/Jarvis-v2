"""memory.store: schema, the three roles, and the pending-fact cap."""

import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import pytest

from memory.store import MAX_PENDING_FACTS, Full, _SCHEMA, connect, propose

BLOB = b"\x00\x00\x80\x3f"
TABLES = (
    "meta",
    "pending_facts",
    "facts",
    "documents",
    "chunks",
    "task_history",
    "chunks_fts",
    "facts_fts",
)

# Each of these would succeed on an open connection if the bridge authorizer allowed it.
BRIDGE_REFUSED = [
    "INSERT INTO facts (text, embedding, approved) VALUES ('x', X'00', 't')",
    "UPDATE pending_facts SET text = 'no'",
    "DELETE FROM pending_facts",
    "DELETE FROM chunks",
    "DROP TABLE meta",
    "ATTACH DATABASE ':memory:' AS extra",
    "PRAGMA writable_schema",
    "PRAGMA data_version = 5",
    "INSERT INTO chunks_fts(chunks_fts) VALUES ('delete-all')",
    "INSERT INTO facts_fts(rowid, text) VALUES (1, 'x')",
    "DELETE FROM chunks_fts_data",
]


def _file(tmp_path: Path) -> Path:
    return tmp_path / "memory.db"


def _user_version(path: Path) -> int:
    # The authorizer refuses every PRAGMA except a read of data_version.
    raw = sqlite3.connect(path)
    try:
        return raw.execute("PRAGMA user_version").fetchone()[0]
    finally:
        raw.close()


def _refused(conn: sqlite3.Connection, sql: str) -> None:
    with pytest.raises(sqlite3.Error):
        conn.execute(sql)
    conn.rollback()


def test_fresh_file_keeps_rows(tmp_path: Path) -> None:
    path = _file(tmp_path)
    first = connect(path, "ingest")
    names = {row[0] for row in first.execute("SELECT name FROM sqlite_master")}
    assert {
        *TABLES,
        "chunks_ai",
        "chunks_ad",
        "facts_ai",
        "facts_ad",
    } <= names
    assert _user_version(path) == 1
    first.execute("INSERT INTO meta (key, value) VALUES ('k', 'v')")
    first.commit()
    first.close()

    second = connect(path, "ingest")
    try:
        assert second.execute("SELECT value FROM meta WHERE key = 'k'").fetchone()[0] == "v"
    finally:
        second.close()


def test_unknown_user_version_refuses(tmp_path: Path) -> None:
    path = _file(tmp_path)
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA user_version = 99")
    raw.close()
    with pytest.raises(ValueError, match="unknown user_version"):
        connect(path, "bridge")


def test_bridge_reads_and_propose(tmp_path: Path) -> None:
    path = _file(tmp_path)
    fresh = connect(path, "bridge")
    try:
        for table in TABLES:
            fresh.execute(f"SELECT * FROM {table}").fetchall()
    finally:
        fresh.close()

    ingest = connect(path, "ingest")
    ingest.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('a.md', 1, 1, 't')"
    )
    ingest.execute(
        "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (1, 0, 'apple apple', ?)",
        (BLOB,),
    )
    ingest.commit()
    ingest.close()

    review = connect(path, "review")
    review.execute(
        "INSERT INTO facts (text, embedding, approved) VALUES ('kestrel kestrel', ?, 't')",
        (BLOB,),
    )
    review.commit()
    review.close()

    bridge = connect(path, "bridge")
    try:
        assert bridge.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'apple' ORDER BY bm25(chunks_fts)"
        ).fetchall() == [(1,)]
        assert bridge.execute(
            "SELECT rowid FROM facts_fts WHERE facts_fts MATCH 'kestrel' ORDER BY bm25(facts_fts)"
        ).fetchall() == [(1,)]

        ingest = connect(path, "ingest")
        ingest.execute(
            "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('b.md', 1, 1, 't')"
        )
        ingest.execute(
            "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (2, 0, 'apple banana', ?)",
            (BLOB,),
        )
        ingest.commit()
        ingest.close()
        review = connect(path, "review")
        review.execute(
            "INSERT INTO facts (text, embedding, approved) VALUES ('kestrel night', ?, 't')",
            (BLOB,),
        )
        review.commit()
        review.close()

        assert bridge.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'apple' ORDER BY bm25(chunks_fts)"
        ).fetchall() == [(1,), (2,)]
        assert bridge.execute(
            "SELECT rowid FROM facts_fts WHERE facts_fts MATCH 'kestrel' ORDER BY bm25(facts_fts)"
        ).fetchall() == [(1,), (2,)]

        propose(bridge, "remember the gate code")
        text, proposed = bridge.execute("SELECT text, proposed FROM pending_facts").fetchone()
        assert text == "remember the gate code"
        assert datetime.fromisoformat(proposed).utcoffset() is not None
    finally:
        bridge.close()


@pytest.mark.parametrize("sql", BRIDGE_REFUSED)
def test_bridge_refuses(tmp_path: Path, sql: str) -> None:
    path = _file(tmp_path)
    ingest = connect(path, "ingest")
    ingest.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('a.md', 1, 1, 't')"
    )
    ingest.execute(
        "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (1, 0, 'apple', ?)",
        (BLOB,),
    )
    ingest.commit()
    ingest.close()
    bridge = connect(path, "bridge")
    try:
        propose(bridge, "pending one")
        _refused(bridge, sql)
    finally:
        bridge.close()


def test_roles_cannot_write_each_others_tables(tmp_path: Path) -> None:
    path = _file(tmp_path)
    ingest = connect(path, "ingest")
    ingest.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('a.md', 1, 1, 't')"
    )
    ingest.execute(
        "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (1, 0, 'apple', ?)",
        (BLOB,),
    )
    ingest.commit()
    for sql in (
        "INSERT INTO facts (text, embedding, approved) VALUES ('x', X'00', 't')",
        "DELETE FROM facts",
        "INSERT INTO pending_facts (text, proposed) VALUES ('x', 't')",
        "DELETE FROM pending_facts",
        "UPDATE chunks SET text = 'changed' WHERE id = 1",
        "UPDATE documents SET size = 2 WHERE id = 1",
    ):
        _refused(ingest, sql)
    assert ingest.execute(
        "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'apple'"
    ).fetchall() == [(1,)]
    ingest.close()

    review = connect(path, "review")
    try:
        review.execute(
            "INSERT INTO facts (text, embedding, approved) VALUES ('alpha fact', ?, 't')",
            (BLOB,),
        )
        review.commit()
        for sql in (
            "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (1, 1, 'x', X'00')",
            "DELETE FROM chunks",
            "UPDATE facts SET text = 'changed' WHERE id = 1",
        ):
            _refused(review, sql)
        assert review.execute(
            "SELECT rowid FROM facts_fts WHERE facts_fts MATCH 'alpha'"
        ).fetchall() == [(1,)]
    finally:
        review.close()


def test_unknown_role(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown role"):
        connect(_file(tmp_path), "other")


def test_propose_cap(tmp_path: Path) -> None:
    conn = connect(_file(tmp_path), "bridge")
    try:
        for i in range(MAX_PENDING_FACTS):
            propose(conn, f"fact {i}")
        with pytest.raises(Full):
            propose(conn, "one more")
        assert conn.execute("SELECT count(*) FROM pending_facts").fetchone()[0] == MAX_PENDING_FACTS
        texts = {row[0] for row in conn.execute("SELECT text FROM pending_facts")}
        assert "one more" not in texts
    finally:
        conn.close()


def test_delete_removes_fts_rows(tmp_path: Path) -> None:
    path = _file(tmp_path)
    ingest = connect(path, "ingest")
    ingest.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('a.md', 3, 4, 't')"
    )
    ingest.execute(
        "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (1, 0, 'zebracake apple', ?)",
        (BLOB,),
    )
    ingest.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES ('b.md', 3, 4, 't')"
    )
    ingest.execute(
        "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (2, 0, 'apple', ?)",
        (BLOB,),
    )
    ingest.commit()
    ingest.close()

    # Second open: foreign_keys is on only because connect sets it again.
    ingest = connect(path, "ingest")
    try:
        ingest.execute("DELETE FROM documents WHERE path = 'a.md'")
        ingest.commit()
        assert ingest.execute("SELECT id FROM chunks").fetchall() == [(2,)]
        assert ingest.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'zebracake'"
        ).fetchall() == []
        assert ingest.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'apple'"
        ).fetchall() == [(2,)]
        assert ingest.execute(
            "INSERT INTO chunks_fts(chunks_fts) VALUES ('integrity-check')"
        ).fetchall() == []
    finally:
        ingest.close()

    review = connect(path, "review")
    try:
        review.execute(
            "INSERT INTO facts (text, embedding, approved) VALUES ('passport alpha', ?, 't')",
            (BLOB,),
        )
        review.commit()
        review.execute("DELETE FROM facts")
        review.commit()
        assert review.execute(
            "SELECT rowid FROM facts_fts WHERE facts_fts MATCH 'passport'"
        ).fetchall() == []
        assert review.execute(
            "INSERT INTO facts_fts(facts_fts) VALUES ('integrity-check')"
        ).fetchall() == []
    finally:
        review.close()


def test_wal_reader_does_not_block(tmp_path: Path) -> None:
    path = _file(tmp_path)
    ingest = connect(path, "ingest")
    ingest.execute("INSERT INTO meta (key, value) VALUES ('k', 'old')")
    ingest.commit()
    bridge = connect(path, "bridge")
    ingest.execute("BEGIN")
    ingest.execute("UPDATE meta SET value = 'new' WHERE key = 'k'")
    box: dict[str, object] = {}

    def read() -> None:
        try:
            box["value"] = bridge.execute("SELECT value FROM meta WHERE key = 'k'").fetchone()[0]
        except Exception as exc:
            box["error"] = exc

    thread = threading.Thread(target=read)
    thread.start()
    thread.join(1)
    try:
        assert not thread.is_alive()
        assert box["value"] == "old"
        assert "error" not in box
    finally:
        ingest.rollback()
        ingest.close()
        bridge.close()


@pytest.mark.parametrize("role", ["bridge", "ingest", "review"])
def test_load_extension_refused(tmp_path: Path, role: str) -> None:
    conn = connect(_file(tmp_path), role)
    try:
        _refused(conn, "SELECT load_extension('x')")
    finally:
        conn.close()


def _schema_names(path: Path) -> set[str]:
    raw = sqlite3.connect(path)
    try:
        return {row[0] for row in raw.execute("SELECT name FROM sqlite_master")}
    finally:
        raw.close()


def test_failed_ddl_rolls_back(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import memory.store as store

    path = _file(tmp_path)
    real = store._SCHEMA
    monkeypatch.setattr(store, "_SCHEMA", real + ("NOT SQL",))
    with pytest.raises(sqlite3.Error):
        connect(path, "bridge")
    raw = sqlite3.connect(path)
    try:
        assert raw.execute("PRAGMA user_version").fetchone()[0] == 0
        assert raw.execute("SELECT name FROM sqlite_master").fetchall() == []
    finally:
        raw.close()
    monkeypatch.setattr(store, "_SCHEMA", real)
    opened = connect(path, "ingest")
    try:
        assert {
            *TABLES,
            "chunks_ai",
            "chunks_ad",
            "facts_ai",
            "facts_ad",
        } <= _schema_names(path)
    finally:
        opened.close()
    assert _user_version(path) == 1


def test_two_openers_on_a_new_file(tmp_path: Path) -> None:
    for n in range(20):
        path = tmp_path / f"{n}.db"
        barrier = threading.Barrier(2)
        errors: list[BaseException] = []

        def open_role(role: str) -> None:
            try:
                barrier.wait()
                conn = connect(path, role)
                conn.close()
            except BaseException as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=open_role, args=("bridge",)),
            threading.Thread(target=open_role, args=("ingest",)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        assert [thread.is_alive() for thread in threads] == [False, False]
        if errors:
            raise errors[0]
        assert {
            *TABLES,
            "chunks_ai",
            "chunks_ad",
            "facts_ai",
            "facts_ad",
        } <= _schema_names(path)


def test_re_read_skips_ddl_after_the_lock_holder_commits(tmp_path: Path) -> None:
    path = _file(tmp_path)
    raw = sqlite3.connect(path, isolation_level=None)
    raw.execute("PRAGMA journal_mode = WAL")
    raw.execute("BEGIN IMMEDIATE")
    assert raw.execute("PRAGMA user_version").fetchone()[0] == 0
    box: dict[str, object] = {}

    def open_bridge() -> None:
        try:
            box["conn"] = connect(path, "bridge")
        except Exception as exc:
            box["error"] = exc

    thread = threading.Thread(target=open_bridge)
    thread.start()
    time.sleep(0.5)
    try:
        for statement in _SCHEMA:
            raw.execute(statement)
        raw.execute("PRAGMA user_version = 1")
        raw.execute("COMMIT")
    finally:
        raw.close()
    thread.join(10)
    try:
        assert not thread.is_alive()
        if "error" in box:
            raise box["error"]
        opened = box["conn"]
        assert isinstance(opened, sqlite3.Connection)
    finally:
        opened = box.get("conn")
        if isinstance(opened, sqlite3.Connection):
            opened.close()
