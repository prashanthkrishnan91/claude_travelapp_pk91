# PR #532 visual proof — remove route diagnostic/review clutter from Journey Desk

Removes the "Check route readiness" / "Route readiness review" and "Review day flow" / "Day
flow review" affordances from the normal itinerary day UI. Both duplicated the inline route
connector information already shown between stops and read as internal/debug tooling in a
user-facing surface.

These screenshots come from a **temporary, uncommitted local harness**
(`frontend/src/app/auth/route-diagnostics-harness/page.tsx`, deleted after capture) that mounted
the real `ItineraryDayColumn` component — the same component Journey Desk renders — inside a
`DndContext`, with fixture `day`/`items` props. No source component was modified to take the
screenshot; only fixture data was supplied. `callRouteEstimate` runs exactly as it does in the
real app (no backend reachable from the harness, so it fails closed and the inline connector
falls back to its existing "Route time unavailable" state — the same honest-copy path the real
app takes whenever no Google Routes leg exists for a pair).

## Screenshots

1. `1-journey-desk-desktop.png` — Day 1 expanded at desktop width with three itinerary items in
   the Morning section. Inline route connectors render between cards ("Route time unavailable"
   for the first pair, "Add location details to improve travel hints." for the pair missing
   coordinates). The compact "2 of 3 stops have location data" status still renders. **No** "Check
   route readiness" button, **no** "Review day flow" button, **no** diagnostic panel anywhere.
2. `2-journey-desk-mobile.png` — the same day at a 375px mobile viewport. Same connectors and
   compact status render; layout is otherwise unchanged.

## What this does NOT change

- Inline route connectors (`renderItemsWithConnectors`, `route-connector-google` /
  `route-connector-unavailable` testids) — unchanged.
- `callRouteEstimate` call site and its `routableStops.length < 2` guard inside
  `ItineraryDayColumn`'s `useEffect` — unchanged.
- The compact `RouteReadinessStatus` "X of Y stops have location data" indicator — kept, since it
  is already compact and directly useful (no disabled/internal diagnostic copy).
- Drag/drop, timeline day-part sections, card layout — unchanged.
- The backend `route-quality-diagnostic` endpoint — untouched; only the frontend affordance that
  called it (`RouteQualityDiagnosticNote`, and its `fetchRouteQualityDiagnostic` import) was
  removed from `ItineraryDayColumn`.
- No AI/LLM calls, route optimization, or reorder-proposal UI were added.
