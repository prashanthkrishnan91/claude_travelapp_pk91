# AI Route Planning v1 visual proof — real user flow from "Plan My Day"

The first PR to deliver the actual AI route-planning *user outcome*: suggesting a more
practical stop order for a day's already-placed activity/meal stops, surfaced inside the
existing Plan My Day result modal. Governed by `docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`.

**Patch update:** the current order and the LLM's proposed order are now both routed through
the existing Google Routes service before anything is surfaced. A changed order is only shown
when the routed comparison clears a conservative, deterministic improvement threshold; the
preview always shows a provider-derived (never LLM-authored) "Estimated travel: about N
minutes/km less" line. When the routed comparison doesn't show a material improvement, the
day's current order is returned unchanged with an honest "already looks practical" message and
no Apply action.

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
2. `2-suggested-current-vs-proposed.png` — a **routed and verified** proposal: current order,
   proposed order, the deterministic "Estimated travel: about 18 minutes less." savings line
   (computed only from Google Routes duration/distance figures), and Cancel / "Apply this
   order" controls.
4. `4-applied-reordered-with-connectors.png` — the day column after the suggestion is applied:
   Riverside Park Walk now precedes the lunch stop, and the existing inline
   "Route time unavailable" connector still renders between stops — unchanged canonical display.
5. `5-mobile-narrow.png` — the same verified-proposal section at a 390px mobile viewport,
   including the savings line.
6. `6-no-review-day-flow-button.png` — the day column with no "Review day flow" button anywhere
   (that component was already removed in PR #532; this PR does not reintroduce it).
7. `7-current-order-already-practical.png` — a routed proposal that did **not** clear the
   improvement threshold: only the deterministic "This day's order already looks practical…"
   message renders, with no current/proposed order lists and no Apply action.
8. `8-day-part-current-sections.png` — a 5-stop day with a non-routeable flight interleaved in
   raw persisted order between two morning stops and three afternoon stops (`City History
   Museum`, `Morning Pastry Stop` morning; `Flight to Lyon`, `Riverside Park Walk`, `Afternoon
   Bistro Lunch` afternoon). `ItineraryDayColumn`'s own Morning/Afternoon section headers (real,
   unmodified component) group them correctly — the same grouping the generate endpoint's
   `current_display_order` now mirrors.
9. `9-day-part-proposed-order.png` — the "Current order"/"Proposed order" preview lists use
   this **canonical day-part display order** (Morning stops, then the afternoon-classified
   flight, then the remaining afternoon stops) — not raw database position order. Only the two
   morning stops are swapped in "Proposed order"; the flight and both other afternoon stops stay
   in the exact same relative order in both columns, proving the boundary was respected.
10. `10-day-part-applied-matches-preview.png` — after applying: the Morning section now shows
    `Morning Pastry Stop` before `City History Museum` (the accepted swap), and the Afternoon
    section is byte-for-byte unchanged — the rendered itinerary matches the preview exactly, and
    no item crossed a day-part boundary.
11. `11-day-part-mobile.png` — the same day-part-aware proposal preview at a 390px mobile
    viewport.

## What this proves

- The suggestion is generated only after the explicit "Plan My Day" click (see
  `frontend/tests/ai-route-planning-plan-my-day.test.mjs` for the static-source proof that
  `generateRouteReorderProposal` is never called from a `useEffect`).
- The LLM proposes, Google Routes verifies: a changed order is only ever routed and surfaced
  when the routed comparison shows a real improvement (`backend/tests/test_route_reorder_proposal_generate.py`).
- The preview performs no write — only `ReorderProposalPreview`'s `handleConfirm` calls
  `applyRouteReorderProposal`, the existing PR #528 apply endpoint.
- No new modal/page/panel/map/dashboard was introduced — the suggestion lives inside the
  existing `DayPlanModal` (the Plan My Day result surface).
- Excluded items (flights/hotels/notes, or stops missing coordinates) are not part of the
  reorder, and fixed-time stops are treated as anchors that untimed stops cannot cross —
  proven server-side by `backend/tests/test_route_reorder_proposal_generate.py`.
- Day-part sections (Morning/Afternoon/Evening/Unscheduled) — the same sections
  `ItineraryDayColumn` renders — are hard boundaries: a stop can only be reordered among other
  stops in its own section, and the preview's current/proposed lists always match that same
  rendered section order, never raw database position order.
