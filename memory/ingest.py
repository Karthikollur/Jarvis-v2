"""Ingest local documents into memory.db. Reads the docs roots; never writes them.

_final_path, _single_name and the text decode are copied from bridge/tools.py.
memory/ does not import bridge: section D makes the bridge import memory.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import datetime
import msvcrt
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np
from pypdf import PdfReader

from memory.embed import DocsRoot, load
from memory.store import connect
from safety.policy import PathRefused, resolve_inside

# ponytail: fixed 1000, no overlap; tune only from the doc eval.
_CHUNK = 1000
_TEXT_CAP = 2 * 1024 * 1024
_PDF_CAP = 20 * 1024 * 1024
_DOTS = frozenset({".obsidian", ".git", ".trash"})
_HEADING = re.compile(r"^(#{1,6})(?:[ \t]+(.*))?$")
_FENCE = chr(96) * 3
_MODEL_KEY = "embedding_model"
_RESET = "delete memory.db chunks with " + chr(96) + "python -m memory reset-documents" + chr(96)

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetFinalPathNameByHandleW.argtypes = [
    wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
]
_kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD


class ModelMismatch(RuntimeError):
    """meta.embedding_model is not the model this run would write."""


@dataclass(frozen=True)
class Report:
    new: int
    changed: int
    unchanged: int
    removed: int
    skipped: tuple[tuple[str, str], ...]


@dataclass
class _Kept:
    path: str
    size: int
    mtime_ns: int
    chunks: list[str] | None  # None: unchanged, content not read


def default_protected() -> list[Path]:
    """The repo and the bridge's storage. Both already realpath'd. Does not create storage."""
    storage = Path(os.environ["LOCALAPPDATA"]) / "Jarvis"
    repo = Path(__file__).resolve().parent.parent
    return [Path(os.path.realpath(storage)), Path(os.path.realpath(repo))]


def default_db() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "Jarvis" / "memory.db"


def ingest(
    roots: list[DocsRoot],
    db: Path,
    embedder: Any,
    *,
    protected: list[Path] | None = None,
    dry_run: bool = False,
) -> Report:
    """Walk every root, then embed and write. A dry run does neither of those two."""
    protected = [] if protected is None else protected
    model = embedder.model
    existing, stored = _load_state(db)
    read_files = True
    kept, skipped = _walk(
        roots, [root.path for root in roots], protected, existing, read_files,
    )
    if stored is not None and stored != model:
        raise ModelMismatch(
            f"embedding model is {stored!r}, not {model!r}. {_RESET}"
        )
    new, changed, unchanged, accepted = _divide(kept, existing)
    removed = [path for path in existing if path not in accepted]
    report = Report(
        len(new), len(changed), unchanged, len(removed), tuple(skipped),
    )
    do_embed = not dry_run
    do_write = not dry_run
    pending = sorted(new + changed, key=lambda item: item.path)
    if do_embed or do_write:
        _apply(
            db, removed, pending, embedder, model, stored is None, do_embed, do_write,
        )
    return report


def reset_documents(db: Path) -> None:
    """Delete every document and the embedding-model key. Exact yes only.

    A missing database is left missing. Facts are not this role's rows.
    """
    if not db.exists():
        return
    if input("Type yes to delete document chunks: ") != "yes":
        return
    conn = connect(db, "ingest")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM meta WHERE key = ?", (_MODEL_KEY,))
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
    protected: list[Path] | None = None,
    embedder: Any = None,
) -> Report | None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in {"ingest", "reset-documents"}:
        raise SystemExit("usage: python -m memory ingest [--dry-run] | reset-documents")
    if db is None:
        db = default_db()
    if args[0] == "reset-documents":
        if len(args) != 1:
            raise SystemExit("usage: python -m memory reset-documents")
        reset_documents(db)
        return None
    if args[1:] not in ([], ["--dry-run"]):
        raise SystemExit("usage: python -m memory ingest [--dry-run]")
    if config is None:
        config = Path(__file__).resolve().parent.parent / "config" / "memory.toml"
    if protected is None:
        protected = default_protected()
    loaded, roots = load(config)
    report = ingest(
        roots,
        db,
        loaded if embedder is None else embedder,
        protected=protected,
        dry_run=args[1:] == ["--dry-run"],
    )
    print(
        f"new {report.new} changed {report.changed} "
        f"unchanged {report.unchanged} removed {report.removed}"
    )
    for path, reason in report.skipped:
        print(f"skipped\t{reason}\t{path}")
    return report


def chunk_text(text: str) -> list[str]:
    """Heading path, then paragraphs, packed to _CHUNK characters of stored text."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    stack: list[str] = []
    body: list[str] = []
    sections: list[tuple[tuple[str, ...], list[str]]] = []
    in_fence = False

    def flush() -> None:
        nonlocal body
        sections.append((tuple(stack), body))
        body = []

    for line in text.split("\n"):
        stripped = line.lstrip(" \t")
        if stripped.startswith((_FENCE, "~~~")):
            body.append(line)
            in_fence = not in_fence
            continue
        if not in_fence:
            match = _HEADING.match(line)
            if match is not None:
                flush()
                title = (match.group(2) or "").strip(" \t")
                stack = stack[: len(match.group(1)) - 1]
                if title:
                    stack.append(title)
                continue
        body.append(line)
    flush()
    return _pack(sections)


def _pack(sections: list[tuple[tuple[str, ...], list[str]]]) -> list[str]:
    chunks: list[str] = []
    for stack, lines in sections:
        head = (" / ".join(stack) + "\n") if stack else ""
        if len(head) >= _CHUNK:  # a heading line over the cap: its first 1000, body dropped
            chunks.append(head[:_CHUNK])
            continue
        room = _CHUNK - len(head)
        buf = ""
        for para in _paragraphs(lines):
            while para:
                if not buf:
                    if len(para) <= room:
                        buf = para
                        para = ""
                    else:
                        chunks.append(head + para[:room])
                        para = para[room:]
                elif len(buf) + 2 + len(para) <= room:
                    buf = buf + "\n\n" + para
                    para = ""
                else:
                    chunks.append(head + buf)
                    buf = ""
        if buf:
            chunks.append(head + buf)
    return chunks


def _paragraphs(lines: list[str]) -> list[str]:
    body = "\n".join(lines).strip("\n")
    if not body:
        return []
    return [
        part.strip(" \t")
        for part in re.split(r"\n[ \t]*\n", body)
        if part.strip(" \t")
    ]


def _walk(
    roots: list[DocsRoot],
    root_paths: list[Path],
    protected: list[Path],
    existing: dict[str, tuple[int, int]],
    read: bool,
) -> tuple[list[_Kept], list[tuple[str, str]]]:
    kept: list[_Kept] = []
    skipped: list[tuple[str, str]] = []
    for root in roots:
        exclude = {name.casefold() for name in root.exclude}
        for dirpath, dirnames, filenames in os.walk(
            str(root.path),
            topdown=True,
            onerror=_onerror,
            followlinks=False,
        ):
            dirnames.sort()
            filenames.sort()
            kept_dirs = []
            for name in dirnames:
                full = os.path.join(dirpath, name)
                reason = _dir_reason(full, name, exclude, root_paths, protected)
                if reason is None:
                    kept_dirs.append(name)
                else:
                    skipped.append((full, reason))
            dirnames[:] = kept_dirs
            for name in filenames:
                full = os.path.join(dirpath, name)
                item, reason = _file(full, root_paths, protected, existing, read)
                if reason is not None:
                    skipped.append((full, reason))
                elif item is not None:
                    kept.append(item)
    return kept, skipped


def _onerror(error: OSError) -> None:
    raise error


def _dir_reason(
    path: str,
    name: str,
    exclude: set[str],
    roots: list[Path],
    protected: list[Path],
) -> str | None:
    info = os.lstat(path)
    if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        return "reparse point"
    folded = name.casefold()
    if folded in exclude:
        return "excluded"
    if folded in _DOTS:
        return "skipped folder"
    return _inside(path, roots, protected)


def _file(
    path: str,
    roots: list[Path],
    protected: list[Path],
    existing: dict[str, tuple[int, int]],
    read: bool,
) -> tuple[_Kept | None, str | None]:
    # Name check before the suffix, so note.md. and "note.md " report the policy
    # message. con.md is refused here and never opened.
    refused = _inside(path, roots, protected)
    if refused is not None:
        return None, refused
    suffix = os.path.splitext(path)[1].casefold()
    if suffix not in {".md", ".txt", ".pdf"}:
        return None, "extension"
    info = os.lstat(path)
    size, mtime = info.st_size, info.st_mtime_ns
    pdf = suffix == ".pdf"
    if _over_pdf(size) if pdf else _over_text(size):
        return None, "too large"
    if existing.get(path) == (size, mtime):
        return _Kept(path, size, mtime, None), None
    if not read:
        return _Kept(path, size, mtime, [""]), None
    data, reason = _open(path, pdf)
    if reason is not None:
        return None, reason
    if pdf:
        text, reason = _pdf_text(path)
        if reason is not None:
            return None, reason
        if _blank(text):
            return None, "no text"
    else:
        assert data is not None
        if _over_text(len(data)):
            return None, "too large"
        if b"\x00" in data:
            return None, "binary"
        text = data.decode("utf-8-sig", errors="replace")
    chunks = chunk_text(text or "")
    if not pdf and not chunks:
        return None, "no text"
    return _Kept(path, size, mtime, chunks), None


def _over_text(size: int) -> bool:
    return size > _TEXT_CAP


def _over_pdf(size: int) -> bool:
    return size > _PDF_CAP


def _blank(text: str | None) -> bool:
    return not (text or "").strip()


def _inside(path: str, roots: list[Path], protected: list[Path]) -> str | None:
    try:
        resolve_inside(path, roots, protected)
    except PathRefused as exc:
        return str(exc)
    return None


def _open(path: str, pdf: bool) -> tuple[bytes | None, str | None]:
    fd = os.open(path, os.O_RDONLY | os.O_BINARY)
    try:
        final = _final_path(fd)
        if final.casefold() != path.casefold():
            return None, "resolved path differs"
        try:
            _single_name(fd)
        except OSError as exc:
            if "hard link" not in str(exc):
                raise
            return None, "hard link"
        if pdf:
            return None, None
        data = os.read(fd, _TEXT_CAP + 1)
    finally:
        os.close(fd)
    return data, None


def _pdf_text(path: str) -> tuple[str | None, str | None]:
    try:
        reader = PdfReader(path)
        if reader.is_encrypted:
            return None, "encrypted"
        parts = [(page.extract_text() or "") for page in reader.pages]
    except Exception:
        return None, "unreadable"
    return "\n".join(parts), None


def _final_path(fd: int) -> str:
    """The real path of what fd has open, as Windows sees it (links resolved)."""
    buffer = ctypes.create_unicode_buffer(32768)
    length = _kernel32.GetFinalPathNameByHandleW(
        msvcrt.get_osfhandle(fd), buffer, len(buffer), 0,
    )
    if not 0 < length < len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value.removeprefix("\\\\?\\")


def _single_name(fd: int) -> os.stat_result:
    """Refuse a file with a second name (hard link). realpath cannot see it."""
    info = os.fstat(fd)
    if info.st_nlink != 1:
        raise OSError("file has more than one hard link")
    return info


def _divide(
    kept: list[_Kept], existing: dict[str, tuple[int, int]],
) -> tuple[list[_Kept], list[_Kept], int, set[str]]:
    new: list[_Kept] = []
    changed: list[_Kept] = []
    accepted: set[str] = set()
    unchanged = 0
    for item in kept:
        accepted.add(item.path)
        if item.chunks is None:
            unchanged += 1
        elif item.path in existing:
            changed.append(item)
        else:
            new.append(item)
    return new, changed, unchanged, accepted


def _apply(
    db: Path,
    removed: list[str],
    pending: list[_Kept],
    embedder: Any,
    model: str,
    write_model: bool,
    do_embed: bool,
    do_write: bool,
) -> None:
    if do_write and removed:
        conn = connect(db, "ingest")
        try:
            _delete(conn, removed)
        finally:
            conn.close()
    for item in pending:
        assert item.chunks is not None
        vectors = _vectors(embedder, item.chunks) if do_embed else None
        if not do_write:
            continue
        conn = connect(db, "ingest")
        try:
            assert vectors is not None
            _write_one(conn, item, vectors, model if write_model else None)
        finally:
            conn.close()
        write_model = False


def _delete(conn: sqlite3.Connection, paths: list[str]) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        for path in paths:
            conn.execute("DELETE FROM documents WHERE path = ?", (path,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _write_one(
    conn: sqlite3.Connection,
    item: _Kept,
    vectors: np.ndarray,
    model: str | None,
) -> None:
    assert item.chunks is not None
    conn.execute("BEGIN IMMEDIATE")
    try:
        if model is not None:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)", (_MODEL_KEY, model),
            )
        conn.execute("DELETE FROM documents WHERE path = ?", (item.path,))
        cursor = conn.execute(
            "INSERT INTO documents (path, size, mtime_ns, ingested) VALUES (?, ?, ?, ?)",
            (item.path, item.size, item.mtime_ns, _now()),
        )
        # The chunks trigger inserts into FTS and would replace lastrowid.
        document_id = cursor.lastrowid
        for seq, text in enumerate(item.chunks):
            conn.execute(
                "INSERT INTO chunks (document_id, seq, text, embedding) VALUES (?, ?, ?, ?)",
                (document_id, seq, text, _blob(vectors[seq])),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _vectors(embedder: Any, chunks: list[str]) -> np.ndarray:
    vectors = np.asarray(embedder.documents(chunks), dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise RuntimeError(
            f"embedder returned {getattr(vectors, 'shape', None)} for {len(chunks)} chunks"
        )
    return vectors


def _blob(row: np.ndarray) -> bytes:
    return np.ascontiguousarray(row, dtype=np.float32).tobytes()


def _load_state(db: Path) -> tuple[dict[str, tuple[int, int]], str | None]:
    """Read rows without connect: that creates the file and sets WAL."""
    if not db.exists():
        return {}, None
    conn = sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = {
            path: (size, mtime)
            for path, size, mtime in conn.execute(
                "SELECT path, size, mtime_ns FROM documents"
            )
        }
        found = conn.execute(
            "SELECT value FROM meta WHERE key = ?", (_MODEL_KEY,),
        ).fetchone()
    finally:
        conn.close()
    return rows, None if found is None else found[0]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
