---
name: system-analysis
description: System Analyst skill for Tutorial Studio. Use to understand a web application before a tutorial is written — read its source code, crawl and click through the running app, map features, user flows, roles, data and stable selectors — and write analysis/analysis.md for the Writer and Director.
---

# System analysis — understand the app before anyone writes

Your output is `projects/<name>/analysis/analysis.md` (template: `analysis-template.md` next to
this file). The Writer builds the story from it and the Director picks selectors from it, so
be concrete: real page names, real button labels, real field names, real URLs.

## 1. Read the brief

`projects/<name>/project.json` (url, repo, start, goal, audience) and `notes.md` (intake).
The **goal** decides depth: map the whole app at a glance, and the flows the goal needs in detail.

## 2. Read the code (when `repo` is set)

Work out, without changing anything in the repo:
- **Stack & entry points**: `package.json` / `composer.json` / `requirements.txt` / `Gemfile`, the
  framework, how it starts (dev script), the port.
- **Routes / pages**: e.g. Next.js `app/` or `pages/`, React Router config, Vue router,
  Laravel `routes/web.php`, Django `urls.py`, Rails `config/routes.rb`, Express routers.
- **Features & rules** behind the goal: validation rules, required fields, what happens on
  save, side effects (emails, notifications), feature flags, permissions per role.
- **Auth & roles**: how sign-in works, which roles see what, seeders/fixtures with demo users
  (never copy real credentials anywhere except telling the Producer which demo user exists).
- **Test hooks**: `data-testid`/`data-test` attributes, ids, `name`s — the most stable selectors.
- **Data**: seed data, what the screens look like empty vs filled; anything that varies per
  run (dates, random ids, "2 minutes ago") that could make filming flaky.
- Existing docs: README, `docs/`, help texts, changelogs — reuse their vocabulary.

## 3. Explore the running app

1. Crawl it: `py scripts/explore.py <name> [--login] --depth 2`. Logins need a `setup` list in
   `analysis/login.json` (same step format as the shotlist, e.g.
   `{"setup":[{"do":"goto","url":"/login"},{"do":"fill","target":"#email","text":"${DEMO_EMAIL}"},
   {"do":"fill","target":"#password","text":"${DEMO_PASSWORD}"},{"do":"click","target":"button[type=submit]"}]}`).
   It writes `analysis/pages.json` (headings, buttons, links, fields with selectors) and
   `analysis/pages/NN.png`. Look at the screenshots.
2. Walk the goal's flow by hand with the browser tools your agent has (or `explore.py --headed`):
   every click, every form, what appears after saving, error states, modals, toasts, loading
   times. Single-page apps change views without links, so the crawler won't see them all.
3. For every control the tutorial will touch, note a **stable selector**, in this order of
   preference: `[data-testid=…]`, `#id`, `input[name=…]`, `role=button[name="Save"]`,
   `text=Exact label`, `button:has-text("Save")`. Avoid position-based CSS (`div > div:nth-child(3)`).

## 4. Write analysis.md

Fill the template. Keep it scannable (tables, short bullets). Mark anything you couldn't verify
as **unverified**. In "Risks for filming" list what could break a take: cookie banners, onboarding
tours, slow requests, animations, random data, things that only work once (e.g. a unique email).

## 5. Report back

Return to the Producer in ≤10 lines: the flow you recommend for the goal (as numbered steps), any
blockers, open questions for the user, and the path to `analysis.md`.
