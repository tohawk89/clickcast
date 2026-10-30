---
name: tutorial-pipeline
description: Producer playbook for making a narrated video tutorial of a web app with Tutorial Studio. Use when the user asks to make, plan, film, re-cut or finish a tutorial / walkthrough / demo video of a website or web project, or runs /tutorial. Covers intake, running the System Analyst, Writer and Director, the two approval gates (story, draft) and delivery.
---

# Tutorial pipeline — the Producer

You are the Producer: the only role that talks to the user. You run the crew in
order and stop at two gates for the user's approval. Read `AGENTS.md` first if you haven't.

## 0. Intake

1. Read `STYLE.md`, `style.json`, the last ~10 rows of the root `FEEDBACK.md` (house lessons; re-making an existing project? also its `projects/<name>/FEEDBACK.md`).
2. Project: if `projects/<name>/project.json` doesn't exist, create it:
   `py scripts/new_project.py <name> --url <URL> --repo <PATH> --start "<cmd>" --goal "<goal>"`
   (kebab-case name; ask for the URL / repo path if the brief doesn't give them).
3. Ask the open questions **in one go** (a multiple-choice tool if your agent has one). Skip what
   the brief or house style already answers; put the house default first, marked "(house style)":
   - **Goal**: after watching, the viewer can… (one sentence). **Audience**: who, how expert.
   - **Length**: ~1 min quick task / 2–4 min walkthrough / longer course with chapters.
   - **Language & voice**: English Kokoro voice (house) / Malay or another language (edge-tts
     voice, online) / the user's own recorded voice.
   - **Look**: video (moving cursor, typing — house) / screenshots (calm slides) / mixed.
   - **Captions** burned in or not (an `.srt` is always made). **Music**: none / soft bed.
   - **Demo login**: which test account; ask the user to put it in `projects/<name>/.env`
     (`DEMO_EMAIL=…`, `DEMO_PASSWORD=…`) themselves. Never ask them to paste a real password in chat.
4. Save the answers under "Intake" in `notes.md`; "always…" answers also go to house style.
5. Make sure the app is reachable (open the URL; if not, run the project's `start` command in the
   background and wait for it). Run `py scripts/doctor.py` if this machine hasn't been checked.

## 1. Analyse → 2. Write

- Run the **system-analyst** (sub-agent, or play it: `pipeline/agents/system-analyst.md`).
  Hand it: project name, goal, audience, repo path, URL, anything the user said about the flow.
  It returns a short summary; the work is in `analysis/analysis.md`. If it reports blockers
  (app down, login fails, the feature doesn't exist), tell the user before going on.
- Run the **writer** (`pipeline/agents/writer.md`) with the project name and the intake answers.
  It writes `story.md`.

## GATE 1 — the story

Show the user the story in chat, compact: title, one line per scene, the narration lines, the
estimated length, and anything the Writer flagged as an assumption. Ask: "Shall I film this, or
what would you change?" Send changes back to the Writer (or edit `story.md` yourself if tiny)
and show the changed parts again. On a clear yes: set `story.md` status to `APPROVED`, add a row to
`notes.md` → Approvals (date, "story", their words), set `project.json` stage `directing`.

## 3–4. Direct → draft

Run the **director** (`pipeline/agents/director.md`) with the project name. It writes the
shotlist, checks it, voices, films, and renders `renders/draft.mp4` + `storyboard.html`, and
tells you what it verified and any compromises it made.

## GATE 2 — the draft

Give the user `renders/draft.mp4` and `renders/storyboard.html` (open it in a browser: the video
plus one row per step; click a row to jump). Ask for feedback by time or step key ("s02.1").
For each comment, follow `pipeline/skills/draft-review`: route it (story → Writer, picture/timing
→ Director, taste → house style), apply, re-render the draft, and show what changed. Repeat until
they approve. Log the approval in `notes.md`.

## 6–7. Final and delivery

`py scripts/build.py <name> --final` (add `--music`, `--captions` per intake). Check frames and
the loudness line. Deliver: path to `final.mp4`, `captions.srt`, and — if music needs it — the
attribution text from `library/CREDITS.md` for the video description. Ask once for feedback.
When the user confirms the final, offer to delete `capture/*/frames` and `renders/.cache`
(list sizes first; they can be rebuilt by re-running capture/build); delete only on a yes.

## Rules you enforce

Two gates, test data only, no production without explicit OK, no publishing/uploading, music only
from approved free sources (ask before downloading). See `AGENTS.md` → Rules.
