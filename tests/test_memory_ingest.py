"""memory.ingest: walk, chunk, incremental replace, dry-run. Tests 1-14 and 16."""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from memory.embed import DocsRoot
from memory.ingest import (
    ModelMismatch,
    Report,
    default_protected,
    ingest,
    main,
    reset_documents,
)
from memory.store import connect

_TEXT = 2 * 1024 * 1024
_PDF = 20 * 1024 * 1024


class Fake:
    """Hash to a unit vector. An empty list raises, as Embedder.documents does."""

    model = "nomic-embed-text"

    def __init__(self, fail_at: int | None = None) -> None:
        self.calls: list[list[str]] = []
        self.fail_at = fail_at
        self.on_documents = None

    def documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            raise np.exceptions.AxisError("axis 1 is out of bounds for array of dimension 1")
        self.calls.append(list(texts))
        if self.on_documents is not None:
            self.on_documents(texts)
        if self.fail_at is not None and len(self.calls) == self.fail_at:
            raise RuntimeError("embed failed")
        rows = []
        for text in texts:
            raw = hashlib.sha256(text.encode()).digest()[:16]
            vec = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
            norm = float(np.linalg.norm(vec))
            rows.append(vec / norm)
        return np.stack(rows)


def _root(tmp: Path) -> Path:
    folder = tmp / "docs"
    folder.mkdir()
    return Path(os.path.realpath(folder))


def _docs(root: Path, exclude: tuple[str, ...] = ()) -> DocsRoot:
    return DocsRoot(Path(os.path.realpath(root)), exclude)


def _run(
    root: Path,
    db: Path,
    embedder: Fake,
    exclude: tuple[str, ...] = (),
    protected: list[Path] | None = None,
) -> Report:
    return ingest(
        [_docs(root, exclude)],
        db,
        embedder,
        protected=[] if protected is None else protected,
    )


def _connect(db: Path):
    conn = connect(db, "ingest")
    return conn


def _rows(db: Path) -> list[tuple]:
    conn = _connect(db)
    try:
        return conn.execute(
            "SELECT documents.path, documents.size, documents.mtime_ns, chunks.seq, chunks.text "
            "FROM documents LEFT JOIN chunks ON chunks.document_id = documents.id "
            "ORDER BY documents.path, chunks.seq"
        ).fetchall()
    finally:
        conn.close()


def _paths(db: Path) -> list[str]:
    conn = _connect(db)
    try:
        return [row[0] for row in conn.execute("SELECT path FROM documents ORDER BY path")]
    finally:
        conn.close()


def _chunks(db: Path, name: str) -> list[str]:
    conn = _connect(db)
    try:
        paths = conn.execute("SELECT path FROM documents").fetchall()
    finally:
        conn.close()
    wanted = [path for (path,) in paths if os.path.basename(path) == name]
    assert len(wanted) == 1, paths
    conn = _connect(db)
    try:
        return [
            text
            for (text,) in conn.execute(
                "SELECT chunks.text FROM chunks JOIN documents "
                "ON documents.id = chunks.document_id WHERE documents.path = ? "
                "ORDER BY chunks.seq",
                (wanted[0],),
            )
        ]
    finally:
        conn.close()


def _match(db: Path, word: str) -> list[str]:
    conn = _connect(db)
    try:
        return [
            text
            for (text,) in conn.execute(
                "SELECT text FROM chunks_fts WHERE chunks_fts MATCH ?", (word,)
            )
        ]
    finally:
        conn.close()


def _reason(report: Report, name: str) -> str:
    hits = [reason for path, reason in report.skipped if os.path.basename(path) == name]
    assert hits == [hits[0]] if hits else False, [(path, reason) for path, reason in report.skipped]
    return hits[0]


def test_rerun_embeds_nothing(tmp_path: Path) -> None:
    """Test 1."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    for name in ("a.md", "b.md", "c.md"):
        (root / name).write_text(f"{name} body\n", encoding="utf-8")
    fake = Fake()
    _run(root, db, fake)
    assert len(fake.calls) == 3
    assert len(_paths(db)) == 3
    _run(root, db, fake)
    assert len(fake.calls) == 3


def test_edits_removals_and_skipped_rows_are_replaced(tmp_path: Path) -> None:
    """Test 2: edit, unlink, NUL, then an exclude added after the first run."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "a.md").write_text("oldword stays\n", encoding="utf-8")
    (root / "b.md").write_text("otherword stays\n", encoding="utf-8")
    secret = root / "secret"
    secret.mkdir()
    (secret / "hidden.md").write_text("hiddenword stays\n", encoding="utf-8")
    fake = Fake()
    _run(root, db, fake)
    assert _match(db, "oldword")
    assert _match(db, "otherword")
    assert _match(db, "hiddenword")

    (root / "a.md").write_text("newword instead\n", encoding="utf-8")
    _run(root, db, fake)
    assert len(fake.calls) == 4
    assert not _match(db, "oldword")
    assert _match(db, "newword")
    assert _match(db, "otherword")
    assert _match(db, "hiddenword")

    (root / "b.md").unlink()
    _run(root, db, fake)
    assert not _match(db, "otherword")
    assert _match(db, "newword")

    (root / "a.md").write_bytes(b"newword\x00nope")
    report = _run(root, db, fake)
    assert _reason(report, "a.md") == "binary"
    assert not _match(db, "newword")
    assert _match(db, "hiddenword")

    report = _run(root, db, fake, exclude=("secret",))
    assert _reason(report, "secret") == "excluded"
    assert not _match(db, "hiddenword")


def test_junctions_and_final_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 3. The symlink half skips where this account cannot create one.

    hello.pdf is swapped for other.pdf the moment the checked read returns.
    """
    import _winapi

    import memory.ingest as ingest_mod

    root, db = _root(tmp_path), tmp_path / "memory.db"
    real = root / "real"
    real.mkdir()
    (real / "n.md").write_text("insidenote\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("outsidesecret\n", encoding="utf-8")
    (root / "sibling.md").write_text("siblingbody\n", encoding="utf-8")
    (root / "trick.md").write_text("trickbody\n", encoding="utf-8")
    (root / "plain.md").write_text("plainbody\n", encoding="utf-8")
    fixture = (Path(__file__).parent / "fixtures" / "hello.pdf").read_bytes()
    (root / "hello.pdf").write_bytes(fixture)
    other = tmp_path / "other.pdf"
    swapped = fixture.replace(b"(Hello PDF)", b"(Other PDF)", 1)
    assert swapped != fixture and len(swapped) == len(fixture)
    other.write_bytes(swapped)
    _winapi.CreateJunction(str(real), str(root / "jin"))
    _winapi.CreateJunction(str(outside), str(root / "outj"))
    alias = root / "alias.md"
    linked = True
    try:
        os.symlink(root / "plain.md", alias)
    except OSError:
        linked = False
    real_final = ingest_mod._final_path

    def patched(fd: int) -> str:
        found = real_final(fd)
        if os.path.basename(found).casefold() == "trick.md":
            return str(root / "not-the-file.md")
        return found

    real_open = ingest_mod._open

    def wrapped_open(path: str, pdf: bool) -> tuple[bytes | None, str | None]:
        result = real_open(path, pdf)
        if os.path.basename(path).casefold() == "hello.pdf":
            os.replace(other, path)
        return result

    monkeypatch.setattr(ingest_mod, "_final_path", patched)
    monkeypatch.setattr(ingest_mod, "_open", wrapped_open)
    try:
        report = _run(root, db, Fake())
    finally:
        for name in ("jin", "outj"):
            link = root / name
            if link.exists():
                os.rmdir(link)
        if linked:
            alias.unlink()
    assert _reason(report, "jin") == "reparse point"
    assert _reason(report, "outj") == "reparse point"
    assert not any(os.sep + "jin" + os.sep in path for path, _reason in report.skipped)
    assert not any(os.sep + "jin" + os.sep in path for path in _paths(db))
    assert not any(os.sep + "outj" + os.sep in path for path in _paths(db))
    assert _match(db, "insidenote")
    assert _match(db, "siblingbody")
    assert not _match(db, "outsidesecret")
    assert not _match(db, "trickbody")
    assert _reason(report, "trick.md") == "resolved path differs"
    if linked:
        assert _reason(report, "alias.md") == "resolved path differs"
        assert not any(path.endswith("alias.md") for path in _paths(db))
    assert "Hello PDF" in _chunks(db, "hello.pdf")[0]
    conn = _connect(db)
    try:
        texts = [text for (text,) in conn.execute("SELECT text FROM chunks")]
    finally:
        conn.close()
    assert all("Other PDF" not in text for text in texts)


def test_hard_link_is_skipped(tmp_path: Path) -> None:
    """Test 4."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("linkedsecret\n", encoding="utf-8")
    os.link(outside / "secret.md", root / "inside.md")
    (root / "plain.md").write_text("visiblenote\n", encoding="utf-8")
    report = _run(root, db, Fake())
    assert _reason(report, "inside.md") == "hard link"
    assert not _match(db, "linkedsecret")
    assert _match(db, "visiblenote")


def test_protected_folder_is_skipped(tmp_path: Path) -> None:
    """Test 5."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    repo = root / "repo"
    repo.mkdir()
    (repo / "secret.md").write_text("hiddenrepo\n", encoding="utf-8")
    (root / "open.md").write_text("visiblenote\n", encoding="utf-8")
    report = _run(root, db, Fake(), protected=[Path(os.path.realpath(repo))])
    assert _reason(report, "repo") == "protected folder"
    assert not _match(db, "hiddenrepo")
    assert _match(db, "visiblenote")
    storage = Path(os.path.realpath(Path(os.environ["LOCALAPPDATA"]) / "Jarvis"))
    repo_root = Path(os.path.realpath(Path(__file__).resolve().parents[1]))
    assert default_protected() == [storage, repo_root]


def test_skipped_names_caps_and_binary(tmp_path: Path) -> None:
    """Test 6."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    for name, word in ((".obsidian", "obsidianword"), (".GIT", "gitword"), (".trash", "trashword")):
        folder = root / name
        folder.mkdir()
        (folder / "x.md").write_text(word + "\n", encoding="utf-8")
    skipped = root / "SkipMe"
    skipped.mkdir()
    (skipped / "x.md").write_text("excludeword\n", encoding="utf-8")
    (root / "note.exe").write_bytes(b"hello")
    (root / "big.md").write_bytes(b"a" * (_TEXT + 1))
    (root / "zero.txt").write_bytes(b"ab\x00cd")
    (root / "bad.txt").write_bytes(b"a\xffb")
    (root / "keep.md").write_text("keepword\n", encoding="utf-8")
    report = _run(root, db, Fake(), exclude=("skipme",))
    assert _reason(report, ".obsidian") == "skipped folder"
    assert _reason(report, ".GIT") == "skipped folder"
    assert _reason(report, ".trash") == "skipped folder"
    assert _reason(report, "SkipMe") == "excluded"
    assert _reason(report, "note.exe") == "extension"
    assert _reason(report, "big.md") == "too large"
    assert _reason(report, "zero.txt") == "binary"
    assert _match(db, "keepword")
    assert "\ufffd" in _chunks(db, "bad.txt")[0]
    for word in ("obsidianword", "gitword", "trashword", "excludeword", "hello"):
        assert not _match(db, word)


def test_chunker(tmp_path: Path) -> None:
    """Test 7."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "heads.md").write_text("# One\n\nalpha\n\n# Two\n\nbeta\n", encoding="utf-8")
    (root / "path.md").write_text("# One\n\n## Two\n\nbody\n", encoding="utf-8")
    (root / "long.md").write_text("p" * 2500, encoding="utf-8")
    (root / "boil.md").write_text("## Boil\n\n" + ("b" * 1500), encoding="utf-8")
    fence = chr(96) * 3
    (root / "fence.md").write_text(
        f"{fence}python\n# boil water\neggs\n{fence}\n", encoding="utf-8"
    )
    (root / "tag.md").write_text("#python\nhello tag\n", encoding="utf-8")
    (root / "crlf.md").write_bytes(
        b"# Title\r\n\r\n" + (b"A" * 600) + b"\r\n\r\n" + (b"B" * 600)
    )
    (root / "empty.md").write_bytes(b"")
    (root / "huge.md").write_text("# " + ("h" * 1200) + "\ndroppedbody\n", encoding="utf-8")
    (root / "pack.md").write_text("# H\n\naaa\n\nbbb\n", encoding="utf-8")
    fake = Fake()
    report = _run(root, db, fake)
    assert _chunks(db, "heads.md") == ["One\nalpha", "Two\nbeta"]
    assert _chunks(db, "path.md") == ["One / Two\nbody"]
    long = _chunks(db, "long.md")
    assert len(long) == 3 and "".join(long) == "p" * 2500
    assert all(len(chunk) <= 1000 for chunk in long)
    boil = _chunks(db, "boil.md")
    assert all(len(chunk) <= 1000 and chunk.startswith("Boil\n") for chunk in boil)
    assert "".join(chunk.removeprefix("Boil\n") for chunk in boil) == "b" * 1500
    assert any("# boil water" in chunk for chunk in _chunks(db, "fence.md"))
    assert any("#python" in chunk for chunk in _chunks(db, "tag.md"))
    crlf = _chunks(db, "crlf.md")
    assert crlf[0].startswith("Title\n") and ("A" * 600) in crlf[0] and "B" not in crlf[0]
    assert all("\r" not in chunk for chunk in crlf)
    assert _chunks(db, "huge.md") == ["h" * 1000]
    assert _chunks(db, "pack.md") == ["H\naaa\n\nbbb"]
    assert _reason(report, "empty.md") == "no text"
    assert all(call for call in fake.calls)
    assert not any(os.path.basename(path) == "empty.md" for path in _paths(db))


def test_model_mismatch_stops(tmp_path: Path) -> None:
    """Test 8."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "keep.md").write_text("keepbody\n", encoding="utf-8")
    conn = connect(db, "ingest")
    conn.execute("INSERT INTO meta (key, value) VALUES ('embedding_model', 'other')")
    conn.execute(
        "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES (?, 1, 1, 't')",
        (str(root / "gone.md"),),
    )
    conn.commit()
    conn.close()
    before = _rows(db)
    fake = Fake()
    with pytest.raises(ModelMismatch, match="reset-documents"):
        _run(root, db, fake)
    assert fake.calls == []
    assert _rows(db) == before
    assert not _match(db, "keepbody")


def test_dry_run_matches_and_does_not_write(tmp_path: Path) -> None:
    """Test 9. Goes through main. Dump and bytes, both after a fresh connection."""
    root = _root(tmp_path)
    (root / "good.md").write_text("hello dry\n", encoding="utf-8")
    (root / "zero.txt").write_bytes(b"a\x00b")
    config = _config(tmp_path / "memory.toml", root)
    db = tmp_path / "memory.db"
    fake = Fake()
    dry = main(
        ["ingest", "--dry-run"], db=db, config=config, protected=[], embedder=fake,
    )
    assert isinstance(dry, Report)
    assert not db.exists()
    assert fake.calls == []
    assert dry.new == 1 and dry.removed == 0
    assert _reason(dry, "zero.txt") == "binary"
    real = main(["ingest"], db=db, config=config, protected=[], embedder=fake)
    assert real == dry
    assert _match(db, "dry")
    before = _snap(db)
    again = main(
        ["ingest", "--dry-run"], db=db, config=config, protected=[], embedder=fake,
    )
    assert _snap(db) == before
    assert len(fake.calls) == 1
    assert again is not None and again.unchanged == 1 and again.new == 0


def test_pdf(tmp_path: Path) -> None:
    """Test 10."""
    from pypdf import PdfWriter

    root, db = _root(tmp_path), tmp_path / "memory.db"
    fixture = (Path(__file__).parent / "fixtures" / "hello.pdf").read_bytes()
    (root / "hello.pdf").write_bytes(fixture)
    (root / "heading.pdf").write_bytes(fixture.replace(b"(Hello PDF)", b"(# Heading)", 1))
    (root / "z.md").write_text("laternote\n", encoding="utf-8")
    blank = root / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(blank)
    secret = root / "secret.pdf"
    locked = PdfWriter()
    locked.add_blank_page(width=72, height=72)
    locked.encrypt("secret", algorithm="RC4-40")
    locked.write(secret)
    huge = root / "huge.pdf"
    huge.write_bytes(b"%PDF")
    os.truncate(huge, _PDF + (1024 * 1024))
    fake = Fake()
    report = _run(root, db, fake)
    assert "Hello PDF" in _chunks(db, "hello.pdf")[0]
    assert _reason(report, "heading.pdf") == "no text"
    assert not any(os.path.basename(path) == "heading.pdf" for path in _paths(db))
    assert _match(db, "laternote")
    assert _reason(report, "blank.pdf") == "no text"
    assert _reason(report, "secret.pdf") == "encrypted"
    assert _reason(report, "huge.pdf") == "too large"
    assert len(fake.calls) == 2
    assert not any(os.path.basename(path) == "blank.pdf" for path in _paths(db))


def test_odd_names(tmp_path: Path) -> None:
    """Test 11. Created and removed with the \\\\?\\ prefix."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "ok.md").write_text("okword\n", encoding="utf-8")
    names = ("con.md", "note.md.", "note.md ", "ca\u200dfe.md")
    made: list[str] = []
    try:
        for name in names:
            made.append(_win_file(root / name))
        report = _run(root, db, Fake())
        assert _reason(report, "con.md") == "reserved or ambiguous file name"
        assert _reason(report, "note.md.") == "reserved or ambiguous file name"
        assert _reason(report, "note.md ") == "reserved or ambiguous file name"
        assert _reason(report, "ca\u200dfe.md") == "unprintable or wildcard character"
        assert _match(db, "okword")
        assert len(_paths(db)) == 1
    finally:
        for win in made:
            os.remove(win)


def test_reset_documents_needs_exact_yes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test 12."""
    missing = tmp_path / "absent.db"

    def boom(_prompt: str) -> str:
        raise AssertionError("input on a missing database")

    monkeypatch.setattr("builtins.input", boom)
    reset_documents(missing)
    assert not missing.exists()

    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "a.md").write_text("keepword\n", encoding="utf-8")
    _run(root, db, Fake())
    review = connect(db, "review")
    review.execute(
        "INSERT INTO facts (text, embedding, approved) VALUES ('keptfact', X'00', 't')"
    )
    review.commit()
    review.close()
    answers = iter(["no", "YES", "y", "", "yes ", "yes"])
    prompts: list[str] = []

    def answer(prompt: str) -> str:
        prompts.append(prompt)
        return next(answers)

    monkeypatch.setattr("builtins.input", answer)
    for _ in range(5):
        main(["reset-documents"], db=db)
        assert _match(db, "keepword")
        assert _meta(db, "embedding_model") == "nomic-embed-text"
        assert _facts(db) == ["keptfact"]
    main(["reset-documents"], db=db)
    assert not _match(db, "keepword")
    assert _paths(db) == []
    assert _meta(db, "embedding_model") is None
    assert _facts(db) == ["keptfact"]
    assert prompts == ["Type yes to delete document chunks: "] * 6


def test_embed_holds_no_write_lock(tmp_path: Path) -> None:
    """Test 13."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "lock.md").write_text("lockword\n", encoding="utf-8")
    ready = connect(db, "ingest")
    ready.close()
    fake = Fake()

    def grab(_texts: list[str]) -> None:
        other = sqlite3.connect(db, timeout=0.2)
        try:
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
        finally:
            other.close()

    fake.on_documents = grab
    _run(root, db, fake)
    assert _match(db, "lockword")


def test_embed_failure_stops(tmp_path: Path) -> None:
    """Test 14."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "a.md").write_text("aaa\n", encoding="utf-8")
    (root / "b.md").write_text("bbb\n", encoding="utf-8")
    (root / "c.md").write_text("ccc\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="embed failed"):
        _run(root, db, Fake(fail_at=2))
    names = [os.path.basename(path) for path in _paths(db)]
    assert names == ["a.md"]
    assert _match(db, "aaa")
    assert not _match(db, "bbb")
    assert not _match(db, "ccc")


def test_missing_root_does_not_write(tmp_path: Path) -> None:
    """Test 16. A renamed root raises from os.walk's onerror; rows stay."""
    root, db = _root(tmp_path), tmp_path / "memory.db"
    (root / "keep.md").write_text("stayword\n", encoding="utf-8")
    docs = _docs(root)
    ingest([docs], db, Fake(), protected=[])
    before = _rows(db)
    away = root.with_name(root.name + "-away")
    root.rename(away)
    try:
        with pytest.raises(OSError):
            ingest([docs], db, Fake(), protected=[])
        assert _rows(db) == before
    finally:
        if away.exists() and not root.exists():
            away.rename(root)


def _config(path: Path, root: Path) -> Path:
    escaped = str(Path(os.path.realpath(root))).replace("\\", "\\\\")
    path.write_text(
        "[embedding]\n"
        'model = "nomic-embed-text"\n'
        'document_prefix = "search_document: "\n'
        'query_prefix = "search_query: "\n'
        "\n"
        "[[docs_root]]\n"
        f'path = "{escaped}"\n'
        "exclude = []\n",
        encoding="utf-8",
    )
    return path


def _snap(db: Path) -> tuple[str, bytes]:
    conn = sqlite3.connect(db)
    try:
        dump = "\n".join(conn.iterdump())
    finally:
        conn.close()
    return dump, db.read_bytes()


def _meta(db: Path, key: str) -> str | None:
    conn = _connect(db)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    finally:
        conn.close()
    return None if row is None else row[0]


def _facts(db: Path) -> list[str]:
    conn = connect(db, "review")
    try:
        return [text for (text,) in conn.execute("SELECT text FROM facts ORDER BY id")]
    finally:
        conn.close()


def _win_file(path: Path) -> str:
    win = "\\\\?\\" + str(path)
    fd = os.open(win, os.O_CREAT | os.O_RDWR | os.O_BINARY)
    os.write(fd, b"x")
    os.close(fd)
    return win
