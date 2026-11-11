import threading
from pathlib import Path

import pytest

from bridge import hotkey
from bridge.hotkey import Listener, listen, load, parse  # bound before conftest fakes `listen`

REPO = Path(__file__).resolve().parents[1]

FREE = "Ctrl+Alt+Shift+F24"  # a combo nothing else on this machine uses


def press(listener):
    """What Windows does when the combo is pressed: WM_HOTKEY to the listening thread."""
    assert hotkey.user32.PostThreadMessageW(listener.thread_id, hotkey.WM_HOTKEY, 1, 0)


@pytest.mark.parametrize(
    "combo, expected",
    [
        ("Ctrl+Alt+End", (0x2 | 0x1, 0x23)),
        ("ctrl + shift + f24", (0x2 | 0x4, 0x87)),
        ("Win+K", (0x8, ord("K"))),
        ("Alt+0", (0x1, 0x30)),
    ],
)
def test_parse(combo, expected):
    assert parse(combo) == expected


@pytest.mark.parametrize(
    "combo", ["End", "Ctrl+Bogus", "", "Ctrl+", "+End", "Ctrl+Ctrl+End", "Ctrl+End+End", 42, None]
)
def test_parse_refuses(combo):
    with pytest.raises(ValueError):
        parse(combo)


def test_shipped_config():
    assert load(REPO / "config" / "hotkey.toml") == "Ctrl+Alt+End"


@pytest.mark.parametrize("text", ['stop = "End"', "stop = 5", 'other = "Ctrl+Alt+End"', ""])
def test_bad_config_refused(dirs, text):
    path = dirs[0] / "hotkey.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load(path)


def test_real_listener_fires_and_closes():
    pressed = threading.Event()
    listener = listen(FREE, pressed.set)
    try:
        assert isinstance(listener, Listener)
        press(listener)
        assert pressed.wait(5)
    finally:
        listener.close()
    assert not listener.thread.is_alive()
    listen(FREE, lambda: None).close()  # unregistered on close: the combo is free again


def test_taken_combo_refused():
    first = listen(FREE, lambda: None)
    try:
        with pytest.raises(RuntimeError, match="could not be registered"):
            listen(FREE, lambda: None)
    finally:
        first.close()


def test_failing_callback_does_not_kill_listener():
    calls = []
    second = threading.Event()

    def callback():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("first press fails")
        second.set()

    listener = listen(FREE, callback)
    try:
        press(listener)
        press(listener)
        assert second.wait(5)
    finally:
        listener.close()
