# PR #523 — Atmospheric Background System v1 · Visual validation

## Screenshot status: NOT captured in this environment

Static screenshots could **not** be produced in the Claude-Code-on-the-web
execution environment, and this PR does **not** claim visual validation is
complete. Reasons:

- No system browser is installed in the container.
- The Playwright/Chromium download is blocked by the environment's network
  policy (`Failed to download Chrome for Testing … Download failure`).
- The authenticated surfaces (home, my trips, concierge, explore, saved,
  journey desk) redirect to `/auth/login` without a live Supabase session +
  backend data, neither of which exists in this preview.

What **is** available as evidence:

- The **Vercel preview deployment** for this branch is live and **Ready** — the
  `/auth/login` and `/auth/signup` screens render fully there (no backend
  needed), and the authenticated surfaces render there with a Supabase session.
- `tsc --noEmit` clean, `next build` green, new contract suite 25/25, Phase 8N
  preserved 50/50, zero new regressions across 11 shell/surface test files.

## Manual validation checklist (run on the Vercel preview or `npm run dev`)

For each surface, confirm: (a) atmosphere is present and is **not** flat beige /
not the old tropical rainbow; (b) text and cards remain clearly readable; (c)
no layout shift on load; (d) mobile crop looks intentional.

### Required shots (to attach when a browser is available)
- [ ] **Login — desktop** (`/auth/login`, ~1440px): cinematic dusk auth-hero
      behind the card; heading/inputs legible; no rainbow gradient.
- [ ] **Login — mobile** (`/auth/login`, 375px): hero crop intentional; card
      centered and readable.
- [ ] **Home or My Trips — desktop** (`/` or `/trips`): warm `library-wash`
      editorial depth (not flat beige); trip cards calm and readable.
- [ ] **Concierge / Explore / Saved — desktop** (`/concierge`, `/explore`,
      `/saved`): richer `atelier-wash` atelier mood; dense UI still legible.
- [ ] **Journey Desk — desktop** (`/trips/<id>`): restrained `desk-texture`
      wash behind the paper desk; Brief card shows the lightest `brief-texture`
      wash (rendered via the shared `AtelierBackdrop`, not a one-off gradient);
      itinerary cards fully readable.
- [ ] **Journey Desk — mobile** (`/trips/<id>`, 375px): desk wash subtle;
      workspace switcher + cards readable.

### Stacking / readability spot-checks
- [ ] Backdrop is visible on each surface (not hidden behind the body canvas).
- [ ] Page chrome (sidebar/floating nav) and all content sit above the backdrop.
- [ ] Auth card + text sit above the auth-hero backdrop.
- [ ] No content is dimmed/occluded by a backdrop layer.

## Acceptance-criteria trace
- No arbitrary/stock/cartoon/vector/AI-fantasy imagery; no hotlinked images;
  no readable text/logos in assets — enforced by the registry (`image: null`)
  and `public/atmosphere/MANIFEST.md`, asserted by
  `tests/atmospheric-background-system-v1.test.mjs`.
- Paper Folio identity preserved (Phase 8N suite 50/50).
