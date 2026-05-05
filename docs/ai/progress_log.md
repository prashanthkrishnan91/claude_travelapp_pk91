# Progress Log

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
