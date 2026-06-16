# Route-Readiness Audit — Post-PR #507
**Date:** 2026-06-16  
**Scope:** Validation-only. No code, SQL, UI, or provider changes.  
**Prerequisite chain audited:** PR #504 (canonical coordinate readers) · PR #506 (flight/hotel exclusion) · PR #507 (RouteReadinessStatus display)

---

## Evidence sources

- Static code analysis: `frontend/src/lib/travelHints.ts`, `frontend/src/lib/tripItemMetadata.ts`, `frontend/src/lib/itineraryCoordinates.ts`, `frontend/src/components/trips/ItineraryDayColumn.tsx`, `frontend/src/lib/api.ts`
- Test contracts: `frontend/tests/route-readiness-status.test.mjs`, `frontend/tests/travel-hints-canonical-coords.test.mjs`, `frontend/tests/travel-hints-non-routable.test.mjs`, `frontend/tests/itinerary-coordinates.test.mjs`, `frontend/tests/plan-my-day-place-resolution-v1.test.mjs`
- Live DB query: Supabase `claude_travelapp_pk91` — 5 trips · 29 days · 231 items (2026-06-16)

---

## 1. Coordinate coverage by item type

| Type | Total | With coords | Missing coords | Coverage |
|---|---|---|---|---|
| activity | 67 | 61 | 6 | 91% |
| meal | 58 | 56 | 2 | 97% |
| hotel | 46 | 45 | 1 | 98% |
| flight | 59 | 0 | 59 | 0% — expected, excluded from route readiness |
| note | 1 | 0 | 1 | n/a — excluded from route readiness |

**Eligible stops (activity + meal): 125 total — 117 with coords, 8 missing. Overall coverage: 93.6%.**

---

## 2. Day-level route readiness — all 29 days

| Category | Days | Count |
|---|---|---|
| < 2 eligible stops → banner hidden | too sparse to assess | **22** |
| ≥ 2 eligible, all with coords → banner hidden (route-ready) | | **5** |
| ≥ 2 eligible, ≥ 1 missing coords → banner **shown** | | **2** |

### Route-ready days (banner hidden — all coords present)

| Trip | Date | Eligible stops | With coords |
|---|---|---|---|
| New York | 2026-05-30 | 4 | 4/4 |
| Miami | 2026-05-22 | 2 | 2/2 |
| Columbus | 2026-06-03 | 2 | 2/2 |
| Chicago | 2026-06-05 | 3 | 3/3 |
| Chicago | 2026-06-07 | 2 | 2/2 |

### Days showing the readiness banner

| Trip | Date | Eligible stops | With coords | Banner text |
|---|---|---|---|---|
| Columbus | 2026-05-29 | 2 | 1 | "1 of 2 stops have location data. Add locations before route planning." |
| Miami | 2026-05-23 | 6 | 5 | "5 of 6 stops have location data. Add locations before route planning." |

### Days too sparse to assess (< 2 eligible stops)

22 of 29 days have 0 or 1 activity/meal stops. Most are arrival/departure days or days with only flights and hotels. The Columbus trip has 9 consecutive days with 0–1 eligible stops.

---

## 3. RouteReadinessStatus behavior — confirmed correct

All four visibility conditions verified from source (`travelHints.ts:121–133`, `ItineraryDayColumn.tsx:369–384, 818`):

| Condition | Code guard | Result |
|---|---|---|
| ≥ 2 eligible stops, ≥ 1 missing coords | `return { total, withCoords }` | **Shown** |
| < 2 eligible stops | `if (eligible.length < 2) return null` | **Hidden** |
| All eligible stops have coords | `if (withCoords === eligible.length) return null` | **Hidden** |
| Flight / hotel items | Not in `eligible` filter (activity \| meal only) | **Excluded from count** |

Component renders unconditionally at `ItineraryDayColumn.tsx:818`; internal logic gates visibility. Contracted by 9 tests in `route-readiness-status.test.mjs`.

---

## 4. Source-path diagnosis for 8 missing-coord items

| Source path | Items | % of missing |
|---|---|---|
| `concierge_idea` (details.source_kind) | **6** | **75%** |
| `from_saved_item` (details.created_from_saved_item) | 1 | 12.5% |
| other / unknown | 1 | 12.5% |

**Root cause: `addConciergeItemToTrip` (`api.ts:2597–2611`) writes only `{ reason }` — no `lat`, `lng`, `place_id`, or `google_maps_uri`.** Every Concierge-added activity/meal item arrives without coordinates. The backend `ConciergeSuggestion` type (`api.ts:1836–1840`) carries only `name`, `type`, and `reason`.

The 1 `from_saved_item` missing coordinates: likely saved before the coordinate-persistence fix landed, or the original Explore result carried no provider `lat`/`lng`. The 1 unknown is legacy or manually entered.

### Coordinate ingress by source path

| Add path | Coordinates on write | Status |
|---|---|---|
| Explore → Add to Day (`addAttractionToDay`, `addRestaurantToDay`) | `lat ?? null`, `lng ?? null` + parity fields | **Sound** |
| Explore → Save → Trip (`addSavedItemToTrip`) | Via `extractItineraryCoordinates(snap)` — only if valid range | **Sound** |
| Saved → Ideas → Itinerary (`assignIdeaToDay`) | PATCH `day_id` only; existing details preserved | **Sound** |
| Plan My Day (via `extractRouteableTripItemMetadata`) | `lat`/`lng` when Google Places upstream resolution succeeds | **Sound** |
| **Concierge → Trip (`addConciergeItemToTrip`)** | `{ reason }` only — **no coordinate fields** | **Gap** |
| Manual / note | n/a — excluded from route readiness | n/a |
| Legacy / unknown origin | Unknown | Edge case |

---

## 5. No route optimization — confirmed absent

Confirmed by source scan and test contracts:

- No `OptimizeDay`, `optimizeRoute`, `routeOptimiz`, or `Optimize Day` in `travelHints.ts` or `ItineraryDayColumn.tsx` (`route-readiness-status.test.mjs:209–214`).
- No reorder / sort in `travelHints.ts` (`route-readiness-status.test.mjs:242–248`).
- No `DirectionsAPI`, `DistanceMatrix`, `RoutesAPI` in `travelHints.ts` or `computeRouteReadiness` (`route-readiness-status.test.mjs:230–240`).
- No geocoding in `travelHints.ts`, `tripItemMetadata.ts`, `itineraryCoordinates.ts`, or `ItineraryDayColumn.tsx`.
- `backend/app/routes/optimize.py` handles flight×hotel combination scoring only — not itinerary reordering.
- `TripMapView.tsx:geocodeCity()` exists for Explore/Build map centering only; structurally isolated from the itinerary and Journey Desk surfaces.

---

## 6. Recommendation

**B — Fix Concierge coordinate ingress before proceeding to route optimization planning.**

### Reasoning

- 93.6% of eligible stops already have coordinates; the gap is narrow and path-specific.
- All 6 dominant missing-coord items trace to `addConciergeItemToTrip` — one function, one payload gap.
- Only 5 of 29 days are route-plannable today (≥2 eligible stops, all with coords). Most days are too sparse regardless of coordinates; adding more stops via any path (including fixing Concierge) will build toward viable route days.

### Fix scope (for the next PR — do not build in this PR)

1. Confirm whether the backend Concierge suggestion response already carries `lat`/`lng` or `place_id` and is simply not forwarded. If yes: single frontend path fix in `addConciergeItemToTrip`.
2. If the backend `ConciergeSuggestion` type does not carry location identity: backend enrichment fix needed — suggestions must carry `place_id`/`lat`/`lng` before the frontend adds them.
3. After the fix, re-run the source-path query in this doc to confirm missing-coord count drops to ≤2 (the non-Concierge edge cases).
4. Once confirmed, proceed to provider/algorithm planning for route optimization.

### Do not proceed to route optimization until

- Concierge-added items carry coordinates (or are explicitly tagged as location-unknown).
- A re-run of the DB query confirms the gap is closed.
