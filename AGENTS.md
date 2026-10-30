# Tutorial Studio — AI agents make video tutorials of web apps

This folder turns a web project into a narrated video tutorial. The user names an app and what the
tutorial should teach. A crew of agent roles analyses the app, writes the story, and, once the user
approves the story, films the app in a real browser (videoshots or screenshots), narrates it,
and edits it into a video. The user reviews a **draft** before the **final** render.

This file is the single source of truth for every AI agent (Claude Code, Gemini CLI, Codex,
Cursor, or any other). `CLAUDE.md` and `GEMINI.md` only point here.
**First time in this folder, or tools missing? Follow [ONBOARDING.md](ONBOARDING.md).**

## The crew

| Role | Who | Skill (instructions) | Produces |
|---|---|---|---|
| **Producer** | you, the agent talking to the user | `pipeline/skills/tutorial-pipeline` | intake, approvals, delivery |
| **System Analyst** | sub-agent `system-analyst` | `pipeline/skills/system-analysis` | `analysis/analysis.md` |
| **Writer** | sub-agent `writer` | `pipeline/skills/story-writing` | `story.md` |
| **Director** | sub-agent `director` | `pipeline/skills/directing` | `shotlist.json` → draft video |
| ↳ Narrator | tool run by the Director | `scripts/voice.py` | `voice/*.wav` |
| ↳ Camera | tool run by the Director | `scripts/capture.py` | `capture/<scene>/` |
| ↳ Editor | tool run by the Director | `scripts/build.py` | `renders/draft.mp4`, `final.mp4` |
| ↳ Review page | tool run by the Producer | `scripts/review.py` | `review.json` (comments, approvals) |
| ↳ Animator (optional) | `/hyperframes` skills | `animations/` | richer title/end cards |
| **Reviewer** | Producer + the user | `pipeline/skills/draft-review` | feedback applied + remembered |

Role definitions live in `pipeline/agents/<role>.md`. If your agent can run sub-agents, run each
role as one (they're installed for you by `scripts/install_agent.py`). If it can't, play the roles
yourself, one after another: read the role file, do its job, then switch back to Producer.
Sub-agents can't talk to the user — only the Producer asks questions and gets approvals.

## The workflow (two approval gates)

```
 user brief ─► 0 Intake ─► 1 Analyse ─► 2 Write story ─► [GATE 1: user approves story.md]
                                                                 │
          [GATE 2: user approves draft] ◄─ 5 Draft ◄─ 4 Film+voice ◄─ 3 Direct (shotlist.json)
                     │
                     └─► 6 Final render ─► 7 Deliver + ask for feedback
```

0. **Intake** (Producer) — read `STYLE.md`, `style.json`, the last ~10 rows of the root `FEEDBACK.md`.
   Create the project: `scripts/new_project.py <name> --url <app url> --repo <source path>`.
   Ask, in one go, only what the brief and house style don't answer: goal (what will the viewer be
   able to do?), audience, length, language + voice, video vs screenshot style, captions, music,
   demo login. Save answers under "Intake" in `projects/<name>/notes.md`. Make sure the app is
   running (the `start` command in `project.json`) and a **demo/test account** is in the project's
   `.env` — never a real user's password, never production data on screen.
1. **Analyse** (System Analyst) — read the source code, crawl the running app (`explore.py`),
   click through the flows, and write `analysis/analysis.md`: features, user flows, roles,
   prerequisites, glossary, stable selectors, risks (popups, slow pages, data that changes).
2. **Write** (Writer) — from the analysis and the intake, write `story.md`: the tutorial as
   scenes, each with what's on screen and the exact narration lines. One narration line = one
   on-screen action, except routine forms: one line for the whole form.
3. **GATE 1** (Producer) — show the user the story (title, scenes, narration, estimated length).
   Change it with the Writer until they say yes. Log the approval in `notes.md` → Approvals.
   **Nothing is filmed before this yes.**
4. **Direct** (Director) — turn the approved story into `shotlist.json` (selectors, actions,
   zooms, callouts), then: `capture.py --check` (all selectors work) → `voice.py` → `capture.py`
   → `build.py --draft`. Look at frames of the draft before handing it back.
5. **GATE 2** (Producer) — start `review.py <name>` (in the background) and send the user to the
   review page: every part (title card, each scene, end card) has its own clip, a comment box and
   **Approve**, and every step its own comment; it all saves to `projects/<name>/review.json`.
   Read it with `review.py <name> --list`. Route each comment: words/story → Writer; picture,
   timing, zoom, selectors → Director; taste ("always…") → house style. Re-run only what changed
   (see "What to re-run"); `build.py` redraws only changed parts. Mark fixes with `--done`.
6. **Final** — only after the user approves the draft (every part approved, confirmed in chat):
   `build.py --final`.
7. **Deliver** — give the path to `renders/final.mp4` and `renders/captions.srt` (for the upload),
   then ask once for feedback and record it (`pipeline/skills/draft-review`).

## Commands (run from this folder)

Windows: `.venv\Scripts\python.exe`, macOS/Linux: `.venv/bin/python` (written as `py` below).

```
py scripts/doctor.py                                   # are all tools installed? (run first)
py scripts/new_project.py <name> --url URL [--repo PATH] [--start "npm run dev"]
py scripts/explore.py <name> [--login] [--depth 2]     # Analyst: crawl pages, controls, selectors
py scripts/capture.py <name> --check                   # Director: test every step, no filming
py scripts/voice.py <name> [--engine kokoro|edge|recorded|silent]   # Narrator
py scripts/capture.py <name> [--scene s02] [--headed]  # Camera (after voice.py)
py scripts/build.py <name> --draft                     # Editor: 720p review copy + storyboard.html
py scripts/build.py <name> --final [--music FILE] [--captions]   # (only changed parts redrawn; --fresh: all)
py scripts/review.py <name>                            # review page: comment + approve per part
py scripts/review.py <name> --list | --done s02.1="reply"   # read the comments / mark one fixed
py scripts/install_agent.py [--agent claude|gemini|codex|all]   # (re)install skills + sub-agents
```

Every script has `--help`. `projects/<name>` can be given as just `<name>`.

### What to re-run after a change

| Changed | Re-run |
|---|---|
| narration text, voice, speed | `voice.py` → `capture.py` (only scenes whose lines changed: `--scene`) → `build.py` |
| actions, selectors, mode of a scene | `capture.py --scene <id>` → `build.py` |
| zoom, callout, highlight, chapter, cards, music, captions, style.json | `build.py` only |

Timing comes from the narration: every step lasts as long as its line, so after a voice change,
re-film the scenes that contain it. `build.py` always works out by itself which parts changed;
a change to style.json or build.py itself redraws them all.

## Project layout

```
AGENTS.md  ONBOARDING.md  README.md      instructions (agents / setup / humans)
STYLE.md  style.json  FEEDBACK.md        the user's taste, learned from feedback (house log, by project id)
pipeline/agents/*.md                     role definitions (System Analyst, Writer, Director)
pipeline/skills/*/SKILL.md               the skills (open SKILL.md format) — the canonical copies
pipeline/commands/tutorial.md            the "/tutorial" entry prompt
scripts/                                 the tools (Python + Playwright + FFmpeg)
examples/demo-app/                       tiny web app for testing the pipeline
library/music, library/sfx, CREDITS.md   free audio, every file logged with its licence
projects/<name>/
  project.json  notes.md  .env           id + brief, intake, approvals; demo logins (never committed)
  FEEDBACK.md                             this tutorial's own feedback log (local)
  review.json                             the user's draft comments + approvals per part (local)
  analysis/     analysis.md, pages.json, pages/*.png       (System Analyst)
  story.md                                                  (Writer, approved at GATE 1)
  shotlist.json                                             (Director)
  voice/        <key>.wav, voice.json                       (Narrator)
  capture/<scene>/  events.json, frames/ or shots/          (Camera)
  assets/       anything extra: HyperFrames cards, logos
  renders/      draft.mp4, final.mp4, storyboard.html, captions.srt, timeline.json,
                scenes/<part>.mp4 (per-part review clips), .cache/parts/ (reused render parts)
```

## Rules

- **Two gates, always.** No filming before the story is approved; no final before the draft is.
- **Test data only.** Film with a demo/test account and seed data. Credentials go in
  `projects/<name>/.env` and appear in the shotlist only as `${NAME}`; password fields use
  `"secret": true`. If a screen would show real personal or customer data, stop and ask.
- The agent never types real passwords or payment details itself; the scripts read them from
  `.env`, which the user fills in.
- Never point the pipeline at a production app without the user saying so explicitly.
- Never publish or upload anything (including `hyperframes publish`) unless the user asks.
- Music and SFX only from free sources the user approved (YouTube Audio Library, Pixabay,
  Freesound CC0/CC-BY); log each file in `library/CREDITS.md`; downloads need the user's OK.
- Don't edit files in `pipeline/` copies installed for an agent (`.claude/`, `.gemini/`,
  `.agents/`): edit `pipeline/` and run `install_agent.py`.
- Verify before saying it's done: look at frames of the render (`ffmpeg -ss <t> -i <video>
  -frames:v 1 check.png`) at each zoom/callout, and read the loudness line `build.py` prints.

## Learning from feedback — on every tutorial

Same system as the video-editor studio: `STYLE.md` (taste in words), `style.json` (the numbers the
scripts use), `FEEDBACK.md` (log). A project can override with `projects/<name>/style.json`.
Whenever the user reacts to a story, draft or final: apply it, decide **house** (all tutorials) vs
**video** (this one) — ask "Always, or just this tutorial?" if unclear — save it, log it, and say in
one line what you saved. Two logs:

- **house** → top of the root `FEEDBACK.md` (shared, pushed to git). Log the project by its `id` from
  `project.json` (e.g. `p-7f3a`), never its name, and word the lesson generally — no app screens,
  wording, client names or data.
- **video / once** → top of `projects/<name>/FEEDBACK.md` (local, never committed).

Details: `pipeline/skills/draft-review`.
