"""Real tool handlers (P3.1). Each takes the args dict the bridge passes (`path` values
already resolved and checked by the policy) and returns plain JSON data.

Rules (docs/plans/P3.1.md): never build or re-resolve a path, never follow a link, never
read a file with a second name (a handler that opens a file's content calls `_single_name`
on the open handle), raise when the job cannot be done (the bridge logs it and answers
"Tool failed")."""

import ctypes
from ctypes import wintypes
import msvcrt
import os
from pathlib import Path
import stat
import subprocess
import time
import tomllib
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


def _single_name(fd: int) -> os.stat_result:
    """Refuse a file with a second name (hard link): that name may live outside the
    roots, and realpath cannot see it. Every handler that opens content calls this."""
    stat = os.fstat(fd)
    if stat.st_nlink != 1:
        raise OSError("file has more than one hard link")
    return stat


def read_text_file(args: dict[str, Any]) -> dict[str, Any]:
    path = str(args["path"])
    fd = os.open(path, os.O_RDONLY | os.O_BINARY)  # a folder fails here
    with os.fdopen(fd, "rb") as handle:
        # Whatever the open reached must be the path the policy checked. A link swapped in
        # after the check would be followed by the open; this refuses it instead.
        if _final_path(fd).casefold() != path.casefold():
            raise OSError("opened file is not the checked path")
        size = _single_name(fd).st_size
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


def _all_windows() -> list[tuple[str, int, bool, bool, int]]:
    """Every top-level window, topmost first: (title, pid, visible, owned, hwnd)."""
    found = []

    def visit(hwnd, _):
        buffer = ctypes.create_unicode_buffer(_user32.GetWindowTextLengthW(hwnd) + 1)
        _user32.GetWindowTextW(hwnd, buffer, len(buffer))
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        visible = bool(_user32.IsWindowVisible(hwnd))
        owned = bool(_user32.GetWindow(hwnd, GW_OWNER))
        found.append((buffer.value, pid.value, visible, owned, hwnd))
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


def _candidates() -> list[tuple[str, int, int]]:
    """What the taskbar shows: visible, titled, not owned (not a dialog). (title, pid, hwnd)."""
    return [(title, pid, hwnd) for title, pid, visible, owned, hwnd in _all_windows()
            if visible and not owned and title]


def list_windows(args: dict[str, Any]) -> dict[str, Any]:
    """What the taskbar shows: visible, titled, not owned by another window (not a dialog).
    No window handles: focus_window (P3.2) takes a title."""
    shown = [(title, pid) for title, pid, hwnd in _candidates()]
    return {
        "windows": [
            {"title": title[:MAX_TEXT], "pid": pid, "app": _app(pid)}
            for title, pid in shown[:MAX_WINDOWS]
        ],
        "truncated": len(shown) > MAX_WINDOWS,
    }


# Fixed path and arguments, no shell, never reachable by the model (Karthik, 2026-11-13).
NVIDIA_SMI = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "nvidia-smi.exe")
_GPU_QUERY = [
    "--query-gpu=name,utilization.gpu,memory.used,memory.total",
    "--format=csv,noheader,nounits",
]


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


_kernel32.GetSystemTimes.argtypes = [ctypes.POINTER(ctypes.c_ulonglong)] * 3
_kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatus)]


def _cpu_times() -> tuple[int, int]:
    """(idle, total) in 100 ns units since boot. Kernel time includes idle time."""
    idle, kernel, user = ctypes.c_ulonglong(), ctypes.c_ulonglong(), ctypes.c_ulonglong()
    if not _kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        raise ctypes.WinError(ctypes.get_last_error())
    return idle.value, kernel.value + user.value


def _cpu_percent() -> float:
    idle1, total1 = _cpu_times()
    time.sleep(0.2)  # ponytail: blocks the call 0.2 s; a background sampler if that matters
    idle2, total2 = _cpu_times()
    total = total2 - total1
    return 0.0 if total <= 0 else 100 * (1 - (idle2 - idle1) / total)


def _parse_gpu(text: str) -> dict[str, Any] | None:
    """First line of nvidia-smi's CSV (ponytail: first GPU only). None if it is not
    exactly name + three numbers."""
    try:
        name, *numbers = (part.strip() for part in text.strip().splitlines()[0].split(","))
        percent, used, total = (float(number) for number in numbers)
    except (IndexError, ValueError):  # no line, wrong field count, or e.g. "[N/A]"
        return None
    return {
        "name": name,
        "percent": round(percent, 1),
        "vram_used_gb": round(used / 1024, 1),  # nvidia-smi reports MiB
        "vram_total_gb": round(total / 1024, 1),
    }


def _gpu() -> dict[str, Any] | None:
    """None when there is no NVIDIA GPU or nvidia-smi fails: the rest still answers."""
    try:
        done = subprocess.run(
            [str(NVIDIA_SMI), *_GPU_QUERY], capture_output=True, encoding="utf-8",
            errors="replace", timeout=2, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _parse_gpu(done.stdout)


def system_stats(args: dict[str, Any]) -> dict[str, Any]:
    memory = _MemoryStatus(dwLength=ctypes.sizeof(_MemoryStatus))
    if not _kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise ctypes.WinError(ctypes.get_last_error())
    used = memory.ullTotalPhys - memory.ullAvailPhys
    return {
        "cpu_percent": round(_cpu_percent(), 1),
        "ram_used_gb": round(used / 1024**3, 1),
        "ram_total_gb": round(memory.ullTotalPhys / 1024**3, 1),
        "ram_percent": round(100 * used / memory.ullTotalPhys, 1),
        "gpu": _gpu(),
    }


SW_RESTORE = 9
SW_MINIMIZE = 6
_user32.IsIconic.argtypes = [wintypes.HWND]
_user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
_user32.SetForegroundWindow.argtypes = [wintypes.HWND]
_user32.SetForegroundWindow.restype = wintypes.BOOL
_user32.GetForegroundWindow.restype = wintypes.HWND


def _settled(hwnd, timeout=0.5, step=0.01) -> bool:
    # ponytail: 500 ms cap; make it config if a slow app needs more
    deadline = time.monotonic() + timeout
    while True:
        if _user32.GetForegroundWindow() == hwnd:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(step)


def _to_front(hwnd) -> bool:
    """True only when `hwnd` is the foreground window afterwards."""
    _user32.SetForegroundWindow(hwnd)
    if _settled(hwnd):
        return True
    _user32.ShowWindow(hwnd, SW_MINIMIZE)
    _user32.ShowWindow(hwnd, SW_RESTORE)
    return _settled(hwnd)


def focus_window(args: dict[str, Any]) -> dict[str, Any]:
    """Bring forward the topmost taskbar window whose title contains the text, or whose
    app file name without .exe equals it (both case-insensitive). The result carries no
    title: the tool does not taint, so it must not hand untrusted text back (rule 5)."""
    wanted = args["title"].casefold()
    for title, pid, hwnd in _candidates():  # EnumWindows order: the first match is topmost
        app = _app(pid) or ""
        if wanted in title.casefold() or app.casefold().removesuffix(".exe") == wanted:
            break
    else:
        raise LookupError("no matching window")
    if _user32.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, SW_RESTORE)
    # ponytail: if the restore does not land, the UI (P6, a foreground process)
    # can grant AllowSetForegroundWindow to the bridge.
    if not _to_front(hwnd):
        raise OSError("Windows refused to bring the window forward")
    return {"focused": True}


HANDLERS = {
    "list_dir": list_dir,
    "read_text_file": read_text_file,
    "list_windows": list_windows,
    "system_stats": system_stats,
}


def load_commands(config: Path) -> dict[str, list[str]]:
    """config/apps.toml: the fixed command each allowed name starts. Any bad entry raises,
    so the bridge does not start (fail closed). A missing file allows nothing, as
    `safety.policy.load_names`, which still decides which names are allowed."""
    if not config.exists():
        return {}
    commands = {}
    for name, entry in tomllib.loads(config.read_text(encoding="utf-8")).items():
        command = entry.get("command") if isinstance(entry, dict) else None
        if (
            not isinstance(command, list)
            or not command
            or not all(isinstance(part, str) for part in command)
            or command[0].startswith(("\\\\", "//"))  # UNC: code off the network; checked before is_file touches it
            or not Path(command[0]).is_absolute()  # a bare name would be looked up on PATH
            or not Path(command[0]).is_file()
        ):
            raise ValueError(
                f"{config.name}: [{name}] command must be a list whose first item is an "
                "absolute path to an existing local file"
            )
        commands[name] = command
    return commands


def mutating(undo_log, commands: dict[str, list[str]]) -> dict[str, Any]:
    """T1 handlers (P3.2): closures over the bridge's UndoLog and the apps.toml commands."""

    def create_folder(args: dict[str, Any]) -> dict[str, Any]:
        path = args["path"]
        os.mkdir(path)  # parent must exist; an existing name fails, nothing is reused
        try:
            record = undo_log.created(path, "create_folder")
        except Exception as error:
            # Act, then record (P3.2 rule 4): the folder stays, never deleted; the call fails.
            raise OSError(f"folder created but not recorded, left in place: {error}") from error
        return {"created": True, "undo_id": record.id}

    def _move(source: Path, target: Path, tool: str) -> str:
        """Move one plain file to the policy's `target`; returns the undo record id."""
        if not stat.S_ISREG(os.lstat(source).st_mode):  # lstat: a link is never followed
            raise OSError("not a plain file")  # files only in v1 (P3.2 rule 3)
        os.rename(source, target)  # refuses an existing target and a cross-drive move
        try:
            return undo_log.moved(source, target, tool).id
        except Exception as error:
            # Act, then record (rule 4): an unrecorded move is put back; the call fails.
            os.rename(target, source)
            raise OSError(f"moved but not recorded, moved back: {error}") from error

    def rename_file(args: dict[str, Any]) -> dict[str, Any]:
        return {"renamed": True, "undo_id": _move(args["path"], args["target"], "rename_file")}

    def move_file(args: dict[str, Any]) -> dict[str, Any]:
        return {"moved": True, "undo_id": _move(args["source"], args["target"], "move_file")}

    def move_files(args: dict[str, Any]) -> dict[str, Any]:
        """P3.2 F: up to 20 files into one folder. Every check runs before the first move;
        a failure part-way stops and reports (nothing is moved back). No names in the result."""
        pairs = list(zip(args["sources"], args["target"], strict=True))
        folder = os.lstat(args["destination"])  # missing -> FileNotFoundError
        # A reparse point is a junction or symlink swapped in after the policy check.
        if not stat.S_ISDIR(folder.st_mode) or folder.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise NotADirectoryError("destination is not a real folder")
        for source, target in pairs:
            if not stat.S_ISREG(os.lstat(source).st_mode):
                raise OSError("not a plain file")
            if os.path.lexists(target):
                raise FileExistsError("landing name taken")
        undo_ids: list[str] = []
        for source, target in pairs:
            try:
                undo_ids.append(_move(source, target, "move_files"))
            except Exception as error:
                if not undo_ids:
                    raise  # nothing moved: a plain failure
                return {"moved": len(undo_ids), "requested": len(pairs), "complete": False,
                        "undo_ids": undo_ids, "failed": type(error).__name__}
        return {"moved": len(undo_ids), "requested": len(pairs), "complete": True, "undo_ids": undo_ids}

    def open_app(args: dict[str, Any]) -> dict[str, Any]:
        # The model supplies only the name (the policy checked it against apps.toml); the
        # command line is fixed in apps.toml. No shell, no inherited console handles.
        # ponytail: the Popen is never waited on; the app outlives the call on purpose.
        name = args["app"]
        process = subprocess.Popen(
            commands[name], shell=False,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return {"opened": name, "pid": process.pid}

    return {
        "create_folder": create_folder, "rename_file": rename_file, "move_file": move_file,
        "move_files": move_files, "open_app": open_app, "focus_window": focus_window,
    }
