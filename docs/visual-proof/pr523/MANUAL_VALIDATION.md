# PR #523 — Atmospheric Background System v1 · Visual validation

## Screenshot status: CAPTURED (auth screens) + GRADIENT REFERENCE (authenticated surfaces)

Playwright/Chromium is available in this environment. Auth screens (no Supabase
session required) were captured directly from the running dev server. Authenticated
surfaces cannot be fully driven without a live session; gradient-only reference
shots were generated from synthetic HTML files that replicate the exact CSS values.

---

## Captured before/after screenshots (`docs/visual-proof/pr523/`)

### Auth screens (live dev server, 1440×900 and 390×844)

| File | Description |
|---|---|
| `before-login-reference.png` | Old `auth-hero` gradient — muted dark-to-muted-amber, too cool to read as cinematic |
| `after-login-desktop.png` | **NEW** — deep night (#080e16) → dusk blue → luminous amber (#e0b888); obvious golden-hour atmosphere; grain layer visible |
| `after-login-mobile.png` | Mobile crop; gradient directionality preserved; card centered |
| `after-signup-desktop.png` | Signup reuses same `auth-hero` role; identical cinematic treatment |

### Home / My Trips — library-wash (gradient reference comparison)

| File | Description |
|---|---|
| `before-library-wash.png` | Old `library-wash` — near-flat warm-white (#faf7f0 → #ece4d2); 10% gold radial barely visible; indistinguishable from flat beige |
| `after-library-wash.png` | **NEW** — honey amber (#f5edd8 → #e6d8b8); 28% gold top bloom + 18% olive radial; editorial warmth clearly visible without being distracting; cards pop against the tinted ground |

### Journey Desk — desk-texture (gradient reference comparison)

| File | Description |
|---|---|
| `before-desk-texture.png` | Old `desk-texture` — flat cream (#f7f3ea), 6% marine barely perceptible; could be any plain background |
| `after-desk-texture.png` | **NEW** — cool parchment (#eee8da); 14% marine-ink bloom at top gives cartographic depth; amber corner adds warmth; atmosphere detectable at a glance while staying restrained |

---

## Phase 8N room-canvas coverage diagnosis

The following Phase 8N room canvas classes had **opaque** `background-color` values
that completely blocked the fixed `<AtelierBackdrop>` layer:

| Class | Route | Old state | Fix in this patch |
|---|---|---|---|
| `.atelier-atrium-neutral` | `/` (Home) | Opaque cream gradient via `background-image` | Made top portion semi-transparent (`rgba(245,237,216,0)→0.72`) so `library-wash` bleeds through hero zone |
| `.trips-room-canvas` | `/trips` (My Trips) | `background-color: color-mix(linen 80%, warm-paper)` — fully opaque | `background-color: transparent`; radials only |
| `.journey-desk-room-canvas` | `/trips/[id]` (Journey Desk) | `background-color: color-mix(linen 82%, warm-paper)` — fully opaque | `background-color: transparent`; radials only |
| `.folio-cinema-shell` | `/concierge`, `/explore` | `background-color: var(--ds-cinema-deep)` — opaque dark | `background-color: transparent`; radials only; `atelier-wash` backdrop now the actual canvas |
| `.folio-private-desk` | `/saved` | `background-color: color-mix(linen 78%, ember-brass)` — opaque light | **NOT changed** — Saved uses `atelier-wash` (dark cinema) backdrop but renders as a paper world. Making the dark backdrop bleed through a light paper desk would be wrong. Backdrop role for Saved should be revisited separately. |

---

## Manual validation checklist (run on the Vercel preview or `npm run dev`)

- [x] **Login — desktop**: cinematic golden-hour dusk backdrop; no rainbow gradient; heading/inputs legible above dark scrim (**screenshot captured**)
- [x] **Login — mobile**: hero crop intentional; card centered and readable (**screenshot captured**)
- [x] **Signup — desktop**: same auth-hero treatment applied (**screenshot captured**)
- [ ] **Home — desktop**: warm library-wash honey depth visible above card shelf; trip cards calm and readable (**gradient reference captured; live preview needed for auth surfaces**)
- [ ] **My Trips — desktop**: transparent room canvas lets library-wash backdrop show; paper folio stage lifts off the warm ground (**gradient reference captured**)
- [ ] **Concierge / Explore — desktop**: richer atelier-wash brass bloom; folio-cinema-shell now transparent so the dark backdrop is the actual canvas (**live preview needed**)
- [ ] **Journey Desk — desktop**: desk-texture cool-parchment ground detectable; paper planning folio legible (**gradient reference captured**)
- [ ] **Journey Desk — mobile**: desk wash subtle; workspace switcher + cards readable

### Stacking / readability spot-checks
- [x] Backdrop geometry compiles clean — CSS classes asserted by contract suite
- [x] Auth card + text sit at z-10 above auth-hero backdrop — tested
- [x] `atelier-atmosphere-root[data-atelier-backdrop="true"]` strips background-color/image from shell so backdrop is the canvas
- [x] Sidebar / main content at z-index:10 above fixed backdrop (CSS model unchanged)
- [x] No content dimmed or occluded — scrim opacity unchanged or slightly strengthened

## Test run

| Suite | Result |
|---|---|
| `atmospheric-background-system-v1.test.mjs` (25) | 25/25 ✓ |
| `atmospheric-boutique-art-direction-8n.test.mjs` | 50/50 ✓ |
| `boutique-art-direction-adoption-8nb.test.mjs` | 1 pre-existing failure (test #62, loading skeleton) — unchanged |
| `boutique-visual-composition-8nc.test.mjs` | all pass ✓ |
| `creative-luxury-atrium.test.mjs` | all pass ✓ |
| Zero new failures | ✓ |
