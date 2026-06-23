# Route Planning v1 — Activation Runbook

**Status:** Feature complete, production-inert. Requires explicit opt-in to activate.  
**Last validated:** 2026-06-23 (post PR #519 merge — inline auto-fetch UX)  
**Governed by:** `docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` (PR #509 ADR)

> **PR #519 UX change:** The separate "Check route" button and `CheckRoutePanel` were removed. Route
> estimates now auto-fetch inline when a day with ≥2 routable stops is expanded. The connector
> between itinerary cards shows `~N min drive · X.X km` directly. Steps below reflect this.

> ⚠️ **Do not activate in production without a controlled rollout decision. This runbook describes the procedure for a deliberate, manual activation in a non-production or controlled preview environment only.**

---

## Required Environment Variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `ROUTE_ESTIMATE_V1_ENABLED` | Yes (to enable) | `false` | Set `true` to activate endpoint |
| `GOOGLE_ROUTES_API_KEY` | Yes (to activate) | `""` (empty) | Server-side only; never expose to frontend |

Both must be set together. Setting only one produces a safe fail-closed response.

---

## Pre-Activation Checks

Run all of the following before enabling in any environment:

1. **Verify feature flag default is off in production.** Confirm `ROUTE_ESTIMATE_V1_ENABLED` is absent or `false` in the production environment config.

2. **Confirm `GOOGLE_ROUTES_API_KEY` is not in any frontend env.** It must not appear as `NEXT_PUBLIC_GOOGLE_ROUTES_API_KEY` or in any frontend bundle. It is a server-side-only secret.

3. **Confirm `production_allowed` remains `False` in provider registry.** Check `backend/app/services/provider_registry.py` — the `google_routes` entry must keep `production_allowed=False`. This flag is informational; activation is controlled solely by the feature flag + API key.

4. **Run the backend test suite** (Tier 0 + route-estimate scope):
   ```
   pytest backend/tests/test_route_estimate_endpoint.py \
          backend/tests/test_route_estimate_api.py \
          backend/tests/test_google_routes_adapter.py \
          backend/tests/test_routing_provider_registry.py -v
   ```

5. **Run the frontend route-estimate tests** (run from the `frontend/` directory):
   ```
   node --test tests/route-estimate-check-route.test.mjs
   node --test tests/route-readiness-status.test.mjs
   ```
   Note: `route-readiness-status.test.mjs` is also covered by `npm test`. `route-estimate-check-route.test.mjs` must be run directly via `node --test` as it is not included in the main `npm test` script.

6. **Confirm call discipline (auto-fetch, not looping).** After PR #519, `callRouteEstimate` is invoked
   from a `useEffect` in `ItineraryDayColumn` keyed on `routableStopsKey` (a stable string encoding
   stop IDs + coordinates). Verify:
   - The effect fires at most once per stable `routableStopsKey` value.
   - No loop: `routeLegs` state (set by the effect) is not in the dependency array.
   - A cancelled-flag cleanup (`cancelled = true`) prevents stale state on unmount.
   - The guard `routableStops.length < 2` prevents calls with insufficient stops.
   - Opening menus, compare/select actions, and expand/collapse (unless routable stop set changes) do **not** fire another call.

7. **Confirm Google Routes API key has appropriate quota limits set** in the Google Cloud Console before use (see Cost Guardrails below).

---

## Smoke-Test Sequence (Non-Production / Preview Only)

After enabling `ROUTE_ESTIMATE_V1_ENABLED=true` and setting `GOOGLE_ROUTES_API_KEY` in a non-production environment:

### Step 1 — Verify disabled path is gone

With both vars set, call the **backend API directly** (FastAPI / Railway preview URL). The route-estimate endpoint is a FastAPI route served by the backend — it is not served by the Vercel frontend. The frontend calls it via `NEXT_PUBLIC_API_URL` (defaults to `http://127.0.0.1:8000` locally; use the Railway preview URL in a deployed preview environment).

```bash
curl -X POST \
  https://<railway-backend-preview-url>/itinerary/<trip_id>/days/<day_id>/route-estimate \
  -H "Authorization: Bearer <valid_token>" \
  -H "Content-Type: application/json" \
  -d '{"stops": [
    {"item_id": "id-1", "item_type": "activity", "lat": 48.8566, "lng": 2.3522, "title": "Eiffel Tower"},
    {"item_id": "id-2", "item_type": "activity", "lat": 48.8606, "lng": 2.3376, "title": "Louvre"}
  ]}'
```

**Expected:** `status: "success"` with `estimates` containing one leg (id-1 → id-2).

### Step 2 — Verify `not_configured` path (temporarily remove key)

With `ROUTE_ESTIMATE_V1_ENABLED=true` but `GOOGLE_ROUTES_API_KEY` unset:
```json
{"status": "not_configured", "reason": "provider_key_missing", "estimates": []}
```

### Step 3 — Verify ownership gate

Use a `trip_id` that belongs to a different user. Expect: HTTP 404.

### Step 4 — Verify stop count validation

Send 1 stop → HTTP 422 (`<2 stops`).  
Send 11 stops → HTTP 422 (`>10 stops`).

### Step 5 — UI smoke test in Journey Desk

1. Open a day with ≥2 activity/meal stops that have canonical coordinates (lat/lng from Google Places).
2. Confirm there is **no** "Check route" button and **no** bottom route-estimate panel (both removed in PR #519).
3. Confirm the inline connector between itinerary cards shows `~N min drive · X.X km` automatically
   (no click required) with `data-testid="route-connector-google"`.
4. Confirm the connector never says "walk" — adapter uses DRIVE + TRAFFIC_UNAWARE.
5. Confirm the stop order in the connectors matches the original manual item order exactly.
6. Confirm opening/closing item menus, compare, or select actions do **not** fire an additional
   route-estimate network call (visible in browser devtools).
7. Switching to another routable day may fire one call for that day's stop set.

### Step 6 — Verify `provider_error` path

Temporarily use an invalid API key. Expect:
```json
{"status": "provider_error", "reason": "provider_call_failed", "estimates": []}
```
UI should show the error message without crashing.

---

## Expected Behavior by State

| State | Condition | `status` | `estimates` | UI shown |
|---|---|---|---|---|
| Disabled | `ROUTE_ESTIMATE_V1_ENABLED` = false | `disabled` | `[]` | Connector falls back to local haversine hint; no error shown |
| Not configured | Flag true, key missing | `not_configured` | `[]` | Connector falls back to local haversine hint; no error shown |
| Auth failure | Trip/day not owned | HTTP 404 | — | Generic catch; connector shows local hint |
| Too few stops | `<2` valid stops | HTTP 422 | — | Effect exits early (`routableStops.length < 2`); no call made |
| Too many stops | `>10` valid stops | HTTP 422 | — | Generic error catch |
| Provider error | Google API error/timeout | `provider_error` | `[]` | Error message from `response.message` |
| Success | All gates pass | `success` | populated | Per-leg durations and distances |

---

## Cost Guardrails

- **At most one ComputeRoutes call per stable routable stop set.** Auto-fetches inline when a day with ≥2 routable stops is expanded; re-fetches only if the stop IDs or coordinates change. No polling, no cron jobs.
- **Hard cap of 10 stops per call.** Enforced at both service layer (HTTP 422) and adapter boundary.
- **Tight field mask:** Only `routes.legs.duration,routes.legs.distanceMeters` — no polylines, no header-level totals, no alternatives.
- **No matrix calls, no traffic-aware routing, no route optimization** — these are v1 hard exclusions.
- **Recommended pre-activation:** Set a daily spend cap and per-key quota limit in Google Cloud Console before enabling. The Routes API charges per request element.
- **Monitoring:** `metadata.provider_call_count` is returned in every response. Use this field for billing reconciliation.

---

## Rollback Steps

If issues are found after activation:

1. **Immediate:** Set `ROUTE_ESTIMATE_V1_ENABLED=false` (or remove the env var). The endpoint immediately returns `status: "disabled"` with no provider calls. No deploy required if the env var change propagates to the runtime.
2. **Key rotation:** If the API key is suspected compromised, rotate it in Google Cloud Console first, then update `GOOGLE_ROUTES_API_KEY` in the environment. Old key becomes invalid immediately.
3. **Full revert:** If the feature itself is problematic, setting the flag to `false` is sufficient — the `useEffect` catches the `disabled` status and falls back to local hints without any user-visible error. No deploy required if the env var change propagates.
4. **No database changes needed.** Route estimates are ephemeral — not persisted. Rollback has no data migration implications.

---

## What This Feature Does (v1 Scope)

- Inline auto-fetch route connector between itinerary cards in Journey Desk (PR #519; no button click required)
- Estimates per-leg drive duration and distance for the current manual stop order
- Activity and meal stops with canonical coordinates only; ≥2 stops required, ≤10 enforced
- At most one ComputeRoutes call per stable routable stop set (keyed on stop IDs + coordinates)
- Shows `~N min drive · X.X km` directly in the connector; falls back to local haversine hints on provider error

## What This Feature Does NOT Do (Out of Scope for v1)

- No Optimize Day / automatic reordering
- No route map drawing or polylines
- No traffic-aware routing
- No ComputeRouteMatrix
- No geocoding (addresses → coordinates)
- No hotel or flight routing
- No multi-day optimization
- No persistent storage of estimates
- No caching
- No automatic/background calls

---

## Files Changed by Route Planning v1

| File | Role |
|---|---|
| `backend/app/core/config.py` | Feature flag + API key config (server-side) |
| `backend/app/routes/route_estimate.py` | Endpoint handler |
| `backend/app/services/route_estimate.py` | Service: fail-closed logic, ownership gate |
| `backend/app/services/google_routes_adapter.py` | HTTP adapter: single ComputeRoutes call |
| `backend/app/services/provider_registry.py` | Registry entry (`production_allowed=False`) |
| `backend/app/models/route_estimate.py` | Pydantic request/response models |
| `frontend/src/lib/api.ts` | `callRouteEstimate()` — POST only, no auto-calls |
| `frontend/src/lib/travelHints.ts` | `getRouteableStopsForEstimate()` — order-preserving filter |
| `frontend/src/components/trips/ItineraryDayColumn.tsx` | Auto-fetch `useEffect` + inline `route-connector-google` connector (PR #519 removed `CheckRoutePanel`) |
| `docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` | Governing ADR |

---

## Key Safety Invariants (Do Not Break)

1. `callRouteEstimate` is called only from the `useEffect` keyed on `routableStopsKey` — at most once per stable stop set. It must not be called from any other `onClick` or lifecycle hook.
2. Coordinates are sent to Google only after trip AND day ownership are verified.
3. `GOOGLE_ROUTES_API_KEY` is never referenced in frontend source (only in tests verifying its absence).
4. Stop order is never changed — `stop_order_preserved: true` in every response.
5. The feature flag default is `False` — missing env var never enables the feature.
6. Missing API key never breaks backend startup — `required_env_vars=()` in registry.
