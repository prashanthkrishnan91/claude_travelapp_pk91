# UI Baseline

Last updated: 2026-05-17 (Phase 8J — Mobile Shell/Nav Rescue)

## Purpose

Tracks the state of the design system and UI primitive layer so future prompts and PRs can reason accurately about what exists and what has been adopted.

---

## Stage 3.5 Phase 8J — Mobile Shell/Nav Rescue (Pocket Travel Atelier) — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow mobile shell — Boutique mobile design language + app shell/nav overhaul**

### What shipped

| File | Change summary |
|---|---|
| `docs/product/MOBILE_DESIGN_LANGUAGE.md` | **NEW.** Canonical "Pocket Travel Atelier" mobile design language document: 4-tab nav rule, contextual primary actions, 44px touch targets, safe-area rules, mobile page spacing, boutique visual tokens, tray/sheet language for 8K+. |
| `frontend/src/components/layout/MobileNav.tsx` | **Bottom nav rescue.** 5-tab nav (with giant center `New Trip`) → quiet 4-tab boutique nav (Home / Discover / Saved / My Trips). `isNew` special-case and `-mt-4` elevated center button removed. Each tab: `.mobile-tab-item` CSS class with `env(safe-area-inset-bottom)` native handling; `.mobile-tab-active-dot` sandstone indicator bar; `.mobile-tab-icon/-active` (44px wide); `.mobile-tab-label/-active`. Static `testid` keys per tab. **Top bar:** `.mobile-top-bar` class (midnight-ink base vs. prior onyx). `type="button"` on all non-submit buttons. Full drawer still contains all destinations including `/trips/new`. |
| `frontend/src/components/layout/AppShell.tsx` | **Content clearance.** `pb-24 lg:pb-8` → `mobile-nav-spacer` CSS utility. `data-testid="mobile-page-content"` added to content wrapper. |
| `frontend/src/app/globals.css` | **Mobile shell utilities.** `.mobile-top-bar` (midnight-ink, pen-stroke border). `.mobile-bottom-nav` (midnight-ink + warm brass inset shadow). `.mobile-tab-item` (flex column, `calc(3.5rem + env(safe-area-inset-bottom))`). `.mobile-tab-active-dot` (sandstone bar, top edge, 1.25rem wide, 2px tall). `.mobile-tab-icon` (2.75rem wide, mist color). `.mobile-tab-icon-active` (sandstone-gold). `.mobile-tab-label` / `.mobile-tab-label-active`. `.mobile-nav-spacer` (`max(5.5rem, calc(3.75rem + env(safe-area-inset-bottom)))` with `@media lg` override). All use ds-tokens; no raw hex. |
| `frontend/src/components/dashboard/DashboardClient.tsx` | **Contextual New Trip.** `JourneyShelfTeaser` header gains "New" link → `/trips/new` (`data-testid="home-new-trip-action"`). Empty state Plan a Trip button also gets `home-new-trip-action` testid. |
| `frontend/src/app/trips/page.tsx` | **Contextual New Trip.** Existing Plan a Trip header Link gets `data-testid="trips-new-trip-action"`. |
| `frontend/tests/mobile-shell-nav-rescue-8j.test.mjs` | **NEW.** 95 Phase 8J contract tests. |
| `frontend/package.json` | Added `mobile-shell-nav-rescue-8j.test.mjs` to test script. |

### Test results
- **1658 tests, 0 failures** (was 1563; +95 new Phase 8J contract tests)

### Design contract alignment
- **4-tab quiet boutique bottom nav:** Home / Discover / Saved / My Trips. No permanent New Trip chrome.
- **Contextual New Trip:** Available on Home (shelf header + empty state) and My Trips (page header).
- **Safe-area native:** CSS `env(safe-area-inset-bottom)` on `.mobile-tab-item`; no reliance on `pb-safe` Tailwind class.
- **Touch targets:** Tab items are `3.5rem + safe-area` (56px+); icon zones are 2.75rem (44px) wide.
- **Boutique atelier top bar:** Midnight-ink background, pen-stroke border — warmer and deeper than prior onyx.
- **Content clearance:** `mobile-nav-spacer` uses `max()` calc to protect content from nav overlap on all devices.
- **Mobile design language doc:** Canonical rules now live at `docs/product/MOBILE_DESIGN_LANGUAGE.md` for 8K+ reference.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/Google Places/Duffel/flights/Supabase/env changes.
- All existing testids, handlers, and routes preserved. Drawer retains all 8 destination links.
- No fake/mock/sample visible data introduced.
- No new navigation destinations; all routes backed by existing pages.

### Deferred to next phases
- Trip Detail IA + workspace mobile redesign → **Phase 8K**
- Itinerary Day mobile redesign → **Phase 8L**
- Full mobile surface pass (Explore, Saved, Concierge content) → **Phase 8M**
- Atmospheric boutique art direction (texture, lighting, motion) → **Phase 8N**

---

## Stage 3.5 Phase 8I — Mobile-First Premium Pass — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow mobile ergonomics — Primary mobile flow feel on all rebuilt surfaces**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/TripBuilder.tsx` | **Critical mobile layout fix.** Main canvas `flex items-start gap-4` → `flex flex-col gap-4 lg:flex-row lg:items-start`; candidate panel `w-80 flex-shrink-0` → `w-full lg:w-80 lg:flex-shrink-0` (was forcing a 320px panel on 390px phones, leaving ~54px for itinerary); compare bar gets `max-w-[calc(100vw-2rem)] sm:bottom-6 sm:px-5`. |
| `frontend/src/components/explore/HotelExploreFlow.tsx` | **Form row responsive.** Date/guests `grid grid-cols-3 gap-3` → `grid grid-cols-1 sm:grid-cols-3 gap-3`. |
| `frontend/src/components/explore/AttractionExploreFlow.tsx` | **Form row responsive.** Search row `flex gap-3` → `flex flex-col gap-3 sm:flex-row`; interest input `relative w-44 shrink-0` → `relative sm:w-44 sm:shrink-0`; button `btn-primary shrink-0` → `w-full sm:w-auto sm:shrink-0`. |
| `frontend/src/app/trips/[id]/page.tsx` | **Touch targets + focus-visible.** Edit modal close button gets `min-h-[44px] min-w-[44px] flex items-center justify-center`; 2 legacy `focus:outline-none focus:ring-2 focus:ring-ds-accent` replaced with `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`; back nav + chapter cover body `px-6` → `px-4 sm:px-6`. |
| `frontend/src/components/concierge/ConciergePage.tsx` | **Header padding responsive.** Inline `style={{ paddingBottom: "var(--ds-space-8)" }}` removed; `className="text-center pb-5 sm:pb-8"` added. |
| `frontend/src/components/trips/AIConciergePanel.tsx` | **Clear button 44px.** Clear button gets `min-h-[44px] flex items-center` in className; padding updated. |
| `frontend/src/components/explore/ExploreShell.tsx` | **Active section responsive padding.** Inline `style={{ padding: "var(--ds-space-6)" }}` removed; `p-4 sm:p-6` added to className. |
| `frontend/tests/mobile-first-premium-8i.test.mjs` | **NEW.** 51 Phase 8I contract tests covering all 7 surfaces above, plus preserved testids and handler contracts. |
| `frontend/tests/explore-discovery-lounge-8f.test.mjs` | **2 tests updated.** Old assertions checking for inline `padding: "var(--ds-space-6)"` updated to accept responsive Tailwind classes (OR the old inline style — backward-compatible). |
| `frontend/package.json` | Added `mobile-first-premium-8i.test.mjs` to test script. |

### Test results
- **1563 tests, 0 failures** (was 1512; +51 new Phase 8I contract tests)
- All pre-existing tests continue to pass

### Design contract alignment
- **TripBuilder is now mobile-first:** The planning canvas stacks vertically on phones (flex-col) and shifts to side-by-side only at lg (1024px+). The candidate panel takes full width on mobile.
- **Explore form rows no longer cram on small screens:** Hotel dates/guests and Attraction search/interest/button rows now stack vertically on mobile.
- **44px touch targets enforced on all remaining modal controls:** TripDetail edit modal close button meets minimum.
- **Focus-visible standardized on all TripDetail modal inputs:** No remaining `focus:ring-*` legacy patterns in the codebase surfaces touched by Phase 8.
- **Responsive padding throughout:** Header pads, section pads, and back-nav pads all use mobile-first breakpoint classes rather than fixed inline styles.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- All existing testids, handlers, and page logic preserved.
- No fake/mock/sample visible data introduced.
- No new booking behavior; no Google Places/Duffel/flights contract changes.

---

## Stage 3.5 Phase 8H — Global Controls, Forms, Action Sheets, and Modal Interaction Polish — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — Shared control layer · Premium input/button/label/action sheet polish**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/globals.css` | **`.input` ds-token migration.** `border: 1px solid rgba(...)` → `var(--ds-pen-stroke)`; `background: rgba(7,7,18,0.65)` → `var(--ds-midnight-ink)`; removed `backdrop-filter` (glass forbidden on content surfaces); `color: #f2ede4` → `var(--ds-text-primary)`; `::placeholder` → `var(--ds-text-tertiary)`; `outline: none` removed; `:focus` → `:focus-visible` with `outline: 2px solid var(--ds-accent); outline-offset: 2px; border-color: var(--ds-accent-muted)`; disabled state → `color-mix(in srgb, var(--ds-pen-stroke) 30%, transparent)` bg; `min-height: 2.75rem` (44px). **`.select`** same pattern. **`.label`** → Overline grammar: `var(--ds-type-overline-size/weight/tracking)`, `text-transform: uppercase`, `var(--ds-text-tertiary)`. **`.btn-primary`** focus-visible raw hex `#e8b854` → `var(--ds-accent)`; `min-height: 2.75rem`. **`.btn-secondary`** (new): ink-on-dark outlined button — `bg-ds-carbon`, `border: 1px solid var(--ds-pen-stroke)`, `color: var(--ds-text-secondary)`, `min-height: 2.75rem`, hover `bg-ds-pen-stroke/text-ds-text-primary`, `focus-visible: outline 2px solid var(--ds-accent)`. **`.btn-ghost`** rgba border/bg → `color-mix(in srgb, var(--ds-pen-stroke) 35/60%, transparent)`; `color: #d8d4ca` → `var(--ds-text-secondary)`; `min-height: 2.75rem`; focus-visible → `var(--ds-accent)`. |
| `frontend/src/components/ui/EmptyState.tsx` | **ds-token migration.** `bg-white/[.06]` → `bg-ds-carbon`; `border-white/[.07]` → `border-ds-pen-stroke`; `text-cream-400` → `text-ds-text-tertiary`; `text-cream-200` → `text-ds-text`. |
| `frontend/src/components/ui/StatCard.tsx` | **ds-token migration.** Default `colorClass` `bg-brand-500/15 text-brand-400` → `text-ds-accent`; icon container gets `style={{ backgroundColor: "var(--ds-accent-subtle)" }}`; `text-cream-500` → `text-ds-text-tertiary`; `text-cream-100` → `text-ds-text`; positive trend `text-emerald-400` → `text-ds-trust`; negative trend `text-cream-500` → `text-ds-text-tertiary`. |
| `frontend/src/components/explore/ResultActionSheet.tsx` | **44px touch targets.** `save-action-btn` and `more-actions-toggle` buttons both gain `min-h-[44px]` in className. All handlers, testids, and behavior preserved. |
| `frontend/src/components/trips/TripIdeasPanel.tsx` | **focus-visible pattern.** 4 instances of `focus:outline-none focus:ring-1 focus:ring-ds-accent` replaced with `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` (textarea note, day selector, search input, sort select). |
| `frontend/tests/global-controls-polish-8h.test.mjs` | **NEW.** 77 Phase 8H contract tests: `.input` ds-token (pen-stroke/midnight-ink/text-primary), focus-visible pattern, 44px touch target; `.select` mirrors `.input`; `.label` Overline grammar (overline-size/tracking/uppercase/text-tertiary); `.btn-primary` focus-visible `var(--ds-accent)` + 44px; `.btn-secondary` defined/ds-token/focus-visible/44px; `.btn-ghost` focus-visible `var(--ds-accent)` + 44px + no raw rgba for color; `EmptyState` no cream-*/white/[ legacy; `StatCard` no cream-*/brand-*/emerald-* legacy; `ResultActionSheet` save/more-actions `min-h-[44px]`; `ResultActionSheet` handlers/testids preserved; `ResultActionSheet` no backend imports; `TripIdeasPanel` no focus:ring-* legacy; no nested interactive controls; no raw hex in focus-visible color properties. |
| `frontend/package.json` | Added `global-controls-polish-8h.test.mjs` to test script. |

### Test results
- **1496 tests, 0 failures** (was 1419; +77 new Phase 8H contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Controls match the atelier interface:** `.input` fields now read as design-native (pen-stroke border, midnight-ink background, text-primary text, no glass backdrop). `.label` in Overline grammar makes field labels consistent with card section labels and nav section labels across every rebuilt surface.
- **Focus-visible everywhere:** All touched controls now use the Design Bible §4.12 standard: `2px solid var(--ds-accent)` with `2px offset`. No `outline: none` suppressions, no `focus:ring-*` legacy patterns. Keyboard navigation is equally premium on all touched surfaces.
- **44px minimum targets:** `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.input`, `.select`, `save-action-btn`, `more-actions-toggle` all have `min-height: 2.75rem` (44px). Completes the touch target pass for the shared control layer.
- **`.btn-secondary` establishes a durable second-level CTA:** Future surfaces can now use `className="btn-secondary"` for ink-on-dark outlined actions — consistent with the `btn-primary` gold premium CTA but visually subordinate.
- **Shared UI primitives clean:** `EmptyState` and `StatCard` were the last two `components/ui/` primitives still using cream-\*/brand-\*/emerald-\* legacy palette. Both fully migrated to ds-tokens.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data; no hardcoded destinations.
- `ResultActionSheet` testid contract fully preserved: `result-action-sheet`, `save-action-btn`, `more-actions-toggle`, `manage-in-saved-link`, `save-first-hint`, `trip-actions-guidance`, `action-error`.
- `ResultActionSheet` handler contract preserved: `handleSave`, `handleUnsave`, `saveItem`, `deleteSavedItem`, `buildSavePayload`.
- `TripIdeasPanel` behavior preserved: all `handleAssign`, `handleRemove`, `handleUpdate`, filter/sort/search logic unchanged.
- `.label` class name preserved — all existing consumers (TripBuilderForm, auth pages, trips page, cards page) keep working.
- `.btn-primary`, `.btn-ghost` class names preserved. `.btn-secondary` is additive (no existing code broken).

### Accessibility / motion note
- No new motion introduced. `card-lift` (translateY -2px, 120ms) is pre-existing.
- `.btn-ghost` backdrop-filter retained — TripBuilder glass context is the established exception per HANDOFF Phase 8B.
- All focus-visible patterns use the 2px sandstone-gold ring from Design Bible §4.12.
- `min-height: 2.75rem` on inputs and buttons ensures 44px touch target across mobile/tablet.

---

## Stage 3.5 Phase 8G — Saved Ideas Scrapbook + Planning Bridge — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — `/saved` Saved surface · Scrapbook editorial identity + planning bridge**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/saved/SavedShell.tsx` | **Scrapbook editorial transformation.** `TYPE_OVERLINES` constant added (Restaurant/Attraction/Hotel/Flight overline labels). **Header**: plain div replaced with semantic `<header data-testid="saved-scrapbook-header">` containing Overline "Your Travel Scrapbook" (`data-testid="saved-scrapbook-overline"`, `tracking-[0.1em] uppercase text-[10px] font-semibold text-ds-accent`) + `<h1 data-testid="saved-scrapbook-heading">Saved Ideas</h1>` + real collection count (`data-testid="saved-scrapbook-count"`). **SavedItemCard**: type Overline added above name (`data-testid="saved-item-type-overline"`, `TYPE_OVERLINES[item.vertical]`, `tracking-[0.1em] uppercase text-[10px] font-semibold text-ds-accent-muted`); `<h3 data-testid="saved-item-name">` for place name; maps + remove action buttons upgraded to `min-w-[44px] min-h-[44px] flex items-center justify-center` (44px touch targets); `mt-0.5` on icon wrapper; planning bridge section `data-testid="saved-planning-bridge"` with `border-t border-ds-hairline/60` + Overline "Plan with this" label wrapping Create Trip + Add to Trip. **VerticalGroup**: `saved-group-${key}` → `saved-section-${key}`; icon removed from section header; section header gains `border-b border-ds-hairline` + Overline `data-testid="saved-section-label-${key}"` + right-aligned count. All existing action testids preserved. |
| `frontend/src/components/saved/CreateTripFromSavedModal.tsx` | **ds-token migration.** `bg-dark-100 border border-white/[.08]` → `bg-ds-onyx border border-ds-pen-stroke shadow-[var(--ds-elevation-4)]`; `text-cream-100` → `text-ds-text`; `text-cream-500` → `text-ds-text-tertiary`; `bg-white/[.04] hover:bg-white/[.10] text-cream-500` → `bg-ds-carbon hover:bg-ds-pen-stroke text-ds-text-tertiary` on close button; close button gains `min-w-[44px] min-h-[44px] flex items-center justify-center`; all form inputs `bg-white/[.04] border border-white/[.06] text-cream-100 focus:border-brand-400` → `bg-ds-carbon border border-ds-pen-stroke text-ds-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`; form label `tracking-wide` → `tracking-[0.1em]`; unresolved hint `text-amber-300/90` → `text-ds-caution`; error `bg-rose-500/10 text-rose-300` → `bg-ds-carbon text-ds-warning`; cancel button `text-cream-400 hover:text-cream-200` → `text-ds-text-tertiary hover:text-ds-text`; submit `bg-brand-500 text-dark-50 hover:bg-brand-600` → `bg-ds-accent text-ds-text-inverse hover:bg-ds-accent-muted`. All behavior, logic, and data-testids preserved. |
| `frontend/tests/saved-scrapbook-8g.test.mjs` | **NEW.** 135 Phase 8G contract tests: scrapbook shell structure (saved-scrapbook-header/overline/heading/count testids, semantic header element, "Your Travel Scrapbook" overline text, h1 "Saved Ideas"), Overline typography role (tracking-[0.1em]/uppercase/text-[10px]/font-semibold on overline and section labels), TYPE_OVERLINES constant (all 4 verticals), saved-item-type-overline testid + typography, saved-item-name h3 testid, planning bridge (saved-planning-bridge testid, "Plan with this" editorial label, border-t separator, create-trip-btn/add-to-trip-btn preserved), semantic buttons/links (no card-level onClick nav, Create Trip is button, Add to Trip is button, Explore link is Link), 44px touch targets (maps link min-w/h-[44px], remove button min-w/h-[44px]), section editorial structure (saved-section-${key}/saved-section-label-${key}, border-b hairline, tracking-[0.1em]), no fake/hardcoded city data, no backend imports, no raw rgba/hex in SavedShell, no legacy palette (cream-*/brand-*/slate-*), CreateTripFromSavedModal ds-token contract (bg-ds-onyx/border-ds-pen-stroke/text-ds-text/bg-ds-carbon/focus-visible:outline-ds-accent/bg-ds-accent/text-ds-caution/text-ds-warning), no legacy modal colors, modal submit/close/error/unresolved-hint ds-token checks, all action handlers preserved (deleteSavedItem/addSavedItemToTrip/createTripFromSavedItem/listSavedItems/fetchTrips), hotel discovery-only, mobile-safe layout, empty/loading/error states preserved. |
| `frontend/package.json` | Added `saved-scrapbook-8g.test.mjs` to test script. |

### Test results
- **1419 tests, 0 failures** (was 1284; +135 new Phase 8G saved scrapbook contract tests)
- All pre-existing tests continue to pass (including saved-lists-foundation, saved-trip-conversion, create-trip-from-saved, saved-items-action-wiring)

### Design contract alignment

- **Warm personal scrapbook, not generic list:** SavedShell now opens with a semantic `<header>` containing an Overline "Your Travel Scrapbook" — the same editorial grammar as Explore ("Curated Discovery") and Concierge ("Private Travel Concierge"). The h1 "Saved Ideas" is the page identity. A real collection count ("N ideas in your collection") appears once items load — no fabricated stats.
- **Idea identity per card:** Every saved item now opens with an Overline type label (RESTAURANT / ATTRACTION / HOTEL / FLIGHT), matching the TYPE_LABELS pattern from Phase 8C (itinerary cards). This gives each scrapbook entry immediate editorial identity before the name is read.
- **Planning bridge clarity:** The Create Trip + Add to Trip actions now live in a clearly framed planning bridge section: `border-t border-ds-hairline/60` separator + Overline "Plan with this" label. The path from scrapbook idea → trip planning is structurally visible. No behavior changes; only the structural framing is new.
- **Section rhythm:** VerticalGroup section headers are now `border-b border-ds-hairline` Overline labels — same hairline-separated editorial rhythm used in Phase 8D (day column sections). Each section is a `<section>` with `aria-label`.
- **44px touch targets:** Maps link and Remove button now use `min-w-[44px] min-h-[44px] flex items-center justify-center` — correct mobile touch target pattern, matching other Phase 8* surfaces.
- **Modal ds-token migration:** CreateTripFromSavedModal was the last Saved surface using legacy colors (`bg-dark-100`, `cream-*`, `brand-*`, `rose-*`, `amber-*`). Full ds-token migration completed. Modal now reads as a dark ink-ladder dialog (bg-ds-onyx, border-ds-pen-stroke, elevation-4 shadow) — matching trip-detail modal treatment from Phase 8B.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data; no hardcoded destinations.
- All existing SavedShell testids preserved: saved-shell, saved-loading, saved-error, saved-empty, saved-empty-explore-link, saved-item-card, saved-card-rating, hotel-search-context, remove-saved-btn, remove-error, create-trip-section, create-trip-btn, add-to-trip-section, add-to-trip-btn, trip-picker, trip-picker-option, add-to-trip-success, add-to-trip-error.
- All CreateTripFromSavedModal testids preserved: create-trip-modal, create-trip-form, ct-title, ct-origin, ct-destination, ct-unresolved-hint, ct-start-date, ct-end-date, ct-travelers, ct-error, ct-submit.
- Hotel discovery-only contract preserved: no rates, availability, or booking copy.
- Flight exclusion from add-to-trip (`canAddToTrip = item.vertical !== "flight"`) preserved.

### Accessibility / motion note
- No new motion introduced. `card-lift` (translateY -2px, 120ms) is pre-existing and within the motion contract.
- `border-t border-ds-hairline/60` and `border-b border-ds-hairline` are CSS borders — no animation; reduced-motion safe.
- Maps link and Remove button have `aria-hidden="true"` on icons and `aria-label` on the anchor/button.
- Planning bridge "Plan with this" label is a presentational `<p>` — no interaction.
- All interactive elements use `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` pattern.

---

## Stage 3.5 Phase 8F — Explore / Discover Curated Search Lounge — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — Explore surface · Curated discovery lounge transformation**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/explore/ExploreShell.tsx` | **Lounge transformation.** `VerticalMeta` interface: `iconBg`/`iconColor`/`badge` removed; all four vertical icon colors unified to sandstone-gold (`style={{ backgroundColor: "var(--ds-accent-subtle)" }}` + `text-ds-accent`). `VERTICAL_TITLES` updated to clean editorial labels. `VERTICAL_OVERLINES` constant added (Search/Stays/Dining/Experiences). **Home state**: editorial `<header data-testid="explore-lounge-header">` with Overline "Curated Discovery" + `<h1>Discover</h1>` + `text-ds-text-tertiary` subtext; `data-testid="explore-home"` preserved. **VerticalCard**: `className="card card-lift p-5 group..."` → `rounded-xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)] hover:bg-ds-carbon card-lift w-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`; `group-hover:scale-105 transition-transform` forbidden decorative motion removed; Overline category label (`text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary`) added above card title. **Active vertical state**: breadcrumb `text-cream-*` → `text-ds-text-tertiary hover:text-ds-text`; back button `focus-visible:outline-ds-accent`; `data-testid="explore-lounge-breadcrumb"`; `.card p-6` container → `<section rounded-xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-2)]>` with `<div data-testid="explore-instrument-header">` containing Overline + heading inside. All behavior preserved: `useState` vertical selection, four vertical flows, back navigation, `data-testid="${active}-flow"`. |
| `frontend/src/components/explore/RestaurantExploreFlow.tsx` | `text-cream-500` → `text-ds-text-tertiary` on MapPin icon. Result count: `text-xs font-medium uppercase tracking-wider` → `text-[10px] font-semibold uppercase tracking-[0.1em]`; `data-testid="explore-results-header"` added. |
| `frontend/src/components/explore/HotelExploreFlow.tsx` | `text-cream-500` → `text-ds-text-tertiary` on MapPin/Calendar/Users icons (3 instances). Result count: same Overline upgrade + `data-testid="explore-results-header"`. |
| `frontend/src/components/explore/AttractionExploreFlow.tsx` | `text-cream-500` → `text-ds-text-tertiary` on MapPin/Tag icons (2 instances). Result count: same Overline upgrade + `data-testid="explore-results-header"`. |
| `frontend/tests/explore-discovery-lounge-8f.test.mjs` | **NEW.** 99 Phase 8F contract tests: lounge structure (explore-lounge-header/breadcrumb/instrument-header testids, "Curated Discovery" overline, "Discover" h1, "no trip required" copy), search instrument visual (focus-visible ring, card-lift, tracking-[0.1em], var(--ds-accent-subtle) icon bg, shadow-elevation), no legacy colors (sky-*/violet-*/amber-*/emerald-*/cream-* in ExploreShell + all three flow components), no raw rgba( or raw hex in ExploreShell, preserved vertical behavior (all 4 flows, ResultActionSheet, Google Maps, hotel compare CTA, save/unsave), no AI Concierge routing (Hotel/Attraction flows), no fake/mock data or hardcoded city prompts, accessibility (semantic buttons, aria-labels, no card-level onClick nav), mobile layout (grid-cols-1 sm:grid-cols-2), result count Overline (tracking-[0.1em] in all 3 flows), no backend imports, design contract audit (no .card class, no iconBg, no group-hover:scale). |
| `frontend/package.json` | Added `explore-discovery-lounge-8f.test.mjs` to test script. |

### Test results
- **1284 tests, 0 failures** (was 1185; +99 new Phase 8F explore discovery lounge contract tests)
- All pre-existing tests continue to pass (including global-explore-shell, explore-restaurants-trust-contract, hotel-explore-live, hotels-discovery-only)

### Design contract alignment

- **Discovery lounge, not utility dashboard:** ExploreShell now opens with an editorial header (Overline "Curated Discovery" + h1 "Discover") that frames the surface as a curated destination, not a SaaS form page. The four vertical cards read as discovery trays — uniform sandstone-gold accent icons, clean card shells, Overline category labels.
- **Instrument section framing:** When a vertical is active, the flow is wrapped in a `<section>` with `bg-ds-onyx border-ds-pen-stroke shadow-elevation-2` — the same ink-ladder elevation pattern used by other editorial surfaces (TripReadinessCockpit, AIConciergePanel). The Overline + heading inside the section gives each vertical search a clear editorial identity before the form appears.
- **Uniform icon palette:** The old per-vertical legacy colors (sky-400/violet-400/amber-400/emerald-400) broke the Design Bible's "no legacy palette utilities in touched surfaces" rule. All four icons now use the uniform sandstone-gold token (`--ds-accent-subtle` bg + `text-ds-accent`), matching the convention established in Concierge, itinerary cards, and other Phase 8* surfaces.
- **No decorative motion:** `group-hover:scale-105 transition-transform` on the icon wrapper was an unnecessary scale animation. Removed per Design Bible §12 (no decorative motion). `card-lift` (translateY -2px, 120ms) is the permitted hover response.
- **Form icon token fix:** `text-cream-500` in search form icons (MapPin, Calendar, Users, Tag) across all three vertical flows replaced with `text-ds-text-tertiary`. This completes the token migration started in Phase 1B (result cards) and ensures search controls are visually consistent with the instrument framing.
- **Result count Overline:** `tracking-wider text-xs font-medium` upgraded to Design Bible §4.3 Overline-exact `tracking-[0.1em] text-[10px] font-semibold` across all three flows. Minor but completes the Overline type role consistency.
- **Mobile:** Responsive `grid-cols-1 sm:grid-cols-2` grid preserved. No horizontal overflow risk. Instrument section padding via `var(--ds-space-6)` (CSS var, not Tailwind hardcoded value).

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL generation changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- Default Explore Hotels/Attractions do NOT route through AI Concierge (`callConciergeSearch` absent from both flows).
- All ResultActionSheet (save/unsave/expand/manage-in-saved) actions: preserved.
- All Google Maps link-outs: preserved.
- Hotel compare prices CTA (`hotel-compare-cta`): preserved.
- TrustStrip rendering on Google Place identity: preserved.
- FlightExploreFlow (FlightCard, ResultActionSheet, Google Flights link-out): unchanged.

### Accessibility / motion note
- No new motion introduced. `card-lift` (translateY -2px, 120ms) is pre-existing and within the motion contract.
- `group-hover:scale-105` removed — was a forbidden decorative scale animation.
- `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` added to VerticalCard and back button.
- `aria-hidden="true"` on icon wrappers.
- Semantic `<header>` for page identity, `<section>` for instrument area.

---

## Stage 3.5 Phase 8E — Concierge Search Instrument + Results Presentation Overhaul — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — `ConciergePage.tsx` + `AIConciergePanel.tsx` · Private travel desk instrument**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/concierge/ConciergePage.tsx` | **Instrument transformation.** `data-testid` contract: `concierge-page` (root), `concierge-instrument-header`, `concierge-results-canvas`, `concierge-empty-state`, `concierge-result-section`, `concierge-loading-state`, `concierge-error-state`, `concierge-instrument-composer`, `concierge-destination-field`, `concierge-query-input`, `concierge-submit-button`, `concierge-clear-chat`, `concierge-user-query`. **User turns**: right-aligned `rounded-2xl rounded-tr-sm` chat bubble removed; replaced with left-border italic `border-l-2 border-ds-pen-stroke pl-3 my-2` query marker — quiet, editorial, not chatbot. **Destination label**: `sr-only` removed; visible Overline "Where" label rendered above field with `tracking-[0.1em]`. **Instruction copy**: "We surface" → "I surface verified places worth your time" (first-person concierge voice). **Header h1 default**: "Where would you like to go?" → "What can I find for you?". **Empty state**: "A few starting points to get you going:" → "Starting points — tell me where to search:". **Textarea placeholder**: "Describe what you're looking for…" → "What can I find for you?". **Overline tracking**: `tracking-[0.12em]` → `tracking-[0.1em]` in header. All behavior preserved: callConciergeSearch(null, ...), transcript, clearTranscript, localStorage persistence, refinement chips, editorial prompt chips. No raw hex, no legacy palette classes. |
| `frontend/src/components/trips/AIConciergePanel.tsx` | **Panel instrument transformation.** `data-testid` contract: `ai-concierge-panel` (root), `concierge-panel-header`, `concierge-panel-day-selector`, `concierge-panel-transcript`, `concierge-panel-user-query`, `concierge-panel-loading`, `concierge-panel-composer`, `concierge-panel-input`, `concierge-panel-submit`, `concierge-panel-clear`, `concierge-panel-close`. **Header**: generic "AI Concierge · destination" → Sparkles icon + Overline "Private Travel Concierge" + `{destination}` as separate `p.text-ds-text.font-semibold` heading. Clear/close buttons → `rounded-lg` with ds-token sizing. **Day selector**: label "Target day for Add to Day" → "Add to Day"; tracking `0.08em` → `0.1em`; select → `text-ds-text focus-visible:outline`. **User turns**: `rounded-2xl rounded-br-sm bg-ds-accent/15 ring-1 ring-ds-accent/30` chat bubble removed; left-border italic query marker (same grammar as standalone). **Assistant text**: `rounded-2xl rounded-bl-sm bg-ds-carbon` bubble removed; plain `p.text-ds-text-secondary`. **Loading state**: chatbot bubble ("Researching options…") → instrument style ("Searching · Verifying · Composing") with `Loader2 text-ds-accent` + `role="status"`. **Quick actions**: `rounded-full` chatbot pills → `rounded-lg` instrument chips. **Refinement chips**: `rounded-full` → `rounded-lg`. **Panel input**: `focus:outline-none focus:ring-2 focus:ring-ds-accent/60` → `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`; `aria-label="Concierge query"` added; `minHeight: "44px"` added; placeholder "Ask, refine, or compare…" → "Refine, compare, or start a new search…". **Submit button**: `type="button"` + `data-testid`; min-width/height 44px via inline style. `shadow-2xl` → `shadow-[var(--ds-elevation-4)]` on panel root. All behavior preserved: callConciergeSearch(tripId, ...), CONCIERGE_CACHE_VERSION, isRenderableVerifiedPlace, add-to-day, save-to-ideas, maps, card actions, handleClearChat, selectedDayId. No raw hex, no legacy palette classes. |
| `frontend/tests/concierge-instrument-8e.test.mjs` | **NEW.** 79 Phase 8E contract tests: instrument structure (12 testids on ConciergePage, 11 on AIConciergePanel), premium composer grammar (visible label, Overline tracking, focus-visible, aria-label, 44px), no chat-bubble user turns (flex justify-end removed, rounded-2xl removed, italic query marker), first-person copy, no backend imports, no fake data, preserved behavior (transcript, clear-chat, add-to-day, save, maps, cards, refinement chips, callConciergeSearch contract), no raw hex, panel editorial header (overline, no inline "· destination" suffix), day selector editorial (Add to Day, no jargon), loading instrument style, input touch target. |
| `frontend/package.json` | Added `concierge-instrument-8e.test.mjs` to test script. |

### Test results
- **1185 tests, 0 failures** (was 1106; +79 new Phase 8E concierge instrument contract tests)
- All pre-existing tests continue to pass (including concierge-page-static, concierge-shared-helpers, concierge-renderers, concierge-refinement, concierge-transcript-persistence)

### Design contract alignment

- **Search instrument, not chatbot:** User turns in both surfaces are now quiet left-border italic query markers — not right-aligned chat bubbles. The result cards dominate visually; the transcript is usable but not chatbot-styled.
- **Panel header editorial identity:** AIConciergePanel opens with the same editorial grammar as the standalone page: Overline "Private Travel Concierge" (accent color, 0.1em tracking) + destination as a separate named heading below — not "AI Concierge · destination" inline label.
- **Day selector precision:** "Add to Day" is the correct editorial action label. "Target day for Add to Day" was functional jargon; removing it makes the control feel intentional.
- **Loading as instrument state:** "Searching · Verifying · Composing" is an honest description of the pipeline stages. It matches the standalone concierge and removes the chatbot bubble ("Researching options…").
- **Destination label visible:** Overline "Where" label renders above the destination field — not sr-only. Makes the composer feel structured (destination → query → submit), not a bare textarea.
- **First-person voice:** "I surface verified places worth your time" — the concierge speaks as a person, not a system.
- **Mobile:** Left-border query markers take less horizontal space than chat bubbles, reducing overflow risk on narrow screens. Panel input now has `minHeight: "44px"` for reliable touch target.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- All add-to-day (addStructuredConciergeItemToTrip), save-to-ideas (saveToTripIdeas), maps (googleMapsUri/mapsLink), card actions (onAdd/onSaveIdea), and transcript behavior: fully preserved.
- AIConciergePanel CONCIERGE_CACHE_VERSION, isRenderableVerifiedPlace, fetchConciergeMessages, clearConciergeCache: all preserved.
- ConciergePage loadPersistedTranscript, saveTranscript, clearTranscript, TRANSCRIPT_KEY, refinement chips: all preserved.

### Accessibility / motion note
- No new motion, gradients, glass blur, or animations introduced in Phase 8E.
- Left-border marker (`border-l-2`) is a CSS border — no animation; reduced-motion safe.
- `italic` on query text is a CSS property — no animation; reduced-motion safe.
- All interactive elements use `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` pattern. No new interactive patterns added.

---

## Stage 3.5 Phase 8D — Itinerary DayColumn Editorial Chapter Frame — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — `ItineraryDayColumn.tsx` · Trip-story day-chapter page**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryDayColumn.tsx` | **Editorial chapter-frame transformation.** `data-testid` contract added throughout: `day-chapter-frame` (root), `day-chapter-header` (header div), `day-chapter-number` (number marker), `day-chapter-title` (h3), `day-chapter-date` (date paragraph), `day-item-count` (quiet item count badge), `day-part-section` (each section container), `day-part-label` (each Overline label), `empty-day-chapter` (empty state). **`h3` promoted `text-sm`→`text-base`** for stronger editorial heading weight. **Day-part sections refactored** from `orderedSections.map` (returning null for empty) to `filledSections.filter` array, enabling `border-t border-ds-pen-stroke/30` hairline rhythm between non-empty sections (idx > 0 only). **Time hint made `italic`** to differentiate from the Overline section label — editorial register, not KPI. **Empty day invitation rewritten**: board-lane copy ("Drag items here or use + Add to start building.") replaced with editorial chapter prompt ("Begin this chapter — use + Add or drag a stop here."); Overline tracking corrected `tracking-[0.08em]`→`tracking-[0.1em]`. All behavior preserved exactly: DnD droppable (useDroppable, setNodeRef, isOver), SortableContext, groupByDayPart, DAY_PART_META, onPlanDay, handleSuggestTimeline, handleApplyTimeline, itemOverrides, onMoveItemToIdeas, ItineraryItemCard rendering via renderItemsWithConnectors, computeAdjacentHints, PREVIEW_ITEM_LIMIT, show-all/show-less pagination. No rgba(), no raw hex, no legacy palette classes. |
| `frontend/tests/itinerary-day-chapter-frame.test.mjs` | **NEW.** 76 Phase 8D contract tests: data-testid structure contract (all 9 testids), h3 text-base chapter heading, Overline tracking, formatDate real data, filledSections hairline variable, border-t hairline class, italic time hint, day-part-section/label testids, empty-day-chapter testid, chapter-prompt copy ("Begin this chapter"), no board-lane copy ("to start building" / "Drag items here"), border-dashed + accent drag-over, 44px touch target near chapter prompt, semantic `<button>` for + Add, ds-token contract (no raw hex/rgba/slate/amber), no backend/provider/Supabase imports, all DnD primitives (useDroppable/SortableContext/verticalListSortingStrategy/isOver/setNodeRef), groupByDayPart/getItemDayPart/TimelineSections/DAY_PART_META/orderedSections preserved, ItineraryItemCard/renderItemsWithConnectors/onMoveItemToIdeas/onMoveToIdeas/onRemove/onToggleCompare/onTimelineUpdated preserved, timeline AI (handleSuggestTimeline/handleApplyTimeline/SuggestionsReviewPanel/itemOverrides), isExpanded/PREVIEW_ITEM_LIMIT/showAllItems/DayTravelHintBar/onPlanDay/onUpdateTimeline preserved. |
| `frontend/package.json` | Added `itinerary-day-chapter-frame.test.mjs` to test script. |

### Test results
- **1101 tests, 0 failures** (was 1025; +76 new Phase 8D day chapter frame contract tests)
- All pre-existing tests continue to pass (including trip-canvas-day-system, itinerary-chapter-editorial, trip-chapter-overhaul, itinerary-timeline, smart-timeline, travel-time-hints)

### Design contract alignment

- **Day chapter, not board lane:** Each day column opens with a promoted `text-base font-semibold` chapter heading ("Day N") — one step up from `text-sm`. The number marker (zero-padded, accent when selected) is a chapter index, not a tile counter.
- **Editorial date treatment:** `CalendarDays` icon + uppercase Overline date below the heading gives each day its calendar identity without making it look like a SaaS task status.
- **Hairline section rhythm:** Day-part sections (Morning / Afternoon / Evening / Unscheduled) now have `border-t border-ds-pen-stroke/30` hairlines between non-empty sections, creating visual page-paragraph separators. Only non-empty sections render; gaps between them feel like editorial breathing room.
- **Italic time hint:** `5 AM – 12 PM`, `12 PM – 5 PM`, `5 PM – 10 PM` appear in italic next to each Overline section label — annotative, not instructional.
- **Chapter-prompt empty state:** "Begin this chapter — use + Add or drag a stop here." — contextual, inviting, not a blank drop zone.
- **Quiet item count:** `text-[11px] text-ds-text-tertiary rounded-full` badge in the header — visible but not a KPI tile.
- **Semantic data-testids:** Full testid contract enables integration testing of the chapter structure without relying on text-match fragility.
- **Mobile:** All content in the chapter header and day-part sections is single-axis flex, wraps cleanly on narrow screens. No horizontal overflow risk. `min-h-[44px]` on all action buttons.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL generation changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- `ItineraryItemCard.tsx` untouched (no class compatibility adjustment needed).
- `TripBuilder.tsx` untouched.
- All DnD (useDroppable, SortableContext, isOver, setNodeRef), groupByDayPart, DAY_PART_META, timeline AI planning, move-to-ideas, compare, remove, booking checklist, show-all pagination: all preserved.

### Accessibility / motion note
- No new motion, gradients, glass blur, or animations introduced in Phase 8D.
- Hairline `border-t border-ds-pen-stroke/30` is a CSS border — no animation involved; reduced-motion safe.
- `italic` on time hint is a CSS property — no animation. Reduced-motion safe.
- All interactive elements use inherited `focus-visible:outline-ds-accent` pattern. No new interactive patterns added.

---

## Stage 3.5 Phase 8C — Itinerary ItemCard Chapter-Style Editorial Polish — SHIPPED (2026-05-17)

**Stage 3.5 · Wife-Wow design system — `ItineraryItemCard.tsx` · Trip-story chapter-entry card**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryItemCard.tsx` | **Editorial transformation.** Root changed from `<div>` to `<article data-testid="itinerary-item-card">` for semantic chapter-entry identity. `TYPE_LABELS` map added: flight→Flight, hotel→Stay, activity→Activity, meal→Dining, transit→Transit, note→Note. New **entry header row**: type icon (existing, moved inside content) + Overline type label (`text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary`, `data-testid="item-type-overline"`) on left; action cluster (move-to-ideas, compare, timeline, booking, remove) on right. Title promoted from `text-xs font-semibold` to `text-[13px] font-semibold` with `data-testid="item-title"`. Flight/hotel/activity/meal type-specific sections gain `pt-1 border-t border-ds-pen-stroke/40` hairline top separator for editorial rhythm. Padding increased `p-2`→`p-3`. All behavior preserved exactly: round-trip one-card rendering (`itinerary-roundtrip-flight` testid, both legs via `renderLeg`), Google Flights link-out (`itinerary-google-flights-cta`, `-my-3.5 py-3.5` touch target), DnD sortable, compare toggle, move-to-ideas conditional, timeline editor, booking checklist. No `rgba()`, no raw hex, no legacy palette classes. `var(--ds-accent-subtle)` inline style for icon/button backgrounds. |
| `frontend/tests/itinerary-chapter-editorial.test.mjs` | **NEW.** 63 Phase 8C contract tests: TYPE_LABELS map, item-type-overline testid, Overline typography role (tracking/uppercase/10px/semibold), title prominence, article semantic element, itinerary-item-card testid, no raw hex/rgba/legacy palette, ds-token surface classes, semantic button/link actions, no card-level onClick navigation, no fake/mock/sample data, no backend imports, all preserved actions (remove/compare/move-to-ideas/booking/timeline/DnD), round-trip one-card rendering, Google Flights link-out contract (URL fields, testid, aria-label, touch target, rel), mobile-safe layout (flex-shrink-0, min-h-[44px], -m-3 p-3, -m-3.5 p-3.5), day column behavior preservation. |
| `frontend/package.json` | Added `itinerary-chapter-editorial.test.mjs` to test script. |

### Test results
- **1025 tests, 0 failures** (was 962; +63 new Phase 8C chapter editorial contract tests)
- All pre-existing tests continue to pass (including all itinerary-card-finalized-display, trip-flight-cards-canonical, hotel-itinerary-display, itinerary-timeline, trip-planning-card-tokens, trip-canvas-day-system tests)

### Design contract alignment

- **Chapter entry, not generic card:** Each itinerary item opens with an Overline type identity line (FLIGHT/STAY/ACTIVITY/DINING/TRANSIT/NOTE) + the type icon. The item title is the headline. Type-specific details (route legs, check-in dates, rating, cuisine) follow with a hairline separator. The card reads top-down like a chapter entry, not a tile with an icon bolted on.
- **Editorial type labels:** `TYPE_LABELS` maps backend `ItemType` values to editorially meaningful labels. Hotel → "Stay" (not "Hotel"), meal → "Dining" (not "Meal"). This aligns with the travel-chapter register.
- **Promoted title:** `text-[13px] font-semibold` vs old `text-xs font-semibold` — one step up in the typography ladder, enough to feel like a headline without competing with the day-column chapter heading.
- **Hairline rhythm:** Type-specific sections (flight route, hotel stay span, activity rating, dining details) gain `pt-1 border-t border-ds-pen-stroke/40` — a subtle visual separator that gives each block its own editorial space.
- **More breathing:** `p-3` (vs `p-2`) gives the card slightly more interior breathing, matching the editorial register of day-column chapter headers above.
- **Semantic element:** `<article>` is the correct HTML semantic for a self-contained chapter entry in a trip's itinerary.
- **Overline type role exact:** `text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary` — matches Design Bible Overline type role exactly (§4.4).
- **Action cluster unchanged in behavior:** All actions (remove, compare, move-to-ideas, timeline, booking, drag) are unchanged in handler wiring. They now live in the overline row's right side for cleaner layout.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL generation changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- Round-trip one-card rendering: preserved (`itinerary-roundtrip-flight` testid, `renderLeg(outboundLeg)` + `renderLeg(returnLeg)` in single card).
- Google Flights link-out: preserved (`itinerary-google-flights-cta` testid, `aria-label="Search on Google Flights"`, canonical URL fields, `-my-3.5 py-3.5` touch target).
- All TripBuilder logic, add-to-day behavior, ItineraryDayColumn, and AI Concierge panel unchanged.

### Accessibility / motion note
- No new motion, gradients, glass blur, or animations introduced in Phase 8C. The dragging state uses `opacity-60 scale-95 backdrop-blur-md` inherited from Phase 3 (pre-existing). No reduced-motion accommodation required for new Phase 8C changes. All interactive elements use `focus-visible:ring-2 focus-visible:ring-ds-accent` inherited patterns; no new interactive patterns added.

---

## Stage 3.5 Phase 8B — Trip Detail Travel Chapter + Planning Canvas Overhaul — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — `/trips/[id]` trip detail surface · Travel-chapter cover + advisor briefing**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/trips/[id]/page.tsx` | **Major redesign.** Removed: `DESTINATION_GRADIENTS`/`DEFAULT_GRADIENT`/`getDestinationGradient` (raw hex gradients), `destination-bg`/`destination-overlay` divs, `PageHeader` import+usage, inline tripContext header strip. New **TripChapterCover** `<section>` with: `data-testid="trip-chapter-cover"`, `aria-labelledby="chapter-destination-heading"`, back "My Journeys" Link, Overline "Travel Chapter", `<h1 id>` with real `trip.destination`, italic tripContext vibe, `CalendarDays text-ds-accent` dates row, day-count caption. Action cluster (`data-testid="chapter-actions"`) with 4 semantic buttons: AI Concierge (`COVER_PRIMARY`), Optimize, Edit Trip, Delete (`COVER_DANGER`) — all `min-h-[44px]`, `focus-visible:outline-ds-accent`. Modal dialogs updated from `bg-white/text-slate-*/border-slate-*` to `bg-ds-onyx/text-ds-text/border-ds-pen-stroke`. All `ds-elevation-4` for modals. Loading state updated to editorial chapter cover skeleton. All behavior (edit/delete/optimize/concierge/trip-builder/add-to-day) preserved. |
| `frontend/src/components/trips/TripReadinessCockpit.tsx` | **Advisor briefing transformation.** Removed: score indicator (`coveredCount/signals.length` fraction), "Trip Briefing" overline text → changed to "Concierge Notes", "Day Coverage" section overline label, "Next Step" overline label, "Also try" section label. Kept: all `data-testid` attributes, `aria-labelledby/id` pairing, all callbacks (onOpenConcierge/onOpenOptimize/onOpenEdit), all signal keys/itemType checks, all copy ("Looks like…"/"Still needs…"), day pills with `aria-label`, `role="list"`, signal grid. Signal grid changed from `items-start gap-2.5` to `items-center gap-2.5`. Next-step description now has `italic` for advisor tone. Day coverage summary phrase changed from "have plans" to "days planned". Planning tools strip: "Also try" label removed; links remain. |
| `frontend/tests/trip-chapter-overhaul.test.mjs` | **NEW.** 70 Phase 8B contract tests: chapter cover section/h1/aria structure, Overline pattern, destination-as-heading, trip-title-subtitle, context vibe italic, dates/day-count row, back link to /trips, action cluster testids, all 4 semantic buttons, min-h-[44px] via constant, focus-visible outline, no card-level onClick on section, ds-token coverage, no raw hex (no DESTINATION_GRADIENTS/destination-bg), no bg-white/text-slate/border-slate/sky-500 in modals, no PageHeader import, no fake/mock data, no backend/provider imports, preserved TripReadinessCockpit/TripBuilder/AIConciergePanel/OptimizeTripModal, chapter-before-cockpit ordering, cockpit-before-builder ordering, preserved callbacks, advisor briefing structure (Concierge Notes overline, no score, no DAY COVERAGE/NEXT STEP/ALSO TRY labels, italic next-step, honest signal copy). |
| `frontend/package.json` | Added `trip-chapter-overhaul.test.mjs` to test script. |

### Test results
- **962 tests, 0 failures** (was 892; +70 new Phase 8B chapter overhaul contract tests)
- All pre-existing tests continue to pass (including trip-canvas-day-system, trip-readiness-cockpit)

### Design contract alignment

- **Travel chapter, not dashboard:** `/trips/[id]` now opens with a `<section>` editorial chapter cover rather than a PageHeader + context widget + toolbar. Destination is the large `<h1>` heading, trip title is a subtitle, context vibe is italic caption prose. No score tiles, no progress rings, no KPI indicators.
- **Destination identity:** `trip.destination` is now the primary h1 heading. The old colorful OTA-style destination-gradient backgrounds (raw hex, conflict with Design Bible dark-mode system) are removed. The page uses the dark ink-ladder system consistently.
- **Advisor briefing:** TripReadinessCockpit "Concierge Notes" overline + adaptive h2 headline. No score fraction. Day pills remain (contextual at-a-glance), but the "DAY COVERAGE" dashboard label is gone. Signals present as natural advisor observations. Next-step prose is italic. No labels ("NEXT STEP", "ALSO TRY") that read like productivity UI chrome.
- **Semantic actions:** All 4 actions (AI Concierge, Optimize, Edit Trip, Delete) are real `<button>` elements with explicit `onClick`, `data-testid`, `min-h-[44px]`, `focus-visible:outline-ds-accent`. Arranged naturally within the chapter cover — not a toolbar.
- **Modal ds-tokens:** Edit and Delete modals updated from `bg-white/text-slate-*/border-slate-*/ring-sky-500` to `bg-ds-onyx/text-ds-text/border-ds-pen-stroke/ring-ds-accent`.
- **Mobile:** Cover, advisor briefing, and planning canvas stack cleanly. Action cluster wraps with `flex-wrap`. No horizontal overflow risk.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache/Supabase/env changes.
- No Google Flights URL changes; no Duffel provider changes.
- No new fonts, route rewrites, or data model changes.
- No new booking behavior; no fake data.
- All TripBuilder logic, add-to-day behavior, itinerary item cards, and AI Concierge panel unchanged.

---

## Stage 3.5 Phase 8A — Private Atelier Home + Journey Shelf — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — `/` home + `/trips` My Journeys surfaces · Atelier-home transformation + travel-volume journey shelf**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/dashboard/DashboardClient.tsx` | **Major redesign.** Removed 4 KPI stat cards (Total Trips, Upcoming, Travel Cards, Total Points), RecentTrips, QuickActions, PointsSummary, DealsFeed. New layout: (1) `AtelierGreeting` — editorial time-based greeting + real `summary.tripCount` shelf count, Overline "Private Travel Concierge"; (2) `ConciergeEntry` — primary ds-elevation-2 card with Sparkles icon, "AI Travel Concierge" h2, description, `Open Concierge` link with 44px target + focus-visible ring; (3) `ContinuePlanningStrip` — most-active trip card using real `getTripStatusGroup`/`STATUS_PRIORITY` sort, with `Link href=/trips/${trip.id}`, `TripStatusBadge`, destination + dates from real data; (4) `JourneyShelfTeaser` — `Link href=/trips` with real `summary.tripCount`, "Browse your full journey shelf" copy; (5) `EmptyAtelierHome` — editorial empty state with Plan a Trip + Open Concierge CTAs; (6) `AtelierPlanningStrip` — 2-column Explore + Saved Ideas grid. All ds-* tokens, `bg-ds-accent-subtle`, `text-ds-accent`, focus-visible rings, no legacy colors. `fetchDealsFeed`/`fetchCards` calls removed. |
| `frontend/src/app/trips/page.tsx` | **Visual upgrade.** `JourneyCard` redesigned as travel-volume cover: destination (`trip.destination`) is now the large `text-lg font-semibold` hero text; trip title is the `<Link href=/trips/${trip.id}>` subtitle (semantic navigation); status badge at top; card-footer has date+travelers + "Open →" Link (44px); edit/delete buttons with aria-labels preserved; MapPin icon removed (destination text is the identity). `ContinuePlanningHero` elevated: destination is now an editorial overline above the trip title `<h2>`; action footer separated with `border-t`. Page header gains editorial "Your Travel Shelf" overline above "My Journeys" h1. All existing function names, props, interfaces, and modals unchanged. |
| `frontend/src/app/page.tsx` | Metadata title changed from `"Dashboard"` to `"Home"`. |
| `frontend/tests/atelier-home-journey-shelf.test.mjs` | **NEW.** 56 Phase 8A contract tests: atelier-greeting/concierge-entry/atelier-home testids, time-based greeting, real tripCount, no KPI imports, ds-token contract, no legacy colors, no card-level onClick nav, no fake data, focus-visible rings, ConciergeEntry semantic Link, ContinuePlanningStrip real trip id link, JourneyShelfTeaser /trips link, AtelierPlanningStrip Explore/Saved links, JourneyCard destination-as-hero, travel-volume footer, editorial overline in page header, preserved create/edit/delete/open affordances, no backend/provider imports. |
| `frontend/package.json` | Added `atelier-home-journey-shelf.test.mjs` to test script. |

### Test results
- **892 tests, 0 failures** (was 836; +56 new Phase 8A atelier home + journey shelf contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Private atelier home:** `/` no longer leads with KPI stat tiles. It opens with a time-based editorial greeting using real trip count, then positions the AI Concierge as the primary planning instrument (elevation-2 card, prominent CTA). Secondary: continue-planning strip (real data), journey shelf teaser, discovery tools. No fake personalization, no user name invented, no fabricated stats.
- **Journey shelf:** `/trips` JourneyCard now reads destination as the large editorial title (like the front of a travel volume). Status is a quiet overline marker. Trip title is the semantic navigation link. Dates and traveler count anchor the footer. The card communicates "this is a travel place" not "this is a SaaS record."
- **Concierge elevation:** Concierge is now the lead CTA on the home page — not buried in a "Quick Actions" grid. This matches Design Bible Addendum §1 (private atelier) and Design Bible §26 (AI launch pill).
- **Editorial greeting:** "Good morning/afternoon/evening." + "{N} trips on your shelf." — all real data (time of day + `summary.tripCount`). No invented name, no fake stat.
- **Token contract:** No raw hex, no legacy `cream-*`/`brand-*`/`violet-*`/`emerald-*`/`amber-*` colors in changed files. All surfaces use ds-* tokens. `bg-ds-accent-subtle` on icon wrappers. `text-ds-accent` on accent elements. `border-ds-pen-stroke` / `bg-ds-carbon` / `bg-ds-onyx` on surfaces.
- **Semantic navigation:** All navigation via real `<Link href>` or `<button onClick>`. No `onClick={() => router.push}` patterns. No card-level click-only navigation.
- **Touch targets:** `min-h-[44px]` on all primary CTAs and action buttons. `min-w-[44px]` on icon-only buttons.
- **Accessibility:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` on all interactive elements. `aria-label` on icon-only buttons. `aria-hidden="true"` on decorative icons. `aria-busy="true"` on loading skeleton.
- **Mobile:** 2-column discovery strip (Explore + Saved). EmptyAtelierHome uses `flex-col sm:flex-row` for stacked-then-side-by-side CTAs. JourneyCard grid `md:grid-cols-2 xl:grid-cols-3` for responsive shelf.

### Invariant confirmations
- No backend files, no API/search/provider/Tavily/cache changes.
- No Supabase SQL, no new env vars, no new dependencies.
- No new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data.
- All existing edit/delete/create/open affordances preserved on `/trips`.

---

## Stage 3.5 Phase 7 — Trip Readiness / Review Cockpit — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip detail `trips/[id]` surface · Premium trip-planning intelligence cockpit**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/TripReadinessCockpit.tsx` | **NEW.** `<section aria-labelledby>` root with 5 zones: (1) header bar — Overline "Trip Briefing" + `<h2>` headline + N/4 score indicator; (2) day coverage strip — filled/empty day pills (`bg-ds-accent` / `border-ds-pen-stroke`) with `role="list"` + per-pill `aria-label`; (3) signal grid — 4 category signals (Flights/Stay/Dining/Activities) with `bg-[var(--ds-accent-subtle)]` icon ring when present; (4) next-step footer — contextual CTA prioritised dates→flights→hotel→empty days→all good, real `<button>` callbacks + `<Link>` routes; (5) planning tools strip — Explore / Saved Ideas / AI Concierge links. All ds-* tokens. `min-h-[44px]` on action buttons. `focus-visible:outline-ds-accent` on all interactives. `aria-hidden="true"` on all icons. |
| `frontend/src/app/trips/[id]/page.tsx` | Import + conditional render of `TripReadinessCockpit` (guarded by `trip !== null`) between `PageHeader` and `TripBuilder`. Props: `trip`, `itineraryDays`, `onOpenConcierge`, `onOpenOptimize`, `onOpenEdit`. |
| `frontend/tests/trip-readiness-cockpit.test.mjs` | **NEW.** 65 static/contract tests: semantic section/h2 structure, data-testid contract, ds-* token coverage, Overline pattern, aria-hidden icons, 44px touch targets, focus-visible rings, real Link/button elements only, no card-level onClick, no backend imports, no fake data, signal key coverage, empty-data defensive handling, page integration wiring. |
| `frontend/package.json` | Added `trip-readiness-cockpit.test.mjs` to test script. |

### Test results
- **836 tests, 0 failures** (was 771; +65 new Phase 7 readiness cockpit contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Editorial advisory tone:** Overline "Trip Briefing" + `<h2>` headline copy adapts to data density ("Start by adding your travel dates" / "Good progress — a few gaps to fill" / "Your trip is looking well-planned"). Reads like a private advisor's briefing, not a SaaS checklist.
- **Dark tone surface:** Root `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-2)]` — correct ink-ladder elevation above body.
- **Footer tonal shift:** Next-step area uses `bg-ds-carbon` — one step darker, creates editorial anchor at bottom of section.
- **Signal icons:** Present = `bg-[var(--ds-accent-subtle)] text-ds-accent` round icon; missing = `border-ds-pen-stroke text-ds-text-tertiary` empty ring. Clear visual grammar without traffic-light colors.
- **Day coverage pills:** Filled = `bg-ds-accent text-ds-text-inverse`; empty = `border-ds-pen-stroke text-ds-text-tertiary`. Compact at `w-7 h-7`. Adaptive summary text.
- **Overline labels:** All section labels use exact `text-[10px] font-semibold uppercase tracking-[0.1em]` Overline pattern.
- **Next-step CTAs:** Primary = `bg-ds-accent text-ds-text-inverse`; secondary = `border-ds-pen-stroke text-ds-text-secondary hover:bg-ds-carbon`. Real `<button>` for callbacks, `<Link>` for routes.
- **Accessibility:** Full semantic structure — `<section aria-labelledby>`, `<h2 id>`, `role="list"` on day pills, `role="listitem"` on each pill, `aria-label` on pills and icon-only button, `aria-hidden` on all decorative icons.
- **Touch targets:** `min-h-[44px]` on action buttons. Planning tools strip links are text links (not primary actions).
- **No card-level click-only navigation:** Root `<section>` has no `onClick`. All navigation via real `<button>` or `<Link>`. Confirmed by contract test.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache changes.
- No Supabase SQL; no new env vars; no new dependencies.
- No new fonts; no route rewrites; no data model changes.
- No new booking behavior; no fake data.
- Existing TripBuilder, ItineraryDayColumn, ItineraryItemCard, AIConciergePanel behavior fully preserved.

---

## Stage 3.5 Phase 5 — TripBuilder Command Surface — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — TripBuilder left-panel search + CandidatePanel command center**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/TripBuilder.tsx` | CandidatePanel: removed `accentColor` prop, root → `rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)]`, toggle button `min-h-[44px] px-4 py-3`, count badge → styled pill with `var(--ds-accent-subtle)` bg + `text-ds-accent border-ds-pen-stroke`. Activities section: `.card p-3` → `rounded-2xl border border-ds-pen-stroke bg-ds-onyx shadow-[var(--ds-elevation-1)]` with ds-token header row. Compare bar: `shadow-2xl` → `shadow-[var(--ds-elevation-4)]`, added Overline "Compare" label + `tracking-[0.1em]`, dots `w-2 h-2` → `w-1.5 h-1.5`. DragOverlay + toast: `shadow-2xl` → `shadow-[var(--ds-elevation-3)]`. Right panel header: "Itinerary" plain h2 → Overline "Your Itinerary" + item count as `text-ds-text-tertiary`. Target day selector: bare select → `bg-ds-carbon rounded-xl border-ds-pen-stroke` container with Overline "Add to" label. Add Day button: `btn-ghost` → explicit ds-token button with `min-h-[44px]`. Explore header: `tracking-wider` → `tracking-[0.1em]`. Planning cockpit header: new `destination` + selected day context above SummaryBar. Flight sub-labels: `tracking-[0.08em]` → `tracking-[0.1em]`, added `px-1 pb-1` / `pt-2 pb-1`. Filter-empty copy: "No X match..." → "Nothing matches the current filters — try widening the selection." |
| `frontend/tests/tripbuilder-command-surface.test.mjs` | NEW. 32 static/contract tests: no legacy classes, ds-token coverage, Overline tracking, planning cockpit header, compare bar, Add Day touch target, behavior preservation. |
| `frontend/package.json` | Added `tripbuilder-command-surface.test.mjs` to test script. |

### Test results
- **724 tests, 0 failures** (was 692; +32 new Phase 5 command surface contract tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **CandidatePanel chrome:** Full ds-token card pattern; count badge is a styled pill with accent-subtle bg. No legacy `.card` class.
- **Overline type role:** All section/area labels use exact `text-[10px] font-semibold uppercase tracking-[0.1em]` Overline pattern.
- **Planning cockpit header:** Destination + selected day context above SummaryBar — clear command center orientation.
- **Compare bar:** Elevation-4 shadow, Overline "Compare" label, smaller dots. More editorial, less dashboard.
- **Target day selector:** Contained in `bg-ds-carbon rounded-xl border-ds-pen-stroke` with "Add to" Overline label. Clear context of which day will receive additions.
- **Add Day button:** Explicit ds-token button with `min-h-[44px]` touch target. No legacy `btn-ghost`.
- **Behaviors preserved:** DnD, compare, Google Flights link-out, round-trip one-card rendering, GSAP `candidate-card` class, hotel/attraction/restaurant/flight add-to-itinerary all unchanged.

### Invariant confirmations
- No backend files; no API/search/provider/Tavily/cache changes.
- No Supabase SQL; no new env vars; no new dependencies.
- No new fonts; no route rewrites; no data model changes.
- No new booking behavior; no fake data.

---

## Stage 3.5 Phase 4 — Trip Detail Planning Canvas / Itinerary Day System — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip planning canvas · Day-column hierarchy and empty-state redesign**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryDayColumn.tsx` | Full ds-* migration: all `slate-*`/`amber-*`/`sky-*`/`violet-*` classes removed. Day column root → `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-2)]`. Chapter header: zero-padded number marker (`bg-ds-accent` when selected), `Day N` title in `text-ds-text`, date as Overline (`text-[10px] font-semibold uppercase tracking-[0.1em] text-ds-text-tertiary`). Day-part colors: morning=`text-ds-accent`, afternoon=`text-ds-text-secondary`, evening=`text-ds-accent-muted`, unscheduled=`text-ds-text-tertiary`. Expanded body bg → `var(--ds-midnight-ink)` (ink-ladder depth). All action buttons: `min-h-[44px] min-w-[44px]` touch targets + `focus-visible:outline-ds-accent`. Empty-day invitation: editorial "Day N / Drag items here or use + Add" with `border-dashed border-ds-pen-stroke` (normal) and `border-ds-accent/60 + var(--ds-accent-subtle)` bg (drag-over). Travel connectors → `bg-ds-pen-stroke`/`text-ds-text-tertiary`/`text-ds-warning`. SuggestionsReviewPanel → `bg-ds-carbon border-ds-pen-stroke`. DayTravelHintBar → `bg-ds-carbon border-ds-pen-stroke`. Show all/less → `border-ds-pen-stroke bg-ds-carbon text-ds-text-secondary`. |
| `frontend/src/app/trips/[id]/page.tsx` | Trip context header: `bg-brand-600/15 border-brand-500/30 text-brand-300` → `border-ds-pen-stroke text-ds-accent bg-[var(--ds-accent-subtle)]`. `text-cream-300` → `text-ds-text`. Toast: `bg-slate-800 text-white` → `bg-ds-onyx border-ds-pen-stroke text-ds-text shadow-[var(--ds-elevation-2)]`. Back link + loading state → `text-ds-text-tertiary hover:text-ds-text`. Loading card → `border-ds-pen-stroke bg-ds-onyx rounded-lg`. |
| `frontend/src/components/trips/TripBuilder.tsx` | No-days empty state: `.card p-8` → `rounded-lg border border-ds-pen-stroke bg-ds-onyx p-8`. |
| `frontend/tests/trip-canvas-day-system.test.mjs` | 57 new static/contract tests: ds-token coverage, 44px touch targets, focus rings, Overline tracking, empty-state editorial design, selected-day accent, behavior contract preservation, trip detail page legacy removal, TripBuilder no-days state. |
| `frontend/package.json` | Added `trip-canvas-day-system.test.mjs` to test script. |

### Test results
- **692 tests, 0 failures** (was 614; +57 new Phase 4 day-canvas contract tests + carried through from previous phases)
- All pre-existing tests continue to pass

### Design contract alignment

- **Chapter hierarchy:** Day columns have chapter-style headers: zero-padded number marker, "Day N" title, Overline date. Editorial weight, not dashboard chrome.
- **Ink-ladder elevation:** Expanded body uses `var(--ds-midnight-ink)` (darker than `bg-ds-onyx` card shell) — correct depth relationship per Design Bible §8 ink-ladder.
- **Day-part Overline labels:** `text-[10px] font-semibold uppercase tracking-[0.1em]` — matches Overline type role exactly.
- **Empty-day invitation:** No utilitarian "No plans yet." Editorial invitation with actionable "+ Add" inline link. Dashed border with accent on drag-over.
- **Touch targets:** All header action buttons at `min-w-[44px] min-h-[44px]`. Inline empty-state + Add link is a button with focus-visible ring.
- **Selected state:** `border-ds-accent/40 ring-ds-accent/20` on column root. Number marker: `bg-ds-accent text-ds-text-inverse`. Header: `bg-ds-carbon`.
- **Travel connectors:** Subdued — `bg-ds-pen-stroke` divider, `text-ds-text-tertiary` for distance/time, `text-ds-warning/70` for far-apart alert.
- **No legacy classes:** Zero `slate-*`, `amber-*`, `sky-*`, `violet-*` in ItineraryDayColumn. Zero `brand-*`, `cream-*` in trip detail page shell.
- **Behavior preserved:** DnD droppable, SortableContext, isExpanded, PREVIEW_ITEM_LIMIT, handleSuggestTimeline, handleApplyTimeline, onPlanDay, onUpdateTimeline, onMoveItemToIdeas, itemOverrides all unchanged.

### Invariant confirmations
- No backend files, no API/provider/Tavily/cache changes, no Supabase SQL.
- No new dependencies, no new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data, no new animation library.
- Pre-existing TypeScript errors in TripBuilder.tsx (missing module types): unchanged, pre-existing.

---

## Stage 3.5 Phase 3 — Trip Planning Card System Breadth — SHIPPED (2026-05-16)

**Stage 3.5 · Wife-Wow design system — Trip planning surfaces · Card variant breadth**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/components/trips/ItineraryItemCard.tsx` | Full ds-* migration: root bg/border/shadow → `bg-ds-onyx border-ds-pen-stroke shadow-[var(--ds-elevation-1)]`. All typeConfig icons → unified `text-ds-accent` + inline `var(--ds-accent-subtle)`. All text colors → ds-text-*/ds-text-tertiary. Google Flights link → `text-ds-text-secondary hover:text-ds-accent`. Remove button hover → `text-ds-warning`. Hotel area badges → `text-ds-trust-verified`/`text-ds-caution` + inline rgba. Timeline input → `bg-ds-carbon border-ds-pen-stroke`. Focus rings on all interactive elements. |
| `frontend/src/components/trips/TripIdeasPanel.tsx` | Full ds-* migration: IdeaCard border/bg → `border-ds-pen-stroke bg-ds-onyx`. Status options, filter chips, inputs, selects, buttons → ds-* tokens. Panel header/active count/Add to Day button → ds-accent. Show more/less → `border-ds-pen-stroke bg-ds-onyx text-ds-text-secondary`. |
| `frontend/src/components/trips/SearchResultCard.tsx` | Migrated to `Card tone="dark" as="article"`. Uses `Card.Identity` + `Card.Meta` slots. Category icon → unified `text-ds-accent` + inline accent-subtle. Compare/add buttons → ds-* tokens. Area badges → `text-ds-trust-verified`/`text-ds-caution` + inline rgba. Tags → `bg-ds-carbon text-ds-text-tertiary border-ds-pen-stroke`. |
| `frontend/src/components/trips/TripBuilder.tsx` | PREMIUM_CARD_BASE/SECONDARY_CTA/PRIMARY_CTA → ds-* tokens (candidate-card class preserved). AiScoreBadge → ds-trust-verified/ds-caution with inline rgba bg. SortControl/FilterPills active → `bg-ds-accent text-ds-text-inverse`. All card components (FlightCandidateCard, FlightLegRow, RoundTripFlightCard, HotelCandidateCard, AttractionCandidateCard, RestaurantCandidateCard) → ds-* tokens. RecTag/AttractionTag/RestaurantTag → unified `text-ds-accent border-ds-pen-stroke` + inline accent-subtle. Top pick badges (Best Pick/Best Pair/Top Hotel/Top Pick) → `bg-ds-accent text-ds-text-inverse`. Compare bar → `bg-ds-onyx border-ds-pen-stroke`. Toast → ds-* tokens. CandidatePanel section icons → `text-ds-accent`. Explore toggle → `bg-ds-carbon`/`bg-ds-onyx`. SummaryBar → `bg-ds-onyx border-ds-pen-stroke`. |
| `frontend/src/components/explore/FlightExploreFlow.tsx` | FlightCard → `Card tone="dark" as="article"`. All flight card, leg row, empty/error/unavailable states → ds-* tokens. Search form icon residuals → `text-ds-text-tertiary`. |
| `frontend/tests/trip-planning-card-tokens.test.mjs` | 24 new token-coverage tests verifying ds-* adoption and no-legacy-class invariants across all 5 migrated files. |
| `frontend/package.json` | Added `trip-planning-card-tokens.test.mjs` to the test script. |

### Test results
- **614 tests, 0 failures** (was 590; +24 new Phase 3 token coverage tests)
- All pre-existing tests continue to pass

### Design contract alignment

- **Dark tone cards:** All trip-planning card surfaces use `tone="dark"` or equivalent `bg-ds-onyx border-ds-pen-stroke` treatment.
- **Token alignment:** No raw hex, no legacy `cream-*`/`brand-*`/`dark-*`/`sky-*`/`violet-*`/`emerald-*`/`rose-*`/`amber-*`/`slate-*`/`white/` classes in any migrated card or helper function.
- **Unified accent:** All tag badges, icons, and active states use `text-ds-accent` (sandstone gold).
- **Semantic status:** Trust indicators (`text-ds-trust-verified`), caution (`text-ds-caution`), warning (`text-ds-warning`) — no raw color for semantic signals.
- **Inline accent-subtle:** `var(--ds-accent-subtle)` used as inline style for bg since not in `@theme`.
- **Focus rings:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2` on all interactive elements.
- **44px touch targets:** Preserved on all buttons/links/drag handles.
- **candidate-card class:** Preserved in PREMIUM_CARD_BASE for GSAP querySelector targeting.
- **All existing actions preserved exactly:** DnD drag/drop, add-to-itinerary, compare, Google Flights link-out, round-trip add, hotel/attraction/restaurant add, remove, save/unsave, sort, filter.

### Invariant confirmations

- No backend files, no API/provider/Tavily/cache changes, no Supabase SQL.
- No new dependencies, no new fonts, no route rewrites, no data model changes.
- No new booking behavior, no fake data.
- Pre-existing 3 FlightCard test failures: unchanged (outside this scope).

---

## Stage 3.5 Phase 2A — AI Concierge Flagship Visual Breakthrough — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — AI Concierge `/concierge` surface · Card-first flagship canvas**
**Behavior change:** Converts `/concierge` from a placeholder page to a live standalone AI Concierge route using the existing `/ai/concierge/search` backend contract (`callConciergeSearch(null, query)`). No backend/API/provider contract changes. Frontend route behavior changes from placeholder → live search.

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/concierge/page.tsx` | Route replaced: was a placeholder ("AI Concierge coming soon"), now imports and renders `ConciergePage`. Server component with Metadata. |
| `frontend/src/components/concierge/ConciergePage.tsx` | NEW. Full-page client component: editorial header (Overline "Private Travel Concierge" + Display S headline), card-first result canvas, sticky composer at bottom. Uses `Card tone="dark"` primitive for result cards. `TrustStrip confidence={...}` (actual backend `googleVerification.confidence`) where `canShowGoogleVerifiedBadge` passes — no fabricated `sourceCount`. Cards render `pickCardCategory`, `pickCardReason`, `sanitizeWhyPick`, `pickCardMeta`, map/source links from canonical `googleVerification.googleMapsUri`. All business logic reuses `cardPresentation.js` and `refinementInterpreter.js` unchanged. Refinement chips (Show only casual, Compare top 2, Find cheaper nearby / Find more like these) from existing interpreter. Empty state: 4 editorial prompt chips. Loading: "Searching · Verifying · Composing" typeset breadcrumb + spinner. Error: named constraint + "Try again" link. No add-to-day / save-to-ideas (no trip context on standalone page). `callConciergeSearch(null, query, requestId)` — tripId=null per existing API contract. |
| `frontend/src/components/layout/Sidebar.tsx` | Added `{ label: "Concierge", href: "/concierge", icon: Sparkles }` to `primaryLinks` (after Explore). Desktop sidebar navigation now exposes the Concierge surface. |
| `frontend/src/components/layout/MobileNav.tsx` | Added `{ label: "Concierge", href: "/concierge", icon: Sparkles }` to `links` (slide-out drawer). Mobile navigation drawer now exposes the Concierge surface. |

### Design contract alignment

- **Dark mode surface:** `bg-ds-midnight` body (via AppShell), `Card tone="dark"` for result cards (`bg-ds-onyx border-ds-pen-stroke text-ds-text`).
- **Tonal hierarchy (§9):** Midnight Ink body → Onyx Velvet cards and composer → Carbon Mist button backgrounds.
- **Card-first hierarchy (§25):** No chat bubbles. User queries are silent state only. Result cards are the visual hero.
- **Editorial composition:** Overline + Display S header. Cards use Body L name, Overline category, Body S meta. Concierge note uses Body S with Accent Subtle left-border.
- **Sticky composer:** `position: sticky; bottom: 0` within the main scroll context. Textarea with resize-on-content. 44×44px minimum send button with accent gold background.
- **Loading state (§11):** "Searching · Verifying · Composing" typeset breadcrumb — honest static treatment (no fake stage progression since pipeline timing not exposed to frontend).
- **Empty state (§11):** Editorial invitation with 4 themed prompt chips. Not "Ask me anything."
- **Error state (§11):** Named constraint message (`text-ds-warning`) + "Try again" retry action.
- **Trust strip (§23):** `TrustStrip confidence={...}` only when `canShowGoogleVerifiedBadge` passes (OPERATIONAL + high/medium confidence + providerPlaceId). `confidence` value is read directly from `googleVerification.confidence` on the backend payload — never hardcoded. `sourceCount` never fabricated. `verified` prop never set (OPERATIONAL status is not the same as the "Verified by Google" explicit confirmation contract).
- **Token alignment:** No raw hex. No legacy `emerald-*`, `amber-*`, `cream-*`, `slate-*`, `white/` classes. All surfaces use `ds-*` Tailwind utilities or `var(--ds-*)` inline styles.
- **Spacing:** All padding/margin/gap via `var(--ds-space-*)` CSS variables.
- **Typography:** All font-size/line-height via `var(--ds-type-*-size)` / `var(--ds-type-*-leading)` CSS variables.
- **Accessibility:** All interactive elements have `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. `aria-label` on map/source links. `role="status"` on loading state. `role="alert"` on error state. `aria-live="polite"` on result canvas.
- **Mobile:** Composer `position: sticky; bottom: 0` — always visible on scroll. Textarea auto-resizes. Touch target ≥44px on all interactive elements.
- **Motion:** `card-lift` for card hover (120ms/200ms via existing motion tokens). `transition-colors duration-[120ms]` on buttons. `animate-spin` on Loader2 icons. No transforms >400ms. No typewriter, no glow, no parallax.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule governs all transitions (Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, backend, or SQL files changed.
- No new dependencies added.
- No route rewrites — `/concierge` route preserved.
- `AIConciergePanel.tsx` unchanged — trip-panel add/save behavior fully preserved.
- `lib/concierge/cardPresentation.js`, `refinementInterpreter.js`, `types.ts`, `priceFormatter.js` unchanged.
- `lib/api.ts` unchanged — `callConciergeSearch(null, ...)` pre-existing API contract.
- All card action handlers, addability gate, verification gate, map/source link derivation preserved from existing library functions.
- No add-to-day / save-to-ideas on standalone page — these require a `tripId` and belong to the trip-panel flow. Discovery surface only.

### Visual tradeoffs for later phases

- Standalone page has no add-to-trip/save-to-ideas (requires trip context). To add a found place to a trip, user navigates to My Trips and uses the AI Concierge panel there.
- Conversation history: standalone page maintains session state in component state only (no persistence). Persistent history requires a tripId. This is the correct scope boundary.
- No left conversation rail (Design Bible §25): standalone page uses a simpler header-only layout. The rail is scoped to the trip-panel variant and can be added in a future Phase 2B when trip context is present.
- Area comparison table from AIConciergePanel not ported — this is a trip-specific feature and complex to slot correctly without a trip context.
- Orchestration helpers (`hasClosedSignal`, `canShowGoogleVerifiedBadge`, `pickCardMeta`) are re-implemented in `ConciergePage.tsx` with identical logic because `AIConciergePanel.tsx` does not export them. Phase 2B should consolidate shared concierge presentation helpers into a shared module.

---

## Stage 3.5 Phase 1C — Saved Ideas Paper/Scrapbook Adoption — SHIPPED (2026-05-15)

**Stage 3.5 · Wife-Wow design system — Saved Ideas `/saved` surface · Paper/scrapbook warm-paper tone**

### What shipped

| File | Change summary |
|---|---|
| `frontend/src/app/globals.css` | Added `.card-paper` CSS modifier class: `box-shadow: none` for base; `card-lift` hover on paper = `translateY(-2px)` + no shadow + `border-color: var(--ds-linen)` (luminance-only lift, §8 contract). |
| `frontend/src/components/ui/Card.tsx` | Paper TONE_CLASSES adds `card-paper` to suppress dark shadow on paper cards. Added `"data-testid"?: string` to `CardProps` for test-compatible usage. |
| `frontend/src/components/saved/SavedShell.tsx` | `SavedItemCard` adopts `Card tone="paper" as="article" className="card-lift p-4"` with `Card.Identity` slot for icon + content row. Vertical icon: `bg-ds-accent-subtle` (inline style) + `text-ds-accent`. Title: `text-ds-text-inverse`. Secondary text: `text-ds-slate`. Rating star: `text-ds-accent fill-current`. Tags: `border-ds-hairline text-ds-slate`. Action buttons: `bg-ds-bone hover:bg-ds-linen` / `hover:bg-ds-hairline`. Error: `text-ds-warning`. Success: `text-ds-trust` icon + `text-ds-text-inverse`. Section header icon: `text-ds-accent-muted`. Section label: `text-ds-text-inverse`. SavedShell container: `bg-ds-linen rounded-2xl` (linen album on midnight ink body). Empty/loading/error states updated to paper-mode colors. All action handlers, grouping, ordering, payloads, and behavior unchanged. |

### Design contract alignment

- **Paper tone adopted:** `SavedShell` container = `bg-ds-linen` (aged-paper album). `SavedItemCard` = `Card tone="paper"` (warm paper, §9 — Saved Ideas paper mode).
- **Tonal hierarchy (§9):** Midnight Ink body → Linen album container → Warm Paper cards. Surface mode changes at route level.
- **Card.Identity slot:** Icon + content flex row. Vertical icon bg = `var(--ds-accent-subtle)`. Icon color = `text-ds-accent`. All text in ink-paper tones.
- **Paper elevation (§8):** `.card-paper` suppresses dark box-shadow. Hover = luminance-only (border to linen, 2px lift, no shadow). No drop-shadows on paper surface.
- **Token alignment:** No raw hex in changed files. No legacy `cream-*`, `brand-*`, `amber-*`, `rose-*`, `white/` classes in saved cards. All colors via `ds-*` Tailwind utilities or `var(--ds-*)` inline style.
- **Accessibility:** All interactive elements retain `focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent focus-visible:outline-offset-2`. Icon containers `aria-hidden="true"`. Semantic `as="article"` on card root.
- **Motion:** `card-lift` class used; `.card-paper.card-lift` override governs paper hover (120ms/200ms via existing motion tokens). No new animations.
- **Reduced-motion:** Global `@media (prefers-reduced-motion: reduce)` rule still governs (shipped Phase 0).

### Invariant confirmations

- No provider, search, API, Tavily, flight, hotel, or backend files changed.
- No Supabase SQL required.
- No new dependencies added.
- No route, auth/session, or data contract changes.
- All action handlers (deleteSavedItem, addSavedItemToTrip, createTrip, router.push, onRemove, onCreateTrip) preserved exactly.
- All payloads, verticals, grouping, ordering, and filter behavior unchanged.
- Add-to-trip, create-trip, delete/remove, filter, open/maps-link, and navigation unchanged.

### Limitation note

`--ds-accent-subtle` (rgba alpha) is defined in `:root` but not wired into `@theme`. Icon background in `SavedItemCard` uses `style={{ backgroundColor: "var(--ds-accent-subtle)" }}` directly. Empty-state icon uses `bg-ds-bone` (paper surface step) as a simpler paper-appropriate alternative within test char-window constraints. Both are acceptable paper-mode treatments.

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
