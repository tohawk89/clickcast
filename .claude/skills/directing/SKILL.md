---
name: directing
description: Director skill for Tutorial Studio. Use after the user approves story.md to turn it into shotlist.json and run the crew tools — capture.py --check, voice.py (narration), capture.py (filming the web app as videoshots or screenshots), build.py (draft/final render) — then verify the draft. Also use to fix a failing step, re-film a scene, or change zooms, callouts, timing or cards.
---

# Directing — from approved story to draft video

Input: the **approved** `story.md` (status `APPROVED`; if not, stop and tell the Producer),
`analysis/analysis.md` (+ `pages.json`) for selectors, `notes.md` intake, `style.json`.
Output: `shotlist.json`, then `renders/draft.mp4` + `renders/storyboard.html`.
The full shotlist format is in `reference.md` next to this file — read it before writing one.

## 1. Write shotlist.json

- One scene per story scene, same ids (`s01`…), `chapter` = the story's chapter name,
  `mode` = the story's look. One step per narration line: `say` = the line **word for word**,
  `do` + `target` = the action. Extra silent steps (`wait`, `scroll`) are fine.
- Selectors from the analysis, most stable first (`[data-testid]`, `#id`, `[name]`,
  `role=…`, `text=…`). Never nth-child chains.
- Sign-in and any preparation the viewer shouldn't watch go in `setup` (not filmed). Credentials
  only as `${DEMO_EMAIL}` / `${DEMO_PASSWORD}` from the project's `.env`; password steps get
  `"secret": true`.
- Emphasis from the story: `zoom`, `callout`, `spotlight`, `focus` (highlight something other than
  what's clicked, e.g. the total after saving). House default zooms on typing (style.json
  `camera.auto_zoom`) — don't add `zoom` to every step; constant zooming is tiring.
- A click that should land as the line ends ("…then click **Save**.") gets `"act_at": 0.8`.
- `intro.say` / `outro.say` from the title/end card narration; `title`, `subtitle`, `outro.title`,
  `outro.text` from the story.

## 2. Check, voice, film

```
py scripts/capture.py <name> --check     # plays every step fast, no filming: fixes selectors cheaply
py scripts/voice.py <name>               # narration clips (cached; only changed lines are redone)
py scripts/capture.py <name>             # films; each step lasts as long as its line
```
- A failing step prints its key (`s02.3`) and saves `capture/<scene>/error.png`. Look at the
  image, fix the selector or add a `wait`/`setup` step, and `--check` again.
- Make the take repeatable: each run starts in a fresh browser profile (empty cookies and
  storage). If the app keeps data server-side, make sure re-running doesn't fail (e.g. unique
  names), or ask the Producer to have the user reset the demo data.
- `voice.py` engine/voice come from the intake (`shotlist.voice` or `style.json`). `recorded`
  writes `voice/script.md` for the user to record; it exits listing what's missing.

## 3. Draft

`py scripts/build.py <name> --draft` (720p, "DRAFT" badge, ~real time). Then **look at it**:
extract frames at each zoom, callout, chapter label and card
(`ffmpeg -ss <t> -i renders/draft.mp4 -frames:v 1 -vf scale=960:-1 check.png`; step times are in
`renders/timeline.json`) and check:
- the cursor lands on the right control and the click ripple is on it;
- zoomed views keep the important thing inside the frame; callouts don't cover what they label;
- nothing private is on screen (real names, emails, tokens, notifications);
- the narration matches what's on screen at that moment (open storyboard.html to skim);
- `build.py` printed `ok loudness` and no `!!` lines (overlapping narration means a line is
  longer than its step: shorten the line, or add `pause`).
Fix and rebuild before handing back. Report to the Producer in ≤10 lines: draft path, length,
what you checked, any compromise (e.g. "s03 is screenshots because the chart animates slowly").

## 4. Changes after review

Use the "What to re-run" table in `AGENTS.md`. Re-film only affected scenes with
`capture.py --scene <id>` (earlier scenes are replayed unfilmed to reach the right state).

## 5. Final (only after the Producer confirms the user approved the draft)

`py scripts/build.py <name> --final [--music library/music/<file>] [--captions]` → check frames
and loudness again → hand back `renders/final.mp4`.

## Optional: animated cards with HyperFrames

Built-in cards are drawn by `build.py` in the brand colours. For a richer look, make a full-frame
card with the `/hyperframes` skills (if your agent has them; `npx hyperframes` otherwise) at
the video's resolution, render it to `projects/<name>/assets/title.mp4`, and set
`"intro": {"card": "assets/title.mp4", "say": "…"}` (same for `outro`).
