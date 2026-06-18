# Route Planning v1 — Activation Runbook

**Status:** Feature complete, production-inert. Requires explicit opt-in to activate.  
**Last validated:** 2026-06-18 (post PR #514 merge)  
**Governed by:** `docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` (PR #509 ADR)

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

5. **Run the frontend route-estimate tests:**
   ```
   npx vitest run frontend/tests/route-estimate-check-route.test.mjs
   npx vitest run frontend/tests/route-readiness-status.test.mjs
   ```

6. **Confirm no automatic calls.** The `callRouteEstimate` function in `frontend/src/lib/api.ts` must be invoked only from the `onClick` handler of the "Check route" button. Verify no `useEffect` calls it (the only `useEffect` in `CheckRoutePanel` resets state to `"idle"` — it does not call the API).

7. **Confirm Google Routes API key has appropriate quota limits set** in the Google Cloud Console before use (see Cost Guardrails below).

---

## Smoke-Test Sequence (Non-Production / Preview Only)

After enabling `ROUTE_ESTIMATE_V1_ENABLED=true` and setting `GOOGLE_ROUTES_API_KEY` in a non-production environment:

### Step 1 — Verify disabled path is gone

With both vars set, make a direct API call and confirm `status` is NOT `"disabled"`:
```bash
curl -X POST \
  https://<preview-url>/itinerary/<trip_id>/days/<day_id>/route-estimate \
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
2. Confirm the "Check route" button is visible.
3. Click "Check route" — confirm loading spinner, then estimated leg durations appear.
4. Confirm estimates are labeled as "estimated only" (not guaranteed times).
5. Confirm the stop order in the results matches the original manual order exactly.
6. Confirm no automatic call fires when switching days or changing items.

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
| Disabled | `ROUTE_ESTIMATE_V1_ENABLED` = false | `disabled` | `[]` | _(button visible but shows error message)_ |
| Not configured | Flag true, key missing | `not_configured` | `[]` | Error message from `response.message` |
| Auth failure | Trip/day not owned | HTTP 404 | — | Generic error catch |
| Too few stops | `<2` valid stops | HTTP 422 | — | Button not rendered (`routableStops.length < 2`) |
| Too many stops | `>10` valid stops | HTTP 422 | — | Generic error catch |
| Provider error | Google API error/timeout | `provider_error` | `[]` | Error message from `response.message` |
| Success | All gates pass | `success` | populated | Per-leg durations and distances |

---

## Cost Guardrails

- **One ComputeRoutes call per manual button click.** No background calls, no cron jobs, no automatic re-estimation on item change.
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
3. **Full revert:** If the feature itself is problematic, the `CheckRoutePanel` component is isolated in `ItineraryDayColumn.tsx`. Removing it from the render tree does not affect other Journey Desk functionality.
4. **No database changes needed.** Route estimates are ephemeral — not persisted. Rollback has no data migration implications.

---

## What This Feature Does (v1 Scope)

- Manual "Check route" button in Journey Desk expanded day view
- Estimates per-leg drive duration and distance for the current manual stop order
- Activity and meal stops with canonical coordinates only
- Single ComputeRoutes call to Google Routes API per click
- Results labeled as estimated, not guaranteed

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
| `frontend/src/components/trips/ItineraryDayColumn.tsx` | `CheckRoutePanel` component — button-triggered only |
| `docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` | Governing ADR |

---

## Key Safety Invariants (Do Not Break)

1. `callRouteEstimate` is called only from `onClick` — never from `useEffect` or page lifecycle.
2. Coordinates are sent to Google only after trip AND day ownership are verified.
3. `GOOGLE_ROUTES_API_KEY` is never referenced in frontend source (only in tests verifying its absence).
4. Stop order is never changed — `stop_order_preserved: true` in every response.
5. The feature flag default is `False` — missing env var never enables the feature.
6. Missing API key never breaks backend startup — `required_env_vars=()` in registry.
