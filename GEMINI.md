@./AGENTS.md

## Gemini CLI specifics

- `/tutorial <project> [brief]` starts the pipeline (`.gemini/commands/tutorial.toml`).
- Skills are read from `.agents/skills/` (copies of `pipeline/skills/`); sub-agents
  (system-analyst, writer, director) from `.gemini/agents/`. Sub-agents need
  `"experimental": {"enableAgents": true}` in `.gemini/settings.json`; `install_agent.py` sets it.
  Without them, play each role yourself by reading `pipeline/agents/<role>.md`.
- If anything is missing, run `.venv\Scripts\python.exe scripts\install_agent.py --agent gemini`.
