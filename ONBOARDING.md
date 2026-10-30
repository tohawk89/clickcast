# Onboarding — for the AI agent setting this up

You are an AI coding agent (Claude Code, Gemini CLI, Codex, Cursor, Copilot, Aider, or another)
opened in this folder for the first time, or asked to "set up the tutorial pipeline". Do these
steps in order, then report to the user in a few lines what you did and what (if anything) they
must do themselves. Don't skip the checks: a later step depends on each one.

## 1. Learn the pipeline

Read [AGENTS.md](AGENTS.md) fully. It defines the crew (Producer, System Analyst, Writer,
Director + tools), the two approval gates, the commands and the rules. Then skim
`pipeline/skills/*/SKILL.md` and `pipeline/agents/*.md` — those are the instructions you'll follow.

## 2. Install the tools

From this folder:

| OS | Command |
|---|---|
| Windows | `powershell -ExecutionPolicy Bypass -File setup.ps1 -Agent <you>` |
| macOS / Linux | `bash setup.sh <you>` |

`<you>` = `claude`, `gemini`, `codex`, or `all`. It installs/checks FFmpeg, Node.js 22+, Python,
creates `.venv` with Playwright, Pillow and the Kokoro voice, finds a browser to film with,
downloads the voice model (~330 MB once), installs the skills for your agent and runs the doctor.
Installing system tools (winget/brew/apt) may need the user's approval — ask before running them
if your permissions require it. If the script stops, read its message, fix that one thing, run it
again (it's safe to repeat).

## 3. Check

`.venv\Scripts\python.exe scripts\doctor.py` (Windows) or `.venv/bin/python scripts/doctor.py`.
Every `[!!]` line has a `fix:` — do it and re-run until it ends with "All set".
`[--]` lines are optional (e.g. `edge-tts`, only needed for Malay or other languages Kokoro lacks).

## 4. Make the skills and roles available to *you*

`scripts/install_agent.py` (run by setup) writes the agent-specific copies from `pipeline/`:

| Agent | Skills | Sub-agents | Entry command | Instructions file |
|---|---|---|---|---|
| Claude Code | `.claude/skills/` | `.claude/agents/` | `/tutorial` | `CLAUDE.md` → AGENTS.md |
| Gemini CLI | `.agents/skills/` | `.gemini/agents/` | `/tutorial` | `GEMINI.md` → AGENTS.md |
| Codex | `.agents/skills/` | — (play the roles in turn) | — (say "make a tutorial…") | `AGENTS.md` |
| anything else | read `pipeline/skills/` directly | play the roles in turn | — | `AGENTS.md` |

**If your agent is not in the table**, set it up by hand the same way, without changing
`pipeline/`:
1. Make sure your agent reads `AGENTS.md` at startup (some read `AGENTS.md` natively; otherwise
   create your agent's instructions file — e.g. `.cursor/rules/tutorial-studio.mdc`,
   `.github/copilot-instructions.md`, `CONVENTIONS.md` — containing only:
   "Read and follow AGENTS.md in the repository root.").
2. If your agent supports SKILL.md skills, copy `pipeline/skills/*` into its skills folder.
   If it supports sub-agents/custom modes, create one per file in `pipeline/agents/` (the body
   is the system prompt; `name`/`description` are in the frontmatter).
3. If it supports custom commands, make `tutorial` from `pipeline/commands/tutorial.md`
   (replace `$ARGUMENTS` with your agent's placeholder for the user's arguments).
4. Write down what you created in `ONBOARDING-LOG.md` (agent, date, files) so the next agent
   knows.

Never edit the generated copies; edit `pipeline/` and re-run `install_agent.py` (or redo step 4).
`install_agent.py --list` shows whether installed copies are current.

## 5. Prove it works: the demo tutorial

A tiny demo app and a finished shotlist are included. Run, from this folder:

```
py -3 -m http.server 8765 -d examples/demo-app        # leave running (macOS/Linux: python3 -m http.server ...)
.venv\Scripts\python.exe scripts\capture.py demo-first-invoice --check
.venv\Scripts\python.exe scripts\voice.py demo-first-invoice
.venv\Scripts\python.exe scripts\capture.py demo-first-invoice
.venv\Scripts\python.exe scripts\build.py demo-first-invoice --draft
```

Expected: "all steps work", 12 voice clips, three scenes filmed, and
`projects/demo-first-invoice/renders/draft.mp4` (~40 s) plus `storyboard.html`. Extract a frame
(`ffmpeg -ss 18.5 -i projects/demo-first-invoice/renders/draft.mp4 -frames:v 1 check.png`) and
look at it: the "Customer" field zoomed in with a purple ring and a cursor. Stop the demo server
afterwards. (The project's `.env` holds the demo app's public test login.)

## 6. Report to the user

Tell them: which agent you set up, that the demo rendered (with the path), anything you couldn't
install, and how to start: _"Make a tutorial of my app at http://localhost:3000 (code in
D:\code\myapp) showing how to create an invoice"_ or `/tutorial <name> <brief>`.
