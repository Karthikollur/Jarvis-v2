# Undo linked-item test setup: plant the junction instead of renaming a record folder

Status: DRAFT (Claude Code, 2026-11-23). Not approved. No code until Karthik approves.

## Context

The `fix: undo rename retry` review (`0491cbe`) found a second flaky test:
`tests/test_undo.py::test_linked_item_refused`. It failed 7 times in 51 runs right after a
full suite run (0 of 30 later; Cursor saw 0 of 20). Every failure is `PermissionError:
[WinError 5]` at line 404, the test's own setup:

```python
record = log.quarantine(original, "delete_file")
os.rename(quarantine / record.id, quarantine / "moved-away")   # line 404
```

`quarantine` has just written `item` and `record.json` into that folder, and another
process (Defender, the indexer) briefly holds a handle inside it. That is the same mechanism
the product retry fixed, but this is a raw `os.rename` in test code, so the retry cannot
cover it. It also failed with the pre-fix `_rename`, so it is older than the fix. Product
code is fine; only the test setup races.

## Change (one commit, `fix: undo linked test setup`)

Files: `tests/test_undo.py`, `docs/PROGRESS.md`. `safety/`, `bridge/`, `config/`,
`pyproject.toml` untouched. No PLAN.md task.

Replace the body of `test_linked_item_refused` (same name, same place) with:

```python
def test_linked_item_refused(env, dirs):
    log, root, quarantine, resolve = env
    # Someone plants a record folder that is a junction to elsewhere, holding a copy of a
    # real record. No folder is renamed here: renaming a just-written record folder races
    # with Defender/the indexer (WinError 5, 2026-11-23).
    target = Path(os.path.realpath(dirs[1])) / "target"
    target.mkdir()
    (target / "item").write_text("not ours")
    original = root / "x.txt"
    original.write_text("x")
    record = log.quarantine(original, "delete_file")
    data = json.loads((quarantine / record.id / "record.json").read_text(encoding="utf-8"))
    planted = "f" * 32
    (target / "record.json").write_text(json.dumps({**data, "id": planted}), encoding="utf-8")
    _winapi.CreateJunction(str(target), str(quarantine / planted))
    refused(log, planted, resolve, root, quarantine, match="link")
    assert (target / "item").read_text() == "not ours"
    assert not original.exists()
```

What changes in the scenario: the junction sits at a new valid id instead of replacing the
real record's folder. `UndoLog.get` checks `_is_link` on the folder at the id whatever its
history, so the check under test is the same. Without that check, `undo` would follow the
planted record and move `target/item` onto `root/x.txt`; the asserts catch that.

Not chosen: routing line 404 through `safety.undo._rename`. It keeps the old scenario in one
line, but ties the test to a private helper and still races for up to 0.5 s.

Not in scope: `tests/test_memory_ingest.py:568` renames a root folder too. It has never
been seen failing.

## Checked before drafting (scratch test outside the repo, nothing in the repo touched)

- The setup above, 40 runs in a row: refused with "record folder is a link" every time,
  `target/item` untouched, `original` still gone.
- With only `get`'s record-folder `_is_link` check disabled (the item check kept), `undo`
  follows the planted record and `root/x.txt` becomes "not ours". So the test still fails
  without the check.

## Mutant (one, restored from the saved bytes after the run)

| Mutant | Killed by |
|---|---|
| `safety/undo.py` `get`: delete `if _is_link(folder): raise UndoRefused("record folder is a link")` | `test_linked_item_refused` |

Killed = exit 1 and `test_linked_item_refused` among the failures, as for the retry fix.

## Verification

- Full suite through `cmd /c`: 730 passed, 4 skipped.
- Right after that suite run (the flake showed up under load), `tests/test_undo.py` 20 runs
  in a row: 0 failures.
- The mutant above. The reviewer (Claude Code) re-runs all three.

## Process

Cursor (implementer): pre-edit summary, then Karthik's go, then one commit and a Session
log entry. Claude Code reviews.
