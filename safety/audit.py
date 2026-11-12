"""Audit log (P2.4): one JSON line per tool request, decision and result.

The bridge writes each line BEFORE the action it describes. `write` lets OSError
propagate so the caller can fail closed: no line, no action.

Append-only means Jarvis code only appends: there is no method to edit, truncate or
delete. Any process running as Karthik can still edit the file (audit point 6); no hash
chain, since a same-user attacker could recompute it.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_RESULT = 2000  # characters of a tool result kept in the log


class AuditLog:
    # ponytail: one file, no rotation; rotate by date when the P6.4 view gets slow.
    def __init__(self, path: Path, wall: Callable[[], float] = time.time) -> None:
        self._path = path
        self._wall = wall
        self._lock = threading.Lock()  # routes run in a thread pool

    def write(self, event: str, **fields: Any) -> None:
        if "result" in fields:
            result = fields["result"]
            text = result if isinstance(result, str) else json.dumps(result, default=str, ensure_ascii=False)
            fields["result"] = text[:MAX_RESULT]
            if len(text) > MAX_RESULT:
                fields.update(truncated=True, length=len(text))
        ts = datetime.fromtimestamp(self._wall(), timezone.utc).isoformat()
        # json.dumps escapes newlines, so no value can start a second line.
        line = json.dumps({"ts": ts, "event": event, **fields}, default=str, ensure_ascii=False)
        # backslashreplace: a lone surrogate (legal in a Windows file name) cannot be encoded
        # as UTF-8. It is written as \udXXX, which JSON reads back, instead of raising
        # after the action already ran.
        with self._lock, self._path.open(
            "a", encoding="utf-8", errors="backslashreplace", newline="\n"
        ) as handle:
            handle.write(line + "\n")
            handle.flush()
