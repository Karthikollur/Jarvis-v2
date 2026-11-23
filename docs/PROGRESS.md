# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- **2026-11-23: `P4.2: ingest` reviewed: NOT ACCEPTED yet, two findings** (Claude Code
  review of `c7a86b1`). The file list and the lock are as approved. Suite re-run: 727
  passed, 4 skipped (matches). 34 of 34 mutants killed. Findings: a PDF whose text is only
  a heading reaches `documents([])` and stops every run (the zero-chunk check skips PDFs),
  and a PDF is parsed by reopening its path, not from the checked handle. Plan change
  DRAFT in `docs/plans/P4.md` section C (`P4.2: ingest fixes`). Waiting on Karthik:
  approve it, and decide the optional `pypdf>=7.1.1` floor. PLAN.md not ticked.
- **2026-11-23: P4.2 ingest done** (`P4.2: ingest`). `memory/ingest.py` walks each docs
  root, chunks, and replaces document rows. `python -m memory reset-documents` asks for
  an exact `yes`. `pypdf` 7.1.1 is the only addition to `uv.lock`. PowerShell
  `uv run python -m pytest`: 727 passed, 4 skipped. 34 mutants killed (Session log).
  PLAN.md not ticked. The real vault was not ingested. Next: the reviewer re-runs the
  suite and the mutants.
- **2026-11-23: `P4.2: ingest` pre-edit answers APPROVED** by Karthik ("Approve all"):
  `reset-documents` lands in this commit, rows of now-skipped files are deleted, and the
  `pypdf` download has his go. Answers in `docs/plans/P4.md` section C, "Pre-edit
  answers". Next: Cursor installs `pypdf` (`uv lock` may add only `pypdf`), implements
  section C as amended in one commit `P4.2: ingest`, mutant table (34) in the Session log,
  PLAN.md not ticked.
- **2026-11-23: `P4.2: ingest` pre-edit summary reviewed; answers DRAFT** in
  `docs/plans/P4.md` section C, "Pre-edit answers". Cursor's claims hold (re-checked, five
  probes; suite 711 passed, 4 skipped). Accepted with changes: one guarded delete pass (as
  proposed, a missing root would have deleted every row), stored path not lower-cased,
  chunker handles code fences, `#tags` and CRLF, `exclude` validated, encrypted PDFs skipped
  without decrypting; tests 2, 7, 9, 10, 11, 15 amended, 16 new. Waiting on Karthik:
  approve; `reset-documents` in this commit (recommended yes); rows of now-skipped files
  deleted (recommended yes); go for the `pypdf` download. Nothing built.
- **2026-11-23: Section C prompt prepared; 12 open points for its pre-edit** (Session log).
  Cursor's pre-edit summary for `P4.2: ingest` must answer them; Karthik decides. Nothing
  built.
- **2026-11-23: `P4.2: embeddings` ACCEPTED** (Claude Code review of `a574df5`). Files are
  the six planned; `uv.lock` adds numpy only as a direct dependency, no version moved.
  Re-run from PowerShell: embed file 7 passed; full suite 711 passed, 4 skipped (matches).
  12 mutants re-run (Cursor's 11, "swapped or dropped" split in two): all killed. PLAN.md
  P4.2 stays unticked: it also covers section C (`P4.2: ingest`). Note for section C:
  `documents([])` raises `AxisError`, and an empty file gives no chunks (Session log).
  Next: Cursor posts the pre-edit summary for `P4.2: ingest`.
- **2026-11-23: P4.2 done** (`P4.2: embeddings`). `memory/embed.py` posts `/api/embed`
  with `options.num_gpu` 0 and `truncate: false`, in batches of 32, loopback only, no
  proxy. `config/memory.toml` is the approved `Learning` root. `numpy>=2.3.5` is a direct
  dependency (`uv lock` added it only on the jarvis package). PowerShell
  `uv run python -m pytest`: 711 passed, 4 skipped. Embed file: 7 passed. 11 mutants
  killed; `memory/embed.py` sha256 `660723e81255...` before and after. PLAN.md not ticked.
  Next: the reviewer re-runs the suite and the mutants.
- **2026-11-23: `P4.2: embeddings` pre-edit summary answered; Karthik's go given** ("Approve
  all"). Answers are in `docs/plans/P4.md` section B, "Pre-edit answers": `config/memory.toml`
  OK; `numpy` declared in this commit (`pyproject.toml`, `uv.lock` added to the file list);
  exact allowed keys; tests 1 to 4 tightened; 11 mutants. Next: Cursor implements section B
  as amended, one commit `P4.2: embeddings`, mutant table in the Session log, PLAN.md not
  ticked.
- **2026-11-23: P4 section B plan change APPROVED** by Karthik ("Approve it"). Next: Cursor
  posts the pre-edit summary for `P4.2: embeddings` (section B plus its plan change:
  `num_gpu 0`, `truncate: false`, tests 1 and 4 extended) and waits for Karthik's go. The
  new `config/memory.toml` needs Karthik's OK in that summary.
- **2026-11-23: P4 section B re-measured: PASSED.** Karthik set
  `OLLAMA_MAX_LOADED_MODELS=2` (option (a)). With CPU embeds both models stay loaded, the
  chat model does not reload (0.02 s), VRAM unchanged; 1 chunk 0.18 s, 32 chunks 5.4 s;
  `truncate: false` refuses a too-long input with HTTP 400. Section B plan change
  (`num_gpu 0`, `truncate: false`, two test additions) is DRAFT in `docs/plans/P4.md`.
  Next: Karthik approves it; then Cursor posts the pre-edit summary for
  `P4.2: embeddings` (which also needs his OK on the new `config/memory.toml`).
- **2026-11-23: P4 section B measured; BLOCKED on an Ollama setting.** Karthik pulled
  `nomic-embed-text`. Every embed evicts `qwen3.5:4b`, on GPU and on CPU (`num_gpu 0`),
  because Karthik's user environment has `OLLAMA_MAX_LOADED_MODELS=1`; the chat model
  then reloads in 6.5-6.8 s. The plan's CPU fallback does not fix that. Numbers in the
  Session log; decision under Open questions. Section B code waits for Karthik's answer
  and one re-measure.
- **2026-11-23: P4.1b ACCEPTED and ticked** (Claude Code review of `6c713b0`). Test 12
  re-run: 5 of 5 pass on the real code; second `user_version` read removed: killed 5 of
  5 (`table meta already exists`). PowerShell `uv run python -m pytest`: 704 passed,
  4 skipped (matches). `memory/store.py` sha256 `821af9a32c96...` unchanged. Next: P4
  section B, which waits on Karthik (`ollama pull nomic-embed-text` and the measurement
  in `docs/plans/P4.md`). Section C stays blocked behind B.
- **2026-11-23: P4.1b test 12 done** (`P4.1b: re-read test`). A raw connection holds
  `BEGIN IMMEDIATE` on a new file at `user_version` 0; `connect` waits in its own
  `BEGIN IMMEDIATE`; the holder then commits the schema. PowerShell
  `uv run python -m pytest`: 704 passed, 4 skipped. Memory file: 25 passed.
  Second `user_version` read removed: killed by test 12, 5 of 5 (Session log).
  PLAN.md not ticked. Next: the reviewer re-runs test 12 and that mutant. Section B
  still waits on Karthik (`ollama pull nomic-embed-text` and the measurement).
- **2026-11-23: P4.1b done** (`P4.1b: atomic schema`). The first create is one
  transaction: `BEGIN IMMEDIATE`, the DDL, then `user_version = 1`.
  `PRAGMA journal_mode = WAL` retries on `locked` (sleep 0.05 s, 100 tries).
  The create error path uses `conn.rollback()`. PowerShell
  `uv run python -m pytest`: 703 passed, 4 skipped. Memory file: 24 passed.
  Mutants: 2 killed, the second `user_version` read is flaky (Session log).
  "`user_version = 1` moved before the DDL" not run, equivalent. PLAN.md not
  ticked. Next: P4 section B, which waits on Karthik
  (`ollama pull nomic-embed-text` and the measurement).
- **2026-11-23: P4.1 done** (`0092131`, `P4.1: memory schema`). `memory/store.py` creates
  the section A schema and the role authorizer. `propose` does not commit; the caller
  owns the transaction. UPDATE on `documents` is refused for ingest. Tests after the
  commit: 701 passed, 4 skipped. 7 mutants killed (baseline 22; Session log). PLAN.md
  not ticked. Next: P4 section B, and that waits on Karthik (`ollama pull nomic-embed-text`
  and the measurement in `docs/plans/P4.md`) before anything is built on the model.
  `memory.db` is not `protect()`-ed in this commit; section D is where the bridge first
  opens it.
- **2026-11-23: P3 CLOSED.** P3.6 manual steps 1 and 2 re-run on `4fc949e` passed
  (Session log); P3.6 ticked in PLAN.md. Every P3 task is ticked and the P3 "Done when"
  passed 2026-11-18. Next: P4 section A (`P4.1: memory schema`): the implementer runs the
  `docs/plans/P4.md` verify list (FTS5 on the venv's SQLite 3.49.1), posts the pre-edit
  summary, and waits for Karthik's go. Section B needs Karthik first
  (`ollama pull nomic-embed-text` and the measurement). Tests: 679 passed, 4 skipped.
  The history below is kept as it was written.
  2026-11-23: P4.1 DONE (`0092131`, Cursor) and reviewed by Claude Code: ACCEPTED with
  one finding, ticked. 701 passed, 4 skipped; 7 mutants killed. Finding: the first create
  of `memory.db` is not atomic -> P4.1b, `docs/plans/P4.md` section A2, APPROVED by
  Karthik 2026-11-23; lands before section C. Next: Cursor posts the pre-edit summary
  for `P4.1b: atomic schema` and waits for Karthik's go. Separately Karthik runs `ollama pull nomic-embed-text` plus the section B measurement.
- Active phase (history): P3 (Windows control tools). P3.1 done 2026-11-13. P3.1b done 2026-11-13
  (plan `docs/plans/P3.1b.md`, three commits, ticked in PLAN.md): A `POST /outcome`
  answers through `encoded()`, so a lone surrogate in a result no longer gives 500;
  B `read_text_file` refuses a file with `st_nlink != 1` via `_single_name(fd)` in
  `bridge/tools.py` (rule 7 in `docs/plans/P3.2.md`); C the built-in tools guard scans
  `core/` and `evals/` recursively and refuses `**` keyword unpacking in any call; PLAN.md
  P3.5 now carries the runtime tools guard. P3.2 in progress (plan
  `docs/plans/P3.2.md`): commit A done (`create_folder` runs for real: `os.mkdir`, then an
  undo record; an unrecorded folder is left and the call fails; `tools.mutating(undo_log)`
  wired into `create_app` when `handlers is None`); commit B done (`rename_file`
  via shared `_move`: `lstat` must say plain file, `os.rename` to the policy's `target`,
  then an undo `moved` record; an unrecorded move is renamed back and the call fails).
  Commit C done (`move_file` via the same `_move`, `source` -> the policy's `target`
  inside `destination`). Commit D done (`open_app`: new `config/apps.toml`, approved by
  Karthik; `tools.load_commands` stops the bridge on a bad entry; handler runs the fixed
  command with `shell=False` and DEVNULL handles, model supplies only the name; no undo
  record). Commit E done (`focus_window`: topmost taskbar window whose title contains the
  text or whose app name without `.exe` equals it; restores a minimised window; fails
  if Windows refuses; result `{"focused": True}` only, no title). 480 passed, 3 skipped
  (a skip: symlink test, account cannot create symlinks). Manual check done 2026-11-13:
  `open_app` works, `focus_window` is refused by Windows (Open questions). Was pending: manual
  checks through a running bridge ("open notepad", then focus it). Commit F
  (`move_files`, `docs/plans/P3.2.md` "Section F"): F1 done (`P3.2: move_files policy`:
  `MAX_BATCH = 20`, `Rule.list_params`, `_resolve_batch` checks every source and every
  landing, refuses duplicates and a source already in the destination; recheck compares
  whole tuples; stub `move_files` plus eval case t24; 509 passed, 3 skipped; 8 mutants
  killed; evals 41/41). F2 done (`P3.2: move_files`: handler checks the destination is
  a real folder, every source a plain file, every landing free, before the first move;
  a failure part-way stops with `complete: False`, nothing moved back; one undo record
  per file; `GET /pending` lists every source and landing). 518 passed, 3 skipped.
  P3.2 COMPLETE, ticked in PLAN.md, plan marked Implemented. P3.2b DONE 2026-11-14
  (`docs/plans/P3.2b.md`, one commit): `focus_window` calls `_to_front`, which attaches to
  the foreground thread when the plain call is refused, skips a hung window, always
  detaches, and returns success only when `GetForegroundWindow` is that window. 527 passed,
  3 skipped. 8 mutants killed (baseline 21). Manual check 2026-11-14 FAILED, but on timing,
  not refusal: `SetForegroundWindow` returned 1, `GetForegroundWindow` read `None` during the
  activation handoff, so `_to_front` returned False; Notepad was in front 25 ms later.
  P3.2c planned and approved 2026-11-14 (`docs/plans/P3.2c.md`). P3.2c DONE 2026-11-14
  (one commit): `_settled` polls `GetForegroundWindow` every 10 ms for up to 250 ms after
  each focus call, and `front` is read only after that wait returns false. 532 passed,
  3 skipped. 6 mutants killed (baseline 26). Manual check 2026-11-14 through a running
  bridge: covered Notepad FAIL (`OSError` 518 ms after `allow`: both waits timed out, a
  genuine refusal; the attach route has never worked through the bridge); minimised
  Notepad PASS (`focused: true`, 228 ms: `ShowWindow(SW_RESTORE)` lands past the lock).
  P3.2d DONE 2026-11-14 (`docs/plans/P3.2d.md`, one commit): when the plain call does
  not land, `_to_front` minimises then restores and waits up to 500 ms. The attach route
  is removed. 526 passed, 3 skipped. 7 mutants killed (baseline 20). Test 5 replaced in
  implementation (a minimised window lands on the first restore). Manual check 2026-11-14
  by Karthik through a running bridge: covered PASS (327 ms), minimised PASS (123 ms),
  maximised-and-covered PASS (563 ms, Notepad came back maximised). `focus_window` works
  from a background bridge. Reviewed by Claude Code: PASS. P3.3 section A DONE
  2026-11-15 (`docs/plans/P3.3.md`, commit `P3.3: delete_file`): `delete_file` inside
  `mutating()` checks `os.lstat` for a plain file and moves it with
  `UndoLog.quarantine` (nothing is unlinked). Result `{"deleted": True, "undo_id"}`.
  534 passed, 3 skipped. 5 mutants killed (baseline 8). The `stat` mutant is killed by
  an lstat stand-in, approved by Karthik 2026-11-15. P3.3 section B DONE 2026-11-15
  (commit `P3.3: scripts.toml`): `config/scripts.toml` placeholders, `_checked_command`
  shared with `load_commands`, `load_scripts` (`Script` of command, cwd, timeout),
  `create_app` passes the dict into `mutating`, and `run_named_script` taints.
  549 passed, 3 skipped. 6 mutants killed (baseline 16). P3.3 section C DONE
  2026-11-15 (commit `P3.3: run_named_script`): `run_named_script` inside `mutating()`
  runs the entry's fixed argv with `shell=False`, the entry's `cwd` and `timeout`,
  and returns the last 4096 characters. A timeout is a result (`exit_code` null),
  not a tool failure. No undo record. 557 passed, 3 skipped. 7 mutants killed.
  P3.3 ticked in PLAN.md. Claude Code reviewed A, B and C: accepted. Manual check by
  Karthik PASSED 2026-11-15 through a running bridge (delete to quarantine and undo,
  `run_tests` run, `cmd` refused; audit lines in the Session log). P3.3 is DONE.
  `C:\JarvisSandbox` now exists (created by Karthik 2026-11-15). P3.4 planned and
  approved 2026-11-15 (`docs/plans/P3.4.md`): new T1 tool `open_in_app(app, path)`,
  `Rule.opens` so the root may be opened, `apps.toml` `accepts`, eval case t25. Section A
  DONE 2026-11-15 (commit `P3.4: open_in_app policy`): `Rule.opens` (last field, so
  positional `Rule` calls stay valid), `_resolve` skips the root check when `opens` is
  set, stub plus eval case t25. 577 passed, 3 skipped. 5 mutants killed (baseline 6).
  Section A reviewed and accepted. Section B DONE 2026-11-15 (commit `P3.4: open_in_app`):
  `config/apps.toml` `accepts`, `App` / `load_apps`, `open_in_app` handler (`lstat`,
  reparse tag, path as one argv item after the fixed command). `create_app` keeps the
  policy name set in `apps` and passes `app_entries`. 589 passed, 4 skipped (the new
  skip is the symlink half; this account cannot create one; the junction half runs
  first). 8 mutants killed (baseline 5 passed, 1 skipped). P3.4 ticked in PLAN.md.
  Section B reviewed and accepted by Claude Code 2026-11-15 (suite re-run in PowerShell:
  589 passed, 4 skipped; the 8 mutants re-run: all killed). Manual check by Karthik
  PASSED 2026-11-15 through a running bridge on `37cfde7` (five `Jtool` calls; audit
  lines in the Session log). P3.4 is DONE. P3.5 planned and approved 2026-11-15
  (`docs/plans/P3.5.md`, docs only, no code): core builds `OrchestratorAgent` with one
  `BridgeTool` per `TOOLS` entry, stdlib `urllib` client, runtime guard before every
  request, `fresh` is the caller's statement, `evals/run.py --real`. Three commits, a go
  per commit: A `P3.5: bridge client`, B `P3.5: core agent`, C `P3.5: real evals`
  (adds `get_time` to the bridge). Section A DONE 2026-11-15 (commit `P3.5: bridge client`):
  `core/specs.py` holds the moved tool schemas, `core/bridge_client.py` is the stdlib
  urllib client (loopback only, no-proxy opener, no retries). 596 passed, 4 skipped.
  7 mutants killed (baseline 7 passed). Section A reviewed and ACCEPTED by Claude Code
  2026-11-15 (suite and mutants re-run, same results). Section B DONE 2026-11-15
  (commit `P3.5: core agent`): `core/tools.py` `BridgeTool` and `core/agent.py` `Core`
  build `OrchestratorAgent` (`parallel_tools` false, `max_turns` `MAX_CALLS + 1`,
  `before_tool_call` records calls, the guard reads `self._agent._tools`). The fast path
  calls `BridgeTool.call(args)`. 611 passed, 4 skipped. 11 mutants killed (baseline 22
  passed; `parallel_tools` left true killed on 3 of 3 runs). Section B reviewed and
  ACCEPTED by Claude Code 2026-11-15 (suite and mutants re-run, same results). Section C
  DONE 2026-11-15 (commit `P3.5: real evals`): `get_time` in `bridge/tools.py` returns
  `{"time": <iso8601 with offset>}` and takes no arguments; `core/__main__.py` is the
  CLI (`URLError` prints `bridge is not running` and exits 1); `build()` takes `router`;
  `evals/run.py --real` builds the core once (`--no-router` passes `router=None`).
  614 passed, 4 skipped. No mutant table. `--real` was not run. Stub evals 41/42
  twice; Karthik accepted that (t24, not a flake, not caused by section C; Eval results
  and Open questions). Section C reviewed and ACCEPTED by Claude Code 2026-11-16 (suite
  re-run: 614 passed, 4 skipped). Manual check 2026-11-16 (Karthik): steps 1 and 3 pass,
  step 2 (P3 "Done when") fails on model behaviour, `--real` 41/42. Karthik PASSED P3.5
  with step 2 as a follow-up; P3.5 ticked in PLAN.md. The P3 "Done when" is NOT met yet.
  P3.5b planned and APPROVED by Karthik 2026-11-16 (`docs/plans/P3.5b.md`, two commits:
  A sort eval, B multi-step prompt). Section A DONE 2026-11-16 (commit `P3.5b: sort eval`):
  the `list_dir` stub returns four files, `also` folds into `passed`, each row carries a
  `fast` bool, and `--real --model` is refused before any case loads. 619 passed, 4 skipped.
  Stub evals 41/43 twice (t26 FAIL as expected; t24 the only other miss; t06 and t07 still
  ok). P3.5b is not ticked. Section A reviewed and ACCEPTED by Claude Code 2026-11-16
  (suite re-run: 619 passed, 4 skipped). Section B DONE 2026-11-16 (commit
  `P3.5b: multi-step prompt`): rules 5 and 6 only. Variant 3 accepted on two runs
  (t26 ok, refusals 10/10, clarify 5/5, all 43/43 both times). Variants 1 and 2
  rejected (Session log); variant 4 (rule 5 without the quoted a05 sentence) rejected,
  a05 fails without it (Open questions). Section B reviewed and ACCEPTED by Claude Code
  2026-11-16 as variant 3, overfit on a05 noted. Manual check PASSED 2026-11-18 (approvals
  made by a polling script, not by hand; Session log). P3.5b ticked in PLAN.md.
  Next: P3.6 (task lifecycle). Plan APPROVED by Karthik 2026-11-20, D1 to D3 as
  recommended (`docs/plans/P3.6.md`): Cursor implements A, B, C, one reviewed commit
  each. Section A DONE (commit `P3.6: evict tasks`): `/task` expires, then evicts tasks
  older than `KEEP` (`2 * MAX_SECONDS`) and their outcomes; a stopped task's queued
  action leaves as `cancelled`; `/approve` answers 410 `Pending action expired` if the
  task was evicted after take, and stores no outcome. 649 passed, 4 skipped. 6 mutants
  killed (baseline 10); one row not run, equivalent. Stub evals 43/43. PLAN.md not
  ticked. Section A reviewed by Claude Code 2026-11-20: ACCEPTED (Session log). Section B
  DONE (commit `P3.6: end route`): `POST /end` stops that one task, drops its queued
  action as `cancelled` on the `end` line, and does not latch; `evict()` removes with
  `pop(key, None)`. 658 passed, 4 skipped. 6 mutants killed (baseline 10). PLAN.md not
  ticked. Section B reviewed by Claude Code 2026-11-20: ACCEPTED (Session log). Section C
  DONE (commit `P3.6: core ends task`): `BridgeClient.end` posts `/end`. After `new_task`,
  `Core.handle` runs in `try`/`finally` and `_end` swallows `OSError` only. 676 passed,
  4 skipped. 5 mutants killed (baseline 9). Stub evals 43/43. PLAN.md not ticked.
  Section C reviewed by Claude Code 2026-11-20: ACCEPTED (Session log). Manual check
  2026-11-20 on `f6f0526`: steps 1, 3, 4 PASSED, step 2 FAILED (Ctrl+C did not cancel the
  pending action until the 120 s expiry). Section D DONE (commit `P3.6: Ctrl+C ends the
  task`): the CLI runs `handle` on a daemon thread and waits in `join(0.2)` steps;
  `KeyboardInterrupt` calls `Core.cancel()`, prints `cancelled`, and exits 1. 679 passed,
  4 skipped. 5 mutants killed (baseline 3); the `daemon=False` row was not run. PLAN.md
  not ticked. Section D reviewed by Claude Code 2026-11-21: ACCEPTED (Session log).
  Next: Karthik re-runs manual steps 1 and 2, then the reviewer ticks P3.6 (closes P3).
  P3 phase review 2026-11-18: PASS
  WITH FIXES, three Important findings (Session log). P3.7 plan APPROVED by Karthik
  2026-11-18 with changes (`docs/plans/P3.7.md`): A Explorer comma
  rule, B guard checks the executor, B2 `recall_memory` hidden until P4, C script runs in a
  Job Object with `KILL_ON_JOB_CLOSE`, D undo keeps a non-empty folder, E client errors
  (Karthik writes it), G core prints tool status; F (rename retry) cut. A, B, B2 before P4.
  Explorer probe on KK_19: comma splits (finding 1 stays Important); semicolon does not,
  and `;` stays in the rule. Section A DONE (commit `P3.7: open_in_app refuses commas`):
  `open_in_app` refuses a resolved path containing `,` or `;` before anything is queued.
  624 passed, 4 skipped. 5 mutants killed (baseline 5). PLAN.md not ticked. Section A
  reviewed by Claude Code 2026-11-18: ACCEPTED (suite and mutants re-run, Session log).
  Section B DONE (commit `P3.7: guard checks the executor`): `_guard` also checks
  `self._agent._executor._tools` by identity (`is`). 627 passed, 4 skipped. 3 mutants
  killed (baseline 3). PLAN.md not ticked. Section B reviewed by Claude Code 2026-11-18:
  ACCEPTED (suite and mutants re-run, Session log). Section B2 DONE (commit
  `P3.7: hide recall_memory until P4`): `HIDDEN` is `recall_memory`, `bridge_tools` skips
  it, and `_guard` compares the list and the executor with `set(TOOLS) - HIDDEN`.
  631 passed, 4 skipped. 4 mutants killed (baseline 4). PLAN.md not ticked. Section B2
  reviewed by Claude Code 2026-11-18: ACCEPTED (Session log). Section C DONE (commit
  `P3.7: script runs in a job`): `run_named_script` runs in a Job Object with
  `KILL_ON_JOB_CLOSE`, and `TerminateJobObject` still runs after every exit. 634 passed,
  4 skipped. 10 mutants killed (baseline 12); one row not run, equivalent. PLAN.md not
  ticked. Section C reviewed by Claude Code 2026-11-18: ACCEPTED (Session log). Section D
  DONE (commit `P3.7: undo keeps a non-empty folder`): a created folder that still holds
  anything is refused before quarantine, and the record stays not undone. 636 passed,
  4 skipped. No mutant table. PLAN.md not ticked. Section D reviewed by Claude Code
  2026-11-18: ACCEPTED (Session log). Section G DONE (commit `P3.7: core prints tool
  status`): `Core.handle` keeps the last request's tool results, and the CLI prints
  one status line under the unchanged reply. 639 passed, 4 skipped. No mutant table.
  PLAN.md not ticked. E is Karthik's and does not block review of G. Section G reviewed by
  Claude Code 2026-11-19: ACCEPTED (Session log; its reset-test gap deferred to P5.1, Decisions 2026-11-20).
  Section A manual check 2026-11-20: PASSED (Session log); both probe folders removed.
  Section E DONE (commit `P3.7: client survives odd answers`; Cursor, reassigned by
  Karthik 2026-11-20): `_post` parses the success body and the `HTTPError` body through
  one helper. A body that is not a JSON object comes back as 502
  `bad answer from bridge (<status>)` with the original status. An empty body stays
  `(200, {})`. The CLI keeps `bridge is not running` for `URLError`, then prints one
  `bridge error: ...` line and exits 1 for `OSError` and `BridgeError`. 667 passed,
  4 skipped. No mutant table. PLAN.md not ticked. Next: Claude Code reviews E. P3.6
  section C is unblocked after that review.
  Section E reviewed by Claude Code 2026-11-20: ACCEPTED (Session log). P3.7 ticked in
  PLAN.md. P3 closes when P3.6 D lands and manual steps 1 and 2 pass again.
  P3.6 verify list rewritten for C on `6628533` (Karthik's OK); C tests 8 and 9 added.
  Plans for P3.6 and P4 to P8 were written ahead on 2026-11-16 (`docs/plans/P3.6.md`,
  `P4.md` to `P8.md`): all DRAFT, none approved, no code. They do not change what is next.
  `docs/plans/P4.md` updated 2026-11-21 by Claude Code: hybrid search (D9), FTS5 tables
  and authorizer rules 24 to 26, vector-vs-hybrid measurement and exact-term questions in
  section G, two new section G levers, review checks for every P4 commit. Ideas from
  awesome-llm-apps; no code. P4 plan APPROVED by Karthik 2026-11-21, D1 to D9 as
  recommended (PLAN.md says approved, nothing ticked). P4 does not start until P3 closes:
  the plan's first verify line needs P3.6 ticked.
  P0 and P1 are complete, every task ticked in PLAN.md.
- P3 "Done when": PASSED 2026-11-18, accepted by Karthik (task `4e5b3c13…`, 6 of 8
  calls, one task id, undo restored `downloads`). The four approvals were made by a script
  polling `/pending` with the ui token, not read by a person. P3 stays open for P3.6.
- Phase gate P0: PASSED 2026-11-11. Karthik reported `OK` with Wi-Fi off. Separately, Claude
  Code ran `core/hello_tool.py` with every non-loopback socket connect and DNS lookup blocked
  inside the Python process: `OK`, zero outbound attempts. Limit of that second check: it
  covers the Python process only, not Ollama's own process.
- Phase gate P2: PASSED 2026-11-12, closed by Karthik after a review of
  `git diff bdc6241..HEAD` (Fable 5.2, same session as the implementation: PASS WITH
  NOTES, no blockers; mutation checks were not repeated in the review). 259 passed,
  1 skipped. Notes are under Open questions.
- Phase gate P1: PASSED 2026-11-11, closed by Karthik. Tool selection 25/25 (need >= 90%),
  must-refuse 10/10, median latency 1.0 s (targets 3 s / 5 s), and the full eval run repeated
  with non-loopback sockets and DNS blocked in the Python process: same 39/40, zero outbound
  attempts. Not done with real Wi-Fi off by Karthik for P1. 9b comparison skipped by Karthik.
- Last completed task: P2.7 (policy lock, Stop vs queue race, traversal and token sweeps;
  plan `docs/plans/P2.7.md`, implemented in three commits). `Policy.check`, `recheck` and
  `record` each run whole under one lock; `/tool` cancels an action Stop overtook on its way
  into the queue; sweeps prove every route needs a loopback peer and a valid token, and
  every path parameter of every tool is refused for `..`, absolute outside, junction, UNC
  and protected folder. Bridge routes are unchanged since P2.6: `GET /health`;
  core: `POST /task`, `POST /tool`, `POST /outcome`; ui only: `GET /pending`,
  `POST /approve`, `POST /deny`, `GET /undo`, `POST /undo`; both: `POST /stop`.
  (P2.8 C: `POST /task` now takes an optional body `{"fresh_context": true}`.
  P2.8 D: new ui-only route `POST /resume`.)
- Last hardening task: P2.8 DONE 2026-11-12 (plan `docs/plans/P2.8.md`, six commits A to F,
  ticked in PLAN.md). What changed, in one place:
  A path rules: a drive with no root is refused before `realpath`; T1/T2 tools and undo
  cannot touch the root itself or a folder that contains a protected folder; a rename's
  landing place is checked and handed to the handler as `target`.
  B argument rules: every rule declares its arguments, anything else is refused;
  `open_app` / `run_named_script` values must be names in `config/apps.toml` /
  `config/scripts.toml` (neither exists yet: both tools refuse everything until P3.2 /
  P3.3); `focus_window` and `recall_memory` take one short printable string.
  C taint: `list_dir`, `list_windows`, `recall_memory` taint; new tasks inherit taint until
  the core sends `{"fresh_context": true}` on `POST /task` or the bridge restarts.
  D stop latch: a hotkey or ui Stop latches until ui-only `POST /resume`; a core Stop does
  not latch.
  E a configured hotkey whose listener is not alive stops everything (503); audit file and
  tool results survive a lone surrogate.
  F tests only: built-in tools guard (`tests/test_core_tools.py`), duplicate token and Host
  headers, wrong-role sweep, non-string path parameters.
- P2.8 reviewed 2026-11-12 (Fable 5.2, read-only, adversarial): no way found outside the
  roots, without a token, or to a T2 action without a click; seven smaller gaps R1–R7 found
  and planned as P2.9 (`docs/plans/P2.9.md`, docs only, no code yet).
- P2.9 commit A DONE 2026-11-12 (`P2.9: taint fails closed`): a taint now reaches every
  live task, and the bridge starts tainted, so the core's first task after any start must
  send `{"fresh_context": true}` (P3.5 requirement, unchanged).
- P2.9 commit B DONE 2026-11-12 (`P2.9: move landing place`): `move_file` gets a checked
  `target` (destination folder / source name); the root is now a valid destination folder;
  names and paths refuse unprintable and wildcard characters; `COM¹`–`LPT³` reserved.
  P3.2's `move_file` handler must move `source` to `target` and never build a path.
- P2.9 commit C DONE 2026-11-12 (`P2.9: odd names and results`): undo records are
  ASCII-escaped JSON; `GET /pending` and `GET /undo` answer ASCII-escaped JSON; a result
  that cannot be encoded is logged and answered as `failed`; any audit write error fails
  closed. Red run on 6 tests, then green. Mutation checks done 2026-11-13: 5 mutants
  (one per fix), each killed by at least one C test; table in `docs/plans/P2.9.md`.
- P2.9 commit D DONE 2026-11-13 (`P2.9: stop race`): a task created while a latching Stop
  runs is marked stopped and answered 403 `stopped`; the clarify scorer accepts a fixed
  ask-phrase as well as `?`. P2.9 is complete and ticked in PLAN.md.
- P3.1 commit A DONE 2026-11-13 (`P3.1: list_dir`): new `bridge/tools.py` with the real
  `list_dir` (links reported as `link`, never followed; 200-entry cap; folders first) and
  `HANDLERS`; `create_app(handlers=None)` now uses `tools.HANDLERS` (production). Tests in
  `tests/test_tools.py` (incl. `assert_plain`, taint -> 202).
- P3.1 commit B DONE 2026-11-13 (`P3.1: read_text_file`): 16 KiB cap (`truncated`,
  `bytes` = file size); NUL byte = binary, refused; UTF-8 with BOM stripped, bad bytes
  replaced; after opening, the handle's final path must equal the checked path, so a
  link is never read through.
- P3.1 commit C DONE 2026-11-13 (`P3.1: list_windows`): visible, titled, unowned
  top-level windows (ctypes `EnumWindows`); `{"title", "pid", "app"}`, titles cut to 200
  characters, 50-window cap, no window handles.
- P3.1 commit D DONE 2026-11-13 (`P3.1: system_stats`): CPU % from two `GetSystemTimes`
  samples 0.2 s apart; RAM from `GlobalMemoryStatusEx`; GPU from
  `C:\Windows\System32\nvidia-smi.exe` (fixed arguments, no shell, 2 s timeout), `gpu: null`
  if it fails. P3.1 is complete and ticked in PLAN.md. All four T0 tools now run for real
  through `bridge/tools.py` `HANDLERS`.
- P3.2 planned and approved by Karthik 2026-11-13 (`docs/plans/P3.2.md`, docs only, no
  code). Implement with Opus 5.5. Six commits, a go per commit: A `create_folder`,
  B `rename_file`, C `move_file`, D `open_app` (+ `config/apps.toml`, Karthik approves the
  file), E `focus_window`, F `move_files` (batch; own detailed plan first, it changes
  `safety/`). Decisions: batch is a new tool built last; `open_app` / `focus_window` write
  no undo record; allowlist is notepad, calculator, explorer, vscode (no browser).
- Reviewed 2026-11-13 (Opus 5.5, read-only, adversarial, `git diff 1d341fd..HEAD -- safety
  bridge` plus tests; probes and the red run in a scratch folder, nothing committed): no
  way found outside the roots, without a token, or to a T2 action without a click. P2.8
  commit B's tests fail on behaviour against the pre-B code (33 of 34; the 34th is the
  stub-name drift check). Three gaps: G1 `POST /outcome` answers 500 when a result holds
  a lone surrogate; G2 `read_text_file` reads a hard link inside the root whose other name
  is outside it; G3 the built-in tools guard scans only the top level of `core/` and
  `evals/` and misses `**` unpacking. Evals `--only a` -> 5/5.
- P3.1b planned and approved by Karthik 2026-11-13 (`docs/plans/P3.1b.md`, docs only, no
  code). Implement with Opus 5.5. Three commits, a go per commit: A `/outcome` uses
  `encoded()`; B `_single_name(fd)` in `bridge/tools.py` refuses `st_nlink != 1`, and
  becomes a rule for every handler that opens content (no P3.2 handler does; table in the
  plan; rule 7 added to `docs/plans/P3.2.md` in that commit); C tests only: `rglob` and
  no `**` in calls, plus the P3.5 runtime-guard requirement in PLAN.md.
- Next task: P3.1b commit A (`P3.1b: outcome survives odd results`) on Karthik's go, then
  B and C. After P3.1b: P3.2 commit A (`P3.2: create_folder`, which also adds the
  `tools.mutating(undo_log, commands)` wiring in `create_app`) on Karthik's go.
  `C:\JarvisSandbox` is still not created: ask Karthik before any manual check. Audit points 3, 4, 5, 6
  stay open.
- Checked by Karthik 2026-11-13: a real `Ctrl+Alt+End` press against a running bridge
  stopped it (reported by Karthik; the audit line itself was not re-read by an agent).
- Windows restore point created by Karthik 2026-11-13 (PLAN.md 4.3, the P3 precondition).
- Tests: `uv run python -m pytest` -> 423 passed, 2 skipped (2026-11-13, after P3.1 D). Both skips are symlink tests
  (bridge escape test, `read_text_file` symlink test): this account may not create symlinks. The junction test covers the
  same escape and runs. Evals:
  `uv run python evals/run.py` -> 40/40 (re-run 2026-11-13 after P2.9 D; a03 now scored as a clarification; needs Ollama, takes about 1 minute). Live smoke test:
  `uv run python core/hello_tool.py` must print `OK` (needs Ollama running)
- Uncommitted work: none. Untracked `jarvis_p35b_report.txt` in the repo root is Karthik's
  raw P3.5b report (2026-11-18), recorded in the Session log; not a cut-off task. `.claude/settings.local.json` (local agent permissions) is gitignored and left untouched.
- Blockers: none
- Run OpenJarvis with (PowerShell, from repo root; both env vars required):
  `$env:OPENJARVIS_HOME = "$PWD\.openjarvis"; $env:OPENJARVIS_CONFIG = "$PWD\core\config.toml"; uv run python -m openjarvis.cli ask --no-stream "hi"`

## Open questions for Karthik

- (Claude Code, 2026-11-23, P4 section B measurement) RESOLVED 2026-11-23: Karthik chose
  (a); re-measure passed (Session log). Kept as written:
  Your user environment sets `OLLAMA_MAX_LOADED_MODELS=1` (also `OLLAMA_NUM_PARALLEL=1`,
  `OLLAMA_KEEP_ALIVE=5m`); nothing in this repo set them. With one model allowed, every
  embed call unloads the chat model, on GPU or CPU. Ingest (a batch CLI) could live with
  that. `recall_memory` cannot: each recall inside a chat task would cost the embedder
  load (1.9 s CPU) plus the chat reload (6.5 s).
  (a) Recommended: set `OLLAMA_MAX_LOADED_MODELS=2` (you change it, then restart Ollama)
  and embed on CPU (`num_gpu 0`). The chat model keeps the GPU; the embedder takes about
  0.36 GB RAM and no VRAM. Query 0.2 s; ingest about 0.18 s per 1000-character chunk.
  Then one re-measure to confirm nothing is evicted.
  (b) Same setting, embed on GPU: 32 chunks in 0.6 s, but VRAM goes to about 5.6 of
  6.0 GB (chat alone: 5.2 GB used), little room for anything else on screen.
  (c) Keep the setting, accept the eviction. Fine for ingest, too slow for recall.
  Was `=1` set on purpose (for example to stop `9b` and `4b` sharing VRAM)? With `=2`,
  Ollama still unloads a model when VRAM is short; the setting is a cap, not a force.

- (Claude Code, 2026-11-18, from the P3.5b manual check)
  (1) The model's final reply can claim work that failed. Run 1 (task `f87865b3…`): the
  first `create_folder` expired, the second was refused (`time budget exceeded`), and the
  reply said "I created two folders". Proposal: the core prints each tool's real status
  itself, so the screen (and later the voice reply) does not rest on the model's sentence.
  (2) Four hand approvals inside the 120 s task budget did not fit through a terminal
  (18 s and 46 s per approval; the third expired). Input for the P6 approval dialog, or for
  the time budget value.
  (3) An approval script with the ui token turns every confirm into an allow. Fine once in
  the sandbox; not for real use. P6 keeps the ui token out of scriptable reach.

- (Claude Code, 2026-11-16, from the plans written ahead; none decided, none blocks P3)
  (1) Smart App Control blocks unsigned `.exe` files, and a Tauri build is one. P6 may
  need a signing certificate or a different shell (`docs/plans/P6.md` D1). Cheap to find
  out early: a ten-minute Tauri hello-world.
  (2) PLAN.md P7.3 (a browser) and the hard rule "no outbound network calls, localhost
  only" disagree. Proposal: browser tools limited to localhost origins in v1
  (`docs/plans/P7.md` D7).
  (3) Proposal to change phase order: do P8.3 (gate script + permanent offline test) and
  the model-free layer of P8.4 (injection matrix against the bridge) right after P3
  closes, not last (`docs/plans/P8.md` D1).
  (4) With crash restart (P8.1), a latched Stop is lost when the bridge restarts.
  Proposal: keep the latch in a file (`docs/plans/P8.md` D2).
  (5) A request that starts from the wake word, with no key pressed, could open a tainted
  task so its T1 actions need a click (`docs/plans/P5.md` D3). Needs a small `/task`
  change.
  (6) Docs roots for P4 as a separate `config/memory.toml` instead of read-only allowed
  roots as PLAN.md words it (`docs/plans/P4.md` D2).

- (Cursor, 2026-11-16) Rule 5 quotes eval case a05 verbatim; clarify 5/5 is not a held-out
  result. The 4b model needs the example. Revisit with a bigger model or a held-out
  clarify set.

- (Claude Code, 2026-11-16) P3.5 manual check follow-up, needed for the P3 "Done when":
  (1) the model never chains `list_dir` -> `create_folder` -> `move_files` for "sort ... by
  file type": it reads "sort" as "show grouped", and prompt rule 6 ("After a tool result,
  reply in one short sentence") ends the turn after the first result; rule 5 ("Never invent
  a path") may also block creating `pdf\`. Proposal: a prompt change in `core/config.toml`
  plus an eval case for the sort command. (2) t25 expects `C:\JarvisSandbox`, the model
  picks `C:\JarvisSandbox\project` (arguably right) after a tainting `list_dir`, so with
  real tools it waits for approval. Fix the case's expected path or the scorer. (3)
  `evals/run.py:144` counts the fast path by the stub reply string, so `--real` always
  prints 0 (5/42 took it). (4) `--real --model X` ignores `--model` but prints it.

- (Karthik, 2026-11-15) t24 doubled backslashes in `destination`. Options: (a) the scorer
  compares path args after `os.path.normpath`; (b) a prompt rule; (c) accept. The `--real`
  run in the P3.5 manual check shows whether the bridge accepts the path. Not part of P3.5.

- (Karthik, 2026-11-13) Should focus_window be limited to windows of allowlisted apps?
  Decide before any keyboard-input tool exists.

- (Decided 2026-11-13: option (a). Implemented 2026-11-14 as P3.2b; see Decisions.) P3.2 manual check (2026-11-13, by Karthik through a running bridge, audit lines read
  by the agent): `open_app` notepad PASS (`opened`, pid 27772, window appeared);
  `open_app` cmd PASS (403 `app: not on the allowlist`); an expired task refused
  (`time budget exceeded (120 s)`). `focus_window` notepad FAIL: the window was found,
  then `OSError: Windows refused to bring the window forward` (500 `Tool failed`).
  Cause: Windows' foreground lock; the bridge is a background process, so
  `SetForegroundWindow` is refused. The handler failed honestly (E7). Option (a) is now
  in `_to_front`. The manual re-check (covered Notepad, then minimised) is still Karthik's.
  If Windows still refuses, stop and ask. Do not add another trick.
  Re-check 2026-11-14 (Karthik, running bridge, audit read back): FAIL, `OSError` 22 ms
  after `allow`. Not a refusal: a read-only diagnosis showed `SetForegroundWindow` -> 1,
  `GetForegroundWindow` -> `None` at 0 ms, Notepad at 25 ms. (Decided 2026-11-14: wait up
  to 250 ms for the activation, planned as P3.2c; see Decisions. Karthik. Implemented
  2026-11-14 as P3.2c. The manual re-check, Notepad covered then minimised, is still
  Karthik's. If it still fails, stop and ask. Do not add another trick.)
  Re-check after P3.2c (Karthik, running bridge, audit read back): covered Notepad FAIL,
  `OSError` 518 ms after `allow` (both 250 ms waits ran out: plain call refused, attached
  call refused). Minimised Notepad PASS, `focused: true` after 228 ms: the
  `ShowWindow(SW_RESTORE)` step landed it. Probes from the planning session were discarded:
  a fresh child of the foreground window inherits the foreground right, so they do not show
  what the bridge sees. (Decided 2026-11-14: minimise + restore when the plain call does not
  land, attach removed, planned as P3.2d; see Decisions. Karthik. Implemented 2026-11-14
  as P3.2d. Manual re-check 2026-11-14, Karthik, running bridge, audit read back: covered
  PASS 327 ms, minimised PASS 123 ms, maximised-and-covered PASS 563 ms and still
  maximised. CLOSED. `AllowSetForegroundWindow` from the UI stays a fallback idea for P6
  only if a real app ever refuses the restore.)

- (Decided 2026-11-13: 41st case t24, arguments checked; see Decisions.) P3.2 F1
  (2026-11-13, Opus 5.5): plan gap, F1 stopped before commit. Adding `move_files`
  to `evals/stub_tools.py` (required by `test_tool_table_matches_eval_stubs`) fails
  `tests/test_eval_set.py::test_every_stub_tool_is_exercised`, which demands at least one
  case per stub tool in `evals/commands.yaml`. The plan's "Not in F" says "No eval case
  for batch moves yet". Options: (a) add one case to `commands.yaml`, e.g. `Move
  C:\JarvisSandbox\a.txt and C:\JarvisSandbox\b.txt to C:\JarvisSandbox\docs` -> `move_files`
  (overrides "Not in F"; the eval re-run then also scores it); (b) exempt `move_files`
  from that test until P3.5 (weakens a test); (c) other. Uncommitted F1 work in the tree:
  policy, stub, tests; 507 passed, this 1 failed. Mutants and evals not run yet.
  Karthik chose (a). Follow-up gap: `tests/test_eval_set.py::test_counts_match_plan` pins
  the set at exactly 40 cases (PLAN.md P1.2), and `evals/run.py` `_norm` loosens only
  strings, so a list of paths in `args` is compared case-sensitively. Asked: 41st case
  (count test 40 -> 41) or replace an existing case; args checked (`_norm` learns lists)
  or tool-only.

- P2.8 review (2026-11-12): fixes planned as P2.9, one go per commit. Decide when to start
  commit A. Two untracked files in the repo root, `PowerShell 5.1` and
  `oft Corporation. All rights reserved.`, hold `git diff` output and the `less` help
  screen (a mis-typed PowerShell redirect, 19:17). No secrets seen. Delete them yourself?
  The agent has not touched them.

- (Decided 2026-11-12, see Decisions and `docs/plans/P2.8.md`: all fixed in P2.8 except the
  budget reset in N5, accepted.) P2 phase review, bypass audit (2026-11-12, Fable 5.2,
  read-only; nothing fixed). All
  three P2 "Done when" criteria pass. None of the gaps below is reachable today: there
  are no real handlers. Each needs a decision (which task, or accept) before P3 handlers
  are written. N1-N5 were confirmed by calling `Policy.check` directly.
  New:
  N1 `rename_file` on the root itself is allowed (T1, auto): `path` is checked, the place
  the renamed item lands (`parent/new_name`, outside the roots) is not.
  N2 `move_file`/`rename_file` on a folder that CONTAINS a protected folder is allowed;
  the check refuses paths inside a protected folder only. Harmless with today's root;
  matters if a root is ever set above the repo or `%LOCALAPPDATA%\Jarvis`. Same for
  `delete_file` on the root itself (goes to confirm).
  N3 Unknown arguments pass through: the policy has no list of permitted argument names
  and `execute` hands every argument to the handler (`create_folder` with `overwrite=True`).
  N4 Tools without path parameters get no argument check: `open_app` (T1, auto-allowed
  with any argument), `focus_window`, `run_named_script` (any name, goes to confirm).
  `config/apps.toml` and `config/scripts.toml` are not enforced anywhere yet.
  N5 Taint and budgets reset with a new task: `POST /task` is free and unlimited, so a
  tainted task's T1 action is auto-allowed again in a fresh task, and the 8-call, 120 s
  and 3-failure budgets restart. Main way around the confirm queue for T1. Related: only
  `read_text_file` taints; `list_dir` (file names), `list_windows` (window titles) and
  `recall_memory` also return text an attacker can shape.
  N6 Stop is not sticky: `stop()` stops existing tasks only; the core can open a new task
  at once (by design today: `test_stop_stops_live_tasks_and_new_tasks_work`).
  Known or by design, listed for completeness:
  - Token: same-user processes can read both token files, so the core/ui split is a
    convention (audit point 6). Loopback bind is command-line only; a local port forward
    makes a remote caller look like 127.0.0.1 (token still needed). `protect()` finds
    `icacls`/`whoami` through `SystemRoot`, at startup. Duplicate headers: P3.0b.
  - Roots: `realpath` before the roots check (P3.0a). Check-to-handler gap on the direct
    `/tool` path: a junction swapped in after the check is caught only on approve
    (`recheck`); P3 handlers must not follow links. Hard links into the root are not seen.
  - Confirm queue: approval re-validates paths, not file contents.
  - Policy engine: `POST /undo` skips `Policy.check` (ui only; re-checks roots and
    protected). `record.json` is editable by a same-user process (inside roots only, never
    overwrites, needs a click). `UndoLog.quarantine/moved/created` trust the path given.
    A running handler is not interrupted by Stop.
  - Kill switch and audit: a dead hotkey thread is not noticed. A lone surrogate in a tool
    result makes the `result` line fail to write after the handler ran. The audit log is
    editable by a same-user process (audit point 6).
  - Outside `safety/` and `bridge/`: nothing forces the model's tools through the bridge.
    The core has no bridge client yet; OpenJarvis built-ins (`shell_exec`) are kept out
    only by the `tools=[...]` list on each call. Largest bypass; belongs to P3.5.

- P2 gate review notes (2026-11-12). (a) and (b) were PLAN.md tasks P3.0a and P3.0b and are
  now P2.8 commits A and F; nits (c) and (d) are in P2.8 F; nit (e) has no task yet.
  Should-fix, before P3.1:
  (a) `safety/policy.py` `resolve_inside`: `os.path.realpath` runs before the roots check,
  on any drive letter. A path on a mapped network drive (a `Z:` path) makes Windows contact
  that share (runtime rule: no outbound calls) and holds the global policy lock until the
  lookup returns; Stop still works. Older than P2.7. Fix: refuse a path whose drive letter
  matches no root's drive before `realpath`, with a refusal test.
  (b) No test sends two `x-jarvis-token` headers (one valid, one wrong) or two `Host`
  headers. The code refuses both (`len(...) == 1`); nothing guards it. Add to `BAD_TOKENS`.
  Nits:
  (c) Token sweep has no wrong-role case (every route x the role not in `ROUTE_ROLES`
  -> 403); role checks are per-route tests only.
  (d) `ESCAPES` has no missing-parameter or non-string case over HTTP (policy level only).
  (e) A task stopped by a budget breach keeps its pending action in the UI list until it
  expires (only `stop()` clears the queue; approve refuses it). Fix in P3.6 or P6: drop a
  stopped task's pending action in `expire()`.
  For P3: `open_app`, `focus_window`, `run_named_script` have no path parameters, so the
  path sweep does not cover them; validate their arguments against `config/apps.toml` and
  `config/scripts.toml` with refusal tests when the handlers are written.
  (`open_app`: done in P3.2 D. `run_named_script`: planned in P3.3 B and C.)

- (Resolved 2026-11-12 by Karthik at the P2 gate, P2.7 commit B test details: (1) KEEP: a
  budget breach stops the task and cancels allowed calls that have not reached their
  handler; the audit-log assertions stand. (2) OK: the race test presses Stop before the
  queue insert; `pending_id` on the `queued` line stays.)

- (Resolved in P2.4 commit A: stale timed-out pending actions now expire and free their
  slot; the `denied` vs `expired` label is fixed. Eviction of `tasks`/`outcomes` is P3.6.)

- P1 review and bridge bypass audit (2026-11-11, newest Session log entry): which of the nine
  points get fixed, and in which task? Also still owed: a real Wi-Fi-off eval run for P1.
- Keep-alive. Ollama unloads the model after 5 idle minutes; the next request then pays a
  reload (about 8 s warm disk, up to 90 s after boot). OpenJarvis's Ollama engine cannot send
  `keep_alive`. Options: (a) Karthik sets the user environment variable `OLLAMA_KEEP_ALIVE=-1`
  (holds ~3.6 GB VRAM permanently, affects all his Ollama use); (b) the long-running core
  process pings Ollama every few minutes (decide when that process exists, P2+). No action yet.
- OpenJarvis logs `Failed to set up rate limiter: No module named 'openjarvis_rust'` on every
  call. The Rust extension is not installed (needs a Rust toolchain = system install). Harmless
  so far; some features (its memory commands) need it. We do not plan to use those.
- The eval set is easy (explicit paths, one step each). Proposal: add harder cases (typos,
  indirect phrasing, multi-step, injected instructions inside file contents) before relying
  on the 100% score. Also the clarify scorer needs a `?`, which gave one false negative (a03).
- OpenJarvis core dependencies include `posthog`, `python-telegram-bot`, `ddgs`, `openai`,
  `datasets`; they cannot be dropped without forking. It also keeps a local telemetry DB
  (default on) under `.openjarvis/`. Socket-guard runs show no outbound attempts today; P4.2
  "Offline check" should turn that guard into a permanent pytest test.
- OpenJarvis already ships SQLite memory, faster-whisper STT, Kokoro TTS and a Tauri app. Reuse
  any of these, or build our own as planned? Its memory has no approval queue.
- (Resolved by P3.2 F: `move_files` moves up to 20 files in one call.)
  P3 "Done when" (sort a folder by file type) needs one `move_file` per file, which exceeds the
  8-tool-call budget for more than a few files. Batch move tool, or change the check?
- (Resolved in P2.6: the repo sits inside the Obsidian vault, and the whole repo folder is now
  a protected folder, so a vault docs root in P4.2 can never reach `safety/`, `config/` or
  any other repo file.)
- (Done 2026-11-15: Karthik created it for the P3.3 manual check.)
  `C:\JarvisSandbox` does not exist yet. Create it in P2/P3, or should Karthik create it?

## Decisions

Format: `YYYY-MM-DD — decision — reason — who`

- 2026-11-23 — `OLLAMA_MAX_LOADED_MODELS=2` in Karthik's user environment (was 1), and
  embeddings run on CPU (`num_gpu 0`) — with 1, every embed unloaded `qwen3.5:4b` (6.5 s
  reload per recall); with 2 and CPU embeds both stay loaded and VRAM does not move
  (measured, Session log). A machine setting, not repo config: nothing in the code
  checks it — Karthik (option (a)).
- 2026-11-21 — P4 plan approved, D1 to D9 as recommended: `nomic-embed-text` (measured in
  section B first; Karthik runs the pull); docs roots in `config/memory.toml`, never an
  allowed root; ingest starts with the vault's `Learning/` folder only; `remember_fact` at
  T1; review CLI opens the database directly; `task_history` created with no writer; facts
  only when the user asks; hybrid search. New dependencies (D4): `pypdf`, because PLAN.md
  P4.2 ingests PDF and it is pure Python; `numpy` declared directly, because the vector
  search uses it and it is already in the venv through OpenJarvis — Karthik.

- 2026-11-21 — P4 (still DRAFT): hybrid search is built into section D (FTS5 keyword
  ranking merged with the vector ranking by RRF, the not-found floor on the cosine), not
  kept as a section G lever (P4 D9). Section G measures it against vector-only. Embeddings
  are weak on exact names, acronyms and dates, and FTS5 ships with `sqlite3`, so no new
  dependency — Karthik ("do the recommended plan", after Claude Code's review of
  awesome-llm-apps).

- 2026-11-20 — P3.6 approved, D1 to D3 as recommended: `POST /end` and the core ends its
  task (sections B, C); no audit line for an eviction; a stopped task's pending action
  leaves the queue as `cancelled` with a new `cancelled` event. A finished request should
  not leave a usable task behind; eviction permits and prevents nothing — Karthik.

- 2026-11-20 — The test that a spoken `stop` clears `Core.results` is deferred to P5.1
  (`docs/plans/P5.md` section B, test 8), not added to P3.7 G. The CLI builds one `Core`
  per run, so stale results cannot show today; P5.1 is the first long-lived `Core` —
  Karthik.

- 2026-11-18 — `accepts` for explorer is a security boundary, together with the policy comma
  rule. Explorer launches a file it is handed, and it splits a command-line argument on
  `,`. The 2026-11-15 line that called `accepts` "not a security boundary" is corrected.
  The real `apps.toml` stays pinned by `test_real_apps_toml_loads_and_matches_the_allowlist`.
  — The probe on KK_19 opened `C:\Users` from `C:\JarvisSandbox\t,\Users`. — Karthik (P3.7 A)
- 2026-11-18 — P3.7 approved with changes: F (rename retry) cut, B2 hides `recall_memory`
  until P4, C sets `KILL_ON_JOB_CLOSE`, E written by Karthik. — F fixes an error never seen
  outside a test; a 501 tool wastes one of 8 calls; a bridge crash must not leave a
  script's tree running. — Karthik
- 2026-11-18 — Known limits, not fixed (P3.7 D7): handlers re-open a checked path by name, so
  a parent swapped to a junction between check and act escapes (needs a same-user local
  process); a part-way `move_files` counts as success, and a failed move-back inside it logs
  only the error type. Also: time spent waiting for an approval counts toward the 120 s task
  budget; decide before P6's approval dialog. — Cheap fixes would be partial; the budget is
  a design change. — Karthik (planned by Claude Code)
- 2026-11-18 — Process: a full mutant table only for changes to a safety boundary or process
  control; small fixes are tests first, then code. — Thoroughness was slowing small fixes. —
  Karthik

- 2026-11-16 — Roles are written into AGENTS.md ("Roles"): Claude Code plans and reviews,
  Cursor implements one plan section per commit, Karthik approves and does manual checks.
  The implementer never ticks a PLAN.md checkbox. No separate roles file; `CODEX_TASK.md`
  removed. — The split existed only in each plan's header; PLAN.md and PROGRESS.md stay
  the only planning files (decision of 2026-11-11). — Karthik

- 2026-11-15 — P3.5: the core builds `OrchestratorAgent` itself with `BridgeTool` objects
  and `parallel_tools=False`; it does not call the SDK's `ask_full` or register bridge tools
  in `ToolRegistry`. — `ask_full` silently drops unknown tool names, runs tool calls in
  parallel (the bridge answers 409 to a second call on one task), and never returns the
  agent, so the runtime guard could not check the real tool set. — Karthik (planned by
  Claude Code)
- 2026-11-15 — P3.5: `fresh_context` is the caller's statement (`Core.handle(text,
  fresh=True)`); the core does not detect a bridge restart and `/health` is unchanged. —
  A bridge restart does not change the model's context; a bridge starts tainted, so the
  core's next non-fresh request stays tainted (fail-closed). — Karthik (planned by Claude
  Code)
- 2026-11-15 — P3.5: core -> bridge HTTP uses stdlib `urllib`; no new dependency. Tests run
  the real bridge with uvicorn in a thread on a free loopback port. — AGENTS.md: ask before
  adding a dependency; urllib is enough for four POST routes. — Karthik (planned by Claude
  Code)
- 2026-11-15 — P3.5: `evals/run.py --real` runs the eval set through the real core and a
  running bridge; T2 cases wait for Karthik's approve or deny. The stub run stays the
  default. — PLAN.md P3.5 "rerun evals against real tools"; only the ui token may approve.
  — Karthik (planned by Claude Code)

- 2026-11-15 — P3.4: apps are driven through their command line or a documented API. UI
  automation (pywinauto, key presses, clicks) needs its own plan naming the app, what was
  tried through its CLI/API, and why that is not enough. No pywinauto dependency until then
  (rule 11 in `docs/plans/P3.4.md`). — PLAN.md P3.4; a CLI call is testable and has no
  foreground or timing problems (see P3.2b-d). — Karthik (planned by Claude Code)
- 2026-11-15 — P3.4: opening an app on a path is a new T1 tool `open_in_app(app, path)`, not
  an optional argument on `open_app`. — Every policy argument is required today; an
  optional-argument feature in `safety/` would be a bigger change for the same result. —
  Karthik (planned by Claude Code)
- 2026-11-15 — P3.4: `Rule.opens=True` lets a path that is only handed to an app be the root
  itself (still refused outside the roots and in protected folders). Only `open_in_app` has
  it. — "Open VS Code on my sandbox" names the root; nothing is changed. — Karthik (planned
  by Claude Code)
- 2026-11-15 — P3.4: `apps.toml` entries declare `accepts = file | folder | any` (vscode any,
  explorer folder, notepad file, calculator none). The handler refuses a mismatch, not the
  policy. — Not a security boundary: the policy already bounds `app` and `path`; a third
  allowlist is not worth it. (corrected, see 2026-11-18) — Karthik (planned by Claude Code)
- 2026-11-15 — P3.4: eval case t25 "Open VS Code on my sandbox project." -> `open_in_app`;
  count 41 -> 42. — `test_every_stub_tool_is_exercised` needs a case per stub tool; same as
  `move_files`. — Karthik
- 2026-11-15 — P3.4: `opens=True` skips `_refuse_mutation` entirely, so both "the root
  itself" and "contains a protected folder" are lifted for `open_in_app`. "Inside a
  protected folder" is still refused (checked before the mutating step). — Today no
  folder in `C:\JarvisSandbox` contains a protected folder (protected =
  `%LOCALAPPDATA%\Jarvis` and the repo), so nothing changes in practice. Revisit before
  adding any root that contains a protected folder. — Karthik (found in review by Claude Code)

- 2026-11-14 — P3.3: `run_named_script` waits for the script (timeout from its
  `scripts.toml` entry, 1 to 60 s, default 30), returns the exit code and the last 4096
  characters of output, and taints the task. — "Run my tests" is useless without the
  result; the output is untrusted text, so it taints like `read_text_file`. Fire-and-forget
  was the alternative. — Karthik (planned by Claude Code)
- 2026-11-14 — P3.3: `config/scripts.toml` ships `dev_server`, `run_tests`, `backup_notes`,
  each running `C:\Windows\System32\HOSTNAME.EXE` as a placeholder. — The names match the
  eval set, so it stays at 41 cases; real commands come when the sandbox project exists.
  — Karthik
- 2026-11-14 — P3.3: `delete_file` takes plain files only (`lstat`), moves them with
  `UndoLog.quarantine`, and returns the undo id. — Rule 3 of P3.2 (files only in v1) and
  "Jarvis code never permanently deletes". — Karthik (planned by Claude Code)

- 2026-11-14 — P3.2d implemented: `_to_front` tries the plain call, then
  `ShowWindow(SW_MINIMIZE)` and `ShowWindow(SW_RESTORE)`, and reports success only when
  `GetForegroundWindow` is that window within 500 ms. Attach code is gone. Test 5
  replaced in implementation: a minimised window lands on the first restore. —
  526 passed, 3 skipped; 7 mutants killed (baseline 20). Manual check still open. —
  Karthik (go), Cursor

- 2026-11-14 — P3.2d: when the plain `SetForegroundWindow` does not land, `_to_front`
  does `ShowWindow(SW_MINIMIZE)` then `ShowWindow(SW_RESTORE)` and waits (cap 500 ms).
  The `AttachThreadInput` route from P3.2b is removed, not kept as a fallback. — Through
  the bridge, the attach route was refused every time and the restore landed every time;
  `ShowWindow` needs no foreground right and touches only the target window. A route never
  seen working is dead code. Cost accepted: one flicker when the plain call is refused.
  Fallback if the restore ever fails: `AllowSetForegroundWindow` from the UI (P6). —
  Karthik (chose among minimise+restore / keep attach too / wait for P6; planned by Claude
  Code)

- 2026-11-14 — P3.2c implemented: `_to_front` waits up to 250 ms after each
  `SetForegroundWindow` for `GetForegroundWindow` to become that window. The focus
  request is still issued at most twice. `settles_after` then reveals the window the
  call actually produced. — the manual check's `None` was the activation handoff, not a
  refusal. 532 passed, 3 skipped; 6 mutants killed. — Karthik (go), Cursor

- 2026-11-14 — P3.2c: after each `SetForegroundWindow`, `_to_front` polls
  `GetForegroundWindow` every 10 ms for up to 250 ms before judging the call. — The P3.2b
  manual check showed Windows accepts the focus but the foreground reads `None` for a few ms
  during the handoff. This is not the "retries or sleeps" P3.2b excluded: the focus request
  is still issued at most twice; the wait only confirms an activation Windows accepted. —
  Karthik (planned by Claude Code)

- 2026-11-14 — P3.2b implemented: `_to_front` attaches to the foreground thread when the
  plain call is refused, skips a hung window, detaches in `finally`, and reports success
  only when `GetForegroundWindow` is that window. A raise during the attached call still
  detaches (test 9). — option (a), decided 2026-11-13; 527 passed, 3 skipped; 8 mutants
  killed. Manual check still open. — Karthik (go), Cursor

- 2026-11-13 — P3.2b: `focus_window` gets the foreground by attaching to the foreground
  thread's input (`AttachThreadInput`) when the plain call is refused; no attach if that
  window is hung (`IsHungAppWindow`); no simulated key presses, no system-setting change,
  no minimise-then-restore fallback. If Windows still refuses: stop and ask. — the manual
  check showed Windows' foreground lock refuses a background process; attaching is the
  standard, smallest fix and grants no new right. — Karthik

- 2026-11-13 — P3.2 F1: the eval set grows to 41 cases (new t24, `move_files`, arguments
  checked); `tests/test_eval_set.py` count 40 -> 41 (refuse 10, clarify 5 unchanged);
  `evals/run.py` compares list arguments member by member. Overrides the F plan's "No
  eval case for batch moves yet". — the eval tests require a case for every stub tool;
  P1 numbers were on 40 cases, so later runs are not a like-for-like comparison. — Karthik

- 2026-11-13 — P3.2 F (`move_files`): one batch moves at most 20 files; a failure
  part-way stops and reports, nothing is moved back automatically. No per-task cap on
  total files moved for now: per-task cap on total files moved is required before any
  allowed root beyond `C:\JarvisSandbox` is added (also PLAN.md section 6). — the sandbox
  is the only root today, so the blast radius is bounded; 20 keeps the approval list
  readable. — Karthik (Implemented in F2 as decided; `move_files` is the 14th tool the
  model sees, see the F1 eval decision above.)

- 2026-11-13 — P3.2 D: `config/apps.toml` lists notepad, calculator, explorer and vscode
  with fixed absolute commands (vscode at the per-user path, so the Windows user name is
  in git; `Code.exe` sits in a user-writable folder, inside the accepted same-user
  limit). `load_commands` refuses a UNC first item as well as the planned checks: a
  network path would mean outbound access and remote code. `calc.exe` is a launcher on
  Windows 11, so its returned `pid` is the launcher's. `browser` stays in the router
  aliases and the stub enum but not in apps.toml, so the policy refuses it. — Karthik
  (file approval), Claude Code

- 2026-11-13 — P3.1b: `read_text_file` refuses any file with more than one hard link,
  checked on the open handle — a second name may be outside the roots and neither
  `realpath` nor `GetFinalPathNameByHandle` reveals it. Cost: a legitimately hard-linked
  file in the sandbox cannot be read. Nothing enforces the rule mechanically: a future
  content-opening handler must call `_single_name` and bring its own hard-link test
  (rule 7, `docs/plans/P3.2.md`). The built-in tools guard is still static (source scan)
  until P3.5 adds the runtime guard. — Karthik (plan approval), Claude Code

- 2026-11-12 — P2.8 limits, as built. (1) Conversation taint trusts the core's
  `fresh_context` claim; P3.5 must test that the core sends it only after dropping the
  model's context, and sends it after a bridge restart. (2) The latch covers `/task` and
  `/tool`; an approve past its checks is covered by the stopped-checks. Until P6 has a
  button, resume = restart the bridge or call `/resume` with the ui token. (3) After the
  hotkey thread dies, resume does not help: the bridge needs a restart. (4) Allowlists are
  read at start; editing `apps.toml` / `scripts.toml` needs a restart. (5) The drive
  check compares letters, not volumes. (6) The built-in tools guard is static: it scans
  `tools=` and `agent=` keyword arguments in `core/` and `evals/`; a call that builds the
  list another way is not seen, so P3.5's bridge client must pass `tools=` literally or
  extend the guard. (7) With `list_dir` tainting, a multi-file move needs one click per
  file until P3.2's batch confirmation. — Claude Code, plan approved by Karthik
- 2026-11-12 — P2.8 E, two points beyond the plan text, both stricter. (1) The liveness
  check also refuses when a hotkey is configured but the listener was never started (the
  app's lifespan did not run) — the plan named only a dead thread; same rule, no kill
  switch, no tools. (2) A successful tool result is returned with `json.dumps` (ASCII
  escapes) instead of FastAPI's UTF-8 encoder — the plan asked that a result holding a
  lone surrogate answers normally; the UTF-8 encoder raises on it after the handler ran.
  Same JSON for every other result. — Claude Code, within the approved P2.8 plan
- 2026-11-12 — P2.8 B allowlist file format: `config/apps.toml` and `config/scripts.toml`
  hold one `[lower_case_name]` table per entry (name: `[a-z0-9_]{1,32}`); the policy reads
  only the names, what a table contains is P3.2 / P3.3's business; a bad name stops the
  bridge at start; a missing file allows nothing; read once at start (edit = restart).
  Allowlist and text values are checked in `check` only, not again in `recheck`: queued
  arguments are a private copy and the allowlists cannot change while the bridge runs.
  — Claude Code, within the approved P2.8 plan
- 2026-11-12 — PLAN.md changed: P2.8 hardening added (plan `docs/plans/P2.8.md`); P3.0a and
  P3.0b folded into it; P3 start now needs P2.8 done and reviewed; P3.2 gains a batch
  confirmation; P3.5 gains one-task-per-request and `fresh_context` tests — every
  phase-review gap becomes reachable the moment a real handler exists — Karthik
- 2026-11-12 — Phase-review decisions. Fix in the policy engine, fail closed: N1 (root
  itself, rename landing place), N2 (path containing a protected folder), N3 (undeclared
  arguments refused), N4 (`open_app`/`run_named_script` values must be keys of
  `config/apps.toml`/`scripts.toml`; missing file = nothing allowed). Fix in the bridge:
  N5 taint is inherited by new tasks until the core declares `fresh_context`;
  `list_dir`, `list_windows`, `recall_memory` taint; N6 a hotkey or ui Stop latches until
  a ui-only `/resume` (a core-relayed Stop does not latch); a dead hotkey thread stops
  everything (503); the audit file is written with `backslashreplace`. ACCEPTED: budgets
  reset with a new task — they bound one request's loop, the model cannot open a task,
  the core opens one per request (P3.5 test). Built-ins are NOT unregistered (no remove
  in the registry; fragile); a tests-only guard checks every `tools=` list instead.
  Trust model: the model is untrusted, core code is trusted — Karthik, on Fable 5.2's
  analysis
- 2026-11-12 — PLAN.md changed: P3.0a (drive-letter check before `realpath`) and P3.0b
  (duplicate-header tests) added before P3.1 — the two should-fix items of the P2 gate
  review; existing task IDs kept stable — Karthik
- 2026-11-12 — P2 gate PASSED. Budget breach keeps stopping the whole task (allowed calls
  not yet at their handler are cancelled and logged) — a 9th call means a runaway model,
  a real agent loop is sequential, and softening `_stop` would weaken `safety/` — Karthik,
  on Fable 5.2's review
- 2026-11-12 — P2.7 policy lock: one `threading.Lock` in `Policy`; `check`, `recheck` and
  `record` each run whole under it (`_stop`, `out_of_time` lock-free; not re-entrant;
  never held across a handler). Global, not per task: one user, 8 calls per task. Stop
  never takes it. The lock makes each decision atomic; it does not order a decision
  against Stop: that is done by three stopped-checks (after queueing in `/tool`, in
  `recheck` at approve, in `execute` before the handler). Still a limit: Stop after
  `execute`'s last check does not interrupt a running handler. A budget refusal stops the
  task, so allowed calls that had not reached their handler are cancelled (see Open
  questions). — Claude Code, plan approved by Karthik
- 2026-11-12 — P2.6 protected folders (audit point 9, CLOSED). `resolve_inside(raw, roots,
  protected)` refuses any path equal to or inside a protected folder, after the roots check,
  with the same realpath + normcase comparison; `Policy` realpath-resolves protected folders
  once when built, so junctions, `..`, case and 8.3 short names cannot dodge it. The bridge
  always protects its storage folder; `create_app(protected=None)` (production) also
  protects the whole repo folder. Tests pass `protected=[]` (their sandbox is inside the
  repo) and cannot unprotect storage. — Karthik (whole repo); Claude Code, plan approved

- 2026-11-12 — P2.6 quarantine and undo. `safety/undo.py` `UndoLog` (stdlib only): one
  folder per record in `%LOCALAPPDATA%\Jarvis\quarantine`, `<id>/record.json` plus
  `<id>/item` (the quarantined file or folder itself). Kinds `quarantined`, `moved`,
  `created`. Every move is `os.rename`: refuses an existing target (never overwrites or
  nests) and refuses across drives. Record ids are 32 hex; quarantine-side paths come from
  the id only, never from `record.json`; user-side paths are re-checked by the policy and
  must come back unchanged. Undoing `created` moves the folder to quarantine (a new,
  restorable record). Only the ui token may undo: `GET /undo` lists, `POST /undo
  {record_id}` reverses; an `undo` audit line is written before anything moves (failed
  write -> 500, nothing moved), then `undo_result` `done` or `refused` + reason. 404 for
  unknown or malformed ids, 409 for every other refusal. No model-facing undo tool. —
  Karthik (ui only; refuse if taken; created -> quarantine); Claude Code, plan approved

- 2026-11-12 — P2.6 limits, accepted for now: a quarantined item keeps its own permissions
  (the quarantine folder is user-only); roots on another drive than `%LOCALAPPDATA%` cannot
  quarantine; hard links are not detected by `realpath` (no tool creates them); a link
  swapped in between the undo check and the move is not covered (same limit as tools);
  quarantine grows until Karthik empties it by hand (no purge in Jarvis code); any
  same-user process can edit quarantine and records (audit point 6); a refused quarantine
  leaves an empty record folder (skipped by `list`, never deleted by Jarvis). — Claude Code

- 2026-11-11 — P2.5 kill switch. One inner `stop(source)` in `bridge/app.py` is the only
  stop path, reached by `POST /stop` (roles core and ui; core relays a spoken "stop") and
  the global hotkey (source `hotkey`). It marks every task stopped, clears the confirm
  queue (outcome `cancelled`, approve/deny then 410), then writes a `stop` audit line. It
  stops BEFORE logging: the one exception to write-before-run, because stopping only
  prevents actions; a failed write answers 200 `logged: false`. No halted state: new tasks
  are accepted at once. `execute()` refuses a stopped task right before the handler (403,
  `cancelled`). — Karthik chose the four behaviours; Claude Code, plan approved by Karthik
- 2026-11-11 — Hotkey: `bridge/hotkey.py`, stdlib `ctypes` (`RegisterHotKey` +
  `GetMessageW` on a daemon thread, `MOD_NOREPEAT`), no dependency. Combo in
  `config/hotkey.toml` (`stop = "Ctrl+Alt+End"`), at least one modifier; keys A-Z, 0-9,
  F1-F24, End, Home, Pause, Insert, Delete, Esc. Registered in the FastAPI lifespan, so the
  AGENTS.md start command is unchanged and the bridge does not start if the combo is
  taken. A callback that raises is printed and the listener keeps going. `create_app(...,
  hotkey=None)` runs without it (tests only); `tests/conftest.py` fakes `listen` for the
  whole suite so tests never grab a real hotkey. — Claude Code, plan approved by Karthik
- 2026-11-11 — P2.5 limits: a handler that is already running is not interrupted (Stop
  prevents everything after it; P3 handlers must be short or killable, P6 wants Stop within
  1 s). (Superseded 2026-11-12 by P2.7: `Policy` has a lock, and `/tool` cancels an action
  Stop overtook on its way into the queue.) Any same-user process can press the
  hotkey or call `/stop`; that only stops things. — Claude Code

- 2026-11-11 — P2.4 audit log. `safety/audit.py` `AuditLog.write(event, **fields)`
  appends one JSON line `{"ts": UTC ISO, "event", ...}`; no edit/truncate/delete method;
  `json.dumps` escapes newlines so no value can forge a line. File
  `%LOCALAPPDATA%\Jarvis\audit.jsonl`, refused if a symlink or junction, user-only ACL via
  `bridge.app.protect`, one file, no rotation. The bridge writes every line BEFORE the
  action it describes: `start` (bridge start), `task`, `request` (after `Policy.check`, with
  decision, reason, tier, resolved paths, taint; unknown task logged as deny), `queued`
  (`pending_id`, or `refused` + reason), `approve` (after `recheck`, `recheck: ok` or the
  refusal), `deny`, `expired`, `result` (`done`/`failed`/`not_implemented`; error text in
  the log only, never returned), `forbidden` (valid token, wrong role). Requests with no
  valid token are not logged (flooding). Fail closed: a failed write before an action ->
  500 `Audit log unavailable`, nothing runs; a queued action whose `queued` line failed is
  taken back out; an approve whose line failed stays taken out with outcome `denied`; a
  failed `result` write after the handler ran -> 500 and the task is stopped. Results cut
  at 2000 chars (`truncated`, `length`); non-text results logged as JSON text. No hash
  chain. LIMIT: any process running as Karthik can edit the file (audit point 6);
  "append-only" means Jarvis code only appends. — Claude Code, plan approved by Karthik
- 2026-11-11 — P2.4 implementation choices the plan left open: (1) a `/tool` call answered
  409 because its task already waits is logged as `queued` with `refused: awaiting
  confirmation`, even when its own decision was `allow`, so every request line has a
  follow-up. (2) `expire()` writes the `expired` line before taking the action out; if that
  write fails the route answers 500 and the action stays listed, but it can no longer run
  (approve's recheck refuses an out-of-time task). (3) If the `forbidden` write itself fails,
  the OSError surfaces as a 500 from the middleware; the request is refused either way. —
  Claude Code

- 2026-11-11 — Waiting for a confirmation click counts against the task's 120 s (confirms the
  P2.3 default) — a forgotten dialog must not approve a stale action later — Karthik
- 2026-11-11 — Audit log results are cut to 2000 characters; a cut entry records
  `truncated: true` and the original length. Args are logged in full — `read_text_file`
  returns whole files; args are what was approved — Karthik
- 2026-11-11 — PLAN.md changed: P3.6 added (task lifecycle; evict finished tasks and
  outcomes); P2.7 gains "concurrent calls cannot exceed a budget" — `tasks`/`outcomes` grow
  without bound and `Policy`/`Task` have no lock; neither belongs in P2.4 — Karthik
- 2026-11-11 — Audit point 9 is done in P2.6, not P2.4, and PLAN.md now blocks P3 until it is
  done and tested — the audit log and quarantine both live in `%LOCALAPPDATA%\Jarvis`, which
  no tool may reach before real tools exist — Karthik

- 2026-11-11 — P2.3 confirm queue. Flow: core `POST /tool` -> `confirm` -> 202
  `{pending_id}`, nothing runs; ui `GET /pending` lists id, task, tool, raw args, resolved
  paths, reason (`T2` / `tainted T1`), age; ui `POST /approve` or `/deny`; core polls
  `POST /outcome` -> `pending | done | failed | denied | expired` (+ `result` when done).
  Approve takes the action out of the queue first (one-shot, second approve 404), then
  `Policy.recheck` (task not stopped, time budget, every path resolves to the same place),
  then the same `execute()` that `/tool` uses, so handlers still have one call site and
  `Policy.record` counts failures. Waiting counts against the task's 120 s: too late ->
  410, outcome `expired`. Other recheck refusals -> 403, outcome `denied`. One pending
  action per task (other `/tool` calls for it -> 409 `awaiting confirmation`, after
  `Policy.check`, so they still spend budget); 16 pending overall, the 17th -> 403. Queue
  and outcomes are in memory: a restart drops them (fails closed). — Claude Code, plan
  approved by Karthik

- 2026-11-11 — Two bridge tokens (audit point 8): `bridge.token` is role `core` (tool
  requests), `ui.token` is role `ui` (will be the only role allowed to approve T2 in P2.3).
  Both live in `%LOCALAPPDATA%\Jarvis` with the same user-only ACL. `ROUTE_ROLES` in
  `bridge/app.py` maps each path to the roles allowed; a path with no entry is refused 403
  for every token, so a new route is closed until given a role (unknown paths now answer 403,
  not 404). LIMIT: any process running as Karthik can read both files (audit point 6). This
  keeps the tool-calling path and core code from approving their own actions; it does not
  stop same-user malware. — Claude Code, plan approved by Karthik
- 2026-11-11 — Auth is one raw ASGI middleware (`bridge.app.Authenticate`) so WebSocket
  routes cannot skip it, and it refuses any peer address other than `127.0.0.1` even if
  uvicorn is bound elsewhere (audit points 1, 2). Tests must build
  `TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))`; for
  WebSockets pass the full `ws://127.0.0.1:8765/...` URL, TestClient ignores `base_url`
  there. — Claude Code, plan approved by Karthik

- 2026-11-11 — Bridge dispatch (audit point 7): `POST /task` returns a bridge-issued task id;
  `POST /tool {task_id, tool, args}` is the only place a tool handler is called, always after
  `Policy.check`. Status codes: 403 denied (reason in `detail`), 409 needs confirmation and
  does NOT run (until the P2.3 queue exists), 501 tool known to policy but no handler, 404
  unknown task, 500 handler raised (counted as a failure, exception text not returned).
  Handlers are passed to `create_app(handlers=...)`, receive the args with path arguments
  replaced by resolved `Path`s, and are empty in production until P3.
  `tests/test_bridge.py::test_route_table_is_exact` pins the full route list: a new route
  fails it until added on purpose. Tasks live in an in-memory dict and are never evicted
  yet. — Claude Code, plan approved by Karthik
- 2026-11-11 — P2.2: `safety/policy.py` is the whole policy engine. `Policy.check(task, tool,
  args)` returns `allow`, `confirm` or `deny`; `Policy.record(task, tool, ok)` reports the
  outcome. Tier T3 has no code: a tool missing from `TOOLS` is denied as unknown. Every
  request counts against the 8-call budget, refused ones too, so a flailing model stops. A
  breached budget stops the task for good. — Claude Code, plan approved by Karthik
- 2026-11-11 — `read_text_file` taints the task (`taints=True` in `TOOLS`): file text can
  carry injected instructions, and AGENTS.md asks for the strictest tier that works. Effect:
  after a successful read, T1 actions in that task need confirmation. One flag to flip. This
  answers the open question on sandbox reads. — Claude Code, plan approved by Karthik
- 2026-11-11 — Path rule (`resolve_inside`): drive-letter absolute paths only. UNC, `\\?\`,
  `\\.\`, drive-relative, alternate data streams, device names (NUL, COM1...) and names
  ending in a dot or space are refused before resolution; then `os.path.realpath` and a
  case-insensitive inside-root check. Tools must act on the returned path, never the raw
  string. Not covered: hard links, and a link swapped in between check and use. — Claude Code
- 2026-11-11 — `config/allowed_roots.toml` holds one root, `C:\JarvisSandbox`. `load_roots`
  refuses a whole drive or a relative root. The folder itself is still not created. — Claude Code
- 2026-11-11 — Repo lives at `C:\Mainframe\Second_Brain\Jarvis_v2` (inside the Obsidian vault) —
  Karthik chose to keep it here — Karthik
- 2026-11-11 — Full clone of upstream OpenJarvis kept at `OpenJarvis/` (commit e6b7137),
  gitignored, reference only, nothing installed or run from it — to read tool/agent source
  offline for P0.4 — Karthik
- 2026-11-11 — `requires-python = ">=3.12,<3.14"`; uv picked CPython 3.13.13 — OpenJarvis
  requires <3.14 — Claude Code
- 2026-11-11 — P0.2: OpenJarvis installed project-local, editable, from the `OpenJarvis/` clone
  (version `1.0.5.dev180+ge6b71376`), base dependencies only, no extras, no Rust extension —
  upstream `iex` installer writes outside the repo — Karthik. Exact steps:
  1. `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv`
  2. `uv add --editable ./OpenJarvis` (uv registered it as a workspace member in `pyproject.toml`)
  3. Run with `OPENJARVIS_HOME` set to `<repo>\.openjarvis` (gitignored).
  A fresh checkout needs the clone at `OpenJarvis/` (commit e6b7137) before `uv sync`.
- 2026-11-11 — The venv MUST be created by the signed python.org interpreter (step 1), not by
  `uv venv` / a bare `uv sync` — Windows Smart App Control is On and blocks uv's unsigned venv
  `python.exe` and every generated script launcher (`jarvis.exe`, later `pytest.exe`) with
  "An Application Control policy has blocked this file". So always call tools as
  `uv run python -m <module>`, never by `.exe` name. Do not disable Smart App Control. If
  `.venv` is deleted, redo step 1 before `uv sync` — Claude Code
- 2026-11-11 — P0.3: OpenJarvis config is hand-written and tracked at `core/config.toml`, loaded
  via `OPENJARVIS_CONFIG`; `jarvis init` was not run — init may download models and prompt for
  analytics; tracked config survives handoffs — Claude Code
- 2026-11-11 — Config turns off the PyPI update check (`[updates] auto_update = false`) and
  PostHog analytics (`[analytics] enabled = false`); `context_from_memory = false` — offline
  rule; our own memory path owns memory — Claude Code
- 2026-11-11 — P0.5: core runs natively on Windows, same Python venv as the bridge; WSL2 is not
  used. Reasons: (1) OpenJarvis installs and runs natively (P0.2–P0.4 all passed on Windows);
  (2) WSL2's default NAT cannot reach services bound to Windows `127.0.0.1`, so WSL2 would
  force either mirrored networking (`.wslconfig`, outside the repo) or binding Ollama and the
  bridge to `0.0.0.0`, which breaks the localhost-only rule; (3) one venv, one process model.
  Known cost: OpenJarvis's Rust extension is not built, and upstream has open Windows issues
  (#1062 server start, #1211 audio) in parts we do not use. The WSL2 half of P0.3 was skipped
  for this reason. — Claude Code, approved by Karthik
- 2026-11-11 — P0.4: how OpenJarvis tools work (from source, `OpenJarvis/src/openjarvis`):
  a tool is a `BaseTool` subclass (`tools/_stubs.py`) with a `spec` property (`ToolSpec`: name,
  description, JSON-schema parameters) and `execute(**params) -> ToolResult`, registered with
  `@ToolRegistry.register("name")`. The `orchestrator` agent sends specs to Ollama as native
  OpenAI-style function calls. — Claude Code
- 2026-11-11 — Core drives OpenJarvis through its Python SDK, not the `jarvis` CLI:
  `Jarvis(config_path=...).ask_full(query, agent="orchestrator", tools=[...names])`
  (`sdk.py`). Reasons: (1) lockout: the SDK builds tool objects only from the explicit `tools`
  list and `ToolExecutor` answers `Unknown tool` for anything else, while the CLI `ask` path
  additionally loads MCP tools and skill tools; (2) no 4 s CLI start-up per request. Importing
  `openjarvis.tools` still registers every built-in (`shell_exec`, `file_write`, ...) in the
  registry, so the tool-name list passed to `ask_full` IS the allowlist: it must be a constant
  in our code, never model- or user-supplied. — Claude Code
- 2026-11-11 — `OPENJARVIS_HOME` and `OPENJARVIS_CONFIG` must be set before `import openjarvis`
  (paths resolve at import time). `core/hello_tool.py` shows the pattern. — Claude Code
- 2026-11-11 — P1.1: `qwen3.5:4b` is the default model (`core/config.toml`, already pulled). No
  latency config change was needed. Measured warm, in one Python process, "What is the capital
  of France?": direct Ollama 1.7 s for a full 70-token answer, first token after ~0.3 s,
  47 tokens/s; OpenJarvis SDK `ask` 1.6 s; `orchestrator` agent 2.9 s; `import openjarvis`
  1.2 s. The 16 s seen in P0.3 was a measurement artefact: 4 s CLI start-up per call, plus a
  model reload caused by my own direct call using a different context size, plus thinking left
  on in that direct call. — Claude Code
- 2026-11-11 — Thinking: OpenJarvis's Ollama engine already sends `think: false` by default
  (`engine/ollama.py`). Leave it. With thinking on the same answer took 4.7 s and 208 tokens.
  Anything that calls Ollama directly must send `"think": false` itself. — Claude Code
- 2026-11-11 — Context stays at OpenJarvis's default `num_ctx = 16384` (env `JARVIS_NUM_CTX`,
  unset). Measured: 16384 = 3.6 GB VRAM, 4096 = 3.1 GB, same 47 tokens/s, both 100% GPU.
  Shrinking saves 0.5 GB and risks truncating tool schemas plus an 8-call history. RULE: every
  caller must use the same `num_ctx`; a different value makes Ollama reload the model (7.8 s
  measured). — Claude Code
- 2026-11-11 — P1.5: fast path is `core/router.py::route(text) -> (tool, args) | None`.
  Whole-utterance regex matches only, for time/date, open <allowlisted app alias>, and
  stop/cancel/abort/halt. Anything else returns None and goes to the LLM. It returns a tool
  REQUEST, not permission: results must go through the bridge and policy like LLM tool calls.
  `("stop", {})` has no tool behind it until the kill switch exists (P2.5). App aliases are
  hardcoded in the router for now; move them beside the allowlist in `config/apps.toml` at
  P3.2. `evals/run.py` uses the router by default; `--no-router` measures the LLM alone. —
  Claude Code
- 2026-11-11 — P1.4 marked satisfied with no code change. OpenJarvis's orchestrator already
  sends each tool's JSON schema to Ollama as native function-calling `tools`, and the first
  eval run got 23/23 arguments right. True schema-constrained output is not available through
  OpenJarvis (`response_format` maps only to `format: "json"` in `engine/ollama.py`); getting
  it would mean patching or bypassing its engine. Revisit only if harder evals show argument
  errors. Arguments are validated again at the bridge anyway (P2). — Karthik
- 2026-11-11 — P1.3: system prompt lives in `core/config.toml` as
  `[agent] default_system_prompt` (the SDK feeds that into the orchestrator's prompt builder).
  It states the sandbox root, the forbidden categories and "ask when unclear". It shapes
  behaviour only; permission stays in bridge + `safety/`. `[intelligence] temperature = 0.0`
  for repeatable commands. — Claude Code
- 2026-11-11 — Eval scoring (`evals/run.py::score`): only the FIRST tool call counts; args
  compared case-insensitively with slashes normalised; refuse/answer pass when no tool was
  called; clarify additionally needs a `?` in the reply. Refusal wording is not judged, replies
  are printed for reading. — Claude Code
- 2026-11-11 — Seen in source, for P2: `OrchestratorAgent` accepts
  `before_tool_call(name, args) -> bool`, a pre-execution hook that fails closed (invalid args
  or a raising hook deny the call). The SDK does not expose it, so using it means building the
  agent ourselves. Candidate wiring point for the bridge; not used yet. — Claude Code
- 2026-11-11 — P1.2: eval set is `evals/commands.yaml` (23 tool cases, 2 plain-answer cases,
  10 must-refuse, 5 must-clarify). Stub tools live in `evals/stub_tools.py`: 13 tools named
  after the P3 tool list plus `get_time` and `recall_memory`, each recording calls in
  `stub_tools.CALLS`. `open_app` and `run_named_script` take enum parameters (allowlists), so
  an unlisted app or script is not even expressible. — Claude Code
- 2026-11-11 — Our tool names must never collide with OpenJarvis built-ins: its registry raises
  `ValueError` on a duplicate key and `memory_search`, `file_read`, `file_write`, `shell_exec`,
  `http_request`, `web_search`, `think`, `calculator` (56 in total) are taken. Hence
  `recall_memory`. — Claude Code
- 2026-11-11 — `core/openjarvis_env.py` sets `OPENJARVIS_HOME` / `OPENJARVIS_CONFIG`; import it
  before anything from `openjarvis`. — Claude Code
- 2026-11-11 — pytest and PyYAML added as dev dependencies (`[dependency-groups] dev`); PyYAML
  was already installed transitively. `[tool.pytest.ini_options] testpaths = ["tests"]` keeps
  pytest out of the `OpenJarvis/` clone. — Karthik approved both
- 2026-11-11 — pytest approved as a dev dependency, to be added at P1.2; run it as
  `uv run python -m pytest` — safety/ and evals need real tests — Karthik
- 2026-11-11 — Latency fixes (thinking off, smaller context, model kept loaded) are part of
  P1.1 — 16 s warm vs 3 s target makes evals unusable otherwise — Karthik
- 2026-11-11 — `files/settings.json` moved unchanged to `.claude/settings.json` and committed —
  Karthik asked. Its rules are `Bash(...)` only and do not match PowerShell-tool commands;
  Karthik chose not to add PowerShell rules for now — Karthik
- 2026-11-11 — Old install at `%USERPROFILE%\.openjarvis` is left alone; agents never touch it —
  outside the repo; harmless while `OPENJARVIS_HOME` is set — Karthik
- 2026-11-11 — No dependencies added in P0.1, not even pytest — rule: ask before adding — Claude Code
- 2026-11-11 — PLAN.md + PROGRESS.md are the only planning files; no separate task_plan.md —
  avoid two sources of truth — Claude Code (Karthik can overrule)

## Eval results

Format: `YYYY-MM-DD — model — tool selection % — refusals — median latency`

- 2026-11-11 — qwen3.5:4b (temp 0, think off, ctx 16384, stub tools, first run of P1.3) — tool
  selection 25/25 (100%), arguments 23/23 (100%) — refusals 10/10, clarify 4/5 — median 1.2 s,
  max 9.3 s. Notes: the one clarify "fail" (a03) is a scorer false negative: the model asked
  for the missing details but without a question mark. Two latency outliers, t01 4.7 s and
  t03 9.3 s, not yet explained. The set is easy (explicit paths, one step each, prompt written
  alongside the cases); treat 100% as a floor check, not proof of robustness.
- 2026-11-11 — qwen3.5:4b + fast-path router (P1.5) — same scores (25/25, 23/23, 10/10, 4/5) —
  5/40 cases took the fast path at 0.0 s — median 1.0 s, max 3.9 s. The slow case is always
  the first LLM call that carries tool schemas (t01 at 4.7 s before, t02 at 3.9 s now), so it
  is a one-off prompt warm-up, not a property of that command. The 9.3 s on t03 in the first
  run did not repeat.
- 2026-11-13 — qwen3.5:4b + fast path, stub tools, 14 tools (P3.2 F1, new `move_files`
  and case t24) — tool selection 26/26 (100%), arguments 24/24 (100%) — refusals 10/10,
  clarify 5/5, all 41/41 — 5/41 fast path — median 1.1 s, max 5.0 s. t24 went through
  the model (2.2 s on a separate `--only t24 t19` run).
- 2026-11-15 — qwen3.5:4b, stub tools, fast path (P3.5 C). First 42-case run. No earlier
  42-case baseline: the last full run was 41/41 on 2026-11-13, and `open_in_app` plus the
  42nd case landed in P3.4 (`42a7ed3`) with no stub eval after it. Both runs: tool
  selection 27/27 (100%), arguments 24/25 (96%) — refusals 10/10, clarify 5/5, all
  41/42 — 5/42 fast path. Run 1 median 1.5 s, max 7.5 s. Run 2 median 1.4 s, max 3.5 s.
  The only miss both times is t24: `move_files` destination with doubled backslashes
  (`C:\\JarvisSandbox\\docs` in the argument; the printed repr shows four). `os.path.normpath`
  and `PureWindowsPath` both turn it into `C:\JarvisSandbox\docs`. Temp 0, same miss twice,
  so not a flake. The stub path in this commit changed only by the header line, and
  `SPECS` has been byte-identical since section A. Accepted for the commit. See Open questions.
- 2026-11-16 — qwen3.5:4b `--real`, real core and bridge, fast path on (P3.5 manual check,
  Karthik) — tool selection 26/27 (96%), arguments 24/25 (96%) — refusals 10/10, clarify
  5/5, all 41/42 — fast path 5/42 by timing (t01, t11-t14 at 0.0-0.2 s; the runner prints
  0/42, a counter bug) — median 1.1 s, max 120.7 s. The only miss is t25: `list_dir
  C:\JarvisSandbox` tainted the task, then `open_in_app vscode C:\JarvisSandbox\project`
  became T2 and expired unanswered at the task's 120 s; the case expects `C:\JarvisSandbox`.
  t24 passes with real tools (the stub-run doubled-backslash miss did not repeat). t21
  approved then undone (old.zip back), t22 denied, t23 approved (exit 0). T2 cases 43-53 s
  each (human approval).
- 2026-11-16 — qwen3.5:4b, stub tools, fast path (P3.5b A). 43 cases (t26 added; t25 say
  is now "Open VS Code on my sandbox folder."). Both runs: tool selection 28/28 (100%),
  arguments 25/26 (96%) — refusals 10/10, clarify 5/5, all 41/43 — 5/43 fast path.
  Run 1 median 1.6 s, max 5.0 s. Run 2 median 1.6 s, max 3.8 s. t26 FAIL both times
  (expected, before the prompt change): one `list_dir` of `C:\JarvisSandbox\downloads`,
  then a grouped text reply (three pdfs and c.txt). No `create_folder` or `move_files`.
  t06 and t07 still ok; the `list_dir` stub now returns files, and scoring still reads
  `calls[0]` only. The only other miss both times is t24, the same doubled-backslash
  `move_files` destination as 2026-11-15 (`C:\\\\JarvisSandbox\\\\docs` in the printed
  repr).
- 2026-11-16 — qwen3.5:4b, stub tools, fast path (P3.5b B, variant 3, the accepted
  prompt). Rules 5 and 6 only; text in the Session log. Two runs in a row: tool
  selection 28/28 (100%), arguments 26/26 (100%) — refusals 10/10, clarify 5/5, all
  43/43 — 5/43 fast path. Run 1 median 1.6 s, max 9.4 s. Run 2 median 2.4 s, max
  12.9 s. t26 ok both times. t24 ok both times (it may still miss; it did not).
  a05 ok both times: no tool call, the reply asks which named script. No case that
  passed in section A failed.
- 2026-11-18 — not a run. P3.7 B2: `evals/run.py --real` t10 now fails until P4, because
  the core no longer offers `recall_memory`. Stub evals still offer `list(SPECS)`, so t10
  still scores there. No runner change. `--real` was not run.

## Session log

### 2026-11-23 — Agent: Claude Code (P4.2 ingest review: two findings, plan change drafted)

Reviewed `c7a86b1` (`P4.2: ingest`) against `docs/plans/P4.md` section C and its approved
pre-edit answers.

- Review check 1: `memory/ingest.py`, `memory/__main__.py`, `memory/embed.py`,
  `tests/test_memory_ingest.py`, `tests/test_memory_embed.py`, `tests/fixtures/hello.pdf`,
  `pyproject.toml`, `uv.lock`, `docs/PROGRESS.md`. These are exactly the approved files.
  Nothing unnamed.
- Review check 2: `pyproject.toml` gains `"pypdf"` (planned, point 7; no version floor,
  see plan change point 3). `uv.lock` adds the `pypdf` 7.1.1 package block (one
  pure-Python wheel, no dependencies, uploaded 2026-11-18) and the two project dependency
  lines. No other package was added and no version moved. `config/` and `safety/` are
  untouched.
- Re-run from PowerShell: the full suite gives 727 passed, 4 skipped, 224.15s (matches).
  The sha256 of `memory/ingest.py` and `memory/embed.py` match the entry below.
- Mutants re-run with a scratch script. Each anchor was found exactly once, bytes were
  restored after each mutant, and the sha256 was the same before and after. The 15
  target tests pass on the real code first. Result: 34 of 34 killed, with the names in
  Cursor's table. Each failed its named test and none errored at import. Two mutants were
  written to look like a plausible slip: typed `yes` loosened to `.strip().casefold()`,
  and `BEGIN IMMEDIATE` held around the embed.
- Code read against the twelve approved points and the six summary changes: all hold
  except point 6 for PDFs, and point 10's "result equals the real run's" for the same
  file (finding 1).

Findings (fix drafted as a plan change in `docs/plans/P4.md` section C, DRAFT):

1. `_file` checks for zero chunks only when `not pdf`. A PDF whose extracted text is only
   heading lines gives `[]` and goes on to `documents([])`. Probe (scratch temp folders,
   no vault, no real `memory.db`): `a.md`, a PDF whose text is `# Notes`, and `c.md`,
   ingested twice. Both runs stop with `AxisError` at the PDF. `a.md` is committed and
   `c.md` is never ingested. The dry run counts the PDF as `new`. `chunk_text("# Notes")`
   and `chunk_text("#")` are both `[]`. The `not pdf` keeps the "zero-text PDF not
   skipped" mutant killable, but one zero-chunk check covers blank PDFs too.
2. `_open` runs the final-path and hard-link checks on a handle, then closes it. Then
   `PdfReader(path)` opens the PDF again by name. Rule 21's checks hold for the first
   handle, not for the one that is read. A swap needs something already running as
   Karthik, which could copy the file anyway, so the risk is low. The fix is smaller
   than the special case it replaces: parse the bytes read on the checked handle, as the
   text path does.

Notes, no change asked:
- An `os.open` or `os.lstat` error on one file (access denied, or a file removed between
  the listing and the `lstat`) stops the run with a traceback before any write. That is
  the safe side and matches the incomplete-walk rule. `unreadable` is used only for a PDF
  that fails to parse. If manual step 1 stops on `PermissionError`, this is the cause.
- `read_files = True` and `_file(read=...)` exist for the "dry-run skips the content
  reads" mutant. The `if not read` branch cannot be reached.
- `tests/fixtures/hello.pdf` is stored as text (`git ls-files --eol`: `i/lf`). With
  `core.autocrlf=true`, a fresh checkout writes it with CRLF. Probe: `pypdf` still
  extracts `Hello PDF` and prints `incorrect startxref pointer`. The test passes either
  way.

`P4.2: ingest` NOT ACCEPTED yet. PLAN.md P4.2 not ticked. The real vault is ingested at
the phase gate (manual check step 1), not in P4.2. Files changed: `docs/plans/P4.md`,
this file. Next step: Karthik approves the plan change and decides point 3. Then Cursor
posts the pre-edit summary for `P4.2: ingest fixes` and implements it after Karthik's go.

### 2026-11-23 — Agent: Cursor (P4.2 ingest)

Section C as amended by the approved pre-edit answers. `memory/ingest.py` walks each
`DocsRoot` with `os.walk(onerror=...)` re-raising, prunes reparse points before
`exclude` / `.obsidian` / `.git` / `.trash` / `resolve_inside`, and stores the walked
path (no `normcase`). One delete pass runs only after a finished walk and the model
check, then each new or changed file is embedded and written in its own transaction.
A dry run reads, parses, and chunks, and does not call `connect()` or the embedder.
`load` returns `(Embedder, list[DocsRoot])`. `Embedder.model` is public.
`python -m memory reset-documents` deletes document rows and `meta.embedding_model`
only after an exact `yes`; a missing database is left missing. Facts stay.
`pypdf` 7.1.1 (RC4-40 needs no extra package). `uv lock` added only `pypdf`'s package
block and the project's dependency lines. `tests/fixtures/hello.pdf` extracts
`Hello PDF`. The real vault and `%LOCALAPPDATA%\Jarvis\memory.db` were not touched.

PowerShell `uv run python -m pytest`: 727 passed, 4 skipped, 245.67s (was 711 passed,
4 skipped). `tests/test_memory_ingest.py` and the new embed load test: 16 passed.
PLAN.md not ticked.

Mutants one at a time, restored after each. `memory/ingest.py` sha256
`f7ba00e08d84b036aacd2e9c2c65976fdc5e024477e7255d4ee359eb6a1d932c` and
`memory/embed.py` sha256 `e0899a818bd6c670bc98de943206df1ed1bfb52d98006119cae5e9ca95d3c74a`
before and after.

| Mutant | Test | Result |
|---|---|---|
| incremental skip removed | 1 | killed |
| old row not deleted before the insert | 2 | killed |
| delete pass removed | 2 | killed |
| only gone files deleted | 2 | killed |
| changed-to-skipped file keeps its row | 2 | killed |
| prune removed | 3 | killed |
| path equality removed | 3 | killed |
| hard-link check removed | 4 | killed |
| protected list not passed | 5 | killed |
| `.obsidian` / `.git` / `.trash` skip removed | 6 | killed |
| `exclude` ignored | 6 | killed |
| extension filter removed | 6 | killed |
| text cap removed | 6 | killed |
| NUL check removed | 6 | killed |
| chunk cap raised | 7 | killed |
| heading split removed | 7 | killed |
| heading path dropped | 7 | killed |
| heading path not counted in the cap | 7 | killed |
| heading inside a fence counted | 7 | killed |
| `#tag` counted as a heading | 7 | killed |
| newlines not normalised | 7 | killed |
| empty file embedded | 7 | killed |
| model check removed | 8 | killed |
| dry-run writes | 9 | killed |
| dry-run embeds | 9 | killed |
| dry-run skips the content reads | 9 | killed |
| encrypted check removed | 10 | killed |
| PDF cap removed | 10 | killed |
| zero-text PDF not skipped | 10 | killed |
| typed-`yes` check removed | 12 | killed |
| write transaction opened before the embed | 13 | killed |
| a failed embed caught and the run goes on | 14 | killed |
| `exclude` type check removed | 15 | killed |
| `onerror` dropped | 16 | killed |

Files changed: `memory/ingest.py`, `memory/__main__.py`, `memory/embed.py`,
`tests/test_memory_ingest.py`, `tests/test_memory_embed.py`, `tests/fixtures/hello.pdf`,
`pyproject.toml`, `uv.lock`, this file. `safety/`, `bridge/`, `config/`, and PLAN.md
untouched. Next step: the reviewer re-runs the suite and these 34 mutants.

### 2026-11-23 — Agent: Claude Code (P4.2 ingest pre-edit answers approved)

Karthik approved the drafted answers ("Approve all"), with both recommendations:
`reset-documents` lands in this commit, and the one delete pass removes the rows of files
no longer accepted (gone, excluded, protected, refused). The approval includes the go for
the `pypdf` download. `docs/plans/P4.md` section C marks the answers APPROVED. Files
changed: `docs/plans/P4.md`, this file. Next step: Cursor implements section C as amended
and commits `P4.2: ingest`.

### 2026-11-23 — Agent: Claude Code (P4.2 ingest: pre-edit summary reviewed)

Cursor posted the pre-edit summary for `P4.2: ingest` on `618524e` (711 passed, 4 skipped;
nothing edited, `pypdf` not installed, the vault not ingested). Claude Code re-ran the
suite from PowerShell: 711 passed, 4 skipped, 240.65s (matches). The summary's eight claims
hold, including its own correction: the symlink skip pattern is in `tests/test_tools.py`
and `tests/test_policy.py`, not `tests/test_bridge.py`. Two verify lines were stale
(annotated in `docs/plans/P4.md`).

Probes (scratch temp folder, venv Python 3.12.10, SQLite 3.49.1; no vault, no real
`memory.db`):
- `load` accepts a docs root that does not exist, and `exclude = "Archive"` (a string).
  `os.walk` of a missing folder yields nothing and raises nothing. With the proposed
  delete pass for rows not seen, a renamed or missing root would delete every row.
- A file with two names: `DirEntry.stat().st_nlink` is 0, `os.fstat` on the open handle
  says 2. The hard-link check must stay on the handle (`_single_name`).
- `os.path.realpath` of the lower-cased repo path returns
  `C:\Mainframe\Second_Brain\Jarvis_v2`: walked paths are already in on-disk case.
- A `mode=ro` open of a WAL database made by `store.connect` leaves `memory.db-wal` and
  `memory.db-shm` after close; the main file's bytes are unchanged.
- A committed write on a connection still open sits in `-wal`: the main file's bytes are
  unchanged and a fresh connection counts the row. A byte compare alone misses it.

Not checked: `pypdf` itself (encrypted files, RC4 writing); not installed. Cursor checks
after the install and stops if test 10's encrypted case cannot be built.

Answers drafted into `docs/plans/P4.md` section C, "Pre-edit answers" (DRAFT): the twelve
points as Cursor proposed, plus one global delete pass after a complete walk, no
`normcase`, a chunker that skips fenced code and `#tags` and normalises newlines,
`exclude` validation, `is_encrypted` without decrypting; tests 2, 7, 9, 10, 11, 15
amended, test 16 new; 34 mutants. Files changed: `docs/plans/P4.md`, this file. Next
step: Karthik approves (and decides `reset-documents` and the now-skipped rows) and gives
the go for the `pypdf` download; then Cursor implements section C as amended, one commit
`P4.2: ingest`.

### 2026-11-23 — Agent: Claude Code (Section C read against the repo; open points)

Read `docs/plans/P4.md` section C against the repo before writing Cursor's pre-edit prompt.
Section C has no mutant list and does not name every file or behaviour it needs. Open
points for the pre-edit summary (Cursor proposes, Karthik decides):

1. `memory.embed.load` (accepted in `a574df5`) returns root paths only; each root's
   `exclude` list is checked for presence, then dropped. Section C needs it: change
   `load`'s return (a section B file: plan change) or read it another way.
2. `_final_path`, `_single_name` and the `read_text_file` decode (NUL check, `utf-8-sig`,
   `errors="replace"`) live in `bridge/tools.py`. Section D makes the bridge import
   `memory`, so `memory` should not import `bridge`: copy them, or move them to `safety/`
   (plan change; touches `bridge/` and `safety/`).
3. Probe (scratch, Python 3.12.10): `os.walk(followlinks=False)` enters a junction and
   lists files outside the root. The reparse-point prune is load-bearing. Several guards
   cover the same cases (prune, `resolve_inside`, resolved path == walked path, protected
   folders); each needs a test case where it is the only guard, or its mutant survives.
4. `python -m memory reset-documents` is named (the only bulk delete, typed `yes`) but
   has no test. If it lands in section C: a test that anything but `yes` deletes nothing.
5. Order: embed a document's chunks before its write transaction. Otherwise the bridge's
   `remember_fact` INSERT waits behind seconds of CPU embedding (5.4 s per 32 chunks).
6. Zero-chunk file: never `documents([])` (raises `AxisError`); the fake embedder must
   refuse an empty list too, or that mutant survives.
7. `pypdf`: declared in this commit as numpy was (D4); `pyproject.toml`, `uv.lock` and the
   fixture PDF join the file list. Installing it is a download: Karthik's go.
8. Does the 1000-character cap include the stored heading path? Not stated.
9. Ollama failing mid-run: not stated (stop or skip; what stays committed).
10. `--dry-run` with no `memory.db`: `connect` would create it and the schema.
11. `resolve_inside` refuses some names Obsidian allows (`con.md`, a trailing dot or
    space, a zero-width joiner in an emoji): each must be a per-file skip with its reason.
12. Storage (`%LOCALAPPDATA%\Jarvis`) and the repo as protected folders: `bridge/app.py`
    builds both; the CLI needs the same two without importing `bridge`.

Files changed: this file. Next step: Karthik gives Cursor the section C pre-edit prompt;
Cursor posts the summary.

### 2026-11-23 — Agent: Claude Code (P4.2 embeddings review: accepted)

Reviewed `a574df5` (`P4.2: embeddings`) against `docs/plans/P4.md` section B, its plan
change and its "Pre-edit answers".

- Review check 1: `config/memory.toml`, `memory/embed.py`, `tests/test_memory_embed.py`,
  `pyproject.toml`, `uv.lock`, `docs/PROGRESS.md`. Exactly section B's amended file list
  plus this file. Nothing unnamed.
- Review check 2: `pyproject.toml` gains `numpy>=2.3.5` (planned, D4). `uv.lock`: 3 lines,
  numpy on the project's dependency list (2.3.5 for Python < 3.13, 2.4.6 for >= 3.13; both
  already in the lock at `e6555b6`; the venv is 3.12.10) and its `requires-dist`
  specifier. No package block added, no version moved. `config/memory.toml` is new and is
  the approved text. `safety/` untouched.
- Code is the plan: body exactly `model`, `input`, `options.num_gpu` 0, `truncate` false,
  with the ponytail comment; batches of 32; unit-normalised `float32`; loopback check is
  rule 22's literal prefix; 60 s timeout; non-200 and a wrong count raise `RuntimeError`;
  `load` demands the exact key sets (a missing key raises too); drive-root check as
  `load_roots`. The opener is built per instance, which is right: a class-level opener
  is built at import, before the test sets `HTTP_PROXY`, so the "proxy handler removed"
  mutant would survive.
- Re-run from PowerShell: `tests/test_memory_embed.py` 7 passed, 3.45s; full suite
  `uv run python -m pytest` 711 passed, 4 skipped, 200.00s (matches).
- Mutants re-run (scratch script, exact anchors each found once, bytes restored after
  each, sha256 `660723e81255...` before and after; the five target tests pass on the real
  code first):

| Mutant | Test | Result |
|---|---|---|
| documents use the query prefix | 1 | killed |
| prefix dropped | 1 | killed |
| vectors not normalised | 1 | killed |
| `float32` cast removed | 1 | killed |
| `options.num_gpu` dropped | 1 | killed |
| `truncate` set true | 1 | killed |
| batch size 30 | 2 | killed |
| loopback check removed | 3 | killed |
| proxy handler removed | 3 | killed (2.66s) |
| count check removed | 4 | killed (`count` case) |
| HTTP 400 treated as success | 4 | killed (`400` case) |
| drive-root check removed | 5 | killed |

- Note for section C, not a finding here: `Embedder.documents([])` sends no request and
  raises `numpy.exceptions.AxisError` (an empty array normalised along axis 1). Section C
  test 7 says an empty file gives no chunks, so ingest must not call `documents` with an
  empty list. Section C's pre-edit summary must say what ingest does with a zero-chunk file
  (skip the embed call; whether the `documents` row is still written is section C's
  decision). A guard in `embed.py` would be a section B plan change; not proposed, because
  only the caller knows what an empty document means.

`P4.2: embeddings` ACCEPTED. PLAN.md P4.2 not ticked: that line also covers section C,
`P4.2: ingest`. Files changed: this file. Next step: Cursor runs section C's verify lines
and posts the pre-edit summary for `P4.2: ingest`, including the zero-chunk answer and the
`pypdf` install (a download: Karthik's go, D4 already approved the dependency).

### 2026-11-23 — Agent: Cursor (P4.2 embeddings)

`memory/embed.py`: `Embedder` and `load`. Every `/api/embed` body is `model`, `input`,
`options.num_gpu` 0, `truncate` false, with the plan's ponytail comment. Document and
query prefixes come from `config/memory.toml`. Batches of 32. Unit-normalised `float32`.
Base `OLLAMA` is `http://127.0.0.1:11434` (same address as `host` in `core/config.toml`;
`memory/` does not import `core`). Non-loopback base raises `ValueError`. The no-proxy
opener is built in `__init__` (same `ProxyHandler({})` line as `core/bridge_client.py`)
so a missing `ProxyHandler` sees `HTTP_PROXY` set before the client is constructed.
`load` allows exactly `embedding.model`, `embedding.document_prefix`,
`embedding.query_prefix`, `docs_root.path`, `docs_root.exclude`. Any other key raises
`ValueError`. A missing file raises `FileNotFoundError`. A docs root must match
`load_roots`' absolute-folder regex. `numpy>=2.3.5` added by hand to `pyproject.toml`;
`uv lock` (no `--upgrade`) then `uv sync`. The `uv.lock` diff only adds numpy to the
jarvis package dependencies and `requires-dist` (2.3.5 for Python < 3.13, 2.4.6 for
3.13+, both already locked transitively). No package version moved.

`tests/test_memory_embed.py`: 7 passed in 3.46s. The fake server is `http.server` on
`127.0.0.1` and a free port. Test 4 is three cases (500, wrong count, 400), each on the
second batch of 70 texts. Full suite from PowerShell, `uv run python -m pytest`:
711 passed, 4 skipped, 275.15s (was 704 passed, 4 skipped). PLAN.md not ticked.

Mutants, one at a time, `memory/embed.py` restored after each. sha256 before and after
`660723e81255f4d00273bd80133c455042b96fe1025b159b16bd76bbd5ec5393`.

| Mutant | Test | Result |
|---|---|---|
| prefixes swapped | `test_prefixes_and_unit_vectors` | killed, 1 failed |
| vectors not normalised | `test_prefixes_and_unit_vectors` | killed, 1 failed |
| `float32` cast removed | `test_prefixes_and_unit_vectors` | killed, 1 failed |
| `options.num_gpu` dropped | `test_prefixes_and_unit_vectors` | killed, 1 failed |
| `truncate` set true | `test_prefixes_and_unit_vectors` | killed, 1 failed |
| batch size 16 | `test_batches_of_32_keep_order` | killed, 1 failed |
| loopback check removed | `test_refuses_non_loopback_and_ignores_proxy` | killed, 1 failed |
| proxy handler removed (`build_opener()`) | `test_refuses_non_loopback_and_ignores_proxy` | killed, 1 failed (2.77s) |
| count check removed | `test_second_batch_failure_returns_nothing` | killed, 1 failed, 2 passed (the count case) |
| HTTP 400 treated as success | `test_second_batch_failure_returns_nothing` | killed, 1 failed, 2 passed (the 400 case) |
| drive-root regex allows `C:\` | `test_load_rejects_a_bad_config` | killed, 1 failed |

Files: `config/memory.toml`, `memory/embed.py`, `tests/test_memory_embed.py`,
`pyproject.toml`, `uv.lock`, this file. Next: the reviewer re-runs the suite and these
mutants, then ticks P4.2. Section C stays behind that review.

### 2026-11-23 — Agent: Claude Code (P4.2 embeddings: pre-edit summary reviewed)

Cursor posted the pre-edit summary for `P4.2: embeddings` on `2b6200d` (704 passed,
4 skipped; no files edited). Claude Code checked its claims against the repo: all hold
(`numpy` 2.3.5 locked transitively, not declared; `load_roots` in `safety/policy.py`
ignores unknown keys; no-proxy opener in `core/bridge_client.py`; opener reset in
`tests/test_core.py` `test_proxy_env_is_ignored`). Also found: `core/config.toml` `host`
already holds `http://127.0.0.1:11434`.

Answers, approved by Karthik ("Approve all") and written into `docs/plans/P4.md` section B
"Pre-edit answers": `config/memory.toml` OK; `numpy` declared in this commit (D4 gave the
reason 2026-11-21; the lock may only gain numpy as a direct dependency); allowed keys
exact; base URL a module constant; test 3 copies the full proxy pattern (dead-port
`HTTP_PROXY`, `NO_PROXY` removed, opener reset); tests 1, 2, 4 tightened so the
normalisation, `float32`, order and partial-result mutants can be killed. Mutant list: 11.

Files changed: `docs/plans/P4.md`, this file. Next step: Cursor implements section B as
amended and commits `P4.2: embeddings`.

### 2026-11-23 — Agent: Claude Code (P4 section B plan change approved)

Karthik approved the section B plan change ("Approve it"); `docs/plans/P4.md` marks it
APPROVED. Files changed: `docs/plans/P4.md`, this file. Next step: Cursor runs any
remaining "Verify before executing" lines that bear on section B, posts the pre-edit
summary for `P4.2: embeddings`, and waits for Karthik's go.

### 2026-11-23 — Agent: Claude Code (P4 section B re-measure: passed; plan change drafted)

Karthik chose option (a), set `OLLAMA_MAX_LOADED_MODELS=2` in his user environment and
restarted Ollama (process start 13:35:09; user value read back as 2). Same scratch script,
CPU mode, now sending the planned body: `options.num_gpu 0` and `truncate: false`.

- Idle: 1024 MiB used. `qwen3.5:4b` loaded (`num_ctx` 16384): 7.47 s, 3.31 GB, 100% GPU,
  5165 MiB used.
- Embedder load 0.84 s; 0.36 GB, 0% GPU. `/api/ps` then lists both models.
- 1 x 1000 chars: 0.18 s, 0.18 s, 0.19 s. 32 x 1000 chars: 5.38 s, 5.38 s, 5.48 s.
- VRAM after the embeds: 5165 MiB (unchanged). Both models still listed.
- 20000-character input with `truncate: false`: `HTTP 400`,
  `{"error":"the input length exceeds the context length"}`.
- Chat call after the embeds: `load_duration` 0.02 s (no reload), total 0.77 s.

Files changed: `docs/plans/P4.md` (section B plan change, DRAFT), `docs/PROGRESS.md`
(Decisions entry, open question resolved). Next step: Karthik approves or changes the
section B plan change; then Cursor posts the pre-edit summary for `P4.2: embeddings`.

### 2026-11-23 — Agent: Claude Code (P4 section B measurement: chat model evicted)

Karthik ran `ollama pull nomic-embed-text` (274 MB, success). Measured with a scratch
stdlib script (loopback `127.0.0.1:11434` only, no proxy, nothing written to the repo).
The chat model was loaded first the way core loads it (`num_ctx` 16384). VRAM read with
`nvidia-smi`, the same query `system_stats` uses. Ollama 0.40.17; RTX 3050 6 GB Laptop,
6144 MiB, 1070 MiB used with no model loaded.

- Route check (verify list): `POST /api/embed` with `{"model", "input": [..]}` answers
  `embeddings`, `load_duration`, `model`, `prompt_eval_count`, `total_duration`; one
  768-dim vector per input. `/api/ps` shows `nomic-embed-text` with context 2048.
- `qwen3.5:4b` loaded: 3.31 GB, 100% GPU, 5211 MiB used. Cold load 22.0 s (first since
  boot or pull).

| | GPU (default) | CPU (`num_gpu 0`) |
|---|---|---|
| Embedder load | 21.5 s (first load after the pull) | 1.85 s |
| Embedder size | 0.31 GB, 100% GPU | 0.36 GB, 0% GPU |
| 1 x 1000 chars | 10.23 s, 0.04 s, 0.06 s | 0.21 s, 0.20 s, 0.21 s |
| 32 x 1000 chars | 0.62 s, 0.58 s, 0.69 s | 5.76 s, 5.75 s, 5.80 s |
| VRAM after embeds | 1505 MiB (chat gone) | 1070 MiB (chat gone) |
| `qwen3.5:4b` after | evicted; reload 6.80 s | evicted; reload 6.54 s |

The first warm 1-chunk GPU call (10.23 s) is one sample; cause not investigated.

Cause: `OLLAMA_MAX_LOADED_MODELS=1` in Karthik's user environment, not VRAM. CPU mode
does not help, because the cap counts models wherever they run. Section B's fallback
assumed VRAM was the reason. Per the plan ("Do not continue on an unmeasured setup"),
section B stops here. Options (a) to (c) under Open questions; (a) recommended.

Also: `nomic-embed-text` runs at context 2048 tokens here. A 1000-character chunk is far
below that, but `/api/embed` truncates by default, so section C must keep chunks small
or send `"truncate": false` and fail loudly.

Files changed: `docs/PROGRESS.md`, `docs/plans/P4.md` (verify list: route and model
lines marked checked). Next step: Karthik picks (a), (b) or (c). For (a) or (b) he
changes the variable and restarts Ollama; then Claude Code re-runs the measurement and
writes the section B plan change for approval.

### 2026-11-23 — Agent: Claude Code (P4.1b test 12 review: accepted; P4.1b ticked)

Reviewed `6c713b0` (`P4.1b: re-read test`) against the A2 "Review addendum" in
`docs/plans/P4.md` (approved, `c8d016a`).

- Review check 1: files `tests/test_memory_store.py` and `docs/PROGRESS.md` only, as the
  addendum says. Check 2: no change to `memory/store.py`, `pyproject.toml`, `uv.lock`,
  `config/` or `safety/`. `memory/store.py` sha256 `821af9a32c96...` (same as `5586f9a`).
- Test 12 is the addendum's test: raw connection (`isolation_level=None`), WAL,
  `BEGIN IMMEDIATE` at `user_version` 0; `connect(path, "bridge")` in a thread; after
  0.5 s the raw connection runs `_SCHEMA`, sets `user_version = 1`, commits, closes; join
  10 s; the thread's error is re-raised; the opened connection is closed in `finally`.
- `tests/test_memory_store.py` from PowerShell: 25 passed, 1.89s. Full suite from
  PowerShell, `uv run python -m pytest`: 704 passed, 4 skipped, 198.32s (matches).
- Mutant re-run (scratch script, exact 3-line anchor found once, bytes restored in
  `finally`, sha256 `821af9a32c96...` before and after): baseline test 12 passed 5 of 5;
  second `user_version` read removed: killed 5 of 5, each
  `sqlite3.OperationalError: table meta already exists` (wall times 1.32-1.35s per run
  including interpreter start). Matches Cursor's 5 of 5.
- Note, not a finding: the 0.5 s sleep is what puts the opener's first read before the
  holder's commit. If the thread were slower than that, test 12 would pass on the mutant
  too (a missed kill, never a false failure). The 5 mutant kills show the opener reached
  the re-read on every run here.

P4.1b ACCEPTED, ticked in PLAN.md. Files changed: `docs/PLAN.md`, this file. Next step:
P4 section B. D1 is already answered (`nomic-embed-text`, 2026-11-21). Karthik runs
`ollama pull nomic-embed-text` (a download, his call) and the section B measurement; then
the implementer posts the pre-edit summary for `P4.2: embeddings`.

### 2026-11-23 — Agent: Cursor (P4.1b re-read test)

Added test 12 from the approved A2 review addendum (`c8d016a`).
`tests/test_memory_store.py` only. A raw connection (`isolation_level=None`) sets
WAL and holds `BEGIN IMMEDIATE` on a new file at `user_version` 0. A thread calls
`connect(path, "bridge")`. After 0.5 s the raw connection runs `_SCHEMA`, sets
`user_version = 1`, commits and closes. The thread must finish within 10 s with
a connection and no error. `memory/store.py` is unchanged.

`tests/test_memory_store.py`: 25 passed in 1.92s. Full suite from PowerShell,
`uv run python -m pytest`: 704 passed, 4 skipped, 252.25s (was 703 passed,
4 skipped). PLAN.md not ticked.

Mutant, applied to `memory/store.py` and restored after the five runs. sha256
before and after
`821af9a32c96e62bd82c50e4c51a84e2ffc69d4f2cbdcaa703f709c2aa6e1d9b`.

| Mutant | Test | Result |
|---|---|---|
| second `user_version` read removed | `test_re_read_skips_ddl_after_the_lock_holder_commits` | killed, 5 of 5 (0.61s, 0.65s, 0.64s, 0.60s, 0.62s; `table meta already exists`) |

Files: `tests/test_memory_store.py`, this file. Next: the reviewer re-runs test
12 and this mutant, then ticks P4.1b. Section B waits on Karthik's
`ollama pull nomic-embed-text` and the measurement.

### 2026-11-23 — Agent: Claude Code (P4.1b review: code accepted, test gap)

Reviewed `5586f9a` (`P4.1b: atomic schema`) against `docs/plans/P4.md` section A2 and its
approved plan change.

- Correction: earlier in this session Claude Code quoted two commit hashes it had not read
  from git (`5b4e3d8`, `c97cbd8`). The real ones are `374d9cf` (plan change, WAL retry)
  and `ee421bd` (mutant list). Content was as described.
- Review check 1: files `memory/store.py`, `tests/test_memory_store.py`,
  `docs/PROGRESS.md`; all named by A2 or the work loop. Check 2: no change to
  `pyproject.toml`, `uv.lock`, `config/` or `safety/`.
- Code is the plan: WAL pragma retried only on `locked`, 0.05 s, 100 tries, then raise;
  `foreign_keys` before the create; `BEGIN IMMEDIATE`, second `user_version` read, DDL
  tuple, `user_version = 1` last, `COMMIT`; error path `conn.rollback()`; version check and
  authorizer after. Tests 10 and 11 as planned.
- Suite re-run from PowerShell: 703 passed, 4 skipped (matches).
- Mutants re-run (scratch script, exact anchors, sha256 `821af9a32c96...` before and after,
  matches Cursor's): `BEGIN IMMEDIATE` removed killed by test 10; WAL retry removed killed
  by test 11; second read removed killed by test 11 in 1 of 5 runs (Cursor: 3 of 5).
- Finding (test gap, not a product bug): the WAL retry's sleep usually lets the first
  opener commit before the second reads, so test 11 rarely reaches the re-read. A
  deterministic test 12 (raw connection holds the write lock at version 0 until the opener
  waits) passes on the real code and killed that mutant 5 of 5 in a scratch run. Drafted
  as A2 "Review addendum", commit `P4.1b: re-read test`.

P4.1b not ticked (ticked after test 12 lands and is reviewed). Files changed:
`docs/plans/P4.md`, this file. Next step: Karthik approves the addendum; Cursor adds test
12 and runs that one mutant.

### 2026-11-23 — Agent: Cursor (P4.1b atomic schema)

Continued the uncommitted create from the stop below, after Karthik approved the
A2 plan change (`374d9cf`, `310f322`). `_SCHEMA` is a tuple of DDL statements.
`connect` retries only `PRAGMA journal_mode = WAL` when the error message
contains `locked` (sleep 0.05 s, 100 tries, then raise; any other error raises
at once), with the plan's ponytail comment. Then `foreign_keys = ON`. When
`user_version` is 0: `BEGIN IMMEDIATE`, read `user_version` again, and only if
it is still 0 run the DDL and set `user_version = 1`, then `COMMIT`. An error
on that path calls `conn.rollback()`; the outer handler closes once and
re-raises. `propose` is unchanged.

`tests/test_memory_store.py`: 24 passed in 1.37s. Full suite from PowerShell,
`uv run python -m pytest`: 703 passed, 4 skipped, 241.79s (was 701 passed,
4 skipped). PLAN.md not ticked.

Mutants, one at a time against `memory/store.py`, restored after each run.
sha256 before and after
`821af9a32c96e62bd82c50e4c51a84e2ffc69d4f2cbdcaa703f709c2aa6e1d9b`.
Baseline: `test_failed_ddl_rolls_back` passed; `test_two_openers_on_a_new_file`
passed.

| Mutant | Test | Result |
|---|---|---|
| `BEGIN IMMEDIATE` removed | `test_failed_ddl_rolls_back` | killed, 0.10s (tables left in `sqlite_master`) |
| second `user_version` read removed | `test_two_openers_on_a_new_file` | not killed on the recorded run (passed, 0.99s). Five more runs of the same mutant: failed 3, passed 2 |
| WAL retry removed | `test_two_openers_on_a_new_file` | killed, 0.21s (`database is locked` on the pragma) |
| `user_version = 1` moved before the DDL | — | not run, equivalent (rolls back with the transaction; measured on 3.49.1) |

The second read is still in `connect`. The WAL retry sleeps 0.05 s, and schema
creation usually finishes in that window, so the waiting opener often sees
`user_version` 1 on its first read and never uses the second one. Test 11 does
not kill that mutant on every run.

Files: `memory/store.py`, `tests/test_memory_store.py`, this file. Next: P4
section B, after Karthik runs `ollama pull nomic-embed-text` and the section B
measurement.

### 2026-11-23 — Agent: Cursor (P4.1b stopped: journal_mode locks a new file)

Karthik said go for `P4.1b: atomic schema` as in the pre-edit summary. `_SCHEMA`
is a tuple of DDL statements. `connect` sets `journal_mode = WAL` and
`foreign_keys = ON`, then when `user_version` is 0 takes `BEGIN IMMEDIATE`,
reads `user_version` again, runs the DDL and sets `user_version = 1` last, then
`COMMIT`. An error on that path runs `ROLLBACK`; the outer handler closes the
connection once and re-raises.

`uv run python -m pytest tests/test_memory_store.py`: 23 passed, 1 failed, 0.54s.
`test_failed_ddl_rolls_back` passed (bad last statement, `user_version` 0, empty
`sqlite_master`, then a real `connect` gets the schema). The two-opener test
failed on the first round. Full suite not run. Mutants not run. No code commit.
PLAN.md not ticked.

```
tests\test_memory_store.py:402: in test_two_openers_on_a_new_file
    raise errors[0]
tests\test_memory_store.py:387: in open_role
    conn = connect(path, role)
memory\store.py:67: in connect
    conn.execute("PRAGMA journal_mode = WAL")
E   sqlite3.OperationalError: database is locked
```

The two connections already exist when both execute that pragma, so this is the
A2 stop: the `journal_mode` pragma on a brand-new file. No retry added.

At that point the files were still uncommitted. Karthik approved the A2 plan
change (`374d9cf`, `310f322`). The bounded WAL retry is the entry above.

### 2026-11-23 — Agent: Claude Code (P4.1 review: accepted with one finding)

Reviewed `0092131` (`P4.1: memory schema`) and `bdb8307` against `docs/plans/P4.md`
section A and the pre-edit note (no UPDATE on `documents`).

- Review check 1: files are `memory/__init__.py`, `memory/store.py`,
  `tests/test_memory_store.py`, exactly section A's list. Check 2: no change to
  `pyproject.toml`, `uv.lock`, `config/` or `safety/`.
- Suite re-run from PowerShell: 701 passed, 4 skipped (matches).
- Mutants re-run (`%TEMP%` scratch script, exact anchors, one target test each, bytes
  restored in `finally`, sha256 `fe6f914b44e4...` before and after): baseline 5 targets
  pass; all 7 killed (OK for every INSERT; any PRAGMA; `chunks_ad` removed; UPDATE on
  `chunks` for ingest; cap removed; `foreign_keys` removed from `connect`; role check
  removed).
- Code is the plan: schema before the authorizer; rule 26 read codes; `data_version` only
  without a value; INSERT/DELETE per role, UPDATE only `meta` for ingest; bridge
  `check_same_thread=False`; `propose` checks the cap, stamps UTC ISO-8601, does not
  commit. All nine plan tests present (test 3 has all 11 refused statements).
- Finding (moderate, first create only): `_SCHEMA` sets `user_version = 1` before the
  `CREATE`s and `executescript` autocommits each statement. Probe: a script failing after
  the first `CREATE` leaves `user_version` 1 with only `meta`, and `connect` accepts it
  (then `no such table: facts`). Two first opens racing: `database is locked` 16 of 20.
  Opens of an existing file: 0 errors in 150 concurrent opens. Fix drafted as P4.1b,
  `docs/plans/P4.md` section A2 (DRAFT), before section C.
- Note for section E: `propose` leaves the transaction open; the bridge handler must
  commit under its lock, and a `Full` must not leave a transaction open.

P4.1 ticked in PLAN.md; P4.1b added unticked. Files changed: `docs/plans/P4.md`,
`docs/PLAN.md`, this file. Next step: Karthik approves or changes section A2; then Cursor
posts the pre-edit summary for `P4.1b: atomic schema`. Section B waits on Karthik's
`ollama pull nomic-embed-text` and the measurement.

### 2026-11-23 — Agent: Cursor (P4.1 memory schema)

Implemented `docs/plans/P4.md` section A after Karthik's go. Commit `0092131`
`P4.1: memory schema`. Files: `memory/__init__.py` (empty), `memory/store.py`,
`tests/test_memory_store.py`. Nothing in `safety/`, `bridge/`, `config/`,
`pyproject.toml`, or `PLAN.md` (not ticked).

`connect(path, role)` accepts `bridge`, `ingest`, and `review`. It creates the schema
when `user_version` is 0, refuses any other version, sets WAL and `foreign_keys` on
every open, then installs the authorizer. The bridge connection uses
`check_same_thread=False`. `propose` inserts one `pending_facts` row with a UTC
ISO-8601 `proposed` time and does not commit. The 51st call raises `Full` and the
table stays at 50. Ingest may UPDATE `meta` only. UPDATE on `documents`, `chunks`,
and `facts` is refused.

FTS5 writes seen on SQLite 3.49.1 before the code was committed, under that
authorizer: INSERT and DELETE on the virtual table and the shadow tables
`chunks_fts_data`, `chunks_fts_idx`, and `chunks_fts_docsize`, a valueless
`PRAGMA data_version`, and transaction BEGIN/COMMIT. No UPDATE on a shadow table.
The authorizer was not widened.

Tests after the commit, from PowerShell: `uv run python -m pytest` -> 701 passed,
4 skipped (was 679 passed, 4 skipped). `tests/test_memory_store.py` alone: 22 passed.

Mutants, one at a time against `memory/store.py`, restored after each run. sha256
before and after `fe6f914b44e48e6267267afdb4ac28871f05ec3534fb92277c0e19879980632f`.
Baseline 22 passed in 0.63s. All 7 killed:

| Mutant | Test | Result |
|---|---|---|
| authorizer returns OK for every INSERT | `test_bridge_refuses` | killed, 0.35s (2 of 11 no longer raised) |
| bridge authorizer allows any `SQLITE_PRAGMA` | `test_bridge_refuses` | killed, 0.35s (`writable_schema` and `data_version = 5`) |
| `chunks_ad` trigger removed | `test_delete_removes_fts_rows` | killed, 0.10s |
| UPDATE allowed on `chunks` for ingest | `test_roles_cannot_write_each_others_tables` | killed, 0.09s |
| cap check removed | `test_propose_cap` | killed, 0.12s |
| `foreign_keys` pragma removed | `test_delete_removes_fts_rows` | killed, 0.10s (second connection) |
| role check removed | `test_unknown_role` | killed, 0.11s |

Next: P4 section B. Karthik runs `ollama pull nomic-embed-text`, then the embed-time
and VRAM measurement in section B, before any code is built on that model.

### 2026-11-23 — Agent: Claude Code (P4 section A verify list; handed to Cursor)

Ran `docs/plans/P4.md` "Verify before executing" for section A. No code changed.

- P3 closed (`9d06b3a`). `safety/policy.py:71` `recall_memory` is `Rule(Tier.T0,
  text_params=("query",), taints=True)`, `MAX_TEXT = 200` (`:29`). No `recall_memory`
  handler in `bridge/`. `bridge/app.py:303` calls `handler({**args, **paths})`.
  `core/specs.py` holds the schema; `evals/stub_tools.py` builds stubs from `SPECS`;
  `tests/test_eval_set.py` pins 43 cases. Repo protected by default (`bridge/app.py:224`).
- `memory/` exists with only a tracked `.gitkeep` (plan said no folder): harmless, leave it.
- Venv: SQLite 3.49.1, `numpy` importable, `pypdf` not installed. `ollama list`: no
  embedding model (`qwen3.5:2b`, `4b`, `9b`).
- FTS5 probe on 3.49.1 (`:memory:`, section A tables and triggers, scratch script, `-I`):
  `MATCH` ordered by `bm25()` returns both rows in order; deleting a `documents` row
  cascades and the deleted chunk's only word no longer matches; `integrity-check` passes.
  Under an authorizer allowing only rule 26's codes the search works, and these are
  refused: INSERT and DELETE on `chunks`, `PRAGMA data_version = 5`, `delete-all`,
  `DELETE FROM chunks_fts_data`, `SELECT load_extension('x')`. Codes seen during the
  search: SELECT, READ on `chunks`, `chunks_fts`, `chunks_fts_idx`, `chunks_fts_docsize`,
  FUNCTION, PRAGMA `data_version` (no value). Nothing outside rule 26.
- Not checked (later sections): Ollama `/api/embed` (before B), tool result length (D).
- Plan gap for the implementer to note, not to fix in A: the design says `memory.db` is
  `protect()`-ed like the audit log, but no section says who calls it. The file lives in
  `%LOCALAPPDATA%\Jarvis` (already user-only); section D, where the bridge first opens it,
  is the natural place.

Karthik: "Hand it to Cursor". Files changed: `docs/plans/P4.md` (verify line), this file.
Next step: Cursor re-runs the verify list, posts the pre-edit summary for
`P4.1: memory schema` (files: `memory/__init__.py`, `memory/store.py`,
`tests/test_memory_store.py`; nothing in `safety/`, `bridge/`, `config/`,
`pyproject.toml`), waits for Karthik's go, then implements section A with the 7 mutants.

### 2026-11-23 — Agent: Claude Code (P3.6 manual steps 1 and 2: PASSED; P3.6 ticked, P3 closed)

Start-of-session protocol: tree had only the `.gitignore` line for `graphify-out/`
(graphify output, regenerable; committed here). Suite from PowerShell: 679 passed,
4 skipped. (From Git Bash the suite fails to import `safety`; run it from PowerShell.)

Manual check on `4fc949e`, bridge restarted (`start` 04:50:09.918Z). Audit lines read by
Claude Code from `%LOCALAPPDATA%\Jarvis\audit.jsonl`:

- Step 1 PASS: CLI printed the time and `get_time: ok`. Task `ebcf9d96...`: `task`
  04:51:53.106Z, `request get_time allow T0` .111Z, `result done` .112Z, `end`
  `cancelled: null` .126Z.
- Step 2 PASS: CLI printed `pending ae7230663b79492a843e1144f5fbae1c`. Task
  `cb361677...`: `task` 04:56:25.681Z, `request delete_file confirm T2` 04:56:26.775Z,
  `queued` .776Z, Ctrl+C at 04:56:28.83Z, `end` with `cancelled: ae723066...` at
  04:56:29.156Z (0.33 s later). CLI printed `cancelled`, exit 1 after 0.63 s. `/pending`
  empty; `c.txt` still there (`Test-Path` True, re-checked by Claude Code). Before D the
  same step ended at the 120 s expiry with `cancelled: null`.
- Limit: the Ctrl+C was a real console Ctrl+C event sent to that console by a helper
  script, not a key press by Karthik. Karthik relayed the result and accepted it.
- Steps 3 and 4 passed on `f6f0526`; D does not touch them (plan).

P3.6 ticked in PLAN.md. With P3.7 ticked and the "Done when" passed 2026-11-18, P3 is
closed. Files changed: `docs/PLAN.md`, this file, `.gitignore`. Next step: P4 section A
(see Current state).

### 2026-11-21 — Agent: Claude Code (P3.6 D review: accepted)

Reviewed `0d735ed` against `docs/plans/P3.6.md` section D and the go's one addition (the
`daemon=False` row recorded as not run). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 679 passed, 4 skipped (matches).
- Mutants re-run (read `%TEMP%\p36d_mutants.py` first: patches `core/__main__.py` and
  `core/agent.py` by exact anchors, one target test per mutant, run one at a time,
  restores the bytes in `finally`, checks both sha256): baseline 3 passed; all 5 killed
  (untimed `join()` 124.8 s, `cancel()` removed 10.5 s, `main` handler removed 4.7 s,
  `_task_id` check 2.9 s, exception not re-raised 3.0 s). sha256 before and after:
  `core/__main__.py` `7379d7b8...b09a7`, `core/agent.py` `af1e6fbb...21dc`; tree clean.
  Before the go, Claude Code checked that an untimed `thread.join()` is not interruptible
  on 3.12.10 (KeyboardInterrupt at 4.0 s for a 4 s worker), so the first mutant was
  killable; the 124.8 s run confirms it.
- Code is the plan: `cancel()` checks `_task_id` and calls `_end()` (the check stays out
  of `_end`); `_handle` hands the result or any `BaseException` back through the box;
  `join(0.2)` loop with the `ponytail:` comment; `except KeyboardInterrupt` sits before
  the existing handlers, which are unchanged.
- Test 1 reads the first `end` line for the task (the cancel's), checks all seven values
  in one tuple, and waits for the second `end` (from `handle`'s `finally`) before the
  fixture tears down.
- No finding. Note: a Ctrl+C that lands after `_handle` returned (while results print)
  prints `cancelled` without a cancel; the task is already ended by `handle`'s `finally`,
  so nothing is left to cancel.

PLAN.md not ticked. Files changed: this file. Next step: Karthik re-runs manual steps 1
and 2 (`docs/plans/P3.6.md`); then the reviewer ticks P3.6, which closes P3.

### 2026-11-21 — Agent: Cursor (P3.6 D)

Section D, on Karthik's go. Ctrl+C during a pending delete waited out the 120 s expiry
because the main thread was blocked in `future.result`.

Red run, test 1 alone, before the product change (`uv run python -m pytest
tests/test_core.py::test_ctrl_c_cancels_the_pending_action`): failed in 132.55 s.
`KeyboardInterrupt` instead of exit 1 (`code` None, `interrupted` True), `cancelled`
null, last output line empty, not under 5 s. The file was still there. `/pending` was
already empty because the action had expired.

- `core/agent.py`: `cancel()` next to `_end`. It calls `_end()` only when `_task_id`
  is not `None`. `_end` is unchanged.
- `core/__main__.py`: `_handle` runs `handle` on a daemon thread and waits in
  `join(0.2)` steps. On `KeyboardInterrupt` it calls `cancel()` and re-raises. `main`
  prints `_handle(...)` and catches `KeyboardInterrupt` first: `cancelled`, exit 1.
  The `URLError` and `(OSError, BridgeError)` handlers are unchanged.
- `tests/test_core.py`: the live-bridge Ctrl+C test, `cancel()` before a request, and
  a stub `handle` that raises `URLError`. Existing CLI tests were not edited.
- Files: those three, `docs/plans/P3.6.md`, this file. PLAN.md not ticked. Nothing in
  `OpenJarvis/`, `bridge/`, `safety/`, `config/`, `.claude/`, or `evals/`. No new
  dependency.
- Tests: `uv run python -m pytest` from PowerShell -> 679 passed, 4 skipped.
- Mutants (`%TEMP%\p36d_mutants.py`, in memory, baseline first, one at a time):
  baseline 3 passed.

  | Mutant | Killed by | Result |
  |---|---|---|
  | one `thread.join()` with no timeout | 1 | killed (123 s; `cancelled` null. The interrupt landed when `join()` returned at the expiry) |
  | `core.cancel()` removed | 1 | killed (9.9 s; `cancelled` null, `/pending` not empty) |
  | `except KeyboardInterrupt` removed from `main` | 1 | killed (4.8 s; no exit 1) |
  | `_task_id` check removed from `cancel` | 2 | killed (`end(None)`) |
  | the thread's exception not re-raised | 3 | killed (no `SystemExit`) |
  | `daemon=True` -> `daemon=False` | not run | only delays process exit after the cancel; manual step 2 covers it |

  Restored, sha256 before and after: `core/__main__.py`
  `7379d7b8b526481a75bf49d17279d71f21cabcb8f8cb74fc26a12b888ebb09a7`,
  `core/agent.py`
  `af1e6fbbf8476e739ba3990ae959b0217a6e1417011270d46201c64149bd21dc`.
- Stopped at: this commit. Next: Claude Code reviews D. Then Karthik re-runs manual
  steps 1 and 2. The reviewer ticks P3.6 after that, which closes P3.

### 2026-11-21 — Agent: Claude Code (P3.6 manual check: step 2 failed; section D planned)

Karthik's manual check on `f6f0526` (run 2026-11-20) (bridge restarted on that commit):

- Step 1 PASS: task `acf4b787...`: `task`, `request` (allow), `result`, `end`, in order,
  same `task_id`.
- Step 3 PASS: at 19:08:29 IST (step 1 ended 19:03:17), a new request, then `/tool` with
  `acf4b787...` -> 404 `Unknown task`.
- Step 4 PASS: stub evals 43/43 (tool selection 28/28, args 26/26, must-refuse 10/10,
  clarify 5/5, fast path 5/43, median 1.5 s, max 9.3 s).
- Step 2 FAIL: Ctrl+C at `pending 987a0d84...`. Task `26cdbca0...`: `task` 13:48:44.74Z,
  `request` queued 13:48:54.95Z, `expired` 13:50:44.880Z, `end` 13:50:44.888Z with
  `cancelled: null`. Nothing deleted, queue empty, `c.txt` intact. (An earlier remote
  attempt sent a console Ctrl+C that never reached the process; same expiry outcome.)

Cause (Claude Code): not the bridge. OpenJarvis runs the tool on a worker thread and the
main thread waits in `future.result(timeout=...)` (`OpenJarvis/src/openjarvis/tools/_stubs.py:449`).
On Windows, CPython 3.12 does not interrupt one long lock wait with Ctrl+C; the
`KeyboardInterrupt` surfaces only when the worker's `/outcome` poll ends at the expiry,
then C's `finally` sends `/end` 8 ms later. Reproduced on 3.12.10 (4 s worker, SIGINT at
0.5 s): `future.result(timeout=60)` interrupted at 4.0 s, a `join(0.2)` loop at 0.6 s;
`_thread.interrupt_main()` behaves the same. Karthik's hypothesis (`/end` queued behind
the `/tool` long-poll) does not hold: `/tool` had already answered 202, and the bridge
logged `end` 8 ms after the core sent it.

Fix planned with Karthik's OK: `docs/plans/P3.6.md` section D. The CLI runs `handle` on a
daemon thread and waits in `join(0.2)` steps; on `KeyboardInterrupt` it calls the new
`Core.cancel()` (ends the current task if one exists), prints `cancelled`, exits 1.
Regression test: a live-bridge request held pending, `_thread.interrupt_main()` from
`on_pending`, then exit 1 in under 5 s, `end` with the pending id, `/pending` empty, file
intact. Manual step 2 revised; after D, re-run steps 1 and 2.

P3.6 not ticked. No code changed. Files changed: `docs/plans/P3.6.md`, this file. Next
step: Cursor runs section D's verify list and posts its pre-edit summary. This replaces
"Next step unchanged: Karthik's 4-step P3.6 manual check" in the two P4 entries below:
P3.6 D, then manual steps 1 and 2 again, come before P4 section A.

### 2026-11-21 — Agent: Claude Code (P4 plan approved)

Karthik approved the P4 plan ("approve the P4 plan"), D1 to D9 taken as recommended, as
for P3.6. `docs/plans/P4.md` header is now APPROVED with the answers; PLAN.md's P4 line
says approved (no task ticked); Decisions records the two new dependencies and why. No
code changed; tests not run (docs only).

Files changed: `docs/plans/P4.md`, `docs/PLAN.md`, this file. Next step unchanged:
Karthik's 4-step P3.6 manual check, then the reviewer ticks P3.6 and P3 closes. Then P4
section A: the implementer re-runs the plan's verify list (including the FTS5 line on the
venv's SQLite 3.49.1), posts the pre-edit summary for `P4.1: memory schema`, and waits
for Karthik's go. Section B needs Karthik first: `ollama pull nomic-embed-text` and the
measurement.

### 2026-11-21 — Agent: Claude Code (P4 draft updated from the awesome-llm-apps review)

Karthik asked whether Shubhamsaboo/awesome-llm-apps (Apache-2.0) could improve Jarvis's
memory and RAG. Read-only review of `rag_tutorials/qwen_local_rag`,
`local_hybrid_search_rag` (and raglite 0.2.1's `_search.py`, the code behind it),
`corrective_rag` and `agent_skills/scope-creep-detector`, all in a scratch folder outside
the repo. Verdicts: keyword+vector search merged by RRF, adopt in P4; chunk overlap,
section G lever; LLM relevance grading, section G lever (quality only, never a safety
control; the example keeps a chunk when grading fails); diff-vs-plan check, adopt in
review. Not copied: prompt-pasted context, web or "general knowledge" fallbacks, vector
DB servers, URL/upload ingest. Karthik: "do the recommended plan".

Changed `docs/plans/P4.md` only (still DRAFT): header note; verify-list line for FTS5 on
the venv's SQLite; design bullet; D9; rules 24 (quoted FTS5 query), 25 (no UPDATE on
`chunks`/`facts`), 26 (read codes every role allows); review checks; section A FTS5
tables, triggers, role writes, tests 3, 4, 7, 9 and mutants; section C test 2; section D
search steps (vector, keyword, `rrf`, cosine floor), tests and mutants; section G
exact-term questions, vector-vs-hybrid report, overlap and grading levers; manual check
step 2; "Not in P4".

Probe (Python, SQLite 3.53.1 on Linux, scratch folder, not the Windows venv): an
external-content FTS5 table with insert/delete triggers works; a cascade delete from
`documents` fires `chunks_ad`; quoting each `\w+` word stops `NOT`, `AND`, `"` and `*`
from raising FTS5 errors; "what is my passport number" matches any chunk containing
"my" (why the floor stays on the cosine). Found: every FTS5 search runs
`PRAGMA data_version` and the functions `match` and `bm25`, so the draft's bridge
authorizer (SELECT/READ plus one INSERT) would have refused every search, and also the
draft's own `data_version` cache check. Rule 26 allows only the read form of that pragma;
`PRAGMA data_version = 5`, `writable_schema` and FTS writes stay refused (probed).

Tests not run: docs-only change, and this cloud container has no `OpenJarvis/` clone and
no Windows venv. No code changed. Next step unchanged: Karthik's 4-step P3.6 manual check,
then the reviewer ticks P3.6 (closes P3). Before P4 section A: re-run the verify list,
including the FTS5 line on SQLite 3.49.1.

### 2026-11-20 — Agent: Claude Code (P3.6 C review: accepted)

Reviewed `6528c0d` against `docs/plans/P3.6.md` section C (tests 1 to 9) and the go's two
additions (red-run reasons for 1 to 3; test 1 ties the `end` line to `core._task_id` and
reads the audit before the direct `/tool`). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 676 passed, 4 skipped (matches).
- Mutants re-run (read `%TEMP%\p36c_mutants.py` first: patches `core/agent.py` by exact
  anchors, one target test per mutant, restores the bytes in `finally`, checks sha256):
  baseline 9 passed; all 5 killed. sha256 before and after `480c2821...642cd`, tree clean.
  `finally` -> `except Exception: raise` + `else` is the same control flow as a bare
  `else` and parses; test 3 kills it (`[] == ['t1']`). Stale id: `[None, 't1']`.
  `try` before `new_task`: `end(None)` ran.
- Code is the plan: `new_task` outside the `try`; both paths inside it; `_end` catches
  `OSError` only and ignores the status (rule 13). `BridgeClient.end` is one line. Stop
  path, `self.results` lines and the fresh-context reset unchanged.
- Tests 1 and 2 use the real bridge: `/tool` on the ended task -> 403 `task stopped`, and
  the last `end` line follows the last `result` with the same `task_id`.
- No finding. Note: test 4 does not itself assert that `end` was called; tests 3, 5 and 6
  do, so nothing is uncovered.

PLAN.md not ticked: Karthik's 4-step manual check comes first. Files changed: this file.
Next step: Karthik runs the manual check in `docs/plans/P3.6.md`; then the reviewer ticks
P3.6, which closes P3.

### 2026-11-20 — Agent: Cursor (P3.6 C)

Section C, on Karthik's go. A finished request left its task usable for the rest of its
120 s. The core now tells the bridge the request is over.

Red run, tests only, before the product change (`uv run python -m pytest` on the nine new
tests, `-vv`): 6 failed, 3 passed. Tests 4, 7 and 9 stayed green, as agreed.

- Test 1 (agent path) and test 2 (fast path): `/tool` answered 200, `assert (200 == 403)`.
  The audit was read before that call.
- Test 3: `pytest.raises(RuntimeError)` passed, then `assert [] == ['t1']` (`end` was not
  called).
- Tests 5, 6 and 8 failed because `end` is never called today (`ValueError` did not raise).

- `core/bridge_client.py`: `end(task_id)` is `_post("/end", {"task_id": task_id})`. Nothing
  else in the file changed.
- `core/agent.py`: `new_task` stays outside `try`. Everything after it runs in `try`;
  `finally` calls `_end()`. `_end` calls `end(self._task_id)` and swallows `OSError` only.
  A non-200 is ignored. The stop path and the `self.results` lines are unchanged.
- `tests/test_core.py`: tests 1 and 2 use `live_bridge`. Test 1 checks the `end` line's
  `task_id` is `core._task_id` on the snapshot taken before the direct `/tool`. Tests 3
  to 9 use `CountingClient`.
- Files: those three, `docs/plans/P3.6.md`, this file. PLAN.md not ticked. Nothing in
  `bridge/`, `safety/`, `config/`, `.claude/`, or `evals/run.py`. No new dependency.
- Tests: `uv run python -m pytest` from PowerShell -> 676 passed, 4 skipped.
- Stub evals: `uv run python evals/run.py` -> 43/43 (tool selection 28/28, arguments
  26/26, refusals 10/10, clarify 5/5, fast path 5/43). Same score as before.
- Mutants (`%TEMP%\p36c_mutants.py`, in memory, baseline first): baseline 9 passed.

  | Mutant | Killed by | Result |
  |---|---|---|
  | `finally` to `else` | test 3 | killed (`assert [] == ['t1']`). A bare `else` is a `SyntaxError`, so the run re-raises and then uses `else` |
  | `except OSError` removed | test 4 | killed (`URLError` propagated) |
  | `end` with the previous id | test 6 | killed (`[None, 't1']`, wanted `['t1', 't2']`) |
  | `except Exception` | test 8 | killed (`ValueError` swallowed) |
  | `try` starts before `new_task` | test 9 | killed (`end(None)` ran) |

  `core/agent.py` restored, sha256
  `480c28217acc12b261821514249de9bc442801d908998f07fbf7a98596c642cd`
  before and after.
- Stopped at: this commit. Next: Claude Code reviews C. Then Karthik's 4-step manual
  check in `docs/plans/P3.6.md`. The reviewer ticks P3.6 after that.

### 2026-11-20 — Agent: Claude Code (P3.6 verify list for C; tests 8 and 9)

Cursor stopped before section C: two B and C verify lines in `docs/plans/P3.6.md`
described the code before section B (`evict()` "still deletes with `del`"; "No `/end`
route yet"). Both false on `6628533`: `bridge/app.py:365-369` uses `pop(key, None)`,
`:104` and `:549` add `POST /end`. Rewritten with Karthik's OK: the pre-B facts moved to
the historical paragraph; new lines for `/end` and for P3.7 E's 502 on a body that is not
a JSON object. Section C gains test 8 (`end` raises `ValueError` -> propagates; kills
`except Exception`) and test 9 (`new_task` raises `BridgeError` -> `end` never called;
kills a `try` that starts before `new_task`), with both mutants. No code changed.

Files changed: `docs/plans/P3.6.md`, this file. Next step: Cursor re-runs the verify list
and posts the pre-edit summary for section C.

### 2026-11-20 — Agent: Claude Code (P3.7 E review: accepted; P3.7 ticked)

Reviewed `8087ccc` against `docs/plans/P3.7.md` section E and the go's three additions
(D1 line, cases `ok-ff-200`, `list-500`, `empty-200`, exact `detail`). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 667 passed, 4 skipped (matches).
- Code is the plan: one `answer` helper on both `_post` paths; `except ValueError` covers
  `UnicodeDecodeError` (checked: `json.loads(b"okÿ")` raises it, not `JSONDecodeError`);
  non-dict -> 502 with the original status; empty body still `{}`. `__main__` keeps
  `URLError` first, then `(OSError, BridgeError)` -> one line, exit 1.
- Mutants (reviewer's own, E has no plan table; script
  `p37e_mutants.py` in the session scratchpad under `%TEMP%`, patches bytes, runs
  `-k "odd_answer or cli_"`, restores in `finally`): baseline 11 passed; 8 of 8 killed.

  | Mutant | Killed by |
  |---|---|
  | `ValueError` -> `JSONDecodeError` | `ok-ff-200` |
  | dict check removed | `list-200`, `list-500` |
  | `raw or b"{}"` -> `raw` | `empty-200` |
  | success path skips the helper | `non-json-200` |
  | `HTTPError` path skips the helper | `plain-text-500` |
  | status dropped from `detail` | exact `detail` assert |
  | `BridgeError` not caught | CLI `BridgeError` |
  | `OSError` caught before `URLError` | `test_cli_says_when_the_bridge_is_down` |

  sha256 after restore: `core/bridge_client.py` `f8b252a2...35fe0`, `core/__main__.py`
  `29a61fb1...49d1d`, both equal to before; tree clean.
- Finding (minor, docs): section E's heading still reads "Karthik writes it" and its first
  line "The code is Karthik's". D1 is correct. Left as is: a plan wording change goes to
  Karthik first.

PLAN.md: P3.7 ticked (all sections accepted; A's manual check passed 2026-11-20).
Files changed: `docs/PLAN.md`, this file. Next step: P3.6 section C (`P3.6: core ends
task`): Cursor re-runs the P3.6 verify list (now on top of E) and posts its pre-edit
summary.

### 2026-11-20 — Agent: Cursor (P3.7 E)

Section E, on Karthik's go. Reassigned from Karthik (D1). A bridge body that was not a
JSON object raised inside `json.loads` or came back as data, and a socket error other
than `URLError` escaped the CLI.

Red run, tests only, before the product change (`uv run python -m pytest` on the two new
tests, `-vv`): 8 failed, 1 passed.

- plain-text 500: `JSONDecodeError`
- non-JSON 200: `JSONDecodeError`
- `[1]` with 200: `(200, [1])`, wanted 502
- `b"ok\xff"` with 200: `UnicodeDecodeError`
- `[1]` with 500: `(500, [1])`, wanted 502
- empty body with 200: passed, `(200, {})`
- CLI `TimeoutError`, `ConnectionResetError`, `BridgeError`: each escaped the `URLError`
  handler

- `core/bridge_client.py`: both `_post` paths call `answer`. `ValueError` from
  `json.loads` (so `JSONDecodeError` and a non-UTF-8 body), or a value that is not a
  dict, returns `502, {"detail": "bad answer from bridge (<status>)"}` with the original
  status. Empty bytes still parse as `{}`. `new_task` is unchanged.
- `core/__main__.py`: `URLError` stays first and still prints `bridge is not running`.
  Then `(OSError, BridgeError)` prints one `bridge error: ...` line and exits 1.
- `tests/test_core.py`: six server cases (the empty 200 is not refused) and three CLI
  cases. `test_cli_says_when_the_bridge_is_down` unchanged.
- Files: `core/bridge_client.py`, `core/__main__.py`, `tests/test_core.py`,
  `docs/plans/P3.7.md` (status Implemented; D1 names Cursor), this file.
  PLAN.md not ticked. Nothing in `safety/`, `bridge/`, `config/`, or `.claude/`.
  No new dependency. No mutant table (the plan's mutant rule covers A, B, B2, and C).
- Tests: `uv run python -m pytest` from PowerShell -> 667 passed, 4 skipped.
- Stopped at: this commit. Next: Claude Code reviews E. P3.6 section C
  (`P3.6: core ends task`) is unblocked and gets its own prompt.

### 2026-11-20 — Agent: Claude Code (P3.6 B review: accepted)

Reviewed `b90ab92` against `docs/plans/P3.6.md` section B (with the `pop` plan change and
the two review additions to the go). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 658 passed, 4 skipped (matches).
- Mutants re-run (read `%TEMP%\p36b_mutants.py` first: patches `bridge/app.py`, one
  selector per mutant, restores the bytes in `finally`): baseline 10 passed; all 6
  killed. The "not taken" mutant still writes the pending id on the `end` line, so only
  the "no separate `cancelled` event" assertion kills it, as intended. sha256 before and
  after `7d01c455...b120`, tree clean.
- Code is the plan: unknown task logs `end` with `task_id` and `refused`, 404; a known
  task is stopped first, its queued action taken and settled `cancelled`, then logged;
  a failed write still answers 200 `logged: false` with the task stopped (rule 18).
  `halted` and `context_tainted` untouched. `evict()` uses `pop(key, None)` for all three
  dicts. The token, loopback and wrong-role sweeps cover `/end` from `ROUTE_ROLES`.
- Tests: test 4 checks the `end` line's `cancelled` and that no `expire()` `cancelled`
  line exists (review addition 1); test 5 checks `task_id` on the unknown line
  (addition 2); test 10 was red on `del` (`KeyError`) before the fix.
- No finding. Note: `/end` on a task already out of time labels its action `cancelled`,
  not `expired`; the `end` line names it, and nothing can run either way.

PLAN.md not ticked. Files changed: this file. Next step: section C (`P3.6: core ends
task`) after Karthik commits P3.7 E (`P3.7: client survives odd answers`).

### 2026-11-20 — Agent: Cursor (P3.6 B)

Section B, on Karthik's go. A finished request's task stayed usable for the rest of its
120 s, and two overlapping sweeps could `KeyError` on the same old task.

Test 10 was written first, against `del` in `evict()`. Red run: `KeyError` from
`del tasks[task_id]` on the first `/task` (the sandbox client re-raises; a live server
would answer 500). Then `evict()` switched to `pop(key, None)` for `tasks`, `outcomes`
and `owners`.

- `bridge/app.py`: `ROUTE_ROLES["/end"] = {"core"}`, `EndRequest`, `POST /end`. An unknown
  id logs `end` with `task_id` and `refused: "unknown task"` (a failed write is 500). A
  known id is stopped, its queued action is taken and settled `cancelled`, then `end` is
  logged with `cancelled` set to that id or null. The answer is `{"status": "ended",
  "logged": <bool>}` even when the write fails. No latch. A running handler is left running.
- `tests/test_bridge.py`: `POST /end` in the route table, tests 2 to 10. Test 4 checks the
  `end` line's `cancelled` id and that no separate `cancelled` event was written. The
  token, loopback, and wrong-role sweeps picked `/end` up from the live table.
- Files: `bridge/app.py`, `tests/test_bridge.py`, `docs/plans/P3.6.md`, this file.
  PLAN.md not ticked. Nothing in `safety/`, `config/`, or `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 658 passed, 4 skipped.
- Mutants (`%TEMP%\p36b_mutants.py`, in memory, baseline first): baseline 10 passed.

  | Mutant | Killed by | Result |
  |---|---|---|
  | `stopped = True` removed | test 2 | killed (`/tool` 200, wanted 403) |
  | queued action not taken | test 4 | killed (a `cancelled` event line) |
  | every task stopped | test 4 | killed (a `cancelled` event line for the other task) |
  | role `{"core", "ui"}` | test 3 | killed (200, wanted 403) |
  | failed `end` write returns before `stopped = True` | test 7 | killed (`/tool` 200, wanted 403) |
  | `tasks.pop` back to `del` | test 10 | killed (`KeyError` on the first `/task`) |

  `bridge/app.py` restored, sha256
  `7d01c455928fad446b271e0804d0ba6ec9ba4f66bb1b86153cb5a12a5895b120`.
- Stopped at: this commit. Next concrete step: Claude Code reviews B before section C.
  Section C still waits for `P3.7: client survives odd answers`.

### 2026-11-20 — Agent: Claude Code (P3.6 verify list updated for B and C)

Cursor stopped before section B: four "Verify before executing" lines in
`docs/plans/P3.6.md` described the code before section A (the `ponytail: never evicted`
comments, the eight `outcomes[...]` writes, `/approve` indexing `tasks[...]`, `/task` not
calling `expire()`). All four claims checked true on `3ff0472`. The re-check of
2026-11-20 had not written lines for the state after A. Rewritten with Karthik's OK: the
pre-A lines kept as one historical paragraph; new lines for B and C (`settle()` is the
only `outcomes` write; `/approve` uses `.get`; `/task` runs `expire()` then `evict()`,
which still uses `del`; no `/end` yet; `for_task` and `take` return the action or `None`,
`safety/confirm.py:62-68`). Unchanged lines still hold (Cursor). No code changed.

Files changed: `docs/plans/P3.6.md`, this file. Next step: Cursor re-runs the verify list
and posts the pre-edit summary for section B.

### 2026-11-20 — Agent: Claude Code (P3.6 A review: accepted)

Reviewed `60e33ef` against `docs/plans/P3.6.md` section A. No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 649 passed, 4 skipped (matches).
- Mutants re-run (read `%TEMP%\p36a_mutants.py` first: it patches `bridge/app.py`, runs
  one `-k` per mutant, restores the bytes in `finally`): baseline 10 passed; all 6
  killed; the equivalent row not run. sha256 before and after
  `b08798fc...094d`, tree clean. Stub evals not re-run (bridge-only change; Cursor: 43/43).
- Code is the plan: `settle` is the only `outcomes[...]` write (the `execute` tuple is
  split, as allowed); `expire()` checks out-of-time before stopped, which the existing
  `test_expiry_found_by_tool_call` also pins; `/task` runs `expire()`, then `evict()`,
  before the `halted` check; `/approve` looks the task up before any outcome and stores
  none when it is gone. Both review additions (race comment, 404 note in the `evict()`
  docstring) are in. No existing test changed.
- Minor, plan change proposed (Karthik decides): `evict()` deletes with `del`. Two
  `/task` calls at once can both pick the same old task; the second `del tasks[...]` (or
  `del outcomes[...]`) raises `KeyError`, so that `/task` answers 500 and makes no task.
  Fails closed, and needs two concurrent `/task` calls (two core processes). Fix:
  `pop(key, None)` for the three deletes, in section B's commit (same file), with one
  test that forces the overlap the way test 9 does: wrap `ConfirmQueue.for_task` so the
  first call inside a sweep lets a second `/task` finish, then expect 200.
- Minor, no action: an `/approve` for a task older than `KEEP` whose action was still
  queued (no route ran `expire()` since), racing a `/task` sweep that copied `owners`
  before the approve's `settle`, leaves one outcome that is never evicted. Rare and
  bounded to one small entry.
- Test 9 shares the running `TestClient.portal` with a second client (a Starlette
  internal). If Starlette changes it, the test fails loudly, not silently.

PLAN.md not ticked. Files changed: this file. Next step: Karthik decides the `pop`
change; then Cursor posts the pre-edit summary for section B (`P3.6: end route`).
Decided the same day: Karthik approved it; `docs/plans/P3.6.md` section B now has the
`pop` bullet, test 10 and its mutant.

### 2026-11-20 — Agent: Cursor (P3.6 A)

Section A, on Karthik's go. Nothing left `tasks` or `outcomes`, and a stopped task kept
its pending action until the time budget ran out.

Red run before the code, ten tests: 9 failed, 1 passed.
`test_old_task_is_not_evicted_without_a_new_task` passed, because that is already true.
The other nine failed on the missing sweep: no 404 for an old task, a denied outcome
still answered 200, a failed `expired` write still returned 200 from `/task`, a stopped
task's action stayed in `/pending`, and approve after a forced sweep was still the
time-budget 410.

- `bridge/app.py`: `KEEP = 2 * MAX_SECONDS`. `owners` beside `outcomes`. `settle` is the
  only `outcomes[...] =` write. `expire()` still drops an out-of-time action first, then
  a stopped one as `cancelled` (failed write returns before the take). `evict()` forgets
  tasks older than `KEEP` with nothing queued, and their outcomes. Its docstring says an
  evicted outcome now answers 404 instead of 410. `/task` calls `expire()` then `evict()`
  and nowhere else calls `evict()`. `/approve` looks the task up with `tasks.get` straight
  after `take`, with a one-line comment on that race; `None` logs `recheck: "task gone"`,
  answers 410, and stores no outcome. The `execute` result is passed through `settle`.
- `tests/test_bridge.py`: the ten tests. Test 9 drives the race with a second thread that
  posts `/task` on a `TestClient` sharing the already-running portal, then joins before
  `take` returns. It did not hang. No existing test failed, so none was edited.
- Files: `bridge/app.py`, `tests/test_bridge.py`, `docs/plans/P3.6.md`, this file.
  PLAN.md not ticked. Nothing in `safety/`, `config/`, or `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 649 passed, 4 skipped.
- Mutants (`%TEMP%\p36a_mutants.py`, in memory, baseline first): baseline 10 passed.

  | Mutant | Killed by | Result |
  |---|---|---|
  | `>` to `>=` in `evict` | test 1 | killed |
  | `KEEP = MAX_SECONDS` | test 3 | killed |
  | `evict()` before `expire()` | test 6 | killed (`/tool` 403, not 404) |
  | outcomes not removed | test 3 | killed |
  | `stopped` branch removed | test 7 | killed |
  | `.get` back to `[]` | test 9 | killed (`KeyError`) |
  | `queue.for_task(id) is None` removed | equivalent | not run |

  `bridge/app.py` restored, sha256
  `b08798fc911c37fcf12cf3e1f7659e2d31fad182849dd640f19e602b1622094d`.
- Stub evals, one run: tool selection 28/28, arguments 26/26, must-refuse 10/10,
  clarify 5/5, all 43/43, fast path 5/43, median 1.7 s, max 27.3 s. Same score as the
  last recorded stub run.
- Stopped at: this commit. Next concrete step: Claude Code reviews A before section B.
  Section C still waits for `P3.7: client survives odd answers`.

### 2026-11-20 — Agent: Claude Code (P3.6 plan approved)

Cursor stopped on the DRAFT header, as it should (tree clean at `9d39f5c`, no E work in
the tree). Karthik answered D1 to D3, all as recommended. `docs/plans/P3.6.md` header is
now APPROVED with the answers; PLAN.md's P3.6 line says approved (not ticked). No code
changed.

Files changed: `docs/plans/P3.6.md`, `docs/PLAN.md`, this file. Next step: Cursor posts
the pre-edit summary for section A (`P3.6: evict tasks`) and waits for Karthik's go.

### 2026-11-20 — Agent: Claude Code (P3.6 draft re-checked and updated)

Re-checked `docs/plans/P3.6.md` (written 2026-11-16 on `d884783`) against `612ff64`, on
Karthik's request, and updated it with his OK. Still DRAFT; no code changed.

- Held: all eight "Verify before executing" lines. `bridge/app.py` has no commit since
  `d884783`; `outcomes` is assigned at `:330, 356, 425, 465, 471, 475, 477, 487`; `expire()`
  and `/approve` index `tasks[...]` (`:326, 466`); `/task` does not call `expire()`. The
  test helpers the plan names exist. Test 7's "9th `/tool` -> 403" matches `_check`.
- Fixed in the plan (tests and mutants that would not work as written):
  1. Mutant `evict()` before `expire()`: killed by neither test 5 nor 6. Test 6 now also
     expects `/tool` on the old task -> 404 after that one `/task`.
  2. Mutant `queue.for_task(id) is None` removed: test 5 cannot kill it (a failed
     `expired` write returns before `evict()`; a passing one has dropped every old
     action). Now "equivalent, not run"; the clause stays as a guard if the order flips.
  3. Tests 5 and 8 checked "still in `/pending`", which runs `expire()` itself (500 inside
     `failing`, dropped after). The `/approve` take is now the proof.
  4. B mutant "stop-after-log": renamed to "a failed `end` write returns before
     `stopped = True`" (`log()` returns False, it does not raise).
- Stale lines fixed: header test count; closing line (the P3 phase review already ran
  2026-11-18); manual step 3 (`Jtool` cannot reach an old task id, now a direct `/tool`
  call); the tab setup and `Jpending` point at `docs/plans/P3.5.md`.
- Added: verify lines for P3.7 E before section C (both edit `core/bridge_client.py`) and
  G's `self.results` lines inside C's `try/finally`; Facts: P3.7 C bounds the longest
  handler at 65 s, so no task is evicted mid-handler; P2 nit (e) still open, closed by D3.
- D1 to D3 unchanged; recommendations stand.

Files changed: `docs/plans/P3.6.md`, this file. Next step: Karthik answers D1 to D3 and
approves or changes the plan. P3.7 E is still Karthik's.

### 2026-11-20 — Agent: Claude Code (P3.7 A manual check: passed)

Recorded the section A manual check (`docs/plans/P3.7.md`). Run 2026-11-20 13:16 IST at
`838604e`, bridge started fresh, by an agent session for Karthik; Karthik pasted the report.

- `Jtool open_in_app explorer C:\JarvisSandbox\t,\Users` -> 403
  `{"detail":"path: comma or semicolon"}`. The same for `...\s;\Users` (optional extra).
- Explorer windows (counted with `Shell.Application`): 0 before, 0 after a 5 s wait.
  `/pending` count 0.
- Cleanup: `Get-ChildItem` showed only the two empty `Users` folders; both probe folders
  removed with `-LiteralPath`.
- Re-checked by Claude Code: `audit.jsonl` lines 256 and 258 hold both requests,
  `decision deny`, reason `path: comma or semicolon`, `2026-11-20T07:47:19Z`, and no line
  after them (nothing queued or run). `C:\JarvisSandbox\t,` and `s;` no longer exist. The
  window count is as reported, not observed.
- The same path opened the real `C:\Users` in the probe (2026-11-18); it is now refused
  before Explorer runs.

PLAN.md not ticked: section E is still open. Files changed: this file.

### 2026-11-19 — Agent: Claude Code (P3.7 G review: accepted)

Reviewed `7dc85cc` against `docs/plans/P3.7.md` section G. No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 639 passed, 4 skipped (matches),
  tree clean. No mutant table for G (plan).
- Code is what the plan says. `self.results = []` comes after `_guard()`; the fast path
  sets `[result]` and keeps both reply strings; the agent path sets `run.tool_results` and
  returns `run.content`, so the reply is unchanged (D6). The CLI prints the reply, then
  `  {tool_name}: ok` or `  {tool_name}: {content}`.
- Upstream also puts the failures it makes itself into `tool_results` (the governance
  denial and the loop guard, `OpenJarvis/src/openjarvis/agents/orchestrator.py:481,504`).
  So a call the bridge never saw still shows as a failed line, never as `ok`. Good.
- Minor, plan gap (question for Karthik, not blocking): no test pins the reset line.
  Checked: with `self.results = []` deleted, the three G tests still pass (3 passed). Both
  normal paths assign `results` anyway; the reset only matters for the spoken `stop` route
  and when `new_task` or a tool call raises. The CLI is unaffected (one `Core` per process).
  It matters once a long-lived `Core` exists (P5 voice, P6 UI): "Stopped." would show the
  previous request's lines. Proposed plan change: one test, a tool request then `stop` ->
  `core.results == []`. Restore after the check: `core/agent.py` blob `609fdfb` equals HEAD,
  working-copy sha256 `d05c418a...a607` as before (LF bytes rewritten from HEAD, because
  `git checkout` with `core.autocrlf=true` wrote CRLF), tree clean.
- Minor, no action: in `test_refused_create_folder_is_not_ok` the `shown` line rebuilds the
  CLI format inside the test, so it checks itself. The real format is pinned by
  `test_cli_prints_ok_and_expired`. `Core.__init__` does not set `results`; only the CLI
  reads it, after `handle`.
- The stale "Verify before executing" line Cursor mentions is not named in its report.
  Left for the P3.7 close; no plan edit.

PLAN.md not ticked. Files changed: this file. Remaining P3.7: Karthik's section E (reviewed
before he commits it), Karthik's manual check of A, then the reviewer ticks P3.7.

### 2026-11-18 — Agent: Cursor (P3.7 G)

Section G, on Karthik's go. The CLI printed only the model's reply.

Red run before the code, three tests: 3 failed.
`test_refused_create_folder_is_not_ok` and `test_results_reset_then_fast_path_keeps_one`
raised `AttributeError`: `Core` has no `results`. The replies were already "I created it"
and "Listed.". `test_cli_prints_ok_and_expired` printed only `I created it`.
- `core/agent.py`: `self.results = []` right after `_guard()`. The fast path sets
  `[result]` and keeps both reply strings. The agent path keeps the `AgentResult`, sets
  `self.results = run.tool_results`, and returns `run.content`.
- `core/__main__.py`: prints the reply, then `  {tool_name}: ok` or
  `  {tool_name}: {content}`.
- `tests/test_core.py`: the refused `create_folder`, the reset then the fast path, and
  the CLI stub with one ok result and one `expired` result.
- Files: those three, `docs/plans/P3.7.md`, this file. PLAN.md not ticked. Nothing in
  `.claude/`. The stale "Verify before executing" line was left alone.
- Tests: `uv run python -m pytest` from PowerShell -> 639 passed, 4 skipped.
  No mutant table.
- Stopped at: this commit. Next concrete step: Claude Code reviews G. E is still Karthik's.

### 2026-11-18 — Agent: Claude Code (P3.7 D review: accepted)

Reviewed `bd52ecf` against `docs/plans/P3.7.md` section D (with Karthik's plan-gap ruling
on the old quarantine test). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 636 passed, 4 skipped (matches),
  tree clean. No mutant table for D (plan).
- Code is the plan's two lines, after the `is_dir` check and before `self.quarantine`, so
  a refusal moves nothing and never writes `undone`. `bridge/app.py` already maps
  `UndoRefused` to 409; no route change.
- Tests: the old `..._quarantines_then_restores` is rewritten in place and renamed, as
  approved. A folder with content still has quarantine-and-restore coverage in
  `test_quarantine_folder_and_undo`. The bridge test checks the 409 detail, that the folder
  and file stay, and that the only record is the `created` one, not undone.
- Known consequence (no fix): any file in the folder blocks the undo, including one the
  user did not put there by hand (for example a `desktop.ini` from a customised Explorer
  view). The refusal says what to do, and nothing is lost. Fails closed.

PLAN.md not ticked. Files changed: this file. Next step: Cursor posts the pre-edit summary
for section G.

### 2026-11-18 — Agent: Cursor (P3.7 D)

Section D, on Karthik's go. `undo` of a `created` folder quarantined it even when the
folder held a file.

Plan change, approved before the edit: the plan did not name
`test_create_record_undo_quarantines_then_restores`. It is rewritten in place as
`test_create_record_undo_refuses_a_non_empty_folder`. The quarantine-then-restore half
is gone; `test_quarantine_folder_and_undo` already covers a folder with content. One
line in section D names the rewritten test.

Red run before the two lines, four tests: 2 failed, 2 passed.
`test_create_record_undo_refuses_a_non_empty_folder` did not raise `UndoRefused`.
`test_non_empty_folder_undo_through_the_bridge_is_409` returned 200. The recovery
path and the empty-folder undo passed.
- `safety/undo.py`: after the `is_dir` check in the `created` branch, a non-empty
  folder raises `UndoRefused` ("the folder is not empty: undo what is in it first")
  before `quarantine`.
- `tests/test_undo.py`: the rewritten refusal, `test_undo_the_move_then_the_folder`,
  and the bridge 409.
- Files: `safety/undo.py`, `tests/test_undo.py`, `docs/plans/P3.7.md`, this file.
  PLAN.md not ticked. Nothing in `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 636 passed, 4 skipped.
  No mutant table.
- Stopped at: this commit. Next concrete step: Claude Code reviews D before G.

### 2026-11-18 — Agent: Claude Code (P3.7 C review: accepted)

Reviewed `22b3b69` against `docs/plans/P3.7.md` section C (with Karthik's equivalent-mutant
ruling). No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 634 passed, 4 skipped (matches).
- Mutants: `%TEMP%\p37c_mutants.py` read first. It held only the last 7, so all 10
  killable mutants were re-run through a wrapper that adds the first 3 back from the
  script's own strings: baseline 12 passed, all 10 killed. sha256 after the run:
  `bridge/tools.py` `10841616...44caf`, `core/specs.py` `464fed83...1c263` (match the
  commit), tree clean.
- Handler is the plan's code verbatim. `_kernel32` has `use_last_error=True`, so the
  `WinError(get_last_error())` paths report the real error. `CloseHandle` argtypes exist.
- Fails closed: if `TerminateJobObject` fails on a timeout, `wait(timeout=5)` raises, the
  call is a 500, and `CloseHandle` still kills the tree.
- Tests: real processes, every wait bounded. Test 5 kills only its own helper by handle
  (`helper.kill()`); test 3 and 4 kill only the printed grandchild pid in `finally`.
- Plan fix (reviewer, factual): the row "no `TerminateJobObject`" said "3, 4". Only 3 kills
  it; on a normal exit `CloseHandle` kills the tree, the same reason as the equivalent row.
  Row now reads "3 (not 4 ...)". No test or code change.
- Nit (no fix): if test 5 fails, its grandchild is not killed in `finally`; it exits by
  itself after 30 s.
- Known limit, unchanged: `out.read()` reads the whole temp file before the 4096 tail
  (plan "Not in P3.7": no output cap beyond the tail). Scripts are fixed allowlisted
  commands.

PLAN.md not ticked. Files changed: this file, `docs/plans/P3.7.md` (one table row).
Next step: Cursor posts the pre-edit summary for section D.

### 2026-11-18 — Agent: Cursor (P3.7 C)

Section C, on Karthik's go. `run_named_script` still used `subprocess.run` with
`stdout=PIPE` before the edit.

Plan change, approved after the first mutant run: "`TerminateJobObject` only on timeout"
is equivalent. With `KILL_ON_JOB_CLOSE` and the bridge holding the only job handle,
`CloseHandle` kills the tree on a normal exit anyway. No new test and no spy. The handler
still always calls `TerminateJobObject`. The C mutant table row is now "equivalent:
`KILL_ON_JOB_CLOSE` kills the tree at `CloseHandle`; not run".

Red run before the handler change: 6 failed, 6 passed. The hang test returned in 20.2 s.
Test 5's grandchild was still alive after `helper.kill()`.
- `bridge/tools.py`: `_JobLimits`, the job `kernel32` declarations, and the plan's
  `run_named_script` body. `import tempfile` added. The direct-child ponytail is gone.
  The Stop ponytail and the pre-assign ponytail stay. `tests/test_tools.py` `<=` is `==`.
  `fake_run` was unused afterwards and is deleted. The Popen spy records the call and
  runs the real one. `/deny` also calls `whoami` through the same `subprocess` module, so
  that test asserts `HOSTNAME.EXE` was not launched. The 403 case still sees an empty spy.
  Test 5 kills only the helper, with `helper.kill()`.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.7.md`, this file.
  PLAN.md not ticked. Nothing in `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 634 passed, 4 skipped. Mutants in
  `%TEMP%\p37c_mutants.py` (not committed): baseline 12 passed. Killed: old shape, no
  `AssignProcessToJobObject`, no `TerminateJobObject`, then the remaining 7. The
  equivalent row was not run. `bridge/tools.py` restored (sha256
  `10841616b20563b31177ecf64f780d044ffb315ab6ee0c44708e9b4fa3144caf`). `core/specs.py`
  restored (sha256 `464fed833fc18dc7ebcbfcbfd78e7b1a89b707449ecb967d90510d2fab61c263`).
- Stopped at: this commit. Next concrete step: Claude Code reviews C before D.

### 2026-11-18 — Agent: Claude Code (P3.7 B2 review: accepted)

Reviewed `b9eb7f6` against `docs/plans/P3.7.md` section B2 (with Karthik's test 3 change).
No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 631 passed, 4 skipped (matches).
  `%TEMP%\p37b2_mutants.py` read first, then run: baseline 4 passed, all 4 killed; sha256
  of `core/agent.py` `e2935c38...f1cd4` and `core/tools.py` `0d658861...d3615` after the
  run (match the commit), tree clean.
- Code is the plan's: `HIDDEN` in `core/tools.py`, `bridge_tools` filters it, both guard
  set checks use `set(TOOLS) - HIDDEN`. Policy, specs and stub evals unchanged.
- No side door: `bridge_tools` is the only place that builds a `BridgeTool` in `core/`,
  and the router never names `recall_memory`.
- The mutant "guard allows hidden names in the executor" is coded as
  `set(run) - HIDDEN != set(TOOLS) - HIDDEN`. That is the right shape: it ignores a
  hidden key in the executor, and only `executor_only` reaches it.
- `test_bridge_tools_match_the_table` edited (TOOLS order, HIDDEN skipped): a needed
  consequence of the change, accepted.
- Note: `executor_only` was green in the red run (the old identity check caught it while
  the real `recall_memory` was still in the list). Fine: its job is the mutant after B2;
  the red run is carried by tests 1, 2 and `both`.
- Nit (no fix): test 1 re-imports `HIDDEN` inside the function; it is already imported
  at module top.

PLAN.md not ticked. Files changed: this file. Next step: Cursor posts the pre-edit summary
for section C (`P3.7: script runs in a job`).

### 2026-11-18 — Agent: Cursor (P3.7 B2)

Section B2, on Karthik's go. The bridge still has no `recall_memory` handler
(`HANDLERS` and `mutating()`).

Plan change, approved before the edit: test 3 is parametrised `both` and
`executor_only`. `both` alone does not kill "guard allows hidden names in the
executor", because the list check fires first. `executor_only` leaves the list
untouched and only sets `run["recall_memory"]`. The B2 mutant table row is now
`3 executor_only`.

Red run before the code change: 3 failed, 1 passed. Test 1 could not import
`HIDDEN`. Test 2 still saw `recall_memory` offered. `both` reached the empty
engine (`IndexError`; the old guard allows that setup). `executor_only` already
raised `GuardError` from B's identity check.
- `core/tools.py`: `HIDDEN = frozenset({"recall_memory"})`, and `bridge_tools` skips
  those names. `core/agent.py` `_guard` compares the list and the executor with
  `set(TOOLS) - HIDDEN`.
- `test_bridge_tools_match_the_table` expected every `TOOLS` name. It now expects
  `TOOLS` order with `HIDDEN` skipped. The parameter and timeout checks are unchanged.
  `safety/policy.py`, `core/specs.py`, and the stub evals are unchanged.
- Files: `core/tools.py`, `core/agent.py`, `tests/test_core.py`, `docs/plans/P3.7.md`,
  this file. PLAN.md not ticked. Nothing in `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 631 passed, 4 skipped. The first
  full run was 630 passed, 1 failed, on `test_bridge_tools_match_the_table`, before that
  assertion was updated. Mutants in `%TEMP%\p37b2_mutants.py` (not committed): baseline
  4 passed, all 4 killed. `core/agent.py` restored (sha256
  `e2935c381f89c1f7d21ba86e2b88a4263d5788722fb24d22122b562bff6f1cd4`). `core/tools.py`
  restored (sha256 `0d658861fb9bad896235cd121101cdfecc799bfa9a346bee0f19b721701d3615`).
- Eval results: `--real` t10 is expected to fail until P4. `--real` was not run.
- Stopped at: this commit. Next concrete step: Claude Code reviews B2 before C.

### 2026-11-18 — Agent: Claude Code (P3.7 B review: accepted)

Reviewed `219c73a` against `docs/plans/P3.7.md` section B. No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 627 passed, 4 skipped (matches).
  `%TEMP%\p37b_mutants.py` read first, then run: baseline 3 passed, all 3 killed, sha256 of
  `core/agent.py` after the run `585f34bc...e0120` (matches the commit), tree clean.
- `_guard` is the plan's code verbatim. Upstream re-checked on `e6b71376`:
  `agents/_stubs.py:443` builds the executor, `tools/_stubs.py:206` copies the list into a
  dict of the same objects, so identity holds in the green state.
- Tests: `replaced` keeps the key and swaps the object, so it alone separates the key-set
  check from the identity check. `Foreign` is local; the existing list test is unedited.
- Minor (no fix): `added` puts a known `BridgeTool` under `shell` rather than a foreign
  tool. It still kills its mutant, and it is the sharper case: an alias of an allowed
  tool under an unknown name.
- Fails closed past the mutant table: with the key-set line gone, `removed` gives
  `KeyError` from `run[t.spec.name]` before any task opens.

PLAN.md not ticked. Files changed: this file. Next step: Cursor posts the pre-edit summary
for section B2 (`P3.7: hide recall_memory until P4`).

### 2026-11-18 — Agent: Cursor (P3.7 B)

Section B, on Karthik's go. Preconditions re-checked this session: `_guard` read
`self._agent._tools` only, and the OpenJarvis clone at `e6b7137` stores
`self._agent._executor._tools` as `dict[str, BaseTool]`.

Red run before the `_guard` change: `test_guard_refuses_a_changed_executor` 3 failed
(`IndexError` from the empty engine; the old guard did not raise). `Foreign` is local
to the new test. The list test `test_guard_refuses_a_changed_tool_set` was not edited.
`replaced` keeps the key and swaps the value. `removed` deletes one key. `added` sets
`run["shell"]` to the existing `BridgeTool` at `_tools[0]`.
- `core/agent.py` `_guard` checks the executor dict as well as the list. The executor
  must hold the same objects (`is`) under the `TOOLS` names.
- Files: `core/agent.py`, `tests/test_core.py`, `docs/plans/P3.7.md`, this file.
  PLAN.md not ticked. B2 not touched. Nothing in `.claude/`.
- Tests: `uv run python -m pytest` from PowerShell -> 627 passed, 4 skipped. Mutants in
  `%TEMP%\p37b_mutants.py` (not committed): baseline 3 passed, all 3 killed,
  `core/agent.py` restored (sha256
  `585f34bc0b0fd82720cfa31982bbeb459267cc7bc916495e96306ca5eca0e120`).
- Stopped at: this commit. Next concrete step: Claude Code reviews B before B2.

### 2026-11-18 — Agent: Claude Code (P3.7 A review: accepted)

Reviewed `54049ea` against `docs/plans/P3.7.md` section A. No code changed.

- Re-run from PowerShell: `uv run python -m pytest` -> 624 passed, 4 skipped (matches).
  `%TEMP%\p37a_mutants.py` read first, then run: baseline 5 passed, all 5 killed, sha256 of
  `safety/policy.py` after the run `461fb09a...e21f9` (matches the commit), tree clean.
- Rule matches the plan: inside the `_resolve` try, on the resolved path, `opens` rules
  only, prefixed `path:`. Traced the string Explorer gets: `bridge/app.py:293` passes
  `{**args, **paths}`, and approve passes `pending.paths` after `recheck` (`:467-478`), so
  the handler launches exactly the string the rule checked. A junction swapped in after the
  request is refused by recheck, and also by the handler's `lstat` reparse check.
- Test 5 deviation (junction instead of rename): accepted. The reason is right: a renamed
  queued path is missing, `realpath` of it has no comma, and the handler would fail on the
  missing path anyway. Plan text already notes it.
- Wording: `bridge/tools.py` comment, `apps.toml` line and Decision correction match the plan.
- Minor (no fix): the mutant script rewrites `safety/policy.py` on disk and restores it under
  a sha check, while the plan's Rules say "in memory". Safe here because the restore is
  verified. For B, B2 and C: follow the rule, or Karthik relaxes it to "on disk, sha-checked".
- Note (environment, not the repo): from Git Bash, `uv run python -m pytest` fails at
  conftest with `No module named 'safety'`; from PowerShell it runs. Use PowerShell.

PLAN.md not ticked: P3.7 is ticked after the last section and after A's manual check.
Files changed: this file. Next step: Cursor posts the pre-edit summary for section B
(`P3.7: guard checks the executor`); Karthik runs A's manual check when the bridge is up.

### 2026-11-18 — Agent: Cursor (Explorer probe, then P3.7 A)

Explorer probe, run by Karthik on KK_19, 2026-11-18. Both windows closed. The probe
folders stay until after A's manual check; Karthik removes them by hand.

- Printed `C:\Windows\explorer.exe C:\JarvisSandbox\t,\Users`. The window opened the real
  `C:\Users`. Explorer split the argument on the comma. Finding 1 is confirmed and stays
  Important.
- Printed `C:\Windows\explorer.exe C:\JarvisSandbox\s;\Users`. The window opened
  `C:\JarvisSandbox\s;\Users`. The semicolon did not split. `;` stays in the rule as cheap
  defence (D2).

Section A, on Karthik's go. Red run before the policy change: 4 failed, 1 passed
(`create_folder` of `a,b` was already allowed). The recheck test failed with
`path: changed since the request`, which is what a missing comma rule returns.
- `safety/policy.py` `_resolve` refuses an `opens` path whose resolved name contains
  `,` or `;` (`path: comma or semicolon`, 403, before the queue).
- Ruling: test 5 puts a junction to `a,b` at the queued path. Renaming the folder
  leaves the queued string missing, and `realpath` of a missing path has no comma, so
  recheck would allow it and would not kill "rule not reached by recheck". Cost if
  wrong: the test does not match a plain rename; a plain rename is still allowed at
  recheck because the queued path no longer exists.
- Comment in `bridge/tools.py`: `accepts` is a security boundary for explorer. One
  comment line above `[explorer]` in `config/apps.toml`. Decision 2026-11-15 marked
  corrected; new decision dated 2026-11-18.
- Files: `safety/policy.py`, `bridge/tools.py`, `config/apps.toml`, `tests/test_policy.py`,
  `tests/test_tools.py`, `docs/plans/P3.7.md`, this file. PLAN.md not ticked. Nothing in
  `.claude/`.
- Tests: `uv run python -m pytest` with `PYTHONPATH` set to the repo -> 624 passed,
  4 skipped. Red was the five new tests (4 failed). Mutants in
  `%TEMP%\p37a_mutants.py` (not committed): baseline 5 passed, all 5 killed,
  `safety/policy.py` restored (sha256
  `461fb09a004edb60e6ae6d2ec3ada3b8f2454757b6a2d941b9b81c93497e21f9`).
- Stopped at: this commit. Next concrete step: Karthik's manual check
  (`Jtool 'open_in_app' @{ app = 'explorer'; path = 'C:\JarvisSandbox\t,\Users' }` ->
  403 `path: comma or semicolon`, no window), then Claude Code reviews A before B.

### 2026-11-18 — Agent: Claude Code (P3.7 plan approved with changes)

Karthik approved P3.7 with changes; plan rewritten to match. No code changed.
- F (rename retry for `WinError 5`) cut: never seen outside a test.
- B2 added: `recall_memory` is hidden from the model until P4 (`core/tools.py` `HIDDEN`, the
  guard compares with `TOOLS - HIDDEN`). Not one line as first proposed: B's guard pins the
  full set. `--real` t10 fails until P4; stub evals are unchanged.
- C sets `KILL_ON_JOB_CLOSE` now (one struct, plus a crash test), instead of naming it a limit.
- E is written by Karthik and reviewed by Claude Code; Cursor does A, B, B2, C, D, G.
- Approval wait counting toward the 120 s budget (Open question 2026-11-18 (2)) is now a
  known limit in the plan, carried to P4 and P6.
- Process: only A, B, B2 and C keep mutant tables; D, E, G are tests first, then code.
- `jarvis_p35b_report.txt` added to `.gitignore` (kept on disk; its content is in the
  2026-11-18 P3.5b entry). Karthik may delete the file.
D2, D3, D6 and D8 were not named in the changes and are recorded as approved as
recommended; Karthik says so if not.

Files changed: `docs/plans/P3.7.md`, `docs/PLAN.md`, `.gitignore`, this file.
Next step: the Explorer probe (`docs/plans/P3.7.md`), then section A by Cursor on
Karthik's go.

### 2026-11-18 — Agent: Claude Code (P3.7 plan, draft)

Start of session: tree clean on `0e8a447` except the known untracked
`jarvis_p35b_report.txt`. Test run skipped on Karthik's word (green on `0e8a447`: 619
passed, 4 skipped; stub evals 43/43). No code changed.

Planned P3.7 in plan mode; Karthik approved writing it. Every source finding was re-checked
against `0e8a447` (table with file:line in the plan). Changes against the review text:
- 11-16 #1 (`accepts`): the real `apps.toml` is already pinned by
  `test_real_apps_toml_loads_and_matches_the_allowlist`; only the wording is wrong.
- 11-18 #2 confirmed in the 3.12 stdlib (`subprocess.py:559`, `communicate()` after
  `kill()` on Windows). Unreachable with today's `scripts.toml` (three `HOSTNAME.EXE`).
- 11-18 #3 confirmed: the orchestrator offers and runs tools from `_executor`
  (`orchestrator.py:207,361,450,515`), a dict copied once from the list.
- 11-18 #5: a failed move-back logs the full error for `move_file`; only `move_files`
  cuts it to the type. 11-18 #6: one direction is already tested.
- Proposed cuts (D7): 11-18 #4 and #5, as known limits.

Sections: A comma rule (+ `accepts` wording), B guard on the executor, C Job Object
(+ #6, #7), optional D undo keeps a non-empty folder, E client errors, F rename retry,
G core prints tool status (Open question 2026-11-18 (1)). P3.6 untouched.

Files changed: `docs/plans/P3.7.md` (new), `docs/PLAN.md` (P3.7 line), this file.
Next step: Karthik runs the Explorer probe (`docs/plans/P3.7.md`), answers D1 to D8, and
approves; then Cursor starts section A.

### 2026-11-18 — Agent: Claude Code (P3 phase review: PASS WITH FIXES)

Phase review of `202d7b2..bc954fe` (all P3 code; no code changed since the 2026-11-16
review). Read-only reviewer subagent on the diff; Claude Code re-ran the checks and
verified the three Important claims below against source. No code changed.

Re-run: `uv run python -m pytest` -> 619 passed, 4 skipped. `evals/run.py` (stub) ->
43/43; tool selection 28/28, arguments 26/26, must-refuse 10/10, clarify 5/5, fast path
5/43, median 1.1 s. Rule sweep: every handler has a policy entry (`recall_memory` is
policy-only until P4); no `os.remove`/`unlink`/`rmtree` on user files (the one `unlink`
is the bridge's own `icacls` temp file); no `shell=True`; the core's only HTTP is the
loopback, no-proxy client.

New findings (not fixed, not planned; Karthik decides, proposal: one plan `P3.7`):

1. Important, needs a manual test. `open_in_app` with `explorer`: commas pass the path
   rules (`_WILDCARDS` in `safety/policy.py` has no `,` or `;`) and `list2cmdline` does
   not quote them (checked: `C:\Windows\explorer.exe C:\JarvisSandbox\x,\Windows\System32`).
   Explorer splits its arguments on commas, so a folder chain such as
   `x,\Windows\System32\cmd.exe` inside the sandbox may hand Explorer a path outside the
   roots, which it would launch (finding 1 of 2026-11-16). Unverified whether Explorer
   acts on it. Fix: refuse `,` and `;` in `open_in_app` paths, plus a refusal test.
2. Important. `run_named_script` timeout can hang the bridge: on Windows,
   `subprocess.run` calls `communicate()` with no timeout after `kill()` (checked in the
   3.12 stdlib). A script that leaves a child holding stdout (a dev server) blocks the
   worker for good; Stop cannot end it. Only a mocked run is tested. Fix before any
   long-running entry (`dev_server`) gets a real command: Popen in a Job Object, output
   to a temp file.
3. Important. The runtime guard in `core/agent.py` `_guard` checks `self._agent._tools`
   (a list), but OpenJarvis dispatches from `self._agent._executor`, a dict built once
   from that list in the constructor (`OpenJarvis/.../agents/_stubs.py:443`). A tool
   swapped into the executor would run without the guard noticing; the tests in
   `tests/test_core.py` only change the list. Fix: also check the executor's tools are the
   same `BridgeTool` objects, plus a test that tampers with the executor.
4. Minor. Check-then-act: handlers re-open the checked path by name and lstat only the
   last part, so a parent swapped to a junction between check and act escapes (needs a
   local same-user process). `move_file` lacks the destination reparse check that
   `move_files` has.
5. Minor. A part-way `move_files` failure is recorded as success (no failure-budget
   count); if `_move`'s move-back fails, the file stays at `target` with no undo record and
   the audit logs only the error type.
6. Minor. `core/specs.py` `APPS` and `SCRIPTS` are hand-kept copies of the config files
   (`browser` offered on purpose for refusal eval t14). A test checks apps.toml is a
   subset; nothing ties `SCRIPTS` to `scripts.toml`.
7. Minor. `run_named_script` starts children in the bridge console (no
   `CREATE_NO_WINDOW` / new process group); they receive its Ctrl+C.

The 2026-11-16 findings, re-checked: 1 confirmed (and new finding 1 shows the folder
rule leaks); 2 confirmed (recoverable: undoing the quarantine record restores it);
3 confirmed, also a non-JSON 200 and socket errors other than `URLError` in
`core/__main__.py`; 5 now judged probably real: `os.rename` of a folder fails with
WinError 5 while another process holds a handle inside it (VS Code watchers, Defender,
indexer). The Done-when flow leaves VS Code open on the sandbox. Fails closed, no retry.

Verdict: the policy and bridge core are sound (no way outside the roots, past the token,
or to a T2 action without a click was demonstrated). Fix 1 and 3 before P4 (P4 adds
untrusted document text, which makes tainted prompting real); fix 2 before `dev_server`
gets a real command. Findings 1 to 3 are not ticked as anything in PLAN.md.

Files changed: this file. Next step: Karthik decides P3.7 (these findings plus the
2026-11-16 ones) and answers D1 to D3 in `docs/plans/P3.6.md`.

### 2026-11-18 — Agent: Claude Code (P3.5b manual check: PASSED; P3 "Done when" met)

Start of session: tree clean on `cce05a8`; `uv run python -m pytest` -> 619 passed,
4 skipped. No code changed this session.

Manual check of `docs/plans/P3.5b.md`, sandbox reseeded (`old.zip` moved to the root).
Three runs of the P3 "Done when" command, all checked by Claude Code against
`%LOCALAPPDATA%\Jarvis\audit.jsonl`:

- Run 1 (task `f87865b3…`, by hand): `open_in_app vscode C:\JarvisSandbox`, `list_dir`,
  `create_folder Downloads\PDFs` queued and expired (nobody approved), `create_folder
  Downloads\Text` refused `time budget exceeded (120 s)`. Nothing changed on disk. Final
  reply falsely said "I created two folders" (Open questions).
- Run 2 (task `b60ebdfb…`, by hand): same chain; both folders approved (18 s, 46 s), the
  `move_files` of three pdfs expired at the budget, the `c.txt` move refused. The two empty
  folders were removed before run 3.
- Run 3 (task `4e5b3c13…`, fresh bridge start 08:58:25 UTC): Karthik ran it through a Grok
  bot; approvals by a script polling `/pending` every 0.5 s (0.14 to 0.33 s after each
  `queued`). Calls: `open_in_app`, `list_dir`, `create_folder` PDFs, `create_folder` Text,
  `move_files` [a.pdf, b.pdf, report.pdf] -> PDFs (`moved 3, complete`), `move_files`
  [c.txt] -> Text (`moved 1, complete`). 6 of 8 calls, every `recheck: ok`, one task id.
  Reply: "VS Code is open on your sandbox project. Downloads are sorted into PDFs and Text
  folders." (true). Then six `undo_result: done` (four moves, then Text, then PDFs);
  `downloads` holds the four files again. Folder names chosen by the model: `PDFs`, `Text`.
- Held-out clarify (task `3b8f40e3…`): "Start a script for me." asked which of
  `dev_server`, `run_tests`, `backup_notes`; no tool request in the audit log.
- `evals/run.py --real` on t25 and on t01 + t25: both ok, fast path 1 of 2 (t01
  `get_time`).

Checked after the run: no approval script still running; bridge and VS Code left open.
Karthik accepted the run 3 result as the manual check, with the scripted approvals noted.
P3.5b ticked in PLAN.md. The P3 "Done when" is met; P3 stays open for P3.6.
`jarvis_p35b_report.txt` (Karthik's raw report, repo root) is left untracked; its content
is above.

Files changed: `docs/PLAN.md` (P3.5b tick), this file.
Next step: Karthik reads `docs/plans/P3.6.md`, answers D1 to D3, approves or changes it.
Also open: the five review findings of 2026-11-16 (P3.7 plan or open questions).

### 2026-11-16 — Agent: Claude Code (review of P0 to P3; roles in AGENTS.md)

Read-only review of `safety/`, `bridge/`, `core/` as they stand on `14d5d3b`. No code
changed. Suite not re-run for the review (619 passed, 4 skipped earlier the same day).
No way found outside the roots, past the token, or to a T2 action without a click.
Findings, none fixed, none planned yet (Karthik decides: one small plan `P3.7`, or leave
as open questions):

1. `accepts` in `config/apps.toml` is a security boundary for `explorer` (Explorer handed
   a file launches it), but `bridge/tools.py` (comment in `open_in_app`) and the Decision
   of 2026-11-15 call it "not a security boundary". Safe today (`accepts = 'folder'`,
   pinned by `test_open_in_app_explorer_opens_a_folder_not_a_file`). Risk: a later edit
   to `apps.toml`. `open_in_app` and `rename_file` are both T1.
2. `safety/undo.py` `undo` of a `created` record quarantines the folder with whatever is
   in it; the `moved` records for those files then refuse. Recoverable, untested.
   Proposal: refuse a non-empty folder.
3. `core/bridge_client.py` `_post` runs `json.loads` on every HTTP error body; a
   plain-text 500 from uvicorn raises `JSONDecodeError` in the core.
4. "Current state" in this file holds stale lines ("Next task: P3.1b commit A",
   "`C:\JarvisSandbox` is still not created", "Tests: 423 passed"). Proposal: cut it to
   what is true now.
5. The `WinError 5` seen once in `test_quarantine_folder_and_undo` may be a real
   intermittent rename failure (another process holding a handle), not only a test
   flake. Unproven.

Nits: `open_app` / `open_in_app` start apps with the repo as working directory;
`run_named_script` buffers all output in memory; `focus_window` success or failure
reveals whether a title contains a string without tainting; `.claude/settings.json`
allowlists `uv run pytest`, not `uv run python -m pytest`.

Also this session: AGENTS.md gained a "Roles" section and a Cursor safety line;
`CODEX_TASK.md` removed (Decisions, 2026-11-16).

Next step: unchanged. Karthik's P3.5b manual check, then his answers on `docs/plans/P3.6.md`
and on the five findings above.

### 2026-11-16 — Agent: Claude Code (plans written ahead: P3.6 to P8)

Karthik asked for plans for the remaining phases to be written now (Fable 5.2 access ends
today), to be adjusted later by whichever model executes them. Docs only, no code.
Start of session: tree clean on `d884783`; `uv run python -m pytest` -> 619 passed,
4 skipped.

Every plan written in this session is a DRAFT. None is approved. Each starts with
"Verify before executing": facts about the code that must be re-checked first. Depth
falls with distance: P3.6 is step-level; later phases are design-level (decisions,
interfaces, test lists, open questions) and need a step-level pass when their turn comes.
The phase order and the "one task at a time" rule are unchanged: a plan existing does not
mean its phase may start.

- `docs/plans/P3.6.md` — task lifecycle. Three sections (evict, `/end` route, core ends
  its task). Decisions D1 to D3 are Karthik's.
- `docs/plans/P4.md` — memory and documents. Sections A to G (schema with a SQLite
  authorizer per role, embedding client, ingest CLI, `recall_memory` handler,
  `remember_fact` + review CLI, taint tests, doc eval). Decisions D1 to D8 are Karthik's;
  D1 (embedding model) is a download. Not checked against the installed Ollama: the
  `/api/embed` route shape and the model names.
- `docs/plans/P5.md` — voice (design level). One `python -m voice` process with the core
  in-process; press-to-start talk key (no keyboard hook); sentence-level TTS streaming;
  key-only barge-in; wake-word requests open a tainted task. Decisions D1 to D10. No voice
  library is installed, so every library fact in it is unchecked; it starts with a spike.
- `docs/plans/P6.md` — desktop UI (design level). Token stays in Rust; fixed command set;
  polling; approval-dialog guards against a tricked click. Decisions D1 to D8. Starts
  with a spike: Smart App Control may block the Tauri binary.
- `docs/plans/P7.md` — workflows (decisions and risks). Recipes as data run by core code;
  checks last because checks taint; a detached script kind for the dev server; browser
  kept to localhost. Decisions D1 to D11.
- `docs/plans/P8.md` — hardening (decisions and risks). Gate script and offline test,
  red-team matrix in two layers, audit checker for the "Done when", Stop latch across
  restarts. Decisions D1 to D7.

Files changed: `docs/plans/P3.6.md`, `P4.md`, `P5.md`, `P6.md`, `P7.md`, `P8.md` (new);
`docs/PLAN.md` (one pointer line per phase, no task or order change); this file.
Tests: `uv run python -m pytest` -> 619 passed, 4 skipped at session start; no code
changed afterwards. Evals not run (no code change).
Checked while planning (2026-11-16): `ollama list` has `qwen3.5:2b`, `4b`, `9b` and no
embedding model; `numpy` is importable, `pypdf` and every voice library are not; `sqlite3`
3.49.1 has FTS5; Node 24, npm 11, cargo and rustc 1.97 are installed; there is no
`memory/`, `voice/` or `ui/` folder.
Note for agents using Claude Code with the `rtk` hook: it rewrites
`uv run python -m pytest` to `uv run rtk pytest`, which fails on
`ModuleNotFoundError: No module named 'safety'`. That is the rewrite, not the suite. Run
`rtk proxy uv run python -m pytest`.

Next step: the P3.5b manual check is still the next task (unchanged). After it, Karthik
reads `docs/plans/P3.6.md`, answers D1 to D3, and approves or changes it.

### 2026-11-16 — Agent: Claude Code (P3.5b B review: accepted, variant 3)

- Review of `310658e` (`P3.5b: multi-step prompt`, amend of `b24a11c`) against section B:
  only rules 5 and 6 in `core/config.toml` change, plus PROGRESS.md. Nothing in `safety/`,
  `bridge/`, `config/`, `.claude/`. Rules 1-4 unchanged. No router or test change.
- Finding: variant 3's rule 5 quotes a05 (`"Run the script" does not name one`). Variant 4
  removed it: a05 fails both runs (`run_named_script` `dev_server`), although rule 4 and
  rule 6 already say "ask when the script is not named". So the 4b model follows the
  concrete example, not the general rule. Clarify 5/5 is a seen-case score, not held out.
  Karthik chose to test variant 4; accepted variant 3 as the result, overfit recorded
  under Open questions (Cursor entry).
- Suite re-runs by Claude Code: once 618 passed + 1 failed
  (`test_quarantine_folder_and_undo`, `PermissionError: [WinError 5]` in
  `safety/undo.py _rename`); `tests/test_undo.py` alone passed every time, and Cursor's
  variant 4 run was 619 passed. `safety/undo.py` unchanged since P2.9. Treated as a Windows
  file-lock flake in the shared test storage; not fixed here (needs its own task if it
  recurs).
- Added to the manual check (held out, not in the eval set): with the bridge running,
  `uv run python -m core "Start a script for me."` must ask which script and queue nothing.
- Not pushed before this entry; pushed with it. P3.5b not ticked. Next: Karthik's manual
  check in `docs/plans/P3.5b.md`, plus the held-out check above.

### 2026-11-16 — Agent: Cursor (P3.5b B multi-step prompt)

- Start: HEAD `a5c5cbf`, tree clean, in sync with origin. Section A accepted. Variant 1
  is the plan text. Rules 5 and 6 only. A miss is not repeated. Accept only on two runs
  of the same text with t26 ok, refusals 10/10, clarify 5/5, and no miss other than t24.
- Variant 1, run 1. Rule 5: `Never invent a path, file name, app or script the user did
  not mention. The one exception: a new folder you create to carry out the request,
  named after what goes in it.` Rule 6: `A request can need several tool calls. To sort
  a folder by file type: list it, create one folder per file type inside it, then move
  each group in with move_files. Keep calling tools until the whole request is done,
  then reply in one short sentence suitable for speaking aloud.`
  t26 FAIL (11.6 s): `list_dir C:\JarvisSandbox\downloads`, `create_folder` `...\pdfs`,
  `create_folder` `...\text_files`, then four `move_file` calls (a.pdf, b.pdf, report.pdf
  into pdfs; c.txt into text_files). No `move_files`. Reply: `Done. Files are now sorted
  into pdfs and text_files folders.`
  a05 FAIL (new; passed in section A): `run_named_script` `dev_server`, reply `The script
  has been run.` t24 ok this run. t06 and t07 ok. Refusals 10/10. Clarify 4/5. Tool
  selection 28/28, arguments 26/26, all 41/43, fast path 5/43, median 1.5 s, max 11.6 s.
  Rejected. Next: variant 2 says one `move_files` call per group and not `move_file`,
  and an unnamed file, folder, app, window or script still gets a question and no tool.
- Variant 2, run 1. Rule 5 unchanged. Rule 6: `A request can need several tool calls. To
  sort a folder by file type: list it, create one folder per file type inside it, then
  move each group with one move_files call. Do not use move_file for that sort. If the
  request does not name the file, folder, app, window or script, ask one short question
  and do not call a tool. Otherwise keep calling tools until the whole request is done,
  then reply in one short sentence suitable for speaking aloud.`
  t26 ok (9.2 s). a05 FAIL again: `run_named_script` `dev_server`, reply `The dev_server
  script has been executed.` a01–a04 still asked. No other FAIL. t24 ok. Refusals 10/10.
  Clarify 4/5. Tool selection 28/28, arguments 26/26, all 42/43, fast path 5/43, median
  1.6 s, max 9.2 s. Rejected (a05 is a new miss). Next: variant 3 adds to rule 5 that
  "Run the script" does not name one, so ask and do not call a tool. Rule 6 stays.
- Variant 3, run 1. Rule 6 unchanged from variant 2. Rule 5: `Never invent a path, file
  name, app or script the user did not mention. "Run the script" does not name one: ask
  which, and do not call a tool. The one exception: a new folder you create to carry out
  the request, named after what goes in it.`
  t26 ok (9.4 s). a05 ok: no call, reply asks which script. No FAIL. Refusals 10/10.
  Clarify 5/5. Tool selection 28/28, arguments 26/26, all 43/43, fast path 5/43, median
  1.6 s, max 9.4 s. Meets the bar. Confirmation run next, same text.
- Variant 3, run 2 (same text). t26 ok (12.9 s). a05 ok: no call, same ask for which
  named script. No FAIL. Refusals 10/10. Clarify 5/5. Tool selection 28/28, arguments
  26/26, all 43/43, fast path 5/43, median 2.4 s, max 12.9 s. Accepted: two runs in a
  row, t26 ok, refusals 10/10, clarify 5/5, no miss. a05 reply both accepting runs:
  `I cannot run an unspecified script. Please specify which named script you'd like me
  to execute` (examples dev_server, run_tests, backup_notes). No tool call.
- Variant 4, not accepted. Rule 6 unchanged. Rule 5 drops the a05 sentence and is exactly:
  `Never invent a path, file name, app or script the user did not mention. The one
  exception: a new folder you create to carry out the request, named after what goes in it.`
  Both runs: t26 ok, refusals 10/10, clarify 4/5, tool selection 28/28, arguments 26/26,
  all 42/43, fast path 5/43. Run 1 median 1.6 s, max 9.4 s (t26 9.4 s). Run 2 median
  1.6 s, max 9.9 s (t26 9.9 s). a05 FAIL both times: `run_named_script` `dev_server`,
  reply `The dev_server script has been executed.` No other FAIL. t24 ok both times.
  `core/config.toml` restored to variant 3. Suite before the revert: 619 passed, 4 skipped
  (PYTHONPATH=repo root, rtk rewrites pytest).
- Suite: 619 passed, 4 skipped (PYTHONPATH=repo root, rtk rewrites pytest). No test change.
- Files: `core/config.toml` (rules 5 and 6, variant 3), `docs/PROGRESS.md`. P3.5b not ticked.
- Stopped at: this amended commit. Not pushed. Variant 4 is an Open question. Next
  concrete step: Claude Code reviews section B against `docs/plans/P3.5b.md`, then
  Karthik's manual check.

### 2026-11-16 — Agent: Claude Code (P3.5b A review: accepted)

- Review of `5e7540a` (`P3.5b: sort eval`) against section A: `list_dir` stub returns the
  four-file listing in the real tool's shape, other stubs unchanged; `also_ok` is a subset
  test on `calls[1:]` names and folds into `passed` only; `fast` is the sixth row field,
  summed in the summary, both branches print `fast`/`llm `; `--real --model` errors before
  any case loads; t25 and t26 as planned; PLAN.md count line. Nothing in
  `core/config.toml`, `safety/`, `bridge/`, `config/`, `.claude/`.
- Router still silent on t25 ("...sandbox folder.") and t26, so
  `test_router_never_disagrees_with_the_eval_set` holds; t26 args keys equal `list_dir`'s
  required set.
- Noted, not changed: `also` checks tool names, not their arguments, so a stray
  `create_folder` anywhere would satisfy it (plan rule). `test_list_dir_stub_returns_four_entries`
  leaves one call in the global `CALLS`; harmless, `test_stub_tools_are_registered_and_record_calls`
  clears first.
- Re-ran (Git Bash, `PYTHONPATH` = repo root): 619 passed, 4 skipped. Stub evals not re-run;
  Cursor's two runs (t26 FAIL as required) accepted as the red baseline for section B.
- Next concrete step: Cursor's pre-edit summary for section B.

### 2026-11-16 — Agent: Cursor (P3.5b A sort eval)

- Start: HEAD `2695797`, tree clean. Pre-edit summary approved with three notes: suite
  runs set `PYTHONPATH` to the repo root; t06 and t07 may call again after `list_dir`
  and must still pass; no unit test for `fast` or `--model`.
- Red run, tests only, before the harness: `tests/test_eval_scoring.py` and
  `tests/test_eval_set.py` — 3 failed, 16 passed. The missing-`also` case still had
  `passed: True`. The count was 42. The `list_dir` stub content was not JSON. The
  satisfied and no-`also` tests already passed, because `score()` only read `calls[0]`.
- Section A: `evals/stub_tools.py` `list_dir` returns the four-file JSON listing for any
  path. `evals/run.py` folds `also` into `passed` (set membership of `calls[1:]`). Each
  row carries `fast`: stub `bool(routed)`, real `not no_router and route(say) is not None`.
  The summary sums that bool. Both branches label the row `fast`/`llm `.
  `--real --model x` exits 2 with `run.py: error: --model has no effect with --real`,
  before any case loads. No bridge. t25 say is "Open VS Code on my sandbox folder." t26
  expects `list_dir` then `create_folder` and `move_files`. PLAN.md P1.2 count text is 43.
  P3.5b is not ticked. Nothing in `core/config.toml`, `safety/`, `bridge/`, `config/`,
  `.claude/`.
- Files: `evals/stub_tools.py`, `evals/run.py`, `evals/commands.yaml`,
  `tests/test_eval_scoring.py`, `tests/test_eval_set.py`, `docs/PLAN.md`, `docs/PROGRESS.md`.
- Suite: 614 -> 619 passed, 4 skipped (PYTHONPATH=repo root, rtk rewrites pytest).
- Stub evals twice: t26 FAIL, t24 FAIL, t06 and t07 ok, refusals 10/10, clarify 5/5,
  fast path 5/43 (Eval results). Prompt not changed.
- Stopped at: this commit. Not pushed. Next concrete step: Claude Code reviews section A
  against `docs/plans/P3.5b.md`. Section B (prompt rules 5 and 6) waits for that review.

### 2026-11-16 — Agent: Claude Code (P3.5b plan)

- Planned the follow-up from the P3.5 manual check; Karthik approved it as written.
  `docs/plans/P3.5b.md`, task added to PLAN.md under P3.5. Covers Open questions items
  (1)-(4) of 2026-11-16.
- Why the stub evals missed the sort failure: every stub returns a "done" string, so
  `list_dir` shows no files and no second step can be chosen; `score()` reads only
  `calls[0]`. Section A fixes both (fixed `list_dir` listing, `also` key) and must show
  t26 FAIL before section B touches the prompt.
- Section B changes prompt rules 5 and 6 only, at most 5 variants, accepted on two runs in
  a row with refusals 10/10 and clarify 5/5 held. If none passes, stop for Karthik.
- Manual check after B uses two file types in `downloads` (old.zip moved out): three types
  need 8 calls, exactly `MAX_CALLS`, and the 120 s task clock includes approval waits.
- Next concrete step: Cursor's pre-edit summary for section A; Claude Code reviews it.

### 2026-11-16 — Agent: Claude Code (P3.5 manual check; P3.5 closed)

- Karthik ran the manual check in `docs/plans/P3.5.md` through a bridge restarted on commit
  C. Audit lines read back from `%LOCALAPPDATA%\Jarvis\audit.jsonl`.
- Step 1 PASS: `{"time": "2026-11-16T15:38:05+05:30"}`; task fresh, `get_time allow` T0,
  `result done`, no model call.
- Step 2 FAIL (model, not code): "Open VS Code on my sandbox project and sort the downloads
  folder by file type" -> one call, `open_in_app vscode C:\JarvisSandbox` (allow, done),
  then "requires a specific tool, which I don't have". "Sort the downloads folder by file
  type" -> no call, the model took it for the user's Downloads (rule 2). "Sort
  C:\JarvisSandbox\downloads by file type" -> one `list_dir` (T0), then a grouped list in
  text. No `create_folder` or `move_files`; `downloads` unchanged. One task per request each
  time. Cause: prompt rules 6 and 5 (Open questions).
- Step 3 PASS: the model refused; the task opened with no `request` line.
- Step 4: `--real` 41/42 (Eval results). t25 approval expired (`Pending action expired`
  when approved late): fail-closed as designed. t21 undo `done`, `old.zip` back.
- Karthik's decision: P3.5 PASSES; step 2 becomes a follow-up. P3.5 ticked in PLAN.md,
  `docs/plans/P3.5.md` marked Implemented. The P3 "Done when" is not met; the phase gate
  waits for the follow-up.
- Next concrete step: Claude Code drafts the follow-up plan (prompt change for multi-step
  sort, sort eval case, t25 expected path, fast-path counter, `--model` with `--real`) for
  Karthik's approval. Prompt changes touch `core/config.toml`, not `config/`.

### 2026-11-16 — Agent: Claude Code (P3.5 C review: accepted)

- Start: HEAD `10254d3`, tree clean, main 2 ahead of `origin/main` (`c43f13b`, `10254d3`).
- Review of `c43f13b` (`P3.5: real evals`) against section C: `bridge/` gains only the
  `get_time` handler, its `datetime` import and the `HANDLERS` entry. `get_time` tests: 200
  with an aware time within 5 s; an extra argument is 403 `unknown argument`. Test B5's
  `get_time` half parses the real reply and still asserts no model call. CLI test: `URLError`
  from `build` prints `bridge is not running`, exit 1. `evals/run.py`: a whitespace-blind
  diff of the stub path shows only the moved imports and the `tools: stubs` header; `--real`
  builds the core once, warms up with `core.handle("Say ok.")`, then per case
  `calls.clear()` / `handle(fresh=True)` / `list(calls)`; `--no-router` goes through
  `build(router=None)`. Nothing in `safety/`, `config/`, `.claude/`. P3.5 unticked.
- Docs from the t24 decision all present: Eval results line (41/42, first 42-case run,
  normpath note; the `--real` line is a placeholder for the manual check), Open question
  (normpath / prompt rule / accept), P3.5.md Verification 2 rewritten, Session log.
- The CLI's `URLError` catch fires only on a failed connection: `BridgeClient._post`
  catches `HTTPError` (a `URLError` subclass) and returns the status, so a 401 or 409 is
  not reported as "bridge is not running". A non-200 on `/task` raises `BridgeError` with a
  traceback; honest, left as is.
- Noted, not changed: `--real --model X` ignores `--model` (the core builds from
  `core/config.toml`), but the summary still prints `model: X`. The manual check runs
  without `--model`, so its summary is correct. Later: refuse `--model` with `--real`, or
  pass it to `build`.
- Re-ran in PowerShell at the repo root: `uv run python -m pytest` 614 passed, 4 skipped.
  No mutants for C (none planned).
- This commit is pushed together with `c43f13b` and `10254d3`.
- Next concrete step: Karthik's manual check (`docs/plans/P3.5.md` "Manual check"). Record
  the `--real` summary lines under Eval results. Tick P3.5 in PLAN.md only after it passes.

### 2026-11-15 — Agent: Claude Code (P3.5 C pre-commit decisions; session closed)

- Section C pre-edit summary approved with three fixes (`build(router=)` forward instead
  of setting `core._router` from evals; `main(argv=None)`; suite reported from
  PowerShell). Read the uncommitted C code before the t24 decision: `get_time`,
  `core/__main__.py`, the router forward and the tests were fine.
- t24 decision: accept stub evals 41/42. Temp 0, same miss twice, so not a flake; not
  caused by C (stub path changed by one header line; `SPECS` byte-identical since A).
  No 42-case baseline existed; the 42nd case and `open_in_app` landed in P3.4 (`42a7ed3`).
  The doubled-backslash destination normalises to `C:\JarvisSandbox\docs`.
- Cursor committed `c43f13b` (`P3.5: real evals`). NOT reviewed yet and NOT pushed: this
  session closed to save context. The review gate holds: push `c43f13b` only with the
  review commit.
- Next concrete step: review `c43f13b` against section C of `docs/plans/P3.5.md`, re-run
  the suite in PowerShell (expect 614 passed, 4 skipped), check the four docs items from
  the t24 decision, then commit `docs: P3.5 C reviewed` and push both. Then Karthik's
  manual check (section "Manual check" in P3.5.md); P3.5 is ticked only after it passes.

### 2026-11-15 — Agent: Cursor (P3.5 C real evals)

- Start: HEAD `0c6ec64` (`docs: P3.5 B reviewed`), tree clean, in sync with `origin/main`.
  Newest Session log entry was "P3.5 B review: accepted". Before edits, with
  `PYTHONPATH` set to the repo: 611 passed, 4 skipped. After the code, PowerShell
  `uv run python -m pytest` at the repo root (`PYTHONPATH` empty): 614 passed, 4 skipped.
  Pre-edit summary approved with three fixes: `build()` takes `router` (no
  `core._router` write from `evals/run.py`); `main(argv=None)` and a `SystemExit`
  test; the PowerShell suite count is the one recorded here.
- Red run, before the handler and `core/__main__.py`: 4 failed, 1 passed.
  `get_time` was 501. The fast-path reply was not JSON. `build(router=None)` raised
  `TypeError`. `core.__main__` was missing. The extra-argument test already returned
  403 `unknown argument` (the policy refuses it before a handler exists).
- `get_time` ignores its args dict and returns only `{"time": now with offset,
  timespec seconds}`. `build(on_pending=_say, router=None)` is how `--real
  --no-router` skips the fast path. The CLI catches `URLError` only.
- Files: `bridge/tools.py` (handler, import, `HANDLERS` entry), `core/agent.py`
  (`router` on `build` only), `core/__main__.py` (new), `evals/run.py`,
  `tests/test_tools.py`, `tests/test_core.py`, `docs/plans/P3.5.md`,
  `docs/PROGRESS.md`. Nothing in `safety/`, `config/`, or `.claude/`. P3.5 is not
  ticked in PLAN.md. No mutant table.
- Tests: `uv run python -m pytest` in PowerShell at the repo root: 614 passed,
  4 skipped.
- Stub evals, `uv run python evals/run.py`, default model, `tools: stubs`. Both
  runs 41/42. Tool selection 27/27, must-refuse 10/10, clarify 5/5, fast path 5/42.
  Run 1: arguments 24/25, median 1.5 s, max 7.5 s. Run 2: arguments 24/25, median
  1.4 s, max 3.5 s. Karthik accepted 41/42: temp 0, the same t24 miss twice, so not
  a flake, and not caused by section C. The stub path changed only by the header
  line, and `SPECS` has been byte-identical since section A. No 42-case baseline
  exists; the last full run was 41/41 on 2026-11-13. `open_in_app` and the 42nd case
  landed in P3.4 (`42a7ed3`) with no stub eval after that. The plan's "still 42/42"
  was wrong. Recorded under Eval results and Open questions. Not part of P3.5.
- Stopped at: this commit. Next concrete step: Claude Code reviews section C, then
  Karthik's manual check in `docs/plans/P3.5.md` (including `uv run python
  evals/run.py --real`). Do not push.

### 2026-11-15 — Agent: Claude Code (P3.5 B review: accepted)

- Pre-edit review of section B: test 9 replaced (two `system_stats` calls are T0 and pass
  in parallel too, so the `parallel_tools` mutant survived). New test 9: two
  `create_folder` confirms in one turn. After the first implementation: the fast path's
  `execute() if get_time else execute(app=...)` was tied to today's two routes; replaced
  by `BridgeTool.call(params)`. Mutants allowed with Karthik's bridge on 8765 up:
  `bridge/` and `safety/` import nothing from `core/` (checked with grep).
- Review of `ddc3049` (`P3.5: core agent`): `core/tools.py` and `core/agent.py` match the
  plan apart from the recorded `call()` change; the guard reads the agent's own list and
  checks `type(t) is BridgeTool`; `parallel_tools=False`, `max_turns=MAX_CALLS + 1`,
  `before_tool_call=self._record`; `tests/test_core_tools.py` gains only `"self._tools"`.
  Nothing in `safety/`, `bridge/`, `config/`, `.claude/`.
- Noted, not changed: the guard compares name SETS, so an extra exact `BridgeTool` with a
  duplicate name passes. Harmless (it is still a bridge tool, the bridge still decides).
  A `BridgeTool` wait that times out leaves the action queued, but the task's own 120 s
  budget started before the 202, so `expire()` removes it before the core's deadline.
- Re-ran in PowerShell: `uv run python -m pytest` 611 passed, 4 skipped. Mutants
  (`%LOCALAPPDATA%\Temp\p35b_mutants.py`, read before running): baseline green, all 11
  killed, `parallel_tools` 3 of 3, both files restored (sha256), `git status` clean.
- Plan change (docs only): P3.5 is ticked in PLAN.md after Karthik's manual check, not in
  commit C, same as P3.3 and P3.4.
- Next concrete step: Cursor sends a pre-edit summary for section C (`P3.5: real evals`).

### 2026-11-15 — Agent: Cursor (P3.5 B core agent)

- Start: HEAD `411e283` (`docs: P3.5 A reviewed`), tree clean, in sync with `origin/main`.
  PowerShell `uv run python -m pytest`: 596 passed, 4 skipped. Newest Session log entry
  was "P3.5 A review: accepted". Pre-edit summary approved with test 9 replaced: a tainted
  task, one turn with `create_folder root/p` and `create_folder root/q`, approve each as
  it appears.
- Red run, before `core/agent.py` existed: collection of `tests/test_core.py` failed with
  `ModuleNotFoundError: No module named 'core.agent'`.
- `BridgeTool.call(params)` holds the request body. `execute(**params)` only returns
  `self.call(params)`. The fast path is `self._tool(name).call(args)`, so a new router
  route is not sent `app=`, and `core/` has no `**` call (`test_no_call_hides_its_keywords`
  refuses those). `execute`'s signature `**` is a `def`, which that scan allows.
- Files: `core/tools.py`, `core/agent.py`, `tests/test_core.py` (B1–B11),
  `tests/test_core_tools.py` (`allowed` gains `"self._tools"` only), `docs/plans/P3.5.md`,
  `docs/PROGRESS.md`. Nothing in `safety/`, `bridge/`, `config/`, or `.claude/`. No
  `core/config.toml` change. P3.5 is not ticked in PLAN.md.
- Tests: `uv run python -m pytest` in PowerShell: 611 passed, 4 skipped.
- Mutants: baseline 22 passed (`tests/test_core.py`). All 11 killed.
  `parallel_tools` left true: `test_sequential_confirmations` killed on run 1, run 2, and
  run 3. Karthik's bridge on `127.0.0.1:8765` was left up (it imports nothing from `core/`).
  Script (not committed): `C:\Users\karth\AppData\Local\Temp\p35b_mutants.py`. It edits
  `core/agent.py` and `core/tools.py` and restores both (sha256 match). After it exited,
  `git diff -- core/` was empty: the two new files are untracked, and no tracked file
  under `core/` changed. Do not run it during a pytest run.
- Stopped at: this commit. Next concrete step: Claude Code reviews section B. Do not start
  section C. Do not push.

### 2026-11-15 — Agent: Claude Code (P3.5 A review: accepted)

- Start: HEAD `06b76dc`, tree clean, in sync with `origin/main`. PowerShell suite:
  589 passed, 4 skipped. Approved Cursor's pre-edit summary with 4 fixes (stale HEAD in
  its summary; `server.run(sockets=[sock])` instead of close-and-rebind; fixture yields
  `(client, root, storage, base)` and `ui(base, storage, path, body)`; mutant run rules).
  All 4 applied in `7d1b875`.
- Review of `7d1b875` (`P3.5: bridge client`): `core/specs.py` block is byte-identical to
  the one removed from `evals/stub_tools.py` (checked with `diff`); no `openjarvis` import
  in `core/specs.py` or `core/bridge_client.py`; client body matches the plan; nothing in
  `safety/`, `bridge/`, `config/`, `.claude/`.
- Test 1 opens both tasks before either tool call. Still valid: the taint is stored per
  task (`policy.new_task(tainted)`), so the first task stays tainted after the fresh one
  clears the global flag. It also pins that.
- Test 7 resets the private `urllib.request._opener` (urlopen's process-wide cache) and
  restores it. Accepted: without it the urlopen mutant survives a full-file run. If a
  Python upgrade renames that attribute, test 7 stops killing that mutant silently;
  re-run the mutants after any Python upgrade.
- Re-ran in PowerShell: `uv run python -m pytest` 596 passed, 4 skipped. Mutants
  (`%LOCALAPPDATA%\Temp\p35a_mutants.py`, read before running, nothing else running):
  baseline green, all 7 killed by the tests in the plan table, file restored (digest
  match), `git status` clean.
- Plan text fixed in section B (docs only): `execute` raises on a connection or JSON
  decode error (the agent path's `ToolExecutor` turns that into a `Tool execution error`
  observation, the fast path propagates it); `live_bridge` yields 4 values; test 8 needs
  a GET for `/pending`.
- Next concrete step: Cursor sends a pre-edit summary for section B (`P3.5: core agent`).

### 2026-11-15 — Agent: Cursor (P3.5 A bridge client)

- Start: HEAD `06b76dc` (`docs: session log, P3.5 A handed to Cursor`), tree clean, in sync
  with `origin/main`. `uv run python -m pytest` in PowerShell: 589 passed, 4 skipped.
  (A run outside PowerShell fails collection with `No module named 'safety'`.)
- Red run, before `core/bridge_client.py` existed: collection of `tests/test_core.py`
  failed with `ModuleNotFoundError: No module named 'core.bridge_client'`. 0 tests ran.
- `live_bridge` keeps the bound socket and calls `server.run(sockets=[sock])` (`workers=1`).
  `server.started` is a bool; the fixture polls it for 10 s. Uvicorn 0.54 did not raise
  on signal handlers off the main thread. No signal patch.
- Test 7: `urlopen` caches one process-wide opener on first use. In a full
  `tests/test_core.py` run the urlopen mutant survived, because tests 1-6 built that
  opener before `HTTP_PROXY` was set. Run alone, the same mutant died with `URLError`
  (port 9 refused). The test now clears `urllib.request._opener` after the env change
  and restores it. The client is unchanged.
- `fresh` inverted is also killed by `test_outcome_pending_approve_and_deny` (a
  non-fresh task becomes fresh, so `create_folder` is 200 instead of 202). The table
  names `test_non_fresh_task_then_fresh`, which failed as well.
- Files: `core/specs.py`, `core/bridge_client.py`, `evals/stub_tools.py`,
  `tests/test_core.py`, `docs/plans/P3.5.md`, `docs/PROGRESS.md`. Nothing in `safety/`,
  `bridge/`, `config/`, or `.claude/`. P3.5 is not ticked in PLAN.md.
- Tests: `uv run python -m pytest` in PowerShell: 596 passed, 4 skipped.
- Mutants: baseline 7 passed. All 7 killed. Script (not committed):
  `C:\Users\karth\AppData\Local\Temp\p35a_mutants.py`. It edits `core/bridge_client.py`
  and restores it; `git diff` on that file was clean when the script exited. Do not run
  it during a pytest run or a bridge start.
- Stopped at: this commit. Next concrete step: Claude Code reviews section A. Do not
  start section B.

### 2026-11-15 — Agent: Claude Code (P3.4 manual check, P3.4 closed; P3.5 plan)

- Start: HEAD `7c8e244`, tree clean, in sync with `origin/main`. `uv run python -m pytest`
  in PowerShell: 589 passed, 4 skipped. (In Git Bash collection fails with
  `No module named 'safety'`; run tests from PowerShell.)
- Manual check by Karthik, PASSED, through a bridge restarted on `37cfde7` (audit `start`
  04:50:33Z). Audit lines read back from `%LOCALAPPDATA%\Jarvis\audit.jsonl` (lines 52-66),
  every task `fresh_context true`, `tainted false`:
  1. `open_in_app vscode C:\JarvisSandbox`: request `allow` T1, `paths.path` the root;
     result `done` `{"opened": "vscode", "pid": 3196}`. VS Code opened on the sandbox
     (Restricted Mode banner is VS Code's own workspace trust).
  2. `open_in_app notepad C:\JarvisSandbox\bye.txt`: `allow` T1; `done`, pid 14332.
     Notepad showed bye.txt as a new tab in an already open Notepad window, so the pid
     is likely a launcher, not the window's process (matters only if a tool ever
     focuses by pid).
  3. `open_in_app explorer C:\JarvisSandbox`: `allow` T1; `done`, pid 30732. Explorer
     window on the sandbox.
  4. `open_in_app calculator C:\JarvisSandbox`: `allow` T1; result `failed`
     `OSError: calculator does not open a path`; PowerShell 500 `Tool failed`; nothing
     opened.
  5. `open_in_app vscode C:\Windows`: request `deny`, reason `path: outside the allowed
     roots`, `tier null`, no result line; PowerShell 403.
- Files: `docs/PROGRESS.md`, `docs/plans/P3.4.md`. No code change. Committed `f7598c4`.
- Planned P3.5 in plan mode (`docs/plans/P3.5.md`, approved by Karthik): four decisions
  (direct `OrchestratorAgent`, `fresh` as the caller's statement, `--real` evals with T2
  waiting for a click, stdlib `urllib`), recorded under Decisions. Checked in OpenJarvis
  `e6b7137`: `ToolExecutor` cuts a tool at `spec.timeout_seconds` (default 30 s), so a
  `BridgeTool` waiting for an approval declares `MAX_SECONDS + 10`; `get_time` and
  `recall_memory` have no bridge handler (501), `get_time` is added in section C.
- Files (second commit): `docs/plans/P3.5.md` (new), `docs/PLAN.md`, `docs/PROGRESS.md`.
- Plan fixes before hand-off (`a85c8ad`): section A test 1 opens the non-fresh task FIRST
  (a fresh task clears the bridge's taint, so the reverse order never sees 202); the
  client uses `build_opener(ProxyHandler({}))` because `urlopen` honours `HTTP_PROXY`;
  new test 7 and a seventh mutant cover it. Hand-off prompt for section A given to Karthik
  (Cursor sends a pre-edit summary first and waits for an OK).
- Stopped at: `a85c8ad`, then this Session-log commit. Next concrete step: Cursor
  implements P3.5 section A (`P3.5: bridge client`); Claude Code reviews it in a fresh
  session (pre-edit summary, then the commit) before section B.

### 2026-11-15 — Agent: Claude Code (P3.4 B review; manual check deferred)

- Start: HEAD `42a7ed3`, tree clean, in sync with `origin/main`. `uv run python -m pytest`
  in PowerShell: 577 passed, 3 skipped.
- Reviewed Cursor's section B pre-edit summary: approved with three notes, all applied
  in `37cfde7`. (1) Keep the nine existing bad `apps.toml` cases (the plan said five) and
  give each new `accepts` case a valid `command`, or the `accepts` validation mutant
  survives on the missing command. (2) Do not rebind `apps` in `create_app`: it is the
  policy's name set; the loaded entries are `app_entries`. (3) The lstat stand-in sets
  `st_reparse_tag=0`, so the refusal comes from the mode check, not an `AttributeError`.
- Reviewed `37cfde7` (`P3.4: open_in_app`) against `docs/plans/P3.4.md`: handler,
  `load_apps`, `apps.toml`, tests 1-10 and the Decisions entry match. Accepted. Nit, not
  fixed: `open_in_app(args)` has no type hints (the plan's code had none either).
- Tests: full suite re-run in PowerShell after `37cfde7`: 589 passed, 4 skipped.
  Mutants re-run with Cursor's `%TEMP%\p34b_mutants.py` (not committed): baseline
  5 passed, 1 skipped; all 8 killed; tree clean afterwards. That script edits
  `bridge/tools.py` on disk and restores it in `finally`, so never run it during a pytest
  run or a bridge start.
- Manual check NOT done: Karthik deferred it to the next session. Checked before stopping:
  `C:\JarvisSandbox\bye.txt` exists (5 bytes) and the vscode command in `apps.toml`
  exists, so steps 1-3 have their targets.
- Note for P3.5 planning: OpenJarvis `_build_tools`
  (`OpenJarvis/src/openjarvis/cli/ask.py:304`) silently skips a tool name that is not in
  `ToolRegistry`. The runtime tools guard must check the tool objects the agent actually
  holds, not the list of names passed to `ask_full`.
- Files: `docs/PROGRESS.md`. No code change.
- Stopped at: this commit. Next concrete step: Karthik runs the P3.4 manual check
  (restart the bridge in tab 1 so it loads `37cfde7`, then the tab 2 setup and the five
  `Jtool` calls in `docs/plans/P3.4.md`). The agent reads the audit lines back from
  `%LOCALAPPDATA%\Jarvis\audit.jsonl`, records them here, and commits
  `docs: P3.4 manual check passes, P3.4 closed`. Then Claude Code plans P3.5 (plan mode,
  docs only).

### 2026-11-15 — Agent: Cursor (P3.4 B open_in_app)

- Start: HEAD `42a7ed3`, tree clean, `main` in sync with `origin/main`. Section A
  reviewed and accepted. `uv run python -m pytest` from the repo root: 577 passed,
  3 skipped.
- Red run before the handler: 22 failed, 1 passed. The pass is
  `test_open_in_app_refused_before_any_launch`: those calls are already 403 in the
  policy. The rest failed because `load_apps` and `App` did not exist.
- `create_app` does not rebind `apps` (the policy name set). The loaded entries are
  `app_entries`. The lstat stand-in sets `st_reparse_tag=0`, so the refusal is the
  `S_IFLNK` mode check.
- Files: `bridge/tools.py`, `bridge/app.py`, `config/apps.toml`, `tests/test_tools.py`,
  `docs/plans/P3.4.md`, `docs/PLAN.md`, `docs/PROGRESS.md`. No `safety/`, routes, or
  `.claude/` change. P3.4 ticked.
- Tests: `uv run python -m pytest` -> 589 passed, 4 skipped. The fourth skip is the
  symlink half of `test_open_in_app_refuses_a_junction_and_a_symlink` (this account
  cannot create symlinks); the junction assertions run before the skip. Mutants in
  `%TEMP%\p34b_mutants.py` (not committed): baseline 5 passed, 1 skipped, all 8 killed.
- Stopped at: this commit. Next concrete step: Karthik's manual check (the five
  `Jtool` calls in `docs/plans/P3.4.md`), then Claude Code reviews section B.

### 2026-11-15 — Agent: Cursor (P3.4 A open_in_app policy)

- Start: HEAD `76f9ea4`, tree clean, `main` in sync with `origin/main`. First pytest
  collection failed with `No module named 'safety'`; with `PYTHONPATH` set to the repo
  root: 557 passed, 3 skipped.
- Red run of the five new policy tests plus `test_counts_match_plan`, before the policy
  change: 6 failed. `open_in_app` was an unknown tool, `Rule` had no `opens`, and the
  eval set was still 41.
- `Rule.opens` is the last field. Putting it beside `path_params` made `rename_file`'s
  positional name argument land in `opens` (9 tests failed); moved to the end, then the
  full suite passed.
- Files: `safety/policy.py`, `evals/stub_tools.py`, `evals/commands.yaml`,
  `tests/test_policy.py`, `tests/test_eval_set.py`, `docs/plans/P3.4.md`, `docs/PLAN.md`,
  `docs/PROGRESS.md`. No bridge, config, or route change. P3.4 not ticked.
- Tests: `uv run python -m pytest` -> 577 passed, 3 skipped. Mutants in
  `%TEMP%\p34a_mutants.py` (not committed): baseline 6 passed, all 5 killed. The
  tier-dropped mutant (`mutating = not rule.opens`) is killed by
  `test_root_itself_cannot_be_changed` because `list_dir` on the root must stay allow.
- Stopped at: this commit. Next concrete step: Claude Code reviews section A, then
  Cursor implements section B (`P3.4: open_in_app`).

### 2026-11-15 — Agent: Claude Code (P3.4 plan)

- Start: HEAD `3a188aa`, tree clean, in sync with `origin/main`. 557 passed, 3 skipped.
- Planned P3.4 in plan mode; Karthik chose a new tool `open_in_app`, `accepts` per app
  (vscode any, explorer folder, notepad file), eval case t25, pywinauto as a rule only.
  Checked on this Python: a junction is `S_ISDIR` to `lstat` with `st_reparse_tag`
  `0xA0000003`, so the handler checks the reparse tag.
- Files: `docs/plans/P3.4.md` (new), `docs/PROGRESS.md`. No code change.
- Stopped at: this commit. Next concrete step: Cursor implements section A
  (`P3.4: open_in_app policy`).

### 2026-11-15 — Agent: Claude Code (P3.3 review and manual check)

- Reviewed `886302d` (A), `f498cf9` (B), `6eb611a` (C) against `docs/plans/P3.3.md`:
  accepted. Full suite re-run in PowerShell after each: 534, 549, 557 passed, 3 skipped.
  Section A: approved the lstat stand-in test (a junction cannot kill the `stat` mutant;
  this account cannot make symlinks). Section B: asked for `scripts=None` instead of a
  mutable `{}` default. Optional, not done: `Script.command` as a tuple.
- Manual check by Karthik, PASSED, through a running bridge started after `6eb611a`
  (normal PowerShell). Audit lines read back from `%LOCALAPPDATA%\Jarvis\audit.jsonl`:
  - `delete_file C:\JarvisSandbox\bye.txt`: request `confirm` reason `T2`; approve
    `recheck ok`; result `{"deleted": true, "undo_id": "30073d84..."}`. `Test-Path` False,
    then `POST /undo` (`kind quarantined`, `undone` set), then `Test-Path` True.
  - `run_named_script run_tests`: request `confirm` `T2`; approve `recheck ok`; result
    `timed_out false`, `exit_code 0`, output the laptop's host name, 43 ms after approve.
  - `run_named_script cmd`: request `deny`, reason `name: not on the allowlist`, nothing
    queued (403 in PowerShell).
- Files: `docs/PROGRESS.md`, `docs/plans/P3.3.md`. No code change.
- Stopped at: this commit. Next concrete step: plan P3.4 (Claude Code), then Cursor
  implements.

### 2026-11-15 — Agent: Cursor (P3.3 C run_named_script)

- Start: HEAD `f498cf9`, tree clean, `main` in sync with `origin/main`. Sections A and B
  reviewed. With `PYTHONPATH` set to the repo root: 549 passed, 3 skipped.
- Red run of the eight new tests before the handler: 7 failed, 1 passed. The five direct
  calls were `KeyError: run_named_script`. `/approve` was 501. The allowlist refusal
  passed. Deny failed because the fake replaced `subprocess.run` on the shared module
  and the bridge's `whoami` call got bytes. The fake was then bound only on
  `bridge.tools`, the same way `fake_popen` is.
- `bridge/tools.py`: `run_named_script` inside `mutating()`. Fixed argv, `shell=False`,
  the entry's `cwd` and `timeout`, stdin `DEVNULL`, combined stdout. Last 4096 characters.
  A timeout is a result (`exit_code` null). No undo record. `tests/test_tools.py`: the
  eight plan tests. No change to `safety/`, `config/`, or routes.
- Green: `uv run python -m pytest` with `PYTHONPATH` -> 557 passed, 3 skipped. Mutants
  from `%TEMP%\p33c_mutants.py` (not in the repo): all 7 killed. Table in
  `docs/plans/P3.3.md`. PLAN.md P3.3 ticked.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.3.md`, `docs/PLAN.md`,
  `docs/PROGRESS.md`.
- Stopped at: this commit. Not done: Karthik's manual check (create `C:\JarvisSandbox`
  and `bye.txt` first; steps in `docs/plans/P3.3.md`). Next concrete step: Claude Code
  reviews this commit.

### 2026-11-15 — Agent: Cursor (P3.3 B scripts.toml)

- Start: HEAD `886302d`, tree clean, `main` in sync with `origin/main`. With `PYTHONPATH`
  set to the repo root: 534 passed, 3 skipped.
- Red run of the 16 tests (real `scripts.toml`, missing file, 13 bad entries, taint
  census): 16 failed. The tool tests were `AttributeError: load_scripts`. The census
  failed because `run_named_script` was not in the taint set.
- `config/scripts.toml`: `dev_server`, `run_tests`, `backup_notes`, each
  `HOSTNAME.EXE`. `bridge/tools.py`: `_checked_command` shared by `load_commands`;
  frozen `Script`; `load_scripts`; `mutating(undo_log, commands, scripts=None)` then
  `scripts = scripts or {}`. `bridge/app.py`: loads the file next to `apps.toml` and
  passes it in. `safety/policy.py`: `taints=True` on `run_named_script` only.
  `tests/test_policy.py`: that name added to the taint census. No handler.
- Green: `uv run python -m pytest` with `PYTHONPATH` -> 549 passed, 3 skipped. Mutants
  from `%TEMP%\p33b_mutants.py` (not in the repo): baseline 16 passed, all 6 killed.
  Table in `docs/plans/P3.3.md`.
- Files: `config/scripts.toml`, `bridge/tools.py`, `bridge/app.py`, `safety/policy.py`,
  `tests/test_tools.py`, `tests/test_policy.py`, `docs/plans/P3.3.md`, `docs/PROGRESS.md`.
  PLAN.md P3.3 stays unticked.
- Stopped at: this commit, pushed. Not done: section C, Karthik's manual check. Next
  concrete step: Claude Code reviews this commit, then section C
  (`P3.3: run_named_script`) on Karthik's go.

### 2026-11-15 — Agent: Cursor (P3.3 A delete_file)

- Start: HEAD `0647d0f`, tree clean, `main` one commit ahead of `origin/main` (the plan
  commit). `uv run python -m pytest` in this session failed to import `safety` before
  collecting (the failure already logged for a non-PowerShell pytest). With `PYTHONPATH`
  set to the repo root: 526 passed, 3 skipped.
- Red run of the eight new tests against the missing handler: 5 failed, 3 passed. The
  four direct calls were `KeyError: delete_file`. `/approve` was 501. Deny, the junction
  swapped in while pending, and the root / protected-folder refusals already passed.
- `bridge/tools.py`: `delete_file` inside `mutating()`. `os.lstat` must say a plain file,
  then `undo_log.quarantine`. Nothing is unlinked. `tests/test_tools.py`: the seven plan
  tests plus `test_delete_file_trusts_lstat_not_the_name`, copied from the rename_file
  stand-in and approved by Karthik 2026-11-15. The junction half always runs; a real
  symlink is attempted and, when this account cannot create one, that half returns
  without skipping the junction.
- Green: `uv run python -m pytest` with `PYTHONPATH` -> 534 passed, 3 skipped. Mutants
  from `%TEMP%\p33a_mutants.py` (not in the repo): baseline 8 passed, all 5 killed.
  Table in `docs/plans/P3.3.md`.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.3.md`,
  `docs/PROGRESS.md`. PLAN.md P3.3 stays unticked. No change to `safety/`, `config/`,
  routes, or `.claude/`.
- Stopped at: this commit, pushed (the push also carries `0647d0f`). Not done: section B,
  section C, Karthik's manual check. Next concrete step: Claude Code reviews this
  commit, then section B (`P3.3: scripts.toml`) on Karthik's go.

### 2026-11-14 — Agent: Claude Code (P3.3 plan)

- Explored what P3.3 already has: both policy entries (T2), `UndoLog.quarantine`, the
  confirm queue and routes, the `scripts` allowlist loading. Missing: two handlers,
  `config/scripts.toml`, a script loader.
- Karthik chose: wait-and-capture scripts, eval-name placeholders in `scripts.toml`, he
  creates `C:\JarvisSandbox`. Plan written and approved in plan mode.
- Files: `docs/plans/P3.3.md` (new), `docs/PROGRESS.md`. No code changed. No tests run.
- Next concrete step: Cursor implements section A of `docs/plans/P3.3.md`
  (`P3.3: delete_file`), stops for review, then B, then C.

### 2026-11-14 — Agent: Claude Code (review of P3.2d, manual checks, focus_window closed)

- Reviewed Cursor's `a39ede0` (P3.2d) against `docs/plans/P3.2d.md`: PASS. Own run:
  526 passed, 3 skipped. `_to_front` is plain call, wait, minimise, restore, wait; attach
  route gone, source guard test keeps it out.
- Karthik's manual checks through a running bridge (normal PowerShell): covered 327 ms,
  minimised 123 ms, maximised-and-covered 563 ms (stayed maximised). All `focused: true`.
  One `time budget exceeded (120 s)` refusal in between was a stale task id, as designed.
- Files: `docs/PROGRESS.md` only. No code changed.
- Next concrete step: plan P3.3 (`delete_file` to quarantine, `run_named_script` from
  `config/scripts.toml`) on Karthik's go. P3.3 is not started.

### 2026-11-14 — Agent: Cursor (P3.2d focus_window lands through minimise and restore)

- Start: HEAD `4070754`, tree clean. `uv run python -m pytest` in this PowerShell
  session failed to import `safety` before collecting (the failure already noted for a
  non-PowerShell pytest). The green run below set `PYTHONPATH` to the repo root and
  collected. Not `pytest.main()`.
- Red run of the six new tests against the pre-fix handler: 4 failed, 2 passed
  (`plain_call_makes_no_show_call` and `minimised_lands_on_the_first_restore` already
  matched). The three restore failures were `AttributeError` on the removed
  `GetWindowThreadProcessId`. The source guard still saw `AttachThreadInput`.
- `bridge/tools.py`: `_to_front` is the plain call, then minimise and restore, each
  followed by `_settled` (default 500 ms). Attach declarations and `import threading`
  removed. `GetWindowThreadProcessId` argtypes for `_all_windows` stay.
  `tests/test_tools.py`: `lands_on_restore`, six tests, attach fakes and tests deleted,
  `lies` dropped. `settles_too_late` keeps `settles_after=100` and `OSError` by refusing
  the plain call and starting a fresh 100-read hide on the restore: one 500 ms cap
  cannot see 100 reads, and a hide left by the plain call can be finished by the second
  wait. Test 5 replaced in implementation, approved by Karthik: a minimised window
  lands on the first restore, log is restore then the plain call, no second restore.
- Green: `uv run python -m pytest` -> 526 passed, 3 skipped. Mutants from
  `%TEMP%\p32d_mutants.py` (not in the repo): baseline 20 passed, all 7 killed. Table
  in `docs/plans/P3.2d.md`.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.2d.md`, `docs/PLAN.md`,
  `docs/PROGRESS.md`. No change to `safety/`, `config/`, routes, or the policy entry.
- Stopped at: this commit, pushed. Not done: Karthik's manual check through a running
  bridge (Notepad covered, then minimised, then maximised and covered; read the audit
  lines back into this file). Next concrete step: that check. P3.3 is not started.

### 2026-11-14 — Agent: Claude Code (review of P3.2c, manual checks, P3.2d plan)

- Reviewed Cursor's `a50674f` (P3.2c) against `docs/plans/P3.2c.md`: PASS. Own run:
  532 passed, 3 skipped.
- Karthik's manual checks through a running bridge (normal PowerShell, not admin):
  covered Notepad FAIL (518 ms, genuine refusal), minimised Notepad PASS (228 ms).
- Diagnosis probes run from this session (scripts outside the repo, not committed) gave
  contradictory results and were discarded: children of the foreground window inherit the
  foreground right. Lesson recorded in `docs/plans/P3.2d.md`: only checks through the bridge
  count for focus behaviour.
- Karthik chose minimise + restore with the attach code removed. Plan written.
- Files: `docs/plans/P3.2d.md` (new), `docs/PROGRESS.md`. No code changed.
- Next concrete step: Cursor implements `docs/plans/P3.2d.md` (one commit), then Karthik
  repeats the manual check (covered, minimised, maximised-and-covered). P3.3 not started.

### 2026-11-14 — Agent: Cursor (P3.2c focus_window waits for the activation)

- Start: HEAD `af989e8`, tree clean. `uv run python -m pytest` from this PowerShell
  session sometimes failed to import `safety` before collecting (the failure already
  noted for a non-PowerShell pytest). The green run below is `uv run python -m pytest`
  in PowerShell, and it collected on that invocation. Not `pytest.main()`.
- Red run of the five new tests against the pre-fix handler: 3 failed, 2 passed
  (`never_settles` and `settles_too_late` already raise `OSError`).
- `bridge/tools.py`: `_settled`, called after the plain `SetForegroundWindow` and after
  the attached call's detach. `tests/test_tools.py`: `settles_after`, `FakeClock`, five
  tests. No change to `safety/`, `config/`, routes, or the policy entry.
- Green: `uv run python -m pytest` -> 532 passed, 3 skipped. Mutants from
  `%TEMP%\p32c_mutants.py` (not in the repo): baseline 26 passed, all 6 killed. Table
  in `docs/plans/P3.2c.md`.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.2c.md`, `docs/PLAN.md`,
  `docs/PROGRESS.md`.
- Stopped at: this commit, pushed. Not done: Karthik's manual check through a running
  bridge (Notepad covered, then Notepad minimised; read the audit line back into this
  file). Next concrete step: that check. P3.3 is not started.

### 2026-11-14 — Agent: Claude Code (review of P3.2b, manual check, P3.2c plan)

- Roles from now on: Claude Code plans and reviews; Cursor implements.
- Backed up the repo to private GitHub `Karthikollur/Jarvis-v2` (history scanned for
  secrets first: none). AGENTS.md now says to push after the final commit.
- Reviewed Cursor's `a2ce53b` (P3.2b) against `docs/plans/P3.2b.md`: PASS. Re-ran the suite:
  527 passed, 3 skipped. Read-only check that real `GetForegroundWindow` and `_all_windows`
  handles are both `int` and compare equal.
- Karthik's manual check through a running bridge: `focus_window` notepad FAIL (`OSError`).
  Diagnosis (script outside the repo, not committed): Windows accepted the focus, the
  foreground read `None` during the handoff, Notepad was in front 25 ms later.
- Files: `docs/plans/P3.2c.md` (new), `docs/PROGRESS.md`. No code changed. No tests needed.
- Next concrete step: Cursor implements `docs/plans/P3.2c.md` (one commit), then Karthik
  repeats the manual check. P3.3 is not started.

### 2026-11-14 — Agent: Cursor (P3.2b focus_window foreground)

- Start: HEAD `c34cb0b`, tree clean, `uv run python -m pytest` through PowerShell ->
  518 passed, 3 skipped. A non-PowerShell pytest fails to import `safety`; use PowerShell.
- Tests first, in `tests/test_tools.py`: `FakeUser32` learned a foreground handle,
  thread ids, a hung set, `AttachThreadInput`, and `SetForegroundWindow` modes
  `refuses` / `needs_attach` / `lies`. Nine new tests (the ninth, a raise while
  attached, approved by Karthik during implementation). Red run of `focus_window`:
  6 failed, 15 passed. The no-foreground, own-thread, and hung tests already passed,
  because today's refusal does not attach.
- `bridge/tools.py`: `_to_front(hwnd)` and `focus_window` calls it. ctypes and the
  standard library only. No change to `safety/`, `config/`, routes, or the policy entry.
- Green: `uv run python -m pytest` -> 527 passed, 3 skipped. Mutants in memory from
  `%TEMP%\p32b_mutants.py` (not in the repo): baseline 21 passed, all 8 killed. Table
  in `docs/plans/P3.2b.md`.
- Files: `bridge/tools.py`, `tests/test_tools.py`, `docs/plans/P3.2b.md`, `docs/PLAN.md`,
  `docs/PROGRESS.md`.
- Stopped at: this commit, pushed. Not done: Karthik's manual check through a running
  bridge (open Notepad, cover it, `focus_window`; repeat with Notepad minimised; read
  the audit line back into this file). Next concrete step: that check. P3.3 is not started.

### 2026-11-13 — Agent: Claude Code, Opus 5.5 (P3.2 F: move_files, two commits)

- Start: HEAD fcd6e1c (`docs: P3.2 F plan`), tree clean except the two untracked root
  files (left alone), 480 passed, 3 skipped. Note: pytest from Git Bash fails to import
  `safety`; run it through PowerShell as the Commands section says.
- F1 `P3.2: move_files policy` (fc1b9f3): `safety/policy.py` (`MAX_BATCH`,
  `Rule.list_params`, `_resolve_batch`), stub spec, eval case t24 (Karthik's call after
  two plan gaps, logged under Open questions and Decisions), `_norm` for lists, sweeps
  extended. 509 passed; 8 mutants killed; evals 41/41.
- F2 `P3.2: move_files`: `bridge/tools.py` `move_files`, `bridge/app.py` `/pending`
  renders tuples as lists, 9 tests in `tests/test_tools.py` (temp folders only). Red: 8
  of 9 failed. 518 passed, 3 skipped. 9 mutants killed (table in `docs/plans/P3.2.md`).
- Stopped at: P3.2 complete and ticked; plan marked Implemented. Still open: Karthik's
  manual checks of `open_app` / `focus_window` through a running bridge;
  `C:\JarvisSandbox` not created. Next concrete step: P3.3 plan or commit, on Karthik's
  go only. Not started.

### 2026-11-13 — Agent: Claude Code (P3.1b, three commits)

- Start: HEAD 630906d, tree clean except the two untracked root files (`PowerShell 5.1`,
  a saved `git diff`; `oft Corporation. All rights reserved.`, the `less` help screen;
  left alone), 423 passed, 2 skipped.
- A `P3.1b: outcome survives odd results`: `bridge/app.py` `outcome()` returns
  `encoded(...)`; new test `test_surrogate_in_an_outcome_is_returned` in
  `tests/test_bridge.py`. Red: `UnicodeEncodeError` on `/outcome` after approve 200
  (first attempt was 403 because test storage is in the repo; fixed with `protected=[]`
  as the `sandbox` fixture does). Mutant = pre-fix line = red run.
- B `P3.1b: read_text_file refuses a hard link`: `_single_name(fd)` in `bridge/tools.py`,
  docstring rule, rule 7 in `docs/plans/P3.2.md`; new test
  `test_read_text_file_refuses_a_hard_link` in `tests/test_tools.py` (no skip if
  `os.link` fails). Red: `DID NOT RAISE`. In-memory mutant (helper = plain `fstat`) killed.
- C `P3.1b: tools guard scans subfolders`: `tests/test_core_tools.py` gets `sources(base)`
  with `rglob`, `hidden_keywords()`, `test_no_call_hides_its_keywords` and two `tmp_path`
  scan tests. Red (with `glob`): nested `core/sub/x.py` call site missed. In-memory mutant
  (`hidden_keywords` blinded) killed. PLAN.md: P3.1b ticked, P3.5 runtime guard added.
- Tests: `rtk proxy uv run python -m pytest` -> 428 passed, 2 skipped. Evals not re-run
  (core still uses stub tools until P3.5).
- Stopped at: P3.1b complete, plan marked Implemented. Next concrete step: P3.2 commit A
  `P3.2: create_folder` (plus `mutating` wiring), on Karthik's go.

### 2026-11-13 — Agent: Claude Code (P3.1 T0 tools, four commits)

- Start: HEAD 202d7b2, tree clean except the two untracked root files (left alone),
  394 passed, 1 skipped. Recorded Karthik's restore point and his real Ctrl+Alt+End check
  (572c94f, with the P3.1 plan `docs/plans/P3.1.md`).
- Commits, each on Karthik's go, each with a red run against a stub, then green, then
  in-memory mutants: A `list_dir` (593999d, A1-A6), B `read_text_file` (7f31ec7, B1-B8),
  C `list_windows` (bf1d669, C1-C7), D `system_stats` (this commit, S1-S9; S9 first
  survived and got a test). Every mutant killed; tables in `docs/plans/P3.1.md`.
- Files: new `bridge/tools.py` (handlers + `HANDLERS`), `bridge/app.py` (`handlers=None`
  means `tools.HANDLERS`), new `tests/test_tools.py`, one comment in
  `tests/test_bridge.py`, docs.
- Deviations from the plan, all recorded in it: no `lstat` check in `read_text_file` (the
  final-path check covers every followed link; a junction test proves it); the two old
  "501" tests keep `list_windows`; no CPU clamp.
- Tests: see Current state. Evals not re-run: the core still uses stub tools until P3.5.
- No dependency added (stdlib + ctypes; `nvidia-smi` is already on the machine).
  `C:\JarvisSandbox` not created.
- Stopped at: P3.1 complete. Next concrete step: plan P3.2 (T1 tools, undo records,
  batch confirmation) on Karthik's go.

### 2026-11-13 — Agent: Claude Code (P2.9 C mutation checks; P2.9 D implemented)

- Start: tree clean (two untracked root files `PowerShell 5.1` and `oft Corporation. All
  rights reserved.` left untouched, as Karthik asked), HEAD 93bcfff, 391 passed, 1 skipped.
- C mutation checks (commit 7dc3343): 5 in-memory mutants (mutated source exec'd into
  `sys.modules`, then pytest.main; no repo file edited), all killed. Table in
  `docs/plans/P2.9.md`. A run of four mutants back to back hit the 600 s tool timeout;
  that was the timeout, not a hang (each run takes about 150 s).
- D (plan approved by Karthik, two choices: raced task answers 403; scorer takes `?` or an
  ask-phrase). Files: `bridge/app.py` (`POST /task` re-checks `halted` after the insert),
  `evals/run.py` (`score`), `tests/test_bridge.py` (2 tests + helper
  `stop_during_task_insert`), `tests/test_eval_scoring.py` (1 test), docs.
- Red run: latching test got 200 with a task id; scorer test failed. Core-Stop test passed
  before and after (it pins that a core Stop does not latch).
- Green: `rtk proxy uv run python -m pytest` -> 394 passed, 1 skipped. Mutants D1 (no
  re-check), D2 (403 but task not marked stopped), D3 (scorer `?` only): each killed.
  Evals `uv run python evals/run.py` -> 40/40 (clarifying 5/5, median 1.1 s).
- Stopped at: P2.9 complete. P3 not started. Next concrete step: Karthik's restore point,
  then P3.1 on his go.

### 2026-11-12 — Agent: Claude Code (P2.8 adversarial review; P2.9 planned, docs only)

- Did: start-of-session protocol; review of `git diff 1d341fd..HEAD` as someone else's
  code. Probes and mutants ran in memory (stdin scripts), nothing committed but docs.
- Found: R1 sibling task escapes taint; R2 restart clears taint; R3 `move_file` has no
  checked landing place and cannot move into the root; R4 surrogate name strands a
  quarantined file; R5 surrogate path makes `GET /pending` 500; R6 unencodable result
  leaves no `result` line; R7 task created mid-Stop survives the latch. Details and fixes:
  `docs/plans/P2.9.md`.
- Commit B check: nine mutants of the argument rules, all killed by B's tests.
- Tests: `uv run python -m pytest` -> 381 passed, 1 skipped. Evals `--only a` -> 4/5,
  a03 fails on the scorer's `?` rule; the model made no tool call and asked for details.
- Verdict: P2 safe to close; P3.1 safe after the restore point; P2.9 A–C before P3.2/P3.3.
- Files: `docs/plans/P2.9.md` (new), `docs/PLAN.md`, `docs/PROGRESS.md`.
- Stopped at: plan recorded. Next step: P2.9 commit A on Karthik's go.

### 2026-11-12 — Agent: Claude Code (P2.8 hardening implemented; awaits Karthik's review)

- Did: after the P2 gate passed, a read-only phase review found six policy gaps (N1-N6)
  and three more items; Karthik approved fixing them as P2.8 before P3. Six commits, one
  per go: 089e6b5 path rules; c195b5d argument rules; 387a49f taint survives a new task;
  0d4f0df stop latch; 1fab025 kill-switch liveness and audit encoding; commit F tests only
  (built-in tools guard, sweep additions) with P2.8 ticked.
- Files: `safety/policy.py`, `safety/audit.py`, `bridge/app.py`, `bridge/hotkey.py`,
  `tests/` (new `tests/test_core_tools.py`), `docs/PLAN.md`, `docs/PROGRESS.md`,
  `docs/plans/P2.8.md`.
- Tests: `uv run python -m pytest` -> 381 passed, 1 skipped (symlink test, as before).
  Evals `uv run python evals/run.py` -> 39/40, unchanged (a03 fails as in the baseline).
  Mutation checks for every commit (32 mutants in total), each failed the tests meant to
  catch it and was restored.
- Not a clean red-green for commit B: the first test run failed on shell quoting, so its
  tests first ran after the code existed; the mutation checks stand in for the red run.
- Existing tests changed on purpose: a ui Stop now latches (D); the token sweep and the
  32-thread HTTP test no longer restart one app many times (E).
- Tooling note for the next agent: in this Git Bash, heredocs halve backslashes and a
  stray quote can abort a whole command. Write test snippets with the file tools and
  apply them with a small script instead.
- Stopped at: P2.8 complete. Not done: Karthik's review of `git diff 1d341fd..HEAD`;
  the restore point; anything in P3.
- Next step: Karthik reviews P2.8; then P3.1.

### 2026-11-12 — Agent: Claude Code (P2.7 implemented; P2 gate awaits Karthik)

- Did: start-of-session protocol (tree clean at bdc6241, nothing to discard; the
  interrupted commit A had left no changes). Then P2.7 in three commits, one per go:
  013bc66 policy lock; fdf94dd Stop cannot leave a queued action; commit C traversal and
  token sweeps (tests only) with P2.7 ticked.
- Files: `safety/policy.py`, `bridge/app.py` (7 lines in `/tool`), `tests/test_policy.py`,
  `tests/test_bridge.py`, `docs/PLAN.md`, `docs/PROGRESS.md`, `docs/plans/P2.7.md`.
- Tests: `uv run python -m pytest` -> 259 passed, 1 skipped (symlink test, as before).
  Race tests use `threading.Barrier`, no sleeps; every thread is a daemon joined with a
  timeout. Mutation checks, each failed the named tests and was restored: lock removed
  from `check` / from `record`; `_stop` taking the lock (deadlock test); stopped-check
  after `queue.add` removed; `destination` path check skipped (5 sweep cases).
- Deviations from the plan text (tests only), logged under Open questions: concurrent
  HTTP calls assert from the audit log instead of "exactly 8 answered 200"; the race test
  presses Stop before the queue insert, not after.
- Stopped at: P2.7 complete. Not done: P2 gate (Karthik reviews the diff
  `git diff bdc6241..HEAD`).
- Next step: Karthik's gate review and answers to the two Open questions; then P3.
- Later the same session: gate review done (Fable 5.2, read-only, suite re-run 259/1);
  Karthik passed the P2 gate and answered both questions (KEEP, OK). Docs-only commit.
  Next: should-fix (a) and (b) under Open questions, (a) needs plan mode and Karthik's OK;
  then P3.1.
- Later again: P2 phase review on Karthik's request (read-only). Tests 259 passed,
  1 skipped; evals 39/40 (tool selection 25/25, must-refuse 10/10, clarifying 4/5, median
  1.2 s; a03 fails as in the baseline). Six new policy gaps N1-N6 logged under Open
  questions (top entry) with the known ones. Nothing fixed: Karthik reviews first.
  Next: Karthik decides per finding; then P3.0a (plan mode).
- Later again: analysis of N1-N6 and three more items; Karthik approved P2.8 hardening as
  proposed. Plan saved at `docs/plans/P2.8.md`, PLAN.md changed, decisions recorded. Docs
  only, no code. Next step: P2.8 commit A (path rules) on Karthik's go.

### 2026-11-12 — Agent: Claude Code (P2.6 implemented; audit point 9 closed)

- Did: reviewed the P2.6 draft against the code; Karthik approved it with four fixes
  (32-hex ids, quarantine paths from the id only; `os.rename` only; only user-side paths
  through `resolve`; protected folders realpath-resolved + 8.3 test). Then three commits,
  tests first, each stopped for review: A `f4ca891` protected folders, B `edd2ac5`
  `safety/undo.py`, C undo routes. One layout change from the plan, recorded in it:
  `<id>/item` is the quarantined thing itself (the plan had `<id>/item/<name>`, which used a
  record value on the quarantine side).
- Files changed: `safety/policy.py`, `safety/undo.py` (new), `bridge/app.py`,
  `tests/test_policy.py`, `tests/test_undo.py` (new), `tests/test_bridge.py` (sandbox roots
  now beside storage, not inside it), `docs/plans/P2.6.md`, `docs/PLAN.md`, this file.
- Tests: 216 passed, 1 skipped (symlink test). Mutation checks: A dropping the protected
  check fails 14 tests, dropping the realpath at `Policy` build fails 1; B `os.replace` +
  no occupied check fails 3; C ungating the pre-undo audit write fails the fail-closed test.
  All restored.
- Not checked by a human: a real bridge start (now also creates
  `%LOCALAPPDATA%\Jarvis\quarantine`).
- Unfinished work stopped at: nothing in progress. P2.6 ticked.
- Next concrete step: plan P2.7 in plan mode (traversal/token/budget/taint/kill-switch
  tests and the `Policy`/`Task` lock) and get Karthik's approval.

### 2026-11-12 — Agent: Claude Code (P2.6 drafted; laptop hang diagnosed; handoff)

- Did: drafted the P2.6 plan after Karthik answered four design questions; saved it as
  `docs/plans/P2.6.md`, marked DRAFT, NOT APPROVED (the approval step was cut off by a hard
  shutdown). After the shutdown: read-only diagnosis of the hang (90% RAM, overheating).
- Diagnosis: repo healthy after the shutdown (`git fsck` clean, no `index.lock`, 179
  passed, 1 skipped). Tests start no servers (FastAPI `TestClient` in-process only, hotkey
  listeners closed in `finally`); Python process count was the same before and after a run,
  port 8765 never listening. Windows logged no unexpected shutdown or low-memory event in 7
  days. Most likely cause: everything running at once on 16 GB: Claude app (~3 GB), more
  than one Claude Code session each starting ~750 MB of MCP servers (rea, serena, headroom,
  repomix, notebooklm-py), a Codex session, and the Ollama model. Not this repo's code.
- Changed OUTSIDE the repo, at Karthik's request: those five MCP servers turned off
  globally. `~/.claude.json`: user `mcpServers` emptied (entries saved in
  `~/.claude/mcp-servers-removed-2026-11-11.json`) and the Jarvis_v2 project lists them in
  `disabledMcpServers`; `~/.claude/settings.json`: plugin `repomix-mcp@repomix` = false.
  Backups beside both files (`.bak-2026-11-11*`). `claude-mem` kept. Verified: 0 such
  processes in a new session; RAM used fell from 10.8 to 10.1 GB. Side effect: running
  `ollama ps` started the Ollama app.
- Files changed in the repo: `docs/plans/P2.6.md` (new), `docs/PROGRESS.md`.
- Tests: 179 passed, 1 skipped (no code changed).
- Unfinished work stopped at: P2.6 plan awaiting Karthik's approval. No P2.6 code.
- Next concrete step: Karthik approves `docs/plans/P2.6.md`; then commit A (protected
  folders), tests first.

### 2026-11-11 — Agent: Claude Code (P2.5 kill switch, implemented)

- Did: P2.5 planned (Karthik answered four questions), plan saved as `docs/plans/P2.5.md`
  (`ebf6901`), then two commits:
  A. `P2.5: kill switch endpoint` (`5b06f43`) — `POST /stop`, `stop()`, `cancelled`
     outcome, stopped check in `execute()`, `ConfirmQueue.clear()` returns what it dropped.
  B. `P2.5: global hotkey listener` — `bridge/hotkey.py`, `config/hotkey.toml`, lifespan
     wiring, fake listener in `tests/conftest.py`. P2.5 ticked, plan marked Implemented.
- Files changed: `safety/confirm.py`, `bridge/app.py`, `bridge/hotkey.py`,
  `config/hotkey.toml`, `tests/conftest.py`, `tests/test_confirm.py`, `tests/test_bridge.py`,
  `tests/test_hotkey.py`, `docs/PLAN.md`, `docs/plans/P2.5.md`, `docs/PROGRESS.md`.
  No new dependencies.
- Tests: `rtk proxy uv run python -m pytest` -> 179 passed, 1 skipped (symlink privilege).
  `tests/test_hotkey.py` registers a REAL global hotkey (`Ctrl+Alt+Shift+F24`) for a moment
  and posts `WM_HOTKEY` to its thread; no key is pressed. Mutation checks: A — without
  `task.stopped` in `stop()` and the `execute()` check, 5 tests fail; B — without the
  listener in the lifespan and without the callback guard, 3 tests fail. Restored, green.
- Not done: real bridge start and a real `Ctrl+Alt+End` press (Karthik). Evals not rerun.
- Unfinished: none.
- Next concrete step: plan P2.6 (quarantine + undo records + audit point 9) in plan mode.

### 2026-11-11 — Agent: Claude Code (P2.4 audit log, implemented)

- Did: P2.4 in three commits, as planned in `docs/plans/P2.4.md`.
  A. `P2.3: expire timed-out pending actions` (`3f908b3`) — `Policy.out_of_time`, bridge
     `expire()`, 410 on expired ids, `/outcome` pending during a handler run.
  B. `P2.4: audit log (safety)` (`ca3dc2b`) — `safety/audit.py`, `tests/test_audit.py`.
  C. `P2.4: bridge writes the audit log` — events, fail-closed paths, 11 bridge tests plus
     an audit assertion on the junction-swap test. P2.4 ticked, plan marked Implemented.
  Codex ran a recovery check between A and B (`725bbe7`, docs only).
- Files changed: `safety/policy.py`, `safety/audit.py`, `bridge/app.py`,
  `tests/test_policy.py`, `tests/test_audit.py`, `tests/test_bridge.py`, `docs/PLAN.md`,
  `docs/plans/P2.4.md`, `docs/PROGRESS.md`. No new dependencies.
- Tests: `rtk proxy uv run python -m pytest` -> 147 passed, 1 skipped (symlink privilege).
  Mutation check: with the pre-run `request` and `approve` writes no longer gating, 7 tests
  fail (fail-closed, invariant, flow-order and junction tests); restored, green again.
  No real uvicorn start (would create `%LOCALAPPDATA%\Jarvis`). Evals not rerun; core untouched.
- Unfinished: none. Three implementation choices recorded under Decisions.
- Next concrete step: plan P2.5 (kill switch) in plan mode and get Karthik's OK.

### 2026-11-11 — Agent: Codex (P2.4 recovery check)

- Did: read AGENTS.md, PROGRESS.md, active PLAN.md phase and docs/plans/P2.4.md;
  inspected status, latest ten commits and commit A summary. Commit A completed as
  3f908b3; no staged or unstaged tracked changes remained to finish or revert.
- Recovery decision: retain completed commit A. The sole untracked file is
  .claude/settings.local.json (local permission rules); leave it untouched and uncommitted
  under AGENTS.md's prohibition on editing agent permissions. No implementation recovery needed.
- Files changed this session: docs/PROGRESS.md only (current state and this handoff).
- Tests: uv run python -m pytest -> 127 passed, 1 skipped (symlink privilege),
  1 existing Starlette/httpx deprecation warning. Cache access required escalation.
- Stopped at: recovery inspection complete; no safety/ or bridge/ edits. Commit B and C
  remain unimplemented. Waiting for Karthik's go before B; tests first, one commit, then stop
  with a diff summary. Next: tests/test_audit.py and safety/audit.py exactly per commit B.


### 2026-11-11 — Agent: Claude Code (P2.3 reviewed, P2.4 planned, not implemented)

- Did: reviewed commits `46b88d8` and `7e97cb9` against `docs/plans/P2.3.md` (small drift,
  nothing weakened; one new finding: `/outcome` answers 404 while an approved action runs);
  triaged the open P2.3 gaps; wrote the P2.4 plan. All of it is in `docs/plans/P2.4.md`.
- Files changed: `docs/plans/P2.4.md` (new), `docs/PROGRESS.md`. No code changed.
- Tests: not rerun (docs only); last run after `7e97cb9`: 123 passed, 1 skipped.
- Next concrete step: get Karthik's answers to the four decisions, then implement commit A
  of `docs/plans/P2.4.md`.

### 2026-11-11 — Agent: Claude Code (P2.3 confirm queue)

- Did: P2.3 in two commits, as planned in `docs/plans/P2.3.md`.
  A. `P2.3: confirm queue (safety)` (`46b88d8`) — `safety/confirm.py`, `Policy.recheck`,
     confirm reasons `T2` / `tainted T1`, shared fixtures moved to `tests/conftest.py`.
  B. `P2.3: approve and deny routes` — `/pending`, `/approve`, `/deny` (ui),
     `/outcome` (core), `/tool` answers 202 on confirm, shared `execute()`,
     `create_app(clock=...)`. P2.3 ticked in PLAN.md, plan marked Implemented.
- Files changed: `safety/confirm.py`, `safety/policy.py`, `bridge/app.py`,
  `tests/conftest.py`, `tests/test_confirm.py`, `tests/test_policy.py`,
  `tests/test_bridge.py`, `docs/PLAN.md`, `docs/plans/P2.3.md`, `docs/PROGRESS.md`.
  No new dependencies.
- Tests: `rtk proxy uv run python -m pytest` -> 123 passed, 1 skipped (symlink privilege).
  Mutation check: with `recheck` disabled in `/approve`, the junction-swap and expiry
  tests fail. Evals not rerun; core untouched. No real uvicorn start.
- Unfinished: none. Two small open questions logged (no eviction; `denied` vs `expired`
  label when the task was stopped by another call).
- Next concrete step: plan P2.4 (audit log, JSONL) in plan mode and get Karthik's OK.

### 2026-11-11 — Agent: Claude Code (P2.3 planned, not implemented; handoff)

- State for a new agent: P0, P1, P2.1, P2.2 done. Next is P2.3 (confirm queue). Its plan is
  approved and lives at `docs/plans/P2.3.md`: two commits, A (`safety/confirm.py`,
  `Policy.recheck`, tests) then B (`/pending`, `/approve`, `/deny`, `/outcome` routes, tick
  P2.3). Both marked remaining in that file. Karthik's instructions for it: execute the plan
  exactly, tests first (including refusal and bypass cases), one commit at a time, stop after
  each commit with a diff summary for Karthik, log anything ambiguous or security-relevant
  under "Open questions for Karthik" instead of improvising in `safety/` or `bridge/`. After B:
  tick P2.3 in PLAN.md and mark the plan file "Implemented".
- Did this session (all committed): P1 phase review and bridge bypass audit (`c8119bf`);
  P2.2 plus audit points 1, 2, 7, 8 (`bc077f2`..`24c86d9`); P2.3 plan (`e18af09`).
- Files changed this entry: `docs/plans/P2.3.md` (status line), `docs/PROGRESS.md`.
- Tests: `uv run python -m pytest` -> 100 passed, 1 skipped (last run after `24c86d9`; no code
  changed since). In Claude Code's Bash tool run it as `rtk proxy uv run python -m pytest`;
  without `rtk proxy` collection fails with a false `No module named 'bridge'`.
- Unfinished work stopped at: an implementation request for P2.3 was interrupted before any
  file was touched. Working tree clean.
- Next concrete step: implement commit A of `docs/plans/P2.3.md`.

### 2026-11-11 — Agent: Claude Code (P2.2 + audit points 1, 2, 7, 8)

- Did, in four commits after Karthik approved the plan:
  A. `P2.1: auth covers WebSocket and checks peer address` (points 1, 2).
  B. `P2.2: policy engine` — `safety/policy.py`, `config/allowed_roots.toml`.
  C. `P2.2: single tool dispatch route through policy` (point 7) — `POST /task`, `POST /tool`.
  D. `P2.2: separate UI credential and per-route roles` (point 8).
- Files changed: `bridge/app.py`, `safety/__init__.py`, `safety/policy.py`,
  `config/allowed_roots.toml`, `tests/test_bridge.py`, `tests/test_policy.py`,
  `docs/PLAN.md`, `docs/PROGRESS.md`. No new dependencies.
- Tests: `uv run python -m pytest` -> 100 passed, 1 skipped (symlink test: no privilege on
  this account; the junction test covers the same escape). Evals not rerun; core is untouched.
- Not done: the manual check with a real uvicorn start. It would create
  `%LOCALAPPDATA%\Jarvis` (outside the repo) for the first time; left for Karthik. The same
  three cases are covered through TestClient.
- Known gaps, on purpose: no confirm queue (409 instead), no audit log, no kill switch, no
  quarantine, no real tool handlers, tasks never evicted, core not wired to the bridge,
  `C:\JarvisSandbox` not created. Path check does not cover hard links or a link swapped in
  between check and use.
- Unfinished work stopped at: nothing in progress. Tree clean after commit D.
- Next concrete step: Karthik reviews the `safety/` and `bridge/` diffs
  (`git diff c8119bf..HEAD -- safety bridge config`). Then P2.3 in plan mode.

### 2026-11-11 — Agent: Claude Code (P1 phase review + bridge bypass audit, read-only)

- Did: start-of-session protocol; P1 "Done when" review against code, tests and fresh eval
  runs; bypass audit of `safety/` and `bridge/`. No code changed. Karthik reviews before any fix.
- Runs: `uv run python -m pytest` -> 42 passed. `evals/run.py` -> 39/40, median 1.1 s, max
  4.8 s. `evals/run.py --no-router` -> 39/40, median 1.3 s, max 4.4 s. Evals with non-loopback
  connect and DNS blocked in the Python process (scratch wrapper, not in repo) -> 39/40, zero
  blocked outbound attempts. Only failure in every run: a03, the known scorer false negative.
- P1 Done-when verdicts:
  - Tool selection >= 90%: PASS. 25/25 with router and with LLM alone; args 23/23. Only the
    first tool call is scored; the set is easy.
  - All must-refuse refused: PASS. 10/10, zero tool calls, all ten replies read and decline.
    Scorer checks "no tool called" only, not wording.
  - Latency within targets: PASS, thin margin. Answers 0.5 s and 1.1 s; slowest tool command
    4.8 s against 5 s (always the first LLM call carrying tool schemas). Stub tools, model
    pre-warmed: real tool time and cold start are not measured.
  - Network off: NOT PROVEN. In-process socket guard only; does not cover Ollama's process. No
    real Wi-Fi-off run for P1. Karthik to do.
- Bypass audit. `safety/` is empty (`.gitkeep` only): no policy engine, allowed roots, taint,
  budgets or confirm queue exist. `bridge/` has only `GET /health`, so no action can run today.
  Points that are open now or open as soon as routes are added:
  1. `@app.middleware("http")` in `bridge/app.py` does not run for WebSocket routes: a
     WebSocket endpoint would skip the token and Host checks.
  2. Loopback is not enforced in code. Bind address comes only from the `--host` flag; the
     Host check reads a client header and never checks `request.client.host`. Started with
     `--host 0.0.0.0`, a LAN client sending `Host: 127.0.0.1` passes it; only the token remains.
  3. `load_token` trusts a pre-existing 64-hex `bridge.token` (fixes ACL, keeps content). No
     rotation.
  4. `protect` verifies ACEs but not file ownership; a foreign owner can re-grant access.
  5. Junction/symlink check covers only the last path component, after `mkdir(parents=True)`.
  6. The token ACL is per user, not per program: any process running as Karthik can read it.
  7. No single choke point: routes are plain FastAPI handlers, nothing forces a future tool
     route through policy, and no test asserts every route is policy-gated.
  8. If P2.3 approve/deny endpoints use the same token as tool requests, the core process (or
     anything from point 6) can approve its own T2 actions. Needs a separate UI-only credential.
  9. `%LOCALAPPDATA%\Jarvis` (token, future quarantine) and this repo's `safety/` and `config/`
     must be explicitly denied by the allowed-roots check, whatever roots are configured.
  Outside those folders: core is not wired to the bridge (eval tools are stubs);
  `core/hello_tool.py` calls `127.0.0.1:8765` with no token and should not survive into P3; the
  `tools=[...]` list passed to `ask_full` is the only thing keeping OpenJarvis's 56 built-ins
  from the model and has no dedicated test.
- Files changed: `docs/PROGRESS.md` only.
- Unfinished work stopped at: P2.2 planning was started (files read) and parked before any
  plan was written. Nothing in progress in the tree.
- Next concrete step: Karthik reviews the nine points and says which to fix and when (1, 2, 7,
  8 matter most for the P2.2 / P2.3 design). Then P2.2 in plan mode, per CLAUDE.md.

### 2026-11-11 — Agent: Codex (P2.1 ACL hardening)

- Did: resolved whoami.exe and icacls.exe through absolute SystemRoot/System32 paths;
  added Everyone SDDL alias handling so its explicit grant is removed.
- Files changed: bridge/app.py, tests/test_bridge.py, docs/PROGRESS.md.
- Tests: baseline 40 passed; full suite after changes 42 passed. New tests grant Everyone
  read on a repo-local token file and verify removal, and inject a foreign verification
  ACE to assert the not-user-only RuntimeError. No token output or production storage writes.
  Existing Starlette httpx deprecation warning remains. No new dependencies.
- Unfinished work: none for requested hardening. Next concrete step: P2.2 policy engine.


### 2026-11-11 — Agent: Codex (P2.1 complete)

- Did: implemented skeleton only: authenticated GET /health, strict loopback Host checks,
  no docs or CORS, persistent random token, hmac.compare_digest, icacls user-only ACLs.
- Dependencies: Karthik approved fastapi and uvicorn plus httpx as dev dependency;
  installed their required transitive dependencies. No pywin32. Existing venv preserved.
- Files changed: bridge/app.py, bridge/__init__.py, tests/test_bridge.py, pyproject.toml,
  uv.lock, .gitignore, AGENTS.md, docs/PLAN.md, docs/PROGRESS.md.
- Tests: uv run python -m pytest -> 40 passed. Real icacls exercised only inside
  repo-local .test-storage; production LOCALAPPDATA storage never created. Token not logged.
  One Starlette httpx deprecation warning; no extra dependency added.
- Unfinished work: none for P2.1. Next: P2.2 policy engine; no tools or policy added here.
- Start: uv run python -m uvicorn bridge.app:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log
  Use x-jarvis-token header. Never bind to other interfaces. Production startup creates
  LOCALAPPDATA/Jarvis storage; tests pass an explicit repo-local directory.


### 2026-11-11 — Agent: Codex (resume check)

- Did: verified the previous handoff, active P2 plan, clean working tree, and recent commits.
- Files changed: `docs/PROGRESS.md` only.
- Tests run + result: `uv run python -m pytest` -> 36 passed; cache access required escalation.
- Unfinished work stopped at: P2.1 remains ready for implementation; adding FastAPI and
  uvicorn still needs explicit dependency approval under AGENTS.md. No dependencies added.
- Next concrete step: obtain dependency approval, implement the P2.1 scope described in the
  preceding planning handoff, test it, and commit the task.


### 2026-11-11 — Agent: Codex (P2.1 planning)

- Did: read AGENTS.md, CLAUDE.md, the handoff, and PLAN.md; inspected git status and the
  last ten commits. Claude left a clean tree at `10da79a`; no interrupted changes to recover.
- Files changed: `docs/PROGRESS.md` only, to record this handoff.
- Tests run + result: `uv run python -m pytest` -> 36 passed. The initial sandbox attempt
  could not initialize uv's cache; access was approved and the resumed run passed.
- Unfinished work stopped at (exact point): P2.1 design prepared, awaiting Karthik's approval
  before bridge edits or adding FastAPI and uvicorn. No dependencies added or bridge code written.
- Next concrete step: approve P2.1: loopback-only FastAPI service, authenticated health route,
  strict Host validation and no CORS, persistent random token protected by a current-user-only
  Windows ACL, with refusal tests for missing/wrong tokens and unsafe hosts and ACL failures.
  Test token storage in repo-local temporary directories; production storage remains the
  planned `%LOCALAPPDATA%\Jarvis` location and is not created during this planning session.

### 2026-11-11 — Agent: Claude Code (first session: P0.1 to P1.6)

Read this entry, then Current state above, then AGENTS.md "Commands". Reasons for everything
are under Decisions; measured numbers are under Eval results.

- What this repo is now: a Python project (`uv`, Python 3.12 venv) with OpenJarvis installed
  editable from a local clone, talking to Windows Ollama (`qwen3.5:4b`). There is no bridge, no
  safety engine, no voice, no UI yet. Folders `bridge/ safety/ memory/ voice/ ui/ config/`
  hold only `.gitkeep`.
- Did, P0 (spike): repo init and layout; OpenJarvis installed project-local; connected to
  Ollama; proved a custom tool can call a `127.0.0.1` server while built-in OpenJarvis tools
  (`shell_exec`, `file_write`, ...) are refused; decided core runs natively on Windows; filled
  in Commands in AGENTS.md.
- Did, P1 (brain + evals): latency baseline; 40-case eval set with 13 stub tools; eval runner;
  system prompt; fast-path router. P1.4 closed by decision with no code. 9b comparison skipped
  by Karthik.
- Files that matter:
  - `core/config.toml` — OpenJarvis config: Ollama host, model, temperature 0, system prompt,
    analytics and update check off.
  - `core/openjarvis_env.py` — sets `OPENJARVIS_HOME` / `OPENJARVIS_CONFIG`; import it before
    anything from `openjarvis`.
  - `core/router.py` — `route(text)`: time / open app / stop without the LLM, else None.
  - `core/hello_tool.py` — P0 demo tool + live self-check. Throwaway once the bridge exists.
  - `evals/commands.yaml`, `evals/stub_tools.py`, `evals/run.py` — eval set, stubs, runner.
  - `tests/` — 36 pytest tests (eval-set shape, scoring rules, router). No model needed.
  - `.claude/settings.json` — Claude Code permission rules, placed at Karthik's request.
  - `OpenJarvis/` — upstream clone, gitignored, never edit. `.openjarvis/` — its runtime data.
- Traps on this machine (details in Decisions):
  1. Windows Smart App Control blocks unsigned `.exe`. Create the venv with the python.org
     interpreter, and run everything as `uv run python -m <module>` or `uv run python <file>`.
     `pytest.exe`, `jarvis.exe` and a `uv venv`-made `python.exe` will not start. Expect the
     same for Piper and possibly Tauri dev builds later.
  2. OpenJarvis registers 56 built-in tools, including shell and file writers. The list of
     tool names passed to `Jarvis.ask_full(..., tools=[...])` is the only allowlist. Keep it a
     constant in our code. Our tool names must not collide with built-ins (registry raises).
  3. Use the OpenJarvis Python SDK, not its CLI: the CLI also loads MCP and skill tools.
  4. Every Ollama caller must use the same `num_ctx` (16384) and send `think: false`, or the
     model reloads (about 8 s) or starts thinking (3x slower).
  5. `%USERPROFILE%\.openjarvis` is an unrelated old install. Never touch it. It gets used
     silently if `OPENJARVIS_HOME` is unset.
  6. In Claude Code's Bash tool an `rtk` wrapper can fail to spawn pytest; use PowerShell for
     `uv run python -m pytest`.
- Tests run + result (end of session): `uv run python -m pytest` -> 36 passed.
  `uv run python evals/run.py` -> 39/40 (tool selection 25/25, args 23/23, refusals 10/10,
  clarify 4/5, median 1.0 s), also with outbound sockets blocked. The one failure, a03, is a
  scorer false negative and is expected until the clarify detector changes.
- Unfinished work stopped at (exact point): nothing in progress. Working tree clean. All P0
  and P1 boxes ticked. P2 not started.
- Next concrete step: P2.1 — bridge skeleton in `bridge/`: FastAPI app bound to `127.0.0.1`
  only, random token generated on first run and stored under `%LOCALAPPDATA%\Jarvis` with a
  current-user-only ACL, every request must carry the token header. Before writing code:
  (1) enter plan mode and get Karthik's OK (CLAUDE.md rule for `bridge/`); (2) ask Karthik to
  approve adding `fastapi` and `uvicorn`; (3) run uvicorn as `uv run python -m uvicorn ...`
  because of trap 1; (4) also reject requests whose `Host` header is not `127.0.0.1:<port>`
  and send no CORS headers, so a web page cannot drive the bridge. Tests must include a
  missing-token and a wrong-token request being refused. Open questions above that P2/P3 will
  hit: whether `read_text_file` taints, the 8-call budget versus the P3 "sort a folder" check,
  who creates `C:\JarvisSandbox`, and keep-alive.

<!-- Copy this template for each session, newest on top.

### YYYY-MM-DD HH:MM — Agent: Claude Code | Codex
- Did:
- Files changed:
- Tests run + result:
- Unfinished work stopped at (exact point):
- Next concrete step:
-->
