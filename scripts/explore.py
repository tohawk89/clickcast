"""System Analyst's crawler: map a running web app's pages, controls and selectors.

Usage:
  .venv\\Scripts\\python.exe scripts\\explore.py <project> [--start /] [--depth 2] [--max-pages 25] [--login]

Opens the app (project.json "url") in a real browser, follows same-origin links breadth-first,
and for every page writes:
  analysis/pages.json     url, title, headings, buttons, links, form fields, each with a stable
                          selector the Director can put in shotlist.json
  analysis/pages/<n>.png  a screenshot to look at
--login runs shotlist.json "setup" (or analysis/login.json) first, so pages behind a sign-in are
reachable. Single-page apps change views without links: also click through them yourself (or with
the browser tools) and note what you find in analysis.md.
"""

import argparse
from collections import deque
from urllib.parse import urljoin, urldefrag, urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

import style
from style import read_json, write_json

MAP_JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 1 && r.height > 1 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const txt = el => (el.innerText || el.value || el.getAttribute('aria-label') || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 80);
  const sel = el => {
    if (el.id) return '#' + CSS.escape(el.id);
    const tid = el.getAttribute('data-testid') || el.getAttribute('data-test');
    if (tid) return `[data-testid="${tid}"]`;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    const t = txt(el);
    if (t && t.length < 40) return `${el.tagName.toLowerCase()}:has-text("${t.replace(/"/g, '\\"')}")`;
    const lab = el.labels && el.labels[0] && el.labels[0].innerText.trim().split('\n')[0];
    if (lab) return `label:has-text("${lab}") >> ${el.tagName.toLowerCase()}`;
    return null;
  };
  const pick = (q, f) => [...document.querySelectorAll(q)].filter(vis).map(f).filter(Boolean);
  return {
    title: document.title,
    headings: pick('h1,h2,h3', el => el.innerText.trim().slice(0, 80)),
    buttons: pick('button,[role=button],input[type=submit]', el => ({ text: txt(el), selector: sel(el) })),
    links: pick('a[href]', el => ({ text: txt(el), href: el.href, selector: sel(el) })),
    fields: pick('input:not([type=hidden]),select,textarea', el => ({
      type: el.type || el.tagName.toLowerCase(), name: el.name || null,
      label: (el.labels && el.labels[0] && el.labels[0].innerText.trim().split('\n')[0]) || el.placeholder || null,
      selector: sel(el) })),
  };
}
"""


def run_steps(page, base, steps):
    for s in steps:
        target = s.get("target")
        if s["do"] == "goto":
            page.goto(urljoin(base + "/", s["url"].lstrip("/")))
        elif s["do"] in ("fill", "type"):
            page.locator(target).first.fill(style.expand(s["text"]))
        elif s["do"] == "click":
            page.locator(target).first.click()
        elif s["do"] == "press":
            page.keyboard.press(s["key"])
        elif s["do"] == "wait":
            page.wait_for_timeout(int(s.get("sec", 1) * 1000))
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except PWTimeout:
            pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--start", default="/", help="first path to open")
    ap.add_argument("--depth", type=int, default=2)
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--login", action="store_true", help="run the setup/login steps first")
    ap.add_argument("--headed", action="store_true", help="show the browser window")
    a = ap.parse_args()

    proj = style.project_dir(a.project)
    style.load_env(proj)
    house = style.load(proj)
    base = read_json(proj / "project.json")["url"].rstrip("/")
    origin = urlparse(base).netloc
    out = proj / "analysis"
    (out / "pages").mkdir(parents=True, exist_ok=True)

    login = []
    if a.login:
        for f in [proj / "shotlist.json", out / "login.json"]:
            if f.exists():
                login = read_json(f).get("setup", [])
                if login:
                    break
        if not login:
            raise SystemExit("!! --login needs a 'setup' list in shotlist.json or analysis/login.json")

    w, h = house["capture"]["viewport"]
    pages, seen = [], set()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel=house["capture"]["browser"], headless=not a.headed)
        except Exception:
            browser = p.chromium.launch(headless=not a.headed)
        page = browser.new_context(viewport={"width": w, "height": h}).new_page()
        if login:
            run_steps(page, base, login)
        queue = deque([(urljoin(base + "/", a.start.lstrip("/")), 0)])
        while queue and len(pages) < a.max_pages:
            url, depth = queue.popleft()
            url = urldefrag(url)[0]
            if url in seen:
                continue
            seen.add(url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_load_state("networkidle", timeout=8000)
            except PWTimeout:
                pass
            except Exception as e:
                pages.append({"url": url, "error": str(e)[:200]})
                continue
            info = page.evaluate(MAP_JS)
            n = len(pages) + 1
            shot = out / "pages" / f"{n:02d}.png"
            page.screenshot(path=str(shot))
            info.update({"n": n, "url": page.url, "screenshot": str(shot.relative_to(proj)).replace("\\", "/")})
            pages.append(info)
            print(f"[{n:02d}] {page.url}  — {info['title']}  ({len(info['buttons'])} buttons, "
                  f"{len(info['fields'])} fields, {len(info['links'])} links)")
            if depth < a.depth:
                for link in info["links"]:
                    u = urldefrag(link["href"])[0]
                    if urlparse(u).netloc == origin and u not in seen and not u.startswith("javascript:"):
                        queue.append((u, depth + 1))
        browser.close()

    write_json(out / "pages.json", pages)
    print(f"\nwrote {out / 'pages.json'} ({len(pages)} pages). Next: read it, look at the screenshots, "
          f"read the source code, then write analysis/analysis.md.")


if __name__ == "__main__":
    main()
