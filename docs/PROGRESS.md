# PROGRESS — shared handoff log

Updated by whichever agent is working (Claude Code or Codex) after EVERY task.
Newest session entry goes at the top of the Session log.

## Current state

- Active phase: P0
- Last completed task: P0.1
- Next task: P0.2
- Tests: not set up yet (pytest not added; adding a dependency needs Karthik's OK)
- Uncommitted work: none
- Blockers: P0.2 needs Karthik to approve the install method (see Open questions)

## Open questions for Karthik

- P0.2 install method. Upstream's Windows installer (`irm .../install.ps1 | iex`) downloads and
  runs code and installs outside the repo, which breaks "no global installs". Proposal: install
  project-locally with `uv` (pinned version, or editable from the `OpenJarvis/` clone) and set
  `OPENJARVIS_HOME` inside the repo. Untested on Windows.
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
- Tests run + result: none exist. `uv sync` succeeds.
- Unfinished work stopped at (exact point): nothing in progress.
- Next concrete step: P0.2, after Karthik approves the install method. Before that, read
  `OpenJarvis/src` for how tools are registered and restricted (read-only, no approval needed).

<!-- Copy this template for each session, newest on top.

### YYYY-MM-DD HH:MM — Agent: Claude Code | Codex
- Did:
- Files changed:
- Tests run + result:
- Unfinished work stopped at (exact point):
- Next concrete step:
-->
