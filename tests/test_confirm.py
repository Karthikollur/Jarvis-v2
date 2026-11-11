import _winapi
import shutil

import pytest

from safety.confirm import ConfirmQueue, QueueRefused
from safety.policy import MAX_SECONDS


@pytest.fixture
def queue(clock):
    return ConfirmQueue(clock, limit=3)


def add(queue, task_id="t1", args=None):
    return queue.add(task_id, "delete_file", args or {"path": "C:\\x"}, {}, "T2")


# --- queue ------------------------------------------------------------------


def test_add_and_take_once(queue, clock):
    clock.now = 5.0
    pending = add(queue)
    assert (pending.task_id, pending.tool, pending.reason, pending.created) == (
        "t1", "delete_file", "T2", 5.0,
    )
    assert queue.list() == [pending]
    assert queue.for_task("t1") == pending
    assert queue.take(pending.id) == pending
    assert queue.take(pending.id) is None  # one-shot
    assert queue.list() == [] and queue.for_task("t1") is None


def test_unknown_id_takes_nothing(queue):
    add(queue)
    assert queue.take("nope") is None
    assert len(queue.list()) == 1


def test_stored_args_do_not_follow_caller(queue):
    args = {"path": "C:\\x"}
    pending = add(queue, args=args)
    args["path"] = "C:\\elsewhere"
    assert pending.args == {"path": "C:\\x"}


def test_one_pending_per_task(queue):
    add(queue, "t1")
    with pytest.raises(QueueRefused, match="awaiting confirmation"):
        add(queue, "t1")
    add(queue, "t2")  # other tasks are not blocked


def test_cap_refused(queue):
    for n in range(3):
        add(queue, f"t{n}")
    with pytest.raises(QueueRefused, match="too many"):
        add(queue, "t3")
    assert len(queue.list()) == 3


def test_clear_empties(queue):
    first = add(queue, "t1")
    add(queue, "t2")
    queue.clear()
    assert queue.list() == []
    assert queue.take(first.id) is None
    add(queue, "t1")  # the task may ask again after a clear


# --- recheck at approve time ------------------------------------------------


def confirmed(policy, root):
    task = policy.new_task()
    args = {"path": str(root / "victim.txt")}
    decision = policy.check(task, "delete_file", args)
    assert decision.action == "confirm"
    return task, args, decision.paths


def test_recheck_passes_when_nothing_changed(policy, dirs):
    task, args, paths = confirmed(policy, dirs[0])
    assert policy.recheck(task, "delete_file", args, paths) is None


def test_recheck_does_not_spend_budget(policy, dirs):
    task, args, paths = confirmed(policy, dirs[0])
    calls = task.calls
    policy.recheck(task, "delete_file", args, paths)
    assert task.calls == calls


def test_recheck_refuses_stopped_task(policy, dirs):
    task, args, paths = confirmed(policy, dirs[0])
    task.stopped = True  # e.g. kill switch, or another budget breach
    assert policy.recheck(task, "delete_file", args, paths) == "task stopped"


def test_recheck_refuses_out_of_time_task(policy, dirs, clock):
    task, args, paths = confirmed(policy, dirs[0])
    clock.now = MAX_SECONDS + 1  # waiting for the click counts against the task
    assert "time budget" in policy.recheck(task, "delete_file", args, paths)
    assert task.stopped


def test_recheck_refuses_junction_swapped_in(policy, dirs):
    root, outside = dirs
    (root / "sub").mkdir()
    task = policy.new_task()
    args = {"path": str(root / "sub" / "victim.txt")}
    decision = policy.check(task, "delete_file", args)
    assert decision.action == "confirm"
    # While the action waits, "sub" is replaced by a junction pointing outside the root.
    shutil.rmtree(root / "sub")
    _winapi.CreateJunction(str(outside), str(root / "sub"))
    reason = policy.recheck(task, "delete_file", args, decision.paths)
    assert reason is not None and "outside the allowed roots" in reason


def test_recheck_refuses_path_that_resolves_elsewhere(policy, dirs):
    root, outside = dirs
    (root / "a").mkdir()
    (root / "b").mkdir()
    task = policy.new_task()
    args = {"path": str(root / "a" / "victim.txt")}
    decision = policy.check(task, "delete_file", args)
    # Still inside the root, but no longer the file that was shown to Karthik.
    shutil.rmtree(root / "a")
    _winapi.CreateJunction(str(root / "b"), str(root / "a"))
    reason = policy.recheck(task, "delete_file", args, decision.paths)
    assert reason == "path: changed since the request"


def test_recheck_refuses_missing_resolved_path(policy, dirs):
    task, args, _ = confirmed(policy, dirs[0])
    assert policy.recheck(task, "delete_file", args, {}) == "path: changed since the request"


def test_recheck_refuses_unknown_tool(policy):
    task = policy.new_task()
    assert policy.recheck(task, "shell_exec", {}, {}) == "unknown tool"
