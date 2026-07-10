# AI Route Planning v1 visual proof — real user flow from "Plan My Day"

The first PR to deliver the actual AI route-planning *user outcome*: suggesting a more
practical stop order for a day's already-placed activity/meal stops, surfaced inside the
existing Plan My Day result modal. Governed by `docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`.

These screenshots come from a **temporary, uncommitted local harness**
(`frontend/src/app/auth/ai-route-harness/page.tsx`, deleted after capture) that mounted the
real `ItineraryDayColumn` and `DayPlanModal` components directly with fixture `day`/`items`/
`plan`/`routeProposal` props — real component code and real Tailwind design tokens, not a
synthetic mockup. No source component was modified to take the screenshots. No live Supabase
backend was available in this sandbox, so `callRouteEstimate` inside `ItineraryDayColumn`
fails closed to its existing "Route time unavailable" state, exactly as it does whenever no
Google Routes leg is reachable in the real app — the inline connector contract is untouched by
this PR (proven further by `backend/tests` and `frontend/tests/ai-route-planning-plan-my-day.test.mjs`).

## Screenshots

1. `1-plan-my-day-before.png` — Day 2, three stops already placed (museum, lunch, park), before
   requesting a suggestion. The existing "Plan My Day" button is visible; no new permanent
   itinerary-column button was added.
2. `2-suggested-current-vs-proposed.png` — after Plan My Day: the existing result modal shows
   the normal attraction/dining suggestions **plus** a new "Here is a more practical order for
   this day" section (reusing `ReorderProposalPreview` from PR #528) with current order,
   proposed order, and a short plain-English rationale.
3. `3-confirmation-controls.png` — the same section, showing the "Cancel" / "Apply this order"
   controls. Nothing is written until "Apply this order" is clicked.
4. `4-applied-reordered-with-connectors.png` — the day column after the suggestion is applied:
   Riverside Park Walk now precedes the lunch stop, and the existing inline
   "Route time unavailable" connector still renders between stops — unchanged canonical display.
5. `5-mobile-narrow.png` — the same suggestion section at a 390px mobile viewport.
6. `6-no-review-day-flow-button.png` — the day column with no "Review day flow" button anywhere
   (that component was already removed in PR #532; this PR does not reintroduce it).

## What this proves

- The suggestion is generated only after the explicit "Plan My Day" click (see
  `frontend/tests/ai-route-planning-plan-my-day.test.mjs` for the static-source proof that
  `generateRouteReorderProposal` is never called from a `useEffect`).
- The preview performs no write — only `ReorderProposalPreview`'s `handleConfirm` calls
  `applyRouteReorderProposal`, the existing PR #528 apply endpoint.
- No new modal/page/panel/map/dashboard was introduced — the suggestion lives inside the
  existing `DayPlanModal` (the Plan My Day result surface).
- Excluded items (flights/hotels/notes, or stops missing coordinates) are not part of the
  reorder — proven server-side by `backend/tests/test_route_reorder_proposal_generate.py`.
