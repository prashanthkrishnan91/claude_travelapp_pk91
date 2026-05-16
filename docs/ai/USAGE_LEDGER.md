# AI Usage Ledger

Committed, sanitized audit trail of Claude token/cost usage by PR, prompt, and delta.

## Purpose

A future auditor can pull this file from GitHub and understand token/cost burn by PR, prompt phase, and per-prompt delta without needing local raw snapshots. Raw `.ai/usage/*.json` files stay local and gitignored.

## Privacy rule

Never commit to this ledger:
- Raw `.ai/usage/*.json` snapshots or baseline files
- Prompts or conversation content
- Secrets, env values, or API keys
- Local Claude DB data (`~/.claude/`)

This file contains only sanitized session-level and delta summaries.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Sanitized ledger | `docs/ai/USAGE_LEDGER.md` | Yes | Auditable PR/prompt-level history |

PR usage notes in the PR body are not sufficient for workflow audits — they are too lossy once the PR is merged. This ledger is the durable audit source.

## Ledger columns

| Column | Description |
|---|---|
| Date | ISO date of the session (YYYY-MM-DD) |
| PR | PR number or `unknown` |
| Prompt ID | Human-readable prompt/patch ID: `initial`, `patch-1`, `patch-2`, `same-chat-pr-2`, etc. |
| Phase | `initial` / `follow-up` / `audit` / `merge-gate` / `backfill` / `unknown` |
| Linked PR | Original PR number if this is a follow-up, or `n/a` |
| Repo area | e.g. `workflow/docs`, `backend/concierge`, `frontend/trip` |
| Claude session | Session URL or `unknown` |
| Model | e.g. `claude-sonnet-4-6`, `claude-opus-4-7` |
| Chat strategy | `same-chat`, `new-chat`, or `unknown` |
| Source | `ccusage`, `statusline`, `manual`, or `unavailable` |
| Input tok | Session-level input tokens (cumulative) |
| Output tok | Session-level output tokens (cumulative) |
| Cache read | Session-level cache read tokens (cumulative) |
| Cache creation | Session-level cache creation tokens (cumulative) |
| Total tok | Session-level total tokens (cumulative) |
| Est. cost | Session-level estimated cost (cumulative) |
| Δ input | Per-prompt delta input tokens vs saved baseline |
| Δ output | Per-prompt delta output tokens vs saved baseline |
| Δ cache read | Per-prompt delta cache read tokens vs saved baseline |
| Δ cache creation | Per-prompt delta cache creation tokens vs saved baseline |
| Δ total | Per-prompt delta total tokens vs saved baseline |
| Δ cost | Per-prompt delta estimated cost vs saved baseline |
| Waste | `none` / `preventable-follow-up` / `necessary-follow-up` / `exploration` / `unknown` |
| Main drivers | What consumed tokens (e.g. broad discovery, many iterations) |
| Follow-up patches | Number of follow-up PRs required |
| Efficiency lesson | One-line lesson for future sessions |

## Ledger table

| Date | PR | Prompt ID | Phase | Linked PR | Repo area | Session | Model | Chat | Source | Input tok | Output tok | Cache read | Cache creation | Total tok | Est. cost | Δ input | Δ output | Δ cache read | Δ cache creation | Δ total | Δ cost | Waste | Main drivers | Follow-up patches | Efficiency lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | #000 | initial | initial | n/a | workflow/docs | unknown | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unknown | template row — replace | 0 | n/a |
| 2026-05-13 | stage3-exit-canonical-flight-seeding | initial | initial | n/a | backend/routes,services,tests | web-claude | claude-opus-4-7 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | unify /trips/create-with-search flight seeding with /explore/flights via canonical_flight_search helper; persist FlightItineraryOffer as Trip Ideas | 0 | one provider seam → fewer divergent flight pathways |
| 2026-05-14 | flight-offer-fingerprint-GbKID | initial | initial | n/a | backend/flights | web-claude | claude-opus-4-7 | same-chat | ccusage | 86 | 26669 | 4051596 | 141748 | 4220099 | $3.58 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | anchor reads, itinerary+trips edits, test additions | 0 | replace title-based dedupe for canonical Duffel offers with deterministic offer_fingerprint |
| 2026-05-14 | stage-3-stabilization-patch-1XAS7 | initial | initial | n/a | frontend/trips,explore,saved,ui + backend/concierge | web-claude | claude-opus-4-7 | same-chat | ccusage | 178 | 46015 | 13861965 | 201866 | 14110024 | $9.34 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | round-trip add → single canonical item; create-trip-from-saved IATA-resolution gate; default Explore Hotels allow_live_research=false (no Tavily) | 0 | one capability slice across three traceable scopes; reuse existing canonical fields instead of re-deriving |
| 2026-05-14 | vertical-search-architecture-gFI1g | initial | initial | n/a | backend/routes,services,models,tests + frontend/explore,api,tests | web-claude | claude-opus-4-7 | same-chat | ccusage | 162 | 71334 | 13989416 | 279277 | 14340189 | $10.52 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | remove allow_live_research flag; canonical /search/hotels + new /search/attractions shared by Explore and trip creation; Explore flows off AI Concierge | 0 | durable vertical-search architecture replaces a boolean-flag symptom patch |
| 2026-05-14 | vertical-search-architecture-gFI1g | follow-up | follow-up | n/a | backend/services/search.py,tests + docs | web-claude | claude-opus-4-7 | same-chat | ccusage | 220 | 89925 | 21299609 | 553994 | 21943748 | $16.36 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | clear stale hotel legacy/mock docstrings + constants after canonical migration; mark _mock_hotels dead legacy; HANDOFF supersede note; focused mock-leak test | 0 | doc/state drift cleanup followed the routing fix in the same PR |
| 2026-05-14 | #373 | initial | initial | n/a | design-system-foundation | session_011UyHNpGEMaT2rAEjcLYsZY | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | anchor reads (HANDOFF/ROADMAP/BUILD_QUEUE/Design Bible addendum/globals.css/package.json/tsconfig); 6 file writes (globals.css token block + @theme wiring + reduced-motion, tailwind.config.ts, Card.tsx, TrustStrip.tsx, UI_BASELINE.md, HANDOFF.md) | 2 | PDF unreadable at read time — flag and ask for token values rather than inferring from existing code; run tsc locally before push to catch polymorphic element type errors |
| 2026-05-14 | #373 | patch-1 | follow-up | #373 | design-system-foundation | session_011UyHNpGEMaT2rAEjcLYsZY | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | Vercel build logs read; 1-line fix (HTMLAttributes<HTMLDivElement> → HTMLAttributes<HTMLElement> to resolve LiHTMLAttributes incompatibility on polymorphic as prop) | 0 | tsc locally before push catches polymorphic element attr conflicts; HTMLElement is the safe base type |
| 2026-05-14 | #373 | patch-2 | follow-up | #373 | design-system-foundation | session_011UyHNpGEMaT2rAEjcLYsZY | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | preventable-follow-up | 4-file token-value correction (all --ds-* to Bible §4 exact hex); replace legacy palette classes (dark-*, cream-*, emerald-*, amber-*) with ds-* utilities in Card.tsx and TrustStrip.tsx; UI_BASELINE.md table corrected | 0 | read Design Bible PDF before writing tokens; if PDF unreadable flag it — do not infer palette values from pre-existing legacy code |
| 2026-05-15 | #376 | initial | initial | n/a | workflow/scripts,docs,ci | unknown | claude-sonnet-4-6 | new-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | anchor reads (CLAUDE.md, certify, PR template, usage tracking, prompt docs, MISS_LEDGER, hooks); ai_pr_readiness_check.py + CI workflow + hook + command + doc updates | 0 | structural enforcement in scripts/CI removes prompt-level workflow repetition |
| 2026-05-15 | #376 | patch-1 | follow-up | #376 | workflow/scripts,docs,ci | unknown | claude-sonnet-4-6 | same-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | checker fixes (USAGE_CLAIM_RE expansion, JSON mode, env-template exemption, runtime exemption); CLAUDE.md guardrail restoration; dangerous-action scaffold (doc + hook + certify) | 1 | expand USAGE_CLAIM_RE before first CI run; test checker against actual PR body wording before pushing |
| 2026-05-15 | #378 | initial | initial | n/a | frontend/explore,docs | session_01M7GEcBtqoecP1DK4wU4Tot | claude-sonnet-4-6 | new-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | read-first anchors (HANDOFF.md, UI_BASELINE.md, DESIGN_IMPLEMENTATION_CONTRACT.md, 4 Explore components, Card.tsx, TrustStrip.tsx, api.ts types); surgical edits to 4 Explore component files + 2 doc files | 1 | include PR template sections (Severity, AI usage note, AI PR readiness, usage ledger) and run readiness checker against PR body draft before posting |
| 2026-05-15 | #379 | initial | initial | n/a | frontend/saved,ui,css,docs | session_012j24rRezk3c4CCdKtCUWQA | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | anchor reads (HANDOFF, UI_BASELINE, DESIGN_CONTRACT, SavedShell, Card, globals.css); 5 file writes (globals.css, SavedShell.tsx, Card.tsx, UI_BASELINE.md, HANDOFF.md); 1 test-window fix (600-char /explore link) | 1 | verify test char-window bounds (e.g. 600-char /explore test) before initial push; include full PR template sections on first post |
| 2026-05-15 | #381 | initial | initial | n/a | frontend/concierge,layout,docs | session_01CAz1oYN19iMiZj34BbSfW6 | claude-sonnet-4-6 | new-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | anchor reads (HANDOFF, UI_BASELINE, DESIGN_CONTRACT, ConciergePage, Sidebar, MobileNav, AIConciergePanel, api.ts, TrustStrip, tests); 4 file writes (ConciergePage.tsx, page.tsx, UI_BASELINE.md, HANDOFF.md) | 1 | commit ledger row rather than relying on PR body text for CI gate; run ai_pr_readiness_check.py --base-ref origin/main against a body file locally before pushing |
| 2026-05-15 | #381 | patch-1 | follow-up | #381 | frontend/concierge,layout,tests,docs | session_01CAz1oYN19iMiZj34BbSfW6 | claude-sonnet-4-6 | same-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | nav discoverability (Sidebar + MobileNav drawer); TrustStrip fabricated sourceCount fix (actual googleVerification.confidence); behavior honesty docs; static contract test file (16 tests); usage ledger row | 0 | merge-blocker review caught fabricated sourceCount and missing nav — both traceable to incomplete scope of initial prompt |
| 2026-05-15 | #383 | initial | initial | #381 | frontend/concierge,tests | session_019jgFPitPycu8ytBDQBKCCi | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | root-cause diagnosis (422 from missing destination); destination input + state + validation in ConciergePage.tsx; destination passed as 4th arg at all 3 callConciergeSearch call sites; editorial chips with explicit destination; 5 new static test assertions | 0 | include destination gate in initial standalone-page PR to avoid post-merge hotfix; backend require_trip_or_destination validator is the source of truth |
| 2026-05-15 | pending-initial | initial | initial | n/a | workflow/docs,scripts | unknown | claude-haiku-4-5-20251001 | new-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | strict ledger-row enforcement for Level 1+ PRs; docs clarification (AI_USAGE_TRACKING, AI_PR_READINESS_GATE, PR template); MISS_LEDGER entry; self-tests proving enforcement | 0 | structural enforcement gates eliminate prompt-level reminder churn |
| 2026-05-15 | #386 | initial | initial | #384 | backend/concierge,db,tests,docs | session_01Rz5Hkzkeja4U7R3pSXawaz | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | anchor reads (evidence_cache.py, semantic_retrieval.py, mock.py, test files); new SupabaseEvidenceCache + SupabaseNoteCache classes; atom serialization; migration SQL; 48 new tests | 0 | include foundation-only keyword and runtime-validation note when branch diff includes prior UI files; update USAGE_LEDGER in same commit |
| 2026-05-15 | #387 | initial | initial | #386 | backend/concierge,tests | session_01Rz5Hkzkeja4U7R3pSXawaz | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | root-cause analysis (frame_extractor _FILLER_WORDS strips best/top); literal_ask reuse in should_run_editorial; value_signals label mismatch fix; 6 new tests | 0 | simulate CI readiness check locally with fake event JSON before pushing; add USAGE_LEDGER row in same commit as code change |
| 2026-05-15 | #388 | initial | initial | #387 | backend/concierge,tests | session_014XYAf1phCCut69vYgLi6Cn | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | anchor reads (evidence_cache.py, frame_extractor.py, test files); _BROAD_COMMODITY_CONCEPTS frozenset + _is_broad_commodity_concept helper; specific_discovery_subtype branch in should_run_editorial; 6 new tests + 1 updated test | 0 | add USAGE_LEDGER row in same commit as code change to avoid CI readiness failure |
| 2026-05-15 | #390 | initial | initial | #388 | backend/concierge,tests,docs | session_01AHt1Sb5DUodPXeLJVJLtii | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | root-cause diagnosis (set-writer skip not propagated to legacy batched_reason_builder; plain queries like "sports bars" collapsed 6→1 card); NoteDecision shared gate in evidence_cache.py; _assemble_card_reasons elif branch; _assemble_card_set never-exclude fix; ROI telemetry fields; 31 new control-plane tests | 0 | add USAGE_LEDGER row in same commit as code change; include full PR template sections on first post |
| 2026-05-16 | #393 | initial | follow-up | #392 | backend/concierge,frontend/concierge,tests,docs | session_01YYBoGHLrn72m7iT3uA14ME | claude-sonnet-4-6 | same-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | concierge.py: vertical routing hotel-token-before-intent-check fix; destination_source tracking; INTENT_GENERAL hotel branch; _semantic_card_first hotels guard; eligibility logging fields; test expansion 70→102 (H/I/J sections); frontend lazy-init race fix; PR readiness gate compliance | 0 | add USAGE_LEDGER row in same commit as code change; run ai_pr_readiness_check.py locally before pushing to catch ledger requirement |
| 2026-05-16 | #393 | patch-2 | follow-up | #392 | backend/concierge/semantic_retrieval.py,backend/tests | session_01YYBoGHLrn72m7iT3uA14ME | claude-sonnet-4-6 | same-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | stabilization-patch | _entity_to_card made vertical-aware: attractions→UnifiedAttractionResult, hotels→UnifiedHotelResult, restaurants→UnifiedRestaurantResult; _assemble_card_set propagates vertical; 4 type-shape assertion tests added (102→106 passing) | 0 | propagate vertical param through _assemble_card_set→_entity_to_card; add type-shape assertions to catch wrong-type bugs |
| 2026-05-16 | #393 | patch-3 | follow-up | #392 | backend/services/concierge.py,backend/tests | session_01YYBoGHLrn72m7iT3uA14ME | claude-sonnet-4-6 | same-chat | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | stabilization-patch | _detect_semantic_vertical venue-head precedence fix: _FOOD_BAR_HEAD_TOKENS checked before attraction modifier tokens so "sunset restaurants"/"rooftop bars"/"beach clubs" → restaurants; 10 regression tests added; 199 backend tests pass | 0 | check food/bar head tokens before attraction modifier tokens in _detect_semantic_vertical |
| 2026-05-16 | #394 | initial | necessary-follow-up | #393 | backend/services/concierge.py,backend/concierge/retrieval_planner.py,backend/tests | session_01A2PprothiuoJYREMj2KWh5 | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | _ATTRACTION_PAT extended with viewpoint/scenic-point phrases so "sunset points"/"lookout points"/"view points" route INTENT_ATTRACTIONS not INTENT_REWARDS_HELP; _SYNONYM_EXPANSIONS: beach/viewpoint/sunset/scenic/lookout synonyms for 2-3 query fanout; plan_queries Q2 uses pref_primary vs concept_label comparison to avoid compound-phrase corruption; 59 new tests (A-H: intent routing, rewards regression, eligibility, query expansion, mocked cards, no-Tavily, vertical regressions) | 0 | add viewpoint phrases to _ATTRACTION_PAT before _REWARDS_PAT for phrase-context precedence; compare pref_primary override against concept label not compound primary |
| 2026-05-16 | #396 | initial | necessary-follow-up | #394 | backend/concierge/ranker.py,backend/concierge/semantic_retrieval.py,backend/concierge/evidence_cache.py,backend/services/concierge.py,backend/tests | session_01MPoNgDbLgibxsPtP6DKjug | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | three-layer natural-feature precision gate: (1) ranker generic-type filter + name-match suppressor for food/bar/hotel entities; (2) pipeline Step 4.7 hard pre-rank gate with honest empty state + venue-head bypass; (3) editorial gate early-return for natural-feature concepts; _ATTRACTION_PAT extended with beach/waterfall/garden/trail/park; 93 new tests in test_natural_feature_precision_gate.py | 0 | check literal_ask for venue-head tokens in _is_natural_feature_query to avoid gate misfiring for "beach bars"/"sunset cocktail bars"; filter generic Google types before computing type_tokens to prevent "point_of_interest" from contributing "point" to type_match score |
| 2026-05-16 | #397 | initial | necessary-follow-up | #396 | backend/concierge/semantic_retrieval.py,backend/app/core/config.py,backend/tests | session_01DjoMz2FUHMPYSZE2qTB1j3 | claude-sonnet-4-6 | new-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | necessary-follow-up | kill switch enforcement: ALLOW_LIVE_RESEARCH_CALLS=false now blocks editorial/Tavily in semantic_retrieval_v1 Step 5.56 before any key read; Settings.allow_live_research_calls pydantic-settings field added; 17 new tests in test_live_research_killswitch.py covering 5 required queries, config mapping, and kill-switch-on selectivity preservation | 0 | patch evidence cache mocks when test needs editorial path to reach selectivity gate; bypass conftest sys.modules stub via importlib.util.spec_from_file_location for Settings config tests |

## Per-prompt delta workflow

```bash
# a) Initial PR prompt: save baseline before, capture after
bash scripts/ai/usage_snapshot.sh --save-baseline before-pr-123
# ... Claude does the work ...
bash scripts/ai/usage_snapshot.sh --pr 123 --prompt-id initial --phase initial \
  --delta-from-baseline .ai/usage/baseline-before-pr-123.json \
  --model claude-sonnet-4-6 --repo-area workflow/docs \
  --main-drivers "anchor reads, file writes" --follow-up-patches 0 \
  --waste-classification none --append-ledger

# b) Follow-up patch delta linked to original PR
bash scripts/ai/usage_snapshot.sh --save-baseline before-patch1
# ... Claude patches ...
bash scripts/ai/usage_snapshot.sh --pr 124 --prompt-id patch-1 --phase follow-up \
  --linked-pr 123 --delta-from-baseline .ai/usage/baseline-before-patch1.json \
  --waste-classification preventable-follow-up --append-ledger
```

If ccusage is unavailable, delta fields show `unavailable` — that is acceptable.

## Backfilling prior sessions

```bash
bash scripts/ai/backfill_usage_ledger.sh --since YYYY-MM-DD
```

Prints 26-column candidate rows with `phase=backfill`, `prompt_id=unknown`, delta=`unavailable`.
Do not guess PR numbers or delta values — mark as `unknown`/`unavailable`.

## Audit guidance

Use this ledger plus GitHub PR history to diagnose token burn:
- High Δ total for `follow-up` phase → contract was unclear at initial PR time.
- `preventable-follow-up` waste → candidate for `docs/ai/MISS_LEDGER.md` promotion.
- High session input tokens, low output → over-broad discovery reads.
- Recurring efficiency lessons → consider OS-level rule change.
