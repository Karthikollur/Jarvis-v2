# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- Active phase: P0
- Active phase is now P1.
- Phase gate P0: PASSED 2026-11-11. Karthik reported `OK` with Wi-Fi off. Separately, Claude
  Code ran `core/hello_tool.py` with every non-loopback socket connect and DNS lookup blocked
  inside the Python process: `OK`, zero outbound attempts. Limit of that second check: it
  covers the Python process only, not Ollama's own process.
- Last completed task: P1.4 (closed without code)
- Next task: P1.5
- Tests: `uv run python -m pytest` -> 12 passed (2026-11-11). Evals:
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
- P0 gate passed and recorded; `.claude/settings.json` put in place at Karthik's request.
- P1.1: measured latency (numbers in Decisions). No code or config change was needed.
- P1.2: `evals/commands.yaml`, `evals/stub_tools.py`, `core/openjarvis_env.py`,
  `tests/test_eval_set.py` (5 tests: counts, unique ids, args fit schemas, every stub used,
  stubs register and record). Nothing has been run against the model yet.
- P1.3: `evals/run.py` (runner + `score`), `tests/test_eval_scoring.py` (7 tests), system
  prompt and temperature in `core/config.toml`. First run: 39/40, see Eval results.
- Tests run + result: `uv run python -m pytest` -> 12 passed. `uv run python evals/run.py` ->
  39/40.
- P1.4: closed by decision, no code (see Decisions).
- Next concrete step: P1.5, deterministic fast-path router before the LLM for the most common
  commands (open app, time, stop). Suggested shape: one pure function in `core/`, e.g.
  `route(text) -> (tool_name, args) | None`, exact/regex matches only ("open <app in APPS>",
  "what time is it", "stop"), returning None for anything else so the LLM handles it. It must
  only ever return tools from the same allowlist the LLM gets, and its output goes through the
  bridge/policy like any other tool call. Test with pytest, including near-misses that must
  NOT match ("open the pod bay doors", "stop the dev server script"). Then P1.6: record
  baseline, optional `uv run python evals/run.py --model qwen3.5:9b`, and look into the two
  latency outliers (t01, t03).

<!-- Copy this template for each session, newest on top.

### YYYY-MM-DD HH:MM — Agent: Claude Code | Codex
- Did:
- Files changed:
- Tests run + result:
- Unfinished work stopped at (exact point):
- Next concrete step:
-->
