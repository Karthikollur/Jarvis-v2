import _winapi
import os
import sys
import threading
from pathlib import Path

import pytest

from safety.policy import (
    MAX_CALLS,
    MAX_FAILURES,
    MAX_SECONDS,
    TOOLS,
    PathRefused,
    Task,
    Tier,
    load_roots,
    resolve_inside,
)

REPO = Path(__file__).resolve().parents[1]


# --- allowed roots ----------------------------------------------------------


@pytest.mark.parametrize(
    "make",
    [
        lambda r, o: str(r),
        lambda r, o: str(r / "a" / "new.txt"),
        lambda r, o: str(r / "a" / ".." / "b.txt"),
        lambda r, o: str(r).upper() + "\\X.TXT",
        lambda r, o: str(r / "a.txt").replace("\\", "/"),
    ],
)
def test_paths_inside_root_allowed(dirs, make):
    root, outside = dirs
    resolved = resolve_inside(make(root, outside), [root])
    assert os.path.normcase(str(resolved)).startswith(os.path.normcase(str(root)))


@pytest.mark.parametrize(
    "make",
    [
        lambda r, o: str(r / ".." / "outside" / "x.txt"),  # traversal
        lambda r, o: str(o / "x.txt"),  # absolute, outside
        lambda r, o: str(o / "x.txt").replace("\\", "/"),
        lambda r, o: str(r) + "Evil\\x.txt",  # sibling sharing the prefix
        lambda r, o: "C:\\Windows\\win.ini",
        lambda r, o: "\\\\server\\share\\x.txt",  # UNC
        lambda r, o: "//server/share/x.txt",
        lambda r, o: "\\\\?\\" + str(r / "x.txt"),  # device paths
        lambda r, o: "\\\\.\\C:\\x.txt",
        lambda r, o: str(r / "x.txt") + ":stream",  # alternate data stream
        lambda r, o: "C:x.txt",  # drive-relative
        lambda r, o: "x.txt",  # relative
        lambda r, o: "..\\x.txt",
        lambda r, o: "\\x.txt",  # rooted, no drive
        lambda r, o: str(r / "NUL"),  # device names
        lambda r, o: str(r / "com1.txt"),
        lambda r, o: str(r / "name."),  # Windows strips these silently
        lambda r, o: str(r / "name "),
        lambda r, o: str(r / "a\0b"),
        lambda r, o: "",
        lambda r, o: None,
        lambda r, o: 5,
    ],
)
def test_paths_outside_root_refused(dirs, make):
    root, outside = dirs
    with pytest.raises(PathRefused):
        resolve_inside(make(root, outside), [root])


def test_junction_out_of_root_refused(dirs):
    root, outside = dirs
    _winapi.CreateJunction(str(outside), str(root / "jump"))
    assert (root / "jump").is_junction()
    with pytest.raises(PathRefused):
        resolve_inside(str(root / "jump" / "x.txt"), [root])
    with pytest.raises(PathRefused):
        resolve_inside(str(root / "jump"), [root])


def test_symlink_out_of_root_refused(dirs):
    root, outside = dirs
    try:
        os.symlink(outside, root / "link", target_is_directory=True)
    except OSError:
        pytest.skip("this Windows account may not create symlinks")
    with pytest.raises(PathRefused):
        resolve_inside(str(root / "link" / "x.txt"), [root])


def test_no_roots_means_nothing_allowed(dirs):
    with pytest.raises(PathRefused):
        resolve_inside(str(dirs[0]), [])


def test_shipped_roots_file():
    assert load_roots(REPO / "config" / "allowed_roots.toml") == [Path("C:\\JarvisSandbox")]


@pytest.mark.parametrize("bad", ["C:\\", "C:", "sandbox", "\\\\server\\share", "C:\\\\x"])
def test_unsafe_root_config_refused(dirs, bad):
    config = dirs[0] / "roots.toml"
    config.write_text(f"[[root]]\npath = '{bad}'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_roots(config)


# --- tiers and taint --------------------------------------------------------


def test_tool_table_matches_eval_stubs():
    from evals.stub_tools import SPECS

    assert set(TOOLS) == set(SPECS)
    for name, rule in TOOLS.items():  # P2.8: the model is offered exactly what the policy accepts
        assert set(SPECS[name][1]["properties"]) == set(rule.params), name


def test_unknown_tool_denied(policy):
    task = policy.new_task()
    for tool in ["shell_exec", "file_write", "", None, 3]:
        assert policy.check(policy.new_task(), tool, {}).action == "deny"
    assert policy.check(task, "get_time", "not a dict").action == "deny"


def test_tiers(policy, dirs):
    root, outside = dirs
    inside = {"path": str(root / "a.txt")}
    assert policy.check(policy.new_task(), "get_time", {}).action == "allow"
    decision = policy.check(policy.new_task(), "create_folder", inside)
    assert (decision.action, decision.tier) == ("allow", Tier.T1)
    assert decision.paths["path"] == Path(os.path.realpath(root / "a.txt"))
    decision = policy.check(policy.new_task(), "delete_file", inside)
    assert (decision.action, decision.reason) == ("confirm", "T2")
    assert policy.check(policy.new_task(), "run_named_script", {"name": "x"}).action == "confirm"


def test_path_argument_outside_root_denied(policy, dirs):
    root, outside = dirs
    escape = str(root / ".." / "outside" / "x.txt")
    for tool, args in [
        ("list_dir", {"path": str(outside)}),
        ("read_text_file", {"path": escape}),
        ("delete_file", {"path": escape}),
        ("create_folder", {}),  # missing argument
        ("move_file", {"source": str(root / "a.txt"), "destination": str(outside)}),
        ("move_file", {"source": escape, "destination": str(root)}),
    ]:
        assert policy.check(policy.new_task(), tool, args).action == "deny", (tool, args)


def test_rename_needs_plain_file_name(policy, dirs):
    path = str(dirs[0] / "a.txt")
    ok = policy.check(policy.new_task(), "rename_file", {"path": path, "new_name": "b.txt"})
    assert ok.action == "allow"
    for name in ["..\\b.txt", "sub/b.txt", "C:b.txt", "..", "", "NUL", "b.txt.", None]:
        args = {"path": path, "new_name": name}
        assert policy.check(policy.new_task(), "rename_file", args).action == "deny", name


def test_taint_upgrades_t1_to_confirm(policy, dirs):
    root, outside = dirs
    folder = {"path": str(root / "new")}
    task = policy.new_task()
    assert policy.check(task, "create_folder", folder).action == "allow"
    assert policy.check(task, "read_text_file", {"path": str(root / "a.txt")}).action == "allow"
    policy.record(task, "read_text_file", ok=True)
    assert task.tainted
    decision = policy.check(task, "create_folder", folder)
    assert (decision.action, decision.tier, decision.reason) == ("confirm", Tier.T2, "tainted T1")
    assert policy.check(task, "open_app", {"app": "notepad"}).action == "confirm"
    assert policy.check(task, "get_time", {}).action == "allow"  # T0 stays automatic


def test_failed_read_does_not_taint(policy):
    task = policy.new_task()
    policy.record(task, "read_text_file", ok=False)
    assert not task.tainted


# --- budgets ----------------------------------------------------------------


def test_call_budget(policy):
    task = policy.new_task()
    for _ in range(MAX_CALLS):
        assert policy.check(task, "get_time", {}).action == "allow"
    assert policy.check(task, "get_time", {}).action == "deny"
    assert task.stopped


def test_refused_calls_count_against_budget(policy):
    task = policy.new_task()
    for _ in range(MAX_CALLS):
        assert policy.check(task, "shell_exec", {}).reason == "unknown tool"
    assert "call budget" in policy.check(task, "get_time", {}).reason


def test_time_budget(policy, clock):
    task = policy.new_task()
    clock.now = MAX_SECONDS
    assert policy.check(task, "get_time", {}).action == "allow"
    clock.now = MAX_SECONDS + 1
    assert policy.check(task, "get_time", {}).action == "deny"
    clock.now = 0  # a stopped task stays stopped
    assert policy.check(task, "get_time", {}).reason == "task stopped"


def test_out_of_time_is_read_only(policy, clock):
    task = policy.new_task()
    clock.now = MAX_SECONDS
    assert not policy.out_of_time(task)
    clock.now = MAX_SECONDS + 1
    assert policy.out_of_time(task)
    assert not task.stopped  # asking does not stop the task
    assert task.calls == 0


def test_retry_budget(policy):
    task = policy.new_task()
    for _ in range(MAX_FAILURES):
        assert policy.check(task, "system_stats", {}).action == "allow"
        policy.record(task, "system_stats", ok=False)
    assert policy.check(task, "system_stats", {}).action == "deny"
    assert task.stopped
    assert policy.check(task, "get_time", {}).action == "deny"


# --- protected folders (P2.6, audit point 9) --------------------------------


@pytest.fixture
def guarded(dirs):
    """(root, protected): a root that contains a protected folder."""
    root = dirs[0]
    protected = root / "prot"
    protected.mkdir()
    return root, protected


@pytest.mark.parametrize(
    "make",
    [
        lambda r, p: str(p / "x.txt"),
        lambda r, p: str(p),  # the folder itself
        lambda r, p: str(r / "a" / ".." / "prot" / "x.txt"),
        lambda r, p: str(p / "x.txt").upper(),
        lambda r, p: str(p / "deeper" / "new.txt"),
    ],
)
def test_protected_folder_refused(guarded, make):
    root, protected = guarded
    with pytest.raises(PathRefused, match="protected folder"):
        resolve_inside(make(root, protected), [root], [protected])


def test_protected_folder_via_junction_refused(guarded):
    root, protected = guarded
    _winapi.CreateJunction(str(protected), str(root / "jump"))
    with pytest.raises(PathRefused, match="protected folder"):
        resolve_inside(str(root / "jump" / "x.txt"), [root], [protected])


def test_rest_of_root_still_allowed(guarded):
    root, protected = guarded
    for path in [root / "x.txt", root / "prot2" / "x.txt", root / "protected.txt"]:
        assert resolve_inside(str(path), [root], [protected]) == Path(os.path.realpath(path))


def test_root_inside_protected_folder_allows_nothing(dirs):
    root = dirs[0]
    for path in [root, root / "x.txt"]:
        with pytest.raises(PathRefused, match="protected folder"):
            resolve_inside(str(path), [root], [root.parent])


def test_protected_folder_given_through_junction(guarded, clock):
    """Fix (d): Policy realpath-resolves protected folders once, when built."""
    from safety.policy import Policy

    root, protected = guarded
    alias = root.parent / "alias"
    _winapi.CreateJunction(str(protected), str(alias))
    policy = Policy([root], clock, [alias])
    decision = policy.check(policy.new_task(), "list_dir", {"path": str(protected / "x")})
    assert (decision.action, decision.reason) == ("deny", "path: protected folder")


def test_protected_folder_via_short_name_refused(guarded):
    import ctypes

    root, protected = guarded
    long_name = root / "protected-folder-with-long-name"
    long_name.mkdir()
    buffer = ctypes.create_unicode_buffer(1024)
    ctypes.windll.kernel32.GetShortPathNameW(str(long_name), buffer, 1024)
    if not buffer.value or Path(buffer.value).name == long_name.name:
        pytest.skip("this volume does not create 8.3 short names")
    with pytest.raises(PathRefused, match="protected folder"):
        resolve_inside(buffer.value + "\\x.txt", [root], [long_name])


def test_check_and_recheck_refuse_protected(guarded, clock):
    from safety.policy import Policy

    root, protected = guarded
    policy = Policy([root], clock, [protected])
    decision = policy.check(policy.new_task(), "delete_file", {"path": str(protected / "x")})
    assert (decision.action, decision.reason) == ("deny", "path: protected folder")
    # Queued while `d` is a plain folder; a junction to the protected folder is swapped in.
    (root / "d").mkdir()
    args = {"path": str(root / "d" / "x.txt")}
    task = policy.new_task()
    decision = policy.check(task, "delete_file", args)
    assert decision.action == "confirm"
    (root / "d").rmdir()
    _winapi.CreateJunction(str(protected), str(root / "d"))
    assert policy.recheck(task, "delete_file", args, decision.paths) == "path: protected folder"


# --- concurrency (P2.7) -----------------------------------------------------
# Routes run in a thread pool, so two requests for one task can reach `Policy` at the
# same time. Each test forces the interleaving with a Barrier instead of hoping a sleep
# lines it up. Under the lock only one thread can be inside, so the barrier never fills:
# it breaks after BARRIER_TIMEOUT and every later wait returns at once.

BARRIER_TIMEOUT = 1.0
JOIN_TIMEOUT = 5.0


def _meet(barrier: threading.Barrier | None) -> None:
    if barrier is not None:
        try:
            barrier.wait(BARRIER_TIMEOUT)
        except threading.BrokenBarrierError:
            pass


class _BarrierTask(Task):
    """A Task whose every read of `calls` waits until all threads have read it."""

    barrier: threading.Barrier | None = None

    @property
    def calls(self) -> int:
        value = self._calls
        _meet(self.barrier)
        return value

    @calls.setter
    def calls(self, value: int) -> None:
        self._calls = value


class _BarrierDict(dict):
    """A failures dict whose every `get` waits until all threads have read it."""

    barrier: threading.Barrier | None = None

    def get(self, key, default=None):
        value = super().get(key, default)
        _meet(self.barrier)
        return value


def _run_all(target, count: int) -> list:
    """Run `target` in `count` daemon threads; return the results. Every thread must
    finish within JOIN_TIMEOUT, so a deadlock fails the test instead of hanging the
    suite (daemon threads cannot block interpreter exit)."""
    results, errors = [], []

    def run():
        try:
            results.append(target())
        except BaseException as error:  # reported below, never lost in the thread
            errors.append(error)

    threads = [threading.Thread(target=run, daemon=True) for _ in range(count)]
    try:
        for thread in threads:
            thread.start()
    finally:
        for thread in threads:
            if thread.ident is not None:
                thread.join(JOIN_TIMEOUT)
    assert not [thread for thread in threads if thread.is_alive()], "a thread hung"
    assert not errors, errors
    return results


def test_concurrent_checks_cannot_exceed_call_budget(policy, clock):
    count = 4
    task = _BarrierTask(started=clock())
    task.calls = MAX_CALLS - 1
    task.barrier = threading.Barrier(count)
    decisions = _run_all(lambda: policy.check(task, "get_time", {}), count)
    task.barrier = None
    assert sorted(decision.action for decision in decisions) == ["allow"] + ["deny"] * (count - 1)
    # The first refusal stops the task, so the later ones may answer "task stopped".
    reasons = [d.reason for d in decisions if d.action == "deny"]
    assert any("call budget" in reason for reason in reasons)
    assert all("call budget" in reason or reason == "task stopped" for reason in reasons)
    assert task.calls == MAX_CALLS and task.stopped


def test_concurrent_failures_are_all_counted(policy, clock):
    task = Task(started=clock(), failures=_BarrierDict())
    task.failures.barrier = threading.Barrier(MAX_FAILURES)
    _run_all(lambda: policy.record(task, "system_stats", ok=False), MAX_FAILURES)
    task.failures.barrier = None
    assert task.failures["system_stats"] == MAX_FAILURES  # no lost update
    decision = policy.check(task, "system_stats", {})
    assert decision.action == "deny" and "failed" in decision.reason


def test_recheck_and_check_do_not_deadlock(policy, clock):
    # Both paths reach `_stop` while holding the lock; the lock is not re-entrant, so
    # `_stop` must not take it. A hang fails in _run_all.
    task = policy.new_task()
    decision = policy.check(task, "delete_file", {"path": str(policy.roots[0] / "x.txt")})
    assert decision.action == "confirm"
    clock.now = MAX_SECONDS + 1
    reasons = _run_all(
        lambda: policy.recheck(task, "delete_file", {"path": str(policy.roots[0] / "x.txt")},
                               decision.paths),
        1,
    )
    assert "time budget" in reasons[0] and task.stopped
    fresh = policy.new_task()
    fresh.started = -MAX_SECONDS  # out of time: check also reaches _stop
    assert _run_all(lambda: policy.check(fresh, "get_time", {}).reason, 1)[0].startswith("time")


def test_call_budget_under_thread_stress(policy):
    # Second net without a test-only Task: switch threads as often as possible.
    count = 32
    task = policy.new_task()
    start = threading.Barrier(count)

    def call():
        _meet(start)
        return policy.check(task, "get_time", {}).action

    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        actions = _run_all(call, count)
    finally:
        sys.setswitchinterval(old)
    assert actions.count("allow") == MAX_CALLS
    assert task.calls == MAX_CALLS


# --- path rules (P2.8 commit A) ---------------------------------------------


def test_path_on_a_drive_without_a_root_is_refused_before_resolution(dirs, monkeypatch):
    # A mapped network drive must never be contacted: realpath may not run at all.
    root = dirs[0]
    other = "Q" if root.drive[0].upper() != "Q" else "R"

    def never(path):
        raise AssertionError(f"realpath was called for {path}")

    monkeypatch.setattr(os.path, "realpath", never)
    for raw in [f"{other}:\\x.txt", f"{other.lower()}:\\a\\..\\x.txt", f"{other}:/x.txt"]:
        with pytest.raises(PathRefused, match="outside the allowed roots"):
            resolve_inside(raw, [root])


@pytest.fixture
def nested(dirs, clock):
    """(policy, root, keep): `keep` is a folder in the root that CONTAINS a protected folder."""
    from safety.policy import Policy

    root = dirs[0]
    keep = root / "keep"
    (keep / "secret").mkdir(parents=True)
    return Policy([root], clock, [keep / "secret"]), root, keep


def _decide(policy, tool, **args):
    decision = policy.check(policy.new_task(), tool, args)
    return decision.action, decision.reason


def test_root_itself_cannot_be_changed(nested):
    policy, root, keep = nested
    inside = str(root / "x")
    assert _decide(policy, "rename_file", path=str(root), new_name="Elsewhere") == (
        "deny", "path: the root itself")
    assert _decide(policy, "delete_file", path=str(root)) == ("deny", "path: the root itself")
    assert _decide(policy, "create_folder", path=str(root)) == ("deny", "path: the root itself")
    assert _decide(policy, "move_file", source=str(root), destination=inside) == (
        "deny", "source: the root itself")
    assert _decide(policy, "move_file", source=inside, destination=str(root)) == (
        "deny", "destination: the root itself")
    # Spelled differently, still the root.
    assert _decide(policy, "delete_file", path=str(root).upper() + "\\a\\..")[0] == "deny"
    assert _decide(policy, "list_dir", path=str(root)) == ("allow", "")  # reading is fine


def test_folder_containing_a_protected_folder_cannot_be_changed(nested):
    policy, root, keep = nested
    refused = "contains a protected folder"
    assert _decide(policy, "rename_file", path=str(keep), new_name="gone") == (
        "deny", f"path: {refused}")
    assert _decide(policy, "delete_file", path=str(keep)) == ("deny", f"path: {refused}")
    assert _decide(policy, "move_file", source=str(keep), destination=str(root / "m")) == (
        "deny", f"source: {refused}")
    assert _decide(policy, "list_dir", path=str(keep)) == ("allow", "")
    # A sibling whose name only starts the same is not an ancestor.
    assert _decide(policy, "delete_file", path=str(root / "kee"))[0] == "confirm"
    assert _decide(policy, "create_folder", path=str(keep / "other"))[0] == "allow"


def test_rename_landing_place_is_checked_and_returned(nested):
    policy, root, keep = nested
    args = {"path": str(root / "a.txt"), "new_name": "b.txt"}
    task = policy.new_task()
    decision = policy.check(task, "rename_file", args)
    assert decision.action == "allow"
    assert decision.paths == {
        "path": Path(os.path.realpath(root / "a.txt")),
        "target": Path(os.path.realpath(root / "b.txt")),
    }
    # Landing on a protected folder's name (any case) is refused.
    for name in ["secret", "SECRET"]:
        assert _decide(policy, "rename_file", path=str(keep / "x"), new_name=name) == (
            "deny", "new_name: protected folder"), name
    # recheck validates the landing place too.
    assert policy.recheck(task, "rename_file", args, decision.paths) is None
    moved = {**decision.paths, "target": root / "elsewhere.txt"}
    assert policy.recheck(task, "rename_file", args, moved) == "new_name: changed since the request"
    assert policy.recheck(task, "rename_file", {**args, "path": str(root)}, decision.paths) == (
        "path: the root itself")


# --- argument rules (P2.8 commit B) -----------------------------------------


def valid_args(tool, root):
    """Arguments the policy accepts for `tool` (fixture allowlists: notepad, x)."""
    rule = TOOLS[tool]
    args = {name: str(root / f"ok-{name}") for name in rule.path_params}
    args |= {name: "ok.txt" for name in rule.name_params}
    args |= {name: {"apps": "notepad", "scripts": "x"}[listed] for name, listed in rule.choices}
    args |= {name: "hello" for name in rule.text_params}
    return args


@pytest.mark.parametrize("tool", TOOLS)
def test_only_declared_arguments_are_accepted(policy, dirs, tool):
    args = valid_args(tool, dirs[0])
    assert set(args) == set(TOOLS[tool].params)
    assert policy.check(policy.new_task(), tool, args).action in ("allow", "confirm")
    for extra in ["overwrite", "permanent", "recursive", "target", ""]:
        decision = policy.check(policy.new_task(), tool, {**args, extra: True})
        assert (decision.action, decision.reason) == ("deny", "unknown argument"), extra
    for missing in args:
        without = {name: value for name, value in args.items() if name != missing}
        decision = policy.check(policy.new_task(), tool, without)
        assert decision.action == "deny" and decision.reason.startswith(f"{missing}: "), missing


@pytest.mark.parametrize("tool, param", [("open_app", "app"), ("run_named_script", "name")])
def test_app_and_script_must_be_on_the_allowlist(policy, tool, param):
    listed = valid_args(tool, Path("unused"))[param]
    assert policy.check(policy.new_task(), tool, {param: listed}).action in ("allow", "confirm")
    for value in [
        "C:/Windows/System32/cmd.exe",
        "powershell -enc AAAA",
        listed + " /c calc",
        listed.upper(),
        "../" + listed,
        "unknown",
        "",
        None,
        7,
        [listed],
        {"name": listed},
    ]:
        decision = policy.check(policy.new_task(), tool, {param: value})
        assert (decision.action, decision.reason) == (
            "deny", f"{param}: not on the allowlist"), repr(value)


def test_no_allowlist_means_nothing_runs(dirs, clock):
    from safety.policy import Policy

    bare = Policy([dirs[0]], clock)  # no apps.toml, no scripts.toml
    for tool, args in [("open_app", {"app": "notepad"}), ("run_named_script", {"name": "x"})]:
        assert bare.check(bare.new_task(), tool, args).action == "deny", tool


def test_text_arguments_are_short_plain_text(policy):
    from safety.policy import MAX_TEXT

    for tool, param in [("focus_window", "title"), ("recall_memory", "query")]:
        assert policy.check(policy.new_task(), tool, {param: "x" * MAX_TEXT}).action == "allow"
        for value in [
            "", "x" * (MAX_TEXT + 1), "a\nb", "a\x00", "a\x7f", "a\u202eb", None, 5, ["Notepad"],
        ]:
            decision = policy.check(policy.new_task(), tool, {param: value})
            assert (decision.action, decision.reason) == (
                "deny", f"{param}: must be short plain text"), repr(value)


def test_load_names(dirs):
    from safety.policy import load_names

    folder = dirs[0]
    assert load_names(folder / "missing.toml") == frozenset()  # no file: nothing allowed
    (folder / "apps.toml").write_text("[notepad]\n[vs_code]\ncommand = 'code'\n", encoding="utf-8")
    assert load_names(folder / "apps.toml") == {"notepad", "vs_code"}
    for bad in ["['Not Pad']\n", "['../x']\n", "[UPPER]\n", "name = 'top-level value'\n"]:
        (folder / "bad.toml").write_text(bad, encoding="utf-8")
        with pytest.raises(ValueError):
            load_names(folder / "bad.toml")
