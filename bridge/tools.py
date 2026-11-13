"""Real tool handlers (P3.1). Each takes the args dict the bridge passes (`path` values
already resolved and checked by the policy) and returns plain JSON data.

Rules (docs/plans/P3.1.md): never build or re-resolve a path, never follow a link, raise
when the job cannot be done (the bridge logs it and answers "Tool failed")."""

import os
from typing import Any

MAX_ENTRIES = 200  # list_dir: entries returned; `total` still counts all


def _kind(entry: os.DirEntry) -> str:
    # Links first: a junction or symlink is reported, never looked into.
    if entry.is_symlink() or entry.is_junction():
        return "link"
    if entry.is_dir(follow_symlinks=False):
        return "dir"
    if entry.is_file(follow_symlinks=False):
        return "file"
    return "other"


def list_dir(args: dict[str, Any]) -> dict[str, Any]:
    entries = []
    with os.scandir(args["path"]) as listing:
        for entry in listing:
            item = {"name": entry.name, "type": _kind(entry)}
            if item["type"] == "file":
                item["size"] = entry.stat(follow_symlinks=False).st_size
            entries.append(item)
    entries.sort(key=lambda item: (item["type"] != "dir", item["name"].casefold()))
    return {
        "entries": entries[:MAX_ENTRIES],
        "total": len(entries),
        "truncated": len(entries) > MAX_ENTRIES,
    }


HANDLERS = {"list_dir": list_dir}
