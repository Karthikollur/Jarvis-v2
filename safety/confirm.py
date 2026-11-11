"""Confirm queue (P2.3): actions waiting for Karthik's click in the UI.

A pending action is one-shot: `take` removes it, so it can be approved or denied once.
What runs on approval is exactly what was stored here. In memory only: a bridge restart
drops every pending action (fails closed).
"""

from __future__ import annotations

import copy
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_PENDING = 16  # across all tasks; limits confirmation flooding


class QueueRefused(Exception):
    """The action was not queued; the message is safe to show."""


@dataclass(frozen=True)
class Pending:
    id: str
    task_id: str
    tool: str
    args: dict[str, Any]
    paths: dict[str, Path]  # resolved at request time; recheck must match them
    reason: str  # "T2" or "tainted T1"
    created: float


class ConfirmQueue:
    def __init__(self, clock: Callable[[], float], limit: int = MAX_PENDING) -> None:
        self.clock = clock
        self.limit = limit
        self._items: dict[str, Pending] = {}
        self._lock = threading.Lock()  # routes run in a thread pool

    def add(
        self, task_id: str, tool: str, args: dict[str, Any], paths: dict[str, Path], reason: str
    ) -> Pending:
        with self._lock:
            if any(p.task_id == task_id for p in self._items.values()):
                raise QueueRefused("awaiting confirmation")
            if len(self._items) >= self.limit:
                raise QueueRefused(f"too many actions awaiting confirmation ({self.limit})")
            pending = Pending(
                uuid.uuid4().hex, task_id, tool, copy.deepcopy(args), dict(paths), reason,
                self.clock(),
            )
            self._items[pending.id] = pending
            return pending

    def list(self) -> list[Pending]:
        with self._lock:
            return list(self._items.values())

    def for_task(self, task_id: str) -> Pending | None:
        with self._lock:
            return next((p for p in self._items.values() if p.task_id == task_id), None)

    def take(self, pending_id: str) -> Pending | None:
        with self._lock:
            return self._items.pop(pending_id, None)

    def clear(self) -> None:
        """For the kill switch (P2.5)."""
        with self._lock:
            self._items.clear()
