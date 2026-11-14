# JARVIS — Implementation Plan

## 1. Goal and scope

**Goal:** a voice-first assistant on Karthik's Windows laptop that answers questions, controls
apps and files within strict limits, remembers approved facts, and searches local documents.
Fully offline at runtime.

**Non-goals for v1**

- A custom operating system. Jarvis runs on Windows.
- Cloud inference or API keys at runtime.
- Unsupervised long-horizon autonomy. A 4B local model cannot do it reliably. v1 runs short,
  supervised workflows of at most 8 tool calls.
- Many specialised agents. v1 is one agent with many tools.
- Sending email or messages, payments, software installs, registry edits.

## 2. Hardware budget

Machine: Windows laptop, NVIDIA RTX 3050 with 6 GB VRAM.

| Component | Choice | Where it runs |
|---|---|---|
| LLM | `qwen3.5:4b` (~3.4 GB) default | GPU |
| LLM (optional) | `qwen3.5:9b` (~6.6 GB) only if evals demand it; will partly spill to CPU | GPU + CPU |
| Speech to text | whisper base/small | CPU |
| Text to speech | Piper | CPU |
| Embeddings | small local embedding model via Ollama | CPU is fine |

Latency targets: simple spoken answer starts within 3 s; single tool command finishes within 5 s.

## 3. Architecture

```
 You (voice / keyboard / UI)
        |
   voice/  ui/  ----------------------------+
        |                                   |  confirmations, Stop
   core/  OpenJarvis agent + Qwen (Ollama)  |
        |  tool requests (HTTP, token)      |
   bridge/  native Windows service  <-------+
        |  every request checked by safety/ policy engine
   Windows: apps, windows, files      memory/: SQLite + embeddings
```

Safety is enforced inside the bridge and on the memory write path, at the point of execution.
Never in the prompt.

**Processes**

- `ollama` — Windows native (already installed).
- `core` — OpenJarvis agent. Runs natively on Windows (decided in P0.5).
- `bridge` — Python FastAPI service on Windows, bound to `127.0.0.1` only, requires a random
  per-install token header. Uses pywinauto / pywin32. Hosts the policy engine.
- `voice` — Python process: openWakeWord, whisper, Piper.
- `ui` — Tauri 2 + React. Shows live steps, T2 confirmations, audit log, memory manager, Stop.

**Sandbox folder:** `C:\JarvisSandbox`. The only allowed file root in v1. Karthik alone can add
roots in `config/allowed_roots.toml`.

## 4. Security model

### 4.1 Tool tiers

| Tier | Meaning | Examples | Gate |
|---|---|---|---|
| T0 | Read-only | list windows, system stats, list/read files in allowed roots, memory search | Automatic |
| T1 | Local and reversible | open allowlisted app, focus window, create folder, move/rename inside roots | Automatic, logged with undo record |
| T2 | Destructive, outbound, or code-running | delete (to quarantine), overwrite, run named script, browser click/submit | Confirm by click or keyboard in UI |
| T3 | Forbidden in v1 | arbitrary shell, registry, credentials, payments, sending messages, paths outside roots, system folders | Not implemented as tools |

Voice "yes" never approves T2. Audio from a video or call could say "confirm".

### 4.2 Runtime rules

- **Allowed roots.** File tools resolve paths fully (`..`, absolute paths, symlinks, junctions,
  UNC paths) before checking they sit inside an allowed root.
- **Taint.** Once a task reads untrusted content (web page, ingested document, clipboard),
  every T1 action in that task becomes T2 for the rest of the task. Untrusted text reaches the
  model inside clearly marked data blocks and is never treated as instructions.
- **Budgets.** Max 8 tool calls and 120 s per task; max 3 retries per failing tool. Breaching any
  budget stops the task and reports what happened.
- **Kill switch.** Global hotkey (default `Ctrl+Alt+End`, configurable) and a tray/UI Stop button
  cancel the running task and clear the confirm queue.
- **Audit log.** Append-only JSONL of every tool request, policy decision, and result.
- **Quarantine and undo.** Deletes and overwrites move originals to
  `%LOCALAPPDATA%\Jarvis\quarantine` with metadata so they can be restored.
- **Bridge network.** `127.0.0.1` only, token required, no firewall rule opened. Token stored in
  `%LOCALAPPDATA%\Jarvis` readable by the current user only.
- **Memory writes.** Facts the model proposes go to a pending queue. Only Karthik-approved facts
  become memory. View, edit, delete supported.
- **Offline check.** A test asserts runtime modules open no outbound connections except localhost.

### 4.3 Dev-time security (while agents build this)

- The repo lives in its own folder. Agents start from the repo root only.
- One commit per task. Karthik reviews diffs in `safety/` and `bridge/` before each phase closes.
- Claude Code uses `.claude/settings.json` allow/ask/deny lists and never bypass mode.
  Codex runs sandboxed with approvals.
- Deny lists are speed bumps, not walls; shell variants can slip past them. Real protection is
  approvals + small diffs + review.
- Create a Windows restore point (or full backup) before P3, the first phase where code controls
  the desktop.
- Optional but recommended from P3: test under a separate standard (non-admin) Windows user.

## 5. Phases

Do not start a phase until the previous phase's "Done when" passes and is recorded in PROGRESS.md.

### P0 — Spike and decisions (~1 day)

- [x] P0.1 Initialise repo: folder layout from AGENTS.md, `uv` project, `.gitignore`, docs in place.
- [x] P0.2 Install OpenJarvis following its current Windows docs (WSL2 or desktop build). Record
      exact steps in PROGRESS.md Decisions.
- [x] P0.3 Connect OpenJarvis to the existing Windows Ollama. If core runs in WSL2, confirm it can
      reach Windows Ollama and a dummy HTTP server on Windows localhost.
- [x] P0.4 From OpenJarvis docs/source, find how to register a custom tool that calls an HTTP
      endpoint. Build a hello-world tool.
- [x] P0.5 Decide core placement (WSL2 vs native). Record decision and reason.
- [x] P0.6 Fill in the Commands section of AGENTS.md.

**Done when:** a typed request in OpenJarvis triggers the custom tool, which hits a Windows
localhost server, with Wi-Fi off.

### P1 — Offline brain + eval harness (~2–3 days)

- [x] P1.1 Pull `qwen3.5:4b`; set as default model.
- [x] P1.2 `evals/commands.yaml`: 40 typed commands with expected tool + arguments, including
      10 that must be refused and 5 ambiguous ones that must trigger a clarifying question.
      Use stub tools. (41 since P3.2 F1: case t24 for `move_files`, decided by Karthik.)
      (42 since P3.4: case t25 for `open_in_app`.)
- [x] P1.3 `evals/run.py`: reports tool-selection accuracy, argument accuracy, refusal correctness,
      median latency.
- [x] P1.4 Use Ollama structured output (JSON schema) for tool calls where OpenJarvis allows it.
      (Satisfied by native function calling; no code. See PROGRESS.md Decisions 2026-11-11.)
- [x] P1.5 Deterministic fast-path router for the most common commands (open app, time, stop)
      before the LLM.
- [x] P1.6 Record 4B baseline in PROGRESS.md. Optionally compare 9B. (9B skipped by Karthik.)

**Done when:** at least 90% correct tool selection, all must-refuse cases refused, latency within
targets, network off.

### P2 — Safety core + bridge skeleton (~3–4 days)

- [x] P2.1 `bridge/`: FastAPI on `127.0.0.1`, token generated on first run, user-only file ACL.
- [x] P2.2 `safety/policy.py`: tier table, allowed-roots check with full path resolution, per-task
      taint flag, budgets.
- [x] P2.3 Confirm queue: pending T2 actions, approve/deny endpoints.
- [x] P2.4 Audit log (JSONL).
- [x] P2.5 Kill switch endpoint + global hotkey listener.
- [x] P2.6 Quarantine + undo records. Includes audit point 9 (PROGRESS.md, P1 review): the
      allowed-roots check refuses `%LOCALAPPDATA%\Jarvis` (tokens, audit log, quarantine) and
      this whole repo folder (Karthik, 2026-11-11), whatever roots are configured, with tests.
- [x] P2.7 Tests: path traversal (`..\`, absolute, junction, UNC), missing/wrong token, budget
      breach, tainted T1 upgraded to T2, kill switch mid-task, concurrent calls cannot exceed a
      budget (`Policy`/`Task` need a lock).
- [x] P2.8 Hardening from the P2 phase review (N1–N6, kill-switch liveness, audit encoding,
      built-in tools guard; absorbs the former P3.0a and P3.0b). Plan: `docs/plans/P2.8.md`.
- [x] P2.9 Fixes from the P2.8 review (R1–R7: taint fails closed, `move_file` landing place,
      odd names and results, stop race). Plan: `docs/plans/P2.9.md`. Commits A–C must land
      before any P3.2 or P3.3 handler; P3.1 may start after the restore point.

**Done when:** all tests pass; a fake tool cannot act outside the sandbox or without a token by
any tested route. Karthik has reviewed the diff.

### P3 — Windows control tools (~1 week)

Before starting: restore point created; P2 reviewed; P2.8 done and reviewed by Karthik. P3 cannot start until audit point 9
(see P2.6) is done and tested.

- [x] P3.1 T0 tools: `list_windows`, `system_stats` (CPU, RAM, GPU, VRAM), `list_dir`,
      `read_text_file` (size cap).
- [x] P3.1b Review gaps G1 to G3: `/outcome` survives a lone surrogate; `read_text_file`
      refuses a hard link; built-in tools guard scans subfolders and refuses `**` in calls.
      Plan: `docs/plans/P3.1b.md`.
- [x] P3.2 T1 tools: `open_app` (allowlist in `config/apps.toml`), `focus_window`, `create_folder`,
      `move_file`, `rename_file`, all with undo records. One batch confirmation for a
      multi-file move on a tainted task (P2.8: `list_dir` taints).
- [x] P3.2b `focus_window` gets the foreground: attach to the foreground thread when Windows
      refuses, skip a hung window, always detach, and count success only from
      `GetForegroundWindow`. Plan: `docs/plans/P3.2b.md`.
- [x] P3.2c `focus_window` waits for the activation: after each focus call, poll
      `GetForegroundWindow` for up to 250 ms. Plan: `docs/plans/P3.2c.md`.
- [x] P3.2d `focus_window` lands through minimise and restore when the plain call does
      not, and the attach route is removed. Plan: `docs/plans/P3.2d.md`.
- [x] P3.3 T2 tools: `delete_file` (to quarantine), `run_named_script` (only entries in
      `config/scripts.toml`). Plan: `docs/plans/P3.3.md`.
- [ ] P3.4 Prefer CLIs and app APIs (e.g. `code <path>`) over UI clicking; pywinauto only where needed.
- [ ] P3.5 Register tools in core; rerun evals against real tools in the sandbox. The core
      opens exactly one task per user request and sends `fresh_context` only when it has
      dropped the model's context (also after a bridge restart); tests for both.
      Runtime tools guard (P3.1b review): one `BridgeTool` class in `core/`; before every
      request the agent's real tool set must equal `TOOLS` by name and be exactly
      `BridgeTool` by type, else refuse. Tests include the refused case.
- [ ] P3.6 Task lifecycle: end/expire tasks; evict finished tasks and outcomes from the bridge
      (history stays in the audit log).

**Done when:** "Open VS Code on my sandbox project and sort the test downloads folder by file
type" completes, every step appears in the audit log, and undo restores the folder.

### P4 — Memory and local documents (~1 week)

- [ ] P4.1 SQLite schema: `facts`, `pending_facts`, `task_history`, `documents`, `chunks`.
- [ ] P4.2 Local embedding pipeline; ingest PDF/MD/TXT from a read-only docs root
      (for example the Obsidian vault, once Karthik adds it to allowed roots as read-only).
- [ ] P4.3 Retrieval tool returning answers with citations (file + chunk).
- [ ] P4.4 Pending-fact approval flow; CLI to review, edit, delete memory.
- [ ] P4.5 Ingested text marked untrusted (taint applies).
- [ ] P4.6 Doc eval: 20 questions over test documents.

**Done when:** at least 80% correct answers with correct citation; nothing enters `facts` without
approval.

### P5 — Voice (~1 week)

- [ ] P5.1 Push-to-talk hotkey -> STT (CPU) -> core -> Piper TTS (CPU).
- [ ] P5.2 Streaming TTS: speak the first sentence while the rest generates.
- [ ] P5.3 Barge-in: speaking or the hotkey interrupts TTS.
- [ ] P5.4 Wake word via openWakeWord, off by default; visible mic indicator whenever listening.
- [ ] P5.5 Test that voice cannot approve T2.

**Done when:** "Jarvis, what's in my sandbox folder?" gets a spoken answer within targets, 10 runs
in a row.

### P6 — Desktop UI (~1 week)

- [ ] P6.1 Tauri 2 + React shell: floating panel + tray icon.
- [ ] P6.2 Voice state animation, live task steps.
- [ ] P6.3 T2 confirmation dialogs (only approval path).
- [ ] P6.4 Audit log view, memory manager, hardware monitor.
- [ ] P6.5 Big Stop button wired to kill switch.

**Done when:** every T2 action can only be approved through the UI; Stop cancels a running task
within 1 s.

### P7 — Supervised workflows (ongoing)

- [ ] P7.1 Plan -> execute -> verify loop inside budgets.
- [ ] P7.2 Named recipes, e.g. "start dev session": open VS Code on project X, run its named dev
      script, open localhost in the browser.
- [ ] P7.3 Browser via Playwright: read-only first; any click/submit is T2; page text is tainted.

**Done when:** 3 recipes pass 10/10 runs each.

### P8 — Hardening and always-on

- [ ] P8.1 Start at logon via Task Scheduler as the normal user (not admin); crash restart.
- [ ] P8.2 Log rotation, resource caps.
- [ ] P8.3 Script that runs all tests + evals before any phase is closed.
- [ ] P8.4 Prompt-injection red-team tests: malicious text in a document or web page asking Jarvis
      to delete or move files.

**Done when:** one week of daily use with zero unconfirmed T2 actions in the audit log.

## 6. Later, not v1

Bigger GPU and 9B+ model; more allowed roots and apps; optional cloud fallback for hard tasks
(breaks the offline rule; Karthik decides).

Per-task cap on total files moved is required before any allowed root beyond
`C:\JarvisSandbox` is added (Karthik, 2026-11-13; `move_files` caps one batch at 20, but a
task may make several calls).
