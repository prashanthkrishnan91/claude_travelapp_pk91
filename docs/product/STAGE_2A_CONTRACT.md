# Stage 2A Contract — Discovery-First Entry

**Status:** Contracted — not yet implemented.
**Date:** 2026-05-11
**Roadmap stage:** Stage 2 — Open app before trip exists.
**Build queue items:** Global Explore Shell v1, Unified Result Actions v1.

---

## Stage 2A Objective

Make the app useful with no trip created. A user who opens Travel Concierge for the first time must be able to discover, browse, and save travel ideas without ever touching "New Trip."

This PR defines the entry contract for that shift. It does not implement the UI.

---

## Target User Journey

```
Open app (no trip)
  → Land on global Explore shell
  → Browse / search by destination or vertical
  → AI Concierge or search surfaces place cards
  → Pick a result → Unified Result Action sheet appears
       ├── Save (to personal shortlist — Stage 3 backing, placeholder in 2A)
       ├── Add to Trip → trip picker if trips exist
       └── Create Trip → pre-filled from result context
  → User has accomplished something without creating a trip first
```

The journey must not disturb existing trip/candidate behavior for users who already have trips.

---

## Current Repo Architecture Inventory

### Explore / Search paths

| Surface | Location | State |
|---|---|---|
| `/search` route | `frontend/src/app/search/page.tsx` | Redirects to `/trips/new` — blocked |
| Explore snapshot | `fetchExploreSnapshot(tripId)` / `saveExploreSnapshot(tripId)` in `api.ts:932,1064` | Trip-scoped, deprecated as primary hydration source |
| Attraction search | `searchRestaurants`, backend `routes/search.py` | Exists, trip-context assumed but not enforced |
| AI Concierge | `callConcierge`, `callConciergeSearch` in `api.ts:1704,1714` | Always bound to a `tripId` |
| No global Explore shell | — | Does not exist |

### Navigation

| Link | Current state |
|---|---|
| Dashboard | `/` |
| My Trips | `/trips` |
| New Trip | `/trips/new` |
| Explore / Discover | **Missing** — not in `Sidebar.tsx` or `MobileNav.tsx` |

### Card / Result components

| Component | Location | Actions exposed |
|---|---|---|
| `SearchResultCard` | `components/trips/SearchResultCard.tsx:72` | `onAdd` (add to trip/day) only — no Save, no Create Trip |
| `ItineraryItemCard` | `components/trips/ItineraryItemCard.tsx` | Trip-context display only |
| `TripIdeasPanel` | `components/trips/TripIdeasPanel.tsx` | Trip-scoped shortlist |

### Save / Add / Create-trip paths

| Action | API function | Backing | State |
|---|---|---|---|
| Save to shortlist | `saveToTripIdeas(tripId, item, kind)` — `api.ts:2013` | `itinerary_items` with `source_kind="concierge_idea"` | **Trip-required** — no global save |
| Add to trip (unscheduled) | `addAttractionToTrip`, `addRestaurantToTrip`, `addHotelToTrip` | `itinerary_items` (day_id IS NULL) | Trip-required |
| Add to day | `addAttractionToDay`, `addRestaurantToDay`, `addHotelToDay` | `itinerary_items` | Trip+day required |
| Create trip | `createTrip(formData)` — `api.ts:176` | `trips` table | Available standalone |
| Create trip + seed | `createTripWithSearch(data)` — `api.ts:196` | `trips` + `itinerary_items` creation seeds | Available standalone |

### Trip candidate selectors (stable — do not disturb)

`frontend/src/lib/tripCandidates.ts` — groups `itinerary_items` by vertical into flights/hotels/attractions/restaurants. `source_kind="concierge_idea"` → Trip Ideas panel. `source_kind="creation_seed"` → seeded candidates. This selector must not be changed in Stage 2A implementation.

---

## Unified Result Action Contract

Every place card surface (Explore, AI Concierge, search) must present exactly three actions in a consistent sheet/menu:

### 1. Save
- **Stage 2A behavior:** Action button exists. Tapping it saves the item to a user-scoped shortlist.
- **Stage 2A backing:** `itinerary_items` with `source_kind="concierge_idea"` and a sentinel `trip_id` (or a new trip-optional save path — implementation choice deferred to Stage 2A slice 2). Do NOT pre-solve Stage 3's saved-list data model here.
- **Stage 3 backing:** Saved list as first-class root object (Stage 3 owns this migration).
- **Forbidden:** Silently failing, crashing without a trip, or leaking "you need a trip to save."

### 2. Add to Trip
- **Behavior:** Opens a trip picker if the user has trips; if zero trips, falls through to Create Trip.
- **Backing:** Existing `addAttractionToTrip` / `addRestaurantToTrip` / `addHotelToTrip` — unchanged.
- **Forbidden:** Crashing or showing an empty state with no guidance when no trips exist.

### 3. Create Trip
- **Behavior:** Opens a lightweight trip creation modal, pre-populating destination from the result card.
- **Backing:** `createTrip(formData)` — unchanged.
- **Forbidden:** Forcing the user to abandon the discovery flow entirely (modal/overlay is preferred over full-page redirect).

### Action surface rules
- All three actions use the same component regardless of entry point (Explore, Concierge, search).
- The action sheet must not import or depend on trip-context state (`TripBuilder`, `tripId` from URL).
- Mobile: sheet slides up from bottom. Desktop: dropdown or card-inline buttons.
- No mock / sample / prototype copy in action labels.

---

## Source-of-Truth Boundaries

| Domain | Canonical source | Stage 2A change? |
|---|---|---|
| Addable place cards | Google Places (Places Addable Authority Pack) | No |
| Enrichment / evidence | Yelp / Foursquare / editorial (Enrichment Evidence Only Pack) | No |
| AI Concierge card fields | `display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick` (AI Concierge Card Contract Pack) | No |
| Trip candidates selector | `tripCandidates.ts` — `itinerary_items` grouped by vertical | No — do not touch |
| Save backing (2A) | `itinerary_items` with `source_kind="concierge_idea"` (trip sentinel or trip-optional path TBD) | Implementation choice in next slice |
| Saved list (Stage 3) | New root object — not built in Stage 2A | Deferred |

---

## Minimal Next Implementation Sequence

These are implementation slices, not this PR. Each slice is one focused PR.

### Slice 1 — Global Explore Shell v1
- Add `/explore` route in Next.js app router.
- Add "Explore" nav link to `Sidebar.tsx` and `MobileNav.tsx`.
- Shell renders a destination search input + vertical filters (Attractions, Restaurants, Hotels, Flights).
- On search, calls existing `searchRestaurants` / attractions / hotels providers (no new backend routes required for v1).
- AI Concierge available without a trip: `callConciergeSearch` must accept `tripId=null` or an optional param (check backend contract before assuming — this is a small backend change or a new endpoint).
- No mock destinations, no sample data, no hardcoded editorial lists.

### Slice 2 — Unified Result Actions v1
- New `ResultActionSheet` component (or `ResultActionMenu` for desktop).
- Three actions: Save, Add to Trip, Create Trip.
- Save: trip-optional save path (sentinel trip or deferred bucket — decide in slice).
- Add to Trip: reuses existing add-to-trip API functions; adds trip picker UI.
- Create Trip: modal wrapping `TripBuilderForm`, pre-filled destination.
- Wire into `SearchResultCard` and the new Explore Shell.
- Do not change `TripBuilder`, `TripIdeasPanel`, or `tripCandidates.ts`.

### Slice 3 — Trip-Optional AI Concierge
- Concierge accessible from Explore shell without trip context.
- Backend: accept optional `trip_id`; when null, skip trip-context hydration; return place cards only.
- Frontend: `callConcierge` / `callConciergeSearch` accept optional `tripId`.
- No change to existing trip-bound Concierge behavior.

---

## Validation Criteria

### Global Explore Shell v1 (Golden Scenarios 1, 2, 6, 7)
- [ ] User opens `/explore` with no trips — sees a useful shell, not an error.
- [ ] User searches for "coffee shops in Tokyo" — gets real Google Places results, no mock data.
- [ ] AI Concierge panel (if shown) returns claim-safe cards.
- [ ] No "create a trip first" gate anywhere in the Explore shell.
- [ ] Navigation shows "Explore" link on both desktop sidebar and mobile nav.
- [ ] Existing `/trips` and `/trips/[id]` flows completely unaffected.

### Unified Result Actions v1 (Golden Scenarios 1, 2, 3, 4, 6)
- [ ] Result card shows Save / Add to Trip / Create Trip actions.
- [ ] Save does not crash or require a trip.
- [ ] Add to Trip works if the user has at least one trip; shows trip picker if multiple.
- [ ] Add to Trip → if zero trips → falls through to Create Trip with pre-fill.
- [ ] Create Trip pre-populates destination from the result card context.
- [ ] Action sheet is consistent across Explore, AI Concierge, and search surfaces.
- [ ] Mobile: sheet slides up correctly, touch targets usable.
- [ ] No regressions: existing trip add / save / ideas flows unchanged.

---

## Out of Scope for Stage 2A

- Saved list as a first-class root object (Stage 3).
- AI destination intelligence / preference-aware recommendations (Stage 4).
- ML ranking of Explore results.
- Road trip mode, deal intelligence, points intelligence, Travel Watchtower.
- Full Wife Wow design sprint.
- Any change to `tripCandidates.ts`, `TripBuilder`, `TripIdeasPanel`, or trip candidate selector behavior.
- SQL migrations (Stage 2A implementation must work within the existing schema or add columns conservatively; no schema rewrites).
- Changes to live research behavior, provider routing, or AI Concierge hydration logic.

---

## Safety Packs Applicable to Stage 2A Implementation

- Google Places Addable Authority Pack
- No Mock/Sample Visible Data Pack
- AI Concierge Card Contract Pack
- Latency Budget Pack
- Enrichment Evidence Only Pack (for any editorial content in Explore)
