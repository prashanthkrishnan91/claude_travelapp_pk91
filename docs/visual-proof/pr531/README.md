# PR #531 visual proof — route-estimate connector honesty fix (audit-blocker patch)

Fixes an audit blocker found on the original PR F patch: when no Google Routes leg exists for a
routeable adjacent pair, the inline connector previously fell back to a local/haversine estimate
(`estimateTravel` in `travelHints.ts`) and rendered it with the same "min drive"/"min walk" + km
copy as a real provider leg — presenting a rough client-side guess as if it were route-estimate
data. The connector now only ever renders a minute/km figure when a real `RouteEstimateLeg` from
the backend matches the pair; otherwise it shows a neutral "Route time unavailable" state with no
duration or distance.

These screenshots come from a **temporary, uncommitted local harness**
(`frontend/src/app/auth/route-connector-harness/page.tsx`, deleted after capture) that mounted the
real `TimelineSections` component — the same component `ItineraryDayColumn` renders — directly
with fixture `items`/`routeLegs` props. `TimelineSections`'s temporary `export` (needed to import
it in isolation) was reverted immediately after capture, so the shipped component is unexported
exactly as before. `TimelineSections` makes no network calls itself (`callRouteEstimate` lives in
the parent `ItineraryDayColumn`), so this fixture-prop harness exercises the exact same connector
rendering code path the real app uses once a day column has loaded its items and route legs —
whatever those legs are (real Google Routes data, or empty because the fetch is disabled,
not-configured, erroring, in-flight, or never ran).

## Screenshots

1. `1-provider-leg-present.png` — a `RouteEstimateLeg` from the backend matches the adjacent pair
   (`fromItemId`/`toItemId`): connector renders the provider duration/distance (`~8 min drive ·
   1.8 km`), `data-testid="route-connector-google"`. Unchanged from before this patch.
2. `2-no-provider-leg-unavailable.png` — same pair shape, but `routeLegs=[]` (covers disabled,
   not_configured, provider_error, in-flight refetch, and "never fetched" — all four look
   identical to this fixture from the connector's point of view, since it only ever reads
   `routeLegs`): connector renders **"Route time unavailable"**, no minute/km figure,
   `data-testid="route-connector-unavailable"`. This is the fix — before this patch, this state
   rendered a fabricated `~N min drive · X km` sourced from local haversine math.
3. `3-missing-location.png` — one stop has no coordinates: unchanged pre-existing honest copy,
   "Add location details to improve travel hints."
4. `4-mobile-narrow.png` — all three states stacked at a 375px mobile viewport; layout unaffected.

## What this does NOT change

- The Google-leg-present branch (`data-testid="route-connector-google"`) is byte-for-byte
  unchanged — provider minute/km rendering, the `Car` icon, and the "drive" (never "walk") label
  are all identical to the original PR F patch.
- The `missing_location` and `skip` (flight/hotel) branches are unchanged.
- No new `callRouteEstimate` call site, no network/timing change — this is a pure rendering-branch
  fix in `renderItemsWithConnectors`.
