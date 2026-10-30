"""Create a tutorial project folder.

Usage:
  .venv\\Scripts\\python.exe scripts\\new_project.py <name> --url http://localhost:3000 [--repo PATH] \\
      [--start "npm run dev"] [--audience "new admins"] [--goal "create an invoice"]

Makes projects/<name>/ with project.json (incl. a random anonymous id such as p-7f3a, used in the
shared house FEEDBACK.md instead of the name), notes.md, a local FEEDBACK.md, an empty .env for
demo logins and the folders every role writes into (analysis/, voice/, capture/, assets/, renders/).
"""

import argparse
import json
import secrets
from datetime import date

from style import PROJECTS, write_json

NOTES = """# {name}

## Brief
- Goal: {goal}
- Audience: {audience}
- App: {url}
- Repo: {repo}

## Intake
(the Producer saves the user's answers here: language/voice, length, captions, music, style)

## Approvals
| Date | Gate | What the user said |
|---|---|---|
"""

ENV = """# Demo / test logins used by shotlist.json as ${NAME}. Never put real passwords here.
# DEMO_EMAIL=demo@example.test
# DEMO_PASSWORD=change-me
"""

FEEDBACK = """# Feedback log — {name}

Feedback about this tutorial only, newest first (local, never committed). House-wide lessons go
in the root `FEEDBACK.md` under this project's id.

| Date | What I said | What changed | Scope |
|---|---|---|---|
"""


def new_id():
    """A short random id that means nothing outside this machine."""
    taken = set()
    for f in PROJECTS.glob("*/project.json"):
        try:
            taken.add(json.loads(f.read_text(encoding="utf-8")).get("id"))
        except (OSError, ValueError):
            pass
    while (pid := f"p-{secrets.token_hex(2)}") in taken:
        pass
    return pid


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name", help="kebab-case project name")
    ap.add_argument("--url", required=True, help="where the web app runs (local dev or staging)")
    ap.add_argument("--repo", default="", help="path to the app's source code (for the System Analyst)")
    ap.add_argument("--start", default="", help="command that starts the app, if it isn't running")
    ap.add_argument("--audience", default="new users")
    ap.add_argument("--goal", default="")
    a = ap.parse_args()

    proj = PROJECTS / a.name
    if (proj / "project.json").exists():
        raise SystemExit(f"!! {proj} already exists")
    for sub in ["analysis", "voice", "capture", "assets", "renders"]:
        (proj / sub).mkdir(parents=True, exist_ok=True)
    write_json(proj / "project.json", {
        "id": new_id(), "name": a.name, "url": a.url.rstrip("/"), "repo": a.repo, "start": a.start,
        "audience": a.audience, "goal": a.goal, "created": date.today().isoformat(),
        "stage": "analysis",
    })
    (proj / "notes.md").write_text(NOTES.format(name=a.name, goal=a.goal or "(ask the user)",
                                                audience=a.audience, url=a.url, repo=a.repo or "(none)"),
                                   encoding="utf-8")
    (proj / "FEEDBACK.md").write_text(FEEDBACK.format(name=a.name), encoding="utf-8")
    (proj / ".env").write_text(ENV, encoding="utf-8")
    print(f"created {proj}")


if __name__ == "__main__":
    main()
