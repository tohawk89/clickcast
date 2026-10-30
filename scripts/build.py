"""Editor: put the captured scenes, cards and narration together into the tutorial video.

Usage:
  .venv\\Scripts\\python.exe scripts\\build.py <project> --draft     # fast 720p review copy
  .venv\\Scripts\\python.exe scripts\\build.py <project> --final     # 1080p, after the user OKs the draft
      [--music library/music/x.mp3] [--captions | --no-captions]

Draft and final share one timeline, so feedback on the draft ("at 0:42 ...") holds for the final.
Picture: title card -> scenes -> end card, cross-faded. In every scene the camera eases in on the
step's target (style.json camera.auto_zoom, or the step's "zoom"), a ring highlights it, a step's
"callout" text sits next to it, and the scene's "chapter" shows as a label at its start.
Sound: the narration clips placed where capture.py timed them, loudness-matched (style.json
audio.lufs), with optional music ducked under the voice.

Portrait (e.g. export final [1080, 1920], draft [720, 1280]) works the same: text and cards are
sized by the shorter side. style.json camera.fit (default 0.7) is the largest share of the frame
a zoomed target may fill (raise it for phone layouts, where fields span the full width);
cards.chapter_position "bottom" (default) or "top" places the chapter label (top keeps a phone's
bottom tab bar visible); cards.overlay_scale (default 1) enlarges callouts and chapter labels
(e.g. 1.4 for a phone layout filmed at a high pixel density, where the app's own text is larger).

Writes renders/draft.mp4 or final.mp4, captions.srt (always: also for the upload), timeline.json
(every step's time in the video) and storyboard.html (the review page: video + one row per step).
"""

import argparse
import bisect
import html
import json
import math
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import style
from style import hex_rgb, read_json, write_json

SR = 48000
XFADE = 0.4


def ease(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def out_ease(u: float) -> float:
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def fmt(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


# ----------------------------------------------------------------------------- timeline

def zoom_for(st: dict, rec: dict, house: dict) -> float | None:
    """The zoom level for a step, or None to show the whole page."""
    cam = house["camera"]
    z = st.get("zoom")
    if z is None:
        mode = cam["auto_zoom"]
        do = rec.get("do")
        z = (mode == "all" or (mode in ("type", "click") and do in ("type", "fill", "select"))
             or (mode == "click" and do in ("click", "dblclick", "hover")))
    if z is False or not rec.get("box"):
        return None
    return cam["zoom"] if z is True else float(z)


def card_file(proj: Path, spec: dict) -> Path | None:
    """A ready-made card video (e.g. rendered with HyperFrames) instead of the built-in one."""
    if not spec.get("card"):
        return None
    f = proj / spec["card"]
    if not f.exists():
        raise SystemExit(f"!! card not found: {f}")
    return f


def plan(proj: Path, shot: dict, house: dict, voice: dict) -> dict:
    """Every segment and step with its time in the final video."""
    pace, cards = house["pacing"], house["cards"]
    segs, clips, t = [], [], 0.0
    intro = shot.get("intro", {})
    if intro is not False:
        say = voice.get("intro")
        f = card_file(proj, intro)
        dur = max(style.probe_duration(f) if f else cards["title_sec"], (say["dur"] + 1.0) if say else 0)
        if say:
            clips.append({"key": "intro", "at": 0.5, **say})
        segs.append({"kind": "title", "start": 0.0, "dur": dur, "file": f})
        t = dur
    for n, sc in enumerate(shot["scenes"], 1):
        ev_file = proj / "capture" / sc["id"] / "events.json"
        if not ev_file.exists():
            raise SystemExit(f"!! {sc['id']} isn't captured yet: run capture.py")
        ev = read_json(ev_file)
        steps = []
        if ev["mode"] == "video":
            for r, st in zip(ev["steps"], sc["steps"]):
                steps.append({**r, "st": st})
            dur = ev["steps"][-1]["t_end"]
        else:
            local = 0.0
            for r, st in zip(ev["steps"], sc["steps"]):
                say = voice.get(r["key"], {}).get("dur", 0) if st.get("say") else 0
                d = max(say + pace["gap"], pace["min_step"] if say else 1.0) + float(st.get("pause", 0))
                steps.append({**r, "st": st, "t_start": local, "t_action": local + 0.35, "t_end": local + d})
                local += d
            dur = local + pace["tail"]
        for s in steps:
            s["zoom"] = zoom_for(s["st"], s, house)
            if s["st"].get("say") and s["key"] in voice:
                clips.append({"key": s["key"], "at": t + s["t_start"] + 0.05, **voice[s["key"]]})
        segs.append({"kind": "scene", "n": n, "id": sc["id"], "title": sc.get("title", ""),
                     "chapter": sc.get("chapter"), "mode": ev["mode"], "size": ev["size"],
                     "scale": ev.get("scale", 1.0), "mouse": ev.get("mouse", []), "clicks": ev.get("clicks", []),
                     "cursor": sc.get("cursor", True),
                     "dir": ev_file.parent, "frames": ev.get("frames", []), "steps": steps,
                     "start": t, "dur": dur})
        t += dur
    outro = shot.get("outro", {})
    if outro is not False:
        say = voice.get("outro")
        f = card_file(proj, outro)
        dur = max(style.probe_duration(f) if f else cards["end_sec"], (say["dur"] + 1.4) if say else 0)
        if say:
            clips.append({"key": "outro", "at": t + 0.5, **say})
        segs.append({"kind": "end", "start": t, "dur": dur, "file": f})
        t += dur
    return {"segments": segs, "clips": clips, "duration": t}


class Clip:
    """Frames of a video file, scaled to the output size; holds the last frame when it runs out."""

    def __init__(self, path: Path, size: tuple[int, int], fps: int):
        w, h = size
        self.size, self.n = size, w * h * 3
        self.last = Image.new("RGB", size)
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(path), "-vf",
                                   f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:-1:-1,fps={fps}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

    def next(self) -> Image.Image:
        b = self.p.stdout.read(self.n)
        if len(b) == self.n:
            self.last = Image.frombytes("RGB", self.size, b)
        return self.last


class Camera:
    """Eased pans/zooms between the steps' targets, in source-image pixels."""

    def __init__(self, seg: dict, house: dict):
        sw, sh = seg["size"]
        self.sw, self.sh = sw, sh
        full = (sw / 2, sh / 2, 1.0)
        ez = house["camera"]["ease"]
        maxz = house["camera"]["max_zoom"]
        fit = float(house["camera"].get("fit", 0.7))
        self.keys = []  # (t0, t1, from_state, to_state)
        cur_target = full
        for s in seg["steps"]:
            if s["zoom"]:
                x, y, w, h = s["box"]
                z = min(s["zoom"], maxz, sw * fit / max(w, 1), sh * fit / max(h, 1))
                z = max(1.0, z)
                vw, vh = sw / z, sh / z
                cx = min(max(x + w / 2, vw / 2), sw - vw / 2)
                cy = min(max(y + h / 2, vh / 2), sh - vh / 2)
                target, t0 = (cx, cy, z), max(s["t_start"], s["t_action"] - ez)
            else:
                target, t0 = full, s["t_start"]
            if target != cur_target:
                self.keys.append((t0, t0 + ez, None, target))
                cur_target = target
        # Fill in where each move starts from (a move can begin before the previous one ends).
        resolved = []
        for t0, t1, _, to in self.keys:
            resolved.append((t0, t1, self._at(resolved, t0, full), to))
        self.keys, self.full = resolved, full

    @staticmethod
    def _lerp(a, b, u):
        e = ease(u)
        return (a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e,
                math.exp(math.log(a[2]) + (math.log(b[2]) - math.log(a[2])) * e))

    def _at(self, keys, t, full):
        state = full
        for t0, t1, a, b in keys:
            if t < t0:
                break
            state = b if t >= t1 else self._lerp(a, b, (t - t0) / (t1 - t0))
        return state

    def at(self, t):
        return self._at(self.keys, t, self.full)


# ----------------------------------------------------------------------------- picture

class Painter:
    def __init__(self, house: dict, size: tuple[int, int], draft: bool, shot: dict):
        self.h, self.W, self.H, self.draft, self.shot = house, size[0], size[1], draft, shot
        self.k = min(size) / 1080  # 1.0 at 1080p landscape and at 1080x1920 portrait
        self.o = float(house["cards"].get("overlay_scale", 1.0))  # callouts + chapter labels
        b = house["brand"]
        self.c_brand, self.c_accent, self.c_dark = hex_rgb(b["color"]), hex_rgb(b["accent"]), hex_rgb(b["dark"])
        self.c_text = hex_rgb(b["text"])
        self.fonts = {}
        self.cache = {}
        self.bg = self._gradient()

    def f(self, weight, px):
        key = (weight, round(px * self.k))
        if key not in self.fonts:
            self.fonts[key] = style.font(self.h, weight, key[1])
        return self.fonts[key]

    def _gradient(self):
        top = Image.new("RGB", (1, 2))
        top.putpixel((0, 0), self.c_dark)
        top.putpixel((0, 1), self.c_brand)
        g = top.resize((self.W, self.H), Image.BILINEAR)
        glow = Image.new("RGB", (self.W, self.H), self.c_brand)
        mask = Image.new("L", (self.W, self.H), 0)
        ImageDraw.Draw(mask).ellipse([self.W * 0.55, -self.H * 0.4, self.W * 1.3, self.H * 0.7], fill=110)
        return Image.composite(glow, g, mask.filter(ImageFilter.GaussianBlur(160 * self.k)))

    def source(self, seg, t):
        """The captured picture for local time t in a scene."""
        if seg["mode"] == "video":
            times = seg.setdefault("_times", [f[1] for f in seg["frames"]])
            i = max(0, bisect.bisect_right(times, t) - 1)
            name = seg["dir"] / "frames" / seg["frames"][i][0]
            blend = None
        else:
            steps = seg["steps"]
            i = max(0, max((j for j, s in enumerate(steps) if s["t_start"] <= t), default=0))
            name = seg["dir"] / steps[i]["shot"]
            blend = None
            if i > 0 and t - steps[i]["t_start"] < 0.3 and steps[i - 1].get("shot") != steps[i]["shot"]:
                blend = (seg["dir"] / steps[i - 1]["shot"], (t - steps[i]["t_start"]) / 0.3)
        img = self._load(name)
        if blend:
            img = Image.blend(self._load(blend[0]), img, ease(blend[1]))
        return img, str(name)

    def _load(self, path):
        key = str(path)
        if key not in self.cache:
            if len(self.cache) > 48:
                self.cache.clear()
            self.cache[key] = Image.open(path).convert("RGB")
        return self.cache[key]

    def scene(self, seg, cam, t):
        src, name = self.source(seg, t)
        sw, sh = src.size
        cx, cy, z = cam.at(t)
        # Source size may differ from the planned size (DPR rounding); scale the camera to it.
        fx, fy = sw / seg["size"][0], sh / seg["size"][1]
        vw, vh = sw / z, sh / z
        x0, y0 = cx * fx - vw / 2, cy * fy - vh / 2
        sx, sy = vw / self.W, vh / self.H
        if abs(z - 1) < 1e-3 and (sw, sh) == (self.W, self.H):
            frame = src.copy()
        else:
            frame = src.transform((self.W, self.H), Image.AFFINE, (sx, 0, x0, 0, sy, y0), resample=Image.BILINEAR)
        to_out = lambda x, y: ((x * fx - x0) / sx, (y * fy - y0) / sy)
        layer = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        hl = self.h["highlight"]
        for s in seg["steps"]:
            if not s.get("box"):
                continue
            st = s["st"]
            show = st.get("highlight", hl["enabled"] and s["do"] not in ("goto", "scroll", "wait", "none", "press")
                          or bool(st.get("focus")))
            if not show and not st.get("callout") and not st.get("spotlight"):
                continue
            # Fully shown from a0 to a1; eases in over fin before a0 and out over fout after a1.
            # Clicks: in well before the tap, out right after it (the page often changes next).
            # Typing: out once the text is typed (the layout may shift after, e.g. auto-fill).
            fin, fout = hl.get("fade_in", 0.45), hl.get("fade_out", 0.3)
            if s["do"] in ("click", "dblclick") and not st.get("focus"):
                a0 = s["t_action"] - hl.get("lead", 0.9)
                a1 = s["t_action"] + 0.1 + (0.8 if st.get("callout") else 0)
            else:
                a0, a1 = s["t_action"] - 0.3, s["t_end"] - 0.1 - fout
                if s["do"] == "type" and st.get("text") and not st.get("secret"):
                    typed = len(str(st["text"])) * self.h["capture"]["type_delay_ms"] / 1000
                    a1 = min(a1, s["t_action"] + typed + 0.5)
            a0 = max(a0, s["t_start"] + fin)
            a1 = max(a1, a0)
            if not (a0 - fin <= t <= a1 + fout):
                continue
            alpha = ease(min(1.0, (t - a0 + fin) / fin, (a1 + fout - t) / fout))
            if alpha <= 0:
                continue
            x, y, w, h = s["box"]
            p = hl["padding"]
            (bx0, by0), (bx1, by1) = to_out(x - p, y - p), to_out(x + w + p, y + h + p)
            r = hl["radius"] * self.k * z
            if st.get("spotlight"):
                dim = Image.new("RGBA", (self.W, self.H), (10, 8, 25, int(130 * alpha)))
                ImageDraw.Draw(dim).rounded_rectangle([bx0, by0, bx1, by1], r, fill=(0, 0, 0, 0))
                layer = Image.alpha_composite(layer, dim)
                d = ImageDraw.Draw(layer)
            if show:
                wd = max(2, round(hl["width"] * self.k))
                d.rounded_rectangle([bx0 - wd, by0 - wd, bx1 + wd, by1 + wd], r + wd,
                                    outline=(*self.c_brand, int(70 * alpha)), width=wd * 3)
                d.rounded_rectangle([bx0, by0, bx1, by1], r, outline=(*self.c_brand, int(255 * alpha)), width=wd)
            if st.get("callout"):
                self._pill(d, st["callout"], (bx0 + bx1) / 2, by0, by1, alpha)
        if seg.get("chapter"):
            self._chapter(d, seg["n"], seg["chapter"], t)
        if seg["cursor"]:
            unit = seg["scale"] * fx / sx  # output px per CSS px
            self._ripples(d, seg, t, to_out, unit)
            pos = self._mouse_at(seg, t)
            if pos:
                self._cursor(layer, *to_out(*pos), unit)
        frame = Image.alpha_composite(frame.convert("RGBA"), layer)
        return frame.convert("RGB"), name

    @staticmethod
    def _mouse_at(seg, t):
        if seg["mode"] == "screenshot":
            cur = [s for s in seg["steps"] if s["t_start"] <= t and s.get("mouse")]
            return cur[-1]["mouse"] if cur else None
        m = seg["mouse"]
        if not m:
            return None
        times = seg.setdefault("_mt", [p[0] for p in m])
        i = bisect.bisect_right(times, t) - 1
        if i < 0:
            return m[0][1:]
        if i >= len(m) - 1 or m[i + 1][0] - m[i][0] > 0.1:  # sparse samples = the mouse was resting
            return m[i][1:]
        a, b = m[i], m[i + 1]
        u = (t - a[0]) / (b[0] - a[0])
        return a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u

    def _ripples(self, d, seg, t, to_out, unit):
        clicks = seg["clicks"] if seg["mode"] == "video" else [
            [s["t_action"] + 0.3, *s["mouse"]] for s in seg["steps"]
            if s.get("mouse") and s["do"] in ("click", "dblclick")]
        for tc, x, y in clicks:
            u = (t - tc) / 0.55
            if 0 <= u <= 1:
                r = 22 * unit * (0.3 + 1.2 * out_ease(u))
                (ox, oy) = to_out(x, y)
                a = 1 - u
                d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=(*self.c_brand, int(90 * a)),
                          outline=(*self.c_brand, int(230 * a)), width=max(2, round(2 * unit)))

    def _cursor(self, layer, x, y, unit):
        size = max(12, round(30 * unit))
        if size not in self.cache:
            big = 8
            pts = [(5, 3), (5, 24), (10.6, 18.6), (14.4, 27), (18.2, 25.3), (14.5, 17.2), (22, 17.2)]
            spr = Image.new("RGBA", (30 * big, 30 * big), (0, 0, 0, 0))
            shadow = Image.new("RGBA", spr.size, (0, 0, 0, 0))
            ImageDraw.Draw(shadow).polygon([(px * big + 4, py * big + 10) for px, py in pts], fill=(0, 0, 0, 90))
            spr = Image.alpha_composite(spr, shadow.filter(ImageFilter.GaussianBlur(10)))
            ImageDraw.Draw(spr).polygon([(px * big, py * big) for px, py in pts], fill=(21, 19, 31, 255),
                                        outline=(255, 255, 255, 255), width=round(1.8 * big))
            self.cache[size] = spr.resize((size, size), Image.LANCZOS)
        spr = self.cache[size]
        hx, hy = 5 * size / 30, 3 * size / 30  # the arrow's tip
        dx, dy = round(x - hx), round(y - hy)
        if dx >= self.W or dy >= self.H or dx + size <= 0 or dy + size <= 0:
            return
        # alpha_composite needs a non-negative destination: crop what sticks out past the edge.
        layer.alpha_composite(spr, dest=(max(0, dx), max(0, dy)), source=(max(0, -dx), max(0, -dy)))

    def _pill(self, d, text, cx, top, bottom, alpha):
        o = self.o
        fnt = self.f("bold", 30 * o)
        k = self.k * o
        tw = d.textlength(text, font=fnt)
        pw, ph = tw + 44 * k, 58 * k
        y = bottom + 16 * k if bottom + 16 * k + ph < self.H - 20 * k else top - 16 * k - ph
        x = min(max(cx - pw / 2, 20 * k), self.W - pw - 20 * k)
        d.rounded_rectangle([x + 3 * k, y + 5 * k, x + pw + 3 * k, y + ph + 5 * k], ph / 2,
                            fill=(0, 0, 0, int(60 * alpha)))
        d.rounded_rectangle([x, y, x + pw, y + ph], ph / 2, fill=(*self.c_brand, int(245 * alpha)))
        d.text((x + pw / 2, y + ph / 2), text, font=fnt, fill=(*self.c_text, int(255 * alpha)), anchor="mm")

    def _chapter(self, d, n, text, t):
        dur = self.h["cards"]["chapter_sec"]
        if t > dur + 0.4:
            return
        u_in, u_out = out_ease((t - 0.2) / 0.45), out_ease((dur + 0.4 - t) / 0.4)
        a = max(0.0, min(u_in, u_out))
        if a <= 0:
            return
        k = self.k * self.o
        f_num, f_txt = self.f("bold", 30 * self.o), self.f("bold", 36 * self.o)
        tw = d.textlength(text, font=f_txt)
        h = 76 * k
        x = 48 * k - (1 - a) * 60 * k
        y = 56 * k if self.h["cards"].get("chapter_position") == "top" else self.H - h - 56 * k
        w = h + 26 * k + tw + 34 * k
        d.rounded_rectangle([x + 3 * k, y + 6 * k, x + w + 3 * k, y + h + 6 * k], 18 * k, fill=(0, 0, 0, int(70 * a)))
        d.rounded_rectangle([x, y, x + w, y + h], 18 * k, fill=(255, 255, 255, int(250 * a)))
        d.rounded_rectangle([x + 10 * k, y + 10 * k, x + h - 10 * k, y + h - 10 * k], 12 * k, fill=(*self.c_brand, int(255 * a)))
        d.text((x + h / 2, y + h / 2), str(n), font=f_num, fill=(255, 255, 255, int(255 * a)), anchor="mm")
        d.text((x + h + 16 * k, y + h / 2), text, font=f_txt, fill=(*self.c_dark, int(255 * a)), anchor="lm")

    def card(self, kind, t, dur):
        img = self.bg.copy()
        d = ImageDraw.Draw(img, "RGBA")
        k, W, H = self.k, self.W, self.H
        if kind == "title":
            kicker = self.shot.get("kicker", "TUTORIAL")
            title = self.shot.get("title", "")
            sub = self.shot.get("subtitle", "")
            items = []
            fk, ft, fs = self.f("bold", 28), self.f("bold", 84), self.f("regular", 40)
            tl = wrap(d, title, ft, W - 360 * k)
            block = 70 * k + len(tl) * 100 * k + (70 * k if sub else 0)
            y = (H - block) / 2
            items.append(("pill", kicker, fk, y))
            y += 80 * k
            for line in tl:
                items.append(("text", line, ft, y))
                y += 100 * k
            if sub:
                items.append(("sub", sub, fs, y + 14 * k))
            out_a = min(1.0, (dur - t) / 0.35) if t > dur - 0.35 else 1.0
            for i, (what, text, fnt, yy) in enumerate(items):
                u = out_ease((t - 0.15 - i * 0.12) / 0.6)
                a = max(0.0, u * out_a)
                dy = (1 - u) * 40 * k
                if what == "pill":
                    tw = d.textlength(text, font=fnt)
                    pw, ph = tw + 40 * k, 50 * k
                    d.rounded_rectangle([(W - pw) / 2, yy + dy, (W + pw) / 2, yy + dy + ph], ph / 2,
                                        fill=(*self.c_accent, int(255 * a)))
                    d.text((W / 2, yy + dy + ph / 2), text, font=fnt, fill=(*self.c_dark, int(255 * a)), anchor="mm")
                else:
                    col = (255, 255, 255, int((255 if what == "text" else 200) * a))
                    d.text((W / 2, yy + dy), text, font=fnt, fill=col, anchor="ma")
        else:
            main = self.shot.get("outro", {}).get("title") or self.h["cards"]["end_text"]
            sub = self.shot.get("outro", {}).get("text", "")
            u = out_ease((t - 0.2) / 0.7)
            d.text((W / 2, H / 2 - 30 * k + (1 - u) * 30 * k), main, font=self.f("bold", 80),
                   fill=(255, 255, 255, int(255 * u)), anchor="mm")
            if sub:
                u2 = out_ease((t - 0.45) / 0.7)
                for i, line in enumerate(wrap(d, sub, self.f("regular", 38), W - 400 * k)):
                    d.text((W / 2, H / 2 + 60 * k + i * 52 * k + (1 - u2) * 20 * k), line, font=self.f("regular", 38),
                           fill=(255, 255, 255, int(210 * u2)), anchor="mm")
            fade = (t - (dur - 0.6)) / 0.6
            if fade > 0:
                d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * min(1, fade))))
        return img

    def watermark(self, img):
        d = ImageDraw.Draw(img, "RGBA")
        fnt = self.f("bold", 30)
        d.rounded_rectangle([self.W - 190 * self.k, 22 * self.k, self.W - 22 * self.k, 74 * self.k], 12 * self.k,
                            fill=(0, 0, 0, 120))
        d.text((self.W - 106 * self.k, 48 * self.k), "DRAFT", font=fnt, fill=(255, 255, 255, 230), anchor="mm")
        return img


# ----------------------------------------------------------------------------- sound

def narration(proj: Path, clips, duration, out: Path) -> None:
    n = int(duration * SR) + SR
    buf = bytearray(n * 2)
    end_prev = 0
    for c in sorted(clips, key=lambda c: c["at"]):
        with wave.open(str(proj / c["file"]), "rb") as w:
            if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2:
                raise SystemExit(f"!! {c['file']} is not 48 kHz mono 16-bit: run voice.py again")
            data = w.readframes(w.getnframes())
        off = int(c["at"] * SR) * 2
        if off < end_prev:
            print(f"!! narration {c['key']} overlaps the line before it by {(end_prev - off) / 2 / SR:.2f}s",
                  file=sys.stderr)
        buf[off:off + len(data)] = data[: max(0, len(buf) - off)]
        end_prev = off + len(data)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(buf[: int(duration * SR) * 2]))


def loudness_filter(src: Path, target: float) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af",
                        f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(re.findall(r"\{[^{}]+\}", r.stderr)[-1])
    if float(m["input_i"]) < -70:
        return "anull"
    return (f"loudnorm=I={target}:TP=-1.5:LRA=11:linear=true:measured_I={m['input_i']}:"
            f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
            f"offset={m['target_offset']}")


def mix(nar: Path, music: Path | None, duration: float, house: dict, out: Path) -> bool:
    """Returns False when there's no narration to measure (voice engine 'silent')."""
    a = house["audio"]
    norm = loudness_filter(nar, a["lufs"])
    inputs = ["-i", str(nar)]
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        duck = ("[m0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=500[m1]" if a["duck"]
                else "[m0]anull[m1]")
        graph = (f"[0:a]{norm},aresample={SR},asplit=2[v][sc];"
                 f"[1:a]aresample={SR},aformat=channel_layouts=mono,volume={a['music_db']}dB,"
                 f"afade=t=in:d=1.0,afade=t=out:st={max(0, duration - 2.5):.2f}:d=2.5,atrim=0:{duration:.3f}[m0];"
                 f"{duck};[v][m1]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[out]")
    else:
        graph = f"[0:a]{norm},aresample={SR},alimiter=limit=0.89[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[out]",
                    "-t", f"{duration:.3f}", "-c:a", "aac", "-b:a", "192k", "-ac", "2", str(out)], check=True)
    return norm != "anull"


def measure(path: Path) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else float("nan")


# ----------------------------------------------------------------------------- captions + review page

def srt(clips, house, out: Path) -> None:
    maxw = house["captions"]["max_words"]
    ts = lambda t: f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(t % 1 * 1000):03d}"
    n, rows = 0, []
    for c in sorted(clips, key=lambda c: c["at"]):
        words = c["text"].split()
        chunks = [words[i:i + maxw] for i in range(0, len(words), maxw)]
        total = sum(len(" ".join(ch)) for ch in chunks) or 1
        t = c["at"]
        for ch in chunks:
            d = c["dur"] * len(" ".join(ch)) / total
            n += 1
            rows.append(f"{n}\n{ts(t)} --> {ts(t + d)}\n{' '.join(ch)}\n")
            t += d
    out.write_text("\n".join(rows), encoding="utf-8")


def storyboard(proj: Path, shot: dict, tl: dict, video: Path, thumbs: dict) -> Path:
    rows = []
    for seg in tl["segments"]:
        if seg["kind"] != "scene":
            label = "Title card" if seg["kind"] == "title" else "End card"
            key = "intro" if seg["kind"] == "title" else "outro"
            say = next((c["text"] for c in tl["clips"] if c["key"] == key), "")
            rows.append(f'<tr data-t="{seg["start"]:.2f}"><td class="t">{fmt(seg["start"])}</td><td>'
                        f'<img src="thumbs/{key}.jpg"></td><td><b>{label}</b></td><td>{html.escape(say)}</td></tr>')
            continue
        rows.append(f'<tr class="scene"><td colspan="4">Scene {seg["n"]} · <b>{html.escape(seg["id"])}</b> '
                    f'{html.escape(seg["title"])} <span>({seg["mode"]}, {seg["dur"]:.1f}s)</span></td></tr>')
        for s in seg["steps"]:
            st = s["st"]
            what = st.get("do", "none")
            tgt = st.get("target") or st.get("url") or st.get("focus") or ""
            extra = " · ".join(x for x in [f"zoom ×{s['zoom']:.1f}" if s["zoom"] else "",
                                           f"callout “{st['callout']}”" if st.get("callout") else ""] if x)
            t = seg["start"] + s["t_start"]
            rows.append(f'<tr data-t="{t:.2f}"><td class="t">{fmt(t)}<br><small>{s["key"]}</small></td>'
                        f'<td><img src="thumbs/{s["key"]}.jpg"></td>'
                        f'<td><code>{html.escape(what)}</code> {html.escape(tgt)}<br><small>{html.escape(extra)}</small></td>'
                        f'<td>{html.escape(st.get("say", ""))}</td></tr>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(shot.get('title', 'Storyboard'))}</title>
<style>body{{font:15px/1.45 system-ui,sans-serif;margin:0;background:#f4f4f8;color:#1b1640}}
header{{position:sticky;top:0;background:#1b1640;color:#fff;padding:12px 16px;display:flex;flex-wrap:wrap;gap:12px 20px;align-items:center;z-index:2}}
header video{{width:min(480px,100%);max-height:60vh;border-radius:8px;background:#000}} header div{{flex:1 1 240px}}
@media (max-width:700px){{header{{position:static}} img{{max-width:140px}} td{{padding:6px}}}} h1{{font-size:20px;margin:0}} header p{{margin:4px 0 0;opacity:.75}}
table{{border-collapse:collapse;width:100%;max-width:1200px;margin:16px auto;background:#fff}}
td{{padding:8px 12px;border-bottom:1px solid #eee;vertical-align:top}} td.t{{white-space:nowrap;color:#5a46d6;font-weight:600}}
tr[data-t]{{cursor:pointer}} tr[data-t]:hover{{background:#f0eeff}} tr.scene td{{background:#ece9ff;font-size:14px}}
tr.scene span{{color:#666}} img{{max-width:240px;max-height:300px;border-radius:6px;display:block}} small{{color:#888}} code{{background:#eee;padding:1px 5px;border-radius:4px}}</style></head>
<body><header><video src="{video.name}" controls></video><div><h1>{html.escape(shot.get('title', ''))}</h1>
<p>{fmt(tl['duration'])} · click a row to jump there · give feedback by time or step key (e.g. “s02.1: say it slower”)</p></div></header>
<table>{''.join(rows)}</table>
<script>const v=document.querySelector('video');document.querySelectorAll('tr[data-t]').forEach(r=>r.onclick=()=>{{v.currentTime=+r.dataset.t+0.05;v.play()}});</script>
</body></html>"""
    out = video.parent / "storyboard.html"
    out.write_text(page, encoding="utf-8")
    return out


# ----------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--draft", action="store_true")
    g.add_argument("--final", action="store_true")
    ap.add_argument("--music", type=Path, help="background music (default: shotlist 'music')")
    ap.add_argument("--captions", action=argparse.BooleanOptionalAction, help="burn captions into the picture")
    a = ap.parse_args()

    proj = style.project_dir(a.project)
    house = style.load(proj)
    shot = read_json(proj / "shotlist.json")
    voice = read_json(proj / "voice" / "voice.json")
    ex = house["export"]
    W, H = ex["draft"] if a.draft else ex["final"]
    fps = ex["fps"]
    tl = plan(proj, shot, house, voice)
    dur = tl["duration"]
    rdir = proj / "renders"
    (rdir / "thumbs").mkdir(parents=True, exist_ok=True)
    name = "draft" if a.draft else "final"
    out = rdir / f"{name}.mp4"
    music = a.music or (Path(shot["music"]) if shot.get("music") else None)
    if music and not music.is_absolute():
        music = style.ROOT / music
    if music and not music.exists():
        raise SystemExit(f"!! music not found: {music}")

    print(f"Timeline {fmt(dur)} ({len(tl['segments'])} segments, {len(tl['clips'])} narration clips)")
    print("Sound...")
    nar = rdir / ".cache" / "narration.wav"
    narration(proj, tl["clips"], dur, nar)
    snd = rdir / ".cache" / f"{name}.m4a"
    voiced = mix(nar, music, dur, house, snd)
    srt_file = rdir / "captions.srt"
    srt(tl["clips"], house, srt_file)

    burn = house["captions"]["burn_in"] if a.captions is None else a.captions
    vf = []
    if burn:
        c = house["captions"]
        path = srt_file.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
        fs = ",".join([f"FontName={c['font']}", f"FontSize={c['size']}", f"Bold={int(c['bold'])}",
                       f"PrimaryColour={style.ass_color(c['color'])}", f"OutlineColour={style.ass_color(c['outline_color'])}",
                       "BorderStyle=1", f"Outline={c['outline']}", "Shadow=0", f"MarginV={c['margin_v']}"])
        vf = ["-vf", f"subtitles=f='{path}':force_style='{fs}'"]
    enc = ["-c:v", "libx264", "-preset", ex["draft_preset"] if a.draft else ex["preset"],
           "-crf", str(ex["draft_crf"] if a.draft else ex["crf"]), "-pix_fmt", "yuv420p"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-i", str(snd), *vf, *enc,
                           "-c:a", "copy", "-map", "0:v", "-map", "1:a", "-shortest", "-movflags", "+faststart",
                           str(out)], stdin=subprocess.PIPE)
    painter = Painter(house, (W, H), a.draft, shot)
    want_thumbs = {}
    for seg in tl["segments"]:
        if seg["kind"] == "scene":
            for s in seg["steps"]:
                want_thumbs[s["key"]] = seg["start"] + min(s["t_end"] - 0.05, s["t_action"] + 0.5)
        else:
            want_thumbs["intro" if seg["kind"] == "title" else "outro"] = seg["start"] + min(seg["dur"] - 0.5, 1.4)
    thumb_frames = {round(t * fps): k for k, t in want_thumbs.items()}

    total = int(round(dur * fps))
    started, last, prev_last = time.time(), None, None
    seg_i, cams = 0, {}
    segs = tl["segments"]
    for f in range(total):
        t = f / fps
        while seg_i + 1 < len(segs) and t >= segs[seg_i + 1]["start"]:
            prev_last = last
            seg_i += 1
        seg = segs[seg_i]
        lt = t - seg["start"]
        if seg["kind"] == "scene":
            if seg_i not in cams:
                cams[seg_i] = Camera(seg, house)
            img, _ = painter.scene(seg, cams[seg_i], lt)
        else:
            if seg.get("file"):
                if seg_i not in cams:
                    cams[seg_i] = Clip(seg["file"], (W, H), fps)
                img = cams[seg_i].next()
            else:
                img = painter.card(seg["kind"], lt, seg["dur"])
        if prev_last is not None and seg_i > 0 and lt < XFADE:
            img = Image.blend(prev_last, img, ease(lt / XFADE))
        last = img
        if a.draft:
            img = painter.watermark(img.copy())
        if f in thumb_frames:
            th = img.copy()
            th.thumbnail((480, 270) if W >= H else (270, 480))
            th.save(rdir / "thumbs" / f"{thumb_frames[f]}.jpg", quality=80)
        ff.stdin.write(img.tobytes())
        if f % (fps * 5) == 0 and f:
            el = time.time() - started
            print(f"  {fmt(t)} / {fmt(dur)}  ({f / el:.0f} fps, ~{(total - f) / (f / el):.0f}s left)", file=sys.stderr)
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("!! ffmpeg failed")

    timeline = {"duration": round(dur, 3), "size": [W, H], "segments": [
        {k: v for k, v in s.items() if k in ("kind", "id", "title", "chapter", "mode", "start", "dur")} |
        ({"steps": [{"key": st["key"], "at": round(s["start"] + st["t_start"], 2), "say": st["st"].get("say", "")}
                    for st in s["steps"]]} if s["kind"] == "scene" else {}) for s in tl["segments"]]}
    write_json(rdir / "timeline.json", timeline)
    page = storyboard(proj, shot, tl, out, thumbs=want_thumbs)
    lufs = measure(out)
    print(f"\nDone -> {out}  ({fmt(dur)}, {W}x{H}, {time.time() - started:.0f}s)")
    print(f"review page -> {page}")
    print(f"captions -> {srt_file}{' (burned in)' if burn else ''}")
    if not voiced:
        print("-- no narration audio (voice engine 'silent'): loudness not checked")
    else:
        ok = abs(lufs - house['audio']['lufs']) <= 1.5
        print(f"{'ok' if ok else '!!'} loudness {lufs:.1f} LUFS (target {house['audio']['lufs']})")
    data = read_json(proj / "project.json")
    data["stage"] = "draft-review" if a.draft else "delivered"
    write_json(proj / "project.json", data)


if __name__ == "__main__":
    main()
