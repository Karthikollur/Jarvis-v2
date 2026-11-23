import _winapi
import itertools
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bridge.app import create_app, load_token
from safety.policy import resolve_inside
from safety.undo import UndoLog, UndoRefused, UnknownRecord

BASE = "http://127.0.0.1:8765"
LOOPBACK = ("127.0.0.1", 50000)


@pytest.fixture
def env(dirs):
    """(log, root, quarantine, resolve). Quarantine sits outside the root and is protected,
    as the bridge storage is."""
    root, outside = (Path(os.path.realpath(folder)) for folder in dirs)
    quarantine = outside / "quarantine"
    ticks = itertools.count()
    log = UndoLog(quarantine, wall=lambda: float(next(ticks)))

    def resolve(raw):
        return resolve_inside(raw, [root], [quarantine])

    return log, root, quarantine, resolve


def snapshot(*folders):
    """Every file and folder below `folders`, with file bytes: proves nothing moved."""
    seen = {}
    for folder in folders:
        for dirpath, dirnames, filenames in os.walk(folder):
            for name in dirnames:
                seen[os.path.join(dirpath, name)] = None
            for name in filenames:
                seen[os.path.join(dirpath, name)] = Path(dirpath, name).read_bytes()
    return seen


def refused(log, record_id, resolve, *folders, match=None, kind=UndoRefused):
    before = snapshot(*folders)
    with pytest.raises(kind, match=match):
        log.undo(record_id, resolve)
    assert snapshot(*folders) == before


# --- quarantine and restore ---------------------------------------------------


def test_quarantine_file_and_undo_restores_bytes(env):
    log, root, quarantine, resolve = env
    original = root / "notes.txt"
    original.write_bytes(b"keep \x00 me")
    record = log.quarantine(original, "delete_file")
    assert not original.exists()
    assert (quarantine / record.id / "item").read_bytes() == b"keep \x00 me"
    on_disk = json.loads((quarantine / record.id / "record.json").read_text(encoding="utf-8"))
    assert on_disk["kind"] == "quarantined"
    assert on_disk["path"] == str(original)
    assert on_disk["tool"] == "delete_file"
    assert on_disk["undone"] is None
    done = log.undo(record.id, resolve)
    assert original.read_bytes() == b"keep \x00 me"
    assert done.undone is not None
    assert log.get(record.id).undone == done.undone


def test_quarantine_folder_and_undo(env):
    log, root, quarantine, resolve = env
    folder = root / "project"
    (folder / "sub").mkdir(parents=True)
    (folder / "sub" / "a.txt").write_text("a")
    record = log.quarantine(folder, "delete_file")
    assert not folder.exists()
    assert (quarantine / record.id / "item" / "sub" / "a.txt").read_text() == "a"
    log.undo(record.id, resolve)
    assert (folder / "sub" / "a.txt").read_text() == "a"


def test_same_name_quarantined_twice_does_not_collide(env):
    log, root, quarantine, resolve = env
    first, second = root / "a" / "x.txt", root / "b" / "x.txt"
    for path, text in [(first, "one"), (second, "two")]:
        path.parent.mkdir()
        path.write_text(text)
    one, two = log.quarantine(first, "delete_file"), log.quarantine(second, "delete_file")
    assert one.id != two.id
    log.undo(two.id, resolve)
    log.undo(one.id, resolve)
    assert (first.read_text(), second.read_text()) == ("one", "two")


def test_move_record_undo_moves_back(env):
    log, root, quarantine, resolve = env
    source, destination = root / "a.txt", root / "sorted" / "a.txt"
    destination.parent.mkdir()
    destination.write_text("moved")  # the tool already moved it
    record = log.moved(source, destination, "move_file")
    log.undo(record.id, resolve)
    assert source.read_text() == "moved"
    assert not destination.exists()


def test_create_record_undo_refuses_a_non_empty_folder(env):
    log, root, quarantine, resolve = env
    folder = root / "new"
    folder.mkdir()
    record = log.created(folder, "create_folder")
    (folder / "added later.txt").write_text("later")
    refused(log, record.id, resolve, root, quarantine, match="not empty")
    assert folder.is_dir()
    assert (folder / "added later.txt").read_text() == "later"
    assert log.get(record.id).undone is None
    assert [item for item in log.list() if item.kind == "quarantined"] == []


def test_undo_the_move_then_the_folder(env):
    log, root, quarantine, resolve = env
    folder = root / "new"
    folder.mkdir()
    created = log.created(folder, "create_folder")
    source, destination = root / "a.txt", folder / "a.txt"
    destination.write_text("moved")
    moved = log.moved(source, destination, "move_file")
    log.undo(moved.id, resolve)
    assert source.read_text() == "moved"
    assert not destination.exists()
    done = log.undo(created.id, resolve)
    assert not folder.exists()
    assert log.get(moved.id).undone is not None
    assert done.undone is not None


def test_non_empty_folder_undo_through_the_bridge_is_409(dirs):
    root = Path(os.path.realpath(dirs[0]))
    storage = root.parent / "storage"
    storage.mkdir()
    app = create_app(storage, roots=[root], protected=[])
    headers = {"x-jarvis-token": load_token(storage)}
    ui = {"x-jarvis-token": load_token(storage, "ui.token")}
    with TestClient(app, base_url=BASE, client=LOOPBACK, headers=headers) as client:
        task = client.post("/task", json={"fresh_context": True})
        assert task.status_code == 200
        made = client.post(
            "/tool",
            json={"task_id": task.json()["task_id"], "tool": "create_folder", "args": {"path": str(root / "new")}},
        )
        assert made.status_code == 200
        folder = root / "new"
        (folder / "added later.txt").write_text("later")
        record_id = made.json()["result"]["undo_id"]
        undone = client.post("/undo", json={"record_id": record_id}, headers=ui)
        assert undone.status_code == 409
        assert undone.json()["detail"] == "the folder is not empty: undo what is in it first"
        assert folder.is_dir()
        assert (folder / "added later.txt").read_text() == "later"
        records = client.get("/undo", headers=ui).json()["records"]
        assert [(record["id"], record["kind"], record["undone"]) for record in records] == [
            (record_id, "created", None)
        ]


def test_create_undo_works_when_quarantine_is_protected_inside_root(dirs):
    """Fix (c): quarantine-side paths never go through `resolve`."""
    root = Path(os.path.realpath(dirs[0]))
    quarantine = root / "quarantine"
    log = UndoLog(quarantine)

    def resolve(raw):
        return resolve_inside(raw, [root], [quarantine])

    folder = root / "new"
    folder.mkdir()
    log.undo(log.created(folder, "create_folder").id, resolve)
    assert not folder.exists()
    restore = next(r for r in log.list() if r.kind == "quarantined")
    log.undo(restore.id, resolve)
    assert folder.is_dir()


# --- records ------------------------------------------------------------------


def test_two_logs_share_records_newest_first(env):
    log, root, quarantine, resolve = env
    other = UndoLog(quarantine)
    first = log.created(root, "create_folder")
    second = other.moved(root / "a", root / "b", "move_file")
    assert [r.id for r in other.list()] == [second.id, first.id]
    assert log.get(second.id) == second


def test_no_way_to_delete():
    public = {name for name in dir(UndoLog) if not name.startswith("_")}
    assert public == {"quarantine", "moved", "created", "list", "get", "undo"}


# --- refusals: nothing moves ---------------------------------------------------


def test_original_location_occupied_refused(env):
    log, root, quarantine, resolve = env
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")
    original.write_text("new file in the way")
    refused(log, record.id, resolve, root, quarantine, match="occupied")
    (root / "b").mkdir()
    (root / "b" / "x.txt").write_text("old")
    record = log.quarantine(root / "b" / "x.txt", "delete_file")
    (root / "b" / "x.txt").mkdir()  # a folder in the way: never nested into
    refused(log, record.id, resolve, root, quarantine, match="occupied")


def test_target_appearing_after_check_is_not_overwritten(env, monkeypatch):
    """Fix (b): os.rename refuses an existing target, so a race cannot overwrite."""
    log, root, quarantine, resolve = env
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")
    real_rename = os.rename

    def racing_rename(src, dst):
        Path(dst).write_text("racer")  # appears between the check and the move
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", racing_rename)
    with pytest.raises(UndoRefused):
        log.undo(record.id, resolve)
    monkeypatch.undo()
    assert original.read_text() == "racer"
    assert (quarantine / record.id / "item").read_text() == "old"
    assert log.get(record.id).undone is None


def test_move_across_drives_refused(env, monkeypatch):
    log, root, quarantine, resolve = env
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")

    def cross_drive(src, dst):
        error = OSError(18, "Invalid cross-device link")
        error.winerror = 17  # ERROR_NOT_SAME_DEVICE
        raise error

    monkeypatch.setattr(os, "rename", cross_drive)
    refused(log, record.id, resolve, root, quarantine, match="drive")
    other = root / "b.txt"
    other.write_text("b")
    before = snapshot(root, quarantine)
    with pytest.raises(UndoRefused, match="drive"):
        log.quarantine(other, "delete_file")
    assert other.read_text() == "b"
    assert [r.path for r in log.list()] == [str(original)]  # no record for the refused one
    assert {k: v for k, v in snapshot(root, quarantine).items() if v is not None} == {
        k: v for k, v in before.items() if v is not None
    }


def test_busy_rename_is_retried(env, monkeypatch):
    log, root, quarantine, _resolve = env
    original = root / "a.txt"
    original.write_text("old")
    real_rename = os.rename
    calls = 0

    def busy_then_rename(src, dst):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise OSError(0, "busy", None, 5)
        real_rename(src, dst)

    monkeypatch.setattr(os, "rename", busy_then_rename)
    record = log.quarantine(original, "delete_file")
    assert calls == 3
    assert not original.exists()
    assert (quarantine / record.id / "item").read_text() == "old"


def test_rename_busy_too_long_is_refused(env, monkeypatch):
    log, root, quarantine, _resolve = env
    original = root / "a.txt"
    original.write_text("old")
    before = snapshot(root, quarantine)
    calls = 0

    def always_busy(src, dst):
        nonlocal calls
        calls += 1
        raise OSError(0, "busy", None, 32)

    monkeypatch.setattr(os, "rename", always_busy)
    with pytest.raises(UndoRefused, match="move failed: PermissionError"):
        log.quarantine(original, "delete_file")
    assert calls == 10
    assert original.read_text() == "old"
    assert log.list() == []
    assert {k: v for k, v in snapshot(root, quarantine).items() if v is not None} == {
        k: v for k, v in before.items() if v is not None
    }


def test_other_rename_errors_are_not_retried(env, monkeypatch):
    log, root, quarantine, _resolve = env
    original = root / "a.txt"
    original.write_text("old")
    calls = 0

    def exists(src, dst):
        nonlocal calls
        calls += 1
        raise FileExistsError(0, "exists", None, 183)

    monkeypatch.setattr(os, "rename", exists)
    with pytest.raises(UndoRefused, match="move failed: FileExistsError"):
        log.quarantine(original, "delete_file")
    assert calls == 1
    assert original.read_text() == "old"


def test_item_missing_refused(env):
    log, root, quarantine, resolve = env
    record = log.moved(root / "a.txt", root / "gone.txt", "move_file")
    refused(log, record.id, resolve, root, quarantine, match="missing")


def test_unknown_and_malformed_ids_refused(env):
    log, root, quarantine, resolve = env
    (quarantine / "notes").mkdir()
    for bad in ["0" * 32, "..", "..\\x", "a/b", "A" * 32, "0" * 31, "", "notes", None, 5]:
        refused(log, bad, resolve, root, quarantine, kind=UnknownRecord)
        with pytest.raises(UnknownRecord):
            log.get(bad)


def test_already_undone_refused(env):
    log, root, quarantine, resolve = env
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")
    log.undo(record.id, resolve)
    original.rename(root / "elsewhere.txt")  # the spot is free again
    refused(log, record.id, resolve, root, quarantine, match="already undone")


def test_path_no_longer_allowed_refused(env):
    log, root, quarantine, resolve = env
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")

    def nothing_allowed(raw):
        return resolve_inside(raw, [])

    refused(log, record.id, nothing_allowed, root, quarantine, match="outside the allowed roots")


def test_junction_swapped_in_refused(env, dirs):
    log, root, quarantine, resolve = env
    (root / "d").mkdir()
    (root / "d" / "a.txt").write_text("old")
    record = log.quarantine(root / "d" / "a.txt", "delete_file")
    (root / "d").rmdir()
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    _winapi.CreateJunction(str(elsewhere), str(root / "d"))  # same name, other folder
    refused(log, record.id, resolve, root, quarantine, match="changed")
    assert list(elsewhere.iterdir()) == []


def test_tampered_record_refused(env, dirs):
    """Fix (a): record.json cannot point the quarantine side anywhere else."""
    log, root, quarantine, resolve = env
    outside = Path(os.path.realpath(dirs[1]))
    bait = outside / "bait.txt"
    bait.write_text("bait")
    original = root / "a.txt"
    original.write_text("old")
    record = log.quarantine(original, "delete_file")
    path = quarantine / record.id / "record.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for tampered in [{**data, "item": str(bait)}, {**data, "id": "f" * 32}, {"kind": "quarantined"}]:
        path.write_text(json.dumps(tampered), encoding="utf-8")
        refused(log, record.id, resolve, root, quarantine, match="unreadable")
    assert bait.read_text() == "bait"


def test_linked_item_refused(env, dirs):
    log, root, quarantine, resolve = env
    # Someone replaces a record folder with a junction to elsewhere.
    target = Path(os.path.realpath(dirs[1])) / "target"
    target.mkdir()
    (target / "item").write_text("not ours")
    original = root / "x.txt"
    original.write_text("x")
    record = log.quarantine(original, "delete_file")
    os.rename(quarantine / record.id, quarantine / "moved-away")
    _winapi.CreateJunction(str(target), str(quarantine / record.id))
    (target / "record.json").write_text(
        (quarantine / "moved-away" / "record.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    refused(log, record.id, resolve, root, quarantine, match="link")
    assert (target / "item").read_text() == "not ours"
    assert not original.exists()


def test_odd_file_name_never_strands_a_quarantined_item(env):
    """P2.9 R4: a lone surrogate is legal in an NTFS name. The record must still be written
    after the item moved, or the item sits in quarantine with no way back."""
    log, root, quarantine, resolve = env
    victim = root / "x\ud800.txt"
    victim.write_text("keep")
    record = log.quarantine(victim, "delete_file")
    assert [r.id for r in log.list()] == [record.id]
    assert log.get(record.id).path == str(victim)
    assert (quarantine / record.id / "item").read_text() == "keep"
    # The policy refuses unprintable paths (P2.9 B), so undo refuses rather than move;
    # the item and its record stay for Karthik to restore by hand.
    refused(log, record.id, resolve, root, quarantine, match="unprintable")
    assert (quarantine / record.id / "item").exists()
