# Progress Log

## 2026-05-05 — Venue-Head-Over-Modifier Contract (semantic retrieval v1 hardening)

**Branch**: `claude/fix-venue-head-modifiers-V1fEK`

**What was built**: A general venue-head-over-modifier contract for semantic place retrieval. "best waterfront breweries" no longer returns Lakefront Park / Chicago Riverwalk / The Lakefront Restaurant; brewery-like cards dominate, and when Google can't verify enough on-concept candidates the system returns fewer/no cards instead of filling with modifier-only wrong-category matches.

**Root cause**: The ranker awarded `query_match=0.6` to any entity returned by a venue-targeted query, lifting wrong-category entities past the `_WRONG_CATEGORY_SUBTYPE_FIT_MAX=0.30` threshold and bypassing the wrong-category penalty.

**Files changed**:
- `backend/app/concierge/ranker.py` — `query_match` weight 0.6 → 0.20; `_WRONG_CATEGORY_PENALTY` 0.20 → 0.30; new `_ON_CONCEPT_SUBTYPE_FIT_MIN=0.45`; post-rank venue-head filter (drop off-concept when ≥ 3 on-concept; return empty when recognized concept and zero on-concept); new `rank_entities_with_stats()` for observability.
- `backend/app/concierge/retrieval_planner.py` — always emit one pure `{venue} {destination}` recall query alongside the geo-targeted variants.
- `backend/app/concierge/semantic_retrieval.py` — turn log now reports `off_concept_dropped`, `on_concept_count`, `venue_head_recognized`.
- `backend/tests/test_semantic_retrieval_v1.py` — 15 new tests (planner head-anchored, ranker discipline, drop filter, regression, reason safety).

**Tests**: 120 tests in `test_semantic_retrieval_v1.py` — all passing. Broader concierge suite (202 tests across `test_concierge*.py`, excluding the env-broken `test_concierge_router_v2.py` import) — all passing.

**Production validation queries to rerun** after deploy with `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
1. best breweries
2. best waterfront breweries
3. breweries near the river
4. taprooms with a view
5. izakayas

**Not started**: PR-3 batched grounded reasoning. Visual design work. Tavily / editorial / Yelp / Foursquare. SQL or frontend changes.

**Supabase SQL**: No.

---

## 2026-05-05 — Semantic Retrieval v1 (PR-2 of AI Concierge Semantic Place Intelligence v2)

**Branch**: `claude/semantic-retrieval-v1-ZfnnV`

**What was built**: Full Semantic Retrieval v1 vertical slice behind a feature flag. The pipeline returns verified addable cards for open-vocabulary natural-language place asks without weakening trust gates.

**Root cause addressed**: Chicago + "best breweries along the waterfront" returned text-only / no cards because the execution brain was a fixed category-bucket router that could not represent "brewery" as an open-vocabulary concept.

**New modules** (7 files, ~900 LOC):
- `frame_extractor.py` — deterministic open-vocabulary ExperienceFrame extraction
- `retrieval_planner.py` — generates 1–3 provider-friendly Google Text Search queries
- `provider_executor.py` — parallel fanout with per-call deadlines
- `place_entity_layer.py` — trust gates: place_id + OPERATIONAL + maps_uri; dedup by stable identity keys
- `ranker.py` — SemanticRanker v1 (subtype_fit 0.34 dominates, no hard category gate) + MinimalEvidenceBundle
- `safe_reason_builder.py` — deterministic honest reasons, no hallucinated facts
- `semantic_retrieval.py` — pipeline orchestrator + TrustGate + structured observability

**Tests**: 46 tests, all passing. Covers all pipeline stages including integration with mocked Google provider.

**Flag**: `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=false` (default). Rollback = set to false.

**Not done (explicit scope)**: LLM batched reasoning (PR-3), Tavily, SQL, frontend UI, Yelp/Foursquare, personalization, vector search.

- 2026-05-05: Fixed live semantic retrieval card display contract for AI Concierge drawer. Root cause: frontend `callConciergeSearch` consumed `/ai/concierge/search` typed response without normalizing snake_case fields (`response_type`, `retrieval_used`, `source_status`, etc.), so verified cards were dropped and UI rendered text-only. Added focused contract tests (backend router typed place payload preservation + empty-card honesty; frontend assertion that search path normalizes typed response before mapping). Production validation checklist: Izakayas; Izakayas on Fulton Street; best breweries; best waterfront breweries; breweries near the river; taprooms with a view. PR-3 batched grounded reasoning not started.
