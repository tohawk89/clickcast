# ClickCast

**Turn any web app into a narrated video tutorial, just by talking to an AI agent.**

You tell the agent what the tutorial should teach. ClickCast reads your app's code, clicks through
it in a real browser, writes the script, films it, adds a voice-over and edits it into a video.
You say yes twice: once to the **script** (before anything is filmed) and once to the **draft**
(before the final render).

```
your brief ─► analyse app ─► write story ─► ✅ you approve ─► film + narrate ─► draft
                                                                                 │
                       final.mp4 + captions ◄── final render ◄── ✅ you approve ◄┘
```

## What you get

- A sharp 1080p MP4 with title/end cards, zooms, highlights, callouts and a smooth cursor
- A voice-over (offline Kokoro voice, Edge voices for Malay and other languages, or your own recording)
- `captions.srt`, ready to upload to YouTube
- A review page where you comment on and approve the video part by part
- It learns your taste: feedback like "always add captions" is saved and used next time

## Tools it uses

| Tool | What it does | Cost |
|---|---|---|
| **AI agent** (Claude Code, Gemini CLI, Codex, Cursor…) | Talks to you, reads the code, writes the story and shot list | 🪙 **uses tokens** |
| **Python 3.10+** | Runs the scripts in `scripts/` | free |
| **Playwright + Chromium/Edge** | Opens your app and films the clicks and typing | free, runs locally |
| **FFmpeg** | Cuts, zooms, fades and mixes the sound into the video | free, runs locally |
| **Kokoro** (offline, ~330 MB) / **Edge TTS** / your own recording | Narration voice | free |
| **HyperFrames** *(optional)* | Richer animated title and end cards | free, runs locally |
| `library/music`, `library/sfx` *(optional)* | Free music and sound effects (licences in `library/CREDITS.md`) | free |

Only the AI agent uses tokens. Filming, voicing and editing are plain scripts on your computer.

## The steps, and when tokens are used

| # | Step | Who does it | You get | Tokens |
|---|---|---|---|---|
| 0 | **Intake**: a few questions (goal, audience, length, language, voice, captions) | Producer (the agent you talk to) | `notes.md` | 🟢 low |
| 1 | **Analyse**: reads the source code, crawls and clicks through the app | System Analyst | `analysis/analysis.md` | 🔴 **high** (the biggest cost) |
| 2 | **Write the story**: scenes plus the exact narration lines | Writer | `story.md` | 🟡 medium |
| 3 | ✅ **Gate 1**: you read the story and approve it or ask for changes | you + Producer | approved story | 🟢 low (🟡 for each round of changes) |
| 4 | **Direct**: turns the story into a shot list and fixes any step that fails | Director | `shotlist.json` | 🟡 medium |
| 5 | **Narrate**: `voice.py` | script | `voice/*.wav` | ⚪ none |
| 6 | **Film**: `capture.py` | script | `capture/<scene>/` | ⚪ none |
| 7 | **Draft**: `build.py --draft` | script | `renders/draft.mp4` | ⚪ none |
| 8 | ✅ **Gate 2**: you review the draft part by part (see below) | you + Producer | your comments | 🟡 medium (the agent reads and applies them) |
| 9 | **Final**: `build.py --final` | script | `renders/final.mp4`, `captions.srt` | ⚪ none |

### Saving tokens

- **Give a clear brief up front** (goal, length, language, login). Every unanswered question is another round.
- **Point the analyst at the right part of the app.** "Only the invoices section" costs much less than the whole app.
- **Get the story right at Gate 1.** Changing words after filming means re-voicing and re-filming.
- **Leave all your comments first, then tell the agent once.** One round of fixes is cheaper than five.
- **Run the scripts yourself** when nothing needs to be decided (see [Commands](#commands-no-tokens)).
  For example, after changing a zoom in `shotlist.json`, just run `build.py` again.
- **Re-do only what changed.** `capture.py --scene s03` re-films one scene, and `build.py` only redraws the parts that changed.

## Reviewing the draft (the storyboard)

The draft is split into **parts**: the title card, each scene (`s01`, `s02`…) and the end card.
Start the review page:

```powershell
.venv\Scripts\python.exe scripts\review.py <name>
```

It opens `renders/storyboard.html` in your browser. For each part you get:

- its own **video clip**, so you watch only that part
- a **comment box** for the whole part, plus one per step (each narration line)
- an **Approve** button

Everything saves to `projects/<name>/review.json` as you type. When you're done, tell the agent
"I've reviewed the draft". It reads your comments, sends each one to the right role (wording →
Writer, picture/timing/zoom → Director) and re-renders **only the parts you commented on**. If you
approved a part and it changes later, it asks you to look again. The final is rendered only when
every part is approved.

## Setup

Run once. It installs what's missing (Python packages, the browser for filming, the offline voice
model) and your agent's skills, then checks everything:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File setup.ps1
```

```bash
# macOS / Linux  (first: brew install ffmpeg node python)
bash setup.sh
```

Or open the folder in your agent and say: *"Set up this pipeline — follow ONBOARDING.md."*

**Check it any time** (after an update, on a new machine, when something breaks):

```powershell
.venv\Scripts\python.exe scripts\doctor.py      # macOS/Linux: .venv/bin/python scripts/doctor.py
```

`[ok]` = fine, `[!!]` = must fix (it shows the fix), `[--]` = optional. `--quick` skips the browser
and voice test. Running setup again is safe; it only downloads what's missing.

You also need your web app running **locally or on staging**, with a **test account**. Never use
real customer data.

## Usage

Open this folder in your agent and describe the tutorial:

> Make a tutorial of my app at http://localhost:3000 (code in D:\code\billing) showing a new user
> how to create their first invoice. About 2 minutes, English, with captions.

In Claude Code or Gemini CLI you can also type `/tutorial <name> <brief>`.

Then:

1. Put the demo login in `projects/<name>/.env` (`DEMO_EMAIL=…`, `DEMO_PASSWORD=…`). The agent never types passwords itself.
2. Read and approve the story (`projects/<name>/story.md`)
3. Review the draft on the review page and leave comments
4. Approve every part → get `renders/final.mp4` and `renders/captions.srt`

## Commands (no tokens)

These are what the agent runs. You can run them yourself too. On Windows use `.venv\Scripts\python.exe`,
on macOS/Linux use `.venv/bin/python`. Every script has `--help`.

```
scripts/doctor.py                                  check all tools are installed
scripts/new_project.py <name> --url URL --repo PATH    create a tutorial project
scripts/explore.py <name> [--login]                crawl the app's pages and controls
scripts/capture.py <name> --check                  test every step without filming
scripts/voice.py <name>                            make the narration
scripts/capture.py <name> [--scene s02]            film (all scenes, or one)
scripts/build.py <name> --draft                    720p draft + review page
scripts/review.py <name>                           open the review page
scripts/review.py <name> --list                    show your comments and approvals
scripts/build.py <name> --final [--captions]       1080p final
```

**What to re-run after a change:**

| You changed | Re-run |
|---|---|
| narration words, voice, speed | `voice.py` → `capture.py --scene <id>` → `build.py` |
| clicks, selectors in a scene | `capture.py --scene <id>` → `build.py` |
| zoom, callout, highlight, cards, music, captions, `style.json` | `build.py` only |

## How it works

A small crew of AI roles, each with its own instructions in `pipeline/`:

| Role | Job |
|---|---|
| Producer | talks to you, collects your two approvals |
| System Analyst | reads the code, explores the app, finds the flows and buttons |
| Writer | writes the scenes and narration (`story.md`) |
| Director | writes the shot list, runs voice → camera → editor |

Full agent instructions: [AGENTS.md](AGENTS.md).

## Project layout

```
pipeline/     role definitions and skills (the source of truth)
scripts/      voice, capture, build, review and helper tools
examples/     a tiny demo app to try the pipeline on
library/      free music and sound effects (see CREDITS.md)
projects/     one folder per tutorial (story, shot list, recordings, renders)
STYLE.md      your saved taste  ·  style.json  the numbers the scripts use
```

## Licence

[MIT](LICENSE). Music and SFX keep their own licences, listed in `library/CREDITS.md`.
