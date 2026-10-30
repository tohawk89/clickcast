# ClickCast

**Turn any web app into a narrated video tutorial, just by talking to an AI agent.**

ClickCast reads your app's code, clicks through it in a real browser, writes the tutorial script,
films it, adds a voice-over and edits it into a finished video. You approve the script before
anything is filmed, and you review a draft before the final render.

```
your brief ─► analyse app ─► write story ─► ✅ you approve ─► film + narrate ─► draft
                                                                                 │
                       final.mp4 + captions ◄── final render ◄── ✅ you approve ◄┘
```

## What you get

- A sharp 1080p MP4 with title/end cards, auto-zoom, highlights, callouts and a smooth cursor
- Natural voice-over (Kokoro offline, Edge voices for Malay and other languages, or your own voice)
- `captions.srt` ready for YouTube
- A clickable storyboard to review the draft step by step
- It learns your taste: feedback like "always add captions" is saved and reused next time

## Requirements

- Python 3.10+ and FFmpeg
- An AI coding agent: Claude Code, Gemini CLI, Codex, Cursor…
- Your web app running locally or on staging, with a **test account** (never real customer data)

## Setup

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File setup.ps1
```

```bash
# macOS / Linux
bash setup.sh
```

Or open the folder in your agent and say: *"Set up this pipeline — follow ONBOARDING.md."*

## Usage

Open this folder in your agent and describe the tutorial:

> Make a tutorial of my app at http://localhost:3000 (code in D:\code\billing) showing a new user
> how to create their first invoice. About 2 minutes, English, with captions.

In Claude Code or Gemini CLI you can also run `/tutorial <name> <brief>`.

Then:

1. Put the demo login in `projects/<name>/.env` (`DEMO_EMAIL=…`, `DEMO_PASSWORD=…`)
2. Approve the story
3. Review `projects/<name>/renders/storyboard.html` and give feedback
4. Approve the draft → get `renders/final.mp4`

## How it works

A small crew of AI roles, each with its own instructions in `pipeline/`:

| Role | Job |
|---|---|
| Producer | talks to you, collects approvals |
| System Analyst | reads the code, explores the app, finds flows and selectors |
| Writer | writes scenes and narration (`story.md`) |
| Director | builds the shot list, runs voice → camera → editor |

The heavy lifting is done by Python scripts in `scripts/` (Playwright for filming, FFmpeg for
editing). Every script has `--help`. Full agent instructions: [AGENTS.md](AGENTS.md).

## Project layout

```
pipeline/     role definitions and skills (source of truth)
scripts/      voice, capture, build and helper tools
examples/     a tiny demo app to try the pipeline
library/      free music and sound effects (see CREDITS.md)
projects/     one folder per tutorial
STYLE.md      your saved taste  ·  style.json  the numbers the scripts use
```

## Licence

[MIT](LICENSE). Music and SFX keep their own licences, listed in `library/CREDITS.md`.
