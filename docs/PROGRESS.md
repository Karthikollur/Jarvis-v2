# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- Active phase: P0
- Last completed task: P0.6 (all P0 tasks ticked)
- Phase gate: P0 "Done when" NOT yet passed. Karthik must turn Wi-Fi off and run
  `uv run python core/hello_tool.py`; it must print `OK`. Record the result here.
- Next task: P1.1, only after the gate above is recorded as passed
- Tests: no pytest yet (adding a dependency needs Karthik's OK). One self-check exists:
  `uv run python core/hello_tool.py` must print `OK` (needs Ollama running)
- Uncommitted work: none
- Blockers: none
- Run OpenJarvis with (PowerShell, from repo root; both env vars required):
  `$env:OPENJARVIS_HOME = "$PWD\.openjarvis"; $env:OPENJARVIS_CONFIG = "$PWD\core\config.toml"; uv run python -m openjarvis.cli ask --no-stream "hi"`

## Open questions for Karthik

- Latency (measured in P0.3, `qwen3.5:4b`, 100% GPU, "reply pong"): cold 90 s, warm 16 s through
  the OpenJarvis CLI, 10 s direct to Ollama, 4 s is bare CLI start-up. The model thinks before
  answering (104 tokens generated for a one-word reply) and Ollama loads it with a 16384 context.
  The 3 s target needs, in P1: thinking off, smaller context, model kept loaded, and core as a
  long-running process instead of a CLI call per request. Not fixed yet.
- OpenJarvis logs `Failed to set up rate limiter: No module named 'openjarvis_rust'` on every
  call. The Rust extension is not installed (needs a Rust toolchain = system install). Harmless
  so far; some features (its memory commands) need it. We do not plan to use those.

- An older OpenJarvis install exists at `%USERPROFILE%\.openjarvis` (created 2026-09-19, has
  `config.toml`, memory and agent DBs). Not touched. If `OPENJARVIS_HOME` is ever unset, this
  repo's OpenJarvis will silently use that folder and its config. Keep, or remove it yourself?
- OpenJarvis core dependencies include `posthog`, `python-telegram-bot`, `ddgs`, `openai`,
  `datasets`. They cannot be dropped without forking. Offline check must prove none of them
  connect out.
- OpenJarvis ships built-in tools that bypass the bridge (`shell_exec`, `file_write`,
  `apply_patch`, `browser`, `web_search`, `http_request`, `channel_tools`) and a CodeAct agent
  that runs model-written Python. Proposal: add to P0.4 a check that only our tool is callable
  (`[agent] tools = "..."`), and never select the CodeAct agent.
- OpenJarvis has `posthog` as a core dependency (analytics default off) and a local telemetry DB
  (default on). No documented offline mode. The Wi-Fi-off check in P0 is a real gate.
- OpenJarvis already ships SQLite memory, faster-whisper STT, Kokoro TTS and a Tauri app. Reuse
  any of these, or build our own as planned? Its memory has no approval queue.
- `.claude/settings.json` is not in place; the file is still at `files/settings.json` (gitignored).
  Agents may not touch `.claude/` unasked. Karthik: move it yourself or say so explicitly. Note
  its rules are `Bash(...)` only and likely do not cover the PowerShell tool.
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
- 2026-11-11 — No dependencies added in P0.1, not even pytest — rule: ask before adding — Claude Code
- 2026-11-11 — PLAN.md + PROGRESS.md are the only planning files; no separate task_plan.md —
  avoid two sources of truth — Claude Code (Karthik can overrule)

## Eval results

Format: `YYYY-MM-DD — model — tool selection % — refusals — median latency`

- (none yet)

## Session log

### 2026-11-11 — Agent: Claude Code
- Did: P0.1. `git init` (branch `main`), moved starter docs from `files/` to root and `docs/`,
  created folder layout with `.gitkeep` files, minimal `pyproject.toml`, `.gitignore`. Cloned
  upstream OpenJarvis to `OpenJarvis/` (full history, gitignored). Reviewed plan against the
  machine and OpenJarvis docs; findings are under Open questions.
- Machine facts: RTX 3050 6 GB; Ollama 0.40.16 with `qwen3.5:4b`, `9b`, `2b` already pulled;
  git, uv, Node 24, WSL2 Ubuntu present.
- Files changed: `AGENTS.md`, `CLAUDE.md`, `docs/PLAN.md`, `docs/PROGRESS.md`, `pyproject.toml`,
  `uv.lock`, `.gitignore`, `.gitkeep` in each layout folder.
- P0.2: installed OpenJarvis into `.venv` (see Decisions for steps and the Smart App Control
  workaround). `uv run python -m openjarvis.cli --version` prints `1.0.5.dev180+ge6b71376`;
  config/data/cache paths resolve under `<repo>\.openjarvis`. Only `--version` has been run;
  no `jarvis init`, no model calls yet.
- P0.3: wrote `core/config.toml`; `ask --no-stream "Reply with exactly: pong"` returned `pong`
  from `qwen3.5:4b` on Windows Ollama (`ollama ps`: 100% GPU). Wi-Fi-off run not done yet; that
  is the P0 "Done when" check.
- P0.4: `core/hello_tool.py` = custom tool `hello_bridge` + self-check. The check starts a dummy
  server on `127.0.0.1:8765` that returns a random code, asks the model to greet Karthik, and
  asserts: only `hello_bridge` was used, the server was hit, the code came back, and
  `shell_exec` / `file_write` / `http_request` / `apply_patch` are refused as `Unknown tool`.
  Result: `OK` in 16 s (warm model).
- Tests run + result: `uv run python core/hello_tool.py` -> OK.
- Unfinished work stopped at (exact point): nothing in progress.
- P0.5: placement decision recorded (native Windows). P0.6: Commands and repo map in AGENTS.md
  filled in.
- Next concrete step: get the Wi-Fi-off result from Karthik and record it under Current state.
  If it fails, find which call went out (candidates: PyPI update check, PostHog, HuggingFace
  via `datasets`) and fix before P1. Then P1.1 (`qwen3.5:4b` is already pulled, so it is
  config only). Before P1.2, ask Karthik to approve adding pytest and resolve the latency
  open question (thinking off, context size, keep-alive).

<!-- Copy this template for each session, newest on top.

### YYYY-MM-DD HH:MM — Agent: Claude Code | Codex
- Did:
- Files changed:
- Tests run + result:
- Unfinished work stopped at (exact point):
- Next concrete step:
-->
