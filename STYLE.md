# My tutorial style

The agents read this before every tutorial and update it whenever I give feedback that should
apply to future tutorials. Numbers the scripts use live in `style.json`; this file holds the
*why* and everything that can't be a number.

_Last updated: 2026-10-29 (first feedback: slower pacing, gentler ring)_

## Audience & tone
- Friendly, plain, second person ("Click **Save**"). No "simply", "just", "easy".
- Say what the viewer will be able to do in the first sentence. End on the visible result and
  one "next up" line.
- Use the app's own words exactly as the UI shows them.

## Pacing
- One narration line = one action; the action lands about halfway through the line
  (`pacing.act_at` 0.55), so the viewer hears what to do as they see it.
- A real pause between lines (`pacing.gap` 0.8 s, voice speed 0.95). The user found 0.35 s rushed —
  let each action settle before the next line.
- Typing is shown at a natural speed (`capture.type_delay_ms` 55); passwords never visibly typed.

## Look
- App filmed at 1280×720 layout, 1.5× density → crisp 1080p with large, readable UI.
- Camera zooms in when typing (`camera.auto_zoom` = type, 1.7×), otherwise shows the whole page.
  Constant zooming is tiring; zoom on purpose.
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
