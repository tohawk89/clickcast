"""Narrator: turn every "say" line in shotlist.json into a voice clip, and time it.

Usage:
  .venv\\Scripts\\python.exe scripts\\voice.py <project> [--engine kokoro|edge|recorded|silent] [--voice ID]

Engines (style.json voice.engine, or the shotlist's "voice" block, or --engine):
  kokoro    local Kokoro-82M via `hyperframes tts` (free, offline; English, Spanish, French, Hindi,
            Italian, Portuguese, Japanese, Chinese). Voices: af_heart, am_michael, bf_emma, ...
  edge      Microsoft Edge online voices via the `edge-tts` package (pip install edge-tts); has
            Malay (ms-MY-YasminNeural, ms-MY-OsmanNeural) and most other languages. Sends the
            narration text to Microsoft.
  recorded  the user's own voice: writes voice/script.md (one line per clip) and reads their
            recordings from voice/rec/<key>.wav|m4a|mp3. Missing clips are listed.
  silent    no audio; durations estimated from word count. For planning and storyboards.

Writes voice/<key>.wav (48 kHz mono) and voice/voice.json {key: {text, file, dur}}. Keys are
"intro", "<scene id>.<step index>" and "outro". Unchanged lines are reused (cached by text+voice).
style.json voice.lexicon {"word": "how to say it"} fixes pronunciation without changing captions.
"""

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import style
from style import read_json, write_json

HF = "hyperframes@0.8.172"


def lines(shot: dict) -> list[tuple[str, str]]:
    out = []
    if shot.get("intro", {}).get("say"):
        out.append(("intro", shot["intro"]["say"]))
    for sc in shot["scenes"]:
        for i, st in enumerate(sc["steps"]):
            if st.get("say"):
                out.append((f"{sc['id']}.{i}", st["say"]))
    if shot.get("outro", {}).get("say"):
        out.append(("outro", shot["outro"]["say"]))
    return out


def to_wav48(src: Path, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "48000",
                    "-c:a", "pcm_s16le", str(dst)], check=True)


def speakable(text: str, lexicon: dict) -> str:
    for word, say in lexicon.items():
        text = text.replace(word, say)
    return text


def tts_kokoro(text: str, out: Path, v: dict) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        txt, wav = Path(tmp) / "line.txt", Path(tmp) / "line.wav"
        txt.write_text(text, encoding="utf-8")
        cmd = [style.npx(), "--yes", HF, "tts", str(txt), "-o", str(wav), "-v", v["voice"], "-s", str(v["speed"])]
        # hyperframes runs Kokoro in Python: use this venv, where setup installs kokoro-onnx.
        env = {**os.environ, "HYPERFRAMES_PYTHON": sys.executable}
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        if r.returncode or not wav.exists():
            raise RuntimeError(f"hyperframes tts failed: {r.stderr[-400:] or r.stdout[-400:]}")
        to_wav48(wav, out)


def tts_edge(text: str, out: Path, v: dict) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mp3 = Path(tmp) / "line.mp3"
        rate = f"{round((float(v['speed']) - 1) * 100):+d}%"
        r = subprocess.run([sys.executable, "-m", "edge_tts", "--voice", v["voice"], "--rate", rate,
                            "--text", text, "--write-media", str(mp3)], capture_output=True, text=True)
        if r.returncode or not mp3.exists():
            raise RuntimeError(f"edge-tts failed (pip install edge-tts?): {r.stderr[-400:]}")
        to_wav48(mp3, out)


def silent(text: str, out: Path, v: dict) -> None:
    dur = 0.35 + len(text.split()) / (2.6 * float(v["speed"]))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                    "-t", f"{dur:.2f}", "-c:a", "pcm_s16le", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--engine", choices=["kokoro", "edge", "recorded", "silent"])
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()

    proj = style.project_dir(a.project)
    house = style.load(proj)
    shot = read_json(proj / "shotlist.json")
    v = {**house["voice"], **shot.get("voice", {})}
    for k in ("engine", "voice", "speed"):
        if getattr(a, k):
            v[k] = getattr(a, k)
    lexicon = v.get("lexicon", {})
    vdir = proj / "voice"
    vdir.mkdir(exist_ok=True)
    index_file = vdir / "voice.json"
    old = read_json(index_file) if index_file.exists() else {}
    todo = lines(shot)

    if v["engine"] == "recorded":
        rec = vdir / "rec"
        rec.mkdir(exist_ok=True)
        (vdir / "script.md").write_text(
            "# Recording script\n\nRecord each line as its own file in `voice/rec/`, named by its key "
            "(e.g. `s01.0.wav`; .m4a/.mp3 also fine). Leave ~0.2 s of silence at both ends.\n\n" +
            "\n".join(f"- **{k}** — {t}" for k, t in todo) + "\n", encoding="utf-8")

    def make(item):
        key, text = item
        sig = hashlib.sha1(f"{v['engine']}|{v['voice']}|{v['speed']}|{speakable(text, lexicon)}".encode()).hexdigest()[:12]
        out = vdir / f"{key}.wav"
        if v["engine"] == "recorded":
            src = next((p for p in sorted((vdir / "rec").glob(f"{key}.*"))), None)
            if not src:
                return key, None, "missing"
            sig = f"rec-{int(src.stat().st_mtime)}-{src.stat().st_size}"
            if old.get(key, {}).get("sig") != sig or not out.exists():
                to_wav48(src, out)
        elif old.get(key, {}).get("sig") != sig or not out.exists():
            {"kokoro": tts_kokoro, "edge": tts_edge, "silent": silent}[v["engine"]](speakable(text, lexicon), out, v)
        else:
            return key, {**old[key], "text": text}, "cached"
        return key, {"text": text, "file": f"voice/{out.name}", "dur": round(style.probe_duration(out), 3), "sig": sig}, "made"

    index, missing = {}, []
    # The first clip runs alone: on a fresh machine it downloads the voice model, which
    # parallel jobs would race on.
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        for key, info, status in [make(todo[0]), *pool.map(make, todo[1:])] if todo else []:
            if info is None:
                missing.append(key)
                continue
            index[key] = info
            print(f"[{status:6}] {key:8} {info['dur']:5.2f}s  {info['text'][:70]}")
    write_json(index_file, index)
    total = sum(i["dur"] for i in index.values())
    print(f"\n{len(index)} clips, {total:.1f}s of narration ({v['engine']}, {v['voice']}) -> {index_file}")
    if missing:
        print(f"!! {len(missing)} recording(s) missing in voice/rec/: {', '.join(missing)}  (script: voice/script.md)")
        sys.exit(1)
    # Clips no longer in the shotlist.
    for f in vdir.glob("*.wav"):
        if f.stem not in index:
            f.unlink()


if __name__ == "__main__":
    main()
