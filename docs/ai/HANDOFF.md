# AI Handoff — Travel Concierge

## Last change (2026-05-07) — PR #268: AI Concierge v2 Visible Copy Quality Contract

**Status: MERGE-READY** — 119 claim-safety reviewer tests pass (64 new for PR #268, 55 unchanged from PR #267); 56 set-level-writer tests pass (unchanged); 68 semantic-query-frame tests pass (unchanged); 67 soft-preference-preservation tests pass (unchanged); 64 SLA tests pass (unchanged); 127 evidence-quality tests pass (unchanged)

### What was built

Visible Copy Quality Contract — deterministic visible-copy quality gates and sanitizers extending the PR #267 claim-safety reviewer. Adds four new blocking patterns for: malformed rating residue in summaries ("Taproom.8" → "Taproom"), unsupported after-hours/crowd positioning ("purpose-built for after-hours crowds"), hidden-gem/localness superlatives without evidence ("under-the-radar picks"), and unsupported scenic/view claims in summaries. Adds one new per-card note rejection pattern for generic occasion-sprawl ("suited for occasions ranging from casual groups to anniversaries").

**Root cause**: PR #267 blocked specific patterns (name-hours inference, internal label leakage, generic filler) but left visible summary/note text without guards for: malformed rating residue from LLM number/name concatenation; overconfident after-hours crowd positioning claims; high-confidence localness superlatives in set-level summaries; unsupported scenic/view superlatives in summaries; and generic occasion-sprawl in per-card notes.

**Changes made**:

1. **`backend/app/concierge/claim_safety_reviewer.py`** (modified):
   - `_MALFORMED_RATING_RESIDUE_RE`: regex matching CamelCase words with accidentally appended decimal-digit rating residue (`Taproom.8`, `Bar.4`).
   - `_AFTER_HOURS_CROWD_RE`: regex blocking "purpose-built for after-hours crowds", "built/designed/tailored for late-night crowds" — overconfident positioning without hours/crowd evidence.
   - `_OCCASION_SPRAWL_RE`: regex blocking "suited for occasions ranging from X to Y", "a range of occasions", "from casual groups to anniversaries" in per-card notes.
   - `_SUMMARY_VIEW_CLAIM_RE`: regex blocking scenic/view superlatives in summaries ("stunning views", "waterfront dining", "panoramic setting", "lake views", etc.) — per-card notes already covered by `reason_validator._UNSUPPORTED_ATTRIBUTE_RE`.
   - `_HIDDEN_GEM_TERMS_RE`: updated to match both "secret" and "secrets" (plural).
   - `_sanitize_malformed_rating_residue()`: strips `.N`/`.N.M` suffix from matched words, preserving the rest of the summary.
   - `review_summary()`: extended with 4 new sanitization passes (before existing checks): malformed rating residue (in-place sub), after-hours crowd (sentence remove), hidden-gem superlatives (sentence remove), unsupported view claims (sentence remove). Chains sanitizations; accumulates `was_sanitized` flag; fail-closed on timeout at each step.
   - `review_note()`: extended with 2 new rejection checks: `after_hours_crowd_overconfidence` (check 4), `generic_occasion_sprawl` (check 5).
   - `ReviewerTelemetry`: 3 new fields — `malformed_summary_count`, `unsupported_superlative_count`, `generic_note_hidden_count` — plus `as_dict()` updated.
   - `review_notes_set()`: counts `after_hours_crowd_overconfidence` → `unsupported_superlative_count`; `generic_occasion_sprawl` → `generic_note_hidden_count` in telemetry.

2. **`backend/tests/test_claim_safety_reviewer.py`** (modified):
   - Tests 16–23 (64 new tests):
     - Tests 16: Malformed rating residue — "Taproom.8" sanitized, residue removed, safe content preserved.
     - Tests 17: After-hours crowd overconfidence — summary/note rejection; gate path; regex variants; honest description passes.
     - Tests 18: Hidden-gem superlatives — "under-the-radar", "best-kept secrets", "locals love" sanitized from summaries.
     - Tests 19: Unsupported view/scenic claims — "stunning views", "waterfront dining", "lake views" sanitized; safe "with a view" user-intent citation passes.
     - Tests 20: Occasion-sprawl in notes — "suited for occasions ranging from X to Y" rejected; specific-occasion mentions pass.
     - Tests 21: Card preservation — all place_ids present even when notes hidden.
     - Tests 22: Invariants — `fallback_note_visible_count=0`, `deterministic_visible_count=0`, new telemetry fields present and defaulted to 0.
     - Tests 23: Regression — PR #267 behaviors (name-alone-signals, internal leakage, generic filler, entity-name temporal inference) unchanged; safe summaries pass unchanged through chained sanitization.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate unchanged
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (unchanged)
- No SQL, no UI changes, no new providers, no new LLM calls, no retrieval/ranking changes
- Reviewer rejects/hides notes only — never drops Google-verified cards
- All PR #267 checks preserved in same order; new checks run before existing checks in `review_summary()`, after existing checks in `review_note()`

### New telemetry added (extends PR #267 `reviewer_telemetry`)

```
malformed_summary_count     — summaries with rating-residue sanitized
unsupported_superlative_count — notes with after-hours crowd overconfidence
generic_note_hidden_count     — notes hidden due to occasion-sprawl
```

### Remaining limitations

- Sanitization is deterministic: rephrased variants of blocked patterns (e.g., "tailor-made for the after-midnight crowd") may not be caught. The set-writer prompt already discourages these; this is the last regex gate.
- `_MALFORMED_RATING_RESIDUE_RE` targets CamelCase words only (capital + 2+ lowercase), avoiding version numbers and abbreviations. All-lowercase concatenations (e.g., "taproom.8") would not be caught but are unlikely in LLM output.
- Hidden-gem/localness checks sanitize at the sentence level; if the entire summary is the offending sentence, it is rejected (empty). This is correct per the "do not over-hide" spec.

### Supabase SQL: No

### Test counts

```
test_claim_safety_reviewer.py:  119 tests, all pass (64 new, 55 unchanged from PR #267)
test_set_level_writer.py:        56 tests, all pass (unchanged)
test_semantic_query_frame.py:    68 tests, all pass (unchanged)
test_soft_preference_preservation.py: 67 tests, all pass (unchanged)
test_sla_card_cap.py:            64 tests, all pass (unchanged)
test_evidence_quality_v3.py:    127 tests, all pass (unchanged)
```

---

## Previous: PR #267: AI Concierge v2 LLM Reviewer / Claim-Safety Gate for Set Writer + Summary

**Status: MERGE-READY** — 55 new claim-safety reviewer tests pass; 56 set-level-writer tests pass (unchanged); 68 semantic-query-frame tests pass (unchanged); 67 soft-preference-preservation tests pass (unchanged); 64 SLA tests pass (unchanged); 127 evidence-quality tests pass (unchanged)

### What was built

Claim-Safety Reviewer Gate — deterministic (regex-based) claim-safety layer that gates set-writer visible output (per-card concierge notes and set-level summary text) before response serialization. Fixes the visible quality failure where the set-writer produced "2AM Izakaya, whose name alone signals late-night credibility" — an unsupported inference from the business name that escaped existing validation.

**Root cause**: The existing `reason_validator.py` correctly blocked hard hour claims ("open until") but had no pattern for name-based temporal inference ("name alone signals late-night credibility"). The LLM set-writer was generating creative inferences from business names that passed all existing checks.

**Changes made**:

1. **`backend/app/concierge/claim_safety_reviewer.py`** (new):
   - `_NAME_HOURS_INFERENCE_RE`: regex blocking "name (alone) signals/implies/suggests late-night/24-hour/open-late" and "whose name (alone) signals/implies/suggests."
   - `_INTERNAL_LABEL_RE`: blocks internal role labels (best_overall, evidence_rich, etc.), dossier internals, and reviewer diagnostics from user-visible output.
   - `_FILLER_SKELETON_RE`: blocks generic filler phrases.
   - `NoteReviewResult`, `SummaryReviewResult`, `ReviewerTelemetry`: typed contracts for reviewer output.
   - `review_note(note, entity_name, frame, evidence, timeout_s)`: per-card deterministic reviewer with entity-name-as-subject temporal inference check ("2AM Izakaya signals 24-hour availability" → rejected).
   - `review_summary(summary, frame, timeout_s)`: set-level summary reviewer with sanitization attempt (removes offending sentence before full rejection).
   - `review_notes_set(notes, entity_names, frame, timeout_s)`: batch reviewer with aggregated `ReviewerTelemetry`.
   - Fail-closed contract: timeout → hide note but keep card; no card drop on any reviewer failure.

2. **`backend/app/concierge/reason_validator.py`** (modified):
   - `_NAME_HOURS_INFERENCE_RE`: same pattern added at the universal per-note level so ALL validation paths (set-writer, batched builder) catch name-hours inference.
   - Check added at step 1e in `validate_reason()`, before the unsupported-attribute check.

3. **`backend/app/concierge/set_level_writer.py`** (modified):
   - `SetWriterResult.reviewer_telemetry`: new optional field for reviewer telemetry dict.
   - `as_telemetry_dict()`: includes `reviewer_telemetry` key when reviewer ran.
   - `write_set_notes()`: calls `review_notes_set()` after existing validation + diversity check. Reviewer budget is capped at 2s and the remaining time budget. Notes rejected by reviewer are hidden (validated=False); cards are NOT dropped.

4. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - `_log_semantic_turn()`: emits `semantic_retrieval_v1.reviewer_telemetry` log line when reviewer ran this turn (sub-key of set_writer_telemetry).

5. **`backend/tests/test_claim_safety_reviewer.py`** (new, 55 tests):
   - Tests 1–8: Summary reviewer rejects name-hours inference; multi-sentence sanitization; allows honest caveats.
   - Tests 9–11: Allows evidence-backed late-night claims; direct hours statements pass.
   - Tests 12–17: Per-card reviewer rejects name-signals temporal claims; allows honest mention; reviewer_ms populated.
   - Tests 18–20: Hidden note does not drop card; telemetry counts correctly.
   - Tests 21–24: Waterfront/view scope boundary (reason_validator owns; reviewer does not double-block).
   - Tests 25–27: Hidden-gem regex coverage; reviewer scope boundary.
   - Tests 28–33: Internal label leakage — role names, dossier fields, reviewer diagnostics rejected.
   - Tests 34–36: Generic filler / repeated skeleton rejected.
   - Tests 37–41: Timeout fail-closed — note hidden, card kept; telemetry reports timed_out.
   - Tests 42–47: Existing contracts — fallback_note_visible_count=0; deterministic_visible_count=0; required telemetry fields.
   - Tests 48–52: reason_validator integration — validate_reason rejects all name-hours inference variants.
   - Tests 53–55: SetWriterResult reviewer_telemetry field; as_telemetry_dict with/without reviewer.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate unchanged
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (unchanged)
- No SQL, no UI changes, no new providers, no new LLM calls, no retrieval/ranking changes
- Reviewer rejects/hides notes only — never drops Google-verified cards

### New telemetry added

```
reviewer_telemetry (sub-key of set_writer_telemetry):
  reviewer_used              — bool
  reviewer_ms                — int
  reviewer_timed_out         — bool
  reviewer_rejected_note_count  — int
  reviewer_hidden_note_count    — int
  reviewer_rejected_summary     — bool
  reviewer_sanitized_summary    — bool
  reviewer_unsupported_claim_count  — int
  reviewer_internal_leakage_count   — int
  final_summary_visible      — bool
  final_note_visible_count   — int
  fallback_note_visible_count — int (invariant: 0)
  deterministic_visible_count — int (invariant: 0)
```

### Remaining limitations

- Reviewer is deterministic (regex-based), not LLM-backed. Complex paraphrases of unsupported claims that don't match the regex patterns may still pass. The set-writer prompt already discourages these patterns; this gate is the last line of defense.
- `review_summary()` is available but no set-level intro summary is currently generated; the reviewer is applied only to per-card notes in this PR.
- Waterfront/view/hidden-gem evidence-based checks remain in `reason_validator.py`; the reviewer adds name-inference and internal-label checks as an independent layer.

### Supabase SQL: No

### Test counts

```
test_claim_safety_reviewer.py:   55 tests, all pass (new)
test_set_level_writer.py:        56 tests, all pass (unchanged)
test_semantic_query_frame.py:    68 tests, all pass (unchanged)
test_soft_preference_preservation.py: 67 tests, all pass (unchanged)
test_sla_card_cap.py:            64 tests, all pass (unchanged)
test_evidence_quality_v3.py:    127 tests, all pass (unchanged)
```

---

## Previous: PR #266: AI Concierge v2 Preference-Aware Retrieval and Ranking for Soft Modifiers

**Status: MERGE-READY** — 67 new soft-preference-preservation tests pass; 68 semantic-query-frame tests pass (unchanged); 56 set-level-writer tests pass; 51 curator tests pass; 54 dossier tests pass; 28 parallel-retrieval tests pass; 64 SLA tests pass; 127 evidence-quality tests pass; pre-existing pydantic env failures remain (unrelated, same as before)

### What was built

Soft Preference Preservation — deterministic backend-only layer that preserves travel modifiers ("hidden gem", "romantic", "late night", "with a view") as normalized soft preferences flowing through retrieval query generation and ranking. Fixes the remaining product gap where "hidden gem restaurants" searched too generically (bare `restaurant Chicago`) after PR #265 correctly fixed the venue head but discarded the user's preference intent.

**Root cause**: PR #265 suppressed "gem" as a `_TRAVEL_PREFERENCE_NOUN` so it no longer became the venue head. However, the `ExperienceFrame` only tracked `suppressed_preference_nouns` as telemetry — neither the retrieval planner nor the ranker used those preserved signals to shape queries or ranking. Result: "hidden gem restaurants" produced only `restaurant Chicago` (generic), returning The Purple Pig and Aba rather than credibly local/neighborhood places.

**Changes made**:

1. **`backend/app/concierge/frame_extractor.py`** (modified):
   - `_HIDDEN_GEM_CONTEXT_PATTERN`: new regex detecting hidden-gem/local-favorite/underrated phrases (`hidden gem`, `local favorite`, `neighborhood haunt`, `underrated`, `undiscovered`, `off the beaten`, `low profile`). Generalised — not per-keyword.
   - `_VIEW_PREFERENCE_PATTERN`: detects `with a view`, `rooftop`, `patio`, `terrace`, `outdoor` for the case where geo_hints is empty (e.g., "taprooms with a view").
   - `_TEMPORAL_PATTERNS`: detects `late night`, `open late`, `after hours`, `night owl` → `late_night` label.
   - `_TEMPORAL_QUALIFIER_TOKENS`: frozenset of words that form temporal phrases ("late", "night", "midnight", "after", "hours", etc.) that must NOT win as primary venue concepts. Prevents "late night izakayas" from extracting "late" as the venue head.
   - `_classified_modifier_tokens()`: now accepts optional `temporal_constraints` parameter; `_TEMPORAL_QUALIFIER_TOKENS` added to exclusion set so temporal words never beat venue heads.
   - `_extract_temporal_constraints(query)`: new function populating `temporal_constraints`.
   - `_extract_normalized_soft_preferences(query, suppressed_nouns, soft_prefs, temporal, geo_hints)`: new function normalizing raw signals into canonical labels (`hidden_gem`, `romantic`, `intimate`, `late_night`, `view_or_geo`). `view_or_geo` only added when `geo_hints` is empty (to avoid double-counting the existing geo_term retrieval path).
   - `ExperienceFrame`: new field `normalized_soft_preferences: List[str]` — canonical preference labels for retrieval/ranking. Backend-only, never surfaced to UI.
   - `temporal_constraints` now populated (was always `[]` before).

2. **`backend/app/concierge/retrieval_planner.py`** (modified):
   - `_PREFERENCE_QUERY_MODIFIERS`: new dict mapping canonical preference → list of query modifier phrases. "hidden_gem" uses ["local favorite", "neighborhood", "underrated"] (not "gem" or "hidden gem" which risk jewelry-shop results). "romantic" uses ["romantic", "date night", "intimate"]. "late_night" uses ["late night", "open late"]. "view_or_geo" uses ["rooftop", "with a view", "outdoor"].
   - `plan_queries()`: new preference-aware path. When `normalized_soft_preferences` is non-empty and no geo_term/loc_anchor present, generates up to cap preference-aware venue-anchored queries (e.g., `local favorite restaurant Chicago`, `neighborhood restaurant Chicago`, `underrated restaurant Chicago`) instead of the generic bare `restaurant Chicago`. Uses first synonym variant as `pref_primary` when more descriptive (e.g., "cocktail bar" for concept "cocktail"). Fallback to original path when geo/loc constraints dominate.

3. **`backend/app/concierge/ranker.py`** (modified):
   - Weight adjustment: `_W_POPULARITY` reduced from 0.06 → 0.04; `_W_TRIP_CONTEXT` from 0.04 → 0.02; `_W_VALUE` from 0.04 → 0.02; new `_W_PREFERENCE_FIT = 0.06`. Weights still sum to 1.0.
   - `RankScore`: new field `preference_fit: float = 0.5` (neutral default); added to `as_dict()`.
   - `_preference_fit(entity, frame)`: new function. Returns 0.5 neutral when no soft preferences active. For `hidden_gem`: prefers moderate-visibility (50–500 reviews = +0.10) over mega-popular (>2000 = -0.05). For `romantic`/`intimate`: +0.08 when name contains romantic vocabulary. For `late_night`: +0.08 when name has EXPLICIT late-night indicators ("Late Night", "Midnight", "After Hours", "All Night", "24 Hour"); "2AM" in a business name deliberately excluded per claim-safety spec. `view_or_geo`: neutral — `geo_fit` already carries the signal.

4. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - `frame_finalization_telemetry`: added `normalized_soft_preferences`, `hidden_gem_preference_active`, `temporal_constraints`.

5. **`backend/tests/test_soft_preference_preservation.py`** (new, 67 tests):
   - Tests 1–5: Frame extraction for hidden gem restaurants, hidden gem bars, romantic cocktail bars, taprooms with a view, late night izakayas.
   - Tests 6–10: Retrieval query shapes — venue-anchored, preference-aware, no bare gem.
   - Tests 11–14: Ranking signal tests — hidden_gem local-scale vs mega-popular, weights invariant, subtype_fit dominance.
   - Tests 15–17: Claim safety — "2AM Izakaya" no late_night boost, view/waterfront neutrality, contract invariants.
   - Tests 18–20+: Telemetry field coverage, `_PREFERENCE_QUERY_MODIFIERS` structure, weight sum, temporal extraction.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate unchanged
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (unchanged)
- No SQL, no UI changes, no new providers, no new LLM calls
- `normalized_soft_preferences` is frame-only backend telemetry — never in any card payload field
- `_W_SUBTYPE_FIT` (0.34) >> `_W_PREFERENCE_FIT` (0.06) — preference cannot override category trust

### New telemetry added to `frame_finalization_telemetry`

```
normalized_soft_preferences    — canonical labels ["hidden_gem", "romantic", "late_night", "view_or_geo"]
hidden_gem_preference_active   — bool shortcut
temporal_constraints           — e.g. ["late_night"]
```

### Query output examples (Chicago)

```
"hidden gem restaurants"  → local favorite restaurant Chicago / neighborhood restaurant Chicago / underrated restaurant Chicago
"hidden gem bars"         → local favorite bar Chicago / neighborhood bar Chicago / underrated bar Chicago
"romantic cocktail bars"  → romantic cocktail bar Chicago / date night cocktail bar Chicago / intimate cocktail bar Chicago
"taprooms with a view"    → rooftop taproom Chicago / with a view taproom Chicago / outdoor taproom Chicago
"late night izakayas"     → late night izakaya Chicago / open late izakaya Chicago / izakaya Chicago
"best waterfront breweries" → brewery Chicago waterfront / brewery Chicago / taproom Chicago waterfront  (geo path unchanged)
```

### Remaining limitations

- Preference-aware ranking boost is modest (max ±0.10 on a 0.06-weight signal). Strong concept candidates are still dominant; this correctly tilts tie-breaks without overriding category trust.
- `_HIDDEN_GEM_CONTEXT_PATTERN` captures the most common phrasings. New phrasings ("sleeper hit", "under the radar spots") are not yet detected by the pattern but will still get `hidden_gem` if they contain a suppressed `_TRAVEL_PREFERENCE_NOUN` like "sleeper".
- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- LLM reviewer gate not built (PR #262).

### Supabase SQL: No

### Test counts

```
test_soft_preference_preservation.py:  67 tests, all pass (new)
test_semantic_query_frame.py:          68 tests, all pass (unchanged)
test_set_level_writer.py:              56 tests, all pass (unchanged)
test_card_curator.py:                  51 tests, all pass (unchanged)
test_evidence_dossier.py:              54 tests, all pass (unchanged)
test_parallel_retrieval.py:            28 tests, all pass (unchanged)
test_sla_card_cap.py:                  64 tests, all pass (unchanged)
test_evidence_quality_v3.py:          127 tests, all pass (unchanged)
```

---

## Previous: PR #265 — AI Concierge v2 Semantic Query Frame Hardening

**Status: MERGE-READY** — 68 new semantic-query-frame tests pass (updated from 59 after review fixes); 56 set-level-writer tests pass; 51 curator tests pass; 54 dossier tests pass; 28 parallel-retrieval tests pass; 64 SLA tests pass; 127 evidence-quality tests pass; 20 pre-existing pydantic env failures remain (unrelated, same as before)

**Review fixes (PR #265 update)**:
- Step 8 assembly extracted into testable `_assemble_card_set()` helper; focused integration tests now exercise the actual assembly path with mocked `_entity_to_card` — old `continue` branch would return 1 card, new path returns 2.
- Telemetry split: `insufficient_verified_candidates` now uses `verified_count < 5` (Google trust gate count) instead of `final_card_count < 5`; added `below_first_card_limit` (final count vs configured limit) and `pre_assembly_verified_count`.

### What was built

Semantic Query Frame Hardening — deterministic frame-finalization layer that prevents travel preference nouns (e.g., "gem" in "hidden gem restaurants") from overriding explicit venue heads. Also fixes a card-count bug where the set-writer primary path was silently dropping Google-verified cards with hidden notes.

**Problem 1 (root cause)**: "hidden gem restaurants" extracted `venue_concept='gem'` and searched `['gem Chicago']`, returning jewelry/gem shops instead of restaurants. Root cause: `gem` was not classified as a modifier token, so it beat `restaurants` (filtered as a `_GENERIC_PLACE_NOUN`).

**Problem 2 (card count)**: The set-writer primary path in `semantic_retrieval.py` Step 8 dropped Google-verified cards whose set-writer notes failed validation, contradicting the PR #261 contract ("hide invalid notes, not valid cards"). This caused 3–4 visible cards when 5–7 were available.

**Changes made**:

1. **`backend/app/concierge/frame_extractor.py`** (modified):
   - `_TRAVEL_PREFERENCE_NOUNS`: new frozenset of nouns that function as soft preference descriptors in compound travel phrases (`gem`, `gems`, `find`, `finds`, `haunt`, `haunts`, `sleeper`, `sleepers`, `discovery`, `discoveries`, `treasure`, `treasures`, `jewel`, `jewels`, `diamond`, `diamonds`). Generalised — not a per-keyword hack.
   - `_classified_modifier_tokens()`: now includes `_TRAVEL_PREFERENCE_NOUNS`, ensuring these tokens are excluded from venue-concept candidates when a concrete venue noun exists.
   - `_find_suppressed_preference_nouns()`: new helper that returns preference nouns found in the query's main clause. Backend-only telemetry — never surfaced in UI.
   - `ExperienceFrame`: new field `suppressed_preference_nouns: List[str]` populated by `_extract_frame_impl`. Backend telemetry only.
   - `_extract_frame_impl()`: computes and populates `suppressed_preference_nouns`; extends debug log to include the field.

2. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Step 7 set-writer primary path: now populates `card_reasons` for ALL cards (including those with hidden/unvalidated notes as `CardReason(validated=False)`). Previously only validated notes were added, causing hidden-note cards to be silently dropped in Step 8.
   - `set_writer_primary_active` flag: initialized to `False`; set `True` only in the set-writer primary branch. Used in Step 8 to distinguish the two paths.
   - Step 8 assembly: when `set_writer_primary_active=True`, cards with `cr.validated=False` are included without a note block (`reason_validated=False`) instead of being excluded. LLM fallback path behavior unchanged.
   - `rejection_stats`: added `insufficient_verified_candidates` (bool, True when `final_card_count < 5`) and `insufficient_verified_candidates_count`.
   - `_log_semantic_turn()`: added `frame_finalization_telemetry` parameter; emits as `semantic_retrieval_v1.frame_finalization_telemetry` separate log line containing raw concepts, finalized venue head, suppressed preference nouns, soft preferences, geography hints, retrieval queries, and insufficient_verified_candidates flag.

3. **`backend/tests/test_semantic_query_frame.py`** (new, 59 tests):
   - `TestTravelPreferenceNounsClassified` (5 tests): preference nouns in set, in classified tokens.
   - `TestHiddenGemRestaurants` (7 tests): venue head=restaurant; no gem/jewelry queries; suppressed_preference_nouns populated.
   - `TestRomanticCocktailBars` (4 tests): cocktail wins; romantic is soft preference.
   - `TestBestWaterfrontBreweries` (5 tests): brewery wins; waterfront is geo hint + ambiguity flag.
   - `TestIzakayas` (3 tests): izakaya unchanged; open_class_detected=True.
   - `TestTaproomsWithAView` (5 tests): taproom wins; view is ambiguity flag; view not standalone query entity.
   - `TestInvariantsPreserved` (11 tests): frame never raises; suppressed nouns tracking; generic noun preferred over preference noun; preference nouns don't leak into concepts.
   - `TestSetWriterCardCountContract` (4 tests): fallback_note_visible_count=0; hidden note card not dropped.
   - `TestTelemetryFields` (6 tests): suppressed_preference_nouns populated; clean queries have empty list.
   - `TestPRContractRegression` (8 tests): PR #257–#261 structural invariants unchanged; new frame field exists; card-count 5–7 contract preserved.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (PR #257 invariant — unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (structural — unchanged)
- Card count contract: valid Google-verified cards with hidden notes are now INCLUDED without a note block (not dropped) — fixes the 3–4 card bug
- Internal evidence gaps, role labels, preference nouns never surfaced in UI (unchanged + new enforcement for suppressed_preference_nouns)
- `suppressed_preference_nouns` is frame-only telemetry — not in any card payload field
- No SQL, no UI changes, no new providers, no LLM calls added

### Frame finalization telemetry added

Emitted as `semantic_retrieval_v1.frame_finalization_telemetry` structured log:
```
raw_concepts                       — [(label, confidence)] list before venue-head finalization
finalized_venue_head               — frame.subtype_concepts[0].label
suppressed_preference_nouns        — preference nouns found and demoted (e.g. ["gem"])
soft_preferences                   — ambience/occasion preferences (e.g. ["romantic"])
geography_hints                    — geo modifiers (e.g. ["waterfront"])
retrieval_queries                  — final Google Text Search queries sent
insufficient_verified_candidates   — True when final_card_count < 5
final_card_count                   — count after trust gate and cap
```

Also added to `rejection_stats`:
```
insufficient_verified_candidates        — bool flag
insufficient_verified_candidates_count  — int
```

### Card-count findings

The 3–4 visible card issue was caused by the set-writer primary path in Step 8 dropping cards whose notes failed validation. Fixed: in set-writer primary mode, cards with hidden notes are now included without a note block rather than excluded. The LLM fallback path behavior is unchanged (cards without validated LLM notes are still excluded in that path).

### Remaining limitations

- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- LLM reviewer gate not built (PR #262).
- `_TRAVEL_PREFERENCE_NOUNS` covers 8 common travel preference descriptor nouns; future expansion possible if new problematic nouns are identified.

### Supabase SQL: No

### Test counts

```
test_semantic_query_frame.py:   59 tests, all pass (new)
test_set_level_writer.py:       56 tests, all pass (unchanged)
test_card_curator.py:           51 tests, all pass (unchanged)
test_evidence_dossier.py:       54 tests, all pass (unchanged)
test_parallel_retrieval.py:     28 tests, all pass (unchanged)
test_sla_card_cap.py:           64 tests, all pass (unchanged)
test_evidence_quality_v3.py:    53 tests, all pass (unchanged)
test_evidence_quality_v4.py:    37 tests, all pass (unchanged)
test_evidence_quality_v5.py:    37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — PR #261: Set-Level Writer v1

**Status: MERGE-READY** — 56 new set-level-writer tests pass; 51 PR #260 curator tests pass; 54 PR #259 dossier tests pass; 28 PR #258 tests pass; 64 PR #257 SLA tests pass; 127 evidence-quality tests pass; 19 pre-existing pydantic env failures remain (unrelated)

### What was built

Set-Level Writer v1 — evidence-grounded, set-aware note generation for AI Concierge v2. No UI, SQL, provider additions, or frontend changes.

**Problem**: AI Concierge note generation was isolated per-card: generic one-offs without role awareness, cross-card distinctness enforcement, or dossier-based evidence. Notes were often repetitive, thin, and rating/review-count primary. PR #261 creates a coordinated set-level writer that uses `CuratedSetResult` + `PlaceEvidenceDossier` to generate notes as a set, not in isolation.

**Changes made**:

1. **`backend/app/concierge/set_level_writer.py`** (new):
   - `SetWriterCardInput`: entity + rank_score + dossier + role + curation_signals + original_rank_index.
   - `SetWriterNote`: place_id + note + validated + rejection_reason + source + role_used_internal + evidence_terms_used + caveat_type. No visible card payload fields.
   - `SetWriterResult`: notes_by_place_id + visible_note_count + hidden_note_count + rejected_note_count + timed_out + fallback_note_visible_count (always 0) + role_note_counts + note_source_counts + repeated_skeleton_count + unsupported_claim_count + `as_telemetry_dict()`.
   - `_EvidenceStub`: minimal evidence adapter for `validate_reason()` built from dossier fields (structured_facts, uncertainty_flags, entity).
   - `_build_card_evidence_block()`: per-card evidence text from dossier — explicit themes vs listing-context distinguished; role converted to user-friendly hint (never raw label); internal_evidence_gaps never included.
   - `_build_set_level_prompt()`: set-level prompt with cross-card distinctness requirement, rating/review anti-patterns, modifier three-way distinction, evidence-only grounding.
   - `_validate_set_writer_note()`: safety gate via `validate_reason` + quality gate via `_QUALITY_THIN_RE`/`_PURE_CAVEAT_FULL_NOTE_RE` (re-used from batched_reason_builder).
   - `_count_repeated_skeletons()`: cross-card skeleton diversity check using `_skeleton()` from batched_reason_builder.
   - `write_set_notes()`: main entry point. Budget-gated via `deadline.budget_for_note_generation_s()`; catches all exceptions; returns `SetWriterResult(timed_out=True)` on any failure. Never raises.

2. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Step 5.8 added after Step 5.7 curator: calls `write_set_notes`; emits `set_writer_telemetry`; catches exceptions and falls back.
   - Step 7 modified: set-writer primary path converts `SetWriterNote` objects to `CardReason` dict when writer succeeded with visible notes; creates `ReasoningResultV2` from writer output; falls back to existing `build_reasons_with_retry` cascade when writer timed out or produced zero notes.
   - `_log_semantic_turn` gains `set_writer_telemetry` parameter.
   - `rejection_stats` gains `set_writer_used` and `set_writer_visible_note_count` fields.
   - `semantic_retrieval_v1.set_writer_telemetry` emitted as a separate structured log line.

3. **`backend/tests/test_set_level_writer.py`** (new, 56 tests):
   - All 20 required test scenarios from PR #261 spec.
   - `TestSetWriterInputBuilding` — builds inputs from curated cards; no visible payload fields.
   - `TestNoRoleLabelInNote` — raw role strings not in evidence block or note text.
   - `TestNoInternalEvidenceGapsExposed` — gaps not in block, not in note fields.
   - `TestNoRatingReviewPrimary` — 10 parametrized bad notes all rejected.
   - `TestExplicitThemeEvidenceUsed` — Place Details themes in evidence block; STRONG quality signal.
   - `TestListingContextLowerTrust` — listing-context vs explicit labels differ in block.
   - `TestNoViewFromAddressAlone` — 4 parametrized scenic claims rejected without evidence.
   - `TestRequestedConfirmedModifierAllowed` — confirmed modifier note tested.
   - `TestUnconfirmedModifierCaveat` — false claim rejected; honest caveat (negation before modifier) passes.
   - `TestUnrequestedThemeNotMisattributed` — outdoor theme allowed without claiming waterfront match.
   - `TestNoteDistinctness` — repeated skeletons counted; distinct notes have zero count.
   - `TestFailedValidationHidesNote` — rejected note → validated=False, note="", fallback_note=0.
   - `TestLowEvidenceCardPreserved` — thin note produces hidden SetWriterNote, not dropped card.
   - `TestTimeoutNoBudgetPath` — no budget → timed_out=True, visible=0, fallback=0.
   - `TestExceptionPathSafe` — LLM/prompt/empty exceptions all return safely.
   - `TestTelemetryAccuracy` — telemetry counts match result; all required keys present.
   - `TestPR257FallbackNoteInvariant` — fallback_note_visible_count always 0.
   - `TestPR258ContractsUnchanged` — parallel_retrieval and deadline_manager unchanged.
   - `TestPR259DossierContractsUnchanged` — dossier classes importable; no note fields.
   - `TestPR260CuratorContractsUnchanged` — curator importable; CuratedCard no visible payload.
   - `TestSemanticRetrievalIntegration` — set_writer importable from retrieval context; empty/capped correctly.
   - `TestPromptStructure` — no raw role labels in prompt; anti-patterns present; distinctness mentioned.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (structural invariant from PR #257 — unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (structural — unchanged)
- View/patio/waterfront themes require explicit enrichment evidence (PR #259 invariant — unchanged)
- Internal evidence gaps never surface as visible note prose (PR #259 invariant — unchanged)
- Curator failure cannot block card return (PR #260 invariant — unchanged)
- Role labels are internal only — never surfaced in visible card payload or user-facing text (new enforcement point)
- Writer failure cannot block card return (new invariant — write_set_notes never raises)
- Failed note validation produces hidden note (validated=False), not fallback prose
- No SQL, no new providers, no UI changes, no frontend payload shape changes

### Set-level writer note rules

1. Evidence-grounded: only dossier-supplied facts may be used; fabrication blocked by reason_validator.
2. Distinct across set: cross-card skeleton diversity checked; prompt enforces structural variation.
3. Role-aware: internal role converted to user-friendly hint in prompt; raw label never in note.
4. Honest modifier caveats: confirmed → may state; not_confirmed → negation required.
5. Listing context lower trust: view entries prefixed "listing_context:" labeled differently from amenity-confirmed entries.
6. Rating/review count forbidden as primary differentiator: blocked in prompt + quality gate.
7. Failed validation hides note block: card still returned; note block hidden (display_why_validated=False).
8. Low-evidence cards: SetWriterNote with validated=False included in notes_by_place_id; card not dropped.

### Telemetry added (PR #261)

Emitted as `semantic_retrieval_v1.set_writer_telemetry` structured log:
```
set_writer_input_count           — cards fed to writer
set_writer_output_count          — cards processed (should equal input)
set_writer_visible_note_count    — notes that passed validation
set_writer_hidden_note_count     — notes hidden (failed validation or null)
set_writer_rejected_note_count   — notes that had content but failed validator
set_writer_timed_out             — True if deadline gate fired
set_writer_fallback_to_existing_path — True if writer was skipped/failed
set_writer_fallback_note_visible_count — always 0 (invariant)
set_writer_role_note_counts      — {role: visible_note_count}
set_writer_note_source_counts    — {source: count}
set_writer_repeated_skeleton_count — notes sharing a structural skeleton
set_writer_unsupported_claim_count — notes rejected for unsupported attribute claims
set_writer_ms                    — writer stage elapsed ms
```

### Remaining limitations

- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- LLM reviewer gate not built (PR #262) — set-writer notes are not re-reviewed.
- Set-writer uses primary model only (no retry cascade for the writer itself); the existing `build_reasons_with_retry` three-pass cascade is used as fallback on writer failure.

### Supabase SQL: No

### Test counts

```
test_set_level_writer.py:     56 tests, all pass (new)
test_card_curator.py:         51 tests, all pass (unchanged — PR #260)
test_evidence_dossier.py:     54 tests, all pass (unchanged — PR #259)
test_parallel_retrieval.py:   28 tests, all pass (unchanged — PR #258)
test_sla_card_cap.py:         64 tests, all pass (unchanged — PR #257)
test_evidence_quality_v3.py:  53 tests, all pass (unchanged)
test_evidence_quality_v4.py:  37 tests, all pass (unchanged)
test_evidence_quality_v5.py:  37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — PR #260: Card Role + Curated Set Ranker v1

**Status: MERGE-READY** — 51 new card-curator tests pass; 54 PR #259 dossier tests pass; 28 PR #258 tests pass; 64 PR #257 SLA tests pass; 19 pre-existing pydantic env failures remain (unrelated)

### What was built

Card Role + Curated Set Ranker v1 — deterministic, typed internal substrate for AI Concierge v2 card selection. No UI, SQL, LLM calls, provider additions, or visible behavior changes.

**Problem**: AI Concierge v2 had no typed layer between ranked verified candidates and future note writing (PR #261). The card set could feel random or repetitive because roles, evidence richness, and modifier confirmation were not formally computed or used for ordering. PR #260 creates this substrate.

**Changes made**:

1. **`backend/app/concierge/card_curator.py`** (new):
   - `CardRole` string constants: `best_overall`, `strongest_query_match`, `modifier_confirmed`, `evidence_rich`, `distinctive_theme`, `geographic_fit`, `safe_popular_fallback`, `interesting_but_weaker`, `low_evidence_holdback`.
   - `CardCurationSignals`: 12 deterministic signals from dossier — concept_fit, geo_fit, modifier_fit, source_confidence, theme_count, has_place_details, has_explicit_modifier_evidence, has_listing_context_only, negative_caveat_count, evidence_gap_count, diversity_key, original_rank_index.
   - `CuratedCard`: entity + rank_score + dossier + role + curation_score + signals + reasons + original_rank_index. No visible card payload fields.
   - `CuratedSetResult`: curated_cards + role_counts + source_confidence_counts + low_evidence_holdback_count + modifier_confirmed_count + evidence_rich_count + reordered_count + input_count + output_count + `as_telemetry_dict()`.
   - `_build_curation_signals()`: extracts signals from PlaceEvidenceDossier. Protected against bad dossier with per-card try/except.
   - `_assign_role()`: deterministic 9-priority role assignment. No category hardcoding.
   - `_compute_curation_score()`: concept_fit=0.50 dominant; theme contribution capped at 0.04 (requires place_details).
   - `curate_cards()`: processes ranked + dossiers; assigns roles; conservatively reorders within first_card_limit. Never raises — bad dossiers fall back to ROLE_INTERESTING_BUT_WEAKER.

2. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Step 5.7 added after Step 5.6 dossier build: calls `curate_cards`; applies reordered cap if `reordered_count > 0`; falls back to original ranked order on any exception.
   - `_log_semantic_turn` gains optional `curator_telemetry` parameter.
   - Curator telemetry emitted as separate log line `semantic_retrieval_v1.curated_set_telemetry`.

3. **`backend/tests/test_card_curator.py`** (new, 51 tests):
   - All 17 required test scenarios from PR #260 spec.
   - `TestRoleAssignmentHighConceptFit` — best_overall/strongest_query_match assignment.
   - `TestModifierConfirmedRole` — modifier_confirmed requires confirmed or explicit evidence.
   - `TestNoModifierConfirmedFromAddress` — address alone cannot create modifier_confirmed.
   - `TestListingContextLowerTrust` — listing_context entries are lower-trust; explicit enrichment wins.
   - `TestReviewCountAloneInsufficientForHighRoles` — review count is card stat, not theme.
   - `TestPlaceDetailsEnrichmentCreatesRichRoles` — place_details + themes → evidence_rich/distinctive_theme.
   - `TestLowEvidenceCardsPreserved` — no cards dropped; low evidence → safe_popular_fallback or low_evidence_holdback.
   - `TestCardCapPreserved` — output count never exceeds input.
   - `TestCuratorNeverMintsCards` — CuratedCard has no addable/display/note/gv fields; entity is same object.
   - `TestCuratorFallbackPath` — bad dossier handled gracefully; integration fallback preserves original order.
   - `TestDeterministicOrdering` — stable output across repeated runs.
   - `TestConservativeReorder` — clearly stronger card can move up within cap.
   - `TestNoBroadReorderByThemeCount` — low concept-fit card cannot jump above high concept via theme count.
   - `TestTelemetryCounts` — role_counts, confidence_counts, reordered_count all accurate.
   - `TestPR257InvariantUnchanged` — fallback_note_visible_count=0 structurally unchanged.
   - `TestPR258InvariantsUnchanged` — parallel_retrieval contracts unchanged.
   - `TestPR259DossierContractsUnchanged` — dossier contracts unchanged.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (structural invariant from PR #257 — unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (structural — unchanged)
- View/patio/waterfront themes require explicit enrichment evidence (PR #259 invariant — unchanged)
- Internal evidence gaps never surface as visible note prose (PR #259 invariant — unchanged)
- Curator failure cannot block card return (new invariant — integration try/except)
- Role labels are internal only — never surfaced in visible card payload or user-facing text
- No SQL, no new providers, no UI changes, no LLM calls, no category-specific keyword patches

### Role assignment rules (deterministic, generic)

1. `best_overall` — concept_fit >= 0.8 AND source_confidence == "strong"
2. `strongest_query_match` — concept_fit >= 0.7
3. `modifier_confirmed` — (modifier_fit == "confirmed" OR has_explicit_modifier_evidence) AND concept_fit >= 0.4 AND NOT listing_context_only
4. `distinctive_theme` — has_place_details AND theme_count >= 3 AND concept_fit >= 0.5
5. `evidence_rich` — has_place_details AND theme_count >= 1 AND concept_fit >= 0.4
6. `geographic_fit` — geo_fit >= 0.7 AND concept_fit >= 0.3
7. `safe_popular_fallback` — concept_fit >= 0.25
8. `low_evidence_holdback` — is_minimal OR concept_fit < 0.25
9. `interesting_but_weaker` — catch-all

### Curation score formula

```
score = 0.50 * concept_fit
      + 0.20 * geo_fit
      + 0.15 * (1 if modifier_confirmed and not listing_context_only else 0)
      + 0.08 * (conf_strong=1.0 | conf_mixed=0.5 | conf_weak=0.0)
      + min(theme_count/5.0, 1.0) * 0.04  (only if has_place_details)
      - min(negative_caveat_count * 0.03, 0.09)
      - min(evidence_gap_count * 0.02, 0.06)
```

concept_fit dominance ensures no low-concept card can overrank a strong-concept card via theme count alone (theme max = 0.04 vs concept_fit 0.50 weight).

### Telemetry added (PR #260)

Emitted as `semantic_retrieval_v1.curated_set_telemetry` structured log:
```
curated_input_count           — cards fed to curator
curated_output_count          — cards after curator (should equal input)
curated_role_counts           — {role: count} per assignment
curated_confidence_counts     — {strong/mixed/weak: count}
curated_reordered_count       — positions changed from original order
curated_modifier_confirmed_count
curated_evidence_rich_count   — evidence_rich + distinctive_theme combined
curated_low_evidence_holdback_count
curated_fallback_to_original_order — True if curator raised
curated_ms                    — curator stage elapsed ms
```

### Remaining limitations

- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- Set-level writer not built (PR #261 will use `CuratedSetResult` as input substrate).
- LLM reviewer gate not built (PR #262).
- Hard cutoff interrupt of in-flight HTTP calls: deferred (same as PR #258).

### Supabase SQL: No

### Test counts

```
test_card_curator.py:         51 tests, all pass (new)
test_evidence_dossier.py:     54 tests, all pass (unchanged — PR #259)
test_parallel_retrieval.py:   28 tests, all pass (unchanged — PR #258)
test_sla_card_cap.py:         64 tests, all pass (unchanged — PR #257)
test_evidence_quality_v3.py:  53 tests, all pass (unchanged)
test_evidence_quality_v4.py:  37 tests, all pass (unchanged)
test_evidence_quality_v5.py:  37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — PR #259: Evidence Dossier v1 + review/theme extraction

**Status: MERGE-READY** — 54 new evidence-dossier tests pass; 28 PR #258 tests pass; 64 PR #257 SLA tests pass; 19 pre-existing pydantic env failures remain (unrelated)

### What was built

Evidence Dossier v1 — typed, structured place intelligence for top Concierge cards. No UI, SQL, provider additions, or frontend changes.

**Problem**: AI Concierge note generation received thin name/category/rating/address evidence. PR #259 normalizes available evidence from Google Places identity + Place Details enrichment into a compact, tested PlaceEvidenceDossier contract for use by the PR #260+ writer/reviewer. The dossier is internal reasoning context only — never exposed as visible prose.

**Changes made**:

1. **`backend/app/concierge/evidence_dossier.py`** (new):
   - `QueryFitEvidence`: concept_fit, modifier_fit, geo_fit, vibe_fit from RankScore + ExperienceFrame.
   - `ProviderEvidenceItem`: source + facts list. Only "google_places" and "google_place_details" populated today (no Yelp/Foursquare stubs — honest absence).
   - `ReviewThemeEvidence`: food_drink, ambiance, service, crowd_noise, view_patio_waterfront, occasion_fit, negative_caveats. View/outdoor themes populated ONLY from explicit enrichment evidence (amenity flags, editorial/review text) or entity name listing context. NOT from formatted_address.
   - `PlaceEvidenceDossier`: full typed contract. `is_minimal=True` when built from critical-path data only.
   - `EvidenceDossierTelemetry`: aggregated turn-level telemetry with `as_log_dict()`.
   - `extract_review_themes()`: deterministic conservative keyword matching from enrichment data. No LLM. No review-count reasoning.
   - `build_place_evidence_dossier()`: builds one dossier from entity + frame + rank_score + optional enrichment.
   - `build_dossiers_for_ranked_cards()`: builds top-N dossiers with deadline/budget gating. Minimal dossiers (no enrichment lookup) when remaining_ms < 100ms.
   - `get_dossier_telemetry()`: aggregates dossier batch into `EvidenceDossierTelemetry`.

2. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Step 5.6 added after enrichment, before evidence bundles: calls `build_dossiers_for_ranked_cards` + `get_dossier_telemetry`.
   - `_log_semantic_turn` gains optional `dossier_telemetry` parameter.
   - Dossier telemetry emitted as a separate structured log line (`semantic_retrieval_v1.dossier_telemetry`) to preserve existing log parsers.

3. **`backend/tests/test_evidence_dossier.py`** (new, 54 tests):
   - All 13 required test scenarios from PR #259 spec.
   - `TestDossierBuildsPerCard` — one dossier per top card; minimal when no enrichment; required fields present.
   - `TestDossierCannotMintCards` — no card/result/verified_place fields; Google facts readable but not card-minting.
   - `TestPlaceDetailsEnrichmentInProviderEvidence` — enrichment creates place_details bucket; upgrades confidence; not minimal.
   - `TestMissingEnrichmentMinimalDossier` — is_minimal=True; WEAK confidence for low fit; MIXED for high fit; gap recorded.
   - `TestReviewThemeExtraction` — review count never produces themes; amenity flags → explicit themes; editorial + snippets → themes.
   - `TestViewOutdoorThemeExplicitOnly` — address "Riverwalk" does NOT → theme; outdoor_seating=True → explicit theme; name token → listing_context only.
   - `TestInternalEvidenceGapsNotVisible` — gaps stored internally only; not in themes, not in provider facts.
   - `TestDossierDeadlineBudgetGating` — low budget → minimal; sufficient budget → enrichment used; None deadline → enrichment used.
   - `TestDossierTelemetry` — built_count, confidence_counts, place_details_count, minimal_count, skipped_count, review_theme_counts_per_card, as_log_dict keys.
   - `TestCardCapUnchanged` — default first_card_limit = 6 unchanged.
   - `TestFallbackNoteInvariant` — dossier has no note/reason/display_why fields.
   - `TestGoogleVerificationInvariantsUnchanged` — OPERATIONAL status in facts; no card minting from enrichment; no non-Google sources.
   - `TestExistingContractsUnchanged` — PR #257, #258, #259 contracts all importable; PR #258 invariants hold.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (structural invariant from PR #257 — unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (structural — unchanged)
- View/patio/waterfront themes require explicit enrichment evidence (new invariant)
- Internal evidence gaps never surface as visible note prose (new invariant)
- No SQL, no new providers, no UI changes

### Telemetry added (PR #259)

Emitted as `semantic_retrieval_v1.dossier_telemetry` structured log:
```
dossier_built_count                  — dossiers built this turn
dossier_confidence_counts            — {strong/mixed/weak: count}
dossier_source_counts                — evidence facts per source
dossier_theme_counts                 — theme signals per theme type
dossier_with_place_details_count     — cards with place_details bucket
dossier_minimal_count                — minimal dossiers (no enrichment)
dossier_skipped_due_to_budget_count  — skipped enrichment lookups (low budget)
```
Plus per-card fields on `EvidenceDossierTelemetry`:
```
review_theme_count_per_card          — theme count per dossier
evidence_sources_used_per_card       — source list per dossier
```

### Remaining limitations

- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- Dossier not yet wired to note generation (PR #260 will use dossier as writer input).
- Card roles / curated ranker not built (PR #260).
- Set-level writer not built (PR #261).
- LLM reviewer gate not built (PR #262).
- Hard cutoff interrupt of in-flight HTTP calls: deferred (same as PR #258).

### Supabase SQL: No

### Test counts

```
test_evidence_dossier.py:     54 tests, all pass (new)
test_parallel_retrieval.py:   28 tests, all pass (unchanged — PR #258)
test_sla_card_cap.py:         64 tests, all pass (unchanged — PR #257)
test_evidence_quality_v3.py:  53 tests, all pass (unchanged)
test_evidence_quality_v4.py:  37 tests, all pass (unchanged)
test_evidence_quality_v5.py:  37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — PR #258: Parallel retrieval + critical/non-critical path split

**Status: MERGE-READY** — 28 new parallel-retrieval tests pass; 64 PR #257 SLA tests pass; 19 pre-existing pydantic env failures remain (unrelated)

### What was built

Critical vs non-critical retrieval stage separation with deadline propagation. No UI, SQL, or provider additions.

**Problem**: Google Text Search fanout used a fixed timeout unaware of the SLA deadline. Place Details enrichment was silently never running (pre-existing NameError bug: `_api_key` vs `api_key` in `_run_pipeline`). No formal critical/non-critical separation existed; slow or failing enrichment could in principle delay the response.

**Changes made**:

1. **`backend/app/concierge/parallel_retrieval.py`** (new):
   - Formalizes critical vs non-critical path separation from v2 amendment §5.
   - `CriticalPathResult`: wraps Google Text Search provider results + timing + timeout count.
   - `NonCriticalEnrichmentResult`: wraps enrichment map + timing + used/skipped counts + skip reason.
   - `ParallelRetrievalResult`: combines both with all 11 PR #258 telemetry fields.
   - `run_critical_google_fanout(queries, api_key, deadline, timeout)`: bounds effective per-call timeout to `min(timeout, remaining_deadline_s - 0.2s)`. Returns empty failure result immediately when remaining < 0.5 s.
   - `run_non_critical_enrichment(entities, api_key, deadline, budget_n)`: skips `enrich_top_cards` entirely when `deadline.budget_for_enrichment_s() == 0.0`. Spreads remaining budget evenly across batch as per-card timeout. Catches all enrichment errors — never propagates.

2. **`backend/app/concierge/deadline_manager.py`** (modified):
   - `budget_for_enrichment_s(reserve_ms=500)`: returns 0.0 when past soft ceiling or when remaining budget ≤ reserve_ms; otherwise returns available seconds. Protects note generation + assembly headroom downstream.

3. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Step 3: replaced `execute_fanout` with `run_critical_google_fanout` — deadline-bounded.
   - Step 5.5: replaced `enrich_top_cards` (which was silently failing due to `_api_key` NameError) with `run_non_critical_enrichment` using correct `api_key` parameter. Enrichment now actually runs when budget allows.
   - Captures `critical_path_ms` (total time through frame + plan + fanout + entity + rank) after step 5.
   - Captures `remaining_budget_before_reasoning_ms` before step 7 (note generation).
   - `_log_semantic_turn` extended with 11 new PR #258 telemetry fields (listed below).

4. **`backend/tests/test_parallel_retrieval.py`** (new, 28 tests):
   - Covers all 10 required test scenarios from PR #258 spec.
   - `TestNonCriticalSkippedPastSoftCeiling` — enrichment skipped past soft ceiling; skipped on budget exhausted; elapsed_ms is small (fast exit).
   - `TestCriticalGoogleRetrieval` — fanout calls execute_fanout; bails when budget < 0.5s; timeout_count tracks failures.
   - `TestEnrichmentCannotMintCards` — result types have no card/identity fields; evidence-only structure enforced.
   - `TestDeadlinePropagationToFanout` — effective timeout bounded by remaining budget; never inflated beyond it.
   - `TestEnrichmentSkippedOnLowBudget` — skipped when budget exactly 0; not skipped when budget sufficient.
   - `TestEnrichmentWithBudget` — enrichment map keyed by place_id; failure returns empty map (no exception).
   - `TestFirstResponseCardCap` — card cap is not applied in parallel_retrieval layer; default remains 6.
   - `TestNoVisibleFallbackNotes` — enrichment/critical result types have no note/reason fields.
   - `TestTelemetryFields` — all 11 ParallelRetrievalResult fields present; timeout_count accurate; skip_count accurate.
   - `TestDeadlineBudgetForEnrichment` — 0 past soft ceiling; 0 when remaining < reserve; positive when sufficient; shrinks over time.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (structural invariant from PR #257 — unchanged)
- `deterministic_visible_count` always 0 (unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- Card cap: default 6, range 5–7 (unchanged)
- Non-Google enrichment cannot mint addable cards (structural: only critical Google path produces cards)
- No SQL, no new providers, no UI changes

### Telemetry added (PR #258)

```
critical_path_ms                       — total time through frame+plan+fanout+entity+rank
non_critical_enrichment_ms             — time for place_details enrichment stage
provider_fanout_ms                     — time for Google Text Search fanout only
provider_timeout_counts                — provider queries that errored/timed out
provider_skipped_due_to_budget_counts  — non-critical cards skipped due to budget
google_critical_success                — at least one Google query returned places
google_critical_candidate_count        — total raw places from successful queries
google_verified_count                  — verified entity count post-entity layer
non_critical_enrichment_used_count     — enrichment results actually used
non_critical_enrichment_skipped_count  — enrichment cards skipped/failed
remaining_budget_before_reasoning_ms   — deadline budget just before note generation
```

### Remaining limitations

- `more_options_cursor_present` is always `False` — cursor lives in router layer (PR #263).
- Evidence Dossier not yet implemented (PR #259).
- Hard cutoff interrupt of in-flight HTTP calls: critical fanout timeout is now deadline-bounded (this PR), but a true kill signal for already-running threads requires OS-level interrupt — deferred.

### Supabase SQL: No

### Test counts

```
test_parallel_retrieval.py:   28 tests, all pass (new)
test_sla_card_cap.py:         64 tests, all pass (unchanged — 5 added in PR #257 batch)
test_evidence_quality_v3.py:  53 tests, all pass (unchanged)
test_evidence_quality_v4.py:  37 tests, all pass (unchanged)
test_evidence_quality_v5.py:  37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — PR #257: SLA + first-response card cap + no-visible-fallback-note contract

**Status: MERGE-READY** — 59 new SLA/cap tests pass; 127 prior quality tests pass; 5 pre-existing pydantic env failures remain (unrelated)

### What was built

Foundation slice of the v2 amendment architecture. No provider, UI, or SQL changes.

**Problem**: AI Concierge search had no hard latency boundary, no limit on first-response card count, and no enforcement that timed-out note generation returns cards without notes (rather than blocking or returning fallback prose).

**Changes made**:

1. **`backend/app/concierge/deadline_manager.py`** (new):
   - `SLAConfig` dataclass: target_ms=3000, soft_ceiling_ms=4000, hard_cutoff_ms=6000, first_card_limit=6, range 5–7.
   - `RequestDeadline`: tracks pipeline start time, exposes `elapsed_ms()`, `remaining_ms()`, `is_past_soft_ceiling()`, `is_past_hard_cutoff()`, `budget_for_note_generation_s()`, and per-stage timing.
   - `clamp_first_card_limit(n)`: clamps to [5, 7].
   - `DEFAULT_SLA` singleton for pipeline use.

2. **`backend/app/concierge/semantic_retrieval.py`** (modified):
   - Creates `RequestDeadline(t_start=t_pipeline_start)` at pipeline start.
   - Before note generation: checks `deadline.budget_for_note_generation_s()`. If 0.0 (past soft ceiling), skips LLM entirely and sets `note_generation_timed_out=True`. Cards still assemble without notes (`reason_validated=False`).
   - When timed out: all trust-gate-passing cards are included without notes (frontend hides note block via `display_why_validated=False`).
   - Normal path: existing behavior (include only validated-note cards; exclude unvalidated).
   - Post-trust-gate: applies `first_card_limit=6` cap (`cards = cards[:first_card_limit]`). Ranked pool of up to 8 remains available for continuation.
   - `_log_semantic_turn` extended with 12 new SLA telemetry fields: `turn_total_ms`, `target_response_ms`, `soft_ceiling_ms`, `hard_cutoff_ms`, `first_return_card_limit`, `pre_cap_card_count`, `visible_note_count`, `hidden_note_count`, `fallback_note_visible_count` (always 0), `note_generation_timed_out`, `cards_without_notes`, `more_options_cursor_present`.

3. **`backend/app/concierge/batched_reason_builder.py`** (modified):
   - `build_reasons_with_retry` gains optional `timeout_s: Optional[float] = None`. When provided, effective timeout = `min(timeout_s, configured_ceiling)`. Caller passes `deadline.budget_for_note_generation_s()`.

4. **`backend/tests/test_sla_card_cap.py`** (new, 59 tests):
   - `TestSLAConfig`, `TestClampFirstCardLimit`, `TestRequestDeadline` — deadline helper unit tests.
   - `TestFirstResponseCardCap` — card cap is 6 default; 5/7 allowed; outside clamped; upstream pool unaffected.
   - `TestDeadlineEnforcesNoteGeneration` — past soft ceiling → budget=0; timed-out cards have validated=False.
   - `TestNoVisibleFallbackNote` — fallback_note_visible_count invariant; note block hidden when validated=False.
   - `TestGoogleVerificationPreserved` — trust gate requirements unchanged; cap applied after gate.
   - `TestSLATelemetryFields` — all 12 required telemetry fields present; invariants hold.
   - `TestBuildReasonsWithRetryTimeout` — optional timeout_s accepted correctly.

### Hard contracts preserved

- `fallback_note_visible_count` always 0 (structural: no deterministic text ever has `reason_validated=True`)
- `deterministic_visible_count` always 0 (existing invariant, unchanged)
- Google verification trust gate: place_id + OPERATIONAL + maps_uri required (unchanged)
- No SQL, no provider changes, no UI changes
- Ranked pool size stays at 8 for continuation/more-options

### Remaining limitations

- `more_options_cursor_present` is always `False` in this PR — cursor lives in the router layer (addressed in PR #263).
- Parallel retrieval critical/non-critical split implemented in PR #258.
- Evidence Dossier not yet implemented (PR #259).
- Hard cutoff guard (kill at 6000ms) is soft-enforced via soft_ceiling skip; deadline-bounded fanout timeout implemented in PR #258.

### Supabase SQL: No

### Test counts

```
test_sla_card_cap.py:         59 tests, all pass (new)
test_evidence_quality_v3.py:  53 tests, all pass (unchanged)
test_evidence_quality_v4.py:  37 tests, all pass (unchanged)
test_evidence_quality_v5.py:  37 tests, all pass (unchanged)
```

---

## Previous change (2026-05-06) — EvidencePack v5 (arch alignment): Concept-generic prompt + unseen-concept tests

**Status: MERGE-READY** — 164 concierge tests pass, 5 pre-existing pydantic env failures remain (unrelated)

### Architecture alignment: concept-generic production code (no category shortcuts)

After v5 was initially opened as PR #255, a second pass ensured no category-specific language remained in production code.

**Problem**: Production prompt contained "For IZAKAYA queries" and "For VIEW queries (e.g., taprooms with a view)" — hard-coded category branches that must not exist in a system whose semantic frame extraction is designed to work for any venue concept.

**Changes made** (`batched_reason_builder.py`):
- Replaced category-specific guidance ("For IZAKAYA queries"/"For VIEW queries") with generic semantic-frame language covering any concept or unverifiable modifier
- `UNVERIFIABLE MODIFIER queries` section: handles scenic views, waterfront, garden, quiet, and any future attribute that cannot be structurally confirmed
- `CONCEPT/SPECIALTY queries` section: uses name/menu/format/style clues from the evidence — works for izakaya, kaiseki, listening bar, tea house, natural wine bar, etc.
- Geo-hint listing-context guidance generalized: no Riverwalk/riverfront hardcoding; works for any `geo_h` term
- Repair section generalized: regex extracts `unsupported_attribute_claim:TERM` and uses `TERM` in the repair hint, not "riverwalk"

**Modifier telemetry term sets** (`semantic_retrieval.py`): Added `_WATER_GEO_MODIFIER_TERMS`, `_SCENIC_VIEW_MODIFIER_TERMS`, `_GARDEN_MODIFIER_TERMS` — clearly commented as telemetry-only, not retrieval eligibility gates or ranking signals. Generic fallback for unknown modifiers uses simple word-token match (no `re` import needed).

**Unseen-concept tests** (`test_evidence_quality_v5.py`): Added `TestUnseenConceptGenericRules` with 8 tests proving quality rules work for venue types not seen during development:
- `test_kaiseki_review_volume_rejected` — review volume rejected for kaiseki
- `test_listening_bar_rating_lead_rejected` — highest-rated rejected for listening bars
- `test_natural_wine_bar_engagement_rejected` — high engagement rejected for wine bars
- `test_kaiseki_specialty_note_passes` — concept/specialty note passes quality gate
- `test_listening_bar_concept_note_passes` — format/concept note passes quality gate
- `test_tea_house_garden_modifier_note_passes` — honest garden caveat passes quality gate
- `test_water_modifier_status_for_natural_wine_bar` — Riverwalk wine bar → confirmed_listing_context; inland wine bar → unknown
- `test_garden_modifier_status_for_tea_house` — garden modifier → none/unknown (correctly uses ambiguity_flags path)

No retrieval/routing/ranking keyword patching was introduced. Modifier telemetry term sets are observability-only.

### Total test count: 164 (37 v5 tests = 29 original + 8 unseen-concept)

---

## Previous change (2026-05-06) — EvidencePack v5: Tighter rating/review rejection + modifier telemetry fix

**Status: Superseded by arch-alignment pass above**

### Problem solved (Level 2 production note quality failures on PR #252 logs)

Post-PR #252 production logs showed remaining failures:
1. Rating/review-primary notes still passed when phrased indirectly (e.g., "notably high ratings", "draws consistently high engagement", "strongest review volume", "smaller review count", "steady review volume", "lightest review footprint")
2. `modifier_status='none'` logged for all "breweries near the river" cards including Northman (should be `confirmed_listing_context` for Northman, `unknown` for others)
3. "taprooms with a view" notes not always addressing the view request honestly
4. "izakayas" notes still sometimes using review volume instead of concept/menu/style fit

Root causes fixed:
1. `_QUALITY_THIN_RE` did not cover indirect rating phrasings — added 11 new patterns: `notably high ratings`, `high engagement`, `review volume`, `review footprint`, `review count`, `feedback volume`, `steady review`, `lightest review`, `carries review`, `strongest review`, `smaller review`
2. `_log_per_card_notes` in `semantic_retrieval.py` only checked `location_modifiers` (empty for geo-hint queries like "breweries near the river"); now checks `geography_hints` too and maps entity name/address to `confirmed_listing_context` / `confirmed_address_context` / `unknown`
3. LLM prompt updated with: explicit view guidance (confirmed or deny honestly), izakaya concept/menu/style anchors, expanded anti-pattern list covering all new indirect phrasings
4. Harness v2 mock note updated: "tap quality and review volume are well-supported" → "tap selection and Bourbon County program are well-documented" (now complies with new gate)

### What was built

**Strengthened `_QUALITY_THIN_RE`** (`batched_reason_builder.py`): Added 11 new rating/review patterns that cover indirect phrasings from PR #252 production logs.

**Improved prompt guidance** (`batched_reason_builder.py`): Extended anti-pattern list; added view-query guidance (confirm or deny explicitly); added izakaya guidance (use name/menu/category/style clues, not review rank).

**Fixed modifier_status telemetry** (`semantic_retrieval.py`): `_log_per_card_notes` now checks both `location_modifiers` and `geography_hints`; maps entity name/address against river/view term sets to produce `confirmed_listing_context`, `confirmed_address_context`, or `unknown` (not `none`) for modifier queries.

**Harness v5** (`tests/evidence_harness_v5.py`): New harness with:
- Exact visible notes printed for all three queries
- PR #252 bad-note rejection proof section (all 6 exact failing notes rejected)
- Northman modifier_status=confirmed_listing_context asserted
- Taproom-view notes checked for view-honest handling
- Izakaya notes checked for concept/menu/style (not review rank)

**Tests v5** (`tests/test_evidence_quality_v5.py`): 37 tests (29 original + 8 unseen-concept) across 6 classes:
- `TestPR252BadNoteRejection` — 6 tests: exact PR #252 failing notes all rejected
- `TestRatingPrimaryV5` — 7 tests: new indirect phrasings rejected, good differentiators pass
- `TestModifierTelemetryV5` — 5 tests: Northman=confirmed_listing_context, regular=unknown, izakaya=none
- `TestTaproomViewQualityV5` — 3 tests: 8/8 validated, no rating-primary, all notes address view
- `TestIzakayaQualityV5` — 3 tests: 8/8 validated, no review-volume notes, venue_head recognized
- `TestHarnessV5Integration` — 5 tests: full end-to-end for all three queries + PR #252 rejection
- `TestUnseenConceptGenericRules` — 8 tests: proves quality gates work for kaiseki, listening bars, tea houses, natural wine bars

**Updated harness v2 mock note** (`tests/evidence_harness_v2.py`): Taproom-with-view card 1 note updated to avoid "review volume" (now complies with stricter gate).

### Files changed

- `backend/app/concierge/batched_reason_builder.py` — 11 new `_QUALITY_THIN_RE` patterns; expanded anti-pattern list in prompt; view and izakaya repair guidance added
- `backend/app/concierge/semantic_retrieval.py` — `_log_per_card_notes`: checks geography_hints; entity name/address → confirmed_listing_context/confirmed_address_context/unknown
- `backend/tests/evidence_harness_v2.py` — 1 mock note updated (review volume → tap selection/program)
- `backend/tests/evidence_harness_v5.py` — New v5 harness (24/24 validated, PR #252 bad-note proof)
- `backend/tests/test_evidence_quality_v5.py` — 29 new tests

### Test results

```
test_evidence_quality_v3.py:       53 tests, all pass (unchanged)
test_evidence_quality_v4.py:       37 tests, all pass (unchanged)
test_evidence_quality_v5.py:       37 tests, all pass (29 original + 8 unseen-concept)
test_reasoning_reliability_v2.py:  38 tests pass (5 pre-existing pydantic env failures)
evidence_harness_v3.py:           19/19 validated STRICT (unchanged)
evidence_harness_v4.py:           24/24 validated STRICT (unchanged)
evidence_harness_v5.py:           24/24 validated STRICT (new)
  Table 1: 8/8 validated (Northman confirmed_listing_context, non-river=unknown)
  Table 2: 8/8 validated (all notes address view honestly, no rating-primary)
  Table 3: 8/8 validated (izakaya concept/menu/style anchors, no review volume)
  PR #252 bad notes: all 6 rejected ✓
frontend tests (concierge-renderers + trust-contract): 45/45 pass
```

### Production contract verification

| Query | Result |
|---|---|
| breweries near the river | 8/8 accepted, Northman modifier_status=confirmed_listing_context, non-river=unknown, no rating-primary notes |
| taprooms with a view | 8/8 accepted, every note addresses view as confirmed or explicitly denied, no rating-primary notes |
| izakayas | 8/8 accepted, venue_head_recognized=True, notes use concept/menu/style anchors |
| PR #252 bad notes | All 6 indirect phrasings rejected by quality gate |

### Hard contracts preserved

- Cards with `validated=False` excluded from response (never shown)
- `deterministic_visible_count` always 0 in telemetry
- No NOTE OMITTED / placeholder in success path
- No rating-lead or pure-caveat-only notes
- per_card_notes production logging preserved and improved
- No legacy whyPick fallback
- Izakaya venue-head recognition preserved
- Northman Riverwalk safe-evidence preserved (not weakened)

### Supabase SQL: No

### Remaining limitations

- "view" as a user modifier goes into `ambiguity_flags` in the frame (not `location_modifiers` or `geography_hints`), so modifier_status for "taprooms with a view" remains "none" per card — this is honest, since Google data cannot structurally verify scenic views
- New `review volume` pattern is broad; if a future editorial note uses "review volume" as secondary context, it will be rejected. Notes should avoid the phrase entirely.

---

### Problem solved (Level 3 production blockers on PR #251 logs)

Production Railway logs showed (post-PR #251):
- `breweries near the river`: 7/8 accepted, 1 card omitted — "The Northman Beer & Cider Garden on the Riverwalk" rejected because "Riverwalk" in its name triggered the unsupported-attribute validator
- `taprooms with a view`: notes were rating/review-primary ("highest-rated", "second-largest review base", etc.)
- `izakayas`: notes were rating/review-primary despite venue_head_recognized=True fix

Root causes fixed:
1. `_evidence_supports_claim` checked only `structured_facts` — not the entity's verified Google name/address. So "Riverwalk" in the verified name was not recognized as listing-context evidence
2. `lake\s*view` in `_UNSUPPORTED_ATTRIBUTE_RE` falsely matched "Lakeview" (Chicago neighborhood), blocking valid notes
3. Plural scenic terms (`river views`, `beautiful views`) were not caught because trailing `\b` blocks plural forms → added `s?` to all view patterns
4. Rating/review-count as primary differentiator was not in quality gate — added patterns for "highest-rated", "review base", "solid mid-tier", "established reputation", "consistent crowd draw", "strong flagship choice"
5. Evidence adequacy: `has_strong_name_match and high_review_count → STRONG` was wrong (rating+reviews is NOT a concrete differentiator) — only `enrichment_facts` upgrades to STRONG now
6. Retry/repair prompt lacked Riverwalk-specific guidance for rejected cards
7. LLM prompt lacked THREE-WAY DISTINCTION for geo/river modifier (listing context / verified feature / unknown)
8. Harness v3 had only 3-card izakaya table and no Northman fixture; v4 adds 8-card scenarios for all queries

### What was built

**Riverwalk safe-evidence** (`reason_validator.py`): `_evidence_supports_claim` now checks entity name and address (word-boundary tokenized). "Riverwalk" in the verified Google name supports a listing-context mention. "river view" / "waterfront seating" are still blocked (tokens not in name). Fixed `lake\s*view` → `lake\s+view` (no more "Lakeview" neighborhood false match). Added `s?` to plural view patterns.

**New boilerplate patterns** (`reason_validator.py`): Added "consistent crowd draw", "strong flagship choice", "established reputation" to `_GENERIC_BOILERPLATE_RE`.

**Rating-primary quality gate** (`batched_reason_builder.py`): Extended `_QUALITY_THIN_RE` with: `highest-rated`, `most-reviewed`, `review base`, `smallest review`, `solid mid-tier`, `strong on volume`, `consistent crowd draw`, `strong flagship choice`, `established reputation`, `volume of feedback`.

**Updated prompt** (`batched_reason_builder.py`): Added THREE-WAY DISTINCTION for geo/river modifier (listing context / verified / unknown). Added RIVERWALK REPAIR guidance in retry pass. Explicit anti-pattern for rating/review as primary differentiator.

**Evidence adequacy v4** (`ranker.py`): Removed `has_strong_name_match and high_review_count → STRONG`. Only `enrichment_facts` (editorial, amenity, review snippet) upgrades to STRONG. Added `modifier_in_name` check — entity name/address contains a user-requested modifier term → OK.

**Harness v4** (`tests/evidence_harness_v4.py`): Complete rewrite with 8-card scenarios:
- Table 1: "breweries near the river" — 8 cards including Northman (card 4), 8/8 validated
- Table 2: "taprooms with a view" — 8 cards with enrichment, 8/8 validated, no rating-primary notes
- Table 3: "izakayas" — 8 cards with editorial, 8/8 validated, venue_head_recognized=True
- New columns: `user_modifier`, `modifier_status` (confirmed_listing_context / unknown / none)
- Per-card `_compute_modifier_status` function with river/view term lookup

**New tests** (`tests/test_evidence_quality_v4.py`): 37 new tests:
- `TestRiverwalkSafeEvidence` — 6 tests: entity-name support, listing note validates, scenic claims rejected, batch orchestrator test
- `TestLakeviewNeighborhood` — 2 tests: neighborhood name allowed, "lake view" (with space) still blocked
- `TestRatingPrimaryRejection` — 9 tests: highest-rated, most-reviewed, review-base, solid-mid-tier, established-reputation, strong-flagship rejected; specific differentiator passes; rating as secondary passes
- `TestEvidenceAdequacyV4` — 6 tests: high subtype_fit+reviews = OK (not STRONG); editorial/amenity = STRONG; modifier-in-name upgrades
- `TestModifierEvidenceContract` — 5 tests: Northman=confirmed_listing_context, regular brewery=unknown, no-modifier=none
- `TestHarnessV4Integration` — 9 tests: 8/8 for all tables, Northman validated, no scenic claims, izakaya venue_head

**Updated test** (`tests/test_evidence_quality_v3.py`): Renamed `test_strong_with_high_subtype_and_reviews` → `test_high_subtype_and_reviews_without_enrichment_is_ok` (now expects OK, not STRONG).

---

### Files changed

- `backend/app/concierge/reason_validator.py` — `_evidence_supports_claim`: entity name/address check; `lake\s*view` → `lake\s+view`; plural `s?` for view patterns; boilerplate patterns added
- `backend/app/concierge/batched_reason_builder.py` — Rating-primary patterns in `_QUALITY_THIN_RE`; THREE-WAY geo/river prompt; RIVERWALK REPAIR hint in retry; anti-pattern list updated
- `backend/app/concierge/ranker.py` — Evidence adequacy: `enrichment_facts` only upgrades to STRONG; added `modifier_in_name` path for OK; removed `high_subtype+reviews → STRONG`
- `backend/tests/test_evidence_quality_v3.py` — Updated one test expectation (STRONG → OK)
- `backend/tests/evidence_harness_v4.py` — New harness with Northman, 8-card izakaya, modifier_status columns
- `backend/tests/test_evidence_quality_v4.py` — 37 new tests across 6 test classes

### Test results

```
test_evidence_quality_v3.py:        53 tests, all pass (unchanged count)
test_evidence_quality_v4.py:        37 tests, all pass (new)
test_reasoning_reliability_v2.py:   38 tests pass (4 pre-existing pydantic env failures)
evidence_harness_v3.py:            19/19 validated STRICT (unchanged)
evidence_harness_v4.py:            24/24 validated STRICT (new)
  Table 1: 8/8 validated (Northman confirmed_listing_context, no scenic claims)
  Table 2: 8/8 validated (Lakeview neighborhood allowed, no rating-primary)
  Table 3: 8/8 validated (izakaya venue_head_recognized=True)
```

### Production contract verification

| Query | Result |
|---|---|
| breweries near the river | 8/8 accepted, Northman validated, no omissions, no unsupported scenic claim |
| taprooms with a view | 8/8 accepted, no rating/review-primary notes, honest view caveats |
| izakayas | 8/8 accepted, venue_head_recognized=True, no rating-primary notes |

### Hard contracts preserved from PR #250/#251

- Cards with `validated=False` excluded from response (never shown)
- `deterministic_visible_count` always 0 in telemetry
- No NOTE OMITTED / placeholder in success path
- No thin concept-fit-only phrases in validated notes
- No rating-lead or pure-caveat-only notes
- per_card_notes production logging preserved
- No legacy whyPick fallback
- Izakaya venue-head recognition preserved

### Supabase SQL: No

### Remaining limitations

- "view" as a user modifier is an ambiguity_flag in the frame (not a location_modifier or geography_hint), so modifier_status remains "none" for "taprooms with a view" queries — honest, but doesn't produce confirmed/unknown distinction per card
- Riverwalk safe-evidence relies on entity name containing "Riverwalk" — if Google changes the listing name, the safe-evidence logic still works (entity name is always verified Google data)
- Evidence adequacy STRONG now requires enrichment (Place Details); without enrichment, even a perfect name match is OK. This is correct but means some notes will be OK-grade with good editorial not fetched yet

---

## Previous change (2026-05-06) — EvidencePack v3 Production-Bar Hardening

**Status: MERGED**

### Problem solved (Level 3 production blockers on PR #251)

Production Railway logs showed:
- `breweries near the river`: 7/8 accepted, reasoning_success=False, 1 card omitted
- `taprooms with a view`: 3/8 accepted, reasoning_success=False, 5 cards omitted
- `izakayas`: 8/8 accepted but `venue_head_recognized=False`
- Bad note in production: "4.7★ from 1,344 reviews. The requested view setting is not verified."

Root causes fixed:
1. Quality gate too narrow — "well-regarded", "highly rated", "great option", "Chicago institution", rating-lead notes, and pure-caveat-only notes all slipped through
2. Safety validator too narrow — "strong local following", "consistent quality", "Chicago institution" not blocked
3. Izakaya not in `_SYNONYM_SETS` → `venue_head_recognized=False` in production logs
4. Misleading "truncating" log in `build_reasons_with_retry` (8 cards processed but log said "truncating" at batch_size=6)
5. Harness v3 had weak assertions (allowed partial validation) and 3-card scenarios (not production-shape)

### What was built

**Izakaya venue-head recognition** (`ranker.py`): Added `frozenset({"izakaya", "izakayas"})` to `_SYNONYM_SETS`. Now `venue_head_recognized=True` for izakaya queries. `TestIzakayaVenueHead` in `test_evidence_quality_v3.py` covers this.

**Strengthened quality gate** (`batched_reason_builder.py`): Extended `_QUALITY_THIN_RE` with: `well-regarded`, `highly-rated`/`highly rated`, `great option`, `top pick`, `strong local following`, `consistent quality`, `Chicago institution`. Added `_PURE_CAVEAT_FULL_NOTE_RE` (anchored regex) to reject notes whose ENTIRE content is a view denial with no differentiator. Added rating-lead check in `_assess_quality()` — notes starting with `\d.★` are rejected as "rating_residue_lead". Fixed misleading "truncating" log → "reasoning all cards".

**Strengthened safety validator** (`reason_validator.py`): Added `strong local following`, `consistent quality`, `Chicago institution` to `_GENERIC_BOILERPLATE_RE`.

**Production-shape harness v3** (`evidence_harness_v3.py`): Complete rewrite with 8-card scenarios:
- Table 1: "breweries near the river" — 8 cards, pass1=7/8 good, 1 thin quality-rejected, retry rescues 1/8
- Table 2: "taprooms with a view" — 8 cards, pass1=3/8 good, 5 thin quality-rejected, retry rescues 5/8
- Table 3: "izakayas" — 3 cards, all pass1, STRONG editorial enrichment
- STRICT assertions: ALL cards `displayWhyValidated=True`, `final_note_omitted_count=0`, `deterministic_visible_count=0`

**New tests** (`test_evidence_quality_v3.py`): 23 new tests added (total 53):
- `TestQualityCriticExtended` — 9 tests for new rejection patterns + caveat-with-differentiator pass
- `TestIzakayaVenueHead` — 4 tests proving synonym-set recognition
- `TestProductionShapeScenarios` — 4 tests: 7/8+1/8, 3/8+5/8, no-truncating-log, telemetry invariants
- `TestHarnessV3Strict` — 5 tests: all-validated per table, exact retry counts

### Files changed

- `backend/app/concierge/ranker.py` — Added `frozenset({"izakaya", "izakayas"})` to `_SYNONYM_SETS`
- `backend/app/concierge/batched_reason_builder.py` — Extended `_QUALITY_THIN_RE`; added `_PURE_CAVEAT_FULL_NOTE_RE`; rating-lead + pure-caveat checks in `_assess_quality()`; fixed "truncating" log
- `backend/app/concierge/reason_validator.py` — Added `strong local following`, `consistent quality`, `chicago institution` to `_GENERIC_BOILERPLATE_RE`
- `backend/tests/evidence_harness_v3.py` — Complete rewrite: 8-card scenarios, strict assertions, telemetry verification
- `backend/tests/test_evidence_quality_v3.py` — 23 new tests (53 total)
- `backend/tests/test_reasoning_reliability_v2.py` — Updated mock notes that used "well-regarded", "Chicago institution", "consistent quality" to use non-generic specific notes
- `backend/tests/test_semantic_retrieval_v1.py` — Updated `test_unknown_concept_keeps_partial_results` to use "kaiseki" (izakaya is now a recognized concept)

### Test results

```
1313 passed (excludes test_restaurant_search_diagnostics.py — pre-existing httpx absence)
  test_evidence_quality_v3.py:        53 tests, all pass (23 new)
  test_reasoning_reliability_v2.py:   42 tests, all pass
  test_semantic_retrieval_v1.py:     208 tests, all pass
  evidence_harness_v3.py:            19/19 validated STRICT
    Table 1: 8/8 validated (7 pass1 + 1 retry)
    Table 2: 8/8 validated (3 pass1 + 5 retry)
    Table 3: 3/3 validated (all pass1)
```

### Hard contracts preserved from PR #250

- Cards with `validated=False` excluded from response (never shown)
- `deterministic_visible_count` always 0 in telemetry
- No NOTE OMITTED / placeholder in success path
- No thin concept-fit-only phrases in validated notes
- No rating-lead or pure-caveat-only notes (new enforcement)

### Env vars

No new env vars. All config from previous sessions unchanged.

### Supabase SQL: No

---

## Previous change (2026-05-05) — Reasoning Reliability v2: Three-Pass Orchestrator + Validated Display Contract

**Status: MERGED** — 0 concierge failures; 20 pre-existing httpx-only remain (unrelated)

### Root cause (this PR)

PR-5 fixed the NameError and template note problems, but production still showed only 1 of 6 cards getting LLM notes ("NOTE OMITTED" on the other 5). Root cause: single-pass, 3-second timeout on Sonnet (~10.8s actual latency), no retry for partial success, no fallback model.

### Architecture (Reasoning Reliability v2)

Three-pass cascade orchestrator in `build_reasons_with_retry()`:
- **Pass 1**: Primary model (haiku, 8s timeout), all cards.
- **Pass 2**: Primary model retry for any cards missing after pass 1.
- **Pass 3**: Fallback model (sonnet, 16s timeout) for any cards still missing.

Per-card `CardReason` dataclass: `note`, `source`, `validated`, `attempt_count`, `retry_used`, `fallback_model_used`, `model_used`. Cards with `validated=False` after all passes are **excluded** from the returned card set — never shown with a deterministic or template note.

`display_why_validated: bool = False` added to `ConciergeDisplayFields`. Frontend gates Concierge Note block on `displayWhyValidated === true`; no legacy fallback chain for semantic cards.

### Hard contracts

- **No NOTE OMITTED in success path**: cards without a validated note are excluded (not returned with placeholder).
- **No deterministic visible notes**: `deterministic_visible_count` is always 0 in telemetry.
- **No user UI testing**: evidence is provided via `backend/tests/evidence_harness_v2.py` tables.

### Evidence harness output (2026-05-05) — Table 5 uses 7 required target queries

Required target queries (Table 5 — must not be changed):
1. `izakayas`
2. `izakayas with waterfront views`
3. `izakayas on Fulton Street`
4. `best breweries`
5. `best waterfront breweries`
6. `breweries near the river`
7. `taprooms with a view`

```
Table 1 (full success):      6/6 validated, 0 omitted  — all llm_evidence_pack_v2_primary, quality-checked
Table 2 (partial+retry):     6/6 validated, 0 omitted  — 1 primary, 5 retry-recovered, quality-checked
Table 3 (timeout+fallback):  4/4 validated, 0 omitted  — all llm_evidence_pack_v2_fallback (sonnet), quality-checked
Table 4 (bad-template):      3/3 validated, 0 omitted  — validator rejected pass-1, retry repaired, quality-checked
Table 5 (target queries):   21/21 validated, 0 omitted  — 7 required queries × 3 cards, quality-checked
  [QUALITY CHECK PASSED] all 5 tables
```

Quality rules enforced in harness and tests:
- No NOTE OMITTED in success path.
- No displayWhyValidated=False in success path.
- No name+rating template notes.
- No generic filler ("well-regarded", "strong local following", "Chicago institution", "consistent quality").
- No unsupported waterfront/view claims without explicit negation caveat.
- "izakayas on Fulton Street" notes must NOT claim to be on Fulton Street (modifier not confirmed by evidence).

### Files changed (this PR)

- `backend/app/concierge/batched_reason_builder.py` — `CardReason`, `ReasoningResultV2`, `_validate_and_trim`, `_run_llm_pass`, `build_reasons_with_retry`; env-driven config for primary/fallback model, timeout, retries, batch size.
- `backend/app/concierge/semantic_retrieval.py` — Step 7 uses `build_reasons_with_retry`; step 8 excludes `validated=False` cards; `_entity_to_card` sets `display_why_validated`.
- `backend/app/models/concierge.py` — `display_why_validated: bool = False` on `ConciergeDisplayFields`.
- `backend/app/concierge/logging.py` — schema-tolerant `_extract_missing_column` (handles Supabase schema-cache error format).
- `frontend/src/lib/concierge/cardPresentation.js` — `pickCardReason` gates on `displayWhyValidated`; no legacy fallback for semantic cards.
- `frontend/src/components/trips/AIConciergePanel.tsx` — added `displayWhyValidated?` and `displayWhySource?` to `DisplayCard.display` type.
- `backend/tests/test_reasoning_reliability_v2.py` — **42 tests** (was 28): added `TestEvidenceHarnessQuality` (7 tests) + `TestFrontendSemanticCardIsolation` (6 tests).
- `backend/tests/test_semantic_retrieval_v1.py` — 9 integration tests updated to use `_MOCK_VALID_REASONS` context manager.
- `backend/tests/evidence_harness_v2.py` — runnable evidence script with 7 required target queries, quality assertions, inline `assert_success_path_quality()`.

### Env vars added (Reasoning Reliability v2)

| Var | Default |
|-----|---------|
| `CONCIERGE_CARD_REASONING_PRIMARY_MODEL` | `claude-haiku-4-5-20251001` |
| `CONCIERGE_CARD_REASONING_FALLBACK_MODEL` | `claude-sonnet-4-6` |
| `CONCIERGE_CARD_REASONING_TIMEOUT_MS` | `8000` |
| `CONCIERGE_CARD_REASONING_MAX_RETRIES` | `1` |
| `CONCIERGE_CARD_REASONING_BATCH_SIZE` | `6` |

---

## Previous change (2026-05-05) — PR-5 STOP-THE-LINE: Runtime Bug Fix, Truthful Telemetry, Template Elimination

**Status: MERGED**

### Root cause chain (PR-5)

PR-4 merged but production still showed template notes. Three root causes:

1. **`NameError: name 'concept' is not defined`** — `_build_batch_prompt` in `batched_reason_builder.py` used an f-string with `{concept}`, `{category}`, `{rating}`, `{N}`, `{city}` as literal example text in anti-pattern rules. Python evaluated them as Python variables — none existed. Fixed: escaped to `{{concept}}` etc.

2. **False success telemetry** — `reason_source = "batched_grounded_v1"` and `grounded_reason_success=True` were set based on `_flag_enabled()` flag status, NOT on actual LLM output. Even when the NameError caused full fallback to deterministic, telemetry said success. Fixed: `ReasoningResult` typed contract; `success=True` only when `accepted_count >= 1`.

3. **Templates still rendered** — Even with the NameError fixed, `build_safe_reason` emits `"Name on Street — rating★ from N reviews."` which the validator accepted. This repeats only fields already visible on the card. Fixed: `_NAME_RATING_ONLY_RE` validator pattern rejects pure name+rating templates; `_minimal_safe_note` returns `""`.

### Durable fixes (PR-5)

**`backend/app/concierge/batched_reason_builder.py`**
- Fix: all `{concept}`, `{category}`, `{rating}`, `{N}`, `{city}` escaped as `{{...}}` in the f-string.
- New `ReasoningResult` dataclass: `attempted`, `success`, `accepted_count`, `rejected_count`, `omitted_count`, `fallback_count`, `prompt_error`, `diversity_flagged`.
- `build_batched_reasons` returns `Tuple[Dict[str, str], ReasoningResult]`.
- Prompt builder exception now caught separately → `prompt_error=True`, `success=False`, fallback returned. Previously swallowed by outer except.
- Improved LLM prompt: analytical framing, explicit anti-pattern list, no template examples.
- Cross-card diversity check: `_skeleton()` + `_check_note_diversity()`.

**`backend/app/concierge/reason_validator.py`**
- New `_NAME_RATING_ONLY_RE`: rejects notes where the ENTIRE content is `{Name} — {rating}★ from {N} reviews.` or `{Name} on {Street} — {rating}★ from {N} reviews.` with no further sentences. Notes that add a caveat sentence (geo disclaimer, modifier caveat) are NOT matched.
- Expanded `_GENERIC_BOILERPLATE_RE`: added "top pick for/because", "worth considering for your trip", "a well-regarded local pick", "perfect for enthusiasts".
- New rejection code `name_rating_only_template`.

**`backend/app/concierge/semantic_retrieval.py`**
- Unpacks `(batched_reasons, reasoning_result)` from `build_batched_reasons`.
- `reason_source = "batched_grounded_v1"` only when `reasoning_result.success` is True.
- `grounded_reason_success` in telemetry = `reasoning_result.success` (truthful).
- Det-reason fallback: `det_reason = ""` (not `_minimal_safe_note(entity)`) when deterministic note is rejected.
- `top_card_city` extraction now filters building fragments (`_NON_NEIGHBORHOOD_FRAGMENTS`) — "Lower Level, Chicago, IL" returns "Chicago", not "Lower Level".
- New telemetry fields: `reasoning_attempted`, `reasoning_model`, `reasoning_success`, `reasoning_failure_reason`, `llm_accepted_count`, `validator_rejected_count`, `note_omitted_count`, `deterministic_visible_count`, `final_note_omitted_count`, `prompt_builder_error`, `diversity_flagged`.

**`backend/app/concierge/semantic_retrieval.py` — `_minimal_safe_note`**
- Returns `""` — the `"Name — rating★"` format is now banned by `_NAME_RATING_ONLY_RE`.
- Function retained for API compatibility but must not be used for visible output.

**`frontend/src/lib/concierge/cardPresentation.js`**
- Removed `FALLBACK_REASON = "A well-regarded local pick..."` constant.
- `splitReason("")` returns `{ short: "" }` (not FALLBACK_REASON).
- `pickCardReason` returns `""` as last resort (not FALLBACK_REASON).
- `sanitizeWhyPick` returns `""` for rejected/thin notes (not FALLBACK_REASON).

**`frontend/src/components/trips/AIConciergePanel.tsx`**
- `ConciergeCard` Concierge Note block wrapped in `{reasonParts.short && (...)}` — block is absent when note is empty.

### No-template/no-note contract

A visible Concierge Note must be one of:
1. A validated, dynamic, card-specific note (from LLM or caveated deterministic path).
2. **Absent** — frontend hides the block entirely.

It must never be:
- `{Name} — {rating}★ from {N} reviews.` — repeats visible card fields
- `{Name} on {Street} — {rating}★ from {N} reviews.` — same
- `Verified {Category} with {rating}★...` — fill-in-the-blank
- `Strong/Good/Great {concept} match...` — zero information
- "A well-regarded local pick with verified listing details." — FALLBACK_REASON gone

### When notes ARE produced by the deterministic path (no LLM)

Notes survive validation when they include additional content beyond name+rating:
- Geo caveat: `"No waterfront proximity confirmed from address."` (query had geo hint)
- View caveat: `"The requested view setting is not verified."` (taprooms with a view)
- Modifier caveat: `"Not directly on Fulton Street — nearest match in the area."` (izakayas on Fulton)

### Deferred (EvidencePack v2 + Google Details enrichment)

Google Place Details enrichment (editorial summaries, more address components) was scoped and assessed. The current pipeline already acquires sufficient structured data for the deterministic path. Full EvidencePack v2 with Google Details enrichment is deferred to PR-6 because:
- Adds latency (additional API calls per card)
- Requires TTL cache design to avoid cost blowup
- LLM path quality is the primary improvement vector (once NameError and templates are fixed)

### Tests (234 passing after PR-5)

New test file: `backend/tests/test_concierge_reasoning_v5.py` (54 tests):
- `TestPromptBuilderNameError` — 8 tests: all 7 validation queries run without NameError
- `TestReasoningResultContract` — 7 tests: tuple return, success/failure semantics
- `TestNameRatingTemplateValidator` — 11 tests: all banned template forms rejected, valid caveated forms pass
- `TestDeterministicFallbackNoTemplate` — 3 tests: rejected notes → empty string
- `TestGeographyCleanup` — 3 tests: building fragments never used as city/area
- `TestEvidenceAdequacy` — 2 tests: thin evidence → omitted, LLM null → omitted_count
- `TestNoInventedModifierClaims` — 5 tests: no invented waterfront/view/river/Fulton
- `TestCrossCardDiversity` — 3 tests: skeleton function, identical flagged, diverse passes
- `TestTruthfulTelemetry` — 3 tests: grounded_success only when LLM accepted
- `TestFrontendCardPresentation` — 5 tests: no FALLBACK_REASON, conditional rendering
- `TestFullRegressionSuite` — 4 tests: all 7 queries prompt runs, plain rejected, geo passes, no templates

Updated existing tests:
- `TestBatchedReasonBuilder` — unpack tuple from `build_batched_reasons` (6 tests updated)
- `TestBatchedReasonModelConfig` — unpack tuple (1 test updated)
- `TestSafeFallbackFormat` — split into `test_fallback_with_geo_or_modifier_passes_validator` (geo queries) + `test_fallback_without_modifier_is_rejected_as_template`
- `TestReasoningSourceContract` — split into `test_deterministic_reason_with_geo_hint_passes_validator` + `test_plain_query_deterministic_reason_rejected_as_template`

### Manual/live-style validation expected results

(After LLM path enabled in production with ANTHROPIC_API_KEY present)

- `"izakayas"` → note **absent** (deterministic template rejected; LLM produces specific note or null)
- `"izakayas with waterfront views"` → note includes caveat "No waterfront proximity confirmed from address." or LLM-generated honest note
- `"izakayas on Fulton Street"` → note includes "Not directly on Fulton Street..." caveat if place not on Fulton
- `"best breweries"` → note **absent** in deterministic path; LLM may produce specific note
- `"best waterfront breweries"` → note includes "No waterfront proximity confirmed from address." caveat
- `"breweries near the river"` → note includes "No river proximity confirmed from address." caveat
- `"taprooms with a view"` → note includes "The requested view setting is not verified." caveat

### Production validation checklist (post-deploy)

1. Check Railway logs: `reasoning_success`, `llm_accepted_count`, `prompt_builder_error` — `prompt_builder_error=False` always; `reasoning_success=True` only when notes accepted.
2. No `name_rating_only_template` in `grounded_reason_success=True` logs.
3. `top_card_city` never shows building fragments (Lower Level, Suite, Lobby, etc.).
4. Visible Concierge Notes are absent OR include meaningful non-template content.
5. "Goose Island Taproom on Fulton Street — 4.8★ from 1,159 reviews." no longer appears.

### Critical invariants preserved
- No fake addable cards. Google place id + OPERATIONAL + Google Maps URI gates unchanged.
- No Tavily / editorial / Yelp / Foursquare.
- Google rating displays on native 0–5 scale.
- No SQL or schema changes.
- No visual redesign — only the Concierge Note block is conditionally hidden when absent.

Supabase SQL: No.
HANDOFF.md edited: Yes — PR-5 post-merge reasoning failure, runtime bug, telemetry contract, no-template/no-note contract, tests.

---

## Previous change (2026-05-05) — PR-4 STOP-THE-LINE: Evidence-First Note Synthesis + Destination Discipline + Runtime Model Config

**Status: MERGED** (PR #246)

### Root cause chain

PR-3 introduced `reason_validator.py` and `batched_reason_builder.py` but the validator was **only applied inside `build_batched_reasons()`** (flag off by default → never reached in production). The deterministic `build_safe_reason()` output went directly to cards with zero validation.

`build_safe_reason()` emitted two successive banned patterns:
1. **`"Strong {concept} match in {city}"`** — the original generic boilerplate (PR-4 first pass fixed this)
2. **`"Verified {type} with {rating}★ across {N} Google reviews."`** — a new fill-in-the-blank template identical in structure for every card (PR-4 addendum fixed this)

Both patterns provide zero card-specific differentiation. The addendum required a full evidence-first rewrite.

### Root causes (all fixed in PR-4)

1. **`build_safe_reason()` emitted fill-in-the-blank templates.** Neither `"Strong izakaya match in Chicago"` nor `"Verified Brewery with 4.5★ across 892 reviews."` anchor on card-specific evidence.
2. **Validator never applied to deterministic output.** Only called inside the disabled LLM path.
3. **No destination discipline.** Lakefront Brewery (Milwaukee, WI) ranked #1 for Chicago requests via review count.
4. **`_GENERIC_MATCH_IN_RE` and `_VERIFIED_TEMPLATE_RE` missing from validator.**
5. **LLM model hardcoded.** `claude-haiku-4-5-20251001` not overridable at runtime; blocked quality validation with a stronger model.

### Durable fixes (PR-4 as merged)

**`backend/app/concierge/safe_reason_builder.py`** — evidence-first, name+street anchored:
- Format: `"Goose Island Brewery on Fulton Street — 4.5★ from 1,159 reviews."`
- Returns `""` when only evidence is type+city+rating (no card differentiator). Empty is better than a template.
- Waterfront/river/view geo hints → `"No waterfront proximity confirmed from address."` (denial, never assertion)
- Confirmed location modifier → `"on {modifier}"` in lead. Unconfirmed → `"Not directly on {modifier} — nearest match in {area}."`
- Street name extracted from formatted address: `"1800 W Fulton St, Chicago, IL"` → `"Fulton Street"`
- `_MODIFIER_ONLY_LABELS`: prevents "waterfront", "rooftop", etc. from being treated as a venue concept.

**`backend/app/concierge/reason_validator.py`** — three rules relevant to this PR:
- `_GENERIC_MATCH_IN_RE`: rejects `"Strong/Good/Great/Solid/Excellent X match"` patterns.
- `_VERIFIED_TEMPLATE_RE`: rejects `"Verified {Category} with {rating}★"` fill-in-the-blank templates.
- `_claim_is_negated()` + `_NEGATION_CONTEXT_RE`: allows waterfront/view in honest negation context (±80 char window).

**`backend/app/concierge/ranker.py`** — destination discipline:
- `_destination_penalty()`: `_DESTINATION_MISMATCH_PENALTY = 0.45` when entity address confirms a different city.
- `RankerStats.destination_penalized_count`: observability field.
- Milwaukee brewery cannot outrank Chicago brewery for Chicago request even with higher review count.

**`backend/app/concierge/batched_reason_builder.py`** — LLM primary path + runtime model config:
- `_flag_enabled()`: auto-enabled when `ANTHROPIC_API_KEY` present (no flag needed in Railway).
- `CONCIERGE_BATCHED_REASONING_MODEL` env var (default: `claude-sonnet-4-6`). Override after validation.
- Evidence bundles enriched: street name, name-signal, rank position/total.
- Prompt explicitly bans template structures, requires cross-card note diversity, allows `null` for thin evidence.
- `null` from LLM = stay on deterministic fallback (not a parse failure).
- Structured log on LLM success: `grounded_reason_model`, `grounded_reason_attempted`, `grounded_reason_success`, `fallback_note_count`, `validator_rejected_count`.

**`backend/app/concierge/semantic_retrieval.py`** — validator on deterministic path + name-anchored fallback:
- `validate_reason()` called on every `det_reason` before card assembly.
- `_minimal_safe_note()`: place-name anchored emergency fallback: `"Goose Island Brewery — 4.5★ from 1,200 reviews."` Never `"Verified {type} with..."`.

### Validator contract (as merged)

A note passes when it:
- Does NOT match `"Strong/Good/Great X match"` (generic boilerplate)
- Does NOT match `"Verified {Category} with {rating}★"` (fill-in-the-blank template)
- Does NOT claim waterfront/view/riverwalk/Michelin/awards/hours/prices UNLESS the term appears inside an explicit negation/caveat (`_claim_is_negated`)
- Does NOT use address-fragment locations ("in Lower Level")
- Does NOT contain internal metric names
- Does NOT assert a location modifier as confirmed unless evidence confirms it
- Does NOT contain distance claims ("5 steps from", "200 feet from")

### Destination discipline contract

- Entity address containing destination city token → no penalty.
- Entity address with confirmed different city → `_DESTINATION_MISMATCH_PENALTY = 0.45` applied to rank score.
- Milwaukee, Evanston, etc. cannot outrank in-city places even with higher ratings.

### Tests (206 passing as merged)

- `TestBatchedReasonModelConfig` — 4 new tests: default is `claude-sonnet-4-6`, env override respected, correct model kwarg sent to Anthropic, deterministic path unaffected when env absent.
- `TestEvidenceFirstContract` — 5 new tests: notes anchor on name, vary by street, return `""` for thin evidence.
- `TestFinalVisibleNoteValidator` — `test_rejects_verified_category_template`, `test_rejects_verified_izakaya_template` (replaced old template-acceptance tests).
- `TestSafeFallbackFormat` — `test_fallback_is_card_specific_not_type_template` (replaced type-label test).
- `TestDestinationDiscipline` — 6 tests: Chicago brewery outranks Milwaukee for Chicago request.
- `TestPR4FullRegressionSuite` — 10 tests: all 7 acceptance criteria queries pass.
- `test_minimal_safe_note_is_name_anchored_not_type_template` — new.
- 12 existing tests updated: caveat phrasing assertions updated for `"No waterfront proximity confirmed from address."` format; template-acceptance tests flipped to template-rejection tests.

### Production validation checklist

With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
1. "best breweries" → notes say `"Half Acre Beer Co on Lincoln Avenue — 4.5★ (800 reviews)."` Not `"Strong brewery match"` or `"Verified Brewery with..."`.
2. "best waterfront breweries" → Chicago breweries dominate (Milwaukee penalized); notes include `"No waterfront proximity confirmed from address."`.
3. "izakayas with waterfront views" → notes include `"No waterfront proximity confirmed from address."` No view assertion.
4. "izakayas on fulton street" → modifier caveat or confirmation in note.
5. "taprooms with a view" → notes do not claim a view.
6. "romantic tapas but not too loud" → note anchors on place name + street.
7. Railway logs: `det_reason_rejected=0` (should be 0 after fix); `destination_penalized=N`; `top_card_city=Chicago` for Chicago requests; `grounded_reason_model=claude-sonnet-4-6`.
8. No `"Strong X match"` or `"Verified X with Y★"` pattern in any visible card note.

### Railway env vars (post-merge)

| Var | Value | Notes |
|---|---|---|
| `CONCIERGE_BATCHED_REASONING_MODEL` | `claude-sonnet-4-6` | Default for quality validation. No deploy needed to change. |
| `CONCIERGE_BATCHED_REASONING_ENABLED` | _(unset — auto)_ | Auto-enables when `ANTHROPIC_API_KEY` is set. |
| `BATCHED_REASON_TIMEOUT_S` | `3.0` | Raise to `5.0` if sonnet is slow. |
| `BATCHED_REASON_MAX_CARDS` | `8` | Leave as-is. |

Downgrade path: after 48h of production logs showing `grounded_reason_success` ≥ 80% with sonnet, set `CONCIERGE_BATCHED_REASONING_MODEL=claude-haiku-4-5-20251001` on Railway. No deploy needed.

### Critical invariants preserved
- No fake addable cards. Google place id + OPERATIONAL + Google Maps URI gates unchanged.
- No Tavily / editorial / Yelp / Foursquare.
- Google rating displays on native 0–5 scale.
- No frontend changes. Card rendering contract not regressed.
- No SQL or schema changes.

Supabase SQL: No.

---

## Previous change (2026-05-05) — PR-3 Batched Grounded Reasoning + Validators + Location Modifier Preservation

### Root cause of bad notes
Two independent bugs were producing generic/wrong card notes:

1. **`_LOCATION_ANCHOR_RE` required capital letters** — "izakayas on fulton street" typed lowercase got `location_modifiers=[]` because the regex matched only `[A-Z]`-anchored phrases. All retrieval queries therefore omitted "Fulton Street" and the deterministic note said "Strong izakaya match in Chicago" with no mention of the user's explicit location ask.

2. **`_area_from_address` returned "Lower Level"** — The address parser took the first non-digit, non-destination segment from the formatted address. For venues inside buildings (airports, malls, concourses), this was a floor/unit descriptor like "Lower Level", producing notes like "Strong izakaya match in Lower Level."

3. **No batched LLM reasoning layer** — Notes were purely deterministic `build_safe_reason` output with no evidence-grounded LLM synthesis and no validators.

### Durable fixes

**`backend/app/concierge/frame_extractor.py`**
- Added `_LOCATION_ANCHOR_LOWERCASE_RE`: second pattern for lowercase street/district names identified by known street suffixes ("street", "avenue", "loop", "market", "district", etc.). Catches "fulton street", "river north", "west loop" etc.
- Updated `_extract_location_modifiers` to run both patterns and title-case the output for consistency.
- Extended `_AMBIGUITY_PATTERNS` to catch standalone "a view" / "views" phrasing (previously only matched compound forms like "waterfront view"), so "taprooms with a view" correctly sets `view_not_structurally_verifiable`.

**`backend/app/concierge/ranker.py`**
- Added `_location_modifier_confirmed()` helper: checks whether significant tokens from the user's location modifier appear in the entity's address or name.
- Updated `build_evidence_bundle()`: adds a `"Address confirms {modifier} area"` structured fact when confirmed, or a `"location_modifier_not_confirmed:{modifier}"` uncertainty flag when not.

**`backend/app/concierge/safe_reason_builder.py`**
- Added `_NON_NEIGHBORHOOD_FRAGMENTS`: frozenset of floor/unit/lobby/level descriptors. `_area_from_address` now skips these instead of returning them as the neighborhood label.
- Added `_location_modifier_phrase()` helper: reads the evidence bundle's location modifier facts/flags and returns either `(confirmed_modifier, "")` or `("", caveat_text)` for honest reason construction.
- Updated `build_safe_reason()`: when a location modifier was requested but not confirmed, appends e.g. "Not directly on Fulton Street — nearest match in the area." When confirmed, uses `" on {modifier}"` as the location part.

**`backend/app/concierge/reason_validator.py`** (new)
- `validate_reason(reason, frame, evidence) → (bool, str)` — rejects notes that:
  - Mention unsupported physical attributes (waterfront, riverwalk, Michelin, awards, quiet/romantic atmosphere, opening hours, prices)
  - Expose internal metric names (subtype_fit, geo_fit, OPERATIONAL, place_id, etc.)
  - Contain generic boilerplate
  - Use address fragments as location ("in Lower Level")
  - Claim an unconfirmed location modifier as fact
- `validate_reasons_batch()` for batch validation.

**`backend/app/concierge/batched_reason_builder.py`** (new)
- `build_batched_reasons(cards_data, frame, timeout) → Dict[str, str]` — one LLM call for all cards using claude-haiku-4-5-20251001.
- Feature flag: `CONCIERGE_BATCHED_REASONING_ENABLED` (default `false`). When disabled, returns deterministic fallbacks.
- Budget gate: skips LLM if card count > `BATCHED_REASON_MAX_CARDS` (default 8).
- Timeout: `BATCHED_REASON_TIMEOUT_S` (default 3.0 seconds).
- LLM prompt is grounded in evidence bundle only; LLM may not invent facts.
- Per-card fallback to deterministic `SafeReasonBuilder` output when LLM fails, times out, returns invalid JSON, or any card fails `validate_reason`.
- Never raises.

**`backend/app/concierge/semantic_retrieval.py`**
- Steps 6-8 restructured: (6) build evidence bundles + deterministic reasons, (7) batched LLM reasoning, (8) assemble cards from batched or deterministic reasons.
- `_entity_to_card()` accepts `reason_source` parameter; sets it on `reason_source` and `display.display_why_source` fields.
- Turn log now emits `reason_source=deterministic_safe_v1|batched_grounded_v1`.

### Validator contract
A note passes validation only when it:
- Does not claim waterfront/riverwalk/view/quiet atmosphere/romantic atmosphere/Michelin/awards/opening hours/prices
- Does not contain internal metric names or provider debug fields
- Does not use floor/unit descriptors as location labels
- Does not assert a location modifier as confirmed unless the evidence bundle confirms it

### Location modifier preservation contract
- `extract_frame("izakayas on fulton street", "Chicago")` → `location_modifiers=["Fulton Street"]`
- `extract_frame("breweries near the river", "Chicago")` → river in `geography_hints` or `location_modifiers`
- `extract_frame("taprooms with a view", "Chicago")` → `ambiguity_flags=["view_not_structurally_verifiable"]`
- Destination city is never echoed back as a location modifier

### Tests (41 new, total 160 in `test_semantic_retrieval_v1.py`, all passing)
- `TestLocationModifierExtractionLowercase` — 7 tests: lowercase "fulton street" captured; "Fulton Street" capitalized still works; river in breweries query; "river north" lowercase captured; "taprooms with a view" gets view ambiguity flag; destination not echoed; title-case normalization.
- `TestEvidenceBundleLocationModifier` — 4 tests: confirmed when address contains modifier; not_confirmed flag when address lacks modifier; no flags when frame has no modifier; no internal fields in bundle.
- `TestImprovedDeterministicReason` — 5 tests: no "Lower Level" in reason; location modifier caveat when unconfirmed; reason is more specific than "Strong X match in Chicago"; no caveat when address confirms modifier; no waterfront claim without evidence.
- `TestReasonValidator` — 11 tests: rejects waterfront/Michelin/internal fields/address fragments/opening hours/prices/quiet atmosphere/romantic atmosphere; accepts grounded specific note; accepts honest location caveat note; rejects false location modifier claim.
- `TestBatchedReasonBuilder` — 7 tests: flag-off uses deterministic; all card keys returned; empty cards; fallback on LLM error; fallback on invalid JSON; per-card fallback on invalid LLM output.
- `TestPR3RegressionSuite` — 7 tests: izakayas open-class still detected; best breweries not regressed; best waterfront breweries brewery-anchored; no waterfront claim; breweries near river preserves geo hint; taprooms with a view no invented views; card payload reason_source field; rating scale native 0-5.

### Latency / budget guardrails added
- `BATCHED_REASON_TIMEOUT_S` (default 3.0s) — hard timeout for LLM call
- `BATCHED_REASON_MAX_CARDS` (default 8) — skip LLM if more cards than this
- `CONCIERGE_BATCHED_REASONING_ENABLED` (default false) — entire LLM path skipped until explicitly enabled
- All fallback paths are synchronous deterministic; no latency added when flag is off

### PGRST204 logging schema issue
Resolved in prior PR (removed `intent_classifier_version` from insert row). Current `persist_concierge_request_log` has `intent_confidence` which maps to `decision.stage2_confidence`. If PGRST204 still appears for `intent_confidence`, the existing schema-drift retry mechanism will drop and retry. No additional change needed in this PR.

### Critical invariants preserved
- No fake addable cards. Google place id + OPERATIONAL + Google Maps URI gates unchanged.
- No Tavily / editorial / Yelp / Foursquare. No SQL or schema changes.
- Google rating displays on native 0–5 scale.
- No frontend changes. Card rendering contract not regressed.
- PR-3 batched LLM path is feature-flagged off by default.

### Production validation checklist
With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
1. "izakayas" → cards render, notes include izakaya concept match and rating.
2. "izakayas on fulton street" (lowercase) → `location_modifiers=["Fulton Street"]` in turn log; cards have location caveat when address doesn't confirm Fulton Street.
3. "best breweries" → brewery cards, no regression.
4. "best waterfront breweries" → brewery cards; no "waterfront" claim in notes unless address confirms water proximity.
5. "breweries near the river" → brewery-anchored; river preserved in geo_hints or location_modifiers.
6. "taprooms with a view" → taproom cards; no invented view claims.
7. Railway logs: `reason_source=deterministic_safe_v1` (or `batched_grounded_v1` if flag enabled).
8. No "Lower Level" appearing as neighborhood in any card note.

Supabase SQL: No.

---

## Previous change (2026-05-05) — INTENT_GENERAL card plumbing fix + PGRST204 logging fix

### Root cause
Two independent bugs were blocking verified place cards from reaching the drawer UI for open-class queries (e.g. "izakayas", "tea houses"):

1. **`backend/app/services/concierge.py` — missing INTENT_GENERAL branch**: `search()` dispatches on intent with `if/elif` branches for every named intent. `INTENT_GENERAL` (returned by `_detect_intent()` when no keyword matches) had **no branch**. Semantic retrieval (`_fetch_live_research`) correctly populated `live_result.restaurants` with 8 verified cards, but `search()` never read them — `restaurants` stayed `[]`, the response was `PlaceRecommendationsResponse(restaurants=[])`, and the drawer UI had nothing to render.

2. **`backend/app/concierge/logging.py` — PGRST204 on every request**: `persist_concierge_request_log()` included `"intent_classifier_version"` in the insert row. That column doesn't exist in the `concierge_request_log` DB table. The existing schema-drift retry mechanism was not catching it, causing a logged exception on every request (non-blocking to response delivery, but noisy).

### Durable fixes
- **`backend/app/services/concierge.py`**: Added `elif intent == INTENT_GENERAL:` block after the `INTENT_GENERAL_DESTINATION` branch. Reads `live_result.restaurants` (primary) or `live_result.attractions` (fallback) and sets `source_status`, `cached_response`, `sources`, and `retrieval_used` exactly like the nightlife/restaurants paths. Does not fire when `force_research_only=True`.
- **`backend/app/concierge/logging.py`**: Removed `intent_classifier_version` from `base_row`. Value is already emitted in structured app logs via `request_log_event()`.

### Tests (7 passing)
- **`test_concierge.py::TestConciergeSearch`** — 3 new tests:
  - `test_intent_general_semantic_restaurants_reach_response`: asserts `len(result.restaurants) == 1`, `source_status == "live_search"`, `retrieval_used is True` when semantic retrieval returns cards for an "izakayas" query.
  - `test_intent_general_empty_semantic_result_returns_no_cards`: asserts `restaurants == []`, `retrieval_used is False` when semantic retrieval returns nothing.
  - `test_intent_general_semantic_attractions_reach_response`: asserts fallback to `attractions` when `restaurants` is empty.
- **`test_concierge_logging_schema_tolerance.py`** — updated 3 tests:
  - `test_intent_classifier_version_never_in_insert_row`: replaces old test that expected `intent_classifier_version` in first insert; now asserts it's never present.
  - `test_two_missing_columns_are_dropped_across_retries`: updated to inject `llm_model` / `pipeline_version` drift (both are real base_row columns).
  - `test_warning_emitted_once_per_process_per_column`: updated to inject `llm_model` drift.

### Critical invariants preserved
- No fake addable cards. Google place id + OPERATIONAL + Google Maps URI gates unchanged.
- No semantic planner / ranker / provider changes.
- No frontend changes.
- PR-3 batched grounded reasoning **not** started.

### Production validation checklist
1. Query "izakayas" or "izakayas on Fulton Street" → drawer shows addable cards, not text-only bubble.
2. Railway logs: no `concierge.request_log.persist_failed` on concierge requests.
3. Query "what's the weather like?" → INTENT_GENERAL, no cards expected (semantic retrieval returns nothing for non-place queries).

Supabase SQL: No.

---

## Previous change (2026-05-05) — Venue-Head-Over-Modifier Contract (semantic retrieval v1 hardening)

### Production finding (post-Semantic Place Understanding v2 validation)
With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
- "best breweries" — improved (brewery-first queries, brewery-like results).
- "best waterfront breweries" — still flawed: cards included Chicago Brewhouse Riverwalk, The Lakefront Restaurant, Lakefront Park, Chicago Horizon, Chicago Riverwalk; deterministic reasons repeated "Good waterfront match in Chicago, near waterfront."

### Root cause
The frame extractor and planner already produced venue-anchored queries, but the ranker leaked through wrong-category cards: `_subtype_fit` awarded `query_match=0.6` to **any** entity returned by a brewery-targeted query (because the source query echoed "brewery"). With concept-confidence weighting that pushed wrong-category entities to ~0.57 — well above the `_WRONG_CATEGORY_SUBTYPE_FIT_MAX=0.30` threshold — so the wrong-category penalty never applied to them. A scenic riverwalk landmark or lakefront restaurant could ride that signal past brewery-only fallbacks and into the final cards.

### Durable fix (one PR, no PR-3 batched LLM reasoning)
- **`backend/app/concierge/ranker.py`**
  - Lowered `query_match` weight from 0.6 → 0.20. Source-query echoes are weak evidence (planner targeted the concept; entity may or may not be on-concept) and must stay below `_WRONG_CATEGORY_SUBTYPE_FIT_MAX` so the penalty kicks in.
  - Raised `_WRONG_CATEGORY_PENALTY` from 0.20 → 0.30 to widen the gap between on-concept and modifier-only matches.
  - Added `_ON_CONCEPT_SUBTYPE_FIT_MIN=0.45` and a post-rank venue-head filter: when the user named a strong venue concept (`confidence ≥ 0.85`) AND there are ≥ 3 on-concept candidates, off-concept candidates are dropped entirely. When the venue concept is recognized (in a known synonym set) AND zero on-concept candidates verified, the ranker returns zero cards rather than filling with modifier-only wrong-category matches. Open-vocabulary heads with no synonym set (e.g. "izakaya") still degrade gracefully.
  - New `rank_entities_with_stats()` returns a `RankerStats` side channel for observability without breaking the public `rank_entities()` signature.
- **`backend/app/concierge/retrieval_planner.py`**
  - Always emits one pure `{venue} {destination}` recall query in addition to the geo-targeted variants, so brewery recall isn't entirely dependent on the geo-modified Google result set. Order: (1) venue + dest + modifier, (2) venue + dest pure recall, (3) synonym + dest + modifier, (4) venue + loc anchor + geo when both present.
- **`backend/app/concierge/semantic_retrieval.py`**
  - `semantic_retrieval_v1.turn` log now reports `off_concept_dropped`, `on_concept_count`, and `venue_head_recognized` for visibility into the post-rank filter.

### Critical invariants preserved
- No fake addable cards. Google place id + OPERATIONAL + Google Maps URI gates unchanged.
- No Tavily / editorial / Yelp / Foursquare. No SQL or frontend changes.
- Google rating displays on native 0–5 scale. PR-3 batched grounded reasoning **not** started in this PR.

### Tests (15 new, total 120 in `test_semantic_retrieval_v1.py`, all passing)
- `TestPlannerNoStandaloneModifierQueries` — 6 parametrized queries verify no `waterfront chicago` / `riverwalk chicago` / `lakefront chicago` / `view chicago` / `water chicago` standalone modifier queries are emitted; pure `brewery chicago` recall query confirmed for waterfront ask; `breweries near the river` stays brewery-first.
- `TestRankerVenueHeadDominance` —
  - Brewery with weak waterfront evidence outranks riverside park with strong waterfront evidence.
  - Source-query echo no longer pushes wrong-category subtype_fit above the penalty threshold.
  - 3 breweries + 3 wrong-category modifier-matches → only breweries survive, with `off_concept_dropped=3`.
  - Recognized venue concept + zero on-concept candidates → empty result.
  - Unknown concept ("izakaya") keeps weak matches (no over-aggressive filtering).
- `TestRegressionExistingVenueHeads` —
  - "best breweries" still returns brewery-like cards.
  - "best waterfront breweries" with mixed Google response (3 breweries + 3 wrong-category) returns only brewery cards.
  - "best izakayas" open-class still works.
- `TestSafeReasonNoUnsupportedModifierClaim` —
  - "Good waterfront match" repetition gone.
  - No unsupported "near the river" / "on the river" claim when address has no river.
  - No unsupported "quiet atmosphere" claim.
  - Brewery anchor (not waterfront) present in reason for waterfront-brewery ask.

### Validation cases (production checklist after deploy)
With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
1. "best breweries" Chicago → brewery-first queries, brewery-like cards. **No regression.**
2. "best waterfront breweries" Chicago → brewery cards dominate; no parks / riverwalk attractions / generic waterfront restaurants in cards; deterministic reasons no longer repeat "Good waterfront match".
3. "breweries near the river" Chicago → brewery-anchored queries; brewery-like cards.
4. "taprooms with a view" Chicago → taproom-anchored queries; taproom-like cards.
5. "best izakayas in Fulton Street" Chicago → unchanged from PR-2.5; izakaya cards.

If Google returns no brewery-like candidates for "best waterfront breweries", expect zero cards rather than wrong-category fillers — `semantic_retrieval_v1.turn outcome=no_cards_after_trust_gate off_concept_dropped=N venue_head_recognized=true`.

PR-3 batched grounded reasoning **has not started yet**.

Supabase SQL: No.

---

## Previous change (2026-05-05) — AI Concierge Semantic Place Understanding v2 (venue head, open-class detector, location modifiers, wrong-category penalty)

### Production finding (post-PR #237 validation)
With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
- "best waterfront breweries" returned mostly waterfront restaurants/parks; reasons repeated "Good waterfront match" on every card.
- "best izakayas in Fulton Street" did not enter semantic retrieval — only the outer `concierge.request` log appeared.

This proved the system still had legacy closed-intent gates and weak frame extraction.

### Root cause
1. **Frame extractor treated geo/style modifiers as venue heads.** "best waterfront breweries" has no preposition before the noun, so `_MODIFIER_SPLIT_RE` did not split. After filler removal the candidate tokens were `["waterfront", "breweries"]`. The extractor picked "waterfront" (token order) as the primary concept with confidence 0.95, and "brewery" came in as secondary. Every downstream stage (retrieval planner, ranker, safe-reason builder) anchored on the modifier instead of the venue head, producing cards titled "Good waterfront match …" and surfacing waterfront restaurants/parks.
2. **`INTENT_GENERAL` was excluded from `_FAST_DYNAMIC_INTENTS`.** "izakaya" is not in any closed-pattern bucket; `_detect_intent("best izakayas in Fulton Street")` returned `INTENT_GENERAL`; `_FAST_DYNAMIC_INTENTS` did not include it; semantic retrieval was skipped silently with `concierge.semantic_skip … intent_not_eligible`. The fix per the spec is **not** to add "izakaya" to a keyword bucket but to add an open-class place-ask detector that admits unknown venue nouns by query shape.
3. **Safe reason builder repeated "in waterfront-targeted search area" on every card** when geo_fit was between 0.55 and 0.80, producing the visible repetition the user reported.

### Durable fix (one PR, no PR-3 batched LLM reasoning)
- **`backend/app/concierge/frame_extractor.py`**
  - New `_GEO_MODIFIER_TOKENS`, `_AMBIENCE_MODIFIER_TOKENS`, `_USE_CASE_TOKENS` sets.
  - `_classified_modifier_tokens()` builds the union of tokens already classified as geo/ambience/value/use-case modifiers; `_extract_primary_concepts()` excludes them so the venue head wins.
  - `_extract_location_modifiers()` parses concrete neighborhood/street anchors (e.g., "Fulton Street", "West Loop") from prepositional phrases.
  - `_extract_use_cases()` captures occasion/use-case tokens ("reading", "groups", "dates").
  - New `is_open_class_place_ask()` open-vocabulary detector — high-recall positive triggers, hard-negative list for clearly non-place asks (flights, weather, packing, currency, visa, points/miles redemption, budget plans, itinerary edits).
  - `ExperienceFrame` gains `location_modifiers`, `use_cases`, `open_class_place_detected`. Modifier-split regex extended to include "good for / great for / perfect for".
- **`backend/app/concierge/retrieval_planner.py`**
  - `plan_queries()` is now venue-first: each query starts with the primary venue (or a near-synonym) and only then adds destination + concrete location anchor (priority) + geo hint. A fourth query combines venue + location + geo when both are present.
- **`backend/app/concierge/ranker.py`**
  - New `_WRONG_CATEGORY_PENALTY = 0.20` applied when the user named a high-confidence venue concept (`confidence ≥ 0.85`) and the entity's `subtype_fit < 0.30`. Prevents wrong-category cards from dominating brewery/sushi asks. Penalty is soft (not a hard reject) so the pipeline degrades gracefully when no on-concept results exist.
- **`backend/app/concierge/safe_reason_builder.py`**
  - Modifier-only labels ("waterfront", "rooftop", "river view", "romantic", etc.) are never treated as venue heads in user-visible text — defensive guard against any upstream extraction mistake.
  - Removed the repetitive "in {hint}-targeted search area" branch; only confirmed proximity (`geo_fit ≥ 0.80`) emits a geo phrase. Verify-suffix already handles unverified attributes.
- **`backend/app/services/concierge.py`**
  - New `_OPEN_CLASS_ELIGIBLE_INTENTS = _FAST_DYNAMIC_INTENTS | {INTENT_GENERAL}`. When the semantic flag is on, `INTENT_GENERAL` queries that pass the open-class detector now enter Semantic Retrieval v1 without ever being added to a closed keyword bucket.
  - New `concierge.semantic_eligible` log line with `eligibility_path=fast_dynamic_intent | open_class` and `open_class_place_detected=true|false`.
  - `concierge.semantic_skip` log line now also reports `open_class_place_detected`.
- **`backend/app/concierge/semantic_retrieval.py`**
  - `semantic_retrieval_v1.turn` log now includes `open_class_place_detected`, `venue_concept`, `location_modifiers`, `soft_preferences`, `negative_constraints`, `use_cases`, `value_signals`, `ambiguity_flags`, and `wrong_category_low_subtype_fit` count.

### Tests (37 new)
- `TestVenueHeadPreservation` — "waterfront breweries" / "rooftop bars" / "outdoor breweries" / "romantic tapas" yield correct venue heads; modifiers stay in geography_hints / soft_preferences.
- `TestLocationModifierExtraction` — "izakayas in Fulton Street" → `location_modifiers=["Fulton Street"]`; destination not echoed; "West Loop" captured.
- `TestOpenClassPlaceAskDetector` — 11 place-like asks (izakaya, tea houses, dessert bars, record stores, arcades, speakeasies, "where to grab drinks", ramen, "coffee shops good for reading", "places to dance") detected; 9 non-place asks (weather, packing, exchange rate, flights, visa, days-count, transfer partner, budget plan) rejected.
- `TestRetrievalPlannerVenueFirstOpenClass` — izakaya queries start with venue and include "Fulton" anchor; "best waterfront breweries" generates only brewery/taproom-anchored queries; unknown venue nouns ("record stores") still venue-first.
- `TestWrongCategoryPenalty` — waterfront park/steakhouse does not beat brewery on a brewery ask; `penalties > 0` for wrong-category entity.
- `TestNonRepetitiveSafeReason` — no "Good waterfront match"; modifier-only labels never become venue heads in reason text; "targeted search area" phrase suppressed when geo_fit weak.
- `TestSemanticIntegrationOpenClassIzakaya` — "best izakayas in Fulton Street" returns verified izakaya cards via mocked Google.
- `TestSemanticTurnObservability` — turn log carries `open_class_place_detected`, `venue_concept`, `location_modifiers`, `retrieval_queries`, `wrong_category_low_subtype_fit`.
- Updated `TestSemanticSkipObservability` — uses a non-place query ("currency exchange rate") to exercise the skip path; new `test_open_class_place_ask_enters_semantic` asserts the open-class path now admits `intent=INTENT_GENERAL` izakaya queries.

### Validation cases (production checklist after deploy)
With `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true`:
1. "best waterfront breweries" Chicago → `semantic_retrieval_v1.turn venue_concept='brewery' geo_hints=['waterfront'] outcome=ok`; brewery cards dominate; no "Good waterfront match" repetition.
2. "best izakayas in Fulton Street" Chicago → `concierge.semantic_eligible … eligibility_path=open_class open_class_place_detected=True`; `semantic_retrieval_v1.turn venue_concept='izakaya' location_modifiers=['Fulton Street']`; izakaya cards (or honest empty result with limited verified matches wording).
3. "nice sushi restaurants with a waterfront view" Chicago → unchanged tapas/sushi-first behavior; no claimed view; ambiguity_flags include `view_not_structurally_verifiable`.
4. "romantic tapas but not too loud" Chicago → unchanged; concept=tapas; reasons safe.
5. Place-like asks "tea houses", "dessert bars", "record stores", "arcades", "coffee shops good for reading" → all enter semantic retrieval.
6. Non-place asks "what is the currency exchange rate", "what to pack", "how many days" → `concierge.semantic_skip semantic_skip_reason=intent_not_eligible open_class_place_detected=False`.

### Production log validation after merge
- **Open-class entry**: `concierge.semantic_eligible … open_class_place_detected=True eligibility_path=open_class`
- **Skip path (non-place)**: `concierge.semantic_skip … open_class_place_detected=False`
- **Turn log**: `semantic_retrieval_v1.turn … venue_concept='brewery' location_modifiers=[] geo_hints=['waterfront'] retrieval_queries=['brewery Chicago waterfront', …] rejection_stats={..., 'wrong_category_low_subtype_fit': N} outcome=ok`

### Scope (not changed in this PR)
- No PR-3 batched LLM reasoning.
- No SQL, no schema changes.
- No frontend changes.
- No Yelp/Foursquare, no Tavily card minting, no editorial fabrication.
- Existing Google verification trust gates (place_id + OPERATIONAL + maps URI) unchanged.

**Supabase SQL**: No.

---

## Last change (2026-05-05) — PR-2.5 Semantic Retrieval Coverage + No-Silent-Fallback Fix

### Production finding (post-PR #235 validation)
`semantic_retrieval_v1.turn` logs appeared for "romantic tapas but not too loud" and "nice sushi restaurants with a waterfront view", but for "best breweries" and "best breweries along the waterfront" only the outer `concierge.request` log appeared with `response_type=place_recommendations` and ~6.7s latency. Semantic retrieval was silently bypassed.

### Root cause
`_NIGHTLIFE_PAT` in `concierge.py` contained `"brewery"` (singular) but **not** `"breweries"` (plural) or common variants (`brewpub`, `taproom`, `craft beer`). Therefore:
- `_detect_intent("best breweries")` → fell through all patterns → returned `INTENT_GENERAL`
- `INTENT_GENERAL` is **not** in `_FAST_DYNAMIC_INTENTS`
- Semantic retrieval was never triggered; request fell to the slow/LLM path
- No log explained the skip — silent failure

### Fix (3 files changed)

**`backend/app/services/concierge.py`**
- Added `"breweries"`, `"brewpub"`, `"brewpubs"`, `"taproom"`, `"taprooms"`, `"craft beer"` to `_NIGHTLIFE_PAT`. This is a plural-form completeness fix, not a closed eligibility bucket — once routed to `INTENT_NIGHTLIFE`, the open-vocabulary semantic pipeline takes over.
- Added `concierge.semantic_skip` log (with `semantic_skip_reason=intent_not_eligible` or `no_destination`) when the semantic flag is ON but a request bypasses semantic retrieval. This makes silent bypasses observable in production.
- Added `fallback_reason` and `fallback_path` fields to existing fallthrough/fallback log lines (`fast_dynamic_or_slow`, `slow_pipeline`).

**`backend/app/concierge/retrieval_planner.py`**
- Added `"breweries"`, `"brewpubs"`, `"taprooms"`, `"craft beer"` as direct synonym expansion keys so that if any of these ever become the primary concept label (e.g., singularization edge case), they expand to the correct brewery variant queries.

### Tests added
- `TestBreweryIntentRouting` (test_concierge.py): 8 parametrized queries (`"best breweries"`, `"best breweries along the waterfront"`, `"craft beer"`, `"brewpubs"`, `"taprooms"`, etc.) all route to `INTENT_NIGHTLIFE`; existing tapas/sushi routing unaffected.
- `TestSemanticSkipObservability` (test_concierge.py): `concierge.semantic_skip` logged with `intent_not_eligible` when flag ON and intent not eligible; no spurious skip log when flag OFF.
- `TestBreweryRetrievalPlannerCoverage` (test_semantic_retrieval_v1.py): brewery queries generate brewery-variant retrieval queries; waterfront ask preserves geo hint; synonym expansion key present.
- `TestBreweryEntityGating` (test_semantic_retrieval_v1.py): invalid/closed brewery places still rejected; valid OPERATIONAL brewery accepted.
- `TestBreweryReasonNoUnsupportedClaims` (test_semantic_retrieval_v1.py): no "confirmed waterfront" claim in reason text.
- `TestMoreOptionsFollowUpBehavior` (test_semantic_retrieval_v1.py): "more options" dedupes prior identity keys; "top 3" (max_cards=3) returns ≤ 3 cards.

### Validation cases (all must pass in production)
1. "best breweries" Chicago → `semantic_retrieval_v1.turn` log, ≥3 verified brewery cards
2. "best breweries along the waterfront" Chicago → `semantic_retrieval_v1.turn`, brewery cards, honest waterfront wording
3. "romantic tapas but not too loud" → unchanged (still semantic, tapas-first)
4. "nice sushi restaurants with a waterfront view" → unchanged (still semantic, sushi-first)
5. "more options" after cards → dedupes prior cards
6. "top 3" follow-up → ≤3 cards returned

### Production log validation after merge
After enabling `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=true` on Railway:
- **Good path**: `semantic_retrieval_v1.turn ... query='best breweries' ... outcome=ok final_card_count≥3`
- **Skip path (now visible)**: `concierge.semantic_skip intent=... semantic_skip_reason=intent_not_eligible` (if a new unrecognized query type falls through)
- **Fallback path (now visible)**: `concierge.semantic_retrieval_v1: no_verified_cards, falling_through ... fallback_reason=no_verified_cards fallback_path=fast_dynamic_or_slow`
- **Regression check**: No `concierge.semantic_skip` for brewery, sushi, or tapas queries

### Scope (not changed in this PR)
- No PR-3 LLM batched reasoning
- No SQL, no schema changes
- No frontend changes
- No Yelp/Foursquare
- No vector search

**Supabase SQL**: No.

---

## Last change (2026-05-05) — Merge-gate audit hardening for PR #235 semantic retrieval v1

### Audit fixes applied
- Enforced strict trust invariant in Place Entity Layer: `businessStatus` is now mandatory and must be `OPERATIONAL`; missing status is rejected (no synthesized default).
- Preserved deterministic semantic safe reasons (`deterministic_safe_v1`) through concierge response assembly so explicit wrappers like “Verify waterfront before booking.” are not scrubbed by generic banned-copy sanitizer.
- Tightened outage semantics: when semantic provider fanout fully fails, semantic returns `SOURCE_UNAVAILABLE` and concierge no longer falls through into legacy card-minting paths for that turn.
- Hardened provider fanout timeout behavior by catching iterator-level `concurrent.futures.TimeoutError` and returning partial successes plus explicit incomplete records instead of aborting the turn.
- Card assembly now propagates verified provider `business_status` from entity records instead of hardcoding `OPERATIONAL`.

### Tests
- Updated semantic retrieval test suite assertions for strict OPERATIONAL gating and unavailable-source behavior.
- Added coverage for missing/closed business status rejection and OPERATIONAL acceptance.
- Added coverage proving deterministic semantic reason-source preservation helper behavior.

**Supabase SQL**: No.

---

## Last change (2026-05-05) — AI Concierge Semantic Place Intelligence v2 PR-2 (Semantic Retrieval v1 verified-card pipeline)

### Problem
Chicago + "best breweries along the waterfront" → text-only, no addable cards. Logs showed `card_pool_size=0`, `sources_used=[]`. The classifier recognized a place ask, but the existing bucket/router execution brain could not represent "brewery" as an open-vocabulary concept and returned zero cards.

### Root-cause fix
Built a new **Semantic Retrieval v1** pipeline behind a feature flag. The new path replaces the category-bucket execution brain with:
1. Open-vocabulary **ExperienceFrame** extraction (deterministic, no LLM, no closed enum)
2. **RetrievalPlanner** generating 1–3 provider-friendly Google Text Search queries from the frame
3. Parallel **provider fanout** (concurrent.futures, per-call deadlines, one failure doesn't kill the turn)
4. **Verified Place Entity Layer** — hard gates: Google place id + OPERATIONAL + maps URI; NOT rejected for broad types or lower rating
5. **SemanticRanker v1** — deterministic feature-based score (subtype_fit 0.34 dominates popularity 0.06, no category hard gate)
6. **MinimalEvidenceBundle** — structured facts only, no invented attributes
7. **SafeReasonBuilder v1** — honest, ask-anchored, never invents views/ambiance/awards
8. **TrustGate** final pass — drops any card missing the three identity fields
9. **Structured observability** — one log line per turn, debuggable in one pass

### Feature flag
`CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED` (Settings field: `concierge_semantic_retrieval_v1_enabled`)
- Default: `False` — existing behavior is completely unchanged when flag is OFF
- When ON: semantic pipeline runs for place-recommendation asks (same intent set as fast_dynamic). Falls back to fast_dynamic or slow pipeline if semantic returns no cards.
- **Rollback**: set `CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED=false`

### Behavior matrix

| Scenario | Flag OFF | Flag ON |
|---|---|---|
| "best breweries" Chicago | Existing pipeline | Semantic pipeline → brewery cards |
| "best breweries along the waterfront" Chicago | No cards (root-cause bug) | Brewery cards, honest geo wording |
| "romantic tapas but not too loud" | Existing pipeline | Tapas-first cards, verify-quiet wrapper |
| "nice sushi restaurants with waterfront view" | Existing pipeline | Sushi-first cards, no invented view |
| Semantic returns 0 cards | N/A | Falls through to fast_dynamic or slow |
| All provider queries fail | N/A | Honest empty response, no fake cards |
| Refine/follow-up turns | Existing pipeline | Existing pipeline (unchanged) |

### Files changed
- `backend/app/concierge/frame_extractor.py` (NEW) — open-vocabulary ExperienceFrame extraction
- `backend/app/concierge/retrieval_planner.py` (NEW) — RetrievalPlanner v1
- `backend/app/concierge/provider_executor.py` (NEW) — parallel Google Text Search fanout
- `backend/app/concierge/place_entity_layer.py` (NEW) — Verified Place Entity Layer + trust gates
- `backend/app/concierge/ranker.py` (NEW) — SemanticRanker v1 + MinimalEvidenceBundle
- `backend/app/concierge/safe_reason_builder.py` (NEW) — SafeReasonBuilder v1
- `backend/app/concierge/semantic_retrieval.py` (NEW) — pipeline orchestrator + TrustGate + observability
- `backend/tests/test_semantic_retrieval_v1.py` (NEW) — 46 tests across all pipeline stages
- `backend/app/core/config.py` (MODIFIED) — added `concierge_semantic_retrieval_v1_enabled: bool = False`
- `backend/app/services/concierge.py` (MODIFIED) — wired semantic pipeline in `_fetch_live_research()`

### Tests (46 total, all passing)
- Frame extraction: brewery, waterfront, tapas+quiet, sushi+view, fallback-on-error, open vocabulary
- Retrieval planner: concept preservation, geo variants, query caps, destination inclusion
- Provider executor: fanout, one-timeout resilience, all-timeout → empty, no-key fallback
- Entity layer: missing id/URI/status rejected; duplicates deduped; broad types NOT rejected
- Ranker: brewery > bar, brewery-near-water > inland-brewery, tapas > cocktail bar, sushi > waterfront generic, popularity cannot overpower subtype_fit
- Safe reasons: ask anchor present, no invented views, verify wrapper for weak attributes
- Integration: ≥3 verified brewery cards from mocked Google, honest waterfront wording, tapas first, sushi first, no fake cards on failure

### Explicit scope boundaries (not changed in this PR)
- No Tavily/editorial card minting
- No weakened Google trust gates
- No SQL
- No frontend UI changes
- No Supabase schema changes
- No batched LLM reasoning (PR-3)
- No Yelp/Foursquare
- No vector search
- No personalization
- Follow-up engine unchanged (existing refine_previous and more_options paths unaffected)

**Supabase SQL**: No.

---

## Last change (2026-05-05) — AI Concierge Semantic Place Intelligence v2 PR-1 (schema-tolerant concierge request logging)

### Problem diagnosed from Railway logs
Live Supabase schema cache can be missing newly expected columns (for example `intent_classifier_version`) while app code already writes them. `persist_concierge_request_log()` attempted a single insert and logged `concierge.request_log.persist_failed` on every affected request, creating noisy per-turn errors that obscured retrieval/ranking debugging.

### Root-cause fix
`backend/app/concierge/logging.py` now handles PostgREST missing-column/schema-cache errors (`PGRST204` / `PGRST116`) as runtime schema drift during observability writes:

1. Attempt insert with full payload.
2. If PostgREST reports missing column, extract offending field name from message/details/hint.
3. Drop the offending field from payload and retry.
4. Repeat up to a small cap (4 attempts) so multiple missing columns are handled in one request.
5. Emit one warning per process per `table+column` pair using `concierge.logging.schema_drift`.
6. Unexpected/non-schema exceptions still log `concierge.request_log.persist_failed` and never raise to caller.

### Behavior matrix

| Scenario | Behavior |
|---|---|
| Missing `intent_classifier_version` (`PGRST204`) | Drop field, retry, insert succeeds if no additional drift |
| Missing two fields across retries | Drop first missing field, retry, drop second, retry, then succeed |
| Same missing column repeats across requests | `concierge.logging.schema_drift` emitted once per process for that table+column |
| Unexpected DB/runtime exception | `concierge.request_log.persist_failed` logged; response path continues |

### Files changed
- `backend/app/concierge/logging.py`
- `backend/tests/test_concierge_logging_schema_tolerance.py`

### Operational note
This PR is runtime-tolerance only (Phase 1 observability hardening). Live Supabase still needs the existing migration 004 applied to align schema permanently.

**Supabase SQL**: No.

---

## Last change (2026-05-04) — AI Concierge Fast Dynamic Place Search v1

### Problem diagnosed from wife-testing
Two product failures:
1. **"tapas bar" → cocktail bars**: `_detect_intent("tapas bar")` matched `_NIGHTLIFE_PAT` on the word "bar", routing to `INTENT_NIGHTLIFE` and building the query `"best cocktail bars and nightlife in Chicago 2026"`. The user's literal intent (tapas/Spanish small plates) was lost.
2. **126s latency**: Old pipeline: Tavily article extraction (~2.6s) → serial candidate verification via Tavily (~40-60s cumulative) → serial Google Places verification per candidate (~50s cumulative) → per-card reason generation (~70s). Total: ~127s.

### Fix: fast_dynamic_place_search.py (feature-flagged)

**Feature flag**: `CONCIERGE_FAST_DYNAMIC_PLACE_SEARCH_V1_ENABLED` (default: `False`)
Settings name: `concierge_fast_dynamic_place_search_v1_enabled`

**When OFF**: existing behavior unchanged.  
**When ON**: fast pipeline for restaurant/nightlife/hidden_gems/luxury/romantic/family/michelin intents.

#### Fast pipeline architecture

1. **Natural-language intent extraction (deterministic)**  
   `parse_place_query(user_query, destination)` returns `ParsedPlaceQuery` with:
   - `canonical_query` — the user's literal ask (preserved verbatim)
   - `search_query` — canonical_query + destination (sent directly to Google)
   - `cuisine` — detected subtype ("tapas", "sushi", "seafood", ...)
   - `place_type` — "restaurant" | "bar" | "restaurant_or_bar"
   - `vibe`, `constraint`, `negative_constraint`
   
   "tapas bar" → cuisine="tapas", place_type="restaurant_or_bar", search_query="tapas bar Chicago"  
   "cocktail bars" → place_type="bar", search_query="cocktail bars Chicago"  
   "romantic tapas but not too loud" → cuisine="tapas", vibe="romantic", negative="not too loud"  
   Negative constraints are stripped from the search query so Google isn't confused.

2. **Direct Google Places text_search**  
   Single call to `places.googleapis.com/v1/places:searchText` with:
   - `textQuery = canonical_query + destination`
   - `maxResultCount = 15`
   No Tavily article extraction. No serial Tavily verification loop.

3. **Filter and rank**  
   - businessStatus != OPERATIONAL → excluded  
   - `_category_score()` < 0.2 → excluded (intent mismatch gate)  
   - `prior_identity_keys` dedup → already-shown cards excluded  
   - Ranked: 0.7 × category_score + 0.3 × bayesian_score

4. **Dynamic deterministic reason building**  
   `_build_dynamic_why()` — always references the user's specific ask:  
   - "tapas bar" → "A stronger tapas/small-plates match than a generic cocktail bar in West Loop."  
   - "sushi + waterfront" → "Best fit if you want sushi with a polished setting near waterfront; verify exact seating when booking."  
   - "romantic tapas" → "Fits the tapas brief with a dinner-date feel in River North."  
   Never invents awards, Michelin mentions, or unverified vibes.  
   No per-card LLM calls. No `build_why_pick_with_structured_evidence` in fast path.

#### Trust gates (unchanged)
- Only OPERATIONAL Google Places results become addable cards.
- `_category_score < 0.2` is rejected (e.g., a cocktail bar for a tapas query scores 0.25 — still included as a match, scored below tapas-specific results).
- Cards come directly from Google; no free-form/fabricated cards.
- `prior_identity_keys` prevents re-showing already-seen cards.

#### Timing logs
`fast_dynamic_place_search.timing` emits:  
`fast_dynamic_enabled`, `extraction_ms`, `google_search_ms`, `google_verify_or_details_ms`, `evidence_enrichment_ms`, `reason_generation_ms`, `total_ms`, `candidate_count`, `verified_count`, `filtered_count`, `final_unique_count`, `pool_hit`, `provider_call`, `reason_mode`

#### Latency improvement
- Old: ~126s (serial Tavily extraction + serial Google verification + LLM reasons)
- New: ~3–8s (single Google text_search + deterministic reasons)
- Follow-up / pool hit: < 1s (pool logic unchanged, works with fast cards)

#### Pool / cache compatibility
Fast-path results populate `live_result.restaurants` the same way the old path does. The existing `ContinuationResultPool` and `prior_identity_keys` dedup in `routes/ai.py` work unchanged. Cache keys separate cleanly: "tapas bar Chicago" vs "cocktail bars Chicago" vs "seafood restaurants Chicago".

#### Rollback
Set `CONCIERGE_FAST_DYNAMIC_PLACE_SEARCH_V1_ENABLED=false` (or remove the env var). The existing slow pipeline resumes with zero code changes required.

### Behavior matrix (flag ON)

| User query | Detected | Search query sent to Google | Reason style |
|-----------|---------|---------------------------|-------------|
| "tapas bar" | cuisine=tapas, type=restaurant_or_bar | "tapas bar Chicago" | "tapas/small-plates match" |
| "nice sushi restaurants with a waterfront view" | cuisine=sushi, constraint=waterfront | "nice sushi restaurants with a waterfront view Chicago" | mentions sushi + waterfront |
| "romantic tapas but not too loud" | cuisine=tapas, vibe=romantic, neg=loud | "romantic tapas Chicago" | "dinner-date feel" |
| "seafood restaurants" | cuisine=seafood | "seafood restaurants Chicago" | seafood-specific |
| "cocktail bars" | type=bar | "cocktail bars Chicago" | cocktail bar |
| "Italian restaurants" | cuisine=italian | "Italian restaurants Chicago" | italian-specific |
| "Mexican restaurants" | cuisine=mexican | "Mexican restaurants Chicago" | mexican-specific |
| "more options" | continuation (pool/provider) | canonical from prior | unchanged |
| "top 3" / "best one" / "compare" | refine_previous (flag: context_v1) | no provider call | card reuse |

### Remaining risks
- Fast path requires GOOGLE_PLACES_API_KEY; falls through to slow path when unavailable.
- Google text_search returns up to 15 results; niche queries in small cities may return fewer.
- Constraint verification (e.g., "waterfront view") is honest — reason says "verify when booking" rather than asserting the view exists.
- In-memory singleton; process restart clears it (same as before).

### What was added / changed
- **`backend/app/core/config.py`** — `concierge_fast_dynamic_place_search_v1_enabled: bool = False`
- **`backend/app/services/fast_dynamic_place_search.py`** — new fast pipeline
- **`backend/app/services/concierge.py`** — `_fetch_live_research()` checks flag and delegates to fast path
- **`backend/tests/test_fast_dynamic_place_search.py`** — 46 tests covering parsing, scoring, reasons, trust gates, feature flag, dedup

**Supabase SQL**: No.

---

## Previous change (2026-05-04) — AI Concierge Conversational Context v1 PR 3 ("More options" fast continuation: pool + early dedup + bounded refill)

### Problem diagnosed from Railway logs
Two root causes behind "only 1 new verified place after more options":

**Root cause 1 (shallow pool / redundant provider calls)**
Continuation query was `"more mexican restaurants"` — a different cache key from the initial
`"mexican restaurants"` search. Tavily returned the same ~10 articles both times, yielding
overlapping candidates. After 27 prior identity keys excluded 9 of 10 results, only 1 unique
card remained. The query itself was surfacing the same shallow provider pool every time.

**Root cause 2 (latency: ~78 s)**
Reason generation and enrichment ran for ALL 10 candidates BEFORE `_exclude_prior_verified_cards`
ran. This wasted ~70 s enriching 9 candidates that were discarded immediately afterwards.

### Fix

#### 1. Canonicalize provider query (removes "more " prefix)
`_contextualized_query = f"more {_query_hint}"` changed to `_canonical_query = _query_hint`
(e.g., `"mexican restaurants"`, not `"more mexican restaurants"`). This:
- Aligns cache key with initial search → cache hit reuse when query is fresh
- Reduces provider query variation → cleaner article extraction

#### 2. In-memory result pool (`backend/app/concierge/result_pool.py`, new)
`ContinuationResultPool` singleton keyed by `(trip_id, canonical_query)` with 10-min TTL.
- `store(trip_id, canonical_query, buckets)` — called after each successful continuation search
- `pop(trip_id, canonical_query)` → `(buckets, total)` or `None` — returns raw pool cards
- `clear(trip_id)` — removes all pool entries for a trip

Pool fast path: if pool has unused verified cards (not in `prior_identity_keys`), returns them
immediately without a provider call. Target: < 2 s backend time on pool hit.

**Documented limitations:**
- In-memory only; pool is lost on process restart or Gunicorn worker recycle.
- Not shared across processes; multi-worker deployments see independent pools. Pool hit rate
  depends on sticky-session or single-worker config (Railway single-replica benefits fully).
- TTL: 10 min.

#### 3. Early dedup before reason_generation
`LiveResearchService.fetch()` now accepts `prior_identity_keys: Optional[frozenset]`.
After Phase 3 (Google Places verification — where stable place IDs are available), candidates
matching prior identity keys are removed from `google_verifications` and `verified_candidates`
BEFORE `normalize_hits()` / reason_generation. This eliminates wasted enrichment for cards
that would be discarded anyway.

Helper `_gv_identity_keys_from_verification(name_lower, gv)` computes `pid:/gmaps:/name_addr:`
keys from a `GooglePlaceVerification` — mirrors the schema in `ai._card_identity_keys`.

#### 4. Bounded refill (≤ 2 variant queries)
When `_final_count < 2` after canonical search + dedup, the continuation path tries up to 2
canonical variant queries ("best {subtype}", "popular {subtype}") via `service.search()`.
Each refill uses the same Google verify gate. Results are aggregated and de-overlapped.
Maximum 3 total provider calls (1 canonical + 2 refill). No loops.

#### 5. Per-stage timing instrumentation
`fetch()` logs `live_research.timing` with:
`cache_ms`, `provider_fetch_ms`, `extraction_ms`, `google_verify_ms`, `prior_dedup_ms`,
`early_dedup_count`, `reason_generation_ms`, `total_ms`, `final_unique_count`.

Continuation block in `ai.py` logs:
- Pool check: `result_pool_hit`, `pool_size_before`, `pool_unique_count`, `pool_ms`
- Provider: `provider_ms`, `dedup_ms`, `final_unique_count`, `total_ms`
- Refill: `variant`, `batch_added`, `total_unique`, `refill_ms`

### Behavior matrix (post-PR 3)

| Query | Path | Provider calls |
|-------|------|---------------|
| "Mexican restaurants" → initial | new_search → provider | 1 |
| "more options" (pool hit, unique cards) | pool fast path | 0 |
| "more options" (pool miss, canonical gives unique) | provider (canonical query) | 1 |
| "more options" (all duplicates) | canonical + up to 2 refill variants | ≤ 3 |
| "more options" (only 1 verified unique) | returns 1 card, no fabrication | ≤ 3 |
| "Italian restaurants" → more options | canonical "italian restaurants" | ≤ 3 |
| "cocktail bars" → more options | canonical "cocktail bars" | ≤ 3 |
| "top 3" / "best one" / "compare these" | refine_previous card reuse | 0 |

### Remaining risks
- Pool is in-memory: multi-instance Railway deploys or dyno restarts will miss the pool.
  Fall-through to provider path is safe; just slower.
- Refill variant queries ("best X") may surface overlapping Tavily articles in small markets
  with few places. After dedup, 0–1 new cards may be the honest result — this is correct
  behavior, not a bug.
- The canonical query change means the cache key for a fresh initial search ("mexican
  restaurants") now matches continuation — cache hit on canonical is intentional and correct.

### What was added / changed
- **`backend/app/concierge/result_pool.py`** — new, in-memory continuation pool
- **`backend/app/services/live_research.py`** — `prior_identity_keys` param to `fetch()`,
  `_gv_identity_keys_from_verification()` helper, per-stage timing, early dedup after Phase 3
- **`backend/app/services/concierge.py`** — `prior_identity_keys` optional param to `search()`
  and `_fetch_live_research()`
- **`backend/app/routes/ai.py`** — reimplemented `more_options_continuation` block:
  canonical query, pool check, early dedup, bounded refill, pool store, timing logs;
  new helpers `_build_prior_identity_keys_set`, `_filter_pool_buckets_by_identity`,
  `_build_place_response_from_pool`, `_refill_variant_queries`, `_response_identity_keys`
- **`backend/tests/test_concierge_more_options.py`** — pool isolation fixture, updated query
  assertions for canonical query (removed "more " prefix), 8 new required tests
- **`backend/tests/test_result_pool.py`** — new, 11 unit tests for ContinuationResultPool
- **`backend/tests/test_concierge_context_resolver.py`** — updated sequence test for new provider
  call contract

---

## Previous change (2026-05-04) — AI Concierge Conversational Context v1 PR 2.5 ("More options" category-preserving continuation)

### Staging QA bug found
After enabling `concierge_context_v1_enabled` in a safe staging environment, the manual wife-test sequence found:
1. "Cocktail bars" → new_search, provider call, verified place cards. ✓
2. "Top 3" → refine_previous, card reuse, no provider call. ✓
3. "Best one" → refine_previous, card reuse, no provider call. ✓
4. "Compare these" → refine_previous, card reuse, no provider call. ✓
5. **"More options" → context layer logs `turn_mode=new_search` correctly, but UI returns generic Chicago early-June advice text and no structured cards.** ✗

### Root cause
The classifier correctly returns `new_search` for "more options" (it's in `_NEW_SEARCH_OVERRIDE_PATTERNS`). However, the bare string `"More options"` has no category signal. When passed to `route_prompt()`, it scored below the `place_recommendations` threshold and was classified as `trip_advice` or `unsupported`, returning a template response instead of a provider-backed place search.

### Fix
Added a narrow continuation intercept in `build_typed_concierge_response()` that fires only when:
- Feature flag `concierge_context_v1_enabled` is ON
- `turn_mode == "new_search"` (classifier did its job correctly)
- `is_more_options_continuation(user_query, ctx)` is True (continuation phrase detected)
- `ctx.has_prior_cards` is True (prior place cards exist)

When all conditions hold:
1. `derive_category_hint(ctx.prior_card_pool)` maps the prior intent → category phrase (e.g. `nightlife` → `"cocktail bars"`)
2. Contextualized query constructed: `f"more {category_hint}"` (e.g. `"more cocktail bars"`)
3. `service.search()` called with contextualized query — full verified provider pipeline runs
4. Returns `PlaceRecommendationsResponse` with `code="more_options_continuation"`

Falls through to existing behavior (no exception raised) if:
- Category hint cannot be safely derived → logs `fall_through_reason=no_prior_category_hint`
- `service.search()` raises → logs `search_failed falling_through=true`
- Validation fails → logs `validation_failed falling_through=true`

### Supported continuation phrases
- "more options"
- "show more"
- "more like these"
- "give me more"
- "another batch"

### Intent → category hint mapping
| Intent | Provider query hint |
|--------|-------------------|
| nightlife | cocktail bars |
| restaurants | restaurants |
| michelin_restaurants | restaurants |
| hidden_gems | restaurants |
| luxury_value | restaurants |
| romantic | restaurants |
| family_friendly | attractions |
| attractions | attractions |
| hotels | hotels |

Unmapped intents (general, general_destination_research, plan_day, etc.) fall back to the dominant bucket (whichever of restaurants/attractions/hotels has the most cards). If all buckets are empty, returns None and falls through.

### Known limitation (v1)
Dedup/novelty is not implemented. If the provider returns some of the same places that appeared in the prior card pool, they will be shown again. The primary fix is "provider search happens and returns structured cards" — not perfect novelty ranking. Document as a known v1 limitation.

### What was added
- **`backend/app/concierge/context.py`**:
  - `_CONTINUATION_PATTERNS` — 5 regex patterns for continuation phrases
  - `_INTENT_TO_QUERY_HINT` — mapping dict (9 intent → hint entries)
  - `ContextWindow.prior_place_category: Optional[str]` — category hint field, populated in `build_context_window()`
  - `is_more_options_continuation(user_query, context_window) -> bool` — exported helper
  - `derive_category_hint(prior_card_pool) -> Optional[str]` — exported helper
  - `build_context_window()` updated to populate `prior_place_category`
- **`backend/app/routes/ai.py`**:
  - Import `is_more_options_continuation`, `derive_category_hint` from `app.concierge.context`
  - Continuation intercept block in `build_typed_concierge_response()` between the refine_previous card-reuse block and the router
- **`backend/tests/test_concierge_more_options.py`** — NEW: 66 tests

### Updated manual wife-test script (after enabling flag in safe environment)
1. "cocktail bars" → new_search, provider call, returns N cards
2. "top 3" → refine_previous, top_n, reuses prior cards, no provider call; `context_reuse.provider_call = false`
3. "best one" → refine_previous, best_one, returns 1 card, no provider call
4. "compare these" → refine_previous, compare, returns prior cards for comparison
5. **"more options" → continuation new search, provider call, `code="more_options_continuation"`, returns fresh place_recommendations cards**

### Observability (log lines when continuation fires)
```
concierge.context.more_options_continuation trip_id=... turn_mode=new_search provider_call=true
  original_user_query="More options" contextualized_query="more cocktail bars"
  prior_category_hint=cocktail bars source_message_id=... card_pool_size=...
```
When category hint cannot be derived:
```
concierge.more_options_continuation.fall_through trip_id=... fall_through_reason=no_prior_category_hint provider_call=true
```

### Behavior changed when flag OFF: No
### Behavior changed when flag ON: Yes (new_search + continuation phrase + prior cards → place_recommendations)
### Provider-call behavior changed: Yes — continuation path calls provider with contextualized query
### Structured card output changed: No (cards come from live provider pipeline, not mutated)
### Trust gates weakened: No
### Supabase SQL: No
### Frontend touched: No
### Backend touched: Yes (`context.py` + `ai.py` + new test file)
### Tests: 66 new passing (214 total concierge context/resolver/router/more-options tests)

---

## Last change (2026-05-04) — AI Concierge Conversational Context v1 PR 2 (feature-flagged REFINE_PREVIOUS card reuse)

### Summary
Implements card reuse for `top_n`, `best_one`, and `compare` follow-up turns behind the feature flag `concierge_context_v1_enabled` (default `False`). When the flag is ON and the classifier returns `refine_previous` with a supported rule, the prior verified card pool is reused and the provider call is skipped entirely. When the flag is OFF or conditions aren't met, behavior is identical to PR 1.

### What was added
- **`backend/app/core/config.py`**: Added `concierge_context_v1_enabled: bool = False` — feature flag, default OFF.
- **`backend/app/concierge/context.py`**: Added `prior_card_pool: Optional[Dict[str, Any]]` to `ContextWindow`. Updated `build_context_window()` to populate `prior_card_pool` from the most-recent assistant message's `structured_results`.
- **`backend/app/concierge/context_resolver.py`** — NEW module:
  - `_SUPPORTED_RULES = frozenset({"top_n", "best_one", "compare"})`
  - `_MAX_COMPARE_CARDS = 6`
  - `_card_passes_trust_gate(card)` — checks `type == "verified_place"`, `google_verification.business_status == "OPERATIONAL"`, non-empty `provider_place_id`, non-empty `google_maps_uri`. Drops cards that fail.
  - `_parse_top_n(query, pool_size)` — extracts N from "top 3" / "show me 5" / "top three" etc. Clamps to [1, pool_size].
  - `RefineResolved` dataclass — returned on successful resolution (restaurants, attractions, hotels, pool metadata).
  - `resolve_refine_previous(ctx, rerank_rule, user_query)` — returns `RefineResolved` or `None` (fall-through).
- **`backend/app/models/concierge.py`**: Added optional `turn_mode: Optional[str]` and `context_reuse: Optional[Dict[str, Any]]` to `ConciergeSearchResponse` for additive response metadata.
- **`backend/app/routes/ai.py`**: Wired resolver into `build_typed_concierge_response()`. Uses `getattr(settings, 'concierge_context_v1_enabled', False)` for safe access. When resolver succeeds: returns `PlaceRecommendationsResponse` with reused cards, `turn_mode="refine_previous"`, `context_reuse` metadata, decision code `"refine_previous_card_reuse"`. Helper functions `_validate_reused_cards()` and `_build_reuse_summary()` added.
- **`backend/tests/test_concierge_context_resolver.py`** — NEW: 50 tests.

### Feature flag
**Name:** `concierge_context_v1_enabled`
**Default:** `False`
**Env var:** `CONCIERGE_CONTEXT_V1_ENABLED=true` to enable.

### Supported rules in PR 2
- `top_n` — returns first N verified cards from prior pool (N parsed from query)
- `best_one` — returns first 1 verified card from prior pool
- `compare` — returns prior verified cards up to `_MAX_COMPARE_CARDS = 6`

### Explicit limitations
- No `date_night` reranking yet
- No `cheapest` / `most_upscale` reranking yet
- No `rooftop` / `vegan` / `open-late` filter support yet
- No `anchor_new` behavior yet
- No frontend tag for reused turns yet
- `destination` in `ContextWindow` remains `None` (as in PR 1) — destination-mismatch reset not yet implemented

### Trust gate (per-card, before reuse)
A card is reused only if all hold:
1. `card["type"] == "verified_place"`
2. `card["google_verification"]["business_status"] == "OPERATIONAL"`
3. `card["google_verification"]["provider_place_id"]` is non-empty
4. `card["google_verification"]["google_maps_uri"]` is non-empty

Cards failing the trust gate are dropped (not patched). If all drop → fall through to provider search.

### Response metadata (when flag ON + reuse succeeds)
```json
{
  "turn_mode": "refine_previous",
  "context_reuse": {
    "provider_call": false,
    "card_pool_size": 5,
    "cards_returned": 3,
    "source_message_id": "...",
    "rerank_rule": "top_n",
    "filter_applied": null
  }
}
```

### Manual wife-test script (after enabling flag in safe environment)
1. "cocktail bars" → new_search, provider call, returns N cards
2. "top 3" → refine_previous, top_n, reuses prior cards, no provider call; `context_reuse.provider_call = false`
3. "best one" → refine_previous, best_one, returns 1 card, no provider call
4. "compare these" → refine_previous, compare, returns prior cards for comparison
5. "more options" → new_search override, provider call again

### Observability (log line extension)
When resolver succeeds:
```
concierge.context_resolver.resolved trip_id=... turn_mode=refine_previous rerank_rule=... provider_call=false pool_size_before=... pool_size_after=... source_message_id=... feature_flag_enabled=true
```
When resolver falls through:
```
concierge.context_resolver.unsupported_rule / no_pool / all_dropped_fall_through ... fall_through_reason=... provider_call=true
```

### Behavior changed when flag OFF: No
### Behavior changed when flag ON: Yes (for refine_previous + top_n/best_one/compare only)
### Provider-call behavior changed: Yes — only for the refine_previous + supported-rule path when flag is ON
### Structured card output changed: No (cards are returned as-is from prior pool)
### Trust gates weakened: No
### Supabase SQL: No
### Frontend touched: No
### Backend touched: Yes (`context.py` + new `context_resolver.py` + `routes/ai.py` + `models/concierge.py`)
### Tests: 50 new passing (747 total with pre-existing failures unchanged)

### Next PR recommendation
**PR 3**: Enable `concierge_context_v1_enabled` in the staging environment and run the manual wife-test script. After validation, consider implementing `date_night` reranking (already classified). Also consider: destination-aware reset detection (fetch trip to compare destination), and `anchor_new` provider behavior.

---

## Last change (2026-05-04) — AI Concierge Conversational Context v1 PR 1 (dark backend foundation)

### Summary
Added a dark backend foundation for AI Concierge follow-up detection. Classifies each user turn and logs the result. No behavior change: provider calls, card output, add-to-trip, and save-to-ideas flows are all identical to before.

### What was added
- **`backend/app/concierge/context.py`** — new module:
  - `TurnMode` literal: `new_search | refine_previous | anchor_new | reset`
  - `RerankRule` literal: `top_n | best_one | compare | date_night | cheapest | most_upscale | filter_constraint | none`
  - `ContextWindow` Pydantic model: `trip_id`, `destination`, `card_pool_size`, `has_prior_cards`, `source_message_id`, `prior_user_prompts`, `reset_reason`
  - `classify_turn(user_query, context_window)` — deterministic regex classifier (no LLM), deny-by-default (ambiguous → `new_search`)
  - `build_context_window(db, trip_id, destination=None)` — reads last 6 `concierge_messages` rows, finds most recent assistant message with place-producing cards, caps user prompts to 3; never raises
  - `log_context_turn(...)` — emits one `concierge.context.turn` structured log line per turn
- **`backend/app/routes/ai.py`** — wired dark classification at the start of `build_typed_concierge_response()`: builds context window, classifies, logs, then continues existing search flow exactly as before; wrapped in try/except so any failure is non-fatal

### Classifier behavior
- `reset`: unconditional for "start over" / "new chat" / "reset"
- `anchor_new`: "near the first one" / "near #1" / "around the second one" / "same area as #2" — only when `has_prior_cards`
- `refine_previous`: "top 3" / "top three" / "show me 5" / "best one" / "which one is best" / "best for date night" / "cheapest" / "most upscale" / "compare these" / "rank these" — only when `has_prior_cards` AND no new_search override signal present
- `new_search` (deny-by-default): no prior cards, OR "more options" / "things to do" / named category (restaurants/bars/etc.) / "in/near/around [location]" / temporal context

### Observability
Each request logs one `concierge.context.turn` line with: `trip_id`, `turn_mode`, `rerank_rule`, `card_pool_size`, `has_prior_cards`, `provider_call_expected_for_future_mode`, `source_message_id`, `reset_reason`.

### Current limitations / TODOs
- `destination` in `ContextWindow` is always `None` in PR 1 — no extra trip fetch is done (would require `_fetch_trip(trip_id, user_id)` call). Reset-on-destination-mismatch is therefore not implemented; add a TODO for PR 2.
- `provider_call_expected_for_future_mode` is `True` for `new_search` and `reset`, `False` for `refine_previous` and `anchor_new` — this is logging-only; actual call skipping is deferred to future PRs.
- Anchor-based search behavior is not implemented; `anchor_new` is classified and logged only.

### Next PR recommendation
**PR 2**: Implement `REFINE_PREVIOUS` behind a feature flag for `top_n`, `best_one`, and `compare` rules only. When the flag is enabled and `turn_mode == refine_previous`, reuse the `card_pool` from the prior assistant message's `structured_results` (already persisted), rerank/subset the cards, and skip the provider call. Test with the manual wife-test sequence:
1. "cocktail bars" → `new_search`, provider call, returns N cards
2. "top 3" → `refine_previous`, top_n, reuses prior cards, no provider call
3. "best for date night" → `refine_previous`, date_night, reranks prior cards
4. "more options" → `new_search`, provider call again

### Behavior changed: No
### Provider-call behavior changed: No
### Structured card output changed: No
### Supabase SQL: No
### Frontend touched: No
### Backend touched: Yes (`context.py` new module, `ai.py` dark wiring)
### Tests: 65 new passing; 25 pre-existing failures in unrelated files (test_restaurant_search_diagnostics, test_trip_days, test_itinerary_auth_scope, test_concierge_router_v2, test_concierge_observability) unchanged

---

## Last change (2026-05-03) — Fix: Wire /search/restaurants to live Google Places provider (production blocker)

### Root cause
After the prior mock-removal hotfix, `search_restaurants` in `backend/app/services/search.py` had **no live provider path**. On every cache miss it returned `[]` with `source_status=no_provider`. `GooglePlacesService` in `google_places.py` existed for single-venue concierge verification only — it was never wired into the restaurant search path. Production showed empty state because the real Google Places API key (`GOOGLE_PLACES_API_KEY`) was present on Railway but was never called.

### Fix
**Backend only** (`search.py`):
- Added `import httpx` at module level (was already in `requirements.txt`).
- Added `_RESTAURANT_SEARCH_FIELD_MASK` (includes `priceLevel`, `primaryType` in addition to the base verification mask).
- Added `_PRICE_LEVEL_MAP` (Google New API string enum → integer 0–4).
- Added `_GOOGLE_TYPE_TO_CUISINE` (Google Places `primaryType` / `types` → human-readable cuisine label).
- Added `_fetch_restaurants_google_places(req, api_key, *, timeout)` — a standalone function that:
  - Queries `POST https://places.googleapis.com/v1/places:searchText` with `"restaurants in {location}"` (or `"{cuisine} restaurants in {location}"` when cuisine is specified).
  - Filters to `businessStatus == "OPERATIONAL"` places only.
  - Maps each place to `RestaurantResult` with `source="google_places"`, canonical `provider_place_id`, `place_id`, `google_maps_uri`, and `booking_url` pointing to `googleMapsUri` (fallback: `place_id` URL — never a loose name+city query URL).
  - Applies cuisine filter after collecting all results; if filter would drop everything, returns all (prevents empty Explore when cuisine label doesn't exactly match Google type).
  - Fails closed to `[]` on any HTTP error, import error, or empty API response.
  - Never returns mock data.
- Updated `search_restaurants` on cache miss:
  - Reads `GOOGLE_PLACES_API_KEY` from env.
  - Logs `provider_configured=True/False` before calling.
  - Calls `_fetch_restaurants_google_places` when key is present.
  - Caches real results with `source="google_places"`.
  - Does NOT cache empty results (provider failure or no results).
  - Logs full count contract: `raw_candidates`, `verified_candidates`, `returned`, `cache_status`, `source_status`.
  - All prior mock-bypass and cache-hit logic preserved unchanged.

### Lesson: After mock removal, search_restaurants must be wired to a real provider path
- Removing the mock fallback without wiring a live provider causes fail-closed empty state on every cache miss.
- The Google Places provider already existed in `google_places.py` for verification; reusing the same endpoint (`places:searchText`) for direct restaurant discovery avoids a parallel implementation.
- `GOOGLE_PLACES_API_KEY` is the env var name for both code (`os.getenv("GOOGLE_PLACES_API_KEY", "")`) and Railway config — these must match exactly.
- Real Google Places results carry `source="google_places"` and will not be discarded by the mock-bypass check (`all(source == "mock")`).
- `_fetch_restaurants_google_places` is a free function (not a method), taking `api_key` explicitly, so it is testable without a SearchService instance.

### Files changed
- `backend/app/services/search.py` — added `httpx` module-level import, `_RESTAURANT_SEARCH_FIELD_MASK`, `_PRICE_LEVEL_MAP`, `_GOOGLE_TYPE_TO_CUISINE`, `_fetch_restaurants_google_places`; updated `search_restaurants` to call live provider on cache miss
- `backend/tests/test_restaurant_search_diagnostics.py` — rewrote: updated pre-existing tests that seeded from cold miss (now uses `_CacheHitDB` with real payloads); added 31 total focused contract tests covering all 10 required scenarios
- `backend/tests/test_explore_snapshot.py` — fixed 2 tests that used `source="mock"` in cache payloads; changed to `source="google_places"` with canonical identity fields so they correctly test cache-hit re-scoring without triggering mock-bypass

### Supabase SQL: No
### Backend touched: Yes (`search.py` — provider wiring; tests updated)
### Frontend touched: No

---

## Last change (2026-05-03) — Hotfix: Explore Restaurants showing mock/fake cards (Bangkok Garden, Corner Brew, Spice Route)

### Root cause
`_mock_restaurants()` in `backend/app/services/search.py` is the exclusive fallback when no live restaurant provider (e.g., Google Places) is configured. On a cache miss, `search_restaurants` called `_mock_restaurants` and cached the result in Supabase `research_cache`. The mock data included venue names like "Bangkok Garden Chicago", "Corner Brew Café Chicago", "Spice Route Chicago", fake addresses ("715 Main St, Chicago"), huge fake review counts (14k–75k), tags ("Must Try", "Local Favorite", "Budget Friendly"), and scores in the 80–90 range.

Critically, `_mock_restaurants` set `provider_place_id = f"mock-{slug}-{city}"` and `google_maps_uri = f"https://www.google.com/maps/place/?q=place_id:mock-..."` — fake-but-plausible identity fields that **passed the frontend trust gate** (`Boolean(googleMapsUri || providerPlaceId || placeId)`). These mock restaurants were then saved to `trips.metadata.explore_snapshot` and hydrated as visible cards on every subsequent page load.

The previous PR (PR #216) fixed the NameError on cache hit — which made the cache correctly return the 12 mock results instead of crashing — directly exposing the mock data as visible cards.

### Three-layer fix

**Layer 1 — Backend (`search.py`):**
- `search_restaurants` on cache miss: returns `[]` instead of calling `_mock_restaurants`. No real provider = no data; mock data must never reach the production API.
- `search_restaurants` on cache hit: if ALL cached items have `source="mock"`, discards the cache and returns `[]` (logged as `cache_status=mock_bypass`). This purges stale mock entries from `research_cache` on first request.
- `_mock_restaurants` stays in the file — it's still callable for isolated unit tests but must not be used in production runtime.

**Layer 2 — Frontend (`api.ts`) — defense-in-depth:**
- `RawRestaurantResult` interface: added `source?: string` field.
- `searchRestaurants`: added `nonMockRaw` pre-filter that drops any result with `source === "mock"` before mapping. The `verified` filter also rejects entries with `providerPlaceId` starting with `"mock-"`.
- `fetchExploreSnapshot` restaurant mapper: added `isMockEntry` guard that returns `null` for snapshot entries where `providerPlaceId.startsWith("mock-")` or `source === "mock"`. Stale mock snapshots are quarantined → `restaurants = []` → `hasHealthyRestaurants = false` → self-heal triggers on next load.
- `saveExploreSnapshot`: added `.filter((r) => !r.providerPlaceId?.startsWith("mock-"))` before the `.map(...)` to prevent mock restaurants from being written to the snapshot.

**Layer 3 — Stale snapshot recovery:**
- With both backend and snapshot mapper changes, an existing trip with mock restaurants in `explore_snapshot` will: (1) quarantine mock entries on snapshot load → `restaurants = []`, (2) trigger self-heal live search → backend returns `[]`, (3) save `[]` to snapshot replacing mock data. Future loads follow the same path until a live provider is configured.

### Lesson: Explore Restaurants must never fall back to mock/demo cards in production
- **Mock/demo restaurants must never render in production Explore Restaurants.** The fallback for "no provider configured" must be an empty list with a clear status, not fabricated venue data.
- **Stale mock snapshots must be quarantined.** Mock identity fields (`provider_place_id = "mock-..."`) are the detection marker. Any snapshot entry with a `mock-` prefixed providerPlaceId must be rejected by `fetchExploreSnapshot` before the trust gate runs.
- **`source="mock"` on API results is the primary signal.** The backend's `SearchResult` base class has always had `source: str` — this field must be checked at the API boundary before mapping.
- **Never set `source_status="ok"` on mock data.** Mock fallbacks logged `source_status=ok` which made them look like verified provider results. The no-provider path now logs `source_status=no_provider`.

### Self-heal behavior for existing trips with mock snapshots
1. `fetchExploreSnapshot` loads snapshot → `isMockEntry` guard filters all 12 mocks → `restaurants = []`
2. `hasHealthyRestaurants = false` → `shouldFetchRestaurants = true`
3. `searchRestaurants(destination)` → backend cache bypass (mock_bypass) → cache miss → no provider → `[]`
4. `setCandidateRestaurants([])` → Explore shows "No restaurants found" (empty state, correct)
5. `saveExploreSnapshot` with `[]` restaurants replaces stale mock snapshot
6. All subsequent loads: snapshot has `[]` → self-heal fires once per load, returns `[]`
7. When a live provider is configured: first miss returns real data → saved to snapshot → no further self-heal needed

### Files changed
- `backend/app/services/search.py` — `search_restaurants`: mock cache bypass + no-provider empty return
- `frontend/src/lib/api.ts` — `RawRestaurantResult.source`, mock guard in `searchRestaurants`, `isMockEntry` guard in `fetchExploreSnapshot`, mock filter in `saveExploreSnapshot`
- `frontend/tests/explore-restaurants-trust-contract.test.mjs` — updated 4 existing tests to match new filter shapes; added 6 new mock-rejection contract tests (total 43 tests)

### Supabase SQL: No
### Backend touched: Yes (`search.py` — mock bypass and no-provider return)
### Frontend touched: Yes (`api.ts` — mock guards; tests only otherwise)

---

## Last change (2026-05-03) — Fix Explore Restaurants 0-result bug (cache hit NameError + snapshot identity)

### Root cause (two-bug chain)

**Bug 1 — Backend `raw_count` undefined on cache hit (primary blocker):**
`SearchService.search_restaurants()` referenced `raw_count` in a `logger.info` call inside the `if cached:` block, but `raw_count` was never defined in that scope. On the first request (cache miss) this variable is absent so no error occurs. On every subsequent request (cache hit), Python raises `NameError: name 'raw_count' is not defined`, which propagates as an unhandled exception → FastAPI returns HTTP 500 → frontend `apiFetch` throws → `searchRestaurants` catch returns `{ restaurants: [] }` → `setCandidateRestaurants([])` → UI shows 0 restaurants.

**Bug 2 — `ExploreSnapshotRestaurant` missing identity fields (persistence cycle):**
The Pydantic model for snapshot restaurants did not declare `provider_place_id`, `google_maps_uri`, or `place_id`. Pydantic silently strips unknown fields on PUT, so these identity fields were never stored in `trips.metadata.explore_snapshot`. On the next page load, `fetchExploreSnapshot`'s identity-trust gate (`if (!googleMapsUri && !providerPlaceId && !placeId) return null`) filtered all snapshot restaurants to `[]`, forcing a self-heal live search on EVERY load — which then hit Bug 1 on the second page load.

### Failure chain for existing trips
1. Cold cache (miss): backend returns 12, frontend shows 12 ✓
2. `saveExploreSnapshot` sends identity fields → Bug 2 strips them → snapshot saved without identity
3. Reload: `fetchExploreSnapshot` maps restaurants, identity check fails → `restaurants = []`
4. Self-heal: `searchRestaurants` called → cache HIT → Bug 1: `NameError` → 500 → frontend gets `[]`
5. `setCandidateRestaurants([])` → UI shows 0 permanently ✗

### Fix
- `backend/app/services/search.py` line 803: added `raw_count = len(cached)` before the cache-hit `logger.info` call.
- `backend/app/models/search.py` `ExploreSnapshotRestaurant`: added `provider_place_id`, `google_maps_uri`, `place_id` optional fields so they survive Pydantic validation on PUT and are stored in JSONB. On the next page load, snapshot restaurants pass the frontend identity trust gate → `hasHealthyRestaurants = true` → no repeated live search needed.

### Self-heal behavior for existing trips
Existing trips with empty/bad snapshots self-heal on the NEXT page load:
1. `fetchExploreSnapshot` returns `restaurants = []` (old snapshot, no identity)
2. `shouldFetchRestaurants = true` → `searchRestaurants` → cache miss OR warm (now no NameError) → 12 restaurants
3. `setCandidateRestaurants(12)` → renders
4. `saveExploreSnapshot` now sends identity fields → `ExploreSnapshotRestaurant` stores them
5. Next reload: snapshot restaurants have identity → pass trust gate → no live search needed

### Files changed
- `backend/app/services/search.py` — added `raw_count = len(cached)` in cache hit block
- `backend/app/models/search.py` — added `provider_place_id`, `google_maps_uri`, `place_id` to `ExploreSnapshotRestaurant`
- `backend/tests/test_restaurant_search_diagnostics.py` — 10 focused tests: miss path, cache hit path (no NameError), cache hit verified identity, count match, stale ai_score rescore, ExploreSnapshotRestaurant identity fields, optional fields, model_dump serialization, unverified regression
- `frontend/tests/explore-restaurants-trust-contract.test.mjs` — 18 focused tests: API mapping, trust gate, RestaurantSearchEnvelope shape, catch envelope, state/snapshot self-heal, canPersistRestaurants guard, hydration camelCase/alias reads, saveExploreSnapshot sends identity, backend model contract, raw_count fix assertion, regression tests for unverified blocking and Maps URL

### Lesson: When backend returned_count > 0 but UI shows 0
**Always trace in this order before touching provider/search logic:**
1. Backend: does the CACHE HIT path have the same variables as the miss path? A NameError/exception in the hit path causes every warm-cache reload to fail silently in the frontend try/catch.
2. API parse: does `apiFetch` + `toCamel` produce camelCase fields the mapper reads? (`source_status` → `sourceStatus`, `google_maps_uri` → `googleMapsUri`)
3. Mapper: does `mapRestaurantToResult` read both camelCase and snake_case aliases?
4. Trust gate: does the mapped result have `googleMapsUri || providerPlaceId || placeId`?
5. State merge: is `setCandidateRestaurants(resolvedRestaurants)` called unconditionally (not gated on `length > 0`)?
6. Snapshot: does the backend model (`ExploreSnapshotRestaurant`) declare the identity fields so they're stored and survive the next hydration?
7. Render: does `filteredRestaurants.length === 0` show "No restaurants match" when `candidateRestaurants.length > 0` with active filters?

### Supabase SQL: No
### Backend touched: Yes (`search.py` bug fix, `models/search.py` field addition)
### Frontend touched: No (tests only)

---

## Last change (2026-05-02) — Provider Result Cache v1

Added a soft-TTL in-memory provider result cache for the `LiveResearchService.fetch()` path (Tavily/Brave/Serper), with a quality gate to avoid serving stale/weak results.

### Files touched
- `backend/app/services/provider_cache.py` — NEW: `ProviderResultCache` class, `is_live_research_payload_quality_sufficient()` quality gate, module-level singleton + reset helper
- `backend/app/services/live_research.py` — `_TTLCache.get_with_status()` compat shim; `_GLOBAL_CACHE` upgraded from `_TTLCache(1800)` to `ProviderResultCache()`; `fetch()` updated with soft-TTL read logic, quality gate on both read and store, structured log events; `reset_global_cache()` updated
- `backend/tests/test_provider_cache.py` — NEW: 46 focused tests covering all cache paths

### Behavior change
**Before:** `LiveResearchService` used a 30-minute hard-expiry `_TTLCache`. On expiry the result was silently discarded and the live provider was called.

**After:** Three-tier soft TTL:
- `0–6h` (FRESH): return from cache; skip live provider
- `6–24h` (STALE): return from cache only if quality gate passes; otherwise fall through to live provider
- `24h+` (EXPIRED): bypass cache, force live provider call

**Quality gate (read + write):**
- Payload must be a non-empty dict
- `cache_version` must match `CONCIERGE_CACHE_VERSION`
- `source_status` must not be `error`/`unavailable`/`none`
- Intent-aware minimum: restaurant intents require ≥1 restaurant OR research_sources; attraction intents require ≥1 attraction OR research_sources; hotel intents require ≥1 hotel OR research_sources; general intents require any non-zero total
- Truly empty payloads (all buckets zero) are never stored or reused

**Log events added:**
- `live_research_cache hit` — FRESH cache reuse
- `live_research_cache stale_reuse` — STALE cache reuse (quality ok)
- `live_research_cache weak_bypass` — cache found but quality gate failed
- `live_research_cache miss` — no cache entry (or expired/bypassed)
- `live_research_cache stored` — result stored after live provider call
- `live_research_cache not_stored` — live result not stored (weak quality)
- `live_research_cache read_error` / `write_error` — cache exception, logged and ignored

**Cache failures are non-fatal:** both `get_with_status()` and `set()` are wrapped in try/except; any exception falls through to the live provider path.

**Backward compatible:** existing tests that inject `_TTLCache(0)` (disabled cache) continue to work via the `get_with_status()` compatibility shim. No Supabase SQL required. No response schema changes. No frontend changes.

### Cache contract for future AI agents
- Cache singleton: `backend/app/services/provider_cache._PROVIDER_CACHE`
- Import: `from app.services.provider_cache import ProviderResultCache, get_provider_cache, reset_provider_cache`
- Cache key: produced by `_make_cache_key(intent, destination, query, dates)` in `live_research.py` — normalizes whitespace/case; includes intent, destination, derived_category, location_anchor
- TTL constants: `FRESH_SECONDS = 21600`, `STALE_SECONDS = 86400` — can be adjusted in `provider_cache.py`
- Quality gate function: `is_live_research_payload_quality_sufficient(payload, intent=..., cache_version=...)` — import from `provider_cache`
- Test helper: `reset_provider_cache()` clears the singleton; `reset_global_cache()` in `live_research.py` calls it automatically

### Known issues
- `ProviderResultCache` is in-memory only: restarts clear the cache. For persistence across restarts, a future v2 could use Redis or Supabase with the existing `research_cache` table.
- STALE tier TTL (6–24h) means popular searches on a busy day will be served stale data for up to 18h when quality is ok. This is intentional (cost reduction) but should be monitored.

### Next likely task
- Monitor `live_research_cache stale_reuse` and `weak_bypass` log rates in production to tune FRESH/STALE thresholds
- Consider a `?refresh=true` query param on `/ai/concierge/search` to force bypass (already has a `DELETE /ai/concierge/cache` endpoint for manual clear)
- Provider result cache v2: Redis or Supabase persistence for cross-restart cache warmth

### Supabase SQL required: No
### Backend touched: Yes (`live_research.py`, new `provider_cache.py`)
### Frontend touched: No
## Last change (2026-05-02) — Explore Score Race Condition Fix (fetchTripItems no longer owns candidate state)

### Summary
Fixed a persistent race condition that caused Explore Attractions and Restaurants to lose AI score badges and Top Pick labels on trips where users had saved AI Concierge ideas.

### Root cause
Two concurrent `useEffect` hooks in `TripBuilder.tsx` both wrote to `candidateAttractions`/`candidateRestaurants`:
1. **`fetchTripItems` effect** (deps `[tripId, destination]`): fetched all trip-level items, filtered `activity`/`meal` items with `day_id=null`, and called `setCandidateAttractions`/`setCandidateRestaurants` — including unscored concierge ideas (`source_kind: "concierge_idea"`, no `ai_score`).
2. **Snapshot-first effect** (deps `[destination, authSessionReady, tripId]`): fetched scored candidates from `trips.metadata.explore_snapshot`.

When `fetchTripItems` resolved after the snapshot effect (common under normal network conditions), it overwrote the scored snapshot candidates with unscored concierge ideas, causing all score badges to disappear.

### Fix
Removed the `persistedAttractions`/`persistedRestaurants` hydration code from the `fetchTripItems` effect. Attractions and restaurants are now owned exclusively by the snapshot-first hydration effect. The `fetchTripItems` effect only sets `candidateFlights` and `candidateHotels`. Removed `destination` from the dep array since it was no longer used.

### Score/snapshot contract (unchanged)
- `fetchExploreSnapshot` reads `aiScore` (primary, from `toCamel`), then `ai_score`, then `score`; enriches stale entries via `computeExploreAttractionScore`/`computeExploreRestaurantScore`
- `saveExploreSnapshot` enriches before persisting; serializes as `ai_score` (snake_case) for backend
- `AiScoreBadge` renders null for score ≤ 0 or non-finite
- Top Pick gated on `(attraction.aiScore ?? 0) > 0`

### Files touched
- `frontend/src/components/trips/TripBuilder.tsx` — removed `persistedAttractions`/`persistedRestaurants` hydration from `fetchTripItems` effect; dep array changed from `[tripId, destination]` to `[tripId]`
- `frontend/tests/explore-hydration.test.mjs` — added 13 new tests covering: race condition fix, normalizeExploreScore priority chain, mapAttractionToResult/mapRestaurantToResult normalizedAiScore, saveExploreSnapshot positive guard, fetchExploreSnapshot storedScore chain, AiScoreBadge null guard, Top Pick positive guard, hasPositiveExploreScore gate, hydrationKey format, loading state flags (total 41 tests)

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-05-02) — Explore Scoring Durability Fix (stale cache re-scoring + snapshot enrichment)

### Summary
Fixed a scoring durability gap where Explore Attractions and Restaurants showed no AI score badges or Top Pick after snapshot load. Root cause: Supabase `research_cache` entries from before scoring was added had `ai_score: null`; cache hits returned these as-is, bypassing `_compute_attraction_ai_score`/`_compute_restaurant_ai_score`; nulls were saved into `trips.metadata.explore_snapshot`; snapshot loaded back with no scores on every subsequent visit.

### Two-layer fix

**Backend (`search.py`):** `search_attractions` and `search_restaurants` now re-score on cache hit any row with `ai_score is None` but non-null `rating` and `num_reviews` using the existing deterministic formulas. Rows with a positive existing score are not re-scored.

**Frontend (`api.ts`):** Added `computeExploreAttractionScore` and `computeExploreRestaurantScore` (mirror exact backend formulas using `Math.log1p` and same weight constants). Both are exported. `fetchExploreSnapshot` now enriches stale snapshot entries: if `aiScore` is null but `rating`/`numReviews` are present, computes a score as fallback (still gated on `> 0`). `saveExploreSnapshot` applies the same enrichment before serializing to backend so future loads get pre-scored snapshots.

### Score gating invariants (unchanged)
- `AiScoreBadge` renders null for score ≤ 0 or non-finite
- Top Pick gated on `(attraction.aiScore ?? 0) > 0`
- Neither computed nor persisted scores are faked — no enrichment if `rating`/`numReviews` absent

### Files touched
- `backend/app/services/search.py` — re-score stale cache hits in `search_attractions` and `search_restaurants`
- `frontend/src/lib/api.ts` — added `computeExploreAttractionScore`, `computeExploreRestaurantScore`; updated `fetchExploreSnapshot` mapper and `saveExploreSnapshot` to enrich stale candidates
- `frontend/tests/explore-hydration.test.mjs` — updated tests 15–16 for new code structure; added 6 new scoring contract tests (total 26 tests)
- `backend/tests/test_explore_snapshot.py` — added 4 new cache-hit re-scoring tests (total 14 tests)

### Supabase SQL: No
### Backend touched: Yes (scoring logic in existing service, no DB schema change)

---

## Previous change (2026-05-02) — Persisted Explore Candidate Snapshots v1 (Attractions + Restaurants)

### Summary
Implemented snapshot-first hydration for the Explore Attractions and Restaurants panels. Scored/ranked candidates from provider search are now persisted per-trip in `trips.metadata.explore_snapshot`. On existing-trip page load, TripBuilder hydrates Attractions and Restaurants from the snapshot first — skipping the expensive provider-backed search call entirely. Provider search only runs when no usable snapshot exists. After a successful provider search the result is saved as the new snapshot.

### Problem solved
Explore recommendations degraded after page refresh because `searchAttractions`/`searchRestaurants` returned provider results without scoring metadata on subsequent calls, causing score badges to show 0 and Top Pick to appear without a valid signal.

### Explore hydration order (after this PR)
1. `fetchTripItems(tripId)` — load flights/hotels from persisted trip-level items (unchanged)
2. `fetchExploreSnapshot(tripId)` — load Attractions + Restaurants from snapshot in `trips.metadata`
3. If snapshot has usable candidates → hydrate state, **no provider call**
4. If snapshot absent/empty → call `searchAttractions(destination)` + `searchRestaurants(destination)`, then `saveExploreSnapshot(tripId, ...)` after success

### How scoring/top-pick is preserved
- `fetchExploreSnapshot` mapper: only positive scores passed through; no fake 0 fallback (see scoring fix above for stale enrichment)
- `saveExploreSnapshot` serializes enriched `ai_score` per candidate using snake_case for backend
- `AiScoreBadge` renders null for score ≤ 0 or non-finite (unchanged)
- Top Pick gated on `(attraction.aiScore ?? 0) > 0` (unchanged)

### How repeated provider calls are avoided
- `exploreSnapshotLoadedRef` stores a `${tripId}:${destination}` hydration key — the combined hydration effect bails immediately on re-render if key already processed
- No separate attractions/restaurants refs needed; single async effect covers both

### Snapshot storage decision
Stored in `trips.metadata.explore_snapshot` (existing `jsonb` column on the `trips` table). No new Supabase table or migration required. Service method merges snapshot into existing metadata, preserving other keys.

### Files touched
- `backend/app/models/search.py` — added `ExploreSnapshotAttraction`, `ExploreSnapshotRestaurant`, `ExploreSnapshot` Pydantic models
- `backend/app/services/trips.py` — added `get_explore_snapshot(trip_id, user_id)` and `save_explore_snapshot(trip_id, user_id, snapshot)` service methods; added `Dict, Any` import
- `backend/app/routes/trips.py` — added `GET /trips/{trip_id}/explore-snapshot` and `PUT /trips/{trip_id}/explore-snapshot` endpoints; imported `ExploreSnapshot`
- `frontend/src/lib/api.ts` — added `ExploreSnapshot` interface, `fetchExploreSnapshot(tripId)`, `saveExploreSnapshot(tripId, snapshot)` exports
- `frontend/src/components/trips/TripBuilder.tsx` — imported `fetchExploreSnapshot`/`saveExploreSnapshot`; added `exploreSnapshotLoadedRef`; replaced two separate hydration effects with one unified snapshot-first async effect
- `frontend/tests/explore-hydration.test.mjs` — updated test #5 title + assertions for snapshot-first behavior; added 14 new snapshot contract tests (total 20 tests)
- `backend/tests/test_explore_snapshot.py` — NEW: 10 backend unit tests for TripsService snapshot methods and ExploreSnapshot models

### Known issues / v1 limits
- Snapshot has no TTL in v1 — once saved it stays until a new provider search runs. This is intentional: provider search is the expensive path and scored data from it is durable.
- User-triggered regeneration path (if implemented later) should clear `exploreSnapshotLoadedRef` and call `saveExploreSnapshot` after the new results arrive.
- Snapshot is per-trip — does not carry over if a user changes the destination.

### Supabase SQL: No (uses existing `trips.metadata jsonb` column)
### Backend touched: Yes (new endpoints + service methods, no DB schema change)

---

## Last change (2026-05-01) — Card points edit + Account identity / sign out

### Summary
Fixed two checkpoint UX issues before wife testing:

**Scope A — Card points editable:** Each travel card on `/cards` now has a pencil-icon edit button that opens an `EditCardModal` (pre-filled with current values). Users can update points balance, cpp value, display name, issuer, and primary status. Updates persist via the existing `PATCH /cards/{card_id}` backend endpoint. Added `updateCard` / `UpdateCardData` to `frontend/src/lib/api.ts`.

**Scope B — Real user identity + sign out:** Sidebar and MobileNav drawer now load the authenticated user from `supabase.auth.getUser()` / `onAuthStateChange`. `getUserDisplay()` prefers `user_metadata.full_name` → `user_metadata.name` → email prefix; falls back to `?` only if none are present. Both Sidebar and the MobileNav drawer show a "Sign out" button that calls `supabase.auth.signOut()` and redirects to `/auth/login`.

### Files touched
- `frontend/src/lib/api.ts` — added `UpdateCardData` interface and `updateCard(cardId, data)` function; calls `PATCH /cards/{cardId}`
- `frontend/src/app/cards/page.tsx` — added `EditCardModal` component; added `editingCard` state; added pencil edit button on each card; added `handleUpdated` to update the local list optimistically
- `frontend/src/components/layout/Sidebar.tsx` — added `user` state via `supabase.auth.getUser()` + `onAuthStateChange`; added `getUserDisplay()` helper (prefers full_name → name → email prefix); added `handleSignOut()` + LogOut button; removed hardcoded "Traveler" / "traveler@example.com"
- `frontend/src/components/layout/MobileNav.tsx` — added same user identity + sign out pattern in the slide-out drawer; drawer now shows user initial + name and a Sign out button
- `frontend/tests/cards-and-account.test.mjs` — NEW: 21 renderer/contract tests covering all acceptance criteria for both scopes

### Behavior change
- `/cards`: each card tile now shows a pencil edit button → opens an edit modal with points balance and all fields pre-filled → Save calls `PATCH /cards/{id}` → card list updates immediately without reload
- Sidebar (desktop): shows authenticated user's display name (or email prefix) and email; avatar shows first letter; "Sign out" button at bottom-left routes to login after sign-out
- MobileNav drawer (mobile): shows user initial + display name and a "Sign out" button at the bottom of the drawer

### Data model
No new tables, no schema change. `updateCard` reuses the existing `PATCH /cards/{id}` endpoint with `TravelCardUpdate` payload (all optional fields).

### Known issues / v1 limits
- User metadata (`full_name`, `name`) depends on what the OAuth/email provider populates; email-only signups will show the email prefix as the name (intentional fallback)

### Supabase SQL: No
### Backend touched: No (existing PATCH endpoint used)

---

## Last change (2026-05-01) — Trip Ideas filters/sort/search v1

### Summary
Added frontend-only search, filter, and sort controls to the Trip Ideas panel so users can manage a large saved shortlist without backend changes. Controls are compact, mobile-usable, and do not affect the AI Concierge, persistence semantics, or itinerary day logic.

### Files touched
- `frontend/src/types/index.ts` — added `createdAt?: string` and `updatedAt?: string` to `ItineraryItem` (backend already sends these via `TimestampedBase`; the `toCamel` transform makes them available; only the TypeScript type was missing them)
- `frontend/src/components/trips/TripIdeasPanel.tsx` — added exported `filterByStatus`, `searchIdeas`, `sortIdeas` pure functions; added `STATUS_FILTER_OPTIONS`, `SORT_OPTIONS`, `PRIORITY_ORDER` constants; added `StatusFilter` and `SortOption` types; replaced `showSkipped` state with `statusFilter: StatusFilter` state; added `searchQuery` and `sortBy` state; added `filteredAndSorted` useMemo pipeline; added compact filter controls UI (search input, status filter pills, sort select, clear button); updated badge count to reflect active (non-skipped) count regardless of current filter; updated empty state to distinguish "no ideas at all" vs "no ideas match filters"; removed the old "N skipped · show" toggle (replaced by the "Skip" status filter pill)
- `frontend/tests/trip-ideas.test.mjs` — added 10 new renderer/contract tests (tests 22–31) covering: exported function presence, filterByStatus logic, searchIdeas field coverage, sortIdeas all four options, PRIORITY_ORDER ranking, STATUS_FILTER_OPTIONS values, SORT_OPTIONS values, search input + accessible labels, hasActiveFilters + handleReset, and empty state differentiation

### Behavior change
- Trip Ideas panel now shows a compact search input + status filter pills (All / Must-do / Maybe / Skip) + sort select (Priority / Recently saved / Name / Category) + "Clear ×" button (visible only when any filter is active)
- **Search** matches title, `item.location`, `details.address`, `details.userNote`/`user_note`, and `ideaCategory()`
- **Status filter default** = "All" (non-skipped), same as before — the old "N skipped · show" toggle is replaced by the "Skip" filter pill
- **Sort default** = Priority (must_do → maybe → skipped)
- **Recently saved** sort uses `item.createdAt` (descending); falls back gracefully when absent
- **Name / Category** sort uses `localeCompare`
- Empty state when no ideas: "Save recommendations from AI Concierge and schedule them later." (unchanged)
- Empty state when ideas exist but none match: "No ideas match your current filters."
- Badge on header reflects active (non-skipped) count regardless of current filter state

### Data assumptions
- `createdAt` / `updatedAt` are provided by the backend (`itinerary_items` table via `TimestampedBase`) and transformed to camelCase by `toCamel()` in `api.ts`; no API change needed
- `details.address`, `details.category`, `details.type`, `details.userNote`/`user_note` are used read-only for search; no new fields added

### Supabase SQL: No
### Backend touched: No

---

## Last change (2026-05-01) — AI/Search cost-control guardrails (per-user throttle + dedupe)

### Summary
Added lightweight, in-memory cost guardrails on expensive provider-backed routes before second-user access. Authenticated users now have per-endpoint throttling windows and short duplicate-request cooldowns on AI Concierge and search APIs. Limits are env-tunable with safe defaults and return HTTP 429 with a frontend-safe JSON detail payload (`code`, `message`, `retry_after_seconds`).

### Supabase SQL: No
### Backend touched: Yes

### Guardrail defaults
- `guardrail_ai_concierge_requests=6`
- `guardrail_ai_concierge_window_seconds=60`
- `guardrail_ai_concierge_dedupe_seconds=8`
- `guardrail_ai_timeline_requests=10`
- `guardrail_ai_timeline_window_seconds=60`
- `guardrail_ai_timeline_dedupe_seconds=5`
- `guardrail_search_requests=20`
- `guardrail_search_window_seconds=60`
- `guardrail_search_dedupe_seconds=3`

### Notes
- Search routes now require authenticated `CurrentUserID` so guardrails are keyed per-user consistently.
- Existing provider fallback behavior is unchanged: when providers/timeouts fail, existing deterministic/sample fallbacks still execute.

---

## Last change (2026-05-01) — Booking-links auth scope closure

### Summary
Closed remaining itinerary hardening gap: `GET /itinerary/items/{item_id}/booking-links` now requires authenticated `CurrentUserID` and resolves itinerary item using user-scoped ownership checks before returning stored/generated booking links.

### Supabase SQL: No
### Backend touched: Yes

---

## Last change (2026-05-01) — Itinerary auth/scoping + sensitive logging hardening

### Summary
Implemented blocker security hardening before second-user access: itinerary route handlers now require authenticated `CurrentUserID`, itinerary service methods enforce ownership checks for trip/day/item operations using authenticated user scope, backend request middleware no longer logs raw request bodies, and frontend API debug logging was reduced to avoid exposing auth/session/token/payload details.

### Supabase SQL: No
### Backend touched: Yes

---

## Last change (2026-05-01) — Travel Time Hints v1 readability + conservative walk estimate cleanup

### Summary
Small frontend-only cleanup for Travel Time Hints v1: connector hint rows now have slightly more vertical breathing room (less cramped between cards), and walking-time hints are now intentionally conservative using an adjustment factor so city-grid walks are less optimistic while still clearly marked as rough (`~`).

### Files touched
- `frontend/src/lib/travelHints.ts` — added `CONSERVATIVE_WALK_FACTOR` + `MAX_WALK_HINT_MIN`; adjusts `walkMinutes` with `Math.ceil(walkMinutes * factor)` before label selection; preserves missing-location and far-apart logic
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — connector spacing/readability tweaks (`py-1`, taller divider line, `leading-snug`) for travel + missing-location connector rows
- `frontend/tests/travel-time-hints.test.mjs` — added focused contract checks for conservative walking constants/adjustment and connector spacing classes

### Supabase SQL: No
### Backend touched: No

---

## Last change (2026-05-01) — Travel Time Hints v1

### Summary
Added read-only day-level Travel Time Hints v1. Adjacent itinerary stops within each timeline section now show helpful hints about travel between them — rough walk/drive estimates when location data exists, gentle "Add location details" prompts when it's missing, and "These two stops may be far apart" warnings when the haversine distance implies a long drive. A `DayTravelHintBar` at the bottom of each expanded day column summarizes day-level issues when any pair is flagged.

### Files touched
- `frontend/src/lib/travelHints.ts` — NEW: exports `PairHint`, `PairHintKind`, `FAR_APART_DRIVE_MIN`, `computeAdjacentHints(items)` (returns one hint per adjacent pair: `travel_ok`, `far_apart`, or `missing_location`), and `summarizeHints(hints)` (aggregates for day-level display); imports `estimateTravel` + `formatTravelBadge` from existing `travelTime.ts`; entirely pure/side-effect free
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — replaced direct `estimateTravel`/`formatTravelBadge` calls in `renderItemsWithConnectors` with `computeAdjacentHints`; added three connector UI branches: `travel_ok` (unchanged walk/drive badge with `~` prefix), `far_apart` (badge + amber warning line), `missing_location` (MapPin icon + italic help text); added `DayTravelHintBar` sub-component that calls `computeAdjacentHints` + `summarizeHints` on `visibleItems` and renders a subtle info bar when any pair has issues; added `Info`, `MapPin` imports from lucide-react; removed `estimateTravel`/`formatTravelBadge` imports (now delegated to `travelHints.ts`)
- `frontend/tests/travel-time-hints.test.mjs` — NEW: 24 contract tests covering exports, PairHintKind values, per-pair hint logic (travel_ok/far_apart/missing_location), summarizeHints aggregation, DayTravelHintBar presence, copy requirements, no-map/no-route scope guard
- `frontend/tests/itinerary-timeline.test.mjs` — updated test 11 to check for `computeAdjacentHints` instead of `estimateTravel` (refactored delegation; behavior preserved)

### Behavior change
- Adjacent items with `details.lat`/`details.lng` within the same timeline section show `~N min walk` or `~N min drive` connectors (same as before, now with `~` prefix to signal rough estimate)
- Adjacent pairs where drive time exceeds ~30 min show an additional amber "These two stops may be far apart." line under the travel badge
- Adjacent pairs missing lat/lng on either item show a soft MapPin icon + "Add location details to improve travel hints." connector (previously showed nothing)
- Each expanded day column shows a `DayTravelHintBar` at the bottom when any pair has issues, with message: "Some stops may be far apart. Consider grouping nearby items." or "Add location details to improve travel hints." followed by "Rough hints only."
- All estimates are clearly labeled rough/approximate (`~` prefix, "Rough hints only" disclaimer)
- No items are mutated, reordered, or moved; hints are read-only

### Hint logic
```
items[i].details.lat/lng + items[i+1].details.lat/lng → haversine distance
  driveMinutes > 30  → far_apart: "These two stops may be far apart."
  driveMinutes ≤ 30  → travel_ok: "~N min walk" or "~N min drive"
  lat/lng missing    → missing_location: "Add location details to improve travel hints."
```

### Known issues / v1 limits
- `FAR_APART_DRIVE_MIN = 30` is a rough city-speed threshold (30 km/h average); actual routing may differ significantly
- `DayTravelHintBar` operates on the flat `visibleItems` list, so cross-section pairs (last morning item → first afternoon item) are also evaluated — this is intentional for day-level overview
- Hints reset when `visibleItems` changes (e.g., after a full itinerary reload); no caching
- No time-of-day awareness (rush hour, transit, etc.) — this is a v1 rough hint only

### Next likely task
- Use `details.lat/lng` for geographic clustering in trip planning suggestions
- Consider showing a day-level "geographic spread" score when all items have coordinates

### Supabase SQL: No
### Backend touched: No

---

## Last change (2026-05-01) — Concierge metadata preservation for Trip Ideas + Day add

### Summary
Persisted optional Google verification metadata when saving AI Concierge results to Trip Ideas and when adding them directly to an itinerary day. Both flows now preserve `details.lat`, `details.lng`, `details.provider_place_id`, `details.formatted_address`, and `details.google_maps_uri` when present, while skipping null/undefined/empty values.

### Files touched
- `frontend/src/lib/api.ts` — added `normalizeGoogleVerificationDetails(item)` helper; wired it into both `addStructuredConciergeItemToTrip` and `saveToTripIdeas` detail payloads so Google verification metadata is merged without overwriting existing fields with empty values
- `frontend/tests/trip-ideas.test.mjs` — added focused contract tests confirming both save/add flows include the metadata helper and that the helper safely no-ops when `googleVerification` is missing

### Behavior change
- AI Concierge → Trip Ideas now persists Google metadata into `details` when available
- AI Concierge → Day now persists Google metadata into `details` when available
- Existing fields (`location`, `address`, `dayPart`, `timeLabel`, notes/status/priority, etc.) remain preserved because this change only appends non-empty metadata keys
- Trip Ideas ↔ Day movement remains day_id-only and continues to preserve `details` as-is

### Known issues / v1 limits
- Metadata persistence is source-dependent: if a card has no `googleVerification`, no new metadata fields are added (expected behavior)

### Next likely task
- Use persisted `details.lat/lng` + place metadata for Travel Time Hints v1 calculations (no UI yet)

### Supabase SQL: No
### Backend touched: No

## Last change (2026-05-01) — Smart Day Timeline AI Planning v1

### Summary
Added a "Suggest Timing" button to each itinerary day column. When clicked for a day that has items, the feature gathers those items and calls a new `POST /ai/timeline/suggest` backend endpoint to suggest `details.dayPart` and optional `details.timeLabel` for each item. The user reviews the suggestions in a compact inline panel and clicks "Apply All Suggestions" to persist them via the existing `updateItemTimeline` / `PATCH /itinerary/items/{id}` path. A deterministic client-side fallback runs when the backend is unreachable or no AI key is configured.

### Files touched
- `frontend/src/lib/dayPlanner.ts` — NEW: exports `DayPlannerSuggestion` type and `suggestTimelineFallback(items)` deterministic rule-based planner; classification rules: breakfast/brunch/cafe → morning, dinner/cocktail bar → evening, lunch → afternoon, generic meal → afternoon, generic activity → morning, flight/hotel → unscheduled; preserves existing `details.dayPart` when already set; `timeLabel` is always `undefined` (not blank string) when not strongly implied
- `frontend/src/lib/api.ts` — added `TimelineSuggestion` interface and `suggestDayTimeline(items)` export; calls `POST /ai/timeline/suggest`; on any error falls back to `suggestTimelineFallback` imported lazily from `dayPlanner.ts`
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — added `suggestingTimeline`, `timelineSuggestions`, `applyingTimeline` state; `handleSuggestTimeline()` handler calls `suggestDayTimeline`, stores suggestions; `handleApplyTimeline()` calls `updateItemTimeline` for each suggestion in parallel, updates `itemOverrides` for optimistic section movement, clears suggestion state; new `SuggestionsReviewPanel` sub-component: shows item → dayPart + timeLabel rows, "Apply All Suggestions" button, and "Dismiss" X button; "Suggest Timing" button added to day header (visible when day has ≥1 item), coloured slate (distinct from amber "Plan My Day"); imports `suggestDayTimeline`, `updateItemTimeline`, `TimelineSuggestion` from `@/lib/api`; imports `Check`, `X` icons from lucide-react
- `backend/app/routes/ai.py` — added Pydantic models `_TimelineItem`, `_TimelineSuggestion`, `_TimelineSuggestRequest`, `_TimelineSuggestResponse`; added `_classify_deterministic()` with same keyword rules as the TS fallback; added `_build_claude_prompt()` and `_parse_claude_suggestions()` for the AI path; added `POST /ai/timeline/suggest` route: uses Claude (`claude-haiku-4-5-20251001`) if `ANTHROPIC_API_KEY` is set, otherwise runs deterministic fallback; safe to call in local/dev/test with no API key; returns `provider: "claude"|"deterministic"` in response
- `frontend/tests/smart-timeline.test.mjs` — NEW: 29 renderer/contract tests covering: `suggestTimelineFallback` export and shape, breakfast→morning, cafe→morning, dinner→evening, lunch→afternoon, flight/hotel→unscheduled, activity→morning, meal→afternoon, explicit dayPart preservation, timeLabel read-through, timeLabel defaults to undefined, day_id never touched, `suggestDayTimeline` export and fallback, backend endpoint path, `TimelineSuggestion` fields, `SuggestionsReviewPanel` controls, no day_id mutation in apply handler

### Behavior change
- Each expanded itinerary day column (when the day has ≥1 item) now shows a "Suggest Timing" button (Clock icon, slate style) in the day header
- Clicking "Suggest Timing" fires `POST /ai/timeline/suggest` with the day's items; a loading spinner appears on the button while the request is in flight
- On success, a `SuggestionsReviewPanel` appears above the timeline sections showing each item with its suggested dayPart and timeLabel
- "Apply All Suggestions" persists each suggestion via the existing `PATCH /itinerary/items/{id}` endpoint (same path as manual timeline controls); items move to the correct section optimistically
- "Dismiss" (X icon) clears the suggestions without applying them
- No items are duplicated, no day_id is changed, no items are moved to Trip Ideas
- Fallback path (no API key, network error) runs entirely in the browser with deterministic rules — feature remains usable in local/dev/test

### AI planner rules (both backend and fallback)
```
breakfast/brunch → morning (timeLabel: "Breakfast")
coffee/cafe/bakery → morning (timeLabel: "Morning coffee")
dinner/supper → evening (timeLabel: "Dinner")
cocktail/bar → evening (timeLabel: "Evening drinks")
nightlife → evening (timeLabel: "Night out")
lunch/midday/noon → afternoon (timeLabel: "Lunch")
generic meal → afternoon (timeLabel: "Lunch")
generic activity → morning (no timeLabel)
flight / hotel → unscheduled (no timeLabel)
already has details.dayPart → preserve (no change)
unsure → unscheduled
```

### Known issues / v1 limits
- Suggestion panel is only shown after user clicks the button; it does not auto-apply. This is by design (requires confirmation).
- If the backend call fails AND the dynamic import of `dayPlanner.ts` also fails (unlikely), the `suggestDayTimeline` promise would reject — callers in `ItineraryDayColumn` guard with `try/finally` so the loading state is cleared.
- Suggestion panel does not persist between page navigations (dismissed on unmount). Applied suggestions do persist via Supabase.
- `SuggestionsReviewPanel` does not support per-item override — it's apply-all or dismiss. Per-item editing is a v2 scope.

### Next likely task
- Wire `onUpdateTimeline` callback up through TripBuilder → page if full parent refresh is desired after apply
- Add per-item suggestion editing (v2 scope)
- Consider auto-expanding day when "Suggest Timing" is triggered from the collapsed view

### Supabase SQL: No
### Backend touched: Yes (`backend/app/routes/ai.py` — new endpoint, no DB writes)

---

## Previous change (2026-05-01) — Manual Timeline Controls v1

### Summary
Added simple manual controls so a user can set or adjust an itinerary day item's timeline placement (Morning / Afternoon / Evening / Unscheduled) and optional freeform timeLabel. Items immediately move to the correct section after saving without a full refresh. No AI scheduling, routing, or map optimization added.

### Files touched
- `frontend/src/lib/api.ts` — added `updateItemTimeline(itemId, currentDetails, { dayPart, timeLabel })`: merges `dayPart` and optional `timeLabel` into existing `details` JSONB and PATCHes via existing `PATCH /itinerary/items/{id}` endpoint; clears `timeLabel` from details when empty
- `frontend/src/components/trips/ItineraryItemCard.tsx` — added `DAY_PARTS` constant (4 options); `onTimelineUpdated` prop; `timelineOpen` / `selectedPart` / `timeLabelInput` / `saving` local state; `handleOpenTimeline` (pre-fills from `item.details`); `handleSaveTimeline` (calls `updateItemTimeline`, fires callback, closes panel); a Clock icon trigger button (hover-only unless already scheduled); inline timeline editor panel (day-part pills + timeLabel input + Save); displays `details.timeLabel` as a small badge when set and no `startTime` exists; imports `updateItemTimeline` from `@/lib/api`
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — updated `getItemDayPart` to explicitly handle `"unscheduled"` value (bypasses `startTime` classification); added `onUpdateTimeline` prop to `ItineraryDayColumnProps`, `TimelineSectionsProps`, and `renderItemsWithConnectors`; added `itemOverrides` local state in `ItineraryDayColumn`; `handleTimelineUpdated` stores updated item in overrides and bubbles to parent; `visibleItems` useMemo applies overrides so the item moves to the correct section immediately; threaded `onUpdateTimeline={handleTimelineUpdated}` into `TimelineSections`
- `frontend/tests/itinerary-timeline.test.mjs` — added 12 new renderer/contract tests (tests 14–25) covering: `updateItemTimeline` export, `dayPart`/`timeLabel` persistence, `onTimelineUpdated` prop, timeline trigger button, 4 day-part options in card, `timeLabelInput` state, `handleSaveTimeline`, `onUpdateTimeline` threading, `itemOverrides` state, details spread for field preservation, explicit unscheduled override, single timeline button

### Behavior change
- Each itinerary day item now shows a Clock icon button (hover-visible, always-visible when already scheduled)
- Clicking the Clock icon opens an inline panel with 4 day-part pills (Morning/Afternoon/Evening/Unscheduled) and an optional timeLabel input
- Saving persists `details.dayPart` and `details.timeLabel` via the existing PATCH endpoint
- Item immediately moves to the correct timeline section without page refresh (optimistic via `itemOverrides`)
- Explicitly setting "Unscheduled" overrides any `startTime`-derived section (new `getItemDayPart` branch)
- If `details.timeLabel` is set and no `startTime` exists, the timeLabel is shown as a small clock badge on the card
- All existing behaviors preserved: drag/drop, Trip Ideas ↔ Day, notes/status/priority, concierge item identity

### Timeline persistence model
```
details.dayPart   = "morning" | "afternoon" | "evening" | "unscheduled"
details.timeLabel = string  (optional, freeform, e.g. "9:00 AM", "After lunch")
```
Frontend merges patch into existing details (preserving all other detail fields). No migration needed.

### Known issues
- `itemOverrides` in `ItineraryDayColumn` resets on full itinerary reload (e.g., after move-to-ideas or parent refresh). This is acceptable for v1 — the server-persisted value will be correct after reload.
- Timeline editor is hover-triggered on desktop; on mobile it becomes accessible when the item already has a schedule (clock icon is always visible at reduced opacity in that case).

### Next likely task
- Wire `onUpdateTimeline` callback up through TripBuilder → page if full parent refresh is desired after timeline changes
- Add `details.dayPart` hint to the AI Concierge → save-to-ideas flow so AI-recommended items can optionally carry a section hint

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-05-01) — Smart Day Timeline v1 Foundation

### Summary
Converted each itinerary day's expanded view from a plain item list into a timeline-grouped layout. Items are now bucketed into **Morning / Afternoon / Evening / Unscheduled** sections based on available time metadata, with no AI scheduling, routing, or time generation added.

### Files touched
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — added `DayPart` type, `DAY_PART_META` config, `getItemDayPart()` helper (reads `details.dayPart`, `details.timeLabel`, then `startTime` hour), `groupByDayPart()`, `renderItemsWithConnectors()` extracted function, and `TimelineSections` sub-component that renders section headers + item cards per bucket; existing travel-time connectors preserved within sections; drag/drop (`SortableContext`, `useDroppable`) unchanged
- `frontend/tests/itinerary-timeline.test.mjs` — NEW: 13 renderer contract tests covering classification signals, section labels, Unscheduled fallback, drag/drop preservation, move-to-ideas guard, and travel connectors

### Behavior change
- Day expanded view: items grouped into Morning / Afternoon / Evening / Unscheduled sections
- If **all** items are unscheduled → single "Unscheduled · N items" header shown (clean fallback)
- If **any** item is timed → section headers (Morning amber, Afternoon sky, Evening violet, Unscheduled slate) appear for non-empty buckets
- Travel-time connectors between adjacent items within the same section are preserved
- All existing behaviors preserved: Trip Ideas → Day, Day → Trip Ideas, drag/drop between days, notes/status/priority, move-to-ideas for concierge items only
- No changes to data model, no migration, no Supabase SQL

### Timeline metadata resolution order
1. `item.details.dayPart` — explicit override ("morning" | "afternoon" | "evening")
2. `item.details.timeLabel` — keyword match (e.g., "Morning", "afternoon stroll", "evening dinner")
3. `item.startTime` — ISO datetime or HH:MM; hour → section boundary
4. Default → `"unscheduled"`

### Section hour boundaries
- Morning: 5:00–11:59
- Afternoon: 12:00–16:59
- Evening: 17:00+

### Known issues
- The collapsed-view preview (first item title + "+N more") does not show section context — acceptable for v1
- `PREVIEW_ITEM_LIMIT = 4` still limits visible items before "Show all N items" is clicked; section grouping applies only to visible items

### Next likely task
- Add optional time input to the "Add item" form so users can assign times and see items move into the correct section
- Add `details.dayPart` to the concierge-to-ideas flow so AI-recommended items can optionally carry a section hint

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-04-30) — Trip Ideas Triage v1

### Summary
Added priority/status triage and user notes to the Trip Ideas panel. Each saved idea now supports a `must_do | maybe | skipped` status and an optional short note. Skipped ideas are hidden from the default list with a "N skipped · show" toggle to reveal them. Status and notes persist to Supabase via the existing JSONB merge approach (no new table, no migration).

### Files touched
- `frontend/src/lib/api.ts` — added `updateIdeaMeta(itemId, currentDetails, patch)` which merges `{ ideaStatus?, userNote? }` into the existing details dict and calls the existing `PATCH /itinerary/items/{id}` endpoint; updated `saveToTripIdeas` to set `idea_status: "maybe"` as the default on new saves
- `frontend/src/components/trips/TripIdeasPanel.tsx` — added `STATUS_OPTIONS` (Must-do / Maybe / Skip); `IdeaCard` now renders a priority row with three pill buttons and an expandable note textarea (auto-debounced 800 ms); `TripIdeasPanel` filters visible ideas by `status !== "skipped"` by default and shows a "N skipped · show / hide" toggle when skipped ideas exist; added `handleUpdate` which optimistically updates local state and calls `updateIdeaMeta`
- `frontend/tests/trip-ideas.test.mjs` — added 3 new tests: `updateIdeaMeta` exported, `saveToTripIdeas` sets `idea_status: "maybe"`, TripIdeasPanel has Must-do/Maybe/Skip buttons
- `backend/tests/test_trip_ideas.py` — added 2 new tests: merged details update preserves `source_kind`, skipped ideas are still returned by the backend list (backend is status-agnostic; frontend filters)

### Behavior change
- New saved ideas default to `idea_status: "maybe"` stored in `details` JSONB
- Each Trip Idea card shows three priority pills: **Must-do** (emerald), **Maybe** (amber), **Skip** (slate)
- Clicking a pill immediately updates optimistically and persists via PATCH
- A **+ note** / **note ✎** button toggles an inline textarea; note is auto-saved 800 ms after last keystroke
- Ideas with `idea_status = "skipped"` are hidden by default; a small link at the bottom of the list reveals them
- Badge count on the Trip Ideas panel header reflects visible (non-skipped) count
- All previous behaviors preserved: Save from AI Concierge, immediate appearance, persist after refresh, assign to day, remove

### Data model
```
details.source_kind   = "concierge_idea"   (unchanged)
details.idea_status   = "must_do" | "maybe" | "skipped"   (new; default "maybe")
details.user_note     = string   (new; optional)
```
Frontend sends full merged details via existing `PATCH /itinerary/items/{id}`. Backend stores them as-is. No new endpoint, no migration.

### Known issues
- IdeaCard local `status`/`note` state is not synced back from props after an API failure (page refresh gives correct state). Acceptable for v1.
- `idea_status` for ideas saved before this PR will be treated as "maybe" by the frontend default logic.

### Next likely task
- Mobile viewport test: three-button status row on small screens
- Consider a subtle animation when status changes (e.g., card fades out on Skip)

### Supabase SQL: No
### Backend touched: No (tests only)

---

## Previous change (2026-04-30) — Trip Ideas UX Discoverability Fix

### Summary
UX patch on top of the Saved Shortlist feature: after saving, the concierge card now clearly shows "Saved to Ideas" (not just "Saved"), an auto-dismissing toast in the concierge drawer says "Saved to Trip Ideas — close this panel to schedule it.", and the Trip Ideas panel is always visible (never hidden when empty) with a subtitle explaining its purpose. Panel auto-expands whenever new ideas arrive.

### Files touched
- `frontend/src/components/trips/AIConciergePanel.tsx` — restored missing `inputRef`/`bottomRef` refs; added `setToast("Saved to Trip Ideas — close this panel to schedule it.")` call in `saveIdea` success path; changed saved button label from `Saved` to `Saved to Ideas`; auto-dismiss `useEffect` already in place
- `frontend/src/components/trips/TripIdeasPanel.tsx` — removed `if (!loading && ideas.length === 0) return null` guard; updated empty state text to "Save recommendations from AI Concierge and schedule them later."; added subtitle "Saved from AI Concierge · add to a day when ready" under heading; added `useEffect` to auto-expand (`setOpen(true)`) when ideas arrive

### Behavior change
- Concierge card saved state label: "Saved" → "Saved to Ideas"
- Toast fires inside concierge drawer after every successful save, auto-dismisses after 4 s
- Trip Ideas panel is always rendered (even empty), so users see where saved items will appear
- Panel auto-expands when the first idea is saved, surfacing it immediately

### Known issues
- Trip Ideas panel is always visible even on trips with no concierge activity — acceptable as it shows helpful onboarding empty state
- Toast position is fixed inside the concierge drawer overlay; visible only while drawer is open (intended — tells user to close and check the panel)

### Next likely task
- Mobile viewport test: two-button layout (Add to Day / Save) on small screens
- Consider a subtle animation when a new idea card appears in TripIdeasPanel

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-04-30) — Saved Trip Ideas / Unscheduled Shortlist

### Summary
Added a "Save to Ideas" flow that lets users save AI Concierge results to a trip without assigning them to a specific day. Saved ideas appear in a new **Trip Ideas** panel in the trip builder. Users can assign an idea to a day (removing it from the unscheduled list) or delete it.

### Files touched
- `backend/app/services/itinerary.py` — added `list_unscheduled_items(trip_id)`: returns items with `day_id IS NULL`
- `backend/app/routes/trips.py` — added `GET /trips/{trip_id}/ideas` endpoint
- `frontend/src/lib/api.ts` — added `fetchTripIdeas`, `saveToTripIdeas` (marks `source_kind: "concierge_idea"` in details), `assignIdeaToDay`, exported `ConciergeItemKind` type
- `frontend/src/components/trips/AIConciergePanel.tsx` — added "Save" button alongside "Add to Day"; `savedIdeaItems`/`savingIdeaItems` state; `saveIdea()` handler; `onIdeaSaved` prop; pre-populates saved state from existing ideas on panel open
- `frontend/src/components/trips/TripIdeasPanel.tsx` — NEW: collapsible panel listing concierge-saved ideas; per-idea "Add to Day" selector+button and remove button; fetches from `/trips/{trip_id}/ideas` filtered by `source_kind=concierge_idea`
- `frontend/src/components/trips/TripBuilder.tsx` — imports and renders `TripIdeasPanel` in right panel above day columns; accepts `ideasRefreshKey` and `onIdeaAssigned` props
- `frontend/src/app/trips/[id]/page.tsx` — adds `tripIdeasKey` state; passes `ideasRefreshKey` to TripBuilder; passes `onIdeaSaved` to AIConciergePanel; `onIdeaAssigned` refreshes itinerary days + TripBuilder
- `backend/tests/test_trip_ideas.py` — NEW: 7 backend unit tests
- `frontend/tests/trip-ideas.test.mjs` — NEW: 12 frontend renderer/contract tests

### Behavior change
- AI Concierge cards now show two actions: **Add to Day** (requires day selection, existing behavior) and **Save** (saves to trip without day assignment, new)
- A **Trip Ideas** section appears in the TripBuilder right panel above itinerary days, only when ideas exist
- Saved ideas are persisted to Supabase `itinerary_items` with `day_id = null` and `details.source_kind = "concierge_idea"`
- Duplicate protection: saving the same place to ideas twice returns the existing item
- Assigning an idea to a day updates `day_id` on the item and removes it from the unscheduled list
- Removing an idea deletes the item from `itinerary_items`

### Known issues
- No schema change: the existing `itinerary_items` table already supports `day_id = null`. The `source_kind` marker is stored in the `details` JSONB column (no migration needed).
- Flight/hotel candidate items (created at trip creation) are also `day_id = null` but are NOT marked `source_kind = "concierge_idea"`, so they remain invisible to the Trip Ideas panel.
- No drag-and-drop from Trip Ideas panel (v1 uses day selector dropdown, consistent with scope).

### Next likely task
- Monitor `source_kind` usage in production to confirm no flight/hotel candidates bleed into the Trip Ideas panel
- Consider adding a "notes" editable field for saved ideas
- Test on mobile: the two-button layout in ConciergeCard should be verified at small viewport widths

### Supabase SQL: No (no migration — existing schema supports `day_id = null` and `details` JSONB)
### Backend touched: Yes (`itinerary.py` service, `trips.py` route)

---

## Previous change (2026-04-29) — UI Design System: Dark Mode-First Foundation

Frontend-only visual upgrade to a premium boutique concierge aesthetic. No backend, API, or business-logic changes.

### Files touched
- `frontend/src/app/globals.css` — full dark theme: body background, `.card`, `.glass`, `.btn-primary` (→ warm gold), `.btn-ghost`, `.btn-emerald`, `.btn-gold`, form controls, badges, skeleton, nav items, color tokens (`--color-cream-*`, `--color-dark-*`, `--color-brand-*`)
- `frontend/src/components/layout/AppShell.tsx` — ambient glow blobs → warm gold/amber on dark bg; loading state → dark
- `frontend/src/components/layout/Sidebar.tsx` — brand icon → gold; borders → white/7%; nav section labels, user avatar
- `frontend/src/components/layout/MobileNav.tsx` — brand icon/active tabs → gold; drawer overlay → black/60%; borders → white/7%
- `frontend/src/components/layout/PageHeader.tsx` — h1 → cream-100; description → cream-500
- `frontend/src/components/ui/StatCard.tsx` — label/value/trend text → cream scale; default colorClass → brand gold
- `frontend/src/components/ui/EmptyState.tsx` — icon container → dark glass surface
- `frontend/src/components/dashboard/DashboardClient.tsx` — stat colorClass props → dark tinted variants
- `frontend/src/components/dashboard/RecentTrips.tsx` — all text/border/hover/link/icon classes → dark
- `frontend/src/components/dashboard/QuickActions.tsx` — action tile surfaces and text → dark
- `frontend/src/components/dashboard/PointsSummary.tsx` — surfaces, text, card color chips → dark
- `frontend/src/components/dashboard/DealsFeed.tsx` — hover/badge/text/link → dark with gold accent
- `frontend/src/app/trips/page.tsx` — modals: `bg-white` → `.card`; inputs → `.input`/`.label`; trip card text/border/button classes → dark

### Behavior change
Visual only. Layout, routing, data, auth, business logic: unchanged. All existing data continues to render identically.

### Design tokens introduced
- `--color-cream-{50–500}`: warm text scale (cream-100 = primary text on dark)
- `--color-dark-{50–500}`: dark surface scale
- `--color-brand-{300–700}`: warm gold accent (replaces sky-blue as primary CTA/accent)

### Known limitations
- Deep trip-detail pages (`/trips/[id]`, concierge panel, search results, cards page) still use light-era Tailwind classes — these pages will inherit the dark card/glass/body styles but inline text classes (`text-slate-*`) may appear dark-on-dark in some sections. Follow-up pass needed.
- Auth pages unchanged (already have a luxury dark background).

### Next likely task
- Page-by-page polish pass: `/trips/[id]` TripBuilder, AIConciergePanel, SearchResultCard, `/cards`, `/settings`
- Consider adding a `text-cream-100` default to `[data-page]` wrappers so any remaining `text-slate-900` elements fall back cleanly
- Validate on mobile (bottom nav gold active state, drawer)

### Supabase SQL required: No
### Backend touched: No

---

## Previous change — whyPick evidence enrichment
Enriched whyPick evidence quality by promoting venue-specific Foursquare tags, Tavily award signals, and Yelp "known for" patterns to structured differentiators (branch: claude/verify-whypick-pipeline-73XFm).

## Files touched
- `backend/app/concierge/evidence.py` — core evidence enrichment
- `backend/tests/test_evidence_normalization.py` — 8 new tests
- `backend/tests/test_whypick_differentiators.py` — 2 updated assertions, 8 new tests

## Behavior change
**Foursquare tag specificity filter** (`_foursquare_tag_is_specific`):
- Tags like "handmade tortillas", "craft cocktails", "zero-waste", "omakase" → `safe_for_copy=True`, `confidence=medium`
- Tags like "trendy", "date-night", "casual" → remain `safe_for_copy=False`
- Effect: venues with only Foursquare tags now surface as differentiators in `select_differentiators()` and reach the LLM prompt as anchors

**Tavily award extraction** (`_AWARD_SIGNAL_RE`):
- Tavily snippets mentioning Michelin stars, James Beard, award-winning → promote an `attribute` unit with `safe_for_copy=True`
- Enables LLM to anchor whyPick on awards even when no Michelin status was supplied explicitly

**Yelp "known for" extraction** (`_KNOWN_FOR_RE`):
- Yelp review excerpts with "known for X", "celebrated for X", "acclaimed for X" → promote an `attribute` unit with `safe_for_copy=True`
- Enables extraction of signature item signals from user reviews

**Before / After examples:**

| Venue | Before | After |
|-------|--------|-------|
| Kumiko (FS tags only, no editorial) | "A cocktail bar in West Loop, a reliable spot for evening drinks." | "Kumiko is a cocktail bar in West Loop known for japanese-inspired cocktails." |
| Mas Maiz (FS tags) | "Mas Maiz is a Mexican restaurant in Capitol Hill..." (rating fallback) | "Mas Maiz is a Mexican restaurant in Capitol Hill known for handmade tortillas." |

## Known issues
- LLM path still requires `ANTHROPIC_API_KEY` to be set; deterministic path is the active path in all test runs
- Foursquare tag content is lowercased in the deterministic copy builder (`specialty_tags[0].lower()`); proper-noun tags like "Japanese" become lowercase
- foursquare_category units remain `safe_for_copy=False` (category labels are not differentiators)

## Next likely task
- Fix lowercasing of specialty tag copy in `reasoning.py` (`_build_nightlife_display_why` / `_build_cuisine_restaurant_display_why`)
- Validate that real-world Foursquare tags returned by live API are specific enough to pass the filter (audit production data)
- Consider surfacing yelp_review_excerpt "known for" extraction also from editorial `source_reason` text for secondary attribute units

## Debug notes
- Test suite: 112 tests, 0 failures as of this change
- `_foursquare_tag_is_specific()` in `evidence.py:46` controls the promotion logic; extend `_GENERIC_FS_TAGS` if new generic tags appear in production
- Award regex: `_AWARD_SIGNAL_RE` in `evidence.py:74`; handles "Michelin stars" (plural) and "James Beard" variants
- All new evidence units preserve the `venue_name` anti-contamination field

## 2026-04-29 Hardening Follow-up (Post PR #164)

### Summary
- Extended generic Foursquare tag blocklist with: `cocktail bar`, `highly rated`, `good drinks`, `nightlife`.
- Added Yelp `known for X` generic-signal guard to reject service/praise-only matches (`great`, `customer`, `service`, `popular`, `nice`, `friendly`, `good food`, `good drinks`) while preserving specific differentiators.
- Threaded safe attribute-claim units (`yelp`/`tavily` attributes) into deterministic fallback specialty tags so fallback whyPick can use concrete non-Foursquare differentiators.

### Tests
- `backend/tests/test_evidence_normalization.py`
- `backend/tests/test_whypick_differentiators.py`
- `backend/tests/test_whypick_integration.py`

### Next Step
- Monitor production logs for fallback whyPick copy quality to confirm no drift toward generic language after adding attribute-driven specialty fallback.

## 2026-05-02 Explore hydration follow-up (existing trips still empty)
- Root assumption corrected: existing-trip Explore candidates are available from persisted itinerary items, not only from runtime provider `/search/attractions` and `/search/restaurants` calls.
- TripBuilder now hydrates `candidateAttractions` and `candidateRestaurants` from `fetchTripItems(tripId)` by mapping trip-level `activity`/`meal` items (`day_id = null`) into the exact panel-rendered candidate state shape.
- Provider-backed attraction/restaurant hydration remains as fallback only when persisted candidates are absent.
- Added one-shot hydration keys (`tripId + destination`) and in-flight request refs to prevent duplicate expensive provider calls during rerenders/refresh loops.

## 2026-05-02 Explore hydration scoring + ranking follow-up
- Existing-trip Explore hydration can ingest persisted itinerary `details` with mixed key casing. Do **not** assume only camelCase: saved payloads may carry `ai_score`, `num_reviews`, `price_level`, `opening_hours`, and sometimes plain `score`.
- If hydration mapper only reads camelCase (`aiScore`), candidate cards degrade to basic metadata with `aiScore` undefined, causing score badge fallback `0` and false-positive Top Pick when badge logic uses list index.
- Existing-trip candidate breadth should not depend solely on persisted trip-level items (often user-pruned subset). Keep one-shot provider refresh for destination hydration so existing trips converge toward create-trip candidate breadth without rerender loops.

- 2026-05-02: Explore score restoration follow-up: unified attraction/restaurant score normalization across both provider search mapping and existing-trip persisted hydration (`aiScore`/`ai_score`/legacy `score`) to restore meaningful ranking after refresh without fake 0 fallbacks; kept Top Pick gated on positive normalized score and retained one-shot provider refresh behavior.

## 2026-05-02 – Wife-testing QA: Trusted Explore restaurant identity
- Explore restaurant cards must have verified Google place identity to be treated as trusted/addable in Explore.
- Frontend now filters out unverified restaurant results/snapshots (missing `google_maps_uri` and place id aliases).
- Restaurant Maps links now prioritize canonical `google_maps_uri`, then `place_id` URL, instead of loose `name + city` query when verified identity exists.
- Snapshot persistence/hydration now carries `provider_place_id` / `google_maps_uri` / `place_id` to prevent reintroducing unverified entities after refresh.

## 2026-05-03 – Explore Restaurants no-empty-list trust contract regression
- Root cause: frontend Explore restaurant trust gate correctly required verified Google identity, but mapper did not recognize newer backend alias fields (`google_place_id`, `formatted_address`, `user_ratings_total`, `review_count`) so valid verified cards could lose identity and get filtered out as untrusted/empty.
- Contract tightened (not loosened): trusted/addable restaurant cards still require canonical Google identity (`google_maps_uri` OR place id identity).
- Mapper/hydrator now preserve alias fields across search response and explore snapshot hydration so verified restaurants survive: `google_place_id` aliases into `providerPlaceId`/`placeId`, address falls back to `formatted_address`, and review count falls back to `review_count`/`user_ratings_total`.
- Added no-empty-list regression contract tests in `frontend/tests/explore-restaurants-trust-contract.test.mjs` and wired them into frontend `npm test`.

## Wife-testing QA regression (2026-05-03)
- Existing trips with persisted `explore_snapshot.restaurants: []` must self-heal via one controlled live Restaurants refetch; empty restaurant snapshots are not a healthy final state.
- Keep verified Google trust gates strict; persist successful verified replacement back to snapshot to recover refresh behavior.

- Restaurant debug rule (2026-05-03): Always log counts/status across backend and frontend: backend `/search/restaurants` must emit raw candidate count, verified candidate count, returned count, `source_status`, and `cache_status`; frontend mapper must log input/mapped/dropped counts with reason buckets; snapshot save must log saved restaurant count and status markers to diagnose whether 0 came from backend or trust-gate filtering.


## 2026-05-04 Concierge context continuation fix (PR 2.6)
- Fixed subtype loss in more-options continuation by deriving a prior place query hint from recent prompts first (e.g., "Italian restaurants") and falling back to broad category only when subtype is unavailable.
- Added safe post-verification duplicate exclusion for more-options provider responses using stable identities in priority order: provider_place_id, google_maps_uri, then normalized name+address fallback.
- Duplicate exclusion is scoped only to continuation provider path; refine_previous reuse (`top 3`/`best one`/`compare`) remains unchanged and still skips provider calls when eligible.
- If unique verified cards are exhausted after exclusion, response intentionally returns fewer cards (including zero) rather than repeating prior cards or fabricating entities.

## 2026-05-04 Concierge continuation dedupe follow-up (PR 2.7)
- Root cause of remaining duplicate cards: continuation dedupe keys were too narrow (`provider_place_id` + `google_maps_uri` + exact `name|formatted_address` only), so cards using alias identity fields or punctuation/format variants in address could bypass exclusion and reappear.
- Durable fix: continuation-only dedupe now builds identity keys from both prior pool and returned verified cards using stable IDs (`google_place_id` / `provider_place_id` / `place_id` / `google_maps_uri`) plus normalized fallback (`normalized name + normalized address`).
- Exclusion remains post-provider/post-verification and runs even when the provider response comes from cache, so cache hits still honor prior-card uniqueness.
- If all candidates are prior duplicates, API returns fewer/zero cards; no fabricated replacements are generated.
- Added continuation dedupe observability log fields: `prior_exclusion_count`, `raw_candidate_count`, `verified_candidate_count`, `excluded_prior_duplicate_count`, `final_unique_count`, and `cache_status`.


### Regression fix (2026-05-04): fresh concierge searches incorrectly labeled Google as unavailable
- **Root cause:** `ConciergeService.search()` set `force_research_only` from `require_google && !live_result.has_data()`. This conflated *any empty live result* (e.g., provider returned no candidate hits) with *actual Google verifier unavailability*.
- **Durable contract:** `force_research_only` now triggers only when `LiveResearchResult.source_status == SOURCE_UNAVAILABLE`.
- **Supporting fix:** `LiveResearchService.fetch()` now marks the strict Google-required/unavailable branch with `source_status=SOURCE_UNAVAILABLE` (instead of `live_search`) so callers can distinguish true dependency unavailability from ordinary empty-search outcomes.
- **Impact:** Fresh searches (`prior_key_count=0`) no longer emit the false warning "Google verification unavailable" unless the verifier is truly unavailable; continuation and prior-dedup logic are unchanged.

- 2026-05-05: AI Concierge rating display scale fix — root cause was a legacy `rating * 2` conversion in `backend/app/concierge/semantic_retrieval.py::_entity_to_card`, which serialized/displayed Google ratings on 0–10. Fixed to preserve native Google 0–5 rating in card `rating` and meta line while leaving review count wiring unchanged. Added focused semantic retrieval regression tests for native 4.6 display + null-rating safety; no semantic retrieval ranking/planning/trust gate behavior changed.

## 2026-05-05 — Live semantic retrieval card display contract fix
- Fixed AI Concierge drawer live contract issue where `/ai/concierge/search` place payloads were not normalized in frontend API client, causing semantic verified cards to be dropped and replies to appear text-only.
- Root cause: response schema mismatch (backend snake_case typed payload vs frontend camelCase expectation in `callConciergeSearch`).
- Tests added/run:
  - backend/tests/test_concierge_router_v2.py (Izakayas + Izakayas on Fulton Street place payload preservation; empty-card no-fabrication behavior)
  - frontend/tests/concierge-renderers.test.mjs (assert search path normalizes typed response before card mapping)
- Production validation checklist:
  - Izakayas
  - Izakayas on Fulton Street
  - best breweries
  - best waterfront breweries
  - breweries near the river
  - taprooms with a view
- PR-3 batched grounded reasoning was not started.

## Update (2026-05-05) — L2 frontend semantic card render hotfix

### Situation
- After the prior `/ai/concierge/search` typed normalization patch, live UI still rendered text-only bubbles for semantic place asks (`izakayas`, `izakayas on fulton street`) even though Railway logs showed `response_type=place_recommendations` and `final_card_count=8`.

### Final root cause
- Frontend drawer renderer (`AIConciergePanel`) used a strict addable-card gate: `type === "verified_place"`.
- In live typed payload variants, cards may still be verified via `verifiedPlace` / `googleVerification` even when `type` is omitted.
- Result: cards reached the assistant message path but were filtered out at render time, so no addable cards were displayed.

### Fix applied
- Added `isRenderableVerifiedPlace` and replaced strict type-only filters for restaurants/attractions/hotels with shape-tolerant verified-card checks (`type` OR `verifiedPlace` OR `googleVerification`).
- Kept changes surgical to frontend rendering path only.

### Tests added/run
- Added frontend regression assertion to ensure renderer no longer hard-requires `type=verified_place`.
- Ran frontend test suite including concierge renderer contracts.

### Production validation checklist (post-deploy)
- `izakayas`
- `izakayas on fulton street`
- `best breweries`
- `best waterfront breweries`
- `breweries near the river`
- `taprooms with a view`

### Scope guardrails
- No semantic planner/ranker/provider/category changes.
- No visual redesign.
- PR-3 batched grounded reasoning **not started**.
- PGRST204 logging/schema issue deferred (non-blocker for card rendering path in this PR).
