# CODEX_TASK — handoff from Claude Code, 2026-11-16

Read `AGENTS.md` first (shared rulebook), then `docs/PROGRESS.md` (Current state + newest
Session log entry). This file only says where the last session stopped.

## Goal

Draft plans for every remaining phase exist in `docs/plans/` so later sessions can execute
them after Karthik approves each one. "Done" for that goal: six plan files committed and
pushed, PLAN.md pointing at them, PROGRESS.md logged. That is done. No code was to be
written and none was.

## Done so far

- `docs/plans/P3.6.md` — task lifecycle, step-level (evict, `POST /end`, core ends its task).
- `docs/plans/P4.md` — memory and documents, phase plan, sections A to G.
- `docs/plans/P5.md` — voice, design level.
- `docs/plans/P6.md` — desktop UI, design level.
- `docs/plans/P7.md` — workflows, decisions and risks.
- `docs/plans/P8.md` — hardening, decisions and risks.
- `docs/PLAN.md` — one pointer line per phase. No task, order or checkbox changed.
- `docs/PROGRESS.md` — Session log entry "plans written ahead: P3.6 to P8", six new Open
  questions, one line in Current state.
- Commits: `918096f`, `4dcac80`, `9e29aa9`, pushed to `origin/main`.

## Current state

- Builds: nothing to build. Tests: `uv run python -m pytest` -> 619 passed, 4 skipped
  (2026-11-16, before the docs commits; no code changed since). Nothing is broken.
- Active task in PLAN.md: P3.5b, unticked, waiting for Karthik's manual check
  (`docs/plans/P3.5b.md`, "Manual check"). An agent cannot do it: it needs his approvals.
- Every plan from this session is DRAFT and NOT approved.

## Remaining steps

There is no agent work pending. Do not start implementing any draft plan.

1. Wait for Karthik's P3.5b manual check result. Done? yes/no: P3.5b is ticked in
   `docs/PLAN.md` and the result is in the Session log.
2. When Karthik has answered D1 to D3 in `docs/plans/P3.6.md` and approved it: run its
   "Verify before executing" list, then implement section A only, showing a pre-edit
   summary first (it touches `bridge/`). Done? yes/no: commit `P3.6: evict tasks` exists,
   tests green, mutant table in the Session log.
3. Sections B and C of P3.6 the same way, one commit each, a go per commit. Done? yes/no:
   P3.6 ticked in PLAN.md after Karthik's manual check.
4. Later phases: each plan's own "Verify before executing" comes first; P4 sections D to
   G and all of P5 to P8 need a step-level plan approved by Karthik before any code.

## Key files

- `AGENTS.md` — rules, commands, repo map. `CLAUDE.md` imports it.
- `docs/PLAN.md` — phases, task IDs, "Done when" per phase.
- `docs/PROGRESS.md` — current state, open questions, decisions, eval results, session log.
- `docs/plans/*.md` — one plan per task or phase; older ones show the house format.
- `safety/policy.py` — policy engine (tiers, roots, taint, budgets). `safety/confirm.py`,
  `audit.py`, `undo.py`.
- `bridge/app.py` — FastAPI bridge, routes, auth, stop latch. `bridge/tools.py` — handlers.
- `core/agent.py`, `core/tools.py`, `core/bridge_client.py`, `core/config.toml` (prompt).
- `evals/run.py`, `evals/commands.yaml`, `evals/stub_tools.py`.

## Commands (PowerShell, repo root)

- Install: `uv sync` (first time: see AGENTS.md "Commands"; the venv must come from the
  signed python.org interpreter).
- Tests: `uv run python -m pytest`
- Evals: `uv run python evals/run.py` (needs Ollama running with `qwen3.5:4b`)
- Bridge (dev): `uv run python -m uvicorn bridge.app:create_app --factory --host 127.0.0.1 --port 8765 --no-access-log`
- One request: `uv run python -m core "What time is it?"`
- No build step yet (no `ui/`).

## Decisions, gotchas, do not change

- Never run tools by `.exe` name (Smart App Control). Always `uv run python -m <module>`.
- Do not change phase order, stack or architecture. Proposals go under "Open questions
  for Karthik" in PROGRESS.md.
- Plan mode / Karthik's OK before any edit in `safety/`, `bridge/` permissions, `config/`.
- Never weaken `safety/` to make a feature work. No new dependency, download or model pull
  without Karthik's yes.
- The drafts contain unchecked facts, each marked in its "Verify before executing"
  section (Ollama `/api/embed` shape, embedding model names, voice library behaviour,
  whether a Tauri binary starts under Smart App Control). Check before relying on them.
- Repo decision 2026-11-11: PLAN.md and PROGRESS.md are the planning files. This
  CODEX_TASK.md exists only because Karthik's handoff rule asks for it; keep PROGRESS.md
  the source of truth and delete this file when it no longer says anything new (ask first).
