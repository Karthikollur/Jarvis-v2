"""memory.review: approve, list, forget. Tests 1-9."""

from __future__ import annotations

import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from memory.embed import Embedder
from memory.ingest import ModelMismatch
from memory.review import facts, forget, main, review
from memory.store import connect

_VECTOR = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)


class Fake:
    """One unit vector per text. documents returns shape (n, 4), so [0] is that vector."""

    model = "nomic-embed-text"

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def documents(self, texts: list[str]) -> np.ndarray:
        self.calls.append(list(texts))
        return np.stack([_VECTOR for _ in texts])


def _db(tmp: Path) -> Path:
    path = tmp / "memory.db"
    conn = connect(path, "ingest")
    conn.close()
    return path


def _pin(db: Path, model: str = "nomic-embed-text") -> None:
    conn = connect(db, "ingest")
    try:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES ('embedding_model', ?)",
            (model,),
        )
        conn.commit()
    finally:
        conn.close()


def _pending(db: Path, text: str, proposed: str = "2026-11-24T00:00:00+00:00") -> int:
    conn = connect(db, "review")
    try:
        cursor = conn.execute(
            "INSERT INTO pending_facts (text, proposed) VALUES (?, ?)",
            (text, proposed),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid
    finally:
        conn.close()


def _insert_fact(db: Path, text: str, approved: str = "2026-11-24T00:00:00+00:00") -> int:
    conn = connect(db, "review")
    try:
        cursor = conn.execute(
            "INSERT INTO facts (text, embedding, approved) VALUES (?, ?, ?)",
            (text, np.ascontiguousarray(_VECTOR).tobytes(), approved),
        )
        conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid
    finally:
        conn.close()


def _pending_rows(db: Path) -> list[tuple]:
    conn = connect(db, "review")
    try:
        return conn.execute(
            "SELECT id, text FROM pending_facts ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def _fact_rows(db: Path) -> list[tuple]:
    conn = connect(db, "review")
    try:
        return conn.execute(
            "SELECT text, embedding, approved, pending_id FROM facts ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


def _answers(monkeypatch: pytest.MonkeyPatch, replies: list[str]) -> list[str]:
    prompts: list[str] = []
    pending = iter(replies)

    def answer(prompt: str) -> str:
        prompts.append(prompt)
        return next(pending)

    monkeypatch.setattr("builtins.input", answer)
    return prompts


def test_approve_stores_the_vector_and_drops_the_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 1."""
    db = _db(tmp_path)
    _pin(db)
    pending_id = _pending(db, "kestrel")
    fake = Fake()
    _answers(monkeypatch, ["a"])
    review(db, fake)
    rows = _fact_rows(db)
    assert _pending_rows(db) == []
    assert len(rows) == 1
    text, blob, approved, stored_pending = rows[0]
    assert text == "kestrel"
    assert stored_pending == pending_id
    vector = np.frombuffer(blob, dtype=np.float32)
    assert np.array_equal(vector, _VECTOR)
    assert float(np.linalg.norm(vector)) == 1.0
    parsed = datetime.fromisoformat(approved)
    assert parsed.tzinfo == timezone.utc
    assert fake.calls == [["kestrel"]]
    conn = connect(db, "review")
    try:
        found = conn.execute(
            "SELECT text FROM facts_fts WHERE facts_fts MATCH 'kestrel'"
        ).fetchall()
    finally:
        conn.close()
    assert found == [("kestrel",)]


def test_edit_approves_typed_text_and_empty_edit_stays_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 2."""
    db = _db(tmp_path)
    _pin(db)
    keep = _pending(db, "keep")
    _pending(db, "old")
    fake = Fake()
    prompts = _answers(monkeypatch, ["e", "", "e", "typed fact"])
    review(db, fake)
    assert prompts == [
        "a)pprove e)dit d)elete s)kip: ",
        "text: ",
        "a)pprove e)dit d)elete s)kip: ",
        "text: ",
    ]
    assert _pending_rows(db) == [(keep, "keep")]
    assert [row[0] for row in _fact_rows(db)] == ["typed fact"]
    assert fake.calls == [["typed fact"]]


def test_delete_removes_the_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 3."""
    db = _db(tmp_path)
    _pin(db)
    _pending(db, "gone")
    fake = Fake()
    _answers(monkeypatch, ["d"])
    review(db, fake)
    assert _pending_rows(db) == []
    assert _fact_rows(db) == []
    assert fake.calls == []


def test_skip_and_unknown_leave_the_row_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 4."""
    db = _db(tmp_path)
    _pin(db)
    first = _pending(db, "one")
    second = _pending(db, "two")
    fake = Fake()
    _answers(monkeypatch, ["s", "x"])
    review(db, fake)
    assert _pending_rows(db) == [(first, "one"), (second, "two")]
    assert _fact_rows(db) == []
    assert fake.calls == []


def test_dead_embedder_leaves_the_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 5."""
    db = _db(tmp_path)
    _pin(db)
    pending_id = _pending(db, "hello")
    embedder = Embedder(
        "http://127.0.0.1:9", "nomic-embed-text", "search_document: ", "search_query: ",
    )
    _answers(monkeypatch, ["a"])
    with pytest.raises(urllib.error.URLError):
        review(db, embedder)
    assert _pending_rows(db) == [(pending_id, "hello")]
    assert _fact_rows(db) == []


def test_model_mismatch_leaves_the_pending_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 6. Missing key, then a different model. Neither message offers reset-documents."""
    db = _db(tmp_path)
    pending_id = _pending(db, "kestrel")
    fake = Fake()
    _answers(monkeypatch, ["a"])
    with pytest.raises(ModelMismatch) as missing:
        review(db, fake)
    assert str(missing.value) == "no embedding model yet. Run python -m memory ingest first"
    assert _pending_rows(db) == [(pending_id, "kestrel")]
    assert _fact_rows(db) == []

    _pin(db, "other")
    _answers(monkeypatch, ["a"])
    with pytest.raises(ModelMismatch) as mismatch:
        review(db, fake)
    assert str(mismatch.value) == "embedding model is 'other', not 'nomic-embed-text'"
    assert "reset-documents" not in str(mismatch.value)
    assert _pending_rows(db) == [(pending_id, "kestrel")]
    assert _fact_rows(db) == []
    assert fake.calls == [["kestrel"], ["kestrel"]]


def test_pending_line_escapes_control_characters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 7."""
    db = _db(tmp_path)
    text = "\x1b[2J\u202e"
    _pending(db, text)
    _answers(monkeypatch, ["s"])
    review(db, Fake())
    out = capsys.readouterr().out
    assert repr(text) in out
    assert "\x1b" not in out
    assert "\u202e" not in out


def test_facts_escape_and_forget_needs_exact_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 8."""
    db = _db(tmp_path)
    text = "\x1b[2J"
    fact_id = _insert_fact(db, text)
    facts(db)
    out = capsys.readouterr().out
    assert repr(text) in out
    assert "\x1b" not in out

    def boom(_prompt: str) -> str:
        raise AssertionError("input on an unknown fact")

    monkeypatch.setattr("builtins.input", boom)
    before = _fact_rows(db)
    forget(db, fact_id + 1)
    assert capsys.readouterr().out == f"no fact {fact_id + 1}\n"
    assert _fact_rows(db) == before

    prompts = _answers(monkeypatch, ["y"])
    forget(db, fact_id)
    assert prompts == ["Type yes to delete this fact: "]
    assert [row[0] for row in _fact_rows(db)] == [text]

    prompts = _answers(monkeypatch, ["yes"])
    forget(db, fact_id)
    assert prompts == ["Type yes to delete this fact: "]
    assert _fact_rows(db) == []


def test_main_missing_db_and_bad_argv(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 9."""
    missing = tmp_path / "absent.db"
    absent_config = tmp_path / "absent.toml"
    main(["review"], db=missing, config=absent_config)
    assert capsys.readouterr().out == "no pending facts\n"
    assert not missing.exists()
    main(["facts"], db=missing, config=absent_config)
    assert capsys.readouterr().out == "no facts\n"
    assert not missing.exists()
    main(["forget", "4"], db=missing, config=absent_config)
    assert capsys.readouterr().out == "no fact 4\n"
    assert not missing.exists()
    for argv in (
        [],
        ["nope"],
        ["forget"],
        ["forget", "x"],
        ["forget", "01"],
        ["forget", "1", "2"],
        ["review", "extra"],
        ["facts", "1"],
    ):
        with pytest.raises(SystemExit) as exc:
            main(argv, db=missing, config=absent_config)
        assert exc.value.code == "usage: python -m memory review | facts | forget <id>"
    assert not missing.exists()
