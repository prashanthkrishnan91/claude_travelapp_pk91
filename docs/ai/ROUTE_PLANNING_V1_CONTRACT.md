# ADR — Route Planning v1 Contract

Status: **Decision-only. No implementation in this PR.**
Date: 2026-06-15
Stage: 3.5 (design adoption) → forward-looking Journey Desk planning capability.
Decision type: Product + technical contract that gates a future capability slice.

This ADR defines the **safe v1 contract** for route planning before any code is
written. It exists because the route-readiness chain (#504, #506, #507, #508)
has now made day-level coordinate coverage honest and observable, which makes it
tempting to jump straight to "Optimize Day." This document deliberately slows
that down and fixes the contract first.

> **Related ADR:** the *AI advisor layer* on top of this travel-time foundation
> is governed separately by `docs/ai/AI_ROUTE_PLANNING_V1_ADR.md` (AI Route
> Planning v1 — read-only, explain-first, no auto-reorder, no fabricated times).
> This document owns the provider / travel-time contract; that one owns how AI is
> allowed to talk about and propose changes to a day's route.

## Context — what already shipped (the route-readiness chain)

These are display/data-correctness changes only. **None of them call a routing
provider, compute travel times, or reorder items.**

- **PR #504** — travel hints read coordinates via the canonical readers
  (`readCanonicalLat`/`readCanonicalLng` in `tripItemMetadata.ts`); no fabricated
  coords.
- **PR #506** — flight/hotel pairs are excluded from adjacent travel hints (only
  activity/meal adjacency is hinted).
- **PR #507** — passive `RouteReadinessStatus` day-level coordinate coverage
  indicator (`computeRouteReadiness` in `travelHints.ts`); display-only; returns
  `null` when fewer than 2 eligible stops or all eligible stops already have
  coordinates.
- **PR #508** — Concierge fast-path now preserves Google Places `lat`/`lng` into
  `GoogleVerification`, closing the last active ingress gap so fast-path-added
  activity/meal items count as located.

Net effect: the app can now **honestly state** how many activity/meal stops on a
day have coordinates. It still does **not** know how long it takes to travel
between them. v1 is about closing that gap *safely*, not about optimization.

## Recommendation (read this first)

**PROCEED, but in the narrowest possible form, and not yet with a live provider.**

1. v1 is a **manual, user-triggered "Check route" action** that returns a
   **per-day travel-time preview** for the existing manual order — labeled as a
   **provider estimate, not a guarantee**. No reordering. No optimization.
2. **Provider choice for v1: start with "no provider yet" → land the registry +
   backend contract behind a flag → then adopt Google Routes API
   (Compute Route Matrix) as the first real provider.** Google is recommended
   over Mapbox/OSRM because the app already standardizes on Google Places for
   canonical identity and already has a centralized `provider_registry.py` that
   models a Google key; adding a Google routing role is the smallest honest
   extension of the existing approved stack. See [Provider decision](#3-provider-decision).
3. **Optimize Day stays disabled** until a provider is live, validated, and the
   merge gate below is satisfied. Until then any "Optimize Day" affordance must
   be absent or explicitly disabled with an honest reason — never a fake reorder.

This ADR does not authorize the implementation. It authorizes the **next 3
PRs** in [Release sequence](#7-release-sequence), each independently gated.

---

## 1. Product contract

### What v1 IS

- **Manual "Check route" action**, per day, in the Journey Desk. Nothing fires
  automatically.
- **Day route summary = travel-time preview only**: for the day's existing
  activity/meal stops *in their current manual order*, show the estimated
  segment travel times (e.g. "~8 min walk", "~15 min drive") and a day total.
- Times are **provider-estimated**, surfaced as estimates, never as guarantees
  or bookable promises.
- The action is only enabled when `RouteReadinessStatus` reports the day is
  route-ready (≥2 eligible stops, all with canonical coordinates).

### What v1 is explicitly NOT ("Not v1")

- ❌ **Auto-reorder / Optimize Day** — no resequencing of items, automatic or
  suggested-and-applied. Optimize Day remains **disabled** until a later,
  separately-approved slice.
- ❌ **Multi-day / whole-trip optimization** — v1 is single-day, current-order
  only.
- ❌ **Hotel/airport routing** — flights, hotels, and notes are never routed
  (see [Eligible item contract](#2-eligible-item-contract)).
- ❌ **Route map drawing / polylines** — no drawn paths, no map line geometry.
  v1 is a text travel-time preview only. (The existing MapTiler basemap is a
  visual tile provider, not a routing provider, and is untouched.)
- ❌ **Hidden / background provider calls** — no calls on page load, no polling.
- ❌ **Fake travel times** — never fabricate, interpolate from straight-line
  distance, or guess a duration when the provider is unavailable. Fail closed
  with an honest empty/disabled state.

---

## 2. Eligible item contract

- **Only `activity` and `meal` stops are routeable.** This mirrors the existing
  adjacency rule already enforced in `travelHints.ts` and `computeRouteReadiness`.
- **Flights, hotels, and notes are excluded** from routing entirely (consistent
  with PR #506). They are not segment endpoints and are never sent to a provider.
- Items **must have canonical coordinates** (`hasRouteableCoordinates` in
  `tripItemMetadata.ts`, reading camelCase-first with snake_case fallback).
- **Missing coordinates disable route planning for that day** (or show a clear
  reason — reuse the existing `RouteReadinessStatus` copy: "X of Y stops have
  location data. Add locations before route planning."). v1 must not silently
  drop a stop and route the remainder, because that would produce a misleading
  total.
- **Never geocode from an address.** This is a hard repo invariant
  (No Mock/Sample Visible Data + Enrichment Evidence Only packs). Coordinates
  come only from canonical Google Places ingress already in place.
- **Never fabricate coordinates, travel times, or sequence.** The provider is
  the only source of a travel time; the user is the only source of sequence in
  v1.

---

## 3. Provider decision

No routing/directions provider exists in `provider_registry.py` today (verified:
the only `route` mention is Duffel flight-offer route data, unrelated). MapTiler
is registered strictly as `MAP_TILE` (visual basemap only, cannot mint
places/geocode). So v1 requires a **new provider role** — call it
`ROUTING` / `route_matrix` — registered explicitly before any adapter is written.

| Candidate | Fit for this app | Cost / rate-limit risk | Impl. complexity | Privacy / data sent | Quality / reliability | Existing env/registry support | v1 verdict |
|---|---|---|---|---|---|---|---|
| **Google Routes API (Compute Route Matrix / Routes)** | High — app already standardizes on Google Places for canonical identity; same vendor, same billing account, same key-management story | Medium — billed per element; **must** be guarded (manual trigger, max-stops cap, cache) | Low–Medium — REST POST, well-documented matrix endpoint | Sends coordinate pairs (no PII beyond lat/lng already stored) | High — mature, traffic-aware, walking/driving modes | **Closest fit** — registry already models a Google key (`GOOGLE_PLACES_API_KEY`); a sibling `GOOGLE_ROUTES_API_KEY` + new `ROUTING` role is a clean extension. *(Routes API may require enabling a separate API + key — treat as a new env var, decided at impl time, not now.)* | **Recommended first real provider** |
| **Mapbox (Matrix / Directions API)** | Medium — good API, but introduces a second mapping vendor alongside MapTiler/Google with no offsetting benefit | Medium — generous free tier, then per-request | Low–Medium — clean REST | Sends coordinates to a new third party | High | Weak — net-new vendor, net-new env, net-new registry role with no reuse | Not for v1 (reconsider only if Google Routes is blocked) |
| **OSRM (self-hosted) / free public OSRM** | Low for v1 — self-host = ops burden; public demo server is **not** acceptable for product traffic (rate-limited, no SLA, ToS) | Self-host: infra cost + maintenance. Public: unreliable / disallowed | High (self-host) | Self-host = best privacy; public = unknown | Self-host good; public poor/unreliable | None — no infra, no registry entry | Not for v1 |
| **No provider yet** | Highest immediate safety — ship registry + backend contract + UI shell behind a flag, returning a clear "routing not configured" state | Zero | Lowest | None | N/A | Already supported (flag-off path) | **Recommended starting point (PR 1–2)** |

**Decision:** sequence **"no provider yet" → Google Routes API**. Stand up the
registry role, config skeleton, and flag-gated backend contract with the
fail-closed "not configured" path first; adopt Google Routes as the first live
provider only after the merge gate is satisfied. Do not add Mapbox or OSRM for
v1.

---

## 4. Cost guardrail (hard safeguards — required before any live provider call)

These are non-negotiable preconditions for the provider-implementation PR:

- **No automatic calls on page load** or on day open. Ever.
- **Only a user-triggered "Check route"** action initiates a provider call.
- **Max stops per request** — hard cap (proposed: **12** eligible stops per day
  request; if a day exceeds it, disable with an honest reason rather than
  truncating silently). Final number decided at impl time, but a cap must exist.
- **Cache policy** — cache a day's matrix result keyed on the ordered set of
  stop coordinates + travel mode (see [cache key concept](#5-backendapi-contract-proposal));
  re-checking an unchanged day must not re-bill.
- **No background polling**, no prefetch, no speculative warming.
- **Clear UI affordance before calling** — the user always knowingly triggers
  the estimate; no implicit calls behind navigation.
- **Graceful failure if quota/key missing** — fail closed to a clear "route
  estimate unavailable" state; never fabricate a time, never retry-storm.

---

## 5. Backend / API contract proposal (documented, NOT implemented)

> Shapes below are a proposal to review in PR 2, not a built endpoint.

**Proposed endpoint:** `POST /trips/{trip_id}/days/{day_id}/route-estimate`
(flag-gated; returns a disabled/not-configured response until a provider is
live).

**Request payload (proposed):**
```jsonc
{
  "mode": "walking | driving",          // default decided at impl time
  "stops": [                            // ordered = current manual order
    { "item_id": "…", "lat": 25.79, "lng": -80.13 }
  ]
}
```
- Server re-validates: only activity/meal items, all with coordinates, ≤ max
  cap. Rejects (422) otherwise — never partially routes.

**Response payload (proposed):**
```jsonc
{
  "provider": "none | google_routes",
  "estimated": true,                    // always an estimate, never guaranteed
  "segments": [
    { "from_item_id": "…", "to_item_id": "…", "duration_seconds": 480, "mode": "walking" }
  ],
  "total_duration_seconds": 1320,
  "cache": { "hit": true, "key": "…" }
}
```

**Error states (proposed):**
- `provider_not_configured` — flag/key absent → honest disabled state (200 with
  `provider:"none"`, or 503; decided at impl).
- `not_route_ready` — <2 eligible stops or missing coords (422).
- `too_many_stops` — exceeds cap (422).
- `provider_error` / `quota_exceeded` — upstream failure → no fabricated times.

**Cache key concept:** hash of `(ordered list of (lat,lng) rounded, mode,
provider)`. Order-sensitive (v1 routes the manual order). Reordering or editing a
stop's coords invalidates naturally.

**Provider registry location:** `backend/app/services/provider_registry.py` —
add a new `ProviderRole.ROUTING` (or `ROUTE_MATRIX`) entry, e.g.
`google_routes`, `production_allowed=False` initially, `required_env_vars`
declared but flag-gated. Adapter file (future): `route_provider_*.py`, consulting
the registry exactly like existing adapters. **No adapter in PR 1.**

**Telemetry / logging needed:** structured log on every route-estimate request —
provider id, stop count, cache hit/miss, duration, outcome (ok / not_ready /
not_configured / error). Name the failure seam (log key) in the implementing PR
body per repo runtime-evidence rules. Track cost-relevant counters (billed calls
vs cache hits) so the cost guardrail is auditable.

**DB schema:** **none required for v1.** Route estimates are derived, ephemeral,
and cacheable in-process / short-TTL. A persisted route table is **not justified**
until/unless v1 graduates to durable optimization — explicitly out of scope here.

---

## 6. UI contract proposal (documented, NOT implemented)

> No UI ships in this ADR or in PR 1. This is the target contract for PR 3.

- **Placement:** the "Check route" action lives in the Journey Desk day surface,
  adjacent to the existing `RouteReadinessStatus` / `DayTravelHintBar` in
  `ItineraryDayColumn` — **the Journey Desk layout is not restructured.**
- **Disabled state:** when `RouteReadinessStatus` is not route-ready (missing
  coords / <2 eligible stops / over cap), the action is disabled with the
  existing honest reason copy. No spinner, no fake result.
- **Loading state:** explicit loading affordance only after the user triggers
  the check (since the call is user-initiated).
- **Error state:** "Route estimate unavailable" with the reason category; never
  a fabricated time.
- **Success state:** per-segment estimates + day total, each clearly labeled as
  **provider-estimated, not guaranteed** (e.g. "~ estimates · traffic and
  conditions vary").
- **Manual vs suggested order:** v1 shows estimates for the **user's manual
  order only**. There is no suggested order in v1. The user keeps full control
  of sequence; the UI must not imply the app will reorder anything.

---

## 7. Release sequence (next 3 PRs after this ADR)

Each PR is an independent capability slice with its own readiness gate. Do not
collapse them.

1. **PR 1 — Provider registry / config skeleton only.**
   Add `ProviderRole.ROUTING` + a `google_routes` entry (`production_allowed=False`,
   flag-gated) to `provider_registry.py`. No adapter, no endpoint, no UI, no live
   call, no new env var *consumed* (declare the intended var name only). Tests:
   registry policy assertions. Docs-adjacent, near-zero runtime risk.

2. **PR 2 — Backend route-estimate endpoint behind a flag.**
   Implement `POST …/route-estimate` returning the fail-closed
   `provider_not_configured` path and the `not_route_ready` / `too_many_stops`
   validations. **No live provider call yet** (or behind a default-off flag).
   Enforce the cost guardrails (cap, no auto-call, cache key). Tests: contract +
   validation + fail-closed behavior. Runtime seam (log key) named in PR body.

3. **PR 3 — UI route preview behind a flag.**
   Add the "Check route" action + loading/error/success/disabled states in the
   Journey Desk day surface, wired to PR 2, all behind the same flag. Estimates
   labeled as provider-estimated. No reorder, no map line. Tests: state
   coverage + disabled-when-not-ready + no-fabrication guards.

*(A live Google Routes adapter — flipping the flag on — is a fourth, separately
gated step, not part of this sequence, and only after the merge gate below.)*

---

## Merge gate for future implementation

Before **any** PR that turns on a live routing provider may merge, all of the
following must be true and stated in the PR body:

- [ ] A `ROUTING` provider entry exists in `provider_registry.py` and is the
      single source of activation policy for the routing call.
- [ ] Cost guardrails are enforced in code: no auto-call, user-triggered only,
      max-stops cap, cache, no polling.
- [ ] Fail-closed path proven: missing key/quota/flag → honest disabled/empty
      state, **no fabricated times**, no retry storm.
- [ ] Only activity/meal stops with canonical coordinates are sent; flights /
      hotels / notes excluded; no geocoding from address.
- [ ] Travel times are labeled provider-estimated, not guaranteed, in every
      surface that shows them.
- [ ] Optimize Day / auto-reorder remains absent or explicitly disabled (not a
      fake reorder).
- [ ] Telemetry distinguishes billed calls from cache hits; the failure seam
      (log key) is named.
- [ ] Supabase SQL requirement stated (expected: **none**).
- [ ] Latency Budget Pack honored (user-triggered, single matrix call, cached).

If any box cannot be checked, the provider stays off.

---

## Out of scope for this ADR (no production changes)

No production code, no package changes, no env vars added, no SQL, no UI, no
Optimize Day, no route map, no item reordering. Existing coordinate ingress
paths (#504/#506/#508) and the Journey Desk layout are untouched. This is a
decision-only document.
