# AI Concierge - Semantic Place Intelligence v2

Architecture Memo and Implementation Blueprint - Revised after technical cofounder review

Date: 2026-05-05
Repo: prashanthkrishnan91/claude_travelapp_pk91
Status: Architecture / spec / planning only. No code in this document.
Severity classification: Level 3 - full plumbing analysis + split plan.

## 0. Revision decision record

This v2 memo revises the OPUS architecture plan. The target architecture is validated, but the original rollout plan is not accepted as implementation-ready without changes.

### Final verdict

Build Semantic Place Intelligence, but do not implement it as an observation-only Frame Extractor first. The first intelligence implementation must be a real vertical slice that returns verified addable cards behind a feature flag.

The product problem is not "breweries are missing from a map." The product problem is that the current concierge still has category/bucket logic acting as the execution brain. Any plan that keeps the broken execution brain alive for too long will waste time and frustrate wife-testing.

### What v2 accepts from the OPUS plan

- LLM plans; deterministic systems verify.
- Google Places remains the canonical source for addable cards.
- Editorial, Tavily, Brave, Serper, Yelp, and Foursquare are evidence only, never card-minting substrates.
- Open-vocabulary ExperienceFrame replaces category routing as the interpretation layer.
- Semantic ranking is feature-based and deterministic.
- Batched reasoning replaces serial per-card LLM reasoning.
- Follow-up handling must operate on the prior result pool whenever possible.
- Trust gates are not negotiable.
- Frontend card shape should remain sticky and backend-first.

### What v2 rejects or revises

| OPUS plan item | v2 decision | Why |
|---|---|---|
| PR-2 observation-only Frame Extractor | Reject | It leaves the current bucket pipeline as the execution brain and may still return no cards. |
| PR-2 + PR-3 split between frame/planner and retrieval/ranker | Revise | The first intelligence PR must drive retrieval and ranking end-to-end behind a flag. |
| Phase 1 depending on Google AI summaries | Reject as dependency | Google summary fields may be unavailable, expensive, or policy-sensitive. They are Phase 2 opportunistic evidence. |
| Startup information_schema check as mandatory Phase 0 | Revise | May require direct DB access or new RPC. Make it best-effort only; runtime schema tolerance is the durable fix. |
| Tavily/editorial evidence in the first vertical slice | Defer | It adds latency and trust complexity before card-return reliability is proven. |
| Full LLM reason quality in the first retrieval PR | Split | First prove fast verified cards and deterministic safe reasons; then add batched LLM reasons and validators. |
| Frontend optional evidence UI in Phase 1 | Defer | Backend payload can be additive, but visible UI changes are unnecessary for the first vertical slice. |

### Implementation principle

Do not build scaffolding that cannot improve the wife test. Every major PR should move one of these metrics:

- verified card return rate
- semantic relevance of returned cards
- reason quality grounded in evidence
- follow-up correctness
- latency and observability

## 1. Current failure and root cause

### Reported production failure

Destination: Chicago
Prompt: "best breweries along the waterfront"
Result: text-only answer, no addable cards.
Follow-up: "best breweries"
Result: text-only answer, no addable cards.

Relevant log facts:

```text
turn_mode=new_search
card_pool_size=0
has_prior_cards=False
provider_call_expected_for_future_mode=True
stage1_prior={'place_recommendations': 1.0, 'trip_advice': 0.0, 'unsupported': 0.0}
response_type=place_recommendations
sources_used=[]
POST /ai/concierge/search -> 200
concierge_request_log persist failed because intent_classifier_version is missing in schema cache
```

### Interpretation

The high-level classifier did not fail. It correctly recognized a place-recommendation ask. The failure happened downstream in retrieval, verification, ranking, card assembly, or fallback behavior.

The current architecture can still classify an ask correctly and produce zero cards because the execution path depends on a fixed ontology, fixed place-type assumptions, and hard category gates. That is the real bug.

### Likely current failure path

1. The prompt is classified as a place recommendation.
2. The existing fast dynamic place parser cannot represent "brewery along the waterfront" as an open-vocabulary experience frame.
3. It may default to a broad or wrong place type, then apply a category score gate that rejects valid breweries.
4. The fallback path may attempt Tavily/editorial extraction, but sources_used=[] means no usable extracted/verified sources made it through.
5. The response degrades to text-only even though the user asked for places.
6. Logging schema drift adds noisy errors and weakens observability, but it is not the direct user-facing card failure.

### Durable root-cause statement

The system still has a bucket/router execution brain. It can recognize that a user wants places, but it cannot robustly plan retrieval and ranking for open-ended natural-language place concepts.

Adding "brewery" to a keyword list is not a fix. It is another patch on the wrong abstraction.

## 2. Non-negotiable architecture invariants

These stay true across all phases.

1. No fake addable cards.
2. Every addable card must have a stable Google place id.
3. Every addable card must have OPERATIONAL business status or equivalent verified open/active status from Google.
4. Every addable card must have a resolvable Google Maps URI.
5. Tavily, Brave, Serper, editorial blogs, Yelp, and Foursquare cannot mint addable cards.
6. Editorial/web sources may enrich only already verified Google entities.
7. Reasons must be grounded in available evidence.
8. Do not invent waterfront views, ambiance, awards, Michelin mentions, distance, neighborhoods, prices, booking details, or opening hours.
9. Weak evidence must be stated honestly and briefly.
10. No slow serial per-card LLM reasoning.
11. Do not block card return on optional enrichment.
12. Follow-up reuse must not mutate card identity or make unsupported new claims.
13. Backend-first. Preserve the existing frontend card shape unless payload compatibility requires additive fields.
14. No SQL in Phase 1 unless a production blocker proves it is necessary.
15. Any SQL must be additive, rollback-safe, and explicitly explained.
16. Observability failures must never block user response.

## 3. Revised target architecture

The architecture target remains Semantic Place Intelligence, but with a stricter implementation order.

```text
User prompt + trip context + prior pool
  -> Turn Interpreter
  -> Experience Frame Extractor
  -> Retrieval Planner
  -> Provider Query Fanout
  -> Verified Place Entity Layer
  -> Semantic Ranker
  -> Minimal Evidence Bundle
  -> Reason Builder
  -> Trust Gate
  -> Result Pool Writer
  -> Typed Response
  -> Structured Observability
```

### What changes in v2

The first semantic PR must include enough of this flow to return cards:

```text
Frame -> Plan -> Google Text Search fanout -> Verify entities -> Rank -> Deterministic safe reason -> Existing card contract
```

The first semantic PR does not need full Tavily enrichment or full batched LLM reasons. It must produce verified addable cards fast and correctly.

### Module summary

| Module | Phase | Required in first semantic PR? | Notes |
|---|---:|---:|---|
| Turn Interpreter | Existing + Phase 3 | Partial | Existing turn modes are reused. Only new_search path is required in first semantic PR. |
| Experience Frame Extractor | Phase 1 | Yes | Open vocabulary. No closed subtype enum. Deterministic fallback required. |
| Retrieval Planner | Phase 1 | Yes | Generates provider-friendly query variants from the frame. |
| Provider Query Fanout | Phase 1 | Yes | Parallel Google Text Search only. Hard cap. Deadlines. |
| Verified Place Entity Layer | Phase 1 | Yes | Google place id + OPERATIONAL + maps URI gate. |
| Semantic Ranker | Phase 1 | Yes | Deterministic feature-based score. No category hard gate. |
| Minimal Evidence Bundle | Phase 1 | Yes | Structured fields + computed geo only. No dependency on Google AI summaries. |
| Deterministic Safe Reason Builder | Phase 1 | Yes | Honest, ask-anchored, no unsupported vibe/view/award claims. |
| Batched LLM Reasoning | Phase 2 | No | Add once retrieval reliability is proven. |
| Reason Validators | Phase 2 | Partial in Phase 1 | Phase 1 has basic banned-claim validation. Phase 2 adds full citation validator. |
| Tavily/editorial enrichment | Phase 3 | No | Evidence only, best-effort, non-blocking. |
| Follow-up Engine v2 | Phase 4 or accelerated | No | Can be accelerated after semantic retrieval if wife testing depends on it. |
| Supabase-backed pool | Phase 4+ | No | In-memory pool is acceptable for Railway single-replica v1. |

## 4. Provider reality and assumption guardrails

This section exists because provider assumptions can silently break the architecture.

### Google Places is canonical, but field availability is not uniform

Implementation must validate current Google Places field names, field-mask behavior, SKU tiers, and policy requirements before coding a field-dependent feature.

The first semantic PR must not rely on review summaries, neighborhood summaries, area summaries, AI-generated place summaries, editorial summaries, or review text being available.

### Phase 1 allowed Google fields

Use a minimal field set that supports verified cards and basic ranking:

- place id
- display name
- formatted address
- location coordinates
- business status
- Google Maps URI
- primary type / types
- rating
- user rating count
- price level if already available cheaply

Phase 1 can compute:

- name-token subtype fit
- Google type overlap as weak evidence
- distance to destination/hotel/water anchors where coordinates are known
- popularity as a weak signal
- diversity and dedup

### Phase 1 must not depend on

- reviewSummary
- neighborhoodSummary / areaSummary
- generativeSummary
- editorialSummary
- raw reviews
- servesBeer / servesWine / outdoorSeating / reservable / menu links unless the current API/SKU policy is confirmed
- Tavily/editorial evidence

Those are Phase 2/3 enrichment, not Phase 1 card-return dependencies.

### Retrieval query strategy

Do not hand the provider only the raw user sentence and hope it understands everything. The planner should generate short provider-friendly queries.

For "best breweries along the waterfront" in Chicago:

```json
[
  "breweries Chicago waterfront",
  "brewery taprooms Chicago Riverwalk",
  "lakefront breweries Chicago"
]
```

For "romantic tapas but not too loud" in Chicago:

```json
[
  "romantic tapas Chicago",
  "Spanish small plates quiet Chicago",
  "intimate tapas restaurant Chicago"
]
```

For "nice sushi restaurants with a waterfront view":

```json
[
  "sushi waterfront view Chicago",
  "sushi near Riverwalk Chicago",
  "upscale sushi lakefront Chicago"
]
```

The literal ask is useful, but provider-friendly variants are required.

### Provider call caps

First semantic PR:

- Google Text Search: maximum 3 calls, hard cap 4.
- Place Details: optional and only if existing client already supports cheap fields; otherwise defer.
- Tavily/editorial: 0 calls.
- LLM frame extraction: 1 call with timeout and deterministic fallback.
- LLM reasoning: 0 calls in the first semantic retrieval PR.

Reasoning PR:

- Add 1 batched LLM call for all final cards.
- No per-card loops.

## 5. ExperienceFrame v2

The frame is the system's semantic representation of the ask. It must be open vocabulary.

### Core schema

```json
{
  "literal_ask": "best breweries along the waterfront",
  "normalized_ask": "best breweries along the waterfront in Chicago",
  "destination": {"city": "Chicago", "country": "US", "lat": 41.8781, "lng": -87.6298},
  "answer_mode": "place_recommendations",
  "follow_up_mode": "new_search",
  "subtype_concepts": [
    {"label": "brewery", "confidence": 0.96},
    {"label": "taproom", "confidence": 0.64}
  ],
  "place_kind_hints": ["bar", "food_and_drink", "establishment"],
  "must_have": [
    {"label": "near_water", "kind": "geo", "confidence": 0.9, "verifiability": "computable"}
  ],
  "soft_preferences": [
    {"label": "best_quality", "confidence": 0.8}
  ],
  "negative_constraints": [],
  "vibe": [],
  "occasion": null,
  "geography_hints": {
    "anchor": "destination_water_axis",
    "named_places": ["waterfront", "riverwalk", "lakefront"],
    "max_distance_km": 3.0
  },
  "temporal_constraints": {},
  "value_signals": {"luxury_for_less": false, "splurge": false, "budget": null},
  "ambiguity_flags": ["geo_ambiguity_river_vs_lake"],
  "confidence": 0.88,
  "needs_provider_call": true,
  "can_answer_from_prior_pool": false
}
```

### Open-vocabulary rule

`subtype_concepts.label` is not an enum. It can be brewery, tapas, omakase, listening bar, izakaya, ramen, natural wine, mezcal bar, supper club, rooftop, art museum, neighborhood bakery, or a concept we have never seen.

The downstream system must not require a code change for a new label.

### Deterministic fallback

If the LLM times out or returns invalid JSON, use a fallback frame:

- subtype_concepts from normalized noun phrases in the prompt
- place_kind_hints from broad lexical cues only
- geography_hints from known terms such as hotel, downtown, waterfront, river, lake, beach
- negative_constraints from explicit words such as not, avoid, no, quiet, loud
- confidence low enough to trigger broader query fanout

Fallback must attempt provider search. It must not return text-only just because frame extraction failed.

## 6. Retrieval Planner v2

The Retrieval Planner converts the frame into provider calls.

### Rules

1. Always produce at least one provider query for a new place search.
2. Prefer short provider-friendly query variants over long poetic sentences.
3. Preserve the core subtype concept in every query variant unless the query is an explicit broad fallback.
4. Geo constraints become query terms and optional geo bias, not hard filters unless the user explicitly says "within X minutes" or "near hotel."
5. Must-have constraints that are hard to verify, such as "waterfront view," should guide retrieval but not force hallucinated claims.
6. Maximum 3 query variants by default.
7. Cache each query variant by canonical query + destination + geo bias.

### Example RetrievalPlan

```json
{
  "mode": "fanout_fetch",
  "provider_queries": [
    {"id": "q1", "engine": "google_text_search", "query_text": "breweries Chicago waterfront", "max_results": 12, "deadline_ms": 900},
    {"id": "q2", "engine": "google_text_search", "query_text": "brewery taprooms Chicago Riverwalk", "max_results": 10, "deadline_ms": 900},
    {"id": "q3", "engine": "google_text_search", "query_text": "lakefront breweries Chicago", "max_results": 10, "deadline_ms": 900}
  ],
  "top_n_cap": 5,
  "hard_timeout_ms": 4000,
  "planner_version": "semantic_retrieval_v1"
}
```

## 7. Verified Place Entity Layer v2

This is the trust spine. It converts raw Google provider results into addable entities.

### Required PlaceEntity fields

```json
{
  "google_place_id": "...",
  "name": "...",
  "formatted_address": "...",
  "coords": {"lat": 0.0, "lng": 0.0},
  "business_status": "OPERATIONAL",
  "google_maps_uri": "...",
  "place_types": ["bar", "food", "establishment"],
  "primary_type": "bar",
  "rating": 4.5,
  "user_rating_count": 900,
  "price_level": null,
  "identity_keys": ["pid:...", "gmaps:...", "name_addr:..."]
}
```

### Hard reject if

- missing Google place id
- business status is missing or not OPERATIONAL when the provider returns this field
- missing Google Maps URI
- duplicate identity key
- name/address match is too weak to trust
- provider result is an editorial/source-only entity

### Do not reject only because

- Google types are broad
- place type is bar instead of restaurant
- subtype is not in a local enum
- rating is lower than another candidate
- evidence for a soft vibe is weak

Those are ranking features, not card-minting gates.

## 8. Semantic Ranker v2

The ranker is deterministic, explainable, and not a bucket router.

### First semantic PR score formula

```text
score = 0.34 * subtype_fit
      + 0.22 * geo_fit
      + 0.12 * quality_signal
      + 0.10 * evidence_strength
      + 0.08 * diversity_signal
      + 0.06 * popularity_signal
      + 0.04 * trip_context_fit
      + 0.04 * value_fit
      - penalties
```

### Feature definitions

- `subtype_fit`: open-vocabulary match using query terms, place name, Google types, and broad provider query source. It is not an enum lookup.
- `geo_fit`: distance to anchor or named geographic feature when computable. For waterfront, use destination-specific water anchors only when available; otherwise use soft query evidence and mark uncertainty.
- `quality_signal`: rating and review count, Bayesian-smoothed. It cannot overpower subtype fit.
- `evidence_strength`: how many reliable structured facts support the candidate.
- `diversity_signal`: prevents five near-duplicates or the same chain/neighborhood cluster.
- `popularity_signal`: deliberately small. Popular but wrong must lose.
- `trip_context_fit`: existing itinerary and hotel proximity when available.
- `value_fit`: only active when the frame asks for value/luxury-for-less.

### Hard constraints vs soft constraints

Hard constraints:

- verified entity
- operational status
- maps URI
- explicit user constraint such as "within 10 minutes of hotel" if hotel coordinates are known

Soft constraints:

- romantic
- quiet
- upscale
- not touristy
- waterfront view when not directly verifiable
- best
- luxury for less

Soft constraints influence rank and reason honesty; they do not fabricate facts.

### Regression examples

For "best breweries along the waterfront":

- Brewery/taproom beats generic high-rated bar.
- Brewery near Riverwalk/lakefront beats brewery far from water.
- Generic restaurant near water loses to brewery farther away, unless no breweries are verified.
- Cards may honestly say "near the water axis, not verified waterfront view."

For "romantic tapas but not too loud":

- Tapas/small-plates restaurant beats cocktail bar.
- Quiet/romantic evidence boosts rank only if evidence exists.
- If quiet evidence is absent, reasons should say "best tapas fit; verify volume on a weekend night" rather than invent quietness.

## 9. Minimal Evidence Bundle v2

Phase 1 evidence is intentionally modest.

### Phase 1 EvidenceBundle

```json
{
  "place_entity_id": "pid:...",
  "items": [
    {"id": "ev_structured", "kind": "structured", "source": "google_text_search", "fields": ["types", "rating", "user_rating_count"], "confidence": 0.9},
    {"id": "ev_name", "kind": "name_match", "source": "computed", "snippet": "name contains brewery/taproom", "confidence": 0.8},
    {"id": "ev_geo", "kind": "geographic", "source": "computed", "data": {"distance_to_anchor_km": 1.2}, "confidence": 1.0},
    {"id": "ev_uncertainty", "kind": "uncertainty", "source": "computed", "data": {"claim": "waterfront_view", "verified": false}, "confidence": 1.0}
  ],
  "evidence_strength": "mixed",
  "weak_constraints": ["waterfront_view"],
  "strong_constraints": ["verified_place", "brewery_name_or_query_fit"]
}
```

### Phase 2 EvidenceBundle

Add optional evidence only after Phase 1 card return works:

- Place Details summaries if available and policy-compliant
- current opening hours if the user asks about timing
- website/menu/reservation fields if cost and policy are accepted
- Tavily/editorial snippet only after entity verification
- source URL and citation IDs for reason grounding

## 10. Reasoning v2

Reasoning is important, but it must be staged correctly.

### Phase 1 deterministic safe reasons

The first semantic retrieval PR can ship deterministic safe reasons if they are honest, ask-anchored, and non-generic.

Examples:

- "Verified brewery/taproom result for your waterfront ask; it ranks highest because it matches the brewery concept and is closest to the Chicago water-axis among verified candidates. Verify exact water views before booking."
- "This is a stronger tapas/small-plates match than the cocktail-bar results, but I do not have enough evidence yet to verify the room is quiet on weekends."
- "Sushi-first and near the water search area; I can verify the place, but not the interior view, so treat the view as a booking-check item."

These are not final concierge-grade reasons, but they are safer than text-only failure and do not compromise trust.

### Phase 2 batched LLM reasons

Add a single batched Sonnet call for all final cards.

Requirements:

- one call per turn, never one call per card
- strict JSON output
- each reason references ask anchors
- each verifiable claim cites an evidence item
- validator rejects unsupported view, award, Michelin, opening-hour, price, neighborhood, or vibe claims
- deterministic fallback if timeout, malformed output, or validator failure

### Banned reason patterns

Reject or rewrite:

- "great choice" with no specific evidence
- "perfect spot" with no specific evidence
- "hidden gem" with no local/evidence support
- "highly rated" as the only reason
- "waterfront view" unless explicitly verified
- "romantic" unless supported by evidence or framed as uncertain
- "not touristy" unless supported by chain/popularity/editorial/review evidence

## 11. Revised rollout plan

### Phase 0 - Observability tolerance

Purpose: remove noisy logging failures and protect analytics from schema drift.

Scope:

- schema-tolerant concierge_request_log writer
- catch missing-column errors, drop field, retry without blocking response
- log one warning per missing column per process
- startup schema check only if supported by existing infrastructure; best-effort, never blocking
- no frontend
- no new SQL in code

Severity: Level 1.
Model: Codex or Sonnet.
Chat: new focused chat.

### Phase 1 - Semantic Retrieval v1 vertical slice

Purpose: first real intelligence slice that can pass brewery/tapas/sushi-with-view card-return tests.

Scope:

- ExperienceFrame extractor with deterministic fallback
- RetrievalPlanner producing provider-friendly query variants
- parallel Google Text Search fanout
- VerifiedPlaceEntity layer
- SemanticRanker v1
- MinimalEvidenceBundle v1
- deterministic safe reason builder
- TrustGate v1 for verified card invariants
- structured logs for frame, plan, provider counts, rejection counts, rank scores, final_card_count
- feature flag: CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=false by default
- no Tavily
- no full LLM reasoner
- no frontend changes
- no SQL

Severity: Level 2.
Model: Claude Sonnet.
Chat: new chat.

Acceptance:

- "best breweries" returns at least 3 verified addable cards in Chicago under flag.
- "best breweries along the waterfront" returns verified brewery/taproom cards, ranked by subtype + geo fit, with honest view/waterfront wording.
- "romantic tapas but not too loud" returns tapas/small-plates first, not cocktail bars first.
- "nice sushi restaurants with a waterfront view" returns sushi-first cards and does not invent a verified view.
- No addable card lacks Google place id, OPERATIONAL status, or maps URI.
- New pipeline is fully disabled when the flag is off.
- Existing frontend card contract still works.

### Phase 2 - Batched reasoning and validators

Purpose: upgrade from deterministic safe reasons to concierge-grade evidence-grounded reasoning.

Scope:

- batched LLM reasoner
- reason output schema
- evidence citation IDs
- citation validator
- banned phrase validator
- geographic/view claim validator
- award/Michelin claim validator
- deterministic fallback on timeout or validation failure
- prompt reviewed by Opus before merge

Severity: Level 2.
Model: Sonnet implementation + Opus prompt review.
Chat: follow-up only if Phase 1 chat remains compact; otherwise new chat.

### Phase 3 - Evidence enrichment

Purpose: improve reason evidence without slowing card return.

Scope:

- optional Place Details enrichment after initial rank
- current opening hours only when temporal ask requires it
- Google AI/summary fields only after field/policy/SKU validation
- Tavily/editorial enrichment only for already verified entities
- source/citation handling
- best-effort deadlines

Severity: Level 2.
Model: Sonnet.
Chat: new chat.

### Phase 4 - Follow-up Engine v2

Purpose: make the concierge conversational, not stateless search.

Scope:

- top 3
- best one
- more options
- compare
- closer to hotel
- less touristy
- more romantic
- cheaper
- not a chain
- what would you pick
- preserve card identity across follow-ups
- pool-first behavior with provider refill only when pool is insufficient

Severity: Level 2.
Model: Sonnet.
Chat: new chat.

Acceleration note: If wife-testing surfaces follow-up pain before Phase 3 enrichment, Phase 4 can move ahead of Phase 3. Follow-up correctness is core UX, not polish.

### Phase 5 - Persistence and personalization

Purpose: make the concierge durable across worker restarts and trips.

Scope:

- Supabase-backed trip pool
- per-trip soft preferences
- per-user preference memory
- selected/rejected card feedback loop
- additive SQL with RLS

Severity: Level 3 if bundled; Level 2 if split.
Model: Opus for spec, Sonnet for implementation.

## 12. Revised PR catalog

### PR-1 - Logging schema tolerance

Title: `concierge: schema-tolerant request log writes`

Scope:

- `backend/app/concierge/logging.py`
- tests for missing-column retry
- optional best-effort startup schema-drift warning if existing infrastructure supports it
- `docs/ai/HANDOFF.md`
- `progress_log.md`

Do not require direct information_schema access if it is not already available.

### PR-2 - Semantic Retrieval v1 vertical slice

Title: `concierge: semantic retrieval v1 verified-card pipeline`

Scope:

- new `backend/app/concierge/frame_extractor.py`
- new `backend/app/concierge/retrieval_planner.py`
- new `backend/app/concierge/provider_executor.py`
- new `backend/app/concierge/place_entity_layer.py`
- new `backend/app/concierge/ranker.py`
- new `backend/app/concierge/safe_reason_builder.py`
- modified route/service gate behind feature flag
- modified contracts only if additive optional debug fields are needed
- tests for frame, planner, provider fanout, entity verification, ranker, trust gate, brewery/tapas regressions

Not included:

- Tavily
- full LLM reasoner
- frontend changes
- SQL
- personalization

### PR-3 - Batched reasoning and trust validators

Title: `concierge: batched grounded reasons and validators`

Scope:

- `reasoning_engine.py`
- `reason_validators.py`
- tests for unsupported claims, banned phrasing, malformed JSON, timeout fallback
- Opus prompt review before merge

### PR-4 - Evidence enrichment

Title: `concierge: evidence enrichment after verified entity ranking`

Scope:

- optional Place Details fields after provider assumptions validated
- optional Tavily/editorial source snippets for verified entities only
- no blocking on enrichment

### PR-5 - Follow-up Engine v2

Title: `concierge: conversational follow-up engine v2`

Scope:

- prior pool operations
- identity preservation
- no provider call for top 3 / best one / closer / cheaper when pool is sufficient
- bounded refill for more options

## 13. Test strategy v2

### Required Phase 1 tests

Frame extraction fixtures:

- best breweries
- best breweries along the waterfront
- romantic tapas but not too loud
- nice sushi restaurants with a waterfront view
- upscale seafood but not touristy
- cocktail bars with a view
- best brunch near our hotel
- somewhere fun after dinner, not too loud, good for one drink

Retrieval planner tests:

- generates 2-3 provider-friendly queries for brewery/waterfront
- preserves subtype in each query variant
- caps query count
- falls back to literal query on low confidence

Provider executor tests:

- runs fanout in parallel
- handles one provider timeout while using other results
- handles all-provider timeout with honest no-card response
- does not call Tavily in Phase 1

Entity layer tests:

- rejects missing place id
- rejects non-operational status
- rejects missing maps URI
- dedupes by Google place id, maps URI, and normalized name/address

Ranker tests:

- brewery beats generic bar for brewery ask
- tapas beats cocktail bar for tapas ask
- sushi beats generic waterfront restaurant for sushi-with-view ask
- closer candidate wins when geo is explicit
- popularity cannot overpower subtype fit

Safe reason tests:

- reason references the ask anchor
- reason does not invent view
- reason does not invent quiet/romantic evidence
- reason uses verify-when-booking wrapper only for requested weak attributes

Integration regression tests:

- Chicago + "best breweries" returns verified cards under flag
- Chicago + "best breweries along the waterfront" returns verified cards under flag
- Chicago + "romantic tapas but not too loud" does not return cocktail bars first
- flag off preserves existing behavior

### Required Phase 2 tests

- batched reason call covers all cards
- no per-card LLM loops
- unsupported waterfront view rejected
- unsupported Michelin/award rejected
- banned generic phrase rejected
- malformed JSON falls back
- reason timeout falls back
- citations refer to known evidence IDs

## 14. Observability v2

Every semantic turn should emit one structured log line:

```json
{
  "log_key": "concierge.semantic_turn",
  "request_id": "...",
  "trip_id": "...",
  "pipeline_version": "semantic_retrieval_v1",
  "feature_flags": {"semantic_retrieval_v1": true},
  "turn_mode": "new_search",
  "frame": {
    "subtype_concepts": ["brewery"],
    "must_have": ["near_water"],
    "negative_constraints": [],
    "ambiguity_flags": ["geo_ambiguity_river_vs_lake"],
    "confidence": 0.88
  },
  "retrieval_plan": {
    "query_count": 3,
    "queries": ["breweries Chicago waterfront", "brewery taprooms Chicago Riverwalk", "lakefront breweries Chicago"]
  },
  "provider_counts": {
    "raw_candidates": 28,
    "deduped_candidates": 17,
    "verified_entities": 10,
    "final_cards": 5
  },
  "rejection_counts": {
    "missing_place_id": 0,
    "not_operational": 1,
    "missing_maps_uri": 0,
    "duplicate": 11
  },
  "rank_top": [
    {"name": "...", "score": 0.81, "subtype_fit": 0.94, "geo_fit": 0.62}
  ],
  "latency_ms": {
    "frame": 900,
    "provider_fanout": 1000,
    "entity_layer": 30,
    "ranker": 20,
    "reason": 10,
    "total": 2100
  },
  "reason_source": "deterministic_safe_v1"
}
```

Logging rules:

- log enough to debug zero-card failures in one pass
- analytics write failure must not block response
- schema drift warning should be deduped per column per process
- use exact pipeline_version values for rollout comparisons

## 15. Rollback plan

Every semantic behavior is behind a feature flag.

### Flags

```text
CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=false
CONCIERGE_BATCHED_REASONING_V1_ENABLED=false
CONCIERGE_EVIDENCE_ENRICHMENT_V1_ENABLED=false
CONCIERGE_FOLLOWUP_V2_ENABLED=false
```

### Rollback behavior

- If Phase 1 has a production issue, disable `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED`.
- If reasons hallucinate, disable `CONCIERGE_BATCHED_REASONING_V1_ENABLED` while keeping verified card retrieval active if safe.
- If enrichment slows latency, disable `CONCIERGE_EVIDENCE_ENRICHMENT_V1_ENABLED`.
- If follow-up logic misroutes, disable `CONCIERGE_FOLLOWUP_V2_ENABLED` and preserve current follow-up behavior.

## 16. First implementation prompt - PR-1

Model: Codex or Claude Sonnet.
Chat strategy: new focused chat.
Usage estimate: Low to Medium.
Extra-cost risk: Low.
UI budget: None; backend/docs only.
Severity classification: Level 1.
Why not smaller: The logging writer must be changed at the root, not patched around individual log fields.

Copyable prompt:

```text
You are working in repo prashanthkrishnan91/claude_travelapp_pk91.

Task: PR-1 of AI Concierge Semantic Place Intelligence v2.

Severity classification: Level 1 - focused root-cause fix in observability/logging.

Execution principles: before coding, state assumptions and success criteria; keep changes simple and surgical; every changed line must trace to this task; fix the root cause, not a symptom; if the durable fix exceeds scope, stop and propose the split.

Goal:
Make concierge_request_log persistence schema-tolerant so missing live Supabase columns such as intent_classifier_version do not create noisy per-turn errors and never affect user responses.

Scope:
- backend/app/concierge/logging.py
- backend/tests focused on concierge observability/logging
- docs/ai/HANDOFF.md
- progress_log.md
- backend/app/main.py ONLY if the repo already has a safe existing way to perform startup schema introspection without new SQL/RPC/direct DB infrastructure.

Required behavior:
1. Catch PostgREST missing-column/schema-cache errors such as PGRST204 and PGRST116 during concierge_request_log persistence.
2. Extract or infer the offending missing column when possible.
3. Drop the offending field from the payload and retry the insert.
4. If the retry hits another missing column, drop that field too and retry until either success or a small retry cap is reached.
5. Emit one warning per process per table+column pair using log key concierge.logging.schema_drift.
6. Unexpected non-schema errors should use the existing persist_failed style log key and must not raise to the caller.
7. Logging persistence must never block the user response.
8. Startup schema drift check is optional/best-effort only. Do not invent new DB infrastructure for it. If existing infrastructure does not support it cleanly, document that runtime tolerance is the Phase 1 fix and leave startup check for a later SQL/RPC PR.

Do not:
- Touch AI Concierge retrieval, ranking, card assembly, frontend, providers, or trust gates.
- Add new SQL.
- Apply Supabase migration 004 from code.
- Add feature flags.
- Hide unexpected logging errors silently; log them without raising.

Tests:
- Missing intent_classifier_version column: writer retries without that field and succeeds.
- Two missing columns across retries: writer drops both and succeeds.
- Repeated calls with same missing column: warning emitted once per process per column.
- Unexpected exception: logged but not raised.
- If a startup check is implemented, test drift and no-drift cases with mocks.

Docs:
- Update docs/ai/HANDOFF.md with problem, fix, behavior matrix, files touched, Supabase SQL: No, and operational note that live Supabase still needs existing migration 004 applied.
- Append one progress_log.md entry.

Stop condition:
If the durable implementation requires broad app startup rewiring, new SQL/RPC, or direct DB infrastructure, stop and report a split plan instead of overbuilding.

Final response format:
Severity classification:
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL:
HANDOFF.md edited:
README.md edited:
Open a PR titled: concierge: schema-tolerant request log writes
Stop after opening the PR.
```

## 17. First intelligence implementation prompt - PR-2

Use this only after PR-1 is merged or intentionally skipped.

Model: Claude Sonnet.
Chat strategy: new chat.
Usage estimate: High.
Extra-cost risk: Medium.
UI budget: None; backend-only except additive contract fields if absolutely required.
Severity classification: Level 2.
Why not Codex/smaller: This is a multi-module backend plumbing change across interpretation, retrieval, verification, ranking, and response assembly. A surgical patch would recreate the bucket-router failure.
Budget gate: Stop after opening one PR. Do not continue into batched reasoning, Tavily enrichment, frontend UI, SQL, or follow-up engine v2.

Copyable prompt:

```text
You are working in repo prashanthkrishnan91/claude_travelapp_pk91.

Task: PR-2 of AI Concierge Semantic Place Intelligence v2 - Semantic Retrieval v1 verified-card pipeline.

Severity classification: Level 2 - full retrieval plumbing fix behind a feature flag.

Execution principles: before coding, state assumptions and success criteria; keep changes simple and surgical; every changed line must trace to this task; fix the root cause, not a symptom; if the durable fix exceeds scope, stop and propose the split.

Read first:
- CLAUDE.md
- docs/ai/HANDOFF.md
- docs/ai/EXECUTION_PRINCIPLES.md
- docs/ai/ISSUE_SEVERITY_ROUTING.md
- existing AI Concierge route/service files
- artifacts/ai_concierge_semantic_place_intelligence.pdf, but follow the v2 revision if present

Problem:
The current AI Concierge can classify natural-language place asks correctly but still return text-only/no cards because retrieval and ranking still depend on bucket/category assumptions. Recent production failure: Chicago, "best breweries along the waterfront" and follow-up "best breweries" produced no addable cards even though the classifier returned place_recommendations.

Goal:
Build the first real Semantic Retrieval v1 vertical slice behind a feature flag. The new path must drive retrieval and ranking, not just log a frame. It must return verified addable cards for open-vocabulary asks without adding more category buckets.

Feature flag:
Add CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED, default false.

Required pipeline when flag is ON for new_search place-recommendation asks:
1. ExperienceFrame extractor
   - LLM JSON extraction if existing LLM infra supports it safely.
   - Deterministic fallback required on timeout/invalid JSON.
   - subtype_concepts must be open-vocabulary strings, not a closed enum.
   - Extract subtype concepts, place_kind_hints, must_have, soft_preferences, negative_constraints, geography_hints, ambiguity_flags, confidence.
2. RetrievalPlanner
   - Generate 1-3 provider-friendly Google Text Search queries from the frame.
   - Always include the core subtype concept in each query where possible.
   - Examples:
     - "best breweries along the waterfront" in Chicago -> breweries Chicago waterfront; brewery taprooms Chicago Riverwalk; lakefront breweries Chicago
     - "romantic tapas but not too loud" -> romantic tapas Chicago; Spanish small plates quiet Chicago; intimate tapas restaurant Chicago
   - Cap Google Text Search calls at 3 by default, hard cap 4.
3. Provider fanout
   - Use existing Google Places client where possible.
   - Run query fanout in parallel with per-call deadlines.
   - No Tavily/editorial calls in this PR.
   - No Place Details dependency unless current code already returns needed cheap fields.
4. Verified Place Entity Layer
   - Canonicalize/dedupe provider results.
   - Hard reject missing Google place id, non-OPERATIONAL status, or missing Google Maps URI.
   - Preserve existing identity-key logic where possible.
   - Do not reject just because Google types are broad or because subtype is not in a local enum.
5. SemanticRanker v1
   - Deterministic score with subtype_fit dominant and popularity small.
   - No category_score < 0.2 hard gate.
   - Features: subtype_fit, geo_fit, quality_signal, evidence_strength, diversity, popularity, trip_context_fit, value_fit, penalties.
6. MinimalEvidenceBundle v1
   - Structured Google fields + computed geography + uncertainty flags.
   - Do not rely on reviewSummary, neighborhoodSummary, generative summaries, Tavily, Yelp, Foursquare, or raw reviews.
7. SafeReasonBuilder v1
   - Deterministic, honest, ask-anchored reasons.
   - No unsupported views, romance, quietness, awards, Michelin, price, opening hours, or neighborhood claims.
   - Use "verify when booking" only for explicitly requested weak attributes, such as waterfront view or quietness.
8. TrustGate v1
   - Final check that every addable card has Google place id, OPERATIONAL status, and Google Maps URI.
   - Drop invalid cards rather than weakening gates.
9. Structured observability
   - Log frame, retrieval plan, provider counts, rejection counts, rank scores, final_card_count, reason_source, latency_by_stage, pipeline_version=semantic_retrieval_v1.

Do not:
- Add brewery/tapas/sushi to another category map as the core fix.
- Use Tavily/editorial sources to mint cards.
- Add full batched LLM reasoning. That is PR-3.
- Add frontend UI changes.
- Add SQL.
- Change existing behavior when the flag is off.
- Weaken Google verification.
- Depend on Google AI/summary fields for Phase 1 success.

Acceptance tests:
- Flag OFF: existing behavior preserved.
- Flag ON, Chicago + "best breweries" returns at least 3 verified addable Google cards.
- Flag ON, Chicago + "best breweries along the waterfront" returns verified brewery/taproom cards, ranked by subtype + geo fit, and does not invent a waterfront view.
- Flag ON, Chicago + "romantic tapas but not too loud" returns tapas/small-plates first, not cocktail bars first.
- Flag ON, Chicago + "nice sushi restaurants with a waterfront view" returns sushi-first cards and labels/phrases view evidence honestly.
- Fake/no-place-id candidates are rejected.
- Non-operational candidates are rejected.
- Missing maps URI candidates are rejected.
- Provider partial timeout still returns cards from successful queries.
- All-provider timeout returns honest no-card/provider-hiccup response, not fake cards.
- No Tavily call happens in this PR.

Files likely touched:
- backend/app/core/config.py
- backend/app/services/concierge.py or backend/app/routes/ai.py, depending on current routing seam
- new backend/app/concierge/frame_extractor.py
- new backend/app/concierge/retrieval_planner.py
- new backend/app/concierge/provider_executor.py
- new backend/app/concierge/place_entity_layer.py
- new backend/app/concierge/ranker.py
- new backend/app/concierge/safe_reason_builder.py
- tests under backend/tests/
- docs/ai/HANDOFF.md
- progress_log.md

Stop conditions:
- If you need frontend changes, stop and explain why.
- If you need SQL, stop and explain why.
- If existing Google client cannot expose required verified fields, stop with a narrow provider-client split plan.
- If the vertical slice cannot be completed safely in one PR, stop after Frame + Planner + Provider + Entity + Ranker skeleton with tests, but do not ship an observation-only path that claims to fix the product issue.

Final response format:
Severity classification:
Root cause/plan:
Files changed:
Tests:
Risks:
Supabase SQL:
HANDOFF.md edited:
README.md edited:
Open a PR titled: concierge: semantic retrieval v1 verified-card pipeline
Stop after opening the PR. Do not proceed to batched LLM reasoning or evidence enrichment.
```

## 18. Merge-gate checklist for PR-2

Use Codex for cheap merge-gate audit after Sonnet opens PR-2.

Audit focus:

- flag off preserves existing behavior
- flag on actually drives retrieval, not observation-only logging
- no new bucket map is acting as the brain
- Google verification gates remain hard
- Tavily/editorial cannot mint cards
- ranker uses subtype as dominant feature and popularity as small feature
- no unsupported reason claims
- no SQL or frontend drift
- tests include the brewery and tapas regressions
- HANDOFF.md and progress_log.md updated

## 19. What success looks like

Short-term success:

- The wife asks "best breweries along the waterfront" and receives verified addable cards, not text-only advice.
- She asks "best breweries" and receives verified brewery/taproom cards, not generic restaurants or no cards.
- She asks "romantic tapas but not too loud" and sees tapas/small plates first, not cocktail bars.
- Reasons are not final-perfect yet, but they are honest and ask-specific.
- Logs explain every zero-card outcome without needing a multi-hour investigation.

Medium-term success:

- Batched reasoning makes the system feel like a real concierge.
- Follow-ups use the pool and return in under a second when possible.
- Optional enrichment improves reasons without slowing cards.
- The system can accept long-tail human asks without code changes.

Long-term success:

- AI Concierge feels like the app's flagship product: dynamic, fast, verified, opinionated, and trustworthy.
- It is better than generic travel chat because every answer materializes as addable, verified itinerary cards.

## 20. Non-goals for this plan

Do not include in the first intelligence PR:

- visual redesign
- animations or design system work
- new itinerary UI
- personalization tables
- Supabase-backed pool
- dashboard/alerting infrastructure
- Tavily editorial synthesis
- Yelp/Foursquare integration
- vector index
- compare UI
- day-plan rewrite

These are valuable later. They are distractions before verified semantic card return works.

## 21. Final recommendation

Proceed in this order:

1. PR-1: logging schema tolerance if you want clean observability before semantic work.
2. PR-2: Semantic Retrieval v1 verified-card vertical slice behind flag.
3. Codex cheap merge gate for PR-2.
4. PR-3: batched grounded reasons and validators.
5. PR-4 or PR-5 depending on wife-testing pain:
   - If card reasons are weak, do evidence enrichment next.
   - If chat follow-ups feel broken, do Follow-up Engine v2 next.

Do not return to bucket patching. Do not let implementation agents turn this into a category list. Do not accept observation-only scaffolding as product progress.
