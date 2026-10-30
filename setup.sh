#!/usr/bin/env bash
# Tutorial Studio setup (macOS / Linux). Safe to run again any time.
#   bash setup.sh [claude|gemini|codex|all]
set -euo pipefail
cd "$(dirname "$0")"
AGENT="${1:-all}"

need() {
  if command -v "$1" >/dev/null 2>&1; then echo "[ok] $1"; else echo "[!!] $1 is missing: $2"; MISSING=1; fi
}
MISSING=0
echo "== 1. Tools"
need ffmpeg  "macOS: brew install ffmpeg · Debian/Ubuntu: sudo apt install ffmpeg"
need node    "install Node.js 22+ from https://nodejs.org (or: brew install node)"
need python3 "macOS: brew install python · Debian/Ubuntu: sudo apt install python3 python3-venv"
[ "$MISSING" = 1 ] && { echo "Install the missing tools above, then run this again."; exit 1; }
NODE_MAJOR=$(node --version | sed 's/v\([0-9]*\).*/\1/')
[ "$NODE_MAJOR" -ge 22 ] || { echo "[!!] Node.js 22+ needed (have $(node --version))"; exit 1; }

echo "== 2. Python environment"
PY=.venv/bin/python
if ! [ -x "$PY" ] || ! "$PY" -c "print(1)" >/dev/null 2>&1; then rm -rf .venv; python3 -m venv .venv; fi
"$PY" -m pip install --upgrade pip -q
"$PY" -m pip install -r requirements.txt -q

echo "== 3. Browser for filming"
"$PY" -m playwright install chromium

echo "== 4. Voice model (Kokoro, ~330 MB, first run only)"
export HYPERFRAMES_PYTHON="$PWD/$PY"
echo "Ready." > /tmp/tts-test.txt
npx --yes hyperframes@0.8.172 tts /tmp/tts-test.txt -o /tmp/tts-test.wav

echo "== 5. Skills and sub-agents for your AI agent"
"$PY" scripts/install_agent.py --agent "$AGENT"

echo "== 6. Check"
"$PY" scripts/doctor.py --quick
echo "All set. Open this folder in your AI agent and say: 'Make a tutorial of <app> showing how to <task>'"
