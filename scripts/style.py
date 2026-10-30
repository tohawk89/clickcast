"""House style and shared helpers for every script.

  style.json                     lasting preferences (all tutorials)
  projects/<name>/style.json     overrides for one tutorial only (same keys, any subset)

Command-line flags override both. STYLE.md explains the *why* behind these numbers.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Windows consoles default to a legacy code page; page titles and narration are UTF-8.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"


def _merge(base: dict, over: dict) -> dict:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def project_dir(path: Path | str) -> Path:
    """projects/<name> from a name, the folder itself, or any path inside it."""
    p = Path(path)
    if not p.exists() and (PROJECTS / p).exists():
        p = PROJECTS / p
    p = p.resolve()
    for q in [p, *p.parents]:
        if q.parent == PROJECTS.resolve():
            return q
    if (p / "project.json").exists():
        return p
    raise SystemExit(f"!! {path} is not a project (expected projects/<name>/project.json)")


def load(proj: Path | None = None) -> dict:
    """House style, with the project's overrides applied."""
    style = json.loads((ROOT / "style.json").read_text(encoding="utf-8"))
    if proj and (proj / "style.json").exists():
        _merge(style, json.loads((proj / "style.json").read_text(encoding="utf-8")))
    return style


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


_ENV = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_env(proj: Path) -> None:
    """projects/<name>/.env (KEY=value lines) -> os.environ. Holds demo logins; never committed."""
    env = proj / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def expand(value: str) -> str:
    """'${DEMO_PASSWORD}' -> value from the environment / project .env."""
    def sub(m):
        if m.group(1) not in os.environ:
            raise SystemExit(f"!! ${{{m.group(1)}}} is not set: add it to the project's .env")
        return os.environ[m.group(1)]
    return _ENV.sub(sub, value)


def probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def npx() -> str:
    return shutil.which("npx") or shutil.which("npx.cmd") or "npx"


FONT_FALLBACKS = {
    "regular": ["C:/Windows/Fonts/segoeui.ttf", "/System/Library/Fonts/SFNS.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf", "arial.ttf"],
    "bold": ["C:/Windows/Fonts/segoeuib.ttf", "/System/Library/Fonts/SFNS.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
}


def font(house: dict, weight: str, size: int):
    """A Pillow font: style.json brand.font / brand.font_bold first, then common system fonts."""
    from PIL import ImageFont
    key = "font_bold" if weight == "bold" else "font"
    for cand in [house["brand"].get(key), *FONT_FALLBACKS[weight]]:
        if not cand:
            continue
        p = Path(cand)
        try:
            return ImageFont.truetype(str(ROOT / p if not p.is_absolute() and (ROOT / p).exists() else p), size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def ass_color(hex_str: str) -> str:
    """'#RRGGBB' -> ASS subtitle colour '&H00BBGGRR'."""
    h = hex_str.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}".upper()
