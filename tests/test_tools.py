"""P3.1: the real T0 tool handlers in bridge/tools.py, called directly and through the bridge."""

import _winapi
import json
import os
import socket
import stat
import subprocess
from pathlib import Path
import tempfile
import types

import pytest
from fastapi.testclient import TestClient

from bridge import tools
from bridge import app as bridge_app
from bridge.app import create_app, load_token
from core.router import APP_ALIASES
from evals.stub_tools import APPS, SCRIPTS
from safety.policy import load_names
from safety.undo import UndoLog

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


def test_read_text_file_refuses_a_hard_link(folders):
    """P3.1b G2: a hard link's other name may be outside the roots; realpath cannot see it."""
    root, outside = folders
    (outside / "secret.txt").write_text("secret")
    os.link(outside / "secret.txt", root / "innocent.txt")
    with pytest.raises(OSError, match="hard link"):
        read(root / "innocent.txt")
    (root / "plain.txt").write_text("plain")
    assert read(root / "plain.txt")["text"] == "plain"


# --- list_windows -----------------------------------------------------------------


def test_list_windows_on_this_desktop():
    """Real call. The list may be empty in a session without a desktop; the shape may not."""
    result = tools.list_windows({})
    assert set(result) == {"windows", "truncated"}
    for window in result["windows"]:
        assert set(window) == {"title", "pid", "app"}
        assert window["title"] and len(window["title"]) <= 200
        assert window["app"] is None or "\\" not in window["app"]
    assert_plain(result)


def test_app_name_is_the_image_file_name_only():
    assert tools._app(os.getpid()).lower() == "python.exe"
    assert tools._app(0) is None  # the idle process cannot be opened


def test_list_windows_keeps_only_taskbar_windows(monkeypatch):
    # (title, pid, visible, owned, hwnd)
    raw = [
        ("Editor", 1, True, False, 11),
        ("hidden", 2, False, False, 12),
        ("dialog", 3, True, True, 13),  # owned: a dialog of another window
        ("", 4, True, False, 14),
        ("x" * 300, 5, True, False, 15),
    ]
    monkeypatch.setattr(tools, "_all_windows", lambda: raw)
    monkeypatch.setattr(tools, "_app", lambda pid: f"app{pid}.exe")
    result = tools.list_windows({})
    assert result == {
        "windows": [
            {"title": "Editor", "pid": 1, "app": "app1.exe"},
            {"title": "x" * 200, "pid": 5, "app": "app5.exe"},
        ],
        "truncated": False,
    }


def test_list_windows_cap(monkeypatch):
    raw = [(f"w{i}", i, True, False, 100 + i) for i in range(tools.MAX_WINDOWS + 1)]
    monkeypatch.setattr(tools, "_all_windows", lambda: raw)
    monkeypatch.setattr(tools, "_app", lambda pid: None)
    result = tools.list_windows({})
    assert (len(result["windows"]), result["truncated"]) == (50, True)
    monkeypatch.setattr(tools, "_all_windows", lambda: raw[:-1])
    assert tools.list_windows({})["truncated"] is False
    assert_plain(result)


# --- system_stats -----------------------------------------------------------------


def test_system_stats_on_this_machine():
    result = tools.system_stats({})
    assert set(result) == {"cpu_percent", "ram_used_gb", "ram_total_gb", "ram_percent", "gpu"}
    assert 0 <= result["cpu_percent"] <= 100
    assert 0 < result["ram_used_gb"] <= result["ram_total_gb"]
    assert 0 < result["ram_percent"] <= 100
    gpu = result["gpu"]
    assert gpu is None or set(gpu) == {"name", "percent", "vram_used_gb", "vram_total_gb"}
    assert_plain(result)


def test_ram_numbers_from_fixed_memory_status(monkeypatch):
    def status(pointer):
        pointer._obj.ullTotalPhys, pointer._obj.ullAvailPhys = 16 * 1024**3, 4 * 1024**3
        return 1

    monkeypatch.setattr(tools._kernel32, "GlobalMemoryStatusEx", status)
    monkeypatch.setattr(tools, "_cpu_percent", lambda: 0.0)
    monkeypatch.setattr(tools, "_gpu", lambda: None)
    result = tools.system_stats({})
    assert (result["ram_used_gb"], result["ram_total_gb"], result["ram_percent"]) == (12.0, 16.0, 75.0)


def test_cpu_percent_is_busy_share_between_two_samples(monkeypatch):
    samples = iter([(1000, 4000), (1050, 4200)])  # (idle, kernel + user): 50 idle of 200
    slept = []
    monkeypatch.setattr(tools, "_cpu_times", lambda: next(samples))
    monkeypatch.setattr(tools.time, "sleep", slept.append)
    assert tools._cpu_percent() == 75.0
    assert slept == [0.2]


def test_gpu_line_parsed():
    line = "NVIDIA GeForce RTX 3050 6GB Laptop GPU, 7, 512, 6144\n"
    assert tools._parse_gpu(line) == {
        "name": "NVIDIA GeForce RTX 3050 6GB Laptop GPU",
        "percent": 7.0,
        "vram_used_gb": 0.5,
        "vram_total_gb": 6.0,
    }
    for junk in ["", "\n", "GPU, [N/A], 1, 2", "only, three, fields", "x, 1, 2, 3, 4"]:
        assert tools._parse_gpu(junk) is None


def test_gpu_is_none_when_nvidia_smi_fails(monkeypatch, folders):
    root, outside = folders
    monkeypatch.setattr(tools, "NVIDIA_SMI", root / "missing.exe")
    assert tools._gpu() is None
    for error in [
        tools.subprocess.TimeoutExpired("nvidia-smi", 2),
        tools.subprocess.CalledProcessError(9, "nvidia-smi"),
    ]:
        def fail(*args, error=error, **kwargs):
            raise error
        monkeypatch.setattr(tools.subprocess, "run", fail)
        assert tools._gpu() is None
    # The rest still answers.
    result = tools.system_stats({})
    assert result["gpu"] is None and result["ram_total_gb"] > 0


def test_nvidia_smi_is_run_fixed_without_a_shell(monkeypatch):
    seen = {}

    def run(command, **kwargs):
        seen.update(command=command, **kwargs)
        return tools.subprocess.CompletedProcess(command, 0, stdout="G, 1, 1024, 2048\n")

    monkeypatch.setattr(tools.subprocess, "run", run)
    assert tools._gpu()["vram_total_gb"] == 2.0
    assert seen["command"][0] == str(tools.NVIDIA_SMI)
    assert not seen.get("shell") and seen["timeout"] <= 2 and seen["check"]


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
    # Control: on a clean task create_folder passes the policy and runs.
    assert call(client, clean, "create_folder", path=str(root / "a")).status_code == 200
    task = fresh_task(client)
    assert call(client, task, "list_dir", path=str(root)).status_code == 200
    queued = call(client, task, "create_folder", path=str(root / "b"))
    assert queued.status_code == 202 and "pending_id" in queued.json()


def test_bridge_uses_the_real_read_text_file(bridge):
    client, root = bridge
    (root / "a.txt").write_text("hi")
    response = call(client, fresh_task(client), "read_text_file", path=str(root / "a.txt"))
    assert response.json() == {"result": {"text": "hi", "bytes": 2, "truncated": False}}


def test_list_windows_taints_so_a_following_t1_call_waits(bridge):
    client, root = bridge
    task = fresh_task(client)
    response = call(client, task, "list_windows")
    assert response.status_code == 200 and "windows" in response.json()["result"]
    queued = call(client, task, "create_folder", path=str(root / "b"))
    assert queued.status_code == 202 and "pending_id" in queued.json()


def test_system_stats_does_not_taint(bridge):
    """Numbers and a vendor GPU name only: a following T1 call runs (200, not 202)."""
    client, root = bridge
    task = fresh_task(client)
    response = call(client, task, "system_stats")
    assert response.status_code == 200 and "cpu_percent" in response.json()["result"]
    assert call(client, task, "create_folder", path=str(root / "b")).status_code == 200


def test_read_text_file_taints_so_a_following_t1_call_waits(bridge):
    client, root = bridge
    (root / "a.txt").write_text("hi")
    task = fresh_task(client)
    assert call(client, task, "read_text_file", path=str(root / "a.txt")).status_code == 200
    queued = call(client, task, "create_folder", path=str(root / "b"))
    assert queued.status_code == 202 and "pending_id" in queued.json()


# --- create_folder (P3.2 A) -------------------------------------------------------


class BrokenLog:
    """An undo log whose record cannot be written (disk full, ACL, ...)."""

    def created(self, path, tool):
        raise OSError("disk full")

    def moved(self, source, destination, tool):
        raise OSError("disk full")


@pytest.fixture
def undo_log(folders):
    root, outside = folders
    return UndoLog(root.parent / "quarantine")


def create(undo_log, path):
    return tools.mutating(undo_log, {})["create_folder"]({"path": path})


def test_create_folder_creates_and_records(folders, undo_log):
    root, outside = folders
    result = create(undo_log, root / "new")
    assert (root / "new").is_dir()
    [record] = undo_log.list()
    assert result == {"created": True, "undo_id": record.id}
    assert (record.kind, record.tool, record.path) == ("created", "create_folder", str(root / "new"))
    assert_plain(result)


def test_create_folder_never_reuses_an_existing_name(folders, undo_log):
    root, outside = folders
    (root / "old").mkdir()
    (root / "old" / "keep.txt").write_text("keep")
    (root / "file").write_text("keep")
    for path in [root / "old", root / "file"]:
        with pytest.raises(FileExistsError):
            create(undo_log, path)
    assert undo_log.list() == []
    assert (root / "old" / "keep.txt").read_text() == "keep" and (root / "file").read_text() == "keep"


def test_create_folder_needs_its_parent(folders, undo_log):
    root, outside = folders
    with pytest.raises(FileNotFoundError):
        create(undo_log, root / "missing" / "new")
    assert not (root / "missing").exists() and undo_log.list() == []


def test_create_folder_unrecorded_is_left_and_fails(folders):
    """Rule 4: never delete. The folder stays; the call fails; the audit line says why."""
    root, outside = folders
    with pytest.raises(OSError, match="not recorded"):
        create(BrokenLog(), root / "new")
    assert (root / "new").is_dir()


def ui(root):
    return {"x-jarvis-token": load_token(root.parent / "storage", "ui.token")}


def test_create_folder_through_the_bridge_is_undoable(bridge):
    client, root = bridge
    response = call(client, fresh_task(client), "create_folder", path=str(root / "new"))
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["created"] is True and (root / "new").is_dir()
    records = client.get("/undo", headers=ui(root)).json()["records"]
    assert [record["id"] for record in records] == [result["undo_id"]]
    undone = client.post("/undo", json={"record_id": result["undo_id"]}, headers=ui(root))
    assert undone.status_code == 200
    assert not (root / "new").exists()
    quarantine = root.parent / "storage" / "quarantine"
    assert any((folder / "item").is_dir() for folder in quarantine.iterdir())  # moved, not deleted


def test_create_folder_on_a_tainted_task_waits_for_approval(bridge):
    client, root = bridge
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "create_folder", path=str(root / "new"))
    assert queued.status_code == 202 and not (root / "new").exists()
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and (root / "new").is_dir()


def test_create_folder_outside_the_root_is_refused(bridge):
    client, root = bridge
    outside = root.parent / "outside"
    response = call(client, fresh_task(client), "create_folder", path=str(outside / "new"))
    assert response.status_code == 403
    assert not (outside / "new").exists()
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


# --- rename_file (P3.2 B) ---------------------------------------------------------


def rename(undo_log, source, target, **extra):
    return tools.mutating(undo_log, {})["rename_file"]({"path": source, "target": target, **extra})


def test_rename_file_renames_and_records(folders, undo_log):
    root, outside = folders
    (root / "a.txt").write_text("keep")
    # A doctored new_name is ignored: only the policy's `target` is used (rule 1).
    result = rename(undo_log, root / "a.txt", root / "b.txt", new_name="evil.txt")
    assert (root / "b.txt").read_text() == "keep"
    assert not (root / "a.txt").exists() and not (root / "evil.txt").exists()
    [record] = undo_log.list()
    assert result == {"renamed": True, "undo_id": record.id}
    assert (record.kind, record.tool, record.source, record.destination) == (
        "moved", "rename_file", str(root / "a.txt"), str(root / "b.txt"),
    )
    assert_plain(result)


def test_rename_file_never_overwrites(folders, undo_log):
    root, outside = folders
    (root / "a.txt").write_text("a")
    (root / "b.txt").write_text("b")
    with pytest.raises(OSError):
        rename(undo_log, root / "a.txt", root / "b.txt")
    assert (root / "a.txt").read_text() == "a" and (root / "b.txt").read_text() == "b"
    assert undo_log.list() == []


def test_rename_file_refuses_a_folder(folders, undo_log):
    root, outside = folders
    (root / "dir").mkdir()
    with pytest.raises(OSError, match="not a plain file"):
        rename(undo_log, root / "dir", root / "dir2")
    assert (root / "dir").is_dir() and not (root / "dir2").exists() and undo_log.list() == []


def test_rename_file_refuses_a_link(folders, undo_log):
    root, outside = folders
    (outside / "secret.txt").write_text("secret")
    try:
        os.symlink(outside / "secret.txt", root / "link.txt")
    except OSError:
        pytest.skip("this account may not create symlinks")
    with pytest.raises(OSError, match="not a plain file"):
        rename(undo_log, root / "link.txt", root / "moved.txt")
    assert os.path.lexists(root / "link.txt") and not os.path.lexists(root / "moved.txt")
    assert undo_log.list() == []


def test_rename_file_unrecorded_is_moved_back(folders):
    """Rule 4: a move that cannot be recorded is renamed back and the call fails."""
    root, outside = folders
    (root / "a.txt").write_text("keep")
    with pytest.raises(OSError, match="not recorded"):
        rename(BrokenLog(), root / "a.txt", root / "b.txt")
    assert (root / "a.txt").read_text() == "keep" and not (root / "b.txt").exists()


def test_rename_file_through_the_bridge_is_undoable(bridge):
    client, root = bridge
    (root / "a.txt").write_text("keep")
    response = call(client, fresh_task(client), "rename_file", path=str(root / "a.txt"), new_name="b.txt")
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["renamed"] is True and (root / "b.txt").read_text() == "keep"
    undone = client.post("/undo", json={"record_id": result["undo_id"]}, headers=ui(root))
    assert undone.status_code == 200
    assert (root / "a.txt").read_text() == "keep" and not (root / "b.txt").exists()


def test_rename_file_on_a_tainted_task_waits_for_approval(bridge):
    client, root = bridge
    (root / "a.txt").write_text("keep")
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "rename_file", path=str(root / "a.txt"), new_name="b.txt")
    assert queued.status_code == 202 and (root / "a.txt").exists()
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and (root / "b.txt").read_text() == "keep"


def test_rename_file_new_name_cannot_leave_the_folder(bridge):
    client, root = bridge
    (root / "a.txt").write_text("keep")
    for new_name in ["..\b.txt", "sub/b.txt", "C:b.txt"]:
        response = call(client, fresh_task(client), "rename_file", path=str(root / "a.txt"), new_name=new_name)
        assert response.status_code == 403, new_name
    assert (root / "a.txt").read_text() == "keep"
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


def test_rename_file_trusts_lstat_not_the_name(folders, undo_log, monkeypatch):
    """Where symlinks cannot be made (skip above), pin that a link as `lstat` reports it
    is refused: the check reads the item itself, never follows it."""
    root, outside = folders
    (root / "a.txt").write_text("keep")
    real = os.lstat(root / "a.txt")
    as_link = os.stat_result((stat.S_IFLNK | 0o777, *tuple(real)[1:]))
    # Undone on leaving the block, even on failure: the temp folder's cleanup needs the real lstat.
    with monkeypatch.context() as patch, pytest.raises(OSError, match="not a plain file"):
        patch.setattr(tools.os, "lstat", lambda path: as_link)
        rename(undo_log, root / "a.txt", root / "b.txt")
    assert (root / "a.txt").exists() and undo_log.list() == []


# --- move_file (P3.2 C) -----------------------------------------------------------


def move(undo_log, source, target, **extra):
    return tools.mutating(undo_log, {})["move_file"]({"source": source, "target": target, **extra})


def test_move_file_moves_into_a_subfolder_and_back_to_the_root(folders, undo_log):
    root, outside = folders
    (root / "sub").mkdir()
    (root / "a.txt").write_text("keep")
    # A doctored destination is ignored: only the policy's `target` is used (rule 1).
    result = move(undo_log, root / "a.txt", root / "sub" / "a.txt", destination=str(outside))
    assert (root / "sub" / "a.txt").read_text() == "keep" and not (outside / "a.txt").exists()
    record = undo_log.get(result["undo_id"])
    assert result == {"moved": True, "undo_id": record.id}
    assert (record.kind, record.tool, record.source, record.destination) == (
        "moved", "move_file", str(root / "a.txt"), str(root / "sub" / "a.txt"),
    )
    assert_plain(result)
    move(undo_log, root / "sub" / "a.txt", root / "a.txt")
    assert (root / "a.txt").read_text() == "keep" and len(undo_log.list()) == 2


def test_move_file_name_clash_refused(folders, undo_log):
    root, outside = folders
    (root / "sub").mkdir()
    (root / "a.txt").write_text("new")
    (root / "sub" / "a.txt").write_text("old")
    with pytest.raises(OSError):
        move(undo_log, root / "a.txt", root / "sub" / "a.txt")
    assert (root / "a.txt").read_text() == "new" and (root / "sub" / "a.txt").read_text() == "old"
    assert undo_log.list() == []


def test_move_file_refuses_a_folder(folders, undo_log):
    root, outside = folders
    (root / "dir").mkdir()
    (root / "sub").mkdir()
    with pytest.raises(OSError, match="not a plain file"):
        move(undo_log, root / "dir", root / "sub" / "dir")
    assert (root / "dir").is_dir() and not (root / "sub" / "dir").exists() and undo_log.list() == []


def test_move_file_unrecorded_is_moved_back(folders):
    root, outside = folders
    (root / "sub").mkdir()
    (root / "a.txt").write_text("keep")
    with pytest.raises(OSError, match="not recorded"):
        move(BrokenLog(), root / "a.txt", root / "sub" / "a.txt")
    assert (root / "a.txt").read_text() == "keep" and not (root / "sub" / "a.txt").exists()


def test_move_file_through_the_bridge_is_undoable(bridge):
    client, root = bridge
    (root / "sub").mkdir()
    (root / "a.txt").write_text("keep")
    response = call(client, fresh_task(client), "move_file", source=str(root / "a.txt"), destination=str(root / "sub"))
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["moved"] is True and (root / "sub" / "a.txt").read_text() == "keep"
    undone = client.post("/undo", json={"record_id": result["undo_id"]}, headers=ui(root))
    assert undone.status_code == 200
    assert (root / "a.txt").read_text() == "keep" and not (root / "sub" / "a.txt").exists()


def test_move_file_on_a_tainted_task_waits_for_approval(bridge):
    client, root = bridge
    (root / "sub").mkdir()
    (root / "a.txt").write_text("keep")
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "move_file", source=str(root / "a.txt"), destination=str(root / "sub"))
    assert queued.status_code == 202 and (root / "a.txt").exists()
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and (root / "sub" / "a.txt").read_text() == "keep"


def test_move_file_cannot_leave_the_root(bridge):
    client, root = bridge
    outside = root.parent / "outside"
    (root / "a.txt").write_text("keep")
    response = call(client, fresh_task(client), "move_file", source=str(root / "a.txt"), destination=str(outside))
    assert response.status_code == 403
    assert (root / "a.txt").read_text() == "keep" and not (outside / "a.txt").exists()
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


# --- move_files (P3.2 F2) ---------------------------------------------------------


def move_many(undo_log, sources, destination, targets=None):
    """The handler as the bridge calls it: resolved `sources`, `destination`, `target`."""
    targets = targets or tuple(Path(destination) / Path(s).name for s in sources)
    args = {"sources": tuple(sources), "destination": destination, "target": tuple(targets)}
    return tools.mutating(undo_log, {})["move_files"](args)


def three_files(root):
    """a.txt and b.txt in in1, c.txt in in2; an empty folder `dest`."""
    for folder in ["in1", "in2", "dest"]:
        (root / folder).mkdir()
    files = [root / "in1" / "a.txt", root / "in1" / "b.txt", root / "in2" / "c.txt"]
    for file in files:
        file.write_text(file.name)
    return files, root / "dest"


def untouched(files, dest, undo_log):
    return all(f.read_text() == f.name for f in files) and list(dest.iterdir()) == [] and undo_log.list() == []


def test_move_files_moves_all_and_records_each(folders, undo_log):
    root, outside = folders
    files, dest = three_files(root)
    targets = [dest / f.name for f in files]
    # A doctored destination is not where files go: only the policy's `target` is used.
    result = move_many(undo_log, files, outside, targets)
    assert all((dest / f.name).read_text() == f.name for f in files)
    assert not any(f.exists() for f in files) and list(outside.iterdir()) == []
    records = [undo_log.get(i) for i in result["undo_ids"]]
    assert result == {"moved": 3, "requested": 3, "complete": True, "undo_ids": [r.id for r in records]}
    assert [(r.kind, r.tool, r.source, r.destination) for r in records] == [
        ("moved", "move_files", str(f), str(dest / f.name)) for f in files
    ]
    assert_plain(result)


def test_move_files_preflight_moves_nothing(folders, undo_log):
    """Every check runs before the first move: a failure leaves everything in place."""
    root, outside = folders
    files, dest = three_files(root)
    (root / "afile").write_text("x")
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    for destination in [root / "missing", root / "afile", root / "jump"]:  # no real folder
        targets = [destination / f.name for f in files]
        with pytest.raises(OSError):
            move_many(undo_log, files, destination, targets)
        assert untouched(files, dest, undo_log), destination
    assert list(outside.iterdir()) == []
    (root / "in1" / "sub").mkdir()  # a folder among the sources (last, so order matters not)
    with pytest.raises(OSError, match="not a plain file"):
        move_many(undo_log, [*files, root / "in1" / "sub"], dest)
    assert untouched(files, dest, undo_log)
    (dest / "c.txt").write_text("taken")  # a taken landing name (last member)
    with pytest.raises(FileExistsError):
        move_many(undo_log, files, dest)
    assert all(f.read_text() == f.name for f in files) and [p.name for p in dest.iterdir()] == ["c.txt"]
    assert (dest / "c.txt").read_text() == "taken" and undo_log.list() == []


class FailsOnSecond:
    """A real undo log whose second record cannot be written."""

    def __init__(self, log):
        self.log, self.count = log, 0

    def moved(self, source, destination, tool):
        self.count += 1
        if self.count == 2:
            raise OSError("disk full")
        return self.log.moved(source, destination, tool)


def test_move_files_failure_part_way_stops_and_reports(folders, undo_log):
    root, outside = folders
    files, dest = three_files(root)
    result = move_many(FailsOnSecond(undo_log), files, dest)
    [record] = undo_log.list()
    assert result == {"moved": 1, "requested": 3, "complete": False, "undo_ids": [record.id], "failed": "OSError"}
    assert (dest / "a.txt").read_text() == "a.txt" and record.source == str(files[0])  # stays moved
    assert files[1].read_text() == "b.txt" and files[2].read_text() == "c.txt"  # back / untouched
    assert sorted(p.name for p in dest.iterdir()) == ["a.txt"]
    assert_plain(result)


def test_move_files_failure_on_the_first_file_raises(folders):
    root, outside = folders
    files, dest = three_files(root)
    with pytest.raises(OSError, match="not recorded"):
        move_many(BrokenLog(), files, dest)
    assert all(f.read_text() == f.name for f in files) and list(dest.iterdir()) == []


def test_move_files_through_the_bridge_is_undoable_file_by_file(bridge):
    client, root = bridge
    files, dest = three_files(root)
    response = call(client, fresh_task(client), "move_files", sources=[str(f) for f in files], destination=str(dest))
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert (result["moved"], result["complete"]) == (3, True)
    assert all((dest / f.name).exists() for f in files)
    for undo_id, file in zip(reversed(result["undo_ids"]), reversed(files)):
        assert client.post("/undo", json={"record_id": undo_id}, headers=ui(root)).status_code == 200
        assert file.read_text() == file.name and not (dest / file.name).exists()


def test_move_files_tainted_batch_waits_for_one_approval(bridge):
    client, root = bridge
    files, dest = three_files(root)
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "move_files", sources=[str(f) for f in files], destination=str(dest))
    assert queued.status_code == 202 and list(dest.iterdir()) == []
    [pending] = client.get("/pending", headers=ui(root)).json()["pending"]
    real = lambda path: os.path.realpath(path)  # noqa: E731
    assert pending["paths"] == {
        "destination": real(dest),
        "sources": [real(f) for f in files],
        "target": [real(dest / f.name) for f in files],
    }
    assert all(f.exists() for f in files)
    approved = client.post("/approve", json={"pending_id": pending["id"]}, headers=ui(root))
    assert approved.status_code == 200 and approved.json()["result"]["moved"] == 3
    assert sorted(p.name for p in dest.iterdir()) == ["a.txt", "b.txt", "c.txt"]


def test_move_files_one_bad_source_refuses_the_batch(bridge):
    client, root = bridge
    files, dest = three_files(root)
    outside = root.parent / "outside"
    (outside / "x.txt").write_text("x")
    for task in [fresh_task(client), client.post("/task").json()["task_id"]]:  # clean and tainted
        sources = [str(files[0]), str(outside / "x.txt"), str(files[1])]
        response = call(client, task, "move_files", sources=sources, destination=str(dest))
        assert response.status_code == 403 and response.json()["detail"].startswith("sources: ")
    assert all(f.read_text() == f.name for f in files) and list(dest.iterdir()) == []
    assert (outside / "x.txt").read_text() == "x"
    assert client.get("/pending", headers=ui(root)).json()["pending"] == []
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


@pytest.mark.parametrize("change", ["source renamed away", "landing replaced by a junction"])
def test_move_files_change_while_pending_moves_nothing(bridge, change):
    client, root = bridge
    files, dest = three_files(root)
    outside = root.parent / "outside"
    task = client.post("/task").json()["task_id"]
    queued = call(client, task, "move_files", sources=[str(f) for f in files], destination=str(dest))
    assert queued.status_code == 202
    if change == "source renamed away":
        files[2].rename(root / "in2" / "gone.txt")
    else:
        _winapi.CreateJunction(str(outside), str(dest / "b.txt"))
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code in (403, 500), approved.text  # policy refusal / preflight failure
    assert files[0].read_text() == "a.txt" and files[1].read_text() == "b.txt"
    assert not (dest / "a.txt").exists() and list(outside.iterdir()) == []
    assert client.get("/undo", headers=ui(root)).json()["records"] == []
    if change != "source renamed away":  # recheck: the landing now resolves outside the root
        assert approved.status_code == 403 and approved.json()["detail"].startswith("destination: ")


# --- open_app (P3.2 D) ------------------------------------------------------------

APPS_TOML = REPO / "config" / "apps.toml"
NOTEPAD = r"C:\Windows\System32\notepad.exe"


class FakePopen:
    """Stands in for subprocess.Popen: no real app is ever launched by a test."""

    calls = []

    def __init__(self, *args, **kwargs):
        FakePopen.calls.append((args, kwargs))
        self.pid = 4321


@pytest.fixture
def fake_popen(monkeypatch):
    """Only bridge.tools sees the fake: the rest of the bridge (icacls, ...) keeps the real one."""
    FakePopen.calls = []
    fake = types.SimpleNamespace(Popen=FakePopen, DEVNULL=subprocess.DEVNULL, run=subprocess.run)
    monkeypatch.setattr(tools, "subprocess", fake)
    return FakePopen.calls


def test_open_app_runs_the_fixed_command_only(fake_popen):
    handler = tools.mutating(None, {"notepad": tools.App([NOTEPAD], None)})["open_app"]
    # Whatever else arrives with the call never reaches the command line.
    result = handler({"app": "notepad", "args": ["--evil"], "path": r"C:\x", "app2": "calc"})
    assert result == {"opened": "notepad", "pid": 4321}
    assert_plain(result)
    [(args, kwargs)] = fake_popen
    assert args == ([NOTEPAD],)
    assert kwargs == {
        "shell": False, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }


def test_open_app_unknown_name_fails_without_launching(fake_popen):
    with pytest.raises(KeyError):
        tools.mutating(None, {"notepad": tools.App([NOTEPAD], None)})["open_app"]({"app": "calculator"})
    assert fake_popen == []


def test_real_apps_toml_loads_and_matches_the_allowlist():
    apps = tools.load_apps(APPS_TOML)
    assert set(apps) == set(load_names(APPS_TOML)) == {"notepad", "calculator", "explorer", "vscode"}
    assert {name: app.accepts for name, app in apps.items()} == {
        "vscode": "any", "explorer": "folder", "notepad": "file", "calculator": None,
    }
    for name, app in apps.items():
        assert Path(app.command[0]).is_absolute() and Path(app.command[0]).is_file(), name


def test_every_app_is_offered_to_the_model_and_reachable_by_voice():
    names = set(tools.load_apps(APPS_TOML))
    assert names <= set(APPS)
    assert names <= set(APP_ALIASES.values())


def test_missing_apps_toml_allows_nothing(folders):
    root, outside = folders
    assert tools.load_apps(root / "apps.toml") == {}


@pytest.mark.parametrize("entry", [
    "",  # no command
    "command = []",
    "command = 'C:\\Windows\\System32\\notepad.exe'",  # a string, not a list
    "command = [1]",
    "command = ['notepad.exe']",  # relative: found on PATH, could be anything
    "command = ['\\Windows\\System32\\notepad.exe']",  # no drive
    "command = ['C:\\Windows\\System32\\no-such-app.exe']",
    "command = ['C:\\Windows\\System32']",  # a folder
    "command = ['\\\\server\\share\\app.exe']",  # UNC: would run code off the network
    pytest.param(
        "command = ['C:\\Windows\\System32\\notepad.exe']\naccepts = 'url'", id="accepts_url"),
    pytest.param(
        "command = ['C:\\Windows\\System32\\notepad.exe']\naccepts = 1", id="accepts_int"),
    pytest.param(
        "command = ['C:\\Windows\\System32\\notepad.exe']\naccepts = true", id="accepts_true"),
    pytest.param(
        "command = ['C:\\Windows\\System32\\notepad.exe']\nnote = 'x'", id="unknown_key"),
])
def test_bad_apps_toml_entry_stops_startup(folders, monkeypatch, entry):
    root, outside = folders
    config = root.parent / "config"
    config.mkdir()
    (config / "apps.toml").write_text(f"[notepad]\n{entry}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        tools.load_apps(config / "apps.toml")
    storage = root.parent / "storage"
    storage.mkdir()
    monkeypatch.setattr(bridge_app, "CONFIG", config)
    with pytest.raises(ValueError):
        create_app(storage, roots=[root], protected=[], hotkey=None)


def test_open_app_through_the_bridge_uses_apps_toml(bridge, fake_popen):
    client, root = bridge
    response = call(client, fresh_task(client), "open_app", app="notepad")
    assert response.status_code == 200
    assert response.json() == {"result": {"opened": "notepad", "pid": 4321}}
    assert fake_popen[0][0] == ([NOTEPAD],)
    assert client.get("/undo", headers=ui(root)).json()["records"] == []  # audit line only


def test_open_app_refuses_names_not_in_apps_toml(bridge, fake_popen):
    client, root = bridge
    for app in ["browser", "cmd", "powershell", "NOTEPAD", "notepad.exe", NOTEPAD]:
        response = call(client, fresh_task(client), "open_app", app=app)
        assert response.status_code == 403, app
    assert fake_popen == []


def test_open_app_on_a_tainted_task_waits_for_approval(bridge, fake_popen):
    client, root = bridge
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "open_app", app="notepad")
    assert queued.status_code == 202 and fake_popen == []
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and len(fake_popen) == 1


# --- open_in_app (P3.4 B) ---------------------------------------------------------

CODE = r"C:\Users\karth\AppData\Local\Programs\Microsoft VS Code\Code.exe"
EXPLORER = r"C:\Windows\explorer.exe"
CALC = r"C:\Windows\System32\calc.exe"


def _listed_apps():
    return {
        "vscode": tools.App([CODE], "any"),
        "notepad": tools.App([NOTEPAD], "file"),
        "explorer": tools.App([EXPLORER], "folder"),
        "calculator": tools.App([CALC], None),
    }


def test_open_in_app_vscode_opens_a_folder(folders, fake_popen):
    root, outside = folders
    folder = root / "proj"
    folder.mkdir()
    result = tools.mutating(None, _listed_apps())["open_in_app"](
        {"app": "vscode", "path": folder, "args": ["--evil"]})
    assert result == {"opened": "vscode", "pid": 4321}
    assert_plain(result)
    [(args, kwargs)] = fake_popen
    assert args == ([CODE, str(folder)],)
    assert kwargs == {
        "shell": False, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }


def test_open_in_app_notepad_opens_a_file_not_a_folder(folders, fake_popen):
    root, outside = folders
    file = root / "a.txt"
    file.write_text("hi")
    (root / "dir").mkdir()
    opened = tools.mutating(None, _listed_apps())["open_in_app"]({"app": "notepad", "path": file})
    assert opened == {"opened": "notepad", "pid": 4321}
    assert fake_popen[0][0] == ([NOTEPAD, str(file)],)
    fake_popen.clear()
    with pytest.raises(OSError, match="notepad opens a file, not a folder"):
        tools.mutating(None, _listed_apps())["open_in_app"]({"app": "notepad", "path": root / "dir"})
    assert fake_popen == []


def test_open_in_app_explorer_opens_a_folder_not_a_file(folders, fake_popen):
    root, outside = folders
    file = root / "a.txt"
    file.write_text("hi")
    folder = root / "dir"
    folder.mkdir()
    opened = tools.mutating(None, _listed_apps())["open_in_app"]({"app": "explorer", "path": folder})
    assert opened == {"opened": "explorer", "pid": 4321}
    assert fake_popen[0][0] == ([EXPLORER, str(folder)],)
    fake_popen.clear()
    with pytest.raises(OSError, match="explorer opens a folder, not a file"):
        tools.mutating(None, _listed_apps())["open_in_app"]({"app": "explorer", "path": file})
    assert fake_popen == []


def test_open_in_app_calculator_does_not_open_a_path(folders, fake_popen):
    root, outside = folders
    file = root / "a.txt"
    file.write_text("hi")
    (root / "dir").mkdir()
    for path in (file, root / "dir", root):
        with pytest.raises(OSError, match="calculator does not open a path"):
            tools.mutating(None, _listed_apps())["open_in_app"]({"app": "calculator", "path": path})
    assert fake_popen == []


def test_open_in_app_refuses_a_junction_and_a_symlink(folders, fake_popen):
    root, outside = folders
    (outside / "secret.txt").write_bytes(b"secret")
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    with pytest.raises(OSError, match="not a plain file or folder"):
        tools.mutating(None, _listed_apps())["open_in_app"]({"app": "vscode", "path": root / "jump"})
    assert fake_popen == []
    assert (outside / "secret.txt").read_bytes() == b"secret"
    try:
        os.symlink(outside / "secret.txt", root / "link.txt")
    except OSError:
        pytest.skip("this account cannot create symlinks")
    with pytest.raises(OSError, match="not a plain file or folder"):
        tools.mutating(None, _listed_apps())["open_in_app"]({"app": "vscode", "path": root / "link.txt"})
    assert fake_popen == []
    assert (outside / "secret.txt").read_bytes() == b"secret"


def test_open_in_app_trusts_lstat_not_the_name(folders, fake_popen, monkeypatch):
    """A link as lstat reports it is refused, even when st_reparse_tag is 0.
    This is what kills `stat` instead of `lstat`."""
    root, outside = folders
    file = root / "a.txt"
    file.write_text("keep")
    real = os.lstat(file)
    as_link = os.stat_result(
        (stat.S_IFLNK | 0o777, *tuple(real)[1:]), {"st_reparse_tag": 0})
    assert as_link.st_reparse_tag == 0 and stat.S_ISLNK(as_link.st_mode)
    with monkeypatch.context() as patch, pytest.raises(OSError, match="not a plain file or folder"):
        patch.setattr(tools.os, "lstat", lambda path: as_link)
        tools.mutating(None, _listed_apps())["open_in_app"]({"app": "notepad", "path": file})
    assert fake_popen == [] and file.read_text() == "keep"


def test_open_in_app_through_the_bridge_may_open_the_root(bridge, fake_popen):
    client, root = bridge
    response = call(client, fresh_task(client), "open_in_app", app="vscode", path=str(root))
    assert response.status_code == 200
    assert response.json()["result"] == {"opened": "vscode", "pid": 4321}
    assert fake_popen[0][0] == ([CODE, str(root)],)
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


def test_open_in_app_refused_before_any_launch(bridge, fake_popen, folders):
    client, root = bridge
    outside = root.parent / "outside"
    for app in ["browser", "cmd", "VSCODE"]:
        response = call(client, fresh_task(client), "open_in_app", app=app, path=str(root))
        assert response.status_code == 403 and response.json()["detail"] == "app: not on the allowlist", app
    outside_path = call(client, fresh_task(client), "open_in_app", app="vscode", path=str(outside / "x.txt"))
    assert outside_path.status_code == 403
    assert outside_path.json()["detail"] == "path: outside the allowed roots"
    on_root = call(client, fresh_task(client), "create_folder", path=str(root))
    assert on_root.status_code == 403 and on_root.json()["detail"] == "path: the root itself"
    assert fake_popen == []
    locked = root / "locked"
    locked.mkdir()
    secret = locked / "secret.txt"
    secret.write_text("secret")
    storage = root.parent / "storage-locked"
    storage.mkdir()
    ran = []
    app = create_app(
        storage, roots=[root], protected=[locked], hotkey=None,
        handlers={"open_in_app": lambda args: ran.append(args)},
    )
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as guarded:
        on_secret = call(guarded, fresh_task(guarded), "open_in_app", app="vscode", path=str(secret))
    assert on_secret.status_code == 403 and on_secret.json()["detail"] == "path: protected folder"
    assert ran == [] and secret.read_text() == "secret"


def test_open_in_app_on_a_tainted_task_waits_for_approval(bridge, fake_popen):
    client, root = bridge
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "open_in_app", app="vscode", path=str(root))
    assert queued.status_code == 202 and fake_popen == []
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and len(fake_popen) == 1


# --- focus_window (P3.2 E) --------------------------------------------------------

# (title, pid, visible, owned, hwnd), in EnumWindows order: topmost first.
WINDOWS = [
    ("", 1, True, False, 101),  # untitled: never a candidate
    ("Secret notepad dialog", 2, True, True, 102),  # owned (a dialog): never a candidate
    ("Hidden notepad", 3, False, False, 103),  # invisible: never a candidate
    ("Untitled - Notepad", 4, True, False, 104),
    ("main.py - Jarvis_v2", 5, True, False, 105),
    ("notes.txt - Notepad", 6, True, False, 106),
]
APPS_BY_PID = {4: "Notepad.exe", 5: "Code.exe", 6: "Notepad.exe"}


class FakeUser32:
    """No real window. `SetForegroundWindow` changes `foreground` unless `refuses`.
    `settles_after` then hides that result for N reads (0) before revealing it.
    `lands_on_restore`: every `ShowWindow(SW_RESTORE)` sets the foreground the same way."""

    def __init__(self, minimised=(), refuses=False):
        self.minimised, self.refuses, self.calls = set(minimised), refuses, []
        self.foreground = 0
        self.lands_on_restore = False
        self.settles_after = 0
        self._hidden = 0

    def IsIconic(self, hwnd):
        return hwnd in self.minimised

    def ShowWindow(self, hwnd, command):
        self.calls.append(("show", hwnd, command))
        if self.lands_on_restore and command == tools.SW_RESTORE:
            self.foreground = hwnd
            self._hidden = self.settles_after
        return True

    def GetForegroundWindow(self):
        if self._hidden:
            self._hidden -= 1
            return 0
        return self.foreground

    def SetForegroundWindow(self, hwnd):
        self.calls.append(("foreground", hwnd))
        if not self.refuses:
            self.foreground = hwnd
        self._hidden = self.settles_after
        return not self.refuses


class FakeClock:
    """`monotonic` is a counter. `sleep` advances it and counts the call. Past two 500 ms
    waits plus one step, it raises so a wait with no deadline cannot hang the run."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        if sum(self.sleeps) > 2 * 0.5 + 0.01:
            raise RuntimeError("focus wait slept past 2 x 500 ms plus one step")


@pytest.fixture
def desktop(monkeypatch):
    """Fake windows and a fake user32: no real window is ever touched by these tests."""
    user32 = FakeUser32()
    monkeypatch.setattr(tools, "_all_windows", lambda: WINDOWS)
    monkeypatch.setattr(tools, "_app", APPS_BY_PID.get)
    monkeypatch.setattr(tools, "_user32", user32)
    monkeypatch.setattr(tools, "time", FakeClock())
    return user32


def focus(title):
    return tools.mutating(None, {})["focus_window"]({"title": title})


def test_focus_window_title_contains_case_insensitive_topmost_wins(desktop):
    result = focus("NOTEPAD")
    assert result == {"focused": True}  # no title: the tool does not taint (rule 5)
    assert_plain(result)
    assert desktop.calls == [("foreground", 104)]  # topmost match, not 106 or a skipped one


def test_focus_window_matches_the_app_name_without_exe(desktop):
    focus("code")
    assert desktop.calls == [("foreground", 105)]


@pytest.mark.parametrize("title", ["code.exe", "cod", "secret", "hidden", "nothing like it"])
def test_focus_window_no_match_fails_and_touches_nothing(desktop, title):
    with pytest.raises(LookupError):
        focus(title)
    assert desktop.calls == []


def test_focus_window_restores_a_minimised_window(desktop):
    desktop.minimised = {105}
    focus("jarvis_v2")
    assert desktop.calls == [("show", 105, tools.SW_RESTORE), ("foreground", 105)]
    assert tools.SW_RESTORE == 9


def test_focus_window_refused_by_windows_fails(desktop):
    desktop.refuses = True
    with pytest.raises(OSError, match="refused"):
        focus("notepad")


def test_focus_window_plain_call_settles_after_two_reads(desktop):
    desktop.settles_after = 2
    assert focus("notepad") == {"focused": True}
    assert desktop.calls == [("foreground", 104)]
    assert tools.time.sleeps == [0.01, 0.01]


def test_focus_window_settles_too_late(desktop):
    """100 reads exceed one 500 ms cap. The restore starts that hide fresh."""
    desktop.refuses = True
    desktop.lands_on_restore = True
    desktop.settles_after = 100
    with pytest.raises(OSError, match="refused"):
        focus("notepad")


def test_focus_window_restore_lands_when_the_plain_call_is_refused(desktop):
    desktop.refuses = True
    desktop.lands_on_restore = True
    assert focus("notepad") == {"focused": True}
    assert desktop.calls == [
        ("foreground", 104),
        ("show", 104, tools.SW_MINIMIZE),
        ("show", 104, tools.SW_RESTORE),
    ]


def test_focus_window_restore_lands_after_forty_reads(desktop):
    desktop.refuses = True
    desktop.lands_on_restore = True
    desktop.settles_after = 40
    assert focus("notepad") == {"focused": True}


def test_focus_window_restore_that_does_not_land_fails(desktop):
    desktop.refuses = True
    with pytest.raises(OSError, match="refused"):
        focus("notepad")
    assert desktop.calls == [
        ("foreground", 104),
        ("show", 104, tools.SW_MINIMIZE),
        ("show", 104, tools.SW_RESTORE),
    ]
    assert sum(tools.time.sleeps) <= 2 * 0.5 + 0.01


def test_focus_window_plain_call_makes_no_show_call(desktop):
    assert focus("notepad") == {"focused": True}
    assert [call for call in desktop.calls if call[0] == "show"] == []


def test_focus_window_minimised_lands_on_the_first_restore(desktop):
    """Test 5 replaced in implementation, approved by Karthik."""
    desktop.minimised = {104}
    desktop.lands_on_restore = True
    assert focus("notepad") == {"focused": True}
    assert desktop.calls == [("show", 104, tools.SW_RESTORE), ("foreground", 104)]


def test_focus_window_source_has_no_attach_route():
    source = (REPO / "bridge" / "tools.py").read_text(encoding="utf-8")
    assert "AttachThreadInput" not in source
    assert "IsHungAppWindow" not in source


def test_all_windows_on_this_desktop_carries_a_handle():
    """Real call; read only."""
    for title, pid, visible, owned, hwnd in tools._all_windows():
        assert isinstance(hwnd, int) and hwnd


def test_focus_window_through_the_bridge(bridge, desktop):
    client, root = bridge
    response = call(client, fresh_task(client), "focus_window", title="notepad")
    assert response.status_code == 200 and response.json() == {"result": {"focused": True}}
    assert desktop.calls == [("foreground", 104)]
    assert client.get("/undo", headers=ui(root)).json()["records"] == []  # audit line only


def test_focus_window_on_a_tainted_task_waits_for_approval(bridge, desktop):
    client, root = bridge
    task = client.post("/task").json()["task_id"]  # the bridge starts tainted (P2.9 R2)
    queued = call(client, task, "focus_window", title="notepad")
    assert queued.status_code == 202 and desktop.calls == []
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200 and desktop.calls == [("foreground", 104)]


def test_focus_window_refuses_odd_titles(bridge, desktop):
    client, root = bridge
    for title in ["", "a\nb", "a\u202eb", "x" * 10_000]:
        assert call(client, fresh_task(client), "focus_window", title=title).status_code == 403
    assert desktop.calls == []


# --- delete_file (P3.3 A) ---------------------------------------------------------


def delete(undo_log, path):
    return tools.mutating(undo_log, {})["delete_file"]({"path": path})


def test_delete_file_quarantines_a_plain_file(folders, undo_log):
    root, outside = folders
    victim = root / "a.txt"
    victim.write_bytes(b"keep")
    result = delete(undo_log, victim)
    assert not victim.exists()
    record = undo_log.get(result["undo_id"])
    assert record.kind == "quarantined"
    assert (root.parent / "quarantine" / record.id / "item").read_bytes() == b"keep"
    assert result == {"deleted": True, "undo_id": record.id}
    assert_plain(result)


def test_delete_file_refuses_a_folder(folders, undo_log):
    root, outside = folders
    (root / "dir").mkdir()
    with pytest.raises(OSError, match="not a plain file"):
        delete(undo_log, root / "dir")
    assert (root / "dir").is_dir() and undo_log.list() == []


def test_delete_file_refuses_a_link(folders, undo_log):
    """A junction is refused by lstat. A real symlink is too, when this account can make one.
    A failed symlink create returns here: the junction half has already run."""
    root, outside = folders
    (outside / "secret.txt").write_bytes(b"secret")
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    with pytest.raises(OSError, match="not a plain file"):
        delete(undo_log, root / "jump")
    assert os.path.lexists(root / "jump")
    assert (outside / "secret.txt").read_bytes() == b"secret" and undo_log.list() == []
    try:
        os.symlink(outside / "secret.txt", root / "link.txt")
    except OSError:
        return
    with pytest.raises(OSError, match="not a plain file"):
        delete(undo_log, root / "link.txt")
    assert os.path.lexists(root / "link.txt")
    assert (outside / "secret.txt").read_bytes() == b"secret" and undo_log.list() == []


def test_delete_file_trusts_lstat_not_the_name(folders, undo_log, monkeypatch):
    """Approved by Karthik 2026-11-15. Copied from the rename_file stand-in: a link as
    `lstat` reports it is refused. This is what kills `stat` instead of `lstat`."""
    root, outside = folders
    (root / "a.txt").write_text("keep")
    real = os.lstat(root / "a.txt")
    as_link = os.stat_result((stat.S_IFLNK | 0o777, *tuple(real)[1:]))
    # Undone on leaving the block, even on failure: the temp folder's cleanup needs the real lstat.
    with monkeypatch.context() as patch, pytest.raises(OSError, match="not a plain file"):
        patch.setattr(tools.os, "lstat", lambda path: as_link)
        delete(undo_log, root / "a.txt")
    assert (root / "a.txt").exists() and undo_log.list() == []


def test_delete_file_through_the_bridge_is_undoable(bridge):
    client, root = bridge
    victim = root / "a.txt"
    victim.write_bytes(b"keep")
    queued = call(client, fresh_task(client), "delete_file", path=str(victim))
    assert queued.status_code == 202
    [pending] = client.get("/pending", headers=ui(root)).json()["pending"]
    assert (pending["reason"], pending["tool"]) == ("T2", "delete_file")
    assert victim.read_bytes() == b"keep"
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 200
    result = approved.json()["result"]
    assert result == {"deleted": True, "undo_id": result["undo_id"]}
    assert not victim.exists()
    undone = client.post("/undo", json={"record_id": result["undo_id"]}, headers=ui(root))
    assert undone.status_code == 200
    assert victim.read_bytes() == b"keep"


def test_delete_file_deny_leaves_the_file(bridge):
    client, root = bridge
    victim = root / "a.txt"
    victim.write_bytes(b"keep")
    queued = call(client, fresh_task(client), "delete_file", path=str(victim))
    assert queued.status_code == 202
    denied = client.post("/deny", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert denied.status_code == 200 and victim.read_bytes() == b"keep"
    outcome = client.post("/outcome", json={"pending_id": queued.json()["pending_id"]})
    assert outcome.json() == {"status": "denied"}


def test_delete_file_change_while_pending_moves_nothing(bridge):
    client, root = bridge
    outside = root.parent / "outside"
    victim = root / "a.txt"
    victim.write_bytes(b"keep")
    (outside / "secret.txt").write_bytes(b"secret")
    queued = call(client, fresh_task(client), "delete_file", path=str(victim))
    assert queued.status_code == 202
    victim.rename(root / "kept.txt")  # the path is now a junction pointing outside the root
    _winapi.CreateJunction(str(outside), str(victim))
    approved = client.post("/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert approved.status_code == 403
    assert (root / "kept.txt").read_bytes() == b"keep"
    assert (outside / "secret.txt").read_bytes() == b"secret" and os.path.lexists(victim)
    assert client.get("/undo", headers=ui(root)).json()["records"] == []


def test_delete_file_refuses_the_root_and_a_protected_folder(folders):
    root, outside = folders
    locked = root / "locked"
    locked.mkdir()
    secret = locked / "secret.txt"
    secret.write_text("secret")
    storage = root.parent / "storage"
    storage.mkdir()
    ran = []
    app = create_app(
        storage, roots=[root], protected=[locked], hotkey=None,
        handlers={"delete_file": lambda args: ran.append(args)},
    )
    headers = {"x-jarvis-token": load_token(storage)}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        on_root = call(client, fresh_task(client), "delete_file", path=str(root))
        on_secret = call(client, fresh_task(client), "delete_file", path=str(secret))
    assert on_root.status_code == 403 and on_root.json()["detail"] == "path: the root itself"
    assert on_secret.status_code == 403 and on_secret.json()["detail"] == "path: protected folder"
    assert ran == [] and secret.read_text() == "secret" and root.is_dir()


# --- scripts.toml (P3.3 B) --------------------------------------------------------


SCRIPTS_TOML = REPO / "config" / "scripts.toml"
_HOST = "C:\\Windows\\System32\\HOSTNAME.EXE"
_SCRIPT = f"command = ['{_HOST}']"


def test_real_scripts_toml_loads_and_matches_the_allowlist():
    scripts = tools.load_scripts(SCRIPTS_TOML)
    assert set(scripts) == set(load_names(SCRIPTS_TOML)) == {"dev_server", "run_tests", "backup_notes"}
    assert set(scripts) <= set(SCRIPTS)
    for name, script in scripts.items():
        assert script.command == [_HOST], name
        assert Path(script.command[0]).is_absolute() and Path(script.command[0]).is_file()
        assert script.cwd == Path(script.command[0]).parent and script.timeout == 30


def test_missing_scripts_toml_allows_nothing(folders):
    root, outside = folders
    assert tools.load_scripts(root / "scripts.toml") == {}


@pytest.mark.parametrize("entry", [
    pytest.param("", id="missing_command"),
    pytest.param("command = ['HOSTNAME.EXE']", id="bare_name"),
    pytest.param("command = ['Windows\\System32\\HOSTNAME.EXE']", id="relative"),
    pytest.param("command = ['\\\\server\\share\\HOSTNAME.EXE']", id="unc"),
    pytest.param("command = ['C:\\Windows\\System32\\no-such-app.exe']", id="missing_file"),
    pytest.param(f"{_SCRIPT}\ncwd = 'Windows'", id="cwd_relative"),
    pytest.param(f"{_SCRIPT}\ncwd = 'C:\\no\\such\\folder'", id="cwd_missing"),
    pytest.param(f"{_SCRIPT}\ncwd = '{_HOST}'", id="cwd_file"),
    pytest.param(f"{_SCRIPT}\ntimeout = 0", id="timeout_0"),
    pytest.param(f"{_SCRIPT}\ntimeout = 61", id="timeout_61"),
    pytest.param(f"{_SCRIPT}\ntimeout = '30'", id="timeout_string"),
    pytest.param(f"{_SCRIPT}\ntimeout = true", id="timeout_true"),
    pytest.param(f"{_SCRIPT}\nnote = 'x'", id="unknown_key"),
])
def test_bad_scripts_toml_entry_stops_startup(folders, monkeypatch, entry):
    root, outside = folders
    config = root.parent / "config"
    config.mkdir()
    (config / "scripts.toml").write_text(f"[run_tests]\n{entry}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        tools.load_scripts(config / "scripts.toml")
    storage = root.parent / "storage"
    storage.mkdir()
    monkeypatch.setattr(bridge_app, "CONFIG", config)
    with pytest.raises(ValueError):
        create_app(storage, roots=[root], protected=[], hotkey=None)


# --- run_named_script (P3.3 C) ----------------------------------------------------


def _one_script(command, cwd, timeout=30):
    return tools.Script(list(command), Path(cwd), timeout)


@pytest.fixture
def fake_run(monkeypatch):
    """Stands in for subprocess.run inside bridge.tools only. The bridge's own icacls calls
    keep the real subprocess. Set `box['result']` to a CompletedProcess or an exception."""
    box = {"calls": [], "result": subprocess.CompletedProcess(["x"], 0, stdout=b"ok\n")}

    def run(*args, **kwargs):
        box["calls"].append((args, kwargs))
        result = box["result"]
        if isinstance(result, Exception):
            raise result
        return result

    fake = types.SimpleNamespace(
        run=run, Popen=subprocess.Popen, DEVNULL=subprocess.DEVNULL,
        PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT, TimeoutExpired=subprocess.TimeoutExpired,
    )
    monkeypatch.setattr(tools, "subprocess", fake)
    return box


def _run_script(script, **extra):
    return tools.mutating(None, {}, {"run_tests": script})["run_named_script"](
        {"name": "run_tests", **extra}
    )


def test_run_named_script_runs_the_fixed_command_only(fake_run):
    script = _one_script([_HOST], Path(_HOST).parent, timeout=12)
    result = _run_script(script, args=["--evil"], path=r"C:\x")
    assert result == {"ran": "run_tests", "timed_out": False, "exit_code": 0, "output": "ok\n"}
    assert_plain(result)
    [(args, kwargs)] = fake_run["calls"]
    assert args == ([_HOST],)
    assert kwargs == {
        "shell": False, "cwd": script.cwd, "timeout": 12,
        "stdin": subprocess.DEVNULL, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
    }


def test_run_named_script_returns_the_output_tail(fake_run):
    text = "START" + ("m" * 10000) + "END"
    fake_run["result"] = subprocess.CompletedProcess([_HOST], 0, stdout=text.encode())
    result = _run_script(_one_script([_HOST], Path(_HOST).parent))
    assert len(result["output"]) == 4096
    assert result["output"].endswith("END") and "START" not in result["output"]


def test_run_named_script_timeout_is_a_result(fake_run):
    fake_run["result"] = subprocess.TimeoutExpired([_HOST], 12, output=b"partial")
    result = _run_script(_one_script([_HOST], Path(_HOST).parent, timeout=12))
    assert result == {"ran": "run_tests", "timed_out": True, "exit_code": None, "output": "partial"}
    assert_plain(result)


def test_run_named_script_nonzero_exit_is_a_result(fake_run):
    fake_run["result"] = subprocess.CompletedProcess([_HOST], 3, stdout=b"nope")
    result = _run_script(_one_script([_HOST], Path(_HOST).parent))
    assert result == {"ran": "run_tests", "timed_out": False, "exit_code": 3, "output": "nope"}


def test_run_named_script_replaces_bytes_that_are_not_utf8(fake_run):
    fake_run["result"] = subprocess.CompletedProcess([_HOST], 0, stdout=b"ok\xff")
    result = _run_script(_one_script([_HOST], Path(_HOST).parent))
    assert result["output"] == "ok\ufffd"


def test_run_named_script_through_the_bridge_taints(bridge):
    client, root = bridge
    task = fresh_task(client)
    queued = call(client, task, "run_named_script", name="run_tests")
    assert queued.status_code == 202
    approved = client.post(
        "/approve", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root)
    )
    assert approved.status_code == 200, approved.text
    result = approved.json()["result"]
    assert result["timed_out"] is False and result["exit_code"] == 0
    assert socket.gethostname().casefold() in result["output"].casefold()
    assert client.get("/undo", headers=ui(root)).json()["records"] == []
    queued_folder = call(client, task, "create_folder", path=str(root / "new"))
    assert queued_folder.status_code == 202
    [pending] = client.get("/pending", headers=ui(root)).json()["pending"]
    assert pending["reason"] == "tainted T1"
    assert not (root / "new").exists()


def test_run_named_script_refuses_names_not_on_the_allowlist(bridge, fake_run):
    client, root = bridge
    for name in ["cmd", "RUN_TESTS", "run_tests.cmd"]:
        response = call(client, fresh_task(client), "run_named_script", name=name)
        assert response.status_code == 403, name
        assert response.json()["detail"] == "name: not on the allowlist"
    assert fake_run["calls"] == []


def test_run_named_script_deny_never_runs(bridge, fake_run):
    client, root = bridge
    queued = call(client, fresh_task(client), "run_named_script", name="run_tests")
    assert queued.status_code == 202
    denied = client.post("/deny", json={"pending_id": queued.json()["pending_id"]}, headers=ui(root))
    assert denied.status_code == 200
    outcome = client.post("/outcome", json={"pending_id": queued.json()["pending_id"]})
    assert outcome.json() == {"status": "denied"}
    assert fake_run["calls"] == []
