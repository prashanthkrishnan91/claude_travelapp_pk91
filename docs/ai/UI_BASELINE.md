# UI Baseline

Last updated: 2026-05-14

## Purpose

Tracks the state of the design system and UI primitive layer so future prompts and PRs can reason accurately about what exists and what has been adopted.

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
