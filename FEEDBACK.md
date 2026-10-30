# Feedback log (house)

Feedback that changed the **house style** — STYLE.md / style.json, used by every future tutorial —
newest first. This file is shared, so the Project column holds the project's `id` from its
`project.json`, never its name, and each row describes the lesson in general terms.
Feedback about one tutorial only (**video** / **once**) goes in `projects/<name>/FEEDBACK.md`,
which stays local.

| Date | Project | What I said | What changed | Scope |
|---|---|---|---|---|
| 2026-10-30 | p-5c1e | Camera zooms and moves around too much and loses the situation; zooming out to show everything is fine | auto_zoom type→never, zoom 1.7→1.5; zoom only on purpose, max 1–2 per scene, never field by field (style.json, STYLE.md, directing skill) | house |
| 2026-10-30 | p-5c1e | Narration goes input by input; one line can cover a whole form plus the things to watch out for (terms checkbox, password rule) | routine forms = one line + silent field steps; narrate only what the viewer could get wrong (STYLE.md, story-writing + directing skills, story template) | house |
| 2026-10-30 | p-5c1e | A mix of video and screenshot per situation works well | mixed look is the default, chosen per scene (STYLE.md, story-writing skill) | house |
| 2026-10-29 | p-5c1e | "Overall it seems to rush" | pacing gap 0.35→0.8 s, min_step 1.4→2.0, tail 0.8→1.2, voice speed 1.0→0.95 (style.json) | house |
| 2026-10-29 | p-5c1e | Highlight ring pops in too fast / fades out late (stays after the page changes), drifts off the input after typing | ring eases in 0.45 s and leads clicks by 0.9 s, fades out 0.3 s right after the tap, ends when typing ends (build.py + style.json highlight) | house |
