# My tutorial style

The agents read this before every tutorial and update it whenever I give feedback that should
apply to future tutorials. Numbers the scripts use live in `style.json`; this file holds the
*why* and everything that can't be a number.

_Last updated: 2026-10-30 (zoom only on purpose, group form fields in one line, mixed look)_

## Audience & tone
- Friendly, plain, second person ("Click **Save**"). No "simply", "just", "easy".
- Say what the viewer will be able to do in the first sentence. End on the visible result and
  one "next up" line.
- Use the app's own words exactly as the UI shows them.

## Pacing
- One narration line = one action; the action lands about halfway through the line
  (`pacing.act_at` 0.55), so the viewer hears what to do as they see it.
- **Except routine forms**: don't narrate field by field — the video already shows the typing.
  One line covers the whole form ("Fill in your details"), the fields are filled as silent steps,
  and narration only returns for what the viewer could get wrong (a password rule, a required
  checkbox such as the terms). Narrate a single field only when it needs explaining.
- A real pause between lines (`pacing.gap` 0.8 s, voice speed 0.95). The user found 0.35 s rushed —
  let each action settle before the next line.
- Typing is shown at a natural speed (`capture.type_delay_ms` 55); passwords never visibly typed.

## Look
- App filmed at 1280×720 layout, 1.5× density → crisp 1080p with large, readable UI.
- **Mixed look by default**: video for scenes where motion teaches (navigating, opening menus, a
  key click), screenshots for long forms, overviews and results. Pick per scene.
- **Zoom only on purpose** (`camera.auto_zoom` = never, 1.5× when used): the default is the whole
  page, so the viewer sees the context. Zoom only when a control is too small to read, at most
  once or twice a scene, and never field by field through a form — the camera jumping around
  loses the situation. Use the ring, a callout or spotlight to point instead.
- Purple ring (`#5A46D6`) around the control being used — it eases in well before a tap and leaves
  right after it, never lingering on the next page or drifting after typing; callouts as purple pills; spotlight
  (dim the rest) for "look at this result" moments.
- Title card with a yellow TUTORIAL pill, end card "Thanks for watching!" — flat, brand purple.
- Chapter label bottom-left at each scene start.
- Scrollbars hidden; drawn cursor with a click ripple.

## Voice
- Kokoro `af_heart`, speed 1.0, for English. Malay → Edge voice `ms-MY-YasminNeural` (ask first,
  it's online).

## Captions & sound
- Captions not burned in by default; `captions.srt` always delivered for the upload.
- Narration at -16 LUFS. Music only if asked: soft, -26 dB, ducked under the voice.

## Never do
- Never show real customer data, real passwords or tokens.
- Never ask viewers to like / subscribe.
- When a choice depends on the viewer (status, type…), say "choose the one that fits you", then
  name what we pick in the demo.
