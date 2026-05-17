# Mobile Design Language — Pocket Travel Atelier

**Status:** Active · Phase 8J
**Scope:** App shell, navigation, page containers, and future mobile surfaces.
**Extends:** Design Bible v1.0 + Addendum v1.1 — enforces mobile-specific rules.

---

## Core principle: one screen, one primary job

Every mobile view has one clear purpose. Chrome (nav, headers) is minimal so content can lead. Complexity is progressive — revealed on demand, not upfront.

---

## Visual identity: warm dark atelier

| Layer | Token | Role |
|---|---|---|
| Base | `var(--ds-midnight-ink)` | Body background, nav bars — deepest layer |
| Surface | `var(--ds-onyx-velvet)` | Cards, trays, elevated content |
| Layer 2 | `var(--ds-carbon-mist)` | Secondary cards, inputs |
| Divider | `var(--ds-pen-stroke)` | Borders, hairlines |
| Accent | `var(--ds-sandstone-gold)` | Active states, primary CTAs, key highlights |
| Text primary | `var(--ds-text-primary)` | Headings, key labels |
| Text quiet | `var(--ds-text-tertiary)` | Inactive nav labels, supporting copy |

**Do not** use flat navy, generic SaaS blue, or decorative gradients in shell surfaces.
**Do not** use raw hex values in shell/nav components — reference ds-tokens only.
**Do not** add glass/backdrop-filter to shell nav surfaces.

---

## Bottom navigation

### 4-tab quiet nav (canonical mobile primary nav)

Tabs: **Home · Discover · Saved · My Trips**
- Exactly 4 primary destinations. No more, no fewer.
- "New Trip" is **not** a bottom-nav tab — it is contextual (see Primary Action below).
- Tab order is fixed: Home → Discover → Saved → My Trips.

### Visual spec
- Background: `var(--ds-midnight-ink)` — deepest layer.
- Top border: `1px solid var(--ds-pen-stroke)` with subtle warm brass gradient overlay.
- Active tab: sandstone-gold active dot at top edge + gold icon + gold label.
- Inactive tab: mist icon (`var(--ds-mist)`) + mist label.
- No filled background pill or tab highlight — dot indicator only.

### Touch targets
- Each tab item: `min-height: calc(3.5rem + env(safe-area-inset-bottom, 0))` — 56px+.
- Icon hit area: at minimum 44×44px (via full-width flex column layout).

### Safe area
- Tab item includes `padding-bottom: env(safe-area-inset-bottom, 0px)` via `.mobile-tab-item` CSS class.
- This ensures tabs do not overlap the iPhone home indicator.
- The nav itself has no separate `pb-safe` — each item handles its own bottom inset.

### Accessibility
- Each tab is a `<Link>` (anchor) with `aria-label` and `aria-current="page"` on the active tab.
- No nested interactive controls inside tab items.
- Focus-visible outline via the standard `focus-visible:outline` Tailwind/CSS pattern.

---

## Top app shell / header

### Mobile top bar
- Background: `var(--ds-midnight-ink)`.
- Bottom border: `1px solid var(--ds-pen-stroke)`.
- Height: `py-2.5` top/bottom (not oversized).
- Sticky at top with `z-40`.
- Slide-out drawer triggered by hamburger icon (unchanged behavior).

### Brand area
- Small plane icon in `bg-ds-carbon` container + "Travel Concierge" label.
- No tagline in the top bar.
- No decorative blur, glass, or gradient on the top bar.

---

## Mobile page content container

### Clearance rule
Every authenticated page content area must clear the bottom nav. Use the `.mobile-nav-spacer` CSS utility on the content wrapper.

```css
.mobile-nav-spacer {
  padding-bottom: max(5.5rem, calc(3.75rem + env(safe-area-inset-bottom, 0px)));
}
@media (min-width: 1024px) {
  .mobile-nav-spacer { padding-bottom: 2rem; }
}
```

### Horizontal padding
- Mobile: `px-4`
- Tablet+: `px-6`
- Desktop+: `px-8`

### Top padding
- Mobile: `pt-5` or `pt-6`
- Desktop: `pt-8`

---

## Contextual primary action

"New Trip" / "Start Trip" does **not** live in the bottom nav. It appears contextually:

| Surface | Action | Form |
|---|---|---|
| Home (no trips) | "Plan a Trip" button | `btn-primary` with `PlusCircle` icon |
| Home (with trips) | "New" link in shelf header | Quiet text link with `PlusCircle` |
| My Trips page header | "Plan a Trip" button | `btn-primary` with `PlusCircle` icon |
| Saved page | "Plan with this" / "Create Trip" | Per-item action |
| Explore | Save/Add flows | Per-result action |

Rules:
- All primary actions must be real `<Link href="/trips/new">` elements.
- No floating global FAB (Floating Action Button).
- No giant permanent "New" chrome in the nav bar.
- Minimum 44px touch target on all contextual action links/buttons.

---

## Touch target minimums

| Control type | Minimum |
|---|---|
| Primary CTA buttons | 48px (`min-h-[3rem]`) |
| Secondary buttons | 44px (`min-h-[2.75rem]`) |
| Icon-only actions | 44×44px (`min-h-[44px] min-w-[44px]`) |
| Bottom nav tab items | 56px+ (via `.mobile-tab-item`) |
| Text links within content | 44px when used as standalone actions |

---

## Section / tray / bottom-sheet language (for 8K–8M)

These patterns are reserved for Phase 8K+ surfaces. Document them here for consistency:

- **Tray:** Slides up from bottom, rounded top corners, dark surface (`bg-ds-onyx`), handle bar at top.
- **Bottom sheet:** Full or half-height tray, used for filter panels, day selectors.
- **Section separator:** `1px solid var(--ds-pen-stroke)` hairline — not gap or background change.
- **Context panel:** Slides in from right for detail views. Does not replace the page.

Do not use these patterns in Phases 8J or earlier.

---

## Motion

- Shell nav: `transition: color 120ms ease` on active/hover states only. No entrance animations.
- Drawer: `transition-transform 200ms ease-out` (existing, preserved).
- All motion obeys `@media (prefers-reduced-motion: reduce)` via the global rule in `globals.css`.
- No parallax, no scroll-linked animation, no bounce effects in Phase 8J.

---

## Anti-patterns (forbidden in shell/nav surfaces)

- Raw hex values (use ds-tokens).
- Glass / `backdrop-filter` on nav bars.
- Floating giant "New" button in bottom chrome.
- `focus:ring-*` — use `focus-visible:outline` pattern.
- Neon, confetti, gradients as decoration.
- `overflow: hidden` on scroll containers.
- Fake/mock data, hardcoded city prompts, placeholder luxury copy.

---

## Enforcement

- Tests: `frontend/tests/mobile-shell-nav-rescue-8j.test.mjs` checks the structural contracts above.
- Design review: Use this document as the checklist for all Phase 8K+ mobile surface work.
- Future phases (8K Trip Detail, 8L Itinerary Day, 8M Surface Pass, 8N Art Direction) must cite and extend this doc.
