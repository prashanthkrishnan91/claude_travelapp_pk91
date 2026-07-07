# PR #523 — Atmospheric Background System v1 · Visual validation

## Screenshot status: v2 CAPTURED — warmer palette patch applied

Playwright/Chromium is available in this environment. Auth screens (no Supabase
session required) were captured directly from the running dev server. Authenticated
surfaces cannot be fully driven without a live session; gradient-only reference
shots were generated from synthetic HTML files that replicate the exact CSS values.

### What changed in v2 (user feedback: "reads as beige → blue-gray")

Root causes fixed:
- `--ds-atelier-vignette` was cold `rgba(6,9,14,0.55)` — gave every page cold-blue edges
- `auth-hero` linear-gradient started with cold blue-blacks (`#080e16 → #1a2b3c`)
- `.atelier-atmosphere-root` contained a marine-ink radial `rgba(31,66,86,0.045)` that tinted the shell
- `atelier-wash` brass bloom (32%) was too small at 14px blur — salon read as "mostly black"
- `folio-cinema-shell` local radial was only 14% amber — insufficient toplight

All four fixed: warm-ink vignette, warm cinema gradient base, terracotta-warm shell, 52% brass salon.

---

## Captured before/after screenshots (`docs/visual-proof/pr523/`)

### Auth screens — v2 (live dev server)

| File | Description |
|---|---|
| `before-login-reference.png` | v0 auth-hero — muted/tropical |
| `after-login-desktop.png` | v1 — deep night (#080e16 cold) → dusk blue → amber |
| `after-login-desktop-v2.png` | **v2 CURRENT** — warm ink (#0c0906) → amber-bronze → luminous gold; no blue-gray at all |
| `after-login-mobile-v2.png` | v2 mobile — warm and cinematic; card readable |
| `after-signup-desktop-v2.png` | v2 signup — same warm auth-hero treatment |

### Concierge / salon — atelier-wash (gradient reference comparison)

| File | Description |
|---|---|
| `before-atelier-wash.png` | Old atelier-wash — 32% brass bloom, 14px blur; barely visible warmth; room mostly black |
| `after-atelier-wash.png` | **v2 CURRENT** — 52% amber window-light upper-left, 26% terracotta lower-right, 32% uplighting bottom; warm-ink base; distinct light sources at 8px blur |

### Home / My Trips — library-wash (gradient reference comparison)

| File | Description |
|---|---|
| `before-library-wash.png` | Old `library-wash` — near-flat warm-white (#faf7f0 → #ece4d2); 10% gold barely visible |
| `after-library-wash.png` | **v1/v2** — honey amber (#f5edd8 → #e6d8b8); 28% gold top bloom + 18% olive radial; editorial warmth visible |

### Journey Desk — desk-texture (gradient reference comparison)

| File | Description |
|---|---|
| `before-desk-texture.png` | Old `desk-texture` — flat cream (#f7f3ea), 6% marine barely perceptible |
| `after-desk-texture.png` | **v1/v2** — cool parchment (#eee8da); 14% marine bloom gives cartographic depth |

### Auth-hero gradient isolation (v1 vs v2)

| File | Description |
|---|---|
| `before-auth-hero-gradient.png` | v1 gradient — cold blue-black base clearly visible |
| `after-auth-hero-gradient.png` | **v2** — warm ink base descends to deep amber-bronze; entirely warm palette |

---

## Phase 8N room-canvas coverage diagnosis

The following Phase 8N room canvas classes had **opaque** `background-color` values
that completely blocked the fixed `<AtelierBackdrop>` layer (fixed in v1, preserved in v2):

| Class | Route | Old state | Fix |
|---|---|---|---|
| `.atelier-atrium-neutral` | `/` (Home) | Opaque cream gradient | Top portion semi-transparent (`rgba(245,237,216,0)→0.72`) |
| `.trips-room-canvas` | `/trips` (My Trips) | `background-color: color-mix(linen 80%, warm-paper)` | `background-color: transparent` |
| `.journey-desk-room-canvas` | `/trips/[id]` | `background-color: color-mix(linen 82%, warm-paper)` | `background-color: transparent` |
| `.folio-cinema-shell` | `/concierge`, `/explore` | `background-color: var(--ds-cinema-deep)` | `background-color: transparent`; strengthened warm radials (v2) |
| `.folio-private-desk` | `/saved` | opaque light paper | **NOT changed** — dark backdrop would bleed wrongly through light paper desk |

---

## Manual validation checklist (run on the Vercel preview or `npm run dev`)

- [x] **Login — desktop**: warm ink→amber-bronze gradient; no cold blue-gray; heading/inputs legible (**v2 screenshot captured**)
- [x] **Login — mobile**: warm cinematic atmosphere; card centered and readable (**v2 screenshot captured**)
- [x] **Signup — desktop**: same warm auth-hero treatment applied (**v2 screenshot captured**)
- [x] **Concierge — gradient reference**: salon now has distinct warm light sources; no longer reads as black+blue-gray edge (**v2 gradient reference captured**)
- [ ] **Home — desktop**: warm library-wash honey depth visible above card shelf (**gradient reference captured; live preview needed**)
- [ ] **My Trips — desktop**: transparent room canvas lets library-wash backdrop show (**gradient reference captured**)
- [ ] **Journey Desk — desktop**: desk-texture parchment ground detectable (**gradient reference captured**)
- [ ] **Journey Desk — mobile**: desk wash subtle; workspace readable

### Stacking / readability spot-checks
- [x] Backdrop geometry compiles clean — CSS classes asserted by contract suite (28/28)
- [x] Auth card + text sit at z-10 above auth-hero backdrop — tested
- [x] `atelier-atmosphere-root[data-atelier-backdrop="true"]` strips background so backdrop is the canvas
- [x] Sidebar / main content at z-index:10 above fixed backdrop (CSS model unchanged)
- [x] Vignette token is warm ink (`rgba(10,6,3,0.55)`) — no cold-blue shell edge
- [x] No cold marine tint in `.atelier-atmosphere-root` shell radials

## Test run

| Suite | Result |
|---|---|
| `atmospheric-background-system-v1.test.mjs` (28) | 28/28 ✓ |
| `atmospheric-boutique-art-direction-8n.test.mjs` | 50/50 ✓ |
| TypeScript `noEmit` | 0 errors ✓ |
| `boutique-art-direction-adoption-8nb.test.mjs` | 1 pre-existing failure (test #62, loading skeleton) — unchanged |
| `boutique-visual-composition-8nc.test.mjs` | all pass ✓ |
| `creative-luxury-atrium.test.mjs` | all pass ✓ |
| Zero new failures | ✓ |
