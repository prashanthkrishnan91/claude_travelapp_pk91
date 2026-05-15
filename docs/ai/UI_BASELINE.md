# UI Baseline

Last updated: 2026-05-15

## Purpose

Tracks the state of the design system and UI primitive layer so future prompts and PRs can reason accurately about what exists and what has been adopted.

---

## Stage 3.5 Phase 1B — Explore Result-Card Adoption — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — Explore result cards · Restaurants, Hotels, Attractions**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/explore/RestaurantExploreFlow.tsx` | `RestaurantCard` adopts `Card` primitive (dark tone, article element, card-lift). Icon → `ds-accent-subtle` bg + `ds-accent` text. Title → `text-ds-text`. Category/address → `text-ds-text-tertiary`. Google Maps link → `bg-ds-carbon` / hover `bg-ds-pen-stroke`. Rating star → `text-ds-accent fill-current`. Review count → `text-ds-text-tertiary`. Tags → `border-ds-pen-stroke text-ds-text-tertiary`. TrustStrip rendered when Google Place source (`providerPlaceId`/`placeId`). Skeleton → Card primitive + `bg-ds-pen-stroke` bars. Empty/idle text → `text-ds-text-tertiary`. Error → `text-ds-warning`. |
| `frontend/src/components/explore/HotelExploreFlow.tsx` | `HotelCard` adopts `Card` primitive (dark tone). Same icon/text token treatment. TrustStrip rendered when `googlePlaceId` present. Compare prices link → `text-ds-accent` + `ds-accent-subtle` bg (inline style). All legacy `violet-*` / `amber-*` / `cream-*` replaced. |
| `frontend/src/components/explore/AttractionExploreFlow.tsx` | `AttractionCard` adopts `Card` primitive (dark tone). Same icon/text treatment. TrustStrip on `googlePlaceId`. Legacy `blue-*` / `amber-*` / `cream-*` replaced. |
| `frontend/src/components/explore/ResultActionSheet.tsx` | Save button idle: `bg-ds-carbon text-ds-text-tertiary`. Save button saved: `ds-accent-subtle` bg (inline) + `text-ds-accent`. More button: `bg-ds-carbon text-ds-text-tertiary`. Expanded links: `bg-ds-carbon text-ds-text-secondary`. Error: `text-ds-warning`. Outer `mt-2` removed (spacing now from `Card.Actions className="mt-3"`). All save/unsave/expand handlers preserved exactly. |

### Design contract alignment

- **Card primitive adopted:** All 3 Explore result card types wrap with `<Card tone="dark" as="article" className="card-lift">`. Card.Identity, Card.Trust, Card.Meta, Card.Actions slots used.
- **TrustStrip adopted:** Rendered with `sourceCount={1}` where Google Place ID confirms Google Places provenance. `verified` prop intentionally omitted — OPERATIONAL status not explicitly confirmed in frontend payload (contract §23 compliance).
- **Token alignment:** All card surfaces reference `--ds-*` tokens. No raw hex in card renderers. Icon bg uses `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` (CSS var direct, not Tailwind wiring since `--color-ds-accent-subtle` not yet in `@theme`). Rating accent unified to `text-ds-accent` (sandstone gold) across all card types.
- **Forbidden patterns removed:** Legacy `amber-*`, `violet-*`, `blue-*`, `cream-*`, `rose-*`, `white/[.0X]` color utilities removed from result cards.
- **Accessibility:** All interactive elements (Maps link, Compare prices, Save, More) have `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. Semantic `as="article"` on card root. Icon containers marked `aria-hidden="true"`.
- **Motion:** `card-lift` hover class preserved (translateY -2px, within motion contract). `transition-colors` used on interactive elements (120ms via global css). No new animation added.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule in `@layer base` governs all transitions (shipped Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, or backend files changed.
- No Supabase SQL required.
- No new dependencies added.
- No route, auth/session, or data contract changes.
- Search form fields (MapPin, Calendar, Tag icons) retain legacy `text-cream-500` — search forms are explicitly out of scope.
- All action handlers (save, unsave, expand, Manage in Saved link) preserved exactly.
- Add-to-trip, save, maps, compare-prices payloads and routes unchanged.

### Limitation note

`--ds-accent-subtle` (rgba alpha) is defined in `:root` but not wired into `@theme`. Icon backgrounds and compare-prices/save-saved button backgrounds use `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` directly. Adding `--color-ds-accent-subtle` to `@theme` is a logical Phase 1B+ follow-up if Tailwind utility is needed broadly.

---

## Stage 3.5 Phase 1A — App Shell & Navigation Frame — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — first visible surface adoption · Shared shell/navigation only**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/globals.css` | Body bg → `var(--ds-midnight-ink)` (solid, replaces purple gradient). Body/heading color → `var(--ds-text-primary)`. `.nav-item` → ds-text-tertiary color + ds-accent-subtle active state + ds-accent active color + color-mix hover bg + focus-visible sandstone ring. `.nav-section-label` → Overline token (10px, 600, 0.1em, uppercase). |
| `frontend/src/components/layout/AppShell.tsx` | Removed 3 forbidden glow blobs (radial-gradient ambient blobs). Removed GSAP card entrance animation (420ms exceeded 400ms hard limit). Loading state → `bg-ds-midnight text-ds-text-tertiary`. Removed `text-cream-100` from main content wrapper. |
| `frontend/src/components/layout/Sidebar.tsx` | Replaced `.glass` with `bg-ds-onyx` (ink-ladder elevation). `border-white/[.07]` → `border-ds-pen-stroke`. Brand mark → `bg-ds-carbon text-ds-accent`. Section labels → `.nav-section-label`. User avatar → `bg-ds-carbon text-ds-accent`. All text → ds-text tokens. Sign-out hover → `text-ds-warning`. |
| `frontend/src/components/layout/MobileNav.tsx` | Same glass→onyx treatment for top bar, drawer, bottom tab bar. Brand marks → ds tokens. Tab active state → `text-ds-accent`. "New Trip" FAB → `bg-ds-accent text-ds-text-inverse`. Drawer slide → 200ms (ds-duration-standard). Menu toggle focus ring. |
| `frontend/src/components/layout/PageHeader.tsx` | `text-cream-100` → `text-ds-text`. `text-cream-500` → `text-ds-text-tertiary`. |

### Design contract alignment

- **Forbidden patterns removed:** Glow blobs (§31 "No glow pulses"), GSAP animation >400ms (§7 hard limit), glass on navigation (§8 "No glass on … navigation").
- **Ink-ladder elevation applied:** Body = midnight ink, nav/sidebar = onyx velvet, brand marks = carbon mist (two steps up).
- **Token alignment:** All nav colors reference `--ds-*` tokens. No raw hex in changed files. No legacy `brand-*`, `cream-*`, `dark-*` classes in shell.
- **Accessibility:** Focus ring added to all nav items (2px sandstone-gold, 2px offset). Touch targets preserved. Reduced-motion global rule still governs.
- **Motion:** Nav transitions use `--ds-duration-standard` (200ms) and `--ds-duration-fast` (120ms) via token vars.

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, saved-trip, or backend files changed.
- No Supabase SQL required.
- No new dependencies added (GSAP still in package.json for TripBuilder; no new packages).
- No route, auth/session, or card action behavior changes.
- No new design tokens (`.nav-section-label` uses existing `--ds-type-overline-*` tokens).

### Limitation note

Glass class (`.glass`) is retained in `globals.css` because `TripBuilder.tsx` still references it. Its removal from shell components is the scope-correct change for this phase. TripBuilder glass removal is deferred to the TripBuilder/Itinerary surface adoption phase.

---

## Design Foundation Phase 0 — SHIPPED (2026-05-14)

**Stage 3.5 · Wife-Wow design system foundation · Design Bible v1.0 Phase 0**

### What shipped

| File | Description |
|---|---|
| `frontend/src/app/globals.css` | Design token `:root` block (`--ds-*`) + semantic `@theme` wiring (`--color-ds-*: var(--ds-*)`) + global reduced-motion safety rule |
| `frontend/tailwind.config.ts` | Minimal Tailwind v4 config; theme tokens live in CSS, not JS |
| `frontend/src/components/ui/Card.tsx` | Composable Card primitive shell (root + 7 named slots: Identity, Trust, Media, Why, Meta, Actions, Caveat) |
| `frontend/src/components/ui/TrustStrip.tsx` | TrustStrip primitive (verified, sourceCount, confidence, caveat) |

### Token categories added

All values are Design Bible v1.0 §4 exact. Named palette tokens are defined first; semantic aliases reference them.

**Dark surface tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-midnight-ink` | Midnight Ink | `#0B1320` |
| `--ds-onyx-velvet` | Onyx Velvet | `#0F1A2C` |
| `--ds-carbon-mist` | Carbon Mist | `#1A2538` |
| `--ds-pen-stroke` | Pen Stroke | `#22324A` |

**Warm paper surface tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-warm-paper` | Warm Paper | `#FAF7F0` |
| `--ds-bone` | Bone | `#F1ECE0` |
| `--ds-linen` | Linen | `#E6DECB` |
| `--ds-hairline` | Hairline | `#D9D2C2` |

**Named palette tokens**

| Token | Name | Hex |
|---|---|---|
| `--ds-sandstone-gold` | Sandstone Gold | `#E0B888` |
| `--ds-ember-brass` | Ember Brass / Brass | `#C5944D` |
| `--ds-pearl-cream` | Pearl Cream | `#F2EBDD` |
| `--ds-cream` | Cream | `#E8E2D4` |
| `--ds-mist` | Mist | `#9AA4B2` |
| `--ds-verified-sage` | Verified Sage | `#88A899` |
| `--ds-caution-amber` | Caution Amber | `#E8B26B` |
| `--ds-whisper-coral` | Whisper Coral | `#D88478` |
| `--ds-slate` | Slate | `#4A5568` |
| `--ds-ink-paper` | Ink Paper | `#1F2530` |

**Semantic role aliases** (reference named tokens):
- Text: `--ds-text-primary` → Pearl Cream, `--ds-text-secondary` → Cream, `--ds-text-tertiary` → Mist, `--ds-text-inverse` → Ink Paper
- Accent: `--ds-accent` → Sandstone Gold, `--ds-accent-muted` → Ember Brass
- Trust: `--ds-trust-verified` → Verified Sage, `--ds-trust-partial` → Caution Amber
- Caution / warning: `--ds-caution` → Caution Amber, `--ds-warning` → Whisper Coral

**Elevation tokens** — four shadow stack levels (`--ds-elevation-1` through `--ds-elevation-4`)

**Motion tokens** — fast/standard/slow durations + standard/decelerate/accelerate easings (`--ds-duration-*`, `--ds-easing-*`)

**Spacing scale tokens — Design Bible v1.0 §4 complete**

| Token | px |
|---|---|
| `--ds-space-1` | 4px |
| `--ds-space-2` | 8px |
| `--ds-space-3` | 12px |
| `--ds-space-4` | 16px |
| `--ds-space-5` | 20px |
| `--ds-space-6` | 24px |
| `--ds-space-8` | 32px |
| `--ds-space-10` | 40px |
| `--ds-space-12` | 48px |
| `--ds-space-16` | 64px |

**Typography role tokens — Design Bible v1.0 §4.4 complete**

| Token prefix | Size / Line-height | Weight | Notes |
|---|---|---|---|
| `--ds-type-display-xl-*` | 64px / 68px | 700 | tracking −0.03em |
| `--ds-type-display-l-*` | 44px / 50px | 700 | tracking −0.025em |
| `--ds-type-display-m-*` | 32px / 38px | 700 | tracking −0.02em |
| `--ds-type-display-s-*` | 24px / 30px | 600 | tracking −0.015em |
| `--ds-type-body-l-*` | 18px / 28px | 400 | |
| `--ds-type-body-*` | 15px / 24px | 400 | |
| `--ds-type-body-s-*` | 13px / 20px | 400 | |
| `--ds-type-caption-*` | 12px / 16px | 400 | |
| `--ds-type-overline-*` | 10px / 14px | 600 | `text-transform: uppercase`, tracking 0.1em |
| `--ds-type-mono-*` | 12px / 16px | 400 | monospace role |
| `--ds-type-quote-*` | 18px / 28px | 400 | `font-style: italic` |

Backward-compatible aliases preserved: `--ds-type-display-*`, `--ds-type-heading-*`, `--ds-type-subheading-*`, `--ds-type-label-*` (reference the new named tokens above).

### Tailwind wiring

All `--color-ds-*` entries in `@theme` read from `var(--ds-*)`. No raw hex in `@theme` for design-token entries. Generates Tailwind utilities including: `bg-ds-midnight`, `bg-ds-onyx`, `bg-ds-paper`, `text-ds-text`, `text-ds-trust`, `text-ds-caution`, `border-ds-pen-stroke`, `border-ds-hairline`, `text-ds-accent`, `text-ds-accent-deep`, etc. Existing `--color-*` palette entries and all existing utility classes are unchanged.

### Primitive token usage

- `Card.tsx` dark tone uses: `bg-ds-onyx border-ds-pen-stroke text-ds-text`
- `Card.tsx` paper tone uses: `bg-ds-paper border-ds-hairline text-ds-text-inverse`
- `TrustStrip.tsx` verified uses: `text-ds-trust` (Verified Sage)
- `TrustStrip.tsx` high confidence uses: `text-ds-trust`
- `TrustStrip.tsx` medium confidence uses: `text-ds-caution` (Caution Amber)
- `TrustStrip.tsx` low confidence / caveat uses: `text-ds-text-tertiary` (Mist)
- No legacy `emerald-*`, `amber-*`, `cream-*`, `dark-*`, or raw `white/` classes in new primitives.

### Surface adoption

**None.** No existing surface (Explore, TripBuilder, Saved, AI Concierge, nav, login) has adopted the Card primitive or new design tokens. The primitives are available for future Phase 1+ slices. Existing screens are visually unchanged.

### Reduced-motion

Global `@media (prefers-reduced-motion: reduce)` rule in `@layer base` suppresses all animation/transition durations. This satisfies Design Bible v1.0 §4.13.

---

## References

- **Design Implementation Contract v1:** `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md` (exact implementation reference for all design PRs — token values, primitive contracts, visual rules, forbidden patterns, self-audit checks, map styling/interaction, state patterns, accessibility/responsive rules, microinteractions, detail panel/sheet/drawer rules, premium form controls, source/date discipline, future-only ideas guardrails)
- Design Bible v1.0: `artifacts/Travel_Concierge_Design_Bible.pdf` (§04 Visual System, §08 Card Design System, §11 Phase 0, §12 Guardrails, §13 First recommended implementation slice)
- Design Bible Addendum v1.1: `docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md` (§1 private atelier, §5 constraint-first feasibility UX, §6 Phase 0 scope confirmation)
- Roadmap: Stage 3.5 — Wife-Wow design system foundation (`docs/product/ROADMAP.md`)

---

## Pre-Phase 0 baseline (reference only)

Before Phase 0, the UI layer consisted of:
- Tailwind v4 with `@theme` color palette (`--color-sky-*`, `--color-slate-*`, `--color-cream-*`, `--color-dark-*`, `--color-brand-*`, etc.)
- Shared CSS component classes in `globals.css` (`.card`, `.btn-primary`, `.btn-gold`, `.btn-ghost`, `.btn-emerald`, `.input`, `.select`, `.badge-*`, `.skeleton`, `.nav-item`, etc.)
- Four `/ui` components: `CityAutocomplete`, `EmptyState`, `Skeleton`, `StatCard`, `TrustStatusBadge`
- No design token semantic layer
- No composable Card primitive
- No TrustStrip primitive
- No reduced-motion global rule
