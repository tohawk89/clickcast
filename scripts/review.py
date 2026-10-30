"""Reviewer: comments and approvals on a draft, part by part, saved in the project.

Usage:
  .venv\\Scripts\\python.exe scripts\\review.py <project>               # open the storyboard to comment
      [--port 8740] [--no-open]
  .venv\\Scripts\\python.exe scripts\\review.py <project> --list        # what the user said (for the agent)
  .venv\\Scripts\\python.exe scripts\\review.py <project> --done s02.1="zoom removed" --done s03

Serving: renders/storyboard.html on http://127.0.0.1:<port>/ (this computer only). Every comment
and Approve click is saved as it happens to projects/<name>/review.json, one item per key: a
part (intro, s01, ..., outro), a step (s01.2) or _general. Keep it running while the user reviews;
stop it with Ctrl+C. Opened as a plain file instead, the page keeps comments in the browser and
offers "Copy feedback" to paste into chat.

--list prints the open comments with their time and narration, which parts are approved, and
which were approved but have changed since (approval is tied to the part's content, so a
re-render of an approved part asks for a new look). --done marks comments as fixed, optionally
with a short reply the user sees next to the comment in the next draft.
"""

import argparse
import json
import re
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

import style
from style import read_json, write_json

KEY = re.compile(r"^[\w.\-]{1,64}$")
TYPES = {".html": "text/html; charset=utf-8", ".json": "application/json", ".mp4": "video/mp4",
         ".jpg": "image/jpeg", ".png": "image/png", ".srt": "text/plain; charset=utf-8", ".css": "text/css"}


def load(proj: Path) -> dict:
    f = proj / "review.json"
    data = read_json(f) if f.exists() else {}
    data.setdefault("items", {})
    return data


def apply(item: dict, patch: dict) -> dict:
    """Same rules as the page: a changed comment is open again; an empty one is removed."""
    if "comment" in patch:
        text = str(patch["comment"]).strip()[:4000]
        if not text:
            for k in ("comment", "status", "reply"):
                item.pop(k, None)
        elif text != item.get("comment"):
            item.update(comment=text, status="open")
    if "approved" in patch:
        if patch["approved"]:
            item.update(approved=True, sig=str(patch.get("sig", ""))[:32])
        else:
            item.pop("approved", None)
            item.pop("sig", None)
    item["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return item


def serve(proj: Path, port: int, open_browser: bool) -> None:
    rdir = (proj / "renders").resolve()
    if not (rdir / "storyboard.html").exists():
        raise SystemExit("!! no storyboard yet: run build.py --draft first")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _local(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                self.send_error(403)
                return False
            return True

        def _json(self, data, code=200):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._local():
                return
            path = urlparse(self.path).path
            if path == "/api/review":
                return self._json(load(proj))
            f = (rdir / unquote(path.lstrip("/") or "storyboard.html")).resolve()
            if not f.is_relative_to(rdir) or not f.is_file() or ".cache" in f.relative_to(rdir).parts:
                return self.send_error(404)
            self._file(f)

        def _file(self, f: Path):
            size = f.stat().st_size
            start, end, code = 0, size - 1, 200
            m = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
            if m and size:  # browsers need byte ranges to seek in a video
                if m[1]:
                    start, end = int(m[1]), min(int(m[2]) if m[2] else size - 1, size - 1)
                else:
                    start = max(0, size - int(m[2] or 0))
                if start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                code = 206
            self.send_response(code)
            self.send_header("Content-Type", TYPES.get(f.suffix.lower(), "application/octet-stream"))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(end - start + 1))
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            try:
                with f.open("rb") as fh:
                    fh.seek(start)
                    left = end - start + 1
                    while left > 0:
                        chunk = fh.read(min(1 << 16, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def do_POST(self):
            if not self._local():
                return
            if urlparse(self.path).path != "/api/review":
                return self.send_error(404)
            try:
                patch = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 65536)))
                key = patch.pop("key")
                assert isinstance(key, str) and KEY.match(key)
            except Exception:
                return self.send_error(400)
            data = load(proj)
            item = apply(data["items"].setdefault(key, {}), patch)
            if not item.keys() - {"at"}:
                del data["items"][key]
            write_json(proj / "review.json", data)
            self._json(item)

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"Review page -> {url}   (comments save to {proj / 'review.json'}; Ctrl+C to stop)", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def fmt(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def show(proj: Path) -> None:
    data, tl_file = load(proj), proj / "renders" / "timeline.json"
    if not tl_file.exists():
        raise SystemExit("!! no timeline yet: run build.py --draft first")
    tl = read_json(tl_file)
    items = data["items"]
    parts = [s for s in tl["segments"] if "key" in s]
    steps = {st["key"]: (st, s) for s in parts for st in s.get("steps", [])}
    ok, stale, todo = [], [], []
    for s in parts:
        it = items.get(s["key"], {})
        (ok if it.get("approved") and it.get("sig") == s["sig"] else stale if it.get("approved") else todo).append(s["key"])
    print(f"Review of {proj.name}: {len(ok)} of {len(parts)} parts approved")
    print(f"  approved: {', '.join(ok) or '-'}")
    if stale:
        print(f"  approved, but changed since (ask for a new look): {', '.join(stale)}")
    print(f"  not approved yet: {', '.join(todo) or '-'}")
    order = [s["key"] for s in parts] + list(steps) + ["_general"]
    rank = lambda k: (order.index(k.split(".")[0]) if k.split(".")[0] in order else len(order), order.index(k) if k in order else 0)
    opened = sorted((k for k, it in items.items() if it.get("status") == "open"), key=rank)
    done = sorted((k for k, it in items.items() if it.get("status") == "done"), key=rank)
    print(f"\nOpen comments ({len(opened)}):" if opened else "\nNo open comments.")
    for k in opened:
        if k in steps:
            st, s = steps[k]
            where = f"step at {fmt(st['t'])} in {s['key']} (full video {fmt(st['at'])})"
            print(f"  {k}: {items[k]['comment']}\n      {where}; narration: \"{st['say']}\"" if st["say"] else
                  f"  {k}: {items[k]['comment']}\n      {where}; no narration")
        else:
            print(f"  {k}: {items[k]['comment']}" + ("   (whole part)" if k != "_general" else "   (whole video)"))
    if done:
        print(f"\nFixed earlier: {', '.join(done)}")
    if len(ok) == len(parts) and not opened:
        print("\nEverything is approved: the draft passes GATE 2 (confirm with the user, then build.py --final).")


def mark_done(proj: Path, specs: list[str]) -> None:
    data = load(proj)
    for spec in specs:
        key, _, reply = spec.partition("=")
        it = data["items"].get(key)
        if not it or not it.get("comment"):
            print(f"!! {key}: no comment to mark as fixed", file=sys.stderr)
            continue
        it["status"] = "done"
        if reply.strip():
            it["reply"] = reply.strip()[:300]
        print(f"fixed: {key}" + (f" ({it['reply']})" if it.get("reply") else ""))
    write_json(proj / "review.json", data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--port", type=int, default=8740)
    ap.add_argument("--no-open", action="store_true", help="don't open the browser")
    ap.add_argument("--list", action="store_true", help="print approvals and open comments")
    ap.add_argument("--done", action="append", metavar='KEY[="reply"]', help="mark a comment as fixed")
    a = ap.parse_args()
    proj = style.project_dir(a.project)
    if a.done:
        mark_done(proj, a.done)
    if a.list:
        show(proj)
    if not (a.done or a.list):
        serve(proj, a.port, not a.no_open)


if __name__ == "__main__":
    main()
