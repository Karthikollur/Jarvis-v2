"""Quarantine and undo records (P2.6).

Deletes and overwrites move the original into quarantine instead of destroying it; moves,
renames and created folders leave a record. `undo` reverses one record. Nothing here ever
deletes or overwrites: every move is `os.rename`, which on Windows refuses an existing
target and refuses to cross drives, so a refusal always means nothing moved.

Layout, one folder per record: `<folder>/<id>/record.json`, plus `<folder>/<id>/item`
(the quarantined file or folder itself) for kind `quarantined`. Quarantine-side paths are
derived from the id only, never read from `record.json`: any same-user process can edit
it (audit point 6). User-side paths in the record are re-checked by `resolve` on undo.
"""

from __future__ import annotations

import errno
import json
import os
import re
import tempfile
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

from safety.policy import PathRefused

KINDS = {"quarantined": ("path",), "moved": ("source", "destination"), "created": ("path",)}
_ID = re.compile(r"[0-9a-f]{32}")


class UndoRefused(Exception):
    pass


class UnknownRecord(UndoRefused):
    pass


@dataclass(frozen=True)
class Record:
    id: str
    ts: str
    kind: str
    tool: str
    path: str | None = None
    source: str | None = None
    destination: str | None = None
    undone: str | None = None


def _is_link(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _rename(source: Path, target: Path) -> None:
    """The only way anything moves. Refuses instead of overwriting, nesting or copying."""
    try:
        os.rename(source, target)
    except OSError as error:
        if getattr(error, "winerror", None) == 17 or error.errno == errno.EXDEV:
            raise UndoRefused("cannot move across drives") from error
        raise UndoRefused(f"move failed: {type(error).__name__}") from error


class UndoLog:
    # ponytail: no purge; Karthik empties quarantine by hand until its size matters.
    def __init__(self, folder: Path, wall: Callable[[], float] = time.time) -> None:
        self._folder = folder
        self._wall = wall
        self._lock = threading.Lock()  # routes run in a thread pool; one undo at a time
        folder.mkdir(parents=True, exist_ok=True)

    # --- writing records -----------------------------------------------------

    def _new(self, kind: str, tool: str, **paths: Path) -> Record:
        ts = datetime.fromtimestamp(self._wall(), timezone.utc).isoformat()
        values = {name: str(path) for name, path in paths.items()}
        return Record(uuid.uuid4().hex, ts, kind, tool, **values)

    def _save(self, record: Record) -> None:
        """Write record.json atomically (temp file + os.replace in the record folder)."""
        folder = self._folder / record.id
        fd, name = tempfile.mkstemp(dir=folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            # ASCII-escaped: a lone surrogate (legal in an NTFS name) cannot be written as
            # UTF-8, and this runs AFTER the item moved (P2.9 R4).
            json.dump(asdict(record), handle)
        os.replace(name, folder / "record.json")

    def quarantine(self, path: Path, tool: str) -> Record:
        """Move a file or folder into quarantine. Call before a delete or an overwrite."""
        record = self._new("quarantined", tool, path=path)
        # An empty record folder is left behind if the move is refused; `list` skips it.
        (self._folder / record.id).mkdir()
        _rename(path, self._folder / record.id / "item")
        self._save(record)
        return record

    def moved(self, source: Path, destination: Path, tool: str) -> Record:
        """Record a move or rename that already happened."""
        return self._record(self._new("moved", tool, source=source, destination=destination))

    def created(self, path: Path, tool: str) -> Record:
        """Record a folder that was just created."""
        return self._record(self._new("created", tool, path=path))

    def _record(self, record: Record) -> Record:
        (self._folder / record.id).mkdir()
        self._save(record)
        return record

    # --- reading records -----------------------------------------------------

    def get(self, record_id: object) -> Record:
        if not isinstance(record_id, str) or not _ID.fullmatch(record_id):
            raise UnknownRecord("unknown record")
        folder = self._folder / record_id
        if _is_link(folder):
            raise UndoRefused("record folder is a link")
        try:
            text = (folder / "record.json").read_text(encoding="utf-8")
        except FileNotFoundError:
            raise UnknownRecord("unknown record") from None
        try:
            record = Record(**json.loads(text))
        except (TypeError, ValueError):
            raise UndoRefused("unreadable record") from None
        needed = KINDS.get(record.kind)
        if (
            record.id != record_id
            or needed is None
            or any(not isinstance(getattr(record, name), str) for name in needed)
            or not all(isinstance(getattr(record, f.name), (str, type(None))) for f in fields(record))
        ):
            raise UndoRefused("unreadable record")
        return record

    def list(self) -> list[Record]:
        """Every readable record, newest first."""
        records = []
        for entry in self._folder.iterdir():
            try:
                records.append(self.get(entry.name))
            except UndoRefused:
                continue
        return sorted(records, key=lambda record: record.ts, reverse=True)

    # --- undo ----------------------------------------------------------------

    def undo(self, record_id: object, resolve: Callable[[str], Path]) -> Record:
        """Reverse one record. Raises UndoRefused (nothing moved) instead of overwriting.

        `resolve` is the policy's path check. Only user-side paths go through it, and each
        must resolve to exactly the path stored, so a junction swapped in is refused.
        Quarantine-side paths are protected and derived from the id, never resolved.
        """
        with self._lock:
            record = self.get(record_id)
            if record.undone is not None:
                raise UndoRefused("already undone")
            paths = {name: self._check(resolve, getattr(record, name)) for name in KINDS[record.kind]}
            if record.kind == "created":
                if not paths["path"].is_dir():
                    raise UndoRefused("the folder to undo is missing")
                self.quarantine(paths["path"], f"undo:{record.id}")
            else:
                if record.kind == "quarantined":
                    item, target = self._folder / record.id / "item", paths["path"]
                    if _is_link(item):
                        raise UndoRefused("quarantined item is a link")
                else:
                    item, target = paths["destination"], paths["source"]
                if not os.path.lexists(item):
                    raise UndoRefused("the item to move back is missing")
                if os.path.lexists(target):
                    raise UndoRefused("original location is occupied")
                _rename(item, target)
            ts = datetime.fromtimestamp(self._wall(), timezone.utc).isoformat()
            done = Record(**{**asdict(record), "undone": ts})
            self._save(done)
            return done

    @staticmethod
    def _check(resolve: Callable[[str], Path], stored: str) -> Path:
        try:
            now = resolve(stored)
        except PathRefused as refused:
            raise UndoRefused(f"path: {refused}") from None
        if now != Path(stored):
            raise UndoRefused("path changed since the record was made")
        return now
