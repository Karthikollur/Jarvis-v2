# AGENTS.md — JARVIS (local-first desktop assistant)

Shared rulebook for every coding agent on this repo: Codex, Claude Code, or anything else.
Claude Code loads it through CLAUDE.md. Read it fully before doing anything.

## What this project is

A local-first, voice-first assistant for Karthik's Windows laptop. The runtime uses no cloud
inference and no API keys.

- Agent framework: OpenJarvis
- Brain: Qwen 3.5 (default `qwen3.5:4b`) via Ollama
- Voice: openWakeWord + whisper (CPU) + Piper TTS (CPU)
- Memory: SQLite + local embeddings
- Desktop control: native Windows tool service ("bridge"), Python + FastAPI + pywinauto
- UI: Tauri 2 + React

It is NOT an operating system. It runs on top of Windows.

- Full plan, phases, task IDs: `docs/PLAN.md`
- Current state and handoff log: `docs/PROGRESS.md`

## Start-of-session protocol (every session, every agent)

1. Read this file, then `docs/PROGRESS.md` (Current state + newest log entry), then the active
   phase in `docs/PLAN.md`.
2. Run `git status` and `git log --oneline -10`.
   If there are uncommitted changes, the previous agent was cut off mid-task. Inspect the diff,
   decide whether to finish or revert it, and record that decision in PROGRESS.md first.
3. Run the test command for the active phase (see Commands below). If tests fail, fixing them is
   your first task.
4. Write one short paragraph saying what you will do this session, then start.

Never assume the repo matches what you remember. Another agent may have worked since.

## Work loop: one task at a time

- Take the next unchecked task ID in the active phase of PLAN.md (for example `P2.3`).
  Do not skip ahead and do not start a later phase.
- One task = one small, focused change = one commit.
- After each task:
  1. Run tests.
  2. Tick the checkbox in PLAN.md.
  3. Update "Current state" in PROGRESS.md.
  4. Commit with message `P2.3: <short summary>`.
- Update PROGRESS.md after EVERY task, not only at session end. Sessions can stop abruptly
  (usage limits). This rule means at most one task of context is ever lost.

## End-of-session handoff

When stopping for any reason, add a Session log entry to PROGRESS.md containing: what you did,
files changed, tests run with results, the exact point where unfinished work stopped, and the
next concrete step. Commit it. Write it for an agent that has never seen this repo.

## Hard rules

- Do not change the architecture, stack, or phase order on your own. Write a proposal under
  "Open questions for Karthik" in PROGRESS.md and continue with the current plan.
- No cloud APIs, API keys, telemetry, or outbound network calls in the runtime. It must work
  with Wi-Fi off. Localhost only.
- Every tool exposed to the model is executed by the bridge and passes through the policy
  engine in `safety/`. The model's judgement is never the permission check.
- Never weaken `safety/` to make a feature work. A new capability gets a new policy entry, at
  the strictest tier that works, with a test.
- No arbitrary shell tool for the model. Only named commands with validated parameters.
- Jarvis code never permanently deletes. Deletes and overwrites move originals to quarantine.
- Do not touch files outside this repo, except the sandbox folder defined in PLAN.md.
- Do not read, print, or commit secrets. There should be none. If you find one, stop and flag it.
- No global installs or system software. Project-local dependencies only (`uv` for Python,
  `npm` for UI). Ask before adding a dependency, and record why under Decisions in PROGRESS.md.
- Every bridge tool and every policy rule needs tests, including a test that the forbidden
  case is refused.

## Safety of the coding agent itself

- Codex: run in the sandboxed, workspace-write mode with approvals on. Never use full-access or
  approval-bypass modes on this laptop.
- Claude Code: respect `.claude/settings.json`. Never use bypass-permissions mode.
- Never edit agent permission files (`.claude/`, Codex config) unless Karthik asks.
- Anything that downloads and executes code (install scripts, installers, model pulls) must be
  approved by Karthik, not run silently.

## Commands

Keep current. Shell is PowerShell, run from the repo root.

Two machine rules first (reasons in PROGRESS.md Decisions, 2026-11-11):

- Windows Smart App Control blocks unsigned `.exe` files, including the `python.exe` that
  `uv venv` creates and every script launcher in `.venv\Scripts` (`jarvis.exe`, `pytest.exe`).
  So the venv must be created by the signed python.org interpreter, and tools are always run
  as `uv run python -m <module>` or `uv run python <file>`, never by `.exe` name. Do not turn
  Smart App Control off.
- `uv sync` needs the upstream clone at `OpenJarvis/` (gitignored workspace member, commit
  `e6b7137`). If it is missing: `git clone https://github.com/open-jarvis/OpenJarvis.git`
  (a download: ask Karthik first).

Commands:

- Python env, first time or after deleting `.venv`:
  `& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv; uv sync`
- Python env, afterwards: `uv sync`
- Check Ollama and models: `ollama list` (needs `qwen3.5:4b`)
- Tests: `uv run python -m pytest` (only `tests/`; fast, no model needed)
- Live smoke test: `uv run python core/hello_tool.py` — must print `OK`; needs Ollama running
- Evals (from P1): `uv run python evals/run.py`
- OpenJarvis CLI, for debugging only (core uses the Python SDK):
  `$env:OPENJARVIS_HOME = "$PWD\.openjarvis"; $env:OPENJARVIS_CONFIG = "$PWD\core\config.toml"; uv run python -m openjarvis.cli ask --no-stream "hi"`
- Bridge (dev): `TBD in P2`
- UI (dev, from P6): `cd ui && npm run dev`

## Repo map

```
AGENTS.md / CLAUDE.md   agent rules
docs/PLAN.md            phases, tasks, acceptance checks
docs/PROGRESS.md        current state, decisions, session log
core/                   OpenJarvis config, prompts, tool registration
OpenJarvis/             upstream source clone (gitignored, read-only reference, installed editable)
.openjarvis/            OpenJarvis runtime data (gitignored)
bridge/                 native Windows tool service (127.0.0.1 only, token auth)
safety/                 policy engine: tiers, allowed roots, taint, budgets, confirm queue, audit, quarantine
memory/                 SQLite schema, ingestion, retrieval, approval queue
voice/                  wake word, STT, TTS, push-to-talk
ui/                     Tauri 2 + React desktop app
config/                 allowed_roots.toml, apps.toml, scripts.toml
evals/                  command and document eval sets + runner
tests/                  unit and integration tests
```
