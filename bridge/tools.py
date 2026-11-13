"""Real tool handlers (P3.1). Each takes the args dict the bridge passes (`path` values
already resolved and checked by the policy) and returns plain JSON data.

Rules (docs/plans/P3.1.md): never build or re-resolve a path, never follow a link, raise
when the job cannot be done (the bridge logs it and answers "Tool failed")."""

import ctypes
from ctypes import wintypes
import msvcrt
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


MAX_BYTES = 16 * 1024  # read_text_file: about 4k tokens for the 4B model

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.GetFinalPathNameByHandleW.argtypes = [
    wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD,
]
_kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD


def _final_path(fd: int) -> str:
    """The real path of what `fd` has open, as Windows sees it (links resolved)."""
    buffer = ctypes.create_unicode_buffer(32768)
    length = _kernel32.GetFinalPathNameByHandleW(msvcrt.get_osfhandle(fd), buffer, len(buffer), 0)
    if not 0 < length < len(buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value.removeprefix("\\\\?\\")


def read_text_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args["path"])
    fd = os.open(path, os.O_RDONLY | os.O_BINARY)  # a folder fails here
    with os.fdopen(fd, "rb") as handle:
        # Whatever the open reached must be the path the policy checked. A link swapped in
        # after the check would be followed by the open; this refuses it instead.
        if _final_path(fd).casefold() != path.casefold():
            raise OSError("opened file is not the checked path")
        size = os.fstat(fd).st_size
        data = handle.read(MAX_BYTES + 1)
    if b"\x00" in data:
        raise ValueError("not a text file")
    return {
        "text": data[:MAX_BYTES].decode("utf-8-sig", errors="replace"),
        "bytes": size,
        "truncated": len(data) > MAX_BYTES,
    }


HANDLERS = {"list_dir": list_dir, "read_text_file": read_text_file}
