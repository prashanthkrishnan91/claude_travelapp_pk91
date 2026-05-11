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
