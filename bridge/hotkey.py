"""Global kill-switch hotkey (P2.5), stdlib ctypes only.

A daemon thread registers the combo with RegisterHotKey and waits for WM_HOTKEY. If the
combo cannot be registered (another program holds it), `listen` raises and the bridge
refuses to start: no kill switch, no tools.
"""

from __future__ import annotations

import ctypes
import threading
import tomllib
import traceback
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
user32.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)
user32.PostThreadMessageW.argtypes = (wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000  # holding the keys fires once
MODIFIERS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
KEYS = {
    **{chr(code): code for code in range(ord("A"), ord("Z") + 1)},
    **{str(digit): 0x30 + digit for digit in range(10)},
    **{f"F{n}": 0x6F + n for n in range(1, 25)},
    "END": 0x23, "HOME": 0x24, "PAUSE": 0x13, "INSERT": 0x2D, "DELETE": 0x2E, "ESC": 0x1B,
}


def parse(combo: object) -> tuple[int, int]:
    """'Ctrl+Alt+End' -> (modifier bits, virtual-key code). At least one modifier."""
    if not isinstance(combo, str):
        raise ValueError("hotkey must be text like 'Ctrl+Alt+End'")
    *names, key = [part.strip() for part in combo.split("+")]
    modifiers = 0
    for name in names:
        bit = MODIFIERS.get(name.lower())
        if bit is None or modifiers & bit:
            raise ValueError(f"bad modifier in hotkey {combo!r}")
        modifiers |= bit
    if not modifiers:
        raise ValueError(f"hotkey {combo!r} needs Ctrl, Alt, Shift or Win")
    if key.upper() not in KEYS:
        raise ValueError(f"unknown key in hotkey {combo!r}")
    return modifiers, KEYS[key.upper()]


def load(config: Path) -> str:
    """Read config/hotkey.toml (`stop = "Ctrl+Alt+End"`). Only Karthik edits that file."""
    combo = tomllib.loads(config.read_text(encoding="utf-8")).get("stop")
    parse(combo)
    return combo


class Listener:
    def __init__(self, combo: str, callback: Callable[[], object]) -> None:
        modifiers, vk = parse(combo)
        self.thread_id = 0
        self._error: str | None = None
        ready = threading.Event()
        self.thread = threading.Thread(
            target=self._run, args=(combo, modifiers | MOD_NOREPEAT, vk, callback, ready),
            name="jarvis-hotkey", daemon=True,
        )
        self.thread.start()
        ready.wait()
        if self._error:
            self.thread.join()
            raise RuntimeError(self._error)

    def _run(self, combo, modifiers, vk, callback, ready) -> None:
        self.thread_id = kernel32.GetCurrentThreadId()
        if not user32.RegisterHotKey(None, 1, modifiers, vk):
            self._error = f"hotkey {combo} could not be registered (error {ctypes.get_last_error()})"
            ready.set()
            return
        ready.set()
        try:
            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    try:
                        callback()
                    except Exception:
                        traceback.print_exc()  # keep listening: a dead kill switch is worse
        finally:
            user32.UnregisterHotKey(None, 1)

    def alive(self) -> bool:
        """False once the listening thread has ended, for any reason: the hotkey is gone."""
        return self.thread.is_alive()

    def close(self) -> None:
        user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
        self.thread.join(timeout=5)


def listen(combo: str, callback: Callable[[], object]) -> Listener:
    """Start listening; raises RuntimeError if the combo is taken."""
    return Listener(combo, callback)
