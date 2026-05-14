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

- **Dark surface tokens** — Midnight Ink, Onyx Velvet, Carbon Mist, Pen Stroke (`--ds-midnight-ink`, `--ds-onyx-velvet`, `--ds-carbon-mist`, `--ds-pen-stroke`)
- **Warm paper surface tokens** — Warm Paper, Parchment, Aged Paper (`--ds-warm-paper`, `--ds-parchment`, `--ds-aged-paper`)
- **Text role tokens** — primary, secondary, tertiary, inverse (`--ds-text-*`)
- **Accent tokens** — warm gold accent, muted, subtle alpha (`--ds-accent`, `--ds-accent-muted`, `--ds-accent-subtle`)
- **Trust signal tokens** — verified (emerald), partial (amber), caveat alpha (`--ds-trust-verified`, `--ds-trust-partial`, `--ds-trust-caveat`)
- **Caution / warning tokens** — `--ds-caution`, `--ds-warning`
- **Elevation tokens** — four shadow stack levels (`--ds-elevation-1` through `--ds-elevation-4`)
- **Motion tokens** — fast/standard/slow durations + standard/decelerate/accelerate easings (`--ds-duration-*`, `--ds-easing-*`)
- **Spacing scale tokens** — `--ds-space-1` through `--ds-space-12`
- **Typography role tokens** — display, heading, subheading, body, label, caption (`--ds-type-*`)

### Tailwind wiring

All `--color-ds-*` entries in `@theme` read from `var(--ds-*)`. No raw hex in `@theme` for design-token entries. Generates Tailwind utilities: `bg-ds-midnight`, `text-ds-accent`, `border-ds-trust`, etc. Existing `--color-*` palette entries and all existing utility classes are unchanged.

### Surface adoption

**None.** No existing surface (Explore, TripBuilder, Saved, AI Concierge, nav, login) has adopted the Card primitive or new design tokens. The primitives are available for future Phase 1+ slices. Existing screens are visually unchanged.

### Reduced-motion

Global `@media (prefers-reduced-motion: reduce)` rule in `@layer base` suppresses all animation/transition durations. This satisfies Design Bible v1.0 §4.13.

---

## References

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
