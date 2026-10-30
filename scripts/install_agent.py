"""Install the pipeline's skills, sub-agents and /tutorial command for an AI coding agent.

Usage:
  .venv\\Scripts\\python.exe scripts\\install_agent.py [--agent claude|gemini|codex|all] [--list]

The canonical copies live in pipeline/ (edit those, then run this again):
  pipeline/skills/<skill>/SKILL.md     open SKILL.md format (name + description frontmatter)
  pipeline/agents/<role>.md            sub-agent definitions (name + description frontmatter)
  pipeline/commands/tutorial.md        the /tutorial entry prompt ($ARGUMENTS = the user's words)

Where each agent finds them:
  claude   .claude/skills/  .claude/agents/  .claude/commands/tutorial.md   (+ CLAUDE.md -> AGENTS.md)
  gemini   .agents/skills/  .gemini/agents/  .gemini/commands/tutorial.toml (+ GEMINI.md -> AGENTS.md;
           sub-agents switched on in .gemini/settings.json)
  codex    .agents/skills/  (Codex reads AGENTS.md natively; no sub-agents: it plays the roles)
Any other agent: tell it to read AGENTS.md; the pipeline/ files are plain Markdown it can follow.
"""

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "pipeline"
STAMP = ".tutorial-studio.json"


def digest() -> str:
    h = hashlib.sha1()
    for f in sorted(SRC.rglob("*")):
        if f.is_file():
            h.update(str(f.relative_to(SRC)).encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:12]


def split_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


def copy_skills(dest: Path) -> list[str]:
    names = []
    for skill in sorted(p for p in (SRC / "skills").iterdir() if (p / "SKILL.md").exists()):
        target = dest / skill.name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)
        names.append(skill.name)
    return names


def copy_agents(dest: Path) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for f in sorted((SRC / "agents").glob("*.md")):
        shutil.copy2(f, dest / f.name)
        names.append(f.stem)
    return names


def stamp(folder: Path, what: dict) -> None:
    (folder / STAMP).write_text(json.dumps({"source": "pipeline/", "digest": digest(), **what}, indent=1),
                                encoding="utf-8")


def install_claude() -> str:
    base = ROOT / ".claude"
    skills = copy_skills(base / "skills")
    agents = copy_agents(base / "agents")
    (base / "commands").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / "commands" / "tutorial.md", base / "commands" / "tutorial.md")
    stamp(base, {"agent": "claude", "skills": skills, "agents": agents})
    return f"claude: {len(skills)} skills -> .claude/skills, {len(agents)} sub-agents -> .claude/agents, /tutorial"


def install_shared_skills() -> list[str]:
    skills = copy_skills(ROOT / ".agents" / "skills")
    stamp(ROOT / ".agents", {"agent": "codex+gemini", "skills": skills})
    return skills


def install_gemini() -> str:
    skills = install_shared_skills()
    base = ROOT / ".gemini"
    agents = copy_agents(base / "agents")
    meta, body = split_frontmatter((SRC / "commands" / "tutorial.md").read_text(encoding="utf-8"))
    body = body.replace("$ARGUMENTS", "{{args}}").replace('"""', "'''")
    (base / "commands").mkdir(parents=True, exist_ok=True)
    (base / "commands" / "tutorial.toml").write_text(
        f'description = {json.dumps(meta.get("description", "Make a video tutorial"))}\n'
        f'prompt = """\n{body.strip()}\n"""\n', encoding="utf-8")
    settings_file = base / "settings.json"
    settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}
    settings.setdefault("experimental", {})["enableAgents"] = True
    settings_file.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    stamp(base, {"agent": "gemini", "agents": agents})
    return f"gemini: {len(skills)} skills -> .agents/skills, {len(agents)} sub-agents -> .gemini/agents, /tutorial"


def install_codex() -> str:
    skills = install_shared_skills()
    return f"codex: {len(skills)} skills -> .agents/skills (AGENTS.md is read natively; roles are played in turn)"


def status() -> None:
    d = digest()
    for folder in [ROOT / ".claude", ROOT / ".gemini", ROOT / ".agents"]:
        f = folder / STAMP
        if not f.exists():
            print(f"[--] {folder.name}: not installed")
            continue
        s = json.loads(f.read_text(encoding="utf-8"))
        state = "up to date" if s["digest"] == d else "STALE (pipeline/ changed: run install_agent.py again)"
        print(f"[{'ok' if s['digest'] == d else '!!'}] {folder.name}: {s['agent']}, {state}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", choices=["claude", "gemini", "codex", "all"], default="all")
    ap.add_argument("--list", action="store_true", help="show what is installed and whether it's current")
    a = ap.parse_args()
    if a.list:
        status()
        return
    todo = ["claude", "gemini", "codex"] if a.agent == "all" else [a.agent]
    for agent in todo:
        print({"claude": install_claude, "gemini": install_gemini, "codex": install_codex}[agent]())
    print("Done. Edit pipeline/ (not these copies) and re-run to update.")


if __name__ == "__main__":
    main()
