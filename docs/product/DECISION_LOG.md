# Decision Log

Product decisions are recorded here so we do not re-litigate direction.

## Template

```
## YYYY-MM-DD — Decision title
- Decision:
- Why:
- Alternatives rejected:
- What would change our mind:
- Roadmap impact:
```

## Seed decisions

## 2026-05-10 — Shift from trip-first to discovery-first
- Decision: The app must be useful before a trip exists. Travel Idea / Saved Item is the future root object; Trip is one conversion path.
- Why: Trip-first gate forces users to commit before they explore; Discover-first matches real user intent and unlocks Saved, AI, and Watchtower stages.
- Alternatives rejected: Keep trip-first and treat Discover as a sub-feature.
- What would change our mind: Strong evidence that users will not engage without a trip context.
- Roadmap impact: Defines Stage 2 as the discovery-first shift; reorders saved/AI work behind it.

## 2026-05-10 — Travel Idea / Saved Item becomes future root object
- Decision: Saved items, not trips, are the long-lived primary object the rest of the product hangs off.
- Why: Saved-first lets Discover, AI, deals, points, and Watchtower all share one substrate.
- Alternatives rejected: Trip-as-root with saved-items as a child container.
- What would change our mind: A demonstrated cost in trip clarity that cannot be repaired.
- Roadmap impact: Stage 3 builds the saved-item foundation as a first-class root object.

## 2026-05-10 — Design sprint waits for Wife Wow Readiness Gate
- Decision: Major design transformation only after Discover + Saved + core trip flows are stable, AI Concierge is trustworthy, and no embarrassing leakage remains.
- Why: Painting the walls before the foundation is set wastes design work and rots fast.
- Alternatives rejected: Do design sprint earlier alongside feature work.
- What would change our mind: A specific high-impact surface where design is the blocker, not features.
- Roadmap impact: Stage 6 is gated by `Wife Wow Readiness Gate`; design polish beyond that gate is deferred.

## 2026-05-11 — Stage 2A Slice 2 Save backing uses lightweight `saved_items` foundation
- Decision: Stage 2A Slice 2 should implement Save on a new first-class, trip-optional `saved_items` backing (user-scoped row per saved result), while leaving all existing trip-scoped `itinerary_items` save/add paths unchanged.
- Why: Current save/add paths are strictly trip-bound (`trip_id` required) and feed trip-candidate/Trip Ideas flows by design; reusing them for global Save would either force a trip requirement or pollute trip planning surfaces. A dedicated `saved_items` substrate keeps discovery-first Save independent now and aligns with the Stage 3 root-object direction without touching `tripCandidates.ts`, `TripIdeasPanel`, TripBuilder, or concierge hydration.
- Alternatives rejected:
  - Option 1 (defer/disable Save): safest short-term but fails Stage 2A's core "discover and save before trip" user value and creates avoidable UX debt in `ResultActionSheet`.
  - Option 3 (reuse trip-scoped save with nullable trip linkage in `itinerary_items`): high regression risk because existing selectors/panels assume `itinerary_items` are trip candidates; this path would blur global saves with trip planning and violate stage boundaries unless multiple downstream consumers are refactored.
  - Option 4 (hidden/sentinel trip or other implicit trip bucket): explicitly forbidden; corrupts trip semantics and user-visible model.
- Risks and mitigations:
  - Risk: introducing a new table requires migration + API plumbing. Mitigation: keep Slice 2 scope minimal (create/list/delete only, strict user scoping, no ranking/list UX expansion yet).
  - Risk: duplicate place saves. Mitigation: enforce uniqueness at DB/API level on `(user_id, place_id, vertical)` or equivalent provider identity key.
  - Risk: accidental coupling into trip candidate flows. Mitigation: explicit boundary that no `saved_items` reads/writes are added to trip candidate selectors or trip panels in Slice 2.
- Exact Slice 2 implementation boundaries (must-haves):
  - Add minimal `saved_items` persistence path (migration + backend route/service + frontend helper) for Save action only.
  - Save payload should store normalized provider identity (Google place_id when present), vertical, display snapshot, and lightweight metadata needed to re-render saved cards.
  - Wire Save action in `ResultActionSheet` + Explore/Search result cards to this new path.
  - Keep Add to Trip/Create Trip on existing trip APIs.
- Exact Slice 2 implementation boundaries (must-NOT):
  - No hidden/sentinel trips.
  - No changes to `tripCandidates.ts`, `TripIdeasPanel`, `TripBuilder`, provider adapters, AI Concierge hydration, or live research behavior.
  - No conversion of global saved items into trip candidates; cross-over (e.g., "Add saved item to trip") is deferred.
  - No full Stage 3 Saved list product surface in this PR.
- SQL note for next implementation PR: include a focused migration creating `saved_items` with `user_id` FK, provider/place identity fields, content snapshot JSON, timestamps, and uniqueness/indexes; do not redesign trips/auth models.
- What would change our mind: Evidence that this migration cannot be delivered surgically (e.g., auth/RLS constraints force broad redesign) or that a pre-existing trip-optional persistence path already exists without trip-flow contamination.
- Roadmap impact: Unblocks Stage 2A Slice 2 action-sheet implementation with safe Save semantics and establishes the minimum substrate Stage 3 can expand.

## 2026-05-11 — Stage 2A Slice 5A: Hotels as discovery-only lodging cards (scope-lock)
- Decision: Hotels in Stage 2A Slice 5 are **discovery-only** lodging/property cards. They use the existing tripless Explore / verified place card pattern (same as Attractions Slice 4). They are **not** bookable hotel offers and carry no rate, price, or availability data.
- Architecture rules locked by this decision:
  - Google Places / verified place identity is acceptable for lodging discovery cards (`HotelDiscoveryCard` / `hotel_discovery` naming).
  - Do not claim real rates, nightly prices, total prices, availability, sold-out status, booking policy, cancellation policy, or "best deal" in Slice 5A.
  - Do not create or mock `/search/hotels`; do not introduce a fake hotel provider.
  - Search context fields (destination/location, check_in, check_out, guests, rooms) must be preserved in card payload so a future provider-backed offer can consume them without a migration.
  - `ResultActionSheet` is expected to support hotel discovery cards in the Slice 5A implementation PR (no new component contract needed).
  - `saved_items` cross-vertical schema (`hotel` enum value already present in migration 005) is sufficient; no additional schema migration is required for Slice 5A.
  - Real hotel rates/availability require a separate, explicitly deferred **Hotel Offer contract** backed by a real provider (e.g., Booking.com, Hotels.com API). That work is Stage 2B or later.
  - Naming convention: use `hotel_discovery` / `lodging_discovery` / `HotelDiscoveryCard` throughout. Avoid `offer`, `rate`, `availability`, `price`, or `booking` in Slice 5A identifiers.
- Why: Unblocks Hotels vertical in Stage 2A without creating false user expectations or requiring a provider integration that is not yet contracted. Mirrors the proven Attractions pattern. Preserves all context fields so the upgrade path to real offers is clean.
- Alternatives rejected:
  - Full provider-backed hotel offers in Slice 5A: no provider contracted; would require fake rates or mock data (violates No Mock/Sample Visible Data Pack).
  - Mock `/search/hotels` endpoint: explicitly forbidden; leaks false availability into user-visible UI.
  - Reusing generic "hotel" naming without discovery/offer separation: risks polluting the future real-offer contract with discovery-layer semantics.
- What would change our mind: A real hotel rate/availability provider is contracted and the Hotel Offer contract is written and reviewed before Slice 5A ships.
- Roadmap impact: Slice 5A ships Hotels discovery. Real hotel offers are explicitly deferred to a named future slice with a provider-backed Hotel Offer contract. BUILD_QUEUE and HANDOFF updated accordingly.

## 2026-05-12 — Provider Registry v1: central provider policy + Explore provider scope reset
- Decision: Add `backend/app/services/provider_registry.py` as the single, canonical source of truth for provider activation, addable-card authority, and disabled/quarantined status. Disallowed providers (Duffel, Amadeus, Brave, Serper, Foursquare) are registered as DISABLED or QUARANTINED and will not activate in production even if API keys are present. Duffel and Amadeus are no longer active roadmap items.
- Why: Provider behavior was scattered across route files, service adapters, and env-var checks with no central authority. The app is a private-use Travel Concierge, not a booking engine or OTA. A registry makes the policy explicit, makes it easy to extend (register + adapter + tests), and ensures disallowed providers fail closed without manual env audits.
- Approved provider stack: Google Places (canonical / addable cards), Anthropic (reasoning / Concierge notes only), Tavily (research context only), Yelp (enrichment/corroboration only), OpenWeather (weather/trip context only).
- Disabled/quarantined: Duffel Flights (DISABLED), Duffel Stays (QUARANTINED), Amadeus (DISABLED), Brave (QUARANTINED), Serper (QUARANTINED), Foursquare (DISABLED).
- Surgical refactors: `live_research.select_default_provider()` consults registry before returning Brave/Serper (fail-closed on registry import failure); `flights_provider.get_flight_provider()` consults registry before building Duffel adapter; `hotels_provider.get_hotel_provider()` consults registry before building Google Places adapter; `hotels_provider_duffel_stays.build_duffel_stays_provider_from_env()` consults registry as outer gate (returns None when QUARANTINED).
- Alternatives rejected: (a) per-file env-var-only gates — scattered, fragile, no central policy; (b) deleting adapter files — risky if adapter code is referenced elsewhere; quarantine is safer.
- What would change our mind: A specific booking/OTA provider is contracted, credentialed, and the Hotel Offer or Flights contract is written — at which point the registry entry is updated and re-approved explicitly.
- Roadmap impact: Provider Registry v1 is now the prerequisite gateway before any new provider is added. Hotels Discovery Live (Slice 5C) is the next product build. Duffel Stays (former Slice 5D) is no longer in the active build queue.

## 2026-05-12 — Stage 2A Slice 5B: Hotel Offer contract + Duffel Stays readiness scaffold
- Decision: Slice 5B adds the typed `HotelOffer` contract and a disabled-by-default `DuffelStaysProvider` scaffold. No live API calls. No user-facing rates.
- Architecture rules locked by this decision:
  - `HotelOffer` dataclass (`backend/app/contracts/hotels.py`) is the canonical shape for provider-backed hotel rate offers. It carries: vertical, provider, provider_property_id, provider_offer_id, destination, check_in, check_out, guests, rooms, currency, total_price, taxes_fees_included, cancellation_summary, booking_url, rate_fetched_at, provider_disclaimer, is_available, error_reason.
  - `HotelOffer` is never constructed by discovery-only adapters. `HotelResult` with `has_real_rate=False` / `offer_kind="discovery"` remains the discovery-card wire type.
  - `DuffelStaysProvider` (`backend/app/services/hotels_provider_duffel_stays.py`) is the Duffel Stays adapter scaffold. It requires `DUFFEL_STAYS_API_KEY` AND explicit `DUFFEL_STAYS_ENABLED=1` to activate. Both absent by default.
  - When disabled or uncredentialed, `search_hotels` returns `HotelSourceStatus.UNAVAILABLE` with zero rows. No mock/fixture fallback.
  - `HotelDiscoveryCard` and `HotelOffer` TypeScript interfaces are separated by `kind` discriminant in `frontend/src/components/explore/types.ts`.
  - **Superseded by Provider Registry v1 (2026-05-12):** `DuffelStaysProvider` is now QUARANTINED in `provider_registry.py`. `build_duffel_stays_provider_from_env()` consults the registry as an outer gate and returns `None` even when both env vars are present. Explicit registry re-approval is required before any Duffel Stays activation. The former "Slice 5D" is not an active roadmap item.
- What would need to change to re-activate Duffel Stays: Update `provider_registry.py` entry from QUARANTINED to an active role, confirm Duffel Stays API access, provision credentials in Railway backend env, implement live offer request in `DuffelStaysProvider.search_hotels`.
- Alternatives rejected:
  - Mock Duffel responses: explicitly forbidden (No Mock/Sample Visible Data Pack).
  - Enabling the adapter without credentials: `build_duffel_stays_provider_from_env` returns `None` without credentials; the seam falls back to `NullHotelProvider`.
- Roadmap impact: Slice 5B ships the contract foundation. Slice 5B preserved the disabled scaffold, but Provider Registry v1 supersedes activation. Slice 5C is Hotels Discovery Live only. Duffel Stays/live hotel offers require explicit future registry re-approval and are not in the active build queue.

## 2026-05-12 — Flights Provider Contract scaffold: Skyscanner + Ignav registry entries

- Decision: Add normalized `FlightItineraryOffer` contract and disabled-promotion-scaffold adapter shells for Skyscanner (preferred) and Ignav (evaluation/backup). Both are registered in Provider Registry v1 as `PENDING`/`EVALUATION` with `production_allowed=False`. No live API calls. No visible flight cards. Existing fail-closed unavailable state preserved.
- Why: Unblocks the implementation PR — when a provider key is confirmed, only the registry entry needs updating + the live adapter body needs implementing. The frontend seam, contract, and test suite are already in place.
- Provider registry roles added: `PENDING` (preferred candidate awaiting key), `EVALUATION` (backup/provisional candidate requiring validation before promotion).
- Promotion path (locked): (1) confirm key + access, (2) update registry entry (`production_allowed=True`, active role), (3) implement live `search_flights` body in the adapter shell, (4) pass validation tests. No shortcut path exists.
- Duffel and Amadeus: remain DISABLED/quarantined. No change.
- Alternatives rejected: adding live implementation before key is confirmed (no key exists); using Duffel/Amadeus (quarantined); mock/placeholder data (No Mock/Sample Visible Data Pack).
- What would change our mind: Both Skyscanner and Ignav are unavailable — would require evaluating another cash provider and adding a new PENDING entry.
- Roadmap impact: Flights v1 implementation PR is unblocked once key is confirmed. Stage 3 v3 ordering unchanged.

## 2026-05-12 — Flight product and provider contract (pre-Stage 3 v3)

- Decision: Flights must be completed before Stage 3 v3 (Create Trip from Saved Item). v1 implementation is cash live/link-out first. Points/award results are a separately gated track. No mock flights, no Duffel, no Amadeus, no booking engine.
- Product definition (locked):
  - User searches with origin, destination, dates, passengers, cabin class, and one-way / round-trip toggle.
  - App returns live available flight options from an approved cash provider.
  - Cards support one-way flights and round-trip pairs. Round-trip may be implemented as paired outbound/return card contract if provider response supports complete itineraries.
  - Each card carries AI scoring (same scoring convention as Hotels/Attractions/Restaurants).
  - Cash price shown only when sourced from a live cash provider (never estimated, never mocked).
  - Points/award price shown only when sourced from a confirmed real award availability API. Not derived from cash prices.
  - Each card has an external deep link to book (link-out; no booking engine, no PNR, no payments).
  - Flight cards are saveable via `ResultActionSheet` and addable to trips via the existing `POST /itinerary/items` path (`day_id: null`, unscheduled candidate). Do **not** use day-scoped helpers.
- Provider strategy (locked):
  - Cash flights: Skyscanner Live Prices is the preferred candidate — supports live create/poll search, bookable itineraries, and deep links. Requires confirmed API key/access before implementation begins.
  - Skyscanner Indicative Prices: may be used for inspiration / rough-estimate surfaces only. Must **never** be labeled as live bookable prices.
  - Duffel: remains DISABLED/quarantined in Provider Registry v1. Not an active roadmap item.
  - Amadeus: remains DISABLED/quarantined. Not an active roadmap item unless explicitly re-approved.
  - Points/award flights: separate provider track. Seats.aero or equivalent may be considered later only with confirmed API access and clear cached/live labeling. Do not infer points prices from cash prices.
- Provenance requirements (locked): every flight card must carry:
  - `provider` (name of the live provider)
  - `live_cached_status` (`live` | `cached`; never omit)
  - `fetched_at` (ISO timestamp)
  - `booking_link_source` (deep-link URL or provider name)
  - `price_currency` and `price_amount` (only when real; never estimated)
  - `points_program` and `points_amount` (only when sourced from a real award API; never derived)
- Fail-closed / disabled behavior (locked):
  - If no approved cash flight provider key is present in the registry, Explore Flights shows a polished "unavailable" state — not mock rows, not placeholder prices.
  - No `/search/flights` mock route reuse.
  - No fake cash or points estimates.
  - No booking, ticketing, or PNR claims beyond the external link-out.
- Non-goals (locked):
  - No booking engine.
  - No payments or checkout.
  - No ticketing or PNR/order management.
  - No Duffel (any product).
  - No Amadeus (unless re-approved).
  - No scraping-heavy provider path.
  - No stale/cached prices labeled as live.
  - No points estimates unless a real award API source is confirmed.
- Sequence: flight implementation is a prerequisite for Stage 3 v3. Stage 3 v3 (Create Trip from Saved Item) proceeds only after flight cards are saveable and addable to trips.
- Why: User explicitly wants real flights before Stage 3 v3. Flights follow the same live/link-out, discovery-first model as Hotels (discovery only) but flight-specific — a real provider is what makes them useful, not a mock UI. The link-out model avoids OTA/booking-engine scope while still delivering live prices.
- Alternatives rejected:
  - Mock flights / placeholder prices: explicitly forbidden (No Mock/Sample Visible Data Pack).
  - Duffel: quarantined; user-rejected.
  - Amadeus: quarantined; user-rejected.
  - Points/award in v1: separately gated; cannot be derived from cash prices.
  - Proceeding to Stage 3 v3 before flights: user-rejected ordering.
- What would change our mind:
  - Skyscanner Live Prices API is not accessible — would require evaluating another live/link-out cash provider (e.g., Travelpayouts, Kiwi.com Tequila, or a TPF-based search).
  - User explicitly reverses the sequencing decision.
- Provider Registry impact: any new flight provider must be registered in `provider_registry.py` before activation. Implementation PR must add a registry entry and gated adapter before any live calls.
- Roadmap impact: Flights implementation is the next item in the build queue. Stage 3 v3 is re-ordered to after flights v1 ships.

## 2026-05-12 — Stage 3 v2: Saved → Trip conversion v1 contract

- Decision: v1 scope is **Add to Existing Trip only**. A user on the `/saved` page can promote a saved idea into an unscheduled itinerary candidate on a trip they already own. "Create new trip from saved item" is explicitly deferred to Stage 3 v3+.
- Why:
  - "Add to Existing Trip" maps cleanly onto the existing `/itinerary/items` POST API and `itinerary_items` schema — no new SQL, no TripBuilder changes, no tripCandidates.ts changes.
  - "Create Trip from Saved Item" requires trip-creation form wiring, destination defaulting, and trip-shell scaffolding — a wider surface that deserves its own contract PR.
  - The `ResultActionSheet` "Add to Trip" on Explore cards stays deferred ("Coming soon"). The conversion action lives only on SavedShell cards in v2, keeping blast radius minimal.
- Safest first implementation slice:
  - On each saved card in `SavedShell`, add an "Add to Trip" action that opens a compact trip picker (inline dropdown or small modal; fetches user's trips via existing list-trips API).
  - On trip selection, call a new small frontend helper `addSavedItemToTrip` that posts to the existing backend route `POST /itinerary/items` with `trip_id`, `item_type`, `title`, `location`, `details`, `position`, and `day_id: null`. Do **not** reuse the day-scoped `createItem` or `addHotelToDay` helpers — those assume a scheduled day context. The direct trip-level route (`ItineraryItemDirectCreate` payload) is the correct path for unscheduled candidates.
  - Flights remain disabled: discovery-only saved flights carry no actionable offer data to add to a trip itinerary. Deferred until a real flight offer exists.
- Data mapping contract (locked): saved_item.display_snapshot + search_context → itinerary_items fields:
  - `title` ← `displaySnapshot.name` ?? `savedItem.displayName`
  - `location` ← `displaySnapshot.address` ?? `displaySnapshot.destination`
  - `item_type` ← restaurant → `meal`; attraction → `activity`; hotel → `hotel`; flight → deferred
  - `details` (open dict) ← vertical-specific safe fields only:
    - All verticals: `name`, `address`, `rating`, `tags`, `googleMapsUri`, `source: "saved_item"`, `savedItemId`
    - Restaurant adds: `cuisine`, `priceLevel`
    - Hotel adds: `checkIn`, `checkOut`, `guests` (from searchContext — discovery context for date awareness only; **no rates, prices, total cost, availability, or booking fields**)
    - Attraction: no vertical-specific additions beyond common fields
  - `aiScore` omitted: user's explicit save is a stronger signal than AI ranking; let tripCandidates default to 0 or sort-stable position
  - `day_id` = null (unscheduled candidate; TripBuilder picks it up via tripCandidates selector)
  - `position` = 0 or list-tail (stable; TripBuilder manages ordering)
- Hotel discovery-only invariant: even after conversion, `details` must never contain `totalPrice`, `nightly_rate`, `availability`, `bookingUrl`, or any rate/booking field. The Hotel Offer contract (Stage 2B+) is the gating requirement for any pricing in the trip workspace.
- Alternatives rejected:
  - Wire "Add to Trip" in ResultActionSheet (Explore cards): wider blast radius; would also need the trip picker inline in the Explore result sheet. SavedShell-first is narrower.
  - Add `trip_id` FK to `saved_items` row directly: unnecessary coupling; the itinerary_items row is the correct trip-scoped object.
  - Bulk "Add all" or "Create trip from all saved": explicit out-of-scope; too much auto-planning magic for v2.
  - Auto-select the most recent trip: silent actions are never right; user must pick explicitly.
- Must-NOT for the implementation PR:
  - No changes to `TripBuilder.tsx`, `tripCandidates.ts`, `TripIdeasPanel`.
  - No SQL migration.
  - No rates, prices, availability, or booking fields in any itinerary_items.details written by this flow.
  - No changes to ResultActionSheet (Explore stays deferred).
  - No new providers, no Concierge calls, no `/search/*` calls.
  - No flights conversion (disabled, clearly labelled).
- What would change our mind: Evidence that the existing `POST /itinerary/items` route is insufficient (e.g., a required field is missing from display_snapshot for a critical vertical) — in which case we extend the snapshot, not the schema.
- Roadmap impact: Stage 3 v2 implementation PR is the next queue item. Stage 3 v3 candidate is "Create Trip from Saved Item" (needs its own contract PR first). After Stage 3 stabilises, Stage 4 (AI destination intelligence) is next.

## 2026-05-12 — Flights v1: Ignav as live provider (Skyscanner rejected)

- Decision: Ignav (`ignav_flights`) is the Flights v1 live provider. `ProviderRole.LINK_OUT`, `production_allowed=True`. Activated by `IGNAV_API_KEY` + `IGNAV_FLIGHTS_ENABLED=1` env vars (server-side only).
- Why Ignav over Skyscanner: Skyscanner Live Prices API access was rejected. Ignav provides a REST API for live flight fares + booking deep-links. Free tier: 1,000 req/month. No booking engine, no PNR — link-out only.
- Why LINK_OUT role: Ignav returns prices + booking URLs for airline/OTA deep-links. The user is redirected to book on the airline or OTA. No payment processing, no ticketing, no PNR in our system.
- Safety constraints locked:
  - API key is server-side only; never `NEXT_PUBLIC_` or client-side.
  - No mock/fabricated flight data in any code path.
  - No points prices. Cash only.
  - No booking engine, no PNR, no payments, no scraping.
  - Duffel and Amadeus remain DISABLED/quarantined.
- Booking link priority: `airline_direct` > `ota` > `provider_deeplink`. UNAVAILABLE if none.
- Latency budget: search call (~15s timeout) + parallel booking links (~5s each, max 5 concurrent) ≈ 20s total. Acceptable for flight search.
- Roadmap impact: Flights v1 shipped. Stage 3 v3 (Create Trip from Saved Item) is next; needs its own contract PR.

## 2026-05-13 — Stage 3 v3: Create Trip from Saved Item — v1 contract

- Decision: "Create Trip from Saved Item" is a user-confirmed trip creation flow prefilled from a saved item. The user always sees and can edit a confirmation form before the trip is created. No silent trip creation in any vertical.

### Flights v1 constraint carry-forward (locked)
Duffel is search-only (`LINK_OUT`, `production_allowed=True`). Google Flights is `SEARCH_REDIRECT` link-out only. No booking/orders. `DUFFEL_BOOKING_ENABLED=0`. Ignav is DISABLED. These constraints are not changed by Stage 3 v3. A saved flight card carries a Google Flights search URL — not a booking. The trip creation flow must not claim booking, confirm availability, or change these constraints.

### Vertical scope — what is enabled in v1

| Vertical | v1 status | Condition |
|---|---|---|
| **Flight** | Enabled | Strongest path; `search_context` has origin, destination, date(s), passengers. Confirmation form pre-filled from these fields. |
| **Hotel** | Enabled with restriction | Pre-fill destination/dates/guests from `search_context` only. Must not imply rate, price, or availability. Confirmation form required. |
| **Restaurant** | Conditional | Enabled only when `search_context.destination` or `display_snapshot.destination` is reliably set. Destination can prefill when reliable; start/end dates are always user-entered required fields. |
| **Attraction** | Conditional | Same condition as Restaurant. Destination can prefill when reliable; start/end dates are always user-entered required fields. |

### Prefill contract — saved flight

Trusted source fields (from `saved_items.search_context` and `display_snapshot`):

| Trip form field | Source field | Fallback |
|---|---|---|
| Trip title | `"{origin} → {destination}"` (city names when resolvable; IATA codes otherwise) | User input |
| Origin | `search_context.origin` | Blank (user must fill) |
| Destination | `search_context.destination` | Blank (user must fill) |
| Start date | `search_context.departure_date` | Blank (user must fill) |
| End date | `search_context.return_date` (round-trip). One-way: default to `departure_date`; user must edit before submit. Never omit. | `departure_date` pre-filled |
| Travelers | `search_context.passengers` (integer) | 1 |
| Cabin class | `search_context.cabin_class` (display-only, not editable in v1) | Omit |
| Itinerary seed | The saved flight added as unscheduled candidate (`day_id: null`) after trip is confirmed and created | — |

### Prefill contract — saved hotel

Trusted source fields:

| Trip form field | Source field | Fallback |
|---|---|---|
| Trip title | `"{destination} trip"` using `search_context.destination` | User input |
| Destination | `search_context.destination` | Blank |
| Start date | `search_context.check_in` | Blank (user must fill) |
| End date | `search_context.check_out` | Blank (user must fill) |
| Travelers | `search_context.guests` (integer) | 1 |
| Itinerary seed | The saved hotel added as unscheduled candidate after trip confirmed | — |

Date condition: if either `check_in` or `check_out` is absent from `search_context`, both date fields show blank and the user must fill them before submitting. Do not pre-fill one date and leave the other blank.

Invariant: `details` for the hotel itinerary seed must never contain `totalPrice`, `nightly_rate`, `availability`, `bookingUrl`, or any rate/booking field (same rule as Stage 3 v2 hotel mapping). Discovery-context fields only.

### Prefill contract — saved restaurant / attraction

Trusted source fields:

| Trip form field | Source field | Fallback |
|---|---|---|
| Trip title | `"{destination} trip"` or `"{name} trip"` | User input |
| Destination | `search_context.destination` ?? `display_snapshot.destination` | **Blank — user must fill if missing** |
| Start date | None — user must enter | Required; no auto-fill |
| End date | None — user must enter | Required; no auto-fill |
| Travelers | None | 1 |
| Itinerary seed | The saved item added as unscheduled candidate after trip confirmed | — |

Gate rule: if destination cannot be reliably resolved from `search_context.destination` or `display_snapshot.destination`, the confirmation form must prompt the user to enter it. Do not fabricate or guess a destination.

### Confirmation form contract (all verticals)

- Form is always shown — no auto-create path exists in v1.
- Required fields (form must not submit unless all are populated): trip title, destination, start date, end date.
- Travelers is optional; pre-filled from saved item context when available; defaults to 1.
- Why both dates are required: the existing trip creation and day-generation logic expects both `start_date` and `end_date` to produce a fully usable trip shell. A trip without an end date creates a degenerate shell that the day grid cannot render correctly.
- Form title: **"Create a new trip"** (not "Book" or "Reserve").
- Submit label: **"Create trip"**.
- The saved item is added as an unscheduled itinerary candidate (`POST /itinerary/items`, `day_id: null`) immediately after the trip creation call succeeds.
- On success, navigate directly to the newly created trip. Do not stay on `/saved`. Do not leave navigation destination ambiguous.

### API reuse (locked)

| Action | API | Notes |
|---|---|---|
| Create trip | Existing `POST /trips` (or equivalent trip creation route) | Reuse as-is; no new backend route |
| Seed itinerary item | Existing `POST /itinerary/items` with `day_id: null` | Same path used by Stage 3 v2 |
| Load user's existing trips | Existing list-trips API | Already used by Stage 3 v2 trip picker |

No new backend routes, no new SQL, no provider calls, no Concierge calls, no `/search/*` calls in v1.

### Trusted fields for prefill (summary)

Only fields from `saved_items.search_context` and `saved_items.display_snapshot` are trusted for prefill. `provenance` is read-only evidence and must not drive form values. Fields not present in `search_context` or `display_snapshot` must show blank in the form, not be guessed or inferred from other sources.

### Must-not-build in Stage 3 v3 implementation PR

- No booking, order creation, or payment of any kind.
- No fake rates, prices, or availability claims for any vertical.
- No Google Flights booking claim (only the existing SEARCH_REDIRECT link passes through as-is).
- No multi-airport Duffel search expansion.
- No new provider calls of any kind.
- No new Concierge calls.
- No SQL migration (existing `saved_items` schema + `itinerary_items` schema covers v1 needs; if a real gap is found, it must be stated explicitly before any migration is written).
- No TripBuilder.tsx changes.
- No `tripCandidates.ts` changes.
- No `ResultActionSheet` wiring for the Create Trip action on Explore cards (deferred; Stage 3 v3 wires SavedShell only, same blast-radius principle as Stage 3 v2).
- No itinerary route changes.
- No auto-scheduling — itinerary seed is always unscheduled (`day_id: null`).
- No "Create trip from all saved items" bulk action.

### Implementation slice for next PR (after this contract merges)

One focused Level 2 frontend PR. Target files: `SavedShell` (add "Create Trip" action per card), a new `CreateTripFromSavedModal` (or inline sheet) component, and the thin `createTripFromSavedItem` API helper.

Steps:
1. Add `createTripFromSavedItem(savedItem)` frontend helper: calls `POST /trips` with prefilled fields → then calls `POST /itinerary/items` with the saved item as unscheduled seed.
2. Add "Create Trip" button/action to each saved card in `SavedShell` (all verticals that satisfy their v1 condition above).
3. Show `CreateTripFromSavedModal` with prefilled form; user confirms or edits; on submit calls the helper above.
4. Navigate to the newly created trip on success (deterministic — not `/saved`, not conditional).
5. Test all four verticals with structural tests (`create-trip-from-saved.test.mjs`). Include: form renders with correct prefill for each vertical; one-way flight defaults end_date to departure_date; round-trip flight uses return_date; missing-destination gate for restaurants/attractions; both date fields required (form does not submit when either is blank); hotel both-dates-absent shows both blank; no-booking/no-rate invariants; API call sequence; navigation to new trip on success.
6. No backend change. No SQL. No TripBuilder change. No provider change.

- Why: Explicit confirmation prevents accidental trip clutter. Pre-fill from `search_context` avoids re-asking the user for information they already provided. Flight is the strongest path because it always provides origin, destination, and date(s) — the minimum trip shell fields. Hotel is the second-best path. Restaurants/attractions need destination fallback because their search context is less reliably set.
- Alternatives rejected:
  - Silent creation (auto-create on one tap): risks polluting the trips list with poorly-named or date-less trips; explicitly rejected.
  - ResultActionSheet wiring on Explore cards in v1: wider blast radius; SavedShell-first keeps the scope equivalent to Stage 3 v2.
  - Date auto-fill for restaurants/attractions: no reliable date source in these verticals; blank is correct.
  - New backend route for combined trip-create + seed: unnecessary; existing `POST /trips` + `POST /itinerary/items` compose cleanly from the frontend.
  - Defer restaurants/attractions entirely: destination-shell is useful and the risk is low when destination is reliable.
- What would change our mind: Evidence that `POST /trips` does not exist or requires a field not derivable from `search_context` (would require a backend contract amendment before implementation begins). Or evidence that `search_context` is not reliably populated for saved flights (would scope flights back to conditional).
- Roadmap impact: Stage 3 v3 implementation PR is the immediate next queue item after this contract merges. Completes the Saved → Plan conversion arc. Opens the door to Stage 4 (AI destination intelligence) once Stage 3 is stable.
