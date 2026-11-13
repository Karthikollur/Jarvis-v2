# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- Active phase: P3 (Windows control tools). P3.1 done 2026-11-13; P3.1b planned, then P3.2 (neither started). P0 and P1 are complete, every task ticked in PLAN.md.
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
- Uncommitted work: none. `.claude/settings.local.json` (local agent permissions) is gitignored and left untouched.
- Blockers: none
- Run OpenJarvis with (PowerShell, from repo root; both env vars required):
  `$env:OPENJARVIS_HOME = "$PWD\.openjarvis"; $env:OPENJARVIS_CONFIG = "$PWD\core\config.toml"; uv run python -m openjarvis.cli ask --no-stream "hi"`

## Open questions for Karthik

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
- P3 "Done when" (sort a folder by file type) needs one `move_file` per file, which exceeds the
  8-tool-call budget for more than a few files. Batch move tool, or change the check?
- (Resolved in P2.6: the repo sits inside the Obsidian vault, and the whole repo folder is now
  a protected folder, so a vault docs root in P4.2 can never reach `safety/`, `config/` or
  any other repo file.)
- `C:\JarvisSandbox` does not exist yet. Create it in P2/P3, or should Karthik create it?

## Decisions

Format: `YYYY-MM-DD — decision — reason — who`

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

## Session log

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
