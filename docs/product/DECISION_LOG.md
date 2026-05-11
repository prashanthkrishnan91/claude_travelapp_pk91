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
