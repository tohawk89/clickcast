@AGENTS.md

## Claude Code specifics

- `/tutorial <project> [brief]` starts the pipeline (`.claude/commands/tutorial.md`).
- The System Analyst, Writer and Director are sub-agents in `.claude/agents/`; call them with the
  Agent tool. You are the Producer: only you talk to the user and collect the two approvals
  (use AskUserQuestion for the intake and for each gate).
- Skills are in `.claude/skills/` (copies of `pipeline/skills/`). If they're missing or stale,
  run `.venv\Scripts\python.exe scripts\install_agent.py --agent claude`.
- To look at the app yourself, use the built-in browser or Claude in Chrome; to film it, always
  use `scripts/capture.py` (it is what makes the video sharp and repeatable).
- The `/hyperframes` skills can make richer title/end cards: render them into the project's
  `assets/` and reference them from the shotlist (`pipeline/skills/directing/reference.md`).
