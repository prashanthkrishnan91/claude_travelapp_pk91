# PR #529 visual proof — AI Route Planning v1 PR D (deterministic day-flow review surface)

`DayFlowReview` is a real, integrated component in `ItineraryDayColumn.tsx`, rendered next to
`RouteReadinessStatus` / `RouteQualityDiagnosticNote` in the shipped app. These screenshots come
from a **temporary, uncommitted local harness** (`frontend/src/app/auth/day-flow-harness/page.tsx`,
deleted after capture) that mounted the real `DayFlowReview` component directly with fixture
`items`/`routeLegs` props — real component code and real Tailwind design tokens, not a synthetic
mockup. The harness briefly re-exported the otherwise-internal `DayFlowReview` function to import
it in isolation; that export was reverted immediately after the screenshots were captured, so the
shipped component stays unexported exactly as before.

No live Supabase-backed backend or itinerary day was available in this sandbox, so the harness
supplies fixture `ItineraryItem[]`/`RouteEstimateLeg[]` props directly instead of loading a real
trip day. `DayFlowReview` itself makes no network calls (no `callRouteEstimate`, no
`fetchRouteQualityDiagnostic`, no mutation) — it is a pure function of the `items`/`routeLegs`
already passed into it, so this fixture-prop harness exercises the exact same code path the real
app uses once a day column has loaded its items and route legs.

## Screenshots

1. `1-collapsed-before-click.png` — collapsed state before any click: only the "Review day flow"
   button is shown, nothing auto-expands.
2. `2-route-data-unavailable.png` — after clicking, with no route legs available: honest "No
   travel-time review is available yet." copy, no fabricated duration/distance.
3. `3-missing-coordinate-excluded-stop.png` — a day with one located stop, one activity/meal stop
   missing coordinates, and a hotel: "Missing coordinates: ... Add locations before route
   planning." plus "Hotels and flights are excluded from route planning v1."
4. `4-route-leg-summary.png` — a fully located day with route legs already present: leg count,
   longest leg (from the leg's own duration/distance fields only), and a current-order summary —
   no fabricated total.
5. `5-mobile-narrow.png` — the missing-coordinate/excluded-stop state at a 375px mobile viewport.
