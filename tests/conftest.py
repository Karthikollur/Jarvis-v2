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
    return Policy([dirs[0]], clock)
