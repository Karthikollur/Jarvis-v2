"""Real tool handlers (P3.1). Each takes the args dict the bridge passes (`path` values
already resolved and checked by the policy) and returns plain JSON data.

Rules (docs/plans/P3.1.md): never build or re-resolve a path, never follow a link, raise
when the job cannot be done (the bridge logs it and answers "Tool failed")."""

import ctypes
from ctypes import wintypes
import msvcrt
import os
from typing import Any

from safety.policy import MAX_TEXT

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


MAX_WINDOWS = 50  # list_windows: a page full of tabs must not flood the context
GW_OWNER = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

_user32 = ctypes.WinDLL("user32", use_last_error=True)
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
_user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
_user32.IsWindowVisible.argtypes = [wintypes.HWND]
_user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
_user32.GetWindow.restype = wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_kernel32.OpenProcess.restype = wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
]
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]


def _all_windows() -> list[tuple[str, int, bool, bool]]:
    """Every top-level window: (title, pid, visible, owned)."""
    found = []

    def visit(hwnd, _):
        buffer = ctypes.create_unicode_buffer(_user32.GetWindowTextLengthW(hwnd) + 1)
        _user32.GetWindowTextW(hwnd, buffer, len(buffer))
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        visible = bool(_user32.IsWindowVisible(hwnd))
        found.append((buffer.value, pid.value, visible, bool(_user32.GetWindow(hwnd, GW_OWNER))))
        return True

    if not _user32.EnumWindows(_WNDENUMPROC(visit), 0):
        raise ctypes.WinError(ctypes.get_last_error())
    return found


def _app(pid: int) -> str | None:
    """File name of the process image, e.g. "Code.exe"; None if Windows will not say."""
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return None  # e.g. an elevated process, or the idle process
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        if not _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return None
        return os.path.basename(buffer.value)
    finally:
        _kernel32.CloseHandle(handle)


def list_windows(args: dict[str, Any]) -> dict[str, Any]:
    """What the taskbar shows: visible, titled, not owned by another window (not a dialog).
    No window handles: focus_window (P3.2) takes a title."""
    shown = [(title, pid) for title, pid, visible, owned in _all_windows()
             if visible and not owned and title]
    return {
        "windows": [
            {"title": title[:MAX_TEXT], "pid": pid, "app": _app(pid)}
            for title, pid in shown[:MAX_WINDOWS]
        ],
        "truncated": len(shown) > MAX_WINDOWS,
    }


HANDLERS = {
    "list_dir": list_dir,
    "read_text_file": read_text_file,
    "list_windows": list_windows,
}
