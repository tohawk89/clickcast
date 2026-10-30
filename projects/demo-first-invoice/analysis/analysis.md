# Analysis — Acme Billing (demo app)

_Analyst: example · 2026-10-29 · repo: examples/demo-app · url: http://localhost:8765_

## In one paragraph
A small invoicing app for small businesses: sign in, see invoices with an outstanding total,
create a new invoice (customer, due date, one line item) and save it as a draft. The tutorial's
goal — create and save a first invoice — covers the main flow end to end.

## Stack
| | |
|---|---|
| Framework | static HTML + vanilla JS (`index.html`, `app.html`, `app.css`) |
| Start | `py -3 -m http.server 8765 -d examples/demo-app` → http://localhost:8765 |
| Auth | email + password checked in the page; session in sessionStorage |
| Demo account | `DEMO_EMAIL` / `DEMO_PASSWORD` in the project's .env |

## Pages
| Page | URL | What it's for | Reached from |
|---|---|---|---|
| Sign in | `/` | email + password | start |
| Invoices | `/app.html` (list view) | outstanding total, count, table | after sign-in |
| New invoice | `/app.html` (form view, same URL) | customer, due date, item, qty, price, live total | "+ New invoice" |

## The flow for this goal
| # | Page | Action | Control (label) | Selector | Result |
|---|---|---|---|---|---|
| 1 | Sign in | type | Email | `#email` | |
| 2 | Sign in | type | Password | `#password` | |
| 3 | Sign in | click | Sign in | `button:has-text("Sign in")` | → Invoices |
| 4 | Invoices | click | + New invoice | `#new-invoice` | form view |
| 5 | New invoice | type | Customer | `#customer` | |
| 6 | New invoice | type | Item description | `.item` | |
| 7 | New invoice | type | Price (RM) | `.price` | Total updates live (`#total`) |
| 8 | New invoice | click | Save invoice | `#save` | back to list, toast "Invoice saved", new row status Draft |

## Rules & behaviour the viewer should know
- Qty defaults to 1; total = qty × price. A saved invoice starts as **Draft**.
- Outstanding = sum of invoices not Paid (includes drafts).

## Glossary
Invoice, Customer, Due date, Item, Qty, Price (RM), Total, Outstanding, Draft / Sent / Paid.

## Risks for filming
- Data lives in localStorage: each capture uses a fresh browser profile, so the list always
  starts with the 2 seed invoices. The toast disappears after 2.5 s.

## Open questions
None.
