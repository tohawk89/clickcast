# Demo app — Acme Billing

A tiny static web app (sign in → invoice list → new invoice) for testing the pipeline and for
onboarding. No server code; data lives in the browser.

    py -3 -m http.server 8765 -d examples/demo-app      # then open http://localhost:8765

Test login (public, fake): `demo@acme.test` / `demo1234`. The finished example project is
`projects/demo-first-invoice/`.
