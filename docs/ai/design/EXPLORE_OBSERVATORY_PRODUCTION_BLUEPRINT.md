# Explore Observatory — Production Implementation Blueprint

**Status:** Implementation blueprint · ready for ONE PR from current `main` (after approval)
**Source concept (approved):** `docs/ai/concepts/explore-observatory-concept-v1.1.html`
**Sibling reference (do not copy):** `docs/ai/concepts/concierge-salon-concept-v1.html` + `docs/ai/design/CONCIERGE_SALON_PRODUCTION_BLUEPRINT.md`
**Target route:** `/explore` (outside-trip Explore). In-trip discovery surfaces are **out of scope**.
**Primary target files:** `frontend/src/components/explore/ExploreShell.tsx` + `frontend/src/app/globals.css` (new OBSERVATORY section). The four vertical flows get a **bounded result-card + index-header reskin only**.

This blueprint translates the approved v1.1 prototype into the real Explore code **without** changing routing, providers, API contracts, search behavior, or saved-item behavior. It exists so the implementer ports the *composition and material language*, not the prototype's demo wiring. The guardrails in §11 and the out-of-scope list in §12 are the contract.

---

## 1. Current Explore component / route inventory

| Layer | File | Role |
|---|---|---|
| Route | `frontend/src/app/explore/page.tsx` | Server component; renders `<ExploreShell />`. Metadata only. |
| Shell | `frontend/src/components/explore/ExploreShell.tsx` | Landing room (4 `VerticalCard`s) + active-vertical view (breadcrumb + instrument header + the chosen flow). Local `useState<ExploreVertical | null>` (`active`). |
| Flow | `RestaurantExploreFlow.tsx` | Destination-only search → `searchRestaurants` → `RestaurantSearchResult[]`. |
| Flow | `AttractionExploreFlow.tsx` | Destination + optional interest → `searchAttractionsExplore` → `ExploreAttractionResult[]`. |
| Flow | `HotelExploreFlow.tsx` | Destination + check-in/out + guests → `searchHotelsExplore` → `ExploreHotelResult[]`. Discovery-only; "Compare prices" Google Hotels link-out. |
| Flow | `FlightExploreFlow.tsx` | `CityAutocomplete` origin/destination + dates + pax + cabin → `searchFlightsExplore` → `FlightExploreResponse` (`ok`/`empty`/`unavailable`/`error`). |
| Shared action | `ResultActionSheet.tsx` | Save/Unsave (`saveItem`/`deleteSavedItem`), "More" → "Manage in Saved" / "Save first…" hint. Add-to-trip lives in `/saved`. |
| Primitives | `components/ui/Card.tsx`, `TrustStrip.tsx`, `CityAutocomplete.tsx` | Card slots, trust signals, airport autocomplete (PR #431 — frozen). |
| Types | `components/explore/types.ts`, `types/index.ts`, `lib/api.ts` | `ExploreVertical`, `ExploreResultContext`, result interfaces. |

**CSS primitives already in play (`globals.css`):** `folio-cinema-lounge` (shell wrapper), `folio-cinema-card` (search instrument section), `folio-cinema-tile` (vertical entry card), `folio-cover-tab`, `editorial-section-rule`, `card-lift`. The Concierge salon vocabulary lives in the ATELIER ROOM SYSTEM section (`~7379+`): `.atelier-salon-portal` + depth layers — **reference for material language, not to be reused verbatim** (Explore is a different room).

**Existing testids (must be preserved unless explicitly justified):** `explore-home`, `explore-lounge-header`, `explore-vertical-grid`, `vertical-card-{flights|hotels|restaurants|attractions}`, `explore-vertical-flow`, `explore-lounge-breadcrumb`, `{vertical}-flow`, `explore-instrument-header`, `restaurant-results`, `attraction-results`, `hotel-results`, `hotel-compare-cta`, `flight-card`, `flight-airline`, `flight-price`, `flight-live-status`, `flight-book-link`, `flight-search-link`, `flight-results-list`, `flight-unavailable-state`, `flight-empty-state`, `flight-error-state`, `flight-search-btn`, `explore-results-header`, `result-action-sheet`, `save-action-btn`, `more-actions-toggle`, `trip-actions-guidance`, `manage-in-saved-link`, `save-first-hint`, `action-error`.

---

## 2. Current data contracts per vertical (verified from source)

**No result type carries any photo / image / thumbnail field.** This is the single most important data fact for §7.

| Vertical | API fn (in `lib/api.ts`) | Result type | Renderable fields | Verify / addable identity | Link-out |
|---|---|---|---|---|
| Restaurants | `searchRestaurants(dest)` → `{ restaurants, terminalNoResults }` | `RestaurantSearchResult` | `name`, `cuisine`, `address`, `rating?`, `numReviews?`, `priceLevel?`, `tags[]` | `providerPlaceId ?? placeId` | `googleMapsUri?` |
| Attractions | `searchAttractionsExplore(dest, interest?)` → `ExploreAttractionResult[]` | `ExploreAttractionResult` | `name`, `category`, `address`, `rating?`, `reviewCount?`, `tags[]` | `googlePlaceId?` | `googleMapsUri?` |
| Hotels | `searchHotelsExplore(dest, checkIn?, checkOut?, guests)` → `ExploreHotelResult[]` | `ExploreHotelResult` | `name`, `address`, `rating?`, `source` | `googlePlaceId?` | `googleMapsUri?` + `compareLink` (Google Hotels search) |
| Flights | `searchFlightsExplore(req)` → `FlightExploreResponse` | `FlightItineraryOffer` (status-gated) | `outboundLeg`/`returnLeg` (times, stops, duration, airline, flightNumber), `price` (live provider only), `cabinClass`, `passengers`, `liveCachedStatus` | n/a (offers, not Places) | `bookingLink` (`airline_direct`/`ota`/`provider_deeplink`/`search_redirect`/`unavailable`) |

**Trust today:** `<TrustStrip sourceCount={1} />` renders only when the place has a Google identity (`providerPlaceId`/`googlePlaceId`). Flights show a `liveCachedStatus` badge instead — no TrustStrip.

**Save context:** every place card builds an `ExploreResultContext` and passes it to `ResultActionSheet`. Flights/hotels carry extra `dates`/`guests`/`passengers`/`cabinClass`. **This mapping must not change** — only the visual wrapper around it.

---

## 3. Exact files likely to change

**Will change (in scope):**
1. `frontend/src/components/explore/ExploreShell.tsx` — landing room reskin (meridian band + Observatory vertical entry cards) and active-vertical header reskin (breadcrumb + vertical mood banner). Logic (`active` state, `setActive`) unchanged.
2. `frontend/src/app/globals.css` — new **OBSERVATORY** section: `.obs-*` primitives (meridian band + depth layers, vertical entry card, editorial index head, premium place card, reduced-motion guards). Reuse existing tokens; no raw hex.
3. `RestaurantExploreFlow.tsx`, `AttractionExploreFlow.tsx`, `HotelExploreFlow.tsx` — swap the per-card visual shell to the shared Observatory place-card treatment + restyle the existing results-header into the editorial index head. **Search/handlers/`buildContext`/`ResultActionSheet` untouched.**
4. `FlightExploreFlow.tsx` — apply the Observatory **card frame** (border/plate-header/typography) to `FlightCard` only; **keep the leg/price/booking structure and all status states exactly as-is**.
5. `frontend/tests/` — new contract test file (e.g. `explore-observatory.test.mjs`) + minimal updates to any existing Explore test that asserts a class/text that legitimately moved.

**Should NOT change:** `app/explore/page.tsx`, `ResultActionSheet.tsx`, `Card.tsx`, `TrustStrip.tsx`, `CityAutocomplete.tsx`, `lib/api.ts`, `types/*`, `AppShell.tsx`, `AtelierNavArtifact`, any backend / provider / SQL file.

**Decision — shared place-card:** introduce one presentational wrapper (e.g. `ObservatoryPlaceCard` inside the explore folder, or a set of `.obs-card*` classes consumed directly) used by Restaurants / Attractions / Hotels. Flights keep their bespoke card (different shape) wearing the same frame. Prefer **CSS-class-level sharing over a new heavy component** to minimize churn; if a component is cleaner, keep it presentational (no fetching, no logic).

---

## 4. Mapping: prototype sections → production components

| Prototype (v1.1) | Production target | Notes |
|---|---|---|
| Doc masthead / banners / phone frames / `<script>` demo wiring | **Nothing** — concept-only chrome | Never ported. |
| Representative top nav | Existing `AppShell` + `AtelierNavArtifact` | Not re-created. Explore renders inside current shell. |
| `.meridian` band (landing) | New `.obs-meridian` rendered at top of `ExploreShell` landing view | Static atelier mood scene (no destination). Reduced-motion-gated drift/bloom. |
| `.vert-grid` of 4 entry cards | `ExploreShell` `VerticalCard`s reskinned to `.obs-vert-card` | Keep `vertical-card-{id}` testids, `onSelect={() => setActive(v.id)}`, labels **Restaurants/Hotels/Attractions/Flights**. |
| `.obs-crumb` breadcrumb | Existing `explore-lounge-breadcrumb` reskinned | Keep "← Explore" back-to-landing behavior (`setActive(null)`). |
| `.meridian.banner` (vertical mood banner) | New `.obs-banner` in `ExploreShell` active view, above the flow | Shows **vertical identity + mood only** (e.g. "Restaurants · verified tables"). Does **not** show the live typed destination (state stays inside the flow — see §11.1). |
| Per-vertical `.instrument` search fields | **Existing flow forms, unchanged** | The prototype's instrument is illustrative; production keeps each flow's real inputs (Restaurants: destination; Attractions: + interest; Hotels: + dates/guests; Flights: CityAutocomplete + dates + pax + cabin). |
| `.index-head` (count + sort chips) | Existing `explore-results-header` line reskinned to `.obs-index-head` | Keep the real "N {nouns} in {destination}" text (it already carries the destination). **Sort chips are illustrative — do NOT add client-side re-sorting in this PR** (would change result ordering behavior). Omit sort chips, or render the existing order only. |
| `.place-card` editorial card | Shared `.obs-card` treatment on Restaurant/Attraction/Hotel cards | Plate = typeset fallback (§7). Save/Map/Source = existing actions (§8). |
| Flight card | `FlightCard` wearing `.obs-card` frame | Leg rows, price, live badge, booking CTA unchanged. |
| `.folio-toast` "kept in your folio" | Optional polish on `ResultActionSheet` saved state | See §8 — visual-only; no new toast architecture required for v1. |

---

## 5. Mobile layout strategy

- **Landing (one screen, no pile):** `.obs-meridian` short banner (height ~`clamp(132px,20vh,168px)`) → `.obs-vert-grid` as a **2×2 grid** of clearly-named cards (Restaurants/Hotels/Attractions/Flights), ≥44px targets, no clipped labels (the v1 clipping bug is fixed by the grid, not a horizontal scroller). Everything sits inside the current mobile header + bottom nav — **do not** add or restyle the bottom nav.
- **Vertical flow:** breadcrumb → short `.obs-banner` (vertical mood) → the flow's existing form → editorial index head → stacked premium cards (single column). The active vertical is explicit via breadcrumb + banner; the destination is explicit via the existing index-head text.
- **Cards:** single-column, plate ~104–116px tall, name/category/trust/meta/actions in reading order; action row (Save · Map · Source) wraps comfortably at ≥44px.
- **Reduced-motion:** meridian drift + bloom disabled; card hover transform removed.
- **Validation:** must be checked on a **real responsive viewport** (DevTools device toolbar at 390×844 and a short 360×640), not only the prototype phone frames (§10).

---

## 6. Desktop layout strategy

- **Landing:** `.obs-meridian` band (height ~`clamp(180px,24vh,232px)`) full-width inside the lounge, then `.obs-vert-grid` as a 4-up row (collapses to 2-up < ~1100px). Content max-width follows the existing lounge container — no new shell width.
- **Vertical flow:** breadcrumb + `.obs-banner` (vertical mood) above the existing instrument section (`folio-cinema-card`), then the editorial index head + a results grid. Restaurants/Attractions/Hotels results may move from a single column to a **2–3 col `.obs-index-grid`**; Flights stay single-column (rich rows). Grid change is presentational only.
- **No two-column portal/dossier composition** (that's the Salon). The Observatory is a vertically-flowing deck — deliberately calmer/different from Concierge.
- **Reduced-motion + focus rings:** preserve 2px `--ds-accent` focus on all interactive elements.

---

## 7. Photo / fallback strategy (honest, real-data-only)

**Fact:** `RestaurantSearchResult`, `ExploreAttractionResult`, `ExploreHotelResult`, and `FlightItineraryOffer` carry **no** photo/image field today.

**Therefore, for this PR:** every place card uses the **typeset editorial plate** — a brass-serial overline + category/identity treatment over a token-built gradient plate (no external image, no stock photo). This is the contract-compliant fallback (Design Implementation Contract §8: "No stock photos. If no verified source photo exists, render typeset layout instead.").

- **Do NOT** add an `<img>`, fetch Google Places photos, introduce a photo field, or wire any image provider in this PR. Doing so is a data-contract + provider change (out of scope, and would need its own gated slice).
- Build the plate so a **future** real `photoUrl` could slot in behind the same frame without a redesign — but ship the typeset plate now. Note this as a future enhancement, not part of this PR.
- The plate must never imply a real photo exists (no "photo loading" shimmer, no fake image credit).

---

## 8. Save / Map / Source preservation plan

- **Save:** keep `ResultActionSheet` exactly. `save-action-btn`, `more-actions-toggle`, `trip-actions-guidance`, `manage-in-saved-link`, `save-first-hint`, `action-error`, and the `saveItem`/`deleteSavedItem` calls + `buildContext` payloads are **untouched**. The Observatory card places `<ResultActionSheet context={context} />` in the same action slot.
- **Map:** keep the existing `googleMapsUri` link-out anchor (restyle to `.obs-btn-ghost`, preserve `target="_blank" rel="noopener noreferrer"`, aria-label, and 44px hit area). Hotels additionally keep the `hotel-compare-cta` Google Hotels link.
- **Source:** "Source" = the existing `TrustStrip` (Verified place · source count). Keep `<TrustStrip sourceCount={1} />` rendered only when a Google identity exists. Do not invent a separate "Source" link unless it maps to existing data; the prototype's "Source" chip is satisfied by the TrustStrip + Map link.
- **Flights:** keep `bookingLink` CTA logic (`flight-book-link` / `flight-search-link` / "Booking link unavailable") and `ResultActionSheet` save exactly.
- **Saved feedback polish (optional, visual-only):** the "kept in your folio" moment may be added as a lightweight transient acknowledgement **inside `ResultActionSheet`'s existing saved state** (e.g. a brief styled confirmation), mirroring the Concierge `atelier-salon-folio-toast` pattern. It must not create a new Saved architecture, must be reduced-motion safe, and must not change save semantics. If it adds any risk, defer it — it is not required for acceptance.

---

## 9. Risk list by vertical

**Restaurants (low):** simplest — destination-only, place cards. Risk: results-header text/testid (`explore-results-header`, `restaurant-results`) must survive the reskin. Mitigation: keep the same elements, restyle classes.

**Attractions (low):** like Restaurants + optional interest field + `reviewCount`/`tags`. Risk: the optional interest input must remain (don't drop a field while reskinning the form area).

**Hotels (medium):**
- Discovery-only contract: **no rates, prices, or availability** may appear. The Observatory plate/meta must not introduce a price slot for hotels (unlike the prototype's `$$` sample). Show rating only.
- `hotel-compare-cta` (Google Hotels link-out) must be preserved and must remain a search link-out (no in-app rates).
- `buildHotelCompareUrl` + `compareLink` in `originalPayload` must stay intact (timezone-safe date formatting already handled — do not touch).

**Flights (highest):**
- **Do NOT touch `CityAutocomplete`** (PR #431 frozen behavior) or the form submit/airport logic.
- Card is structurally different (legs, not a Place). Apply only the outer frame/typography; keep `LegRow`, `formatTime` (no UTC conversion), `formatPrice`, `cabinLabel`, live badge, booking CTA, and all four status states (`ok`/`empty`/`unavailable`/`error`) exactly.
- Price is **live-provider-only**; never render a price plate or "from $X" sample. No TrustStrip on flights.
- Provider may be disabled → the polished `flight-unavailable-state` must still render correctly inside the new shell.

**Cross-cutting:** the meridian/banner must use light-on-dark text (pearl/cream) over a guaranteed dark scrim — never `--world-ink` dark text on the dark band (the readability failure mode from the Concierge work). Verify AA.

---

## 10. Testing / validation plan

- **Tier:** UI slice → **Tier 1–2** per `docs/ai/TEST_ROUTING.md`. Do **not** run the full backend suite.
- **Static contract tests** (new `frontend/tests/explore-observatory.test.mjs`, source-reading like the salon tests):
  - `globals.css` defines the new `.obs-meridian` (+ depth layers), `.obs-vert-card`, `.obs-index-head`, `.obs-card`, each new motion rule has a `prefers-reduced-motion` override.
  - `ExploreShell.tsx` still renders all 4 `vertical-card-{id}` testids, `explore-home`, `explore-vertical-grid`, breadcrumb, and uses `setActive`.
  - Each flow still renders its results testid (`restaurant-results`/`attraction-results`/`hotel-results`/`flight-results-list`), `explore-results-header` (place flows), `ResultActionSheet`, and the map/compare/booking link-outs.
  - **No fabricated data:** assert the production sources contain none of the prototype's demo strings (e.g. `Taberna do Mercado`, `Cevicheria`, `from $640`, `Source photo`, `data-v`).
  - Hotels: assert no price/`$$`/currency rendering added to the hotel card; `hotel-compare-cta` preserved.
  - Flights: assert `CityAutocomplete` import + the four status states + `flight-price` from `offer.price` only.
- **Full frontend run:** `cd frontend && npm test` + `tsc --noEmit` + `next lint` must be clean (current baseline ~3023 tests, 0 failures).
- **Manual browser smoke (required, real viewports):**
  - `/explore` landing on desktop (1440×900, 1280×800) and mobile (390×844, 360×640): meridian readable, 4 verticals named + unclipped, ≥44px targets, no horizontal scroll at 200% zoom.
  - Enter each vertical → run a **real search** → verify cards render, Save works (writes to Saved), Unsave works, Map/Compare/Booking link-outs open, Flights unavailable/empty/error states render.
  - Verify no card-count regression vs `main`, addability unchanged, reduced-motion disables drift/bloom.
  - If a browser cannot be run, **say so explicitly** in the PR body — do not claim visual success.

---

## 11. Implementation guardrails (hard)

1. **No universal cross-vertical destination/search controller.** Each flow keeps its own local state and search. The vertical mood **banner shows vertical identity + mood only**, not a lifted destination string. (If, later, the banner should echo the typed destination, that's a future enhancement via a lightweight per-flow callback — not this PR, and not a shared controller.)
2. **Do not replace/redesign the app shell or navigation.** No edits to `AppShell.tsx`, `AtelierNavArtifact`, header, or mobile bottom nav. Explore reskins **inside** them.
3. **Preserve routes, providers, API contracts, saved-item behavior.** No `lib/api.ts`, `types/*`, backend, or provider edits.
4. **Honor each vertical's production differences** (§9): Hotels discovery-only/no prices; Flights live-provider price + status states + frozen CityAutocomplete.
5. **Real image fields only** — none exist → typeset plate only (§7). No new image fetch/provider.
6. **No fabricated content** — no fake places, prices, ratings, photos, open-now, availability, awards, or unsupported labels. Render a field only when the backend supplies it; omit otherwise (no `N/A`/`—`).
7. **No backend rewrite, no new providers.**
8. **Tokens only** — `--ds-*` / existing world vars / `color-mix`; no raw hex in components or new CSS. Spacing via `--ds-space-*`.
9. **Reduced-motion** guards on every new transition/animation; AA contrast on the dark meridian (light text only).

---

## 12. Out of scope (explicitly)

- Unified cross-vertical search; lifting destination state into `ExploreShell`.
- Any change to `AppShell`, navigation, header, or bottom nav.
- Photos / image pipeline / Google Places photo fetch / new image fields.
- Hotel rates/prices/availability; OTA/in-app booking; new flight providers; re-enabling disabled providers.
- Client-side result re-sorting / new filters (the prototype's sort chips are illustrative — omit).
- New Saved architecture or add-to-trip behavior in Explore (add-to-trip stays in `/saved`).
- Map provider/theme changes; detail drawers; the Concierge two-column portal/dossier composition.
- Backend, SQL, Supabase, provider registry, or API contract changes.

**Supabase SQL required: No.**

---

## 13. Implementation sequence for ONE focused PR

Do these in order; commit once at the end (one PR from `main`).

1. **Inspect (read-only):** `ExploreShell.tsx`, the four flows, `ResultActionSheet.tsx`, `types.ts`, the result types in `types/index.ts` + `lib/api.ts`, the relevant `globals.css` primitives, and `tests/` Explore coverage.
2. **Add CSS:** new **OBSERVATORY** section in `globals.css` — `.obs-meridian` (+ scene/bloom/grain/horizon/vignette depth layers), `.obs-vert-card`, `.obs-banner`, `.obs-index-head`, `.obs-card` (+ plate/serial/trust/meta/actions), reduced-motion overrides. Material language echoes the Salon; silhouette is the wide meridian deck (different room).
3. **Reskin `ExploreShell`:** landing → meridian band + `.obs-vert-card` grid (4-up desktop / 2×2 mobile), preserving all testids and `setActive`. Active view → reskinned breadcrumb + `.obs-banner` (vertical mood) above the unchanged instrument section.
4. **Reskin place cards** (Restaurants → Attractions → Hotels): wrap each existing card's content in the shared `.obs-card` treatment; restyle the existing results-header into `.obs-index-head`. Keep every field mapping, `buildContext`, `TrustStrip`, map/compare link-outs, and `ResultActionSheet`. Hotels: no price slot.
5. **Reskin `FlightCard` frame only:** apply `.obs-card` border/header/typography; leave legs/price/badge/booking/status states intact.
6. **(Optional) Saved-feedback polish** inside `ResultActionSheet` saved state — visual only, reduced-motion safe; defer if any risk.
7. **Tests:** add `explore-observatory.test.mjs` (§10); update only the existing assertions that legitimately moved, justified in the PR body.
8. **Validate:** `npm test` + `tsc` + `lint` clean; manual browser smoke on real desktop + mobile viewports (§10), running a live search per vertical and confirming save/map/source + no card-count regression.
9. **Open one PR** from `main`, ready for review, filling the PR template honestly (Level 1–2 UI slice; roadmap stage 3.5 visible adoption; test tier + why; AI usage note; **Supabase SQL: No**). Update `docs/ai/HANDOFF.md` (replace/summarize) in the same PR. Stop after opening the PR.

---

## 14. Final implementer prompt skeleton (paste into a fresh chat, after approval)

```
Repo: prashanthkrishnan91/claude_travelapp_pk91
Branch: fresh branch from main.

Task: Reskin the outside-trip Explore (/explore) into the cinematic
"Observatory" composition per the approved prototype. UI reskin of
ExploreShell.tsx + globals.css, plus a bounded result-card/index-header
reskin of the four vertical flows. NO backend/API/provider/SQL/state-logic
changes; NO app-shell/nav changes; NO unified cross-vertical search.

Read first (in order):
- docs/ai/design/EXPLORE_OBSERVATORY_PRODUCTION_BLUEPRINT.md   ← the contract; follow exactly
- docs/ai/concepts/explore-observatory-concept-v1.1.html       ← approved visual concept
- frontend/src/components/explore/ExploreShell.tsx + the four *ExploreFlow.tsx + ResultActionSheet.tsx + types.ts
- frontend/src/app/globals.css (folio-cinema-* primitives; ATELIER ROOM SYSTEM for material reference)

Build to blueprint §4–§6 (mapping + mobile + desktop), §7 (typeset plate — no photos),
§8 (preserve Save/Map/Source + ResultActionSheet), §9 (vertical risks: Hotels no prices,
Flights frozen CityAutocomplete + status states + live price only). Honor all §11 guardrails
and §12 out-of-scope. Tokens only, light-on-dark meridian (AA), reduced-motion guards.

Validate per §10: frontend npm test + tsc + lint clean; add explore-observatory.test.mjs;
manual browser smoke on real desktop + mobile viewports running a live search per vertical
(save/map/source + no card-count regression). If you cannot run a browser, say so explicitly.

Open one PR from main, ready for review, PR template honest (Level 1–2 UI slice; test tier +
why; AI usage note; Supabase SQL: No). Update docs/ai/HANDOFF.md (replace/summarize). Stop
after opening the PR.
```

---

*This blueprint is documentation only. It does not modify the production app. Implementation happens in a separate PR per §13–§14, after explicit approval.*
