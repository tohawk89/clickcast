---
name: story-writing
description: Writer skill for Tutorial Studio. Use to turn a System Analyst's analysis of a web app into a tutorial story (story.md) — scenes, what is on screen, and the exact narration lines — for the user to approve before filming. Also use to revise a story or narration after feedback.
---

# Story writing — the script the user approves

Input: `projects/<name>/analysis/analysis.md`, `notes.md` (intake: goal, audience, length,
language, look), `STYLE.md` (house voice and pacing). Output: `projects/<name>/story.md`, using
`story-template.md` next to this file. The Director turns it into the shotlist almost line by line,
so it must be both pleasant to read and precise.

## Shape

- **Promise → steps → result → next.** Intro line says what the viewer will be able to do. Each
  scene is one sub-task with a short chapter name (2–4 words). End on the visible result, then
  one line on what to watch/do next.
- **Length**: narration runs at ~150 words/minute plus ~1 s per action. Stay within the intake's
  length; for a 1–2 min tutorial, 3–5 scenes. Cut anything the goal doesn't need.
- **Follow the real flow** from the analysis, in the order a user does it. Don't invent features,
  labels or menu paths; if the analysis says "unverified", flag it in "Assumptions".

## Narration lines

- **One line = one on-screen action** (or one thing to look at). The Director films each line as
  one step, timed by how long it takes to say. 5–20 words per line.
- Say it as you show it: "Click **New invoice**." The action happens about halfway through the
  line, so the verb comes early and the label matches the button exactly as the UI writes it.
- Second person, present tense, friendly and plain. No "simply/just/easy". Explain *why* only when
  it helps the viewer decide something.
- Write for the ear: short sentences, numbers as they're said ("four hundred and fifty ringgit"
  only if the TTS would misread "RM 450"; otherwise write normally and the Director can add a
  pronunciation fix). Spell product names the way they should be pronounced, or note it.
- Language: the intake's language. For Malay or others, write natively in that language — don't
  translate English phrasing word for word.
- Typing lines name what gets typed ("Type the customer's name"); the actual demo value goes in
  the "Action" column (test data only — e.g. "Kopi Corner Sdn Bhd", never a real customer).
- Login: if the viewer needs to see signing in, show the email being typed and say "enter your
  password" — the password itself is never shown or said. Otherwise sign in off camera (setup).

## Look

Per scene pick **video** (things move: cursor, typing, menus opening — default) or
**screenshot** (calm overview, reading a result, a long form you don't need to watch filled).
Mark what deserves attention: **zoom** (small or important controls, typing), **callout** (a
2–5 word label next to something), **spotlight** (dim everything else).

## Revising

When the user or Producer sends changes, edit `story.md` in place, bump the version in the status
line, and list what changed at the top under "Changes in vN" so the Producer can show just that.
Keep scene ids stable (`s01`, `s02`…) — the Director re-films only scenes that changed.

## Hand back

Return to the Producer: the title, estimated length, number of scenes, and the assumptions or
questions, in ≤8 lines. Don't approve it yourself — status stays `DRAFT vN — waiting for approval`.
