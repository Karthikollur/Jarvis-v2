import tempfile
from pathlib import Path

import pytest

from safety.policy import Policy

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def dirs():
    """(root, outside): an allowed root and a sibling folder that is not allowed."""
    storage = REPO / ".test-storage"
    storage.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=storage) as directory:
        root, outside = Path(directory) / "root", Path(directory) / "outside"
        root.mkdir()
        outside.mkdir()
        yield root, outside


class Clock:
    now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def policy(dirs, clock):
    return Policy([dirs[0]], clock, apps={"notepad"}, scripts={"x"})


class FakeListener:
    def __init__(self, combo, callback):
        self.combo, self.callback, self.closed = combo, callback, False
        self.dead = False  # a test sets this to simulate the hotkey thread dying

    def alive(self):
        return not (self.closed or self.dead)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def fake_hotkey(monkeypatch):
    """The suite never grabs a real global hotkey. Returns the listeners the bridge made.
    tests/test_hotkey.py imported the real `listen` before this runs."""
    made = []

    def listen(combo, callback):
        made.append(FakeListener(combo, callback))
        return made[-1]

    monkeypatch.setattr("bridge.hotkey.listen", listen)
    return made
