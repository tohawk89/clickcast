"""Camera: play shotlist.json in a real browser and film it, paced by the narration.

Usage:
  .venv\\Scripts\\python.exe scripts\\capture.py <project> [--scene s02 --scene s03] [--headed]

Run voice.py first: each step lasts as long as its "say" line, so picture and voice line up.
Each scene's "mode":
  video       "videoshot": the browser filmed at full sharpness (viewport x scale, e.g. 1280x720
              at 1.5 = 1920x1080) as timed JPEG frames, ~20 fps; the mouse glides to each target.
  screenshot  one still per step. For click/hover/press the still is taken just before the action
              (mouse on the target); otherwise just after it.
The mouse path and clicks are recorded, not filmed: build.py draws the cursor and click ripples
smoothly at the video's frame rate, and scales them with the camera zoom.

Capture options (style.json "capture", projects/<name>/style.json, or the shotlist's "capture"):
  viewport [w, h], scale   layout size in CSS px x pixel density = video size (432x768 @2.5 =
                           1080x1920 portrait; keep the width <= 767 for phone layouts)
  mobile: true             phone emulation: touch, isMobile, a phone user agent (user_agent to
                           override), so CSS (pointer: coarse) matches and phone-only controls show
  css: "..."               extra CSS injected into every page (e.g. hide a dev-tool overlay;
                           the Laravel Herd "Edit with Herd" pill is always hidden)
  safe_area [top, bottom]  CSS px covered by fixed bars; a target inside them is scrolled to the
                           centre before the cursor moves to it (fixed elements are left alone)
Step actions beyond click/type/...: "upload" taps the visible button/label "target" (drawn tap,
no real click, so no file dialog or camera opens) and attaches "file" (relative to the project)
to "input" (default: the file input inside the target). "same_tab": true on a click makes links
and window.open() load in the current tab instead of a new one. "wait" with a "target" waits
until that element is visible (up to 15 s). A "scroll" with a "target" plus callout/spotlight/
highlight marks the target where it ends up after scrolling.
"setup" steps (e.g. signing in with ${DEMO_PASSWORD} from the project's .env) run first and are
never filmed. --scene re-films only those scenes; earlier scenes are replayed quickly, unfilmed,
so the app is in the right state.

Writes capture/<scene>/events.json (step timings, target boxes and mouse path in video pixels,
frame list) plus frames/*.jpg or shots/*.png. On a failing step it saves capture/<scene>/error.png
and stops with the step's key, so the Director can fix that step in shotlist.json.
"""

import argparse
import asyncio
import base64
import json
import math
import shutil
import sys
import time
from urllib.parse import urljoin

from playwright.async_api import async_playwright, TimeoutError as PWTimeout

import style
from style import read_json, write_json

# Hide scrollbars: they are noise in a tutorial and differ between machines.
CLEAN_JS = r"""
(() => {
  const add = () => {
    if (document.getElementById('__tt_clean')) return;
    const s = document.createElement('style'); s.id = '__tt_clean';
    s.textContent = 'html::-webkit-scrollbar,body::-webkit-scrollbar{width:0!important;height:0!important}html{scrollbar-width:none}'
      + '#herd-ai-host,#herd-ai-root{display:none!important}' + (window.__TT_CSS || '');
    document.documentElement.appendChild(s);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
"""

SHOT_BEFORE = {"click", "dblclick", "hover", "press", "upload"}
MOBILE_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/130.0.0.0 Mobile Safari/537.36")
# Make links and window.open() of the next click load in this tab (Print buttons that open a new tab).
SAME_TAB_JS = r"""(el) => {
  const a = el.closest('a,form'); if (a) a.removeAttribute('target');
  if (!window.__tt_open) { window.__tt_open = window.open;
    window.open = (u) => { if (u) location.href = new URL(u, location.href).href; return window; }; }
}"""
# Is the element fixed/sticky (header, footer, tab bar)? Those can't be scrolled to.
FIXED_JS = r"""(el) => { for (let e = el; e && e !== document.body; e = e.parentElement) {
  const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') return true; } return false; }"""


class Fail(Exception):
    pass


class Camera:
    def __init__(self, page, cdp, house, base, viewport, scale, safe_area=None):
        self.page, self.cdp, self.house, self.base, self.scale = page, cdp, house, base, scale
        self.safe = safe_area
        self.vw, self.vh = viewport
        self.pos = (self.vw * 0.5, self.vh * 0.55)
        self.frames, self.mouse, self.clicks = [], [], []
        self.t0, self.recording, self.task, self.fdir, self.stalls = time.time(), False, None, None, 0

    # -- filming
    async def _loop(self):
        last, n = None, 0
        clip = {"x": 0, "y": 0, "width": self.vw, "height": self.vh, "scale": self.scale}
        # With phone emulation a clip is measured in page coordinates and drifts when the page
        # scrolls; the plain viewport shot is already viewport x scale, so take that instead.
        shot = {"clip": clip} if not self.house["capture"].get("mobile") else {}
        q = self.house["capture"]["jpeg_quality"]
        while self.recording:
            t1 = self.now()
            try:
                # A capture can stall forever while the page navigates: skip it and take the next.
                r = await asyncio.wait_for(self.cdp.send("Page.captureScreenshot", {
                    "format": "jpeg", "quality": q, **shot, "optimizeForSpeed": True}), 1.0)
            except Exception:
                self.stalls += 1
                await asyncio.sleep(0.03)
                continue
            t = (t1 + self.now()) / 2
            data = base64.b64decode(r["data"])
            if data == last:
                continue  # unchanged picture: the previous frame holds
            name = f"{n:06d}.jpg"
            (self.fdir / name).write_bytes(data)
            self.frames.append([name, round(t, 4)])
            last, n = data, n + 1

    async def start(self, fdir):
        self.fdir, self.frames, self.mouse, self.clicks, self.stalls = fdir, [], [], [], 0
        self.t0 = time.time()
        self.mark()
        self.recording = True
        self.task = asyncio.create_task(self._loop())
        while not self.frames:
            await asyncio.sleep(0.01)

    async def stop(self):
        self.recording = False
        try:
            await asyncio.wait_for(self.task, 2.0)
        except asyncio.TimeoutError:
            pass
        return self.frames

    def now(self):
        return time.time() - self.t0

    def mark(self):
        self.mouse.append([round(self.now(), 4), round(self.pos[0] * self.scale, 1), round(self.pos[1] * self.scale, 1)])

    # -- acting
    async def settle(self, ms=3000):
        try:
            await self.page.wait_for_load_state("networkidle", timeout=ms)
        except PWTimeout:
            pass

    async def box(self, selector, fast=True):
        loc = self.page.locator(selector).first
        try:
            await loc.wait_for(state="visible", timeout=10000)
            await loc.scroll_into_view_if_needed(timeout=5000)
        except PWTimeout:
            raise Fail(f"'{selector}' is not visible on the page after 10 s")
        b = await loc.bounding_box()
        if not b:
            raise Fail(f"'{selector}' has no box on screen")
        if self.safe:
            top, bottom = self.safe
            if (b["y"] < top or b["y"] + b["height"] > self.vh - bottom) and not await loc.evaluate(FIXED_JS):
                await loc.evaluate("(el, s) => el.scrollIntoView({block: 'center', behavior: s})",
                                   "instant" if fast else "smooth")
                await asyncio.sleep(0.1 if fast else 0.7)
                b = await loc.bounding_box() or b
        return b

    def move_time(self, x, y):
        d = math.hypot(x - self.pos[0], y - self.pos[1])
        return 0.0 if d < 2 else min(1.0, max(0.35, d / self.house["capture"]["mouse_px_per_sec"]))

    async def glide(self, x, y, fast=False):
        """Move the mouse to x, y along an eased, slightly curved path, recording it."""
        x0, y0 = self.pos
        dist = math.hypot(x - x0, y - y0)
        dur = self.move_time(x, y)
        if fast or dur == 0:
            await self.page.mouse.move(x, y)
            self.pos = (x, y)
            self.mark()
            return
        n = max(8, int(dur * 60))
        bend = min(60, dist * 0.12)
        nx, ny = -(y - y0) / dist, (x - x0) / dist
        t_start = time.time()
        for i in range(1, n + 1):
            u = i / n
            e = u * u * (3 - 2 * u)
            arc = math.sin(math.pi * e) * bend
            self.pos = (x0 + (x - x0) * e + nx * arc, y0 + (y - y0) * e + ny * arc)
            await self.page.mouse.move(*self.pos)
            self.mark()
            lag = t_start + dur * u - time.time()
            if lag > 0:
                await asyncio.sleep(lag)
        self.pos = (x, y)

    async def sleep_until(self, t):
        d = t - self.now()
        if d > 0:
            await asyncio.sleep(d)

    async def click(self, fast, double=False):
        self.clicks.append([round(self.now(), 4), round(self.pos[0] * self.scale, 1), round(self.pos[1] * self.scale, 1)])
        if double:
            await self.page.mouse.dblclick(*self.pos)
            return
        await self.page.mouse.down()
        await asyncio.sleep(0 if fast else 0.08)
        await self.page.mouse.up()

    async def act(self, st, t_act, fast, before_shot=None):
        """Perform one step. Returns the box (CSS px) to highlight, or None."""
        page, do = self.page, st.get("do", "none")
        target = st.get("target")
        # "focus" is measured before the action: a click may close what it points at.
        focus = await self.box(st["focus"], fast) if st.get("focus") else None
        box = None
        if do == "goto":
            await page.goto(urljoin(self.base + "/", st["url"].lstrip("/")), wait_until="domcontentloaded")
            await self.settle()
        elif do in ("click", "dblclick", "hover", "type", "fill", "select", "upload"):
            b = await self.box(target, fast)
            cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
            if do in ("type", "fill"):
                cx = b["x"] + min(b["width"] * 0.25, 60)
            if not fast:
                await self.sleep_until(t_act - self.move_time(cx, cy))
            await self.glide(cx, cy, fast)
            box = b
            if before_shot and do in SHOT_BEFORE:
                await before_shot()
            if st.get("same_tab"):
                await page.locator(target).first.evaluate(SAME_TAB_JS)
            if do == "select":
                await self.click(fast)
                await page.locator(target).first.select_option(style.expand(str(st["value"])))
            elif do == "upload":
                # A drawn tap only: a real click would open the file dialog (or the camera).
                self.clicks.append([round(self.now(), 4), round(self.pos[0] * self.scale, 1),
                                    round(self.pos[1] * self.scale, 1)])
                f = self.house["_proj"] / style.expand(str(st["file"]))
                if not f.exists():
                    raise Fail(f"upload file not found: {f}")
                inp = st.get("input") or f"{target} input[type=file]"
                await page.locator(inp).first.set_input_files(str(f))
            elif do != "hover":
                await self.click(fast, double=do == "dblclick")
            if do in ("type", "fill"):
                loc = page.locator(target).first
                if st.get("clear", True):
                    await loc.fill("")
                text = style.expand(str(st["text"]))
                if fast or do == "fill" or st.get("secret"):
                    await loc.fill(text)
                else:
                    await page.keyboard.type(text, delay=self.house["capture"]["type_delay_ms"])
            await self.settle(1500 if do in ("click", "dblclick", "upload") else 300)
        elif do == "press":
            if before_shot:
                await before_shot()
            if not fast:
                await self.sleep_until(t_act)
            await page.keyboard.press(st["key"])
            await self.settle(1500)
        elif do == "scroll":
            how = "instant" if fast else "smooth"
            if target:
                await page.locator(target).first.evaluate("(el, b) => el.scrollIntoView({behavior: b, block: 'center'})", how)
            else:
                await page.evaluate(f"window.scrollBy({{top: {int(st.get('y', 400))}, behavior: '{how}'}})")
            await asyncio.sleep(0.1 if fast else 0.9)
            # Marked up after scrolling (callout/spotlight/highlight): measure where the target ended up.
            if target and (st.get("callout") or st.get("spotlight") or st.get("highlight")):
                box = await page.locator(target).first.bounding_box()
        elif do == "wait":
            if target:  # wait until something shows up (e.g. a lookup result), up to 15 s
                try:
                    await page.locator(target).first.wait_for(state="visible", timeout=15000)
                except PWTimeout:
                    raise Fail(f"'{target}' did not appear within 15 s")
            sec = float(st.get("sec", 0 if target else 1))
            await asyncio.sleep(min(sec, 0.5) if fast else sec)  # a short wait also helps --check past animations
        elif do != "none":
            raise Fail(f"unknown action do='{do}'")
        return focus or box


async def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--scene", action="append", help="only (re)film these scene ids")
    ap.add_argument("--headed", action="store_true", help="show the browser window while filming")
    ap.add_argument("--check", action="store_true",
                    help="dry run: play every step quickly without filming, to test the selectors (no voice needed)")
    a = ap.parse_args()

    proj = style.project_dir(a.project)
    style.load_env(proj)
    house = style.load(proj)
    house["_proj"] = proj
    shot = read_json(proj / "shotlist.json")
    voice_file = proj / "voice" / "voice.json"
    if not voice_file.exists() and not a.check:
        raise SystemExit("!! run voice.py first: steps are timed by their narration")
    voice = read_json(voice_file) if voice_file.exists() else {}
    base = (shot.get("url") or read_json(proj / "project.json")["url"]).rstrip("/")
    cap = house["capture"] = {**house["capture"], **shot.get("capture", {})}
    vw, vh = cap["viewport"]
    scale = cap["scale"]
    size = [round(vw * scale), round(vh * scale)]
    pace = house["pacing"]
    wanted = set(a.scene or [s["id"] for s in shot["scenes"]])
    unknown = wanted - {s["id"] for s in shot["scenes"]}
    if unknown:
        raise SystemExit(f"!! no such scene: {', '.join(sorted(unknown))}")
    ids = [s["id"] for s in shot["scenes"]]
    if len(set(ids)) != len(ids):
        raise SystemExit("!! scene ids must be unique")
    last_wanted = max(i for i, s in enumerate(shot["scenes"]) if s["id"] in wanted)
    if a.check:
        wanted, last_wanted = set(), len(shot["scenes"]) - 1

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel=cap["browser"], headless=not a.headed)
        except Exception:
            browser = await p.chromium.launch(headless=not a.headed)
        phone = {"is_mobile": True, "has_touch": True,
                 "user_agent": cap.get("user_agent") or MOBILE_UA} if cap.get("mobile") else {}
        ctx = await browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=scale,
                                        locale=shot.get("locale", "en-US"),
                                        color_scheme=shot.get("color_scheme", "light"), **phone)
        if cap.get("css"):
            await ctx.add_init_script(f"window.__TT_CSS = {json.dumps(cap['css'])};")
        await ctx.add_init_script(CLEAN_JS)
        page = await ctx.new_page()
        cam = Camera(page, await ctx.new_cdp_session(page), house, base, (vw, vh), scale, cap.get("safe_area"))
        await page.goto(base, wait_until="domcontentloaded")
        await cam.settle()

        print("setup (not filmed)...")
        for st in shot.get("setup", []):
            await cam.act(st, 0, fast=True)

        for sc in shot["scenes"][:last_wanted + 1]:
            film = sc["id"] in wanted
            mode = sc.get("mode", "video")
            sdir = proj / "capture" / sc["id"]
            if film:
                shutil.rmtree(sdir, ignore_errors=True)
                (sdir / ("frames" if mode == "video" else "shots")).mkdir(parents=True)
                print(f"\n== {sc['id']} [{mode}] {sc.get('title', '')}")
                if mode == "video":
                    await cam.start(sdir / "frames")
                else:
                    cam.t0, cam.mouse, cam.clicks = time.time(), [], []
            else:
                print(f"{'checking' if a.check else 'replaying'} {sc['id']} (not filmed)")
            steps = []
            for i, st in enumerate(sc["steps"]):
                key = f"{sc['id']}.{i}"
                if st.get("say") and key not in voice and not a.check:
                    raise SystemExit(f"!! {key} has a 'say' line but no voice clip: run voice.py again")
                say = voice[key]["dur"] if st.get("say") and key in voice else 0.0
                fast = not film or mode == "screenshot"
                t_start = cam.now()
                t_act = t_start + (say * float(st.get("act_at", pace["act_at"])) if say else 0.15)
                shot_file = sdir / "shots" / f"{i:02d}.png"
                rec = {"i": i, "key": key, "do": st.get("do", "none"), "t_start": round(t_start, 3)}

                async def take():
                    await page.screenshot(path=str(shot_file))
                    rec["shot"] = f"shots/{shot_file.name}"
                    rec["mouse"] = [round(cam.pos[0] * scale, 1), round(cam.pos[1] * scale, 1)]

                n_clicks = len(cam.clicks)
                try:
                    box = await cam.act(st, t_act, fast, before_shot=take if (film and mode == "screenshot") else None)
                except Exception as e:
                    if film and cam.recording:
                        await cam.stop()
                    err = sdir / "error.png"  # also on --check / replays, so a failing step can be seen
                    err.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(err))
                    tgt = st.get("target") or st.get("focus") or st.get("url") or ""
                    print(f"!! step {key} ({st.get('do')} {tgt}) failed: {str(e).splitlines()[0][:300]}")
                    print(f"   the page at that moment: {err}")
                    await browser.close()
                    sys.exit(1)
                acted = cam.clicks[n_clicks][0] if len(cam.clicks) > n_clicks else max(t_act, t_start)
                rec["t_action"] = round(acted if rec["do"] not in ("goto", "none", "wait") else t_start, 3)
                if film and mode == "screenshot" and "shot" not in rec:
                    await asyncio.sleep(0.3)
                    await take()
                if film and mode == "video":
                    await cam.sleep_until(t_start + max(say + pace["gap"], pace["min_step"] if say else 0.4)
                                          + float(st.get("pause", 0)))
                rec["t_end"] = round(cam.now(), 3)
                if box:
                    rec["box"] = [round(box["x"] * scale), round(box["y"] * scale),
                                  round(box["width"] * scale), round(box["height"] * scale)]
                steps.append(rec)
            if film:
                frames = []
                if mode == "video":
                    await cam.sleep_until(cam.now() + pace["tail"])
                    end = cam.now()
                    frames = await cam.stop()
                    steps[-1]["t_end"] = round(end, 3)
                    print(f"   {len(frames)} frames, {end:.1f}s ({len(frames) / end:.0f} fps of change, {cam.stalls} stalled captures skipped)")
                write_json(sdir / "events.json", {"scene": sc["id"], "mode": mode, "size": size, "scale": scale, "steps": steps,
                                                  "frames": frames, "mouse": cam.mouse, "clicks": cam.clicks})
                for r in steps:
                    print(f"   {r['key']:8} {r['do']:7} {r['t_start']:6.2f}-{r['t_end']:6.2f}s  box={r.get('box')}")
        await browser.close()
    print("\nall steps work." if a.check else "\ncaptured. Next: build.py --draft")


if __name__ == "__main__":
    asyncio.run(main())
