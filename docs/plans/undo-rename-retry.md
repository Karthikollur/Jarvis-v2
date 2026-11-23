# Undo rename retry: bounded retry in `safety/undo.py` `_rename` (fix for the undo-test flake)

Status: APPROVED by Karthik 2026-11-23 (plan mode; chose "Retry in `_rename`" over a test-only retry or a known flake).

## Context

`tests/test_undo.py::test_quarantine_folder_and_undo` fails about 1 run in 5 on this
laptop. It has failed three times now: 2026-11-16 (`WinError 5`), once more in the P3.5b
re-runs, and 2026-11-23 in the P4.2 review (`UndoRefused: move failed: PermissionError`).
Each time `os.rename` was moving a folder that held a file written moments earlier. That
fits another process (Defender, the search indexer, an editor's watcher) briefly holding
a handle to the file. Windows then refuses the folder rename with `ERROR_ACCESS_DENIED`
(5) or `ERROR_SHARING_VIOLATION` (32). A real `delete_file` of a folder just written to
would be refused the same way. That is safe (nothing moves) but it is a spurious refusal.

Karthik cut this retry from P3.7 (D1: "no one has seen the error outside a test"). On
2026-11-23 he chose it again over a test-only retry or a documented known flake.

## Change (one commit, `fix: undo rename retry`)

Files: `safety/undo.py`, `tests/test_undo.py`, `docs/PROGRESS.md`. Before Cursor starts,
Claude Code copies this plan to `docs/plans/undo-rename-retry.md` marked APPROVED. No
PLAN.md task (it is a fix, logged in PROGRESS like P3.7's). `bridge/`, `config/`,
`pyproject.toml` untouched.

`safety/undo.py`, `_rename` only (`time` is already imported):

```python
_BUSY = {5, 32}  # ERROR_ACCESS_DENIED, ERROR_SHARING_VIOLATION


def _rename(source: Path, target: Path) -> None:
    """The only way anything moves. Refuses instead of overwriting, nesting or copying."""
    for attempt in range(10):
        try:
            os.rename(source, target)
            return
        except OSError as error:
            if getattr(error, "winerror", None) == 17 or error.errno == errno.EXDEV:
                raise UndoRefused("cannot move across drives") from error
            if getattr(error, "winerror", None) not in _BUSY or attempt == 9:
                raise UndoRefused(f"move failed: {type(error).__name__}") from error
            # ponytail: another process briefly holds a handle inside the folder
            # (Defender, indexer); bounded, 0.5 s at most, then refuse as before.
            time.sleep(0.05)
```

Why this does not weaken `safety/`. A failed `os.rename` moves nothing, so trying it
again has no side effect. An existing target (`FileExistsError`, 183) and a cross-drive
move (17) are still refused on the first try. After 10 tries the refusal and its message
are exactly what they are today. The undo lock can be held 0.5 s longer at most.

Not in scope: `bridge/tools.py` `_move`. It moves plain files only, has never failed, and
moving folders is the case that fails.

## Tests (`tests/test_undo.py`, new, next to the refusal tests)

Each test fakes `os.rename` with `monkeypatch` and counts the calls. A busy error is
`OSError(0, "busy", None, 5)` (or `32`). On Windows the fourth argument sets `winerror`
and makes it a `PermissionError`.

1. `test_busy_rename_is_retried`: the first 2 calls raise winerror 5, then the real
   rename runs. `quarantine` succeeds, the item is in quarantine, 3 calls.
2. `test_rename_busy_too_long_is_refused`: every call raises winerror 32. `quarantine`
   raises `UndoRefused` matching `move failed: PermissionError`, exactly 10 calls, the
   file is still in place (`snapshot`), and `list()` has no record for it.
3. `test_other_rename_errors_are_not_retried`: one call raises
   `FileExistsError(0, "exists", None, 183)`. `UndoRefused`, exactly 1 call.

The existing tests stay as they are (`test_target_appearing_after_check_is_not_overwritten`,
`test_move_across_drives_refused`, the flaky folder test).

## Mutants (one at a time, restored after each)

| Mutant | Killed by |
|---|---|
| retry removed (`range(1)`) | 1 |
| every `OSError` retried (busy check dropped) | 3 |
| bound raised (`range(10)` to `range(20)`, `attempt == 19`) | 2 |
| 5 dropped from `_BUSY` | 1 |
| 32 dropped from `_BUSY` | 2 |

"Sleep removed" is not run: no test measures time, so it would survive (record it as
not run).

## Verification

- `uv run python -m pytest` from the repo root, through `cmd /c` in Cursor's terminal:
  all pass.
- `tests/test_undo.py` 20 runs in a row (`1..20 | % { cmd /c "uv run python -m pytest
  tests/test_undo.py -q" }`): 0 failures. It failed 1 run in 5 before the fix.
- The five mutants above, results in the Session log. The reviewer (Claude Code) re-runs
  the suite, the 20-run loop and the mutants.

## Process

Cursor (implementer): pre-edit summary, then Karthik's go, then one commit and a Session
log entry. Claude Code reviews, as for every `safety/` change.
