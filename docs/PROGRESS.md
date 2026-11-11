# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- Active phase: P2 (not started). P0 and P1 are complete, every task ticked in PLAN.md.
- Phase gate P0: PASSED 2026-11-11. Karthik reported `OK` with Wi-Fi off. Separately, Claude
  Code ran `core/hello_tool.py` with every non-loopback socket connect and DNS lookup blocked
  inside the Python process: `OK`, zero outbound attempts. Limit of that second check: it
  covers the Python process only, not Ollama's own process.
- Phase gate P1: PASSED 2026-11-11, closed by Karthik. Tool selection 25/25 (need >= 90%),
  must-refuse 10/10, median latency 1.0 s (targets 3 s / 5 s), and the full eval run repeated
  with non-loopback sockets and DNS blocked in the Python process: same 39/40, zero outbound
  attempts. Not done with real Wi-Fi off by Karthik for P1. 9b comparison skipped by Karthik.
- Last completed task: P1.6
- Next task: P2.1. It touches `bridge/`, so CLAUDE.md requires plan mode and Karthik's OK
  before editing. It also needs new dependencies (FastAPI, uvicorn): ask first.
- Tests: `uv run python -m pytest` -> 36 passed (2026-11-11). Evals:
  `uv run python evals/run.py` -> 39/40 (needs Ollama, takes about 1 minute). Live smoke test:
  `uv run python core/hello_tool.py` must print `OK` (needs Ollama running)
- Uncommitted work: none
- Blockers: none
- Run OpenJarvis with (PowerShell, from repo root; both env vars required):
  `$env:OPENJARVIS_HOME = "$PWD\.openjarvis"; $env:OPENJARVIS_CONFIG = "$PWD\core\config.toml"; uv run python -m openjarvis.cli ask --no-stream "hi"`

## Open questions for Karthik

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
- Does `read_text_file` on a sandbox file taint the task? Plan lists only web, ingested docs,
  clipboard.
- The repo sits inside the Obsidian vault. P4.2 proposes the vault as a read-only docs root,
  which would include this repo's own `safety/` and `config/`. Exclude the repo folder, or move it?
- `C:\JarvisSandbox` does not exist yet. Create it in P2/P3, or should Karthik create it?

## Decisions

Format: `YYYY-MM-DD — decision — reason — who`

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
