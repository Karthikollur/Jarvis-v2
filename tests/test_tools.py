"""P3.1: the real T0 tool handlers in bridge/tools.py, called directly and through the bridge."""

import _winapi
import json
import os
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from bridge import tools
from bridge.app import create_app, load_token

REPO = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8765"
LOOPBACK = ("127.0.0.1", 50000)


def assert_plain(value):
    """Results must be plain JSON data: dict with str keys, list, str, int, float, bool, None."""
    if isinstance(value, dict):
        for key, item in value.items():
            assert type(key) is str, f"non-str key {key!r}"
            assert_plain(item)
    elif isinstance(value, list):
        for item in value:
            assert_plain(item)
    else:
        assert value is None or type(value) in (str, int, float, bool), f"not plain: {value!r}"


def test_assert_plain_refuses_what_json_would_mangle():
    assert_plain({"a": [1, 2.5, "x", True, None, {"b": []}]})
    for bad in [(1, 2), {(1, 2): "x"}, {1: "x"}, Path("x"), b"x", {"a": {1, 2}}]:
        with pytest.raises(AssertionError):
            assert_plain(bad)


@pytest.fixture
def folders():
    """(root, outside): an empty folder to list and a sibling folder outside it."""
    (REPO / ".test-storage").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=REPO / ".test-storage") as directory:
        base = Path(os.path.realpath(directory))
        (base / "root").mkdir()
        (base / "outside").mkdir()
        yield base / "root", base / "outside"


# --- list_dir -------------------------------------------------------------------


def test_list_dir_entries_sorted_folders_first(folders):
    root, outside = folders
    (root / "b.txt").write_text("abc")
    (root / "A.md").write_text("")
    (root / "zeta").mkdir()
    (root / "Alpha").mkdir()
    result = tools.list_dir({"path": root})
    assert result == {
        "entries": [
            {"name": "Alpha", "type": "dir"},
            {"name": "zeta", "type": "dir"},
            {"name": "A.md", "type": "file", "size": 0},
            {"name": "b.txt", "type": "file", "size": 3},
        ],
        "total": 4,
        "truncated": False,
    }
    assert_plain(result)


def test_list_dir_reports_a_junction_and_never_looks_inside(folders):
    root, outside = folders
    (outside / "secret.txt").write_text("x")
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    result = tools.list_dir({"path": root})
    assert result["entries"] == [{"name": "jump", "type": "link"}]
    assert "secret" not in json.dumps(result)
    assert_plain(result)


def test_list_dir_cap(folders):
    root, outside = folders
    for i in range(tools.MAX_ENTRIES):
        (root / f"{i:03}.txt").write_text("")
    full = tools.list_dir({"path": root})
    assert (len(full["entries"]), full["total"], full["truncated"]) == (200, 200, False)
    (root / "999.txt").write_text("")
    over = tools.list_dir({"path": root})
    assert (len(over["entries"]), over["total"], over["truncated"]) == (200, 201, True)
    assert over["entries"][-1]["name"] == "199.txt"  # sorted first, then cut
    assert_plain(over)


def test_list_dir_empty_folder(folders):
    root, outside = folders
    assert tools.list_dir({"path": root}) == {"entries": [], "total": 0, "truncated": False}


def test_list_dir_on_a_file_fails(folders):
    root, outside = folders
    (root / "f.txt").write_text("x")
    with pytest.raises(OSError):
        tools.list_dir({"path": root / "f.txt"})


# --- read_text_file ---------------------------------------------------------------


def read(path):
    return tools.read_text_file({"path": path})


def test_read_text_file_small(folders):
    root, outside = folders
    (root / "a.txt").write_bytes(b"hello\nworld")
    result = read(root / "a.txt")
    assert result == {"text": "hello\nworld", "bytes": 11, "truncated": False}
    assert_plain(result)


def test_read_text_file_cap(folders):
    root, outside = folders
    (root / "exact.txt").write_bytes(b"a" * tools.MAX_BYTES)
    exact = read(root / "exact.txt")
    assert (len(exact["text"]), exact["bytes"], exact["truncated"]) == (16384, 16384, False)
    (root / "over.txt").write_bytes(b"a" * tools.MAX_BYTES + b"bcd")
    over = read(root / "over.txt")
    assert (over["text"], over["bytes"], over["truncated"]) == ("a" * 16384, 16387, True)
    assert_plain(over)


def test_read_text_file_empty_bom_and_bad_utf8(folders):
    root, outside = folders
    (root / "e.txt").write_bytes(b"")
    assert read(root / "e.txt") == {"text": "", "bytes": 0, "truncated": False}
    (root / "bom.txt").write_bytes(b"\xef\xbb\xbfhi")
    assert read(root / "bom.txt")["text"] == "hi"
    (root / "bad.txt").write_bytes(b"ab\xffcd")
    result = read(root / "bad.txt")
    assert result["text"] == "ab�cd"
    assert_plain(result)


def test_read_text_file_refuses_binary_and_folders(folders):
    root, outside = folders
    (root / "bin.dat").write_bytes(b"ab\x00cd")
    with pytest.raises(ValueError):
        read(root / "bin.dat")
    with pytest.raises(OSError):
        read(root)


def test_read_text_file_refuses_what_it_did_not_check(folders, monkeypatch):
    """If what was opened is not the checked path (a link swapped in after the policy
    check), the read is refused, not followed."""
    root, outside = folders
    (root / "a.txt").write_text("x")
    monkeypatch.setattr(tools, "_final_path", lambda fd: str(outside / "a.txt"))
    with pytest.raises(OSError, match="not the checked path"):
        read(root / "a.txt")


def test_read_text_file_never_reads_through_a_junction(folders):
    """A real link, no privilege needed: the open itself would succeed through the junction,
    so only the final-path check stands between the model and the target."""
    root, outside = folders
    (outside / "secret.txt").write_text("secret")
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    with pytest.raises(OSError, match="not the checked path"):
        read(root / "jump" / "secret.txt")


def test_read_text_file_never_follows_a_symlink(folders):
    root, outside = folders
    (outside / "secret.txt").write_text("secret")
    try:
        os.symlink(outside / "secret.txt", root / "link.txt")
    except OSError:
        pytest.skip("this account may not create symlinks")
    with pytest.raises(OSError):
        read(root / "link.txt")


# --- through the bridge, with the production handler table ----------------------


@pytest.fixture
def bridge(folders):
    """(client, root): a bridge built with handlers=None, i.e. bridge.tools.HANDLERS."""
    root, outside = folders
    storage = root.parent / "storage"
    storage.mkdir()
    app = create_app(storage, roots=[root], protected=[])
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        yield client, root


def fresh_task(client):
    """The bridge starts tainted (P2.9 R2): a first task opens with fresh_context."""
    response = client.post("/task", json={"fresh_context": True})
    assert response.status_code == 200
    return response.json()["task_id"]


def call(client, task, tool, **args):
    return client.post("/tool", json={"task_id": task, "tool": tool, "args": args})


def test_bridge_uses_the_real_list_dir_by_default(bridge):
    client, root = bridge
    (root / "a.txt").write_text("x")
    response = call(client, fresh_task(client), "list_dir", path=str(root))
    assert response.status_code == 200
    assert response.json()["result"]["entries"] == [{"name": "a.txt", "type": "file", "size": 1}]


def test_list_dir_odd_name_still_answers(bridge):
    client, root = bridge
    (root / "x\ud800.txt").write_text("")
    response = call(client, fresh_task(client), "list_dir", path=str(root))
    assert response.status_code == 200
    assert response.json()["result"]["entries"][0]["name"] == "x\ud800.txt"


def test_list_dir_taints_so_a_following_t1_call_waits(bridge):
    client, root = bridge
    clean = fresh_task(client)
    # Control: on a clean task create_folder passes the policy (no handler yet: 501).
    assert call(client, clean, "create_folder", path=str(root / "a")).status_code == 501
    task = fresh_task(client)
    assert call(client, task, "list_dir", path=str(root)).status_code == 200
    queued = call(client, task, "create_folder", path=str(root / "b"))
    assert queued.status_code == 202 and "pending_id" in queued.json()


def test_bridge_uses_the_real_read_text_file(bridge):
    client, root = bridge
    (root / "a.txt").write_text("hi")
    response = call(client, fresh_task(client), "read_text_file", path=str(root / "a.txt"))
    assert response.json() == {"result": {"text": "hi", "bytes": 2, "truncated": False}}


def test_read_text_file_taints_so_a_following_t1_call_waits(bridge):
    client, root = bridge
    (root / "a.txt").write_text("hi")
    task = fresh_task(client)
    assert call(client, task, "read_text_file", path=str(root / "a.txt")).status_code == 200
    queued = call(client, task, "create_folder", path=str(root / "b"))
    assert queued.status_code == 202 and "pending_id" in queued.json()
