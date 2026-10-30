"""Check that everything the pipeline needs is installed and working.

Usage:
  .venv\\Scripts\\python.exe scripts\\doctor.py [--quick]

Prints one line per check: [ok] fine, [!!] must fix (with the fix), [--] optional.
Exit code 0 when nothing must be fixed. --quick skips launching the browser and the voice test.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import install_agent  # noqa: E402
import style  # noqa: E402

ROOT = style.ROOT
WIN = sys.platform == "win32"
PY = r".venv\Scripts\python.exe" if WIN else ".venv/bin/python"
SETUP = "powershell -ExecutionPolicy Bypass -File setup.ps1" if WIN else "bash setup.sh"
problems = 0


def say(level, what, fix=""):
    global problems
    if level == "!!":
        problems += 1
    print(f"[{level}] {what}" + (f"\n     fix: {fix}" if fix else ""))


def version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()

    print("== Python")
    in_venv = Path(sys.prefix).resolve() == (ROOT / ".venv").resolve()
    say("ok" if in_venv else "!!", f"Python {sys.version.split()[0]} ({sys.executable})",
        "" if in_venv else f"run the scripts with {PY} (create it with: {SETUP})")
    for mod, pkg, need in [("playwright", "playwright", True), ("PIL", "pillow", True),
                           ("kokoro_onnx", "kokoro-onnx", True), ("soundfile", "soundfile", True),
                           ("edge_tts", "edge-tts", False)]:
        ok = importlib.util.find_spec(mod) is not None
        if ok:
            say("ok", f"{pkg}")
        elif need:
            say("!!", f"{pkg} missing", f"{PY} -m pip install -r requirements.txt")
        else:
            say("--", f"{pkg} not installed (only for voice engine 'edge': Malay and other languages)",
                f"{PY} -m pip install edge-tts")

    print("== Tools")
    for tool in ["ffmpeg", "ffprobe"]:
        v = version([tool, "-version"]) if shutil.which(tool) else None
        say("ok" if v else "!!", v or f"{tool} not found",
            "" if v else ("winget install Gyan.FFmpeg" if WIN else "brew install ffmpeg / sudo apt install ffmpeg"))
    node = version(["node", "--version"]) if shutil.which("node") else None
    major = int(node.lstrip("v").split(".")[0]) if node else 0
    say("ok" if major >= 22 else "!!", f"Node.js {node}" if node else "Node.js not found",
        "" if major >= 22 else ("winget install OpenJS.NodeJS.LTS" if WIN else "install Node.js 22+ (nodejs.org)") +
        "  (needed for the Kokoro voice via hyperframes)")

    print("== Browser (Camera)")
    house = style.load()
    if not a.quick:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                p.chromium.launch(channel=house["capture"]["browser"]).close()
                say("ok", f"Playwright can drive {house['capture']['browser']}")
            except Exception:
                try:
                    p.chromium.launch().close()
                    say("ok", "Playwright's own Chromium (house browser not found; that's fine)")
                except Exception:
                    say("!!", "no browser Playwright can launch", f"{PY} -m playwright install chromium")

    print("== Voice (Narrator)")
    model = Path.home() / ".cache" / "hyperframes" / "tts" / "models" / "kokoro-v1.0.onnx"
    say("ok" if model.exists() else "--", "Kokoro voice model downloaded" if model.exists()
        else "Kokoro model not downloaded yet (~330 MB, happens on first voice.py run)")
    if not a.quick and major >= 22:
        with tempfile.TemporaryDirectory() as tmp:
            txt, wav = Path(tmp) / "t.txt", Path(tmp) / "t.wav"
            txt.write_text("Ready.", encoding="utf-8")
            r = subprocess.run([style.npx(), "--yes", "hyperframes@0.8.172", "tts", str(txt), "-o", str(wav)],
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                               env={**os.environ, "HYPERFRAMES_PYTHON": sys.executable})
            say("ok" if wav.exists() else "!!", "Kokoro text-to-speech works" if wav.exists()
                else f"Kokoro text-to-speech failed: {(r.stderr or r.stdout)[-200:].strip()}",
                "" if wav.exists() else f"re-run {SETUP}")

    print("== Fonts")
    for weight in ["regular", "bold"]:
        f = style.font(house, weight, 20)
        name = getattr(f, "path", "Pillow default")
        say("ok" if name != "Pillow default" else "--", f"{weight} font: {name}",
            "" if name != "Pillow default" else "set brand.font / brand.font_bold in style.json to a .ttf path")

    print("== Agent setup")
    stamp_ok = False
    for folder in [".claude", ".gemini", ".agents"]:
        s = ROOT / folder / ".tutorial-studio.json"
        if s.exists():
            stamp_ok = True
            fresh = json.loads(s.read_text(encoding="utf-8"))["digest"] == install_agent.digest()
            say("ok" if fresh else "!!", f"{folder}: skills/agents installed" + ("" if fresh else " but STALE"),
                "" if fresh else f"{PY} scripts/install_agent.py")
    if not stamp_ok:
        say("!!", "no agent skills installed", f"{PY} scripts/install_agent.py --agent <claude|gemini|codex|all>")

    print()
    if problems:
        print(f"{problems} thing(s) to fix (see 'fix:' lines above).")
        sys.exit(1)
    print("All set. Try the demo: see ONBOARDING.md step 5.")


if __name__ == "__main__":
    main()
