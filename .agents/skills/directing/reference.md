# shotlist.json reference

A complete working example: `projects/demo-first-invoice/shotlist.json` (films
`examples/demo-app`). Paths are relative to the project folder; times in seconds.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `title`, `subtitle` | string | title card text (and the storyboard's title) |
| `kicker` | string | small pill above the title (default `TUTORIAL`) |
| `url` | string | app base URL (default: `project.json` url) |
| `locale`, `color_scheme` | string | browser locale (`en-US`, `ms-MY`…), `light` / `dark` |
| `capture` | object | overrides `style.json` capture: `viewport` [w,h] CSS px, `scale` (pixel density: 1280×720 × 1.5 = 1920×1080 video), `browser` (`msedge`/`chrome`/`chromium`), `type_delay_ms`, `mobile`, `user_agent`, `css`, `safe_area` (see "Phone / vertical videos") |
| `voice` | object | overrides `style.json` voice: `engine` (`kokoro`/`edge`/`recorded`/`silent`), `voice`, `speed`, `lexicon` {"word": "how to say it"} |
| `music` | path | background music file (e.g. `library/music/calm.mp3`; relative to the studio root) |
| `intro` | object or `false` | title card: `say` (narration over it), `card` (a video file to use instead of the built-in card) |
| `setup` | steps | run before filming, never filmed (sign-in, dismissing banners, preparing data) |
| `scenes` | list | see below |
| `outro` | object or `false` | end card: `title` (default style `cards.end_text`), `text` (second line), `say`, `card` |

## Scene

| Key | Meaning |
|---|---|
| `id` | unique, stable: `s01`, `s02`… Voice clips and capture folders are named after it |
| `title` | for the storyboard |
| `chapter` | label shown bottom-left at the start of the scene ("1  Sign in"); omit for none |
| `mode` | `video` (videoshot: real motion, typing, cursor glides — default) or `screenshot` (one still per step, cross-faded) |
| `cursor` | `false` hides the drawn cursor in this scene |
| `steps` | list of steps, played in order |

Scenes follow each other in the same browser tab: scene 2 starts where scene 1 ended.

## Step

| Key | Meaning |
|---|---|
| `say` | narration line. The step lasts as long as the line (+ `pacing.gap`); without it the step is short |
| `do` | `goto` (`url`), `click`, `dblclick`, `hover`, `type` (`text`), `fill` (`text`, instant), `select` (`value`), `press` (`key`, e.g. `Enter`, `Control+K`), `scroll` (`target`, or `y` pixels), `wait` (`sec`; with `target`: until that element is visible, up to 15 s), `upload` (`file`, see below), `none` (just narration) |
| `target` | Playwright selector of the control: `#id`, `[data-testid="save"]`, `input[name="email"]`, `role=button[name="Save"]`, `text=New invoice`, `button:has-text("Save")` |
| `text` / `value` / `key` / `url` / `sec` / `y` | the action's argument. `${NAME}` is replaced from the project's `.env` |
| `secret` | `true` for passwords: filled instantly, never typed visibly |
| `clear` | `false` keeps what's already in the field before typing |
| `act_at` | when the action happens, as a fraction of the line (default `pacing.act_at` 0.55): `0.8` = near the end |
| `pause` | extra seconds of hold after the step |
| `focus` | selector to highlight/zoom instead of the target (measured *before* the action) — also for `none` steps: "The total updates here." |
| `zoom` | `true` (style zoom), a number (e.g. `2`), or `false`. Default from `camera.auto_zoom`: `type` = zoom on typing/selecting, `click` = also clicks, `all`, `never` |
| `highlight` | `false` to hide the ring around the target. Ring timing is in style.json `highlight`: `lead` (s before a tap it is fully shown, 0.9), `fade_in` 0.45, `fade_out` 0.3. On clicks it leaves right after the tap; on typing, once the text is typed |
| `callout` | short label (2–5 words) in a pill next to the target |
| `spotlight` | `true` dims everything except the target |
| `file` / `input` | for `upload`: the file to attach (relative to the project, e.g. `assets/plan.png`) and the file input (default: `<target> input[type=file]`). The tap on `target` (the visible button/label) is drawn only — no real click, so no file dialog or camera opens. Never target a "Take photo" button |
| `same_tab` | `true` on a `click`: links and `window.open()` load in the same tab instead of a new one (e.g. a Print button that opens a print view) |

A `scroll` with a `target` and a `callout`/`spotlight`/`highlight` marks the target where it ends
up after scrolling.

## Phone / vertical videos

Put these in `projects/<name>/style.json` (or the shotlist's `capture`):

```json
{"capture": {"viewport": [432, 768], "scale": 2.5, "mobile": true, "safe_area": [80, 125],
             "css": "#cookie-banner{display:none!important}"},
 "camera": {"zoom": 1.5, "fit": 0.95},
 "cards": {"chapter_position": "top", "overlay_scale": 1.4},
 "export": {"final": [1080, 1920], "draft": [720, 1280]}}
```

- `viewport` × `scale` = the video size (432×768 × 2.5 = 1080×1920). Keep the width ≤ 767 px so
  the app's phone layout shows.
- `mobile: true` emulates a phone (touch, isMobile, Android user agent; `user_agent` overrides),
  so `(pointer: coarse)` matches and phone-only controls (camera/gallery buttons) appear. Native
  `<select>` pickers are then filmed open while a value is chosen.
- `safe_area` [top, bottom]: CSS px covered by fixed header/footer bars; targets under them are
  scrolled to the centre before the tap (fixed elements themselves are left alone).
- `css`: extra CSS on every page. The Laravel Herd "Edit with Herd" pill is always hidden.
- `camera.fit` (default 0.7): the largest share of the frame a zoomed target may fill; full-width
  phone fields need ~0.95 to zoom at all. `cards.chapter_position: "top"` keeps the bottom tab bar
  visible; `cards.overlay_scale` enlarges callouts and chapter labels.
- If the flow registers an account on camera, keep the address in `.env` (e.g. `REG_EMAIL`) and
  bump it before each real capture (and after `--check`, which submits the form too).

## Screenshot scenes

The still for `click`/`dblclick`/`hover`/`press` is taken just before the action (the cursor is on
the control the viewer should click); for everything else just after it. Each still shows for as
long as its line; the zoom/highlight/callout animate on top.

## What the tools write

- `voice/voice.json` — key (`intro`, `s01.0`, …, `outro`) → text, file, duration.
- `capture/<id>/error.png` — the page when a step failed (also on `--check`).
- `capture/<id>/events.json` — per step: `t_start`, `t_action`, `t_end`, `box` (target in video
  pixels); the mouse path and clicks (the cursor is drawn by `build.py`); frame list.
- `renders/timeline.json` — every step's time in the video (use it to answer "what's at 0:42?").
- `renders/storyboard.html` — the review page. `renders/captions.srt` — captions for the upload.
