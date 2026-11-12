import json
import threading
from pathlib import Path

import pytest

from safety.audit import MAX_RESULT, AuditLog


def lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.fixture
def log_path(dirs):
    return dirs[0] / "audit.jsonl"


def test_each_write_is_one_parseable_line(log_path):
    log = AuditLog(log_path, wall=lambda: 0.0)
    log.write("task", task_id="t1")
    raw = log_path.read_bytes()
    assert raw.count(b"\n") == 1 and raw.endswith(b"\n")
    assert b"\r" not in raw
    assert lines(log_path) == [{"ts": "1970-01-01T00:00:00+00:00", "event": "task", "task_id": "t1"}]


def test_appends_never_truncates(log_path):
    AuditLog(log_path).write("start")
    AuditLog(log_path).write("task", task_id="a")
    AuditLog(log_path).write("task", task_id="b")
    assert [entry["event"] for entry in lines(log_path)] == ["start", "task", "task"]
    assert [entry.get("task_id") for entry in lines(log_path)] == [None, "a", "b"]


def test_argument_cannot_forge_a_line(log_path):
    forged = '\n{"event": "approve"}\n'
    AuditLog(log_path).write("request", args={"path": forged})
    entries = lines(log_path)
    assert len(entries) == 1
    assert entries[0]["event"] == "request"
    assert entries[0]["args"] == {"path": forged}


def test_paths_and_other_values_serialise(log_path):
    AuditLog(log_path).write("request", paths={"path": Path("C:/JarvisSandbox/a.txt")}, text="ü")
    entry = lines(log_path)[0]
    assert entry["paths"] == {"path": str(Path("C:/JarvisSandbox/a.txt"))}
    assert entry["text"] == "ü"


def test_long_result_is_cut(log_path):
    log = AuditLog(log_path)
    log.write("result", status="done", result="x" * (MAX_RESULT + 500))
    log.write("result", status="done", result="short")
    cut, short = lines(log_path)
    assert MAX_RESULT == 2000
    assert cut["result"] == "x" * MAX_RESULT
    assert cut["truncated"] is True
    assert cut["length"] == MAX_RESULT + 500
    assert short["result"] == "short"
    assert "truncated" not in short and "length" not in short


def test_non_text_result_is_logged_as_text(log_path):
    AuditLog(log_path).write("result", status="done", result={"items": [1, 2]})
    assert lines(log_path)[0]["result"] == '{"items": [1, 2]}'


def test_unwritable_path_raises(dirs):
    log = AuditLog(dirs[0] / "missing-folder" / "audit.jsonl")
    with pytest.raises(OSError):
        log.write("start")


def test_no_way_to_edit_or_delete():
    public = {name for name in dir(AuditLog) if not name.startswith("_")}
    assert public == {"write"}


def test_concurrent_writes_stay_intact(log_path):
    log = AuditLog(log_path)

    def worker(n):
        for i in range(20):
            log.write("request", worker=n, i=i, args={"pad": "y" * 500})

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(50)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    entries = lines(log_path)
    assert len(entries) == 1000
    assert {(e["worker"], e["i"]) for e in entries} == {(n, i) for n in range(50) for i in range(20)}


def test_lone_surrogate_is_written_escaped(log_path):
    # P2.8: an unpaired surrogate cannot be encoded as UTF-8. The line must still be written.
    log = AuditLog(log_path, wall=lambda: 0.0)
    log.write("request", args={"path": "C:\\x\\a\ud800.txt"})
    log.write("result", status="done", result="b\udfff")
    raw = log_path.read_bytes()
    assert raw.count(b"\n") == 2
    first, second = lines(log_path)
    assert first["args"] == {"path": "C:\\x\\a\ud800.txt"}
    assert second["result"] == "b\udfff"
