# CLAUDE.md

@AGENTS.md

The line above imports the shared rulebook. If it did not load, read `AGENTS.md` now. It is
mandatory, and it is the same rulebook Codex follows, so both agents can hand work to each other.

## Claude Code specifics

- Use plan mode for any task touching `safety/`, `bridge/` permissions, or `config/`.
  Show the plan and wait for Karthik's OK before editing.
- Subagents only for read-only exploration (reading OpenJarvis docs or source). Code changes
  happen in the main session, one task at a time.
- You cannot see how much of your usage window is left. That is why the after-every-task
  PROGRESS.md update and commit in AGENTS.md is not optional.
- If Karthik says "wrap up" or "handoff", write the Session log entry and commit immediately.
- Codex may have worked since your last session. Always run the start-of-session protocol.
