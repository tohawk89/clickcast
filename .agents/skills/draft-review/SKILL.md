---
name: draft-review
description: Review-and-learn skill for Tutorial Studio. Use whenever the user reacts to a tutorial story, draft or final video — to route each comment to the right role, apply it, re-render only what's needed, and save lasting preferences to STYLE.md / style.json / FEEDBACK.md so every tutorial gets closer to the user's taste.
---

# Draft review — apply feedback, remember taste

## Find what they mean

Comments come as times ("at 0:42"), step keys ("s02.1"), or descriptions ("the zoom on the price").
Map them with `renders/timeline.json` (each step's start time) and `storyboard.html`.
If you can't tell which moment they mean, ask with the two nearest candidates.

## Route it

| Comment is about | Who | Typical fix |
|---|---|---|
| what's said, order, scenes, length | Writer | edit `story.md` (bump version) → Director re-syncs `say` lines |
| pronunciation | Director | `voice.lexicon` in shotlist or style.json |
| voice, speed | Director | shotlist `voice` (this video) or style.json (always) |
| wrong click, missing step, flaky screen | Director | shotlist step → `capture.py --check` → `--scene` re-film |
| too fast / slow | Director | `pause`, `act_at`, `voice.speed`, style `pacing.gap` |
| zoom, highlight, callout, chapter label | Director | step fields or style `camera` / `highlight` → `build.py` only |
| cards, colours, fonts, captions look, music level | Director | `style.json` brand/cards/captions/audio → `build.py` only |

Re-run only what's needed (AGENTS.md → "What to re-run") and render a new draft. Tell the user
what changed in one or two lines, with the new time if things moved.

## Remember it

1. Decide the scope. A taste statement ("too slow", "I hate zooming on buttons", "always captions")
   with nothing video-specific → **house**. About this app or this tutorial → **video**. Unsure →
   ask "Always, or just this tutorial?"
2. Save it:
   - house → change `style.json` if it's a number/setting, and the matching section of `STYLE.md`
     in words (bump "Last updated"). Praise counts too ("love the spotlight") — record what worked.
   - video → `projects/<name>/style.json` (same keys, any subset) or `notes.md`.
3. Log it — there are two logs, because the root one is shared (pushed to git) and projects are not:
   - house → a row at the **top** of the root `FEEDBACK.md`. In the Project column write the
     project's `id` from `project.json` (e.g. `p-7f3a`), **never its name, URL or client**. Describe
     the lesson in general terms ("pacing felt rushed", "highlight ring lingers after the tap"),
     with nothing that reveals the app's screens, wording or data.
   - video / once → a row at the **top** of `projects/<name>/FEEDBACK.md` (local only; create it
     from the root table header if missing). Here quote the user's exact words freely.
   - Both? (e.g. "too fast here, and always") → one row in each.
4. Say in one line what you saved, e.g. "Saved to house style: zoom only on typing, 1.5×."

If the same kind of feedback appears twice in the root `FEEDBACK.md`, the house style isn't strict enough:
tighten it and say so. Never silently undo a saved preference; if a new request contradicts one,
point it out and ask which wins.

## After delivery

Ask once: "Anything you'd change — story, pacing, voice, look?" When they confirm the final, the
Producer offers the clean-up (see tutorial-pipeline § 6–7).
