# AI Concierge Semantic Place Intelligence v2 Amendment

Date: 2026-05-06  
Repo: `prashanthkrishnan91/claude_travelapp_pk91`  
Status: Architecture amendment / implementation north star  
Severity classification: Level 3 — architecture correction and full delivery plan

## 1. Purpose

This document amends `artifacts/ai_concierge_semantic_place_intelligence.pdf` and becomes the binding north-star plan for AI Concierge work from PR #256 onward.

The original PDF remains the base architecture. This amendment supersedes the PDF wherever the PDF allows slower latency, visible fallback notes, deterministic-only trust gates, late card-role work, or repeated UI testing between architecture PRs.

The product goal is unchanged: build a best-in-world AI travel concierge, not a keyword search app. The AI Concierge must support open natural-language place understanding, verified Google-backed addable cards, fast premium-ranked results, evidence-grounded judgment, conversational follow-ups, and an addictive UX that makes Google Maps a support link rather than the destination.

## 2. What happened and why this amendment exists

The original architecture was not completed. PRs #250-#255 implemented and hardened a partial semantic-retrieval and note-quality slice, then repeatedly patched symptoms:

- cards could be returned for previously failing open-language asks,
- Google verification and typed card contracts improved,
- deterministic visible fallbacks were blocked,
- note logging and quality regexes improved,
- modifier telemetry and concept-generic prompt language improved.

However production screenshots showed the system still produced shallow, literal-decoding notes such as reasoning from a place name or category instead of explaining why a card is worth choosing. The request path could also remain too slow. That is a product failure. A safe but useless note is not a concierge note.

The lesson: the old PR loop optimized for preventing bad claims, not for producing trustworthy, comparative, premium judgment under a hard latency budget.

## 3. Superseded assumptions from the original PDF

The following original-PDF ideas are superseded:

1. **Latency targets**: p50 `<4s`, p95 `<7.5s`, hard timeout `9s` are no longer good enough. They become fallback ceilings only.
2. **Visible deterministic fallback reasons**: fallback prose should not be shown. A card without a strong note is better than a card with a weak note.
3. **Trust Gate as mostly deterministic validators**: regex/citation validators catch hallucinations but cannot judge whether a note is useful. A real reviewer agent is required.
4. **Card roles as Phase 4+ polish**: roles are core to curation and must ship with the search/reasoning foundation.
5. **UI testing after every micro-PR**: stop. Complete the full architecture sequence with code review, tests, and logs first. Then do one end-to-end UI validation pass.

## 4. New non-negotiable product invariants

1. **Target response time**: p50 <= 2.5s, p75 <= 3.0s, p95 <= 4.0s.
2. **Hard kill-switch**: server returns the best available response by 6.0s.
3. **First response curation**: default first response is 6 cards; allowed range is 5-7 cards.
4. **More options**: additional cards are available through pool-backed continuation, not first-response dumping.
5. **Verified-only cards**: every addable card must have stable Google `place_id`, `OPERATIONAL` status, and Google Maps URI.
6. **Evidence flexibility**: Google is canonical for addability; Yelp/Foursquare/Tavily/editorial/web/review summaries can all provide reasoning evidence when trustworthy and available within budget.
7. **No visible fallback notes**: if a note is weak, unsafe, timed out, fallback-generated, or merely restates visible rating/review/category/address data, hide it.
8. **No forced notes**: a card can be excellent without a note. The `Concierge Note` block is earned, not guaranteed.
9. **No literal-decoding notes**: notes may not reason primarily from “the name suggests,” “category anchors,” “address suggests,” or “has many reviews.”
10. **Set-level reasoning**: notes explain why each card belongs in the curated set and why someone would choose it over the others.
11. **Reviewer-gated reasoning**: visible notes require a reviewer pass for usefulness, specificity, groundedness, comparative value, query-fit, and premium tone.
12. **No mid-sequence UI pivoting**: after PR #256 starts, do not pivot based on partial UI tests until the architecture sequence is complete and certification passes.

## 5. Final architecture: Premium Concierge Intelligence Engine

```text
User query + trip context + prior pool
  -> Turn Interpreter
  -> Semantic Frame Agent
  -> Deadline Manager
  -> Parallel Retrieval Layer
       - Google Text Search / Nearby / Details where budgeted
       - cache lookup
       - optional Yelp/Foursquare/editorial evidence in parallel
  -> Verified Place Entity Layer
       - canonicalize
       - dedupe
       - Google operational/addable gate
  -> Curated Ranker
       - semantic fit
       - geo fit
       - vibe fit
       - evidence strength
       - diversity
       - card roles
  -> Place Evidence Dossier Builder
       - compact evidence for top 5-7 only
       - review themes, not review counts
       - source confidence and caveats
  -> Set-Level Concierge Writer
       - one summary
       - one role per card
       - optional note per card
  -> LLM Concierge Reviewer Gate
       - approve | rewrite_once | hide
  -> Response Assembler
       - show approved notes only
       - hide weak notes
       - include more-options cursor
  -> Result Pool + Observability
```

## 6. Stage budgets

These are engineering targets, not promises to wait this long.

| Stage | Target |
|---|---:|
| Turn classification + trip context | 50-100ms |
| Semantic frame extraction | 150-400ms target, 700ms budget |
| Parallel Google retrieval/verification | 600-1000ms |
| Entity layer + dedupe | <75ms |
| Curated ranker + diversity + role draft | <150ms |
| Evidence dossier for top 5-7 | 300-700ms |
| Set-level writer | 400-700ms |
| Reviewer gate | 250-500ms |
| Response assembly | <100ms |
| Target end-to-end | <=3000ms |
| Soft ceiling | <=4000ms |
| Hard cutoff | <=6000ms |

If any non-critical step misses its budget, skip/degrade that step and return the best available verified cards.

## 7. Evidence model

### 7.1 Verification vs reasoning evidence

Google remains the only verification spine for addable cards.

Reasoning evidence may come from:

- Google identity, status, ratings, categories, address, coordinates, hours, photos, summaries where available;
- Yelp review themes, categories, vibe, food/drink/service/crowd signals where available;
- Foursquare tastes, tags, tips, and venue personality where available;
- Tavily/Brave/Serper/editorial snippets as supporting evidence only;
- computed geography, distance, walk-time, hotel/itinerary context;
- prior selected/rejected places once personalization phases begin.

Do not box the reasoner into a single provider when multiple trustworthy signals are available. Do keep addable-card minting strict.

### 7.2 Evidence Dossier shape

For each top card, build a compact `PlaceEvidenceDossier`:

```json
{
  "place_id": "google-place-id",
  "name": "...",
  "neighborhood": "...",
  "category": "...",
  "query_fit": {
    "concept_fit": 0.0,
    "modifier_fit": 0.0,
    "geo_fit": 0.0,
    "vibe_fit": 0.0
  },
  "provider_evidence": {
    "google": [],
    "yelp": [],
    "foursquare": [],
    "editorial": [],
    "computed": []
  },
  "review_themes": {
    "food_drink": [],
    "ambiance": [],
    "service": [],
    "crowd_noise": [],
    "view_patio_waterfront": [],
    "occasion_fit": [],
    "negative_caveats": []
  },
  "confidence": "strong|mixed|weak",
  "internal_evidence_gaps": []
}
```

`internal_evidence_gaps` must never become visible fallback prose.

## 8. Curated ranking and card roles

The first response is not inventory. It is a curated shortlist.

The Ranker must produce 5-7 cards with diversity and role coverage. Roles are first-class output, not UI polish.

Suggested card role enum:

```text
best_overall
most_query_specific
best_atmosphere
best_food_or_drink_program
best_date_night
best_value_feel
closest_or_easiest
most_distinctive
safe_crowd_pleaser
caveat_pick
more_options_candidate
```

Role assignment rules:

- Do not assign six cards the same role.
- Do not include duplicate-feeling cards unless the query demands it.
- Use pairwise comparison across the final set.
- Every visible note should connect to the card role.
- A card can be shown without a note but should still have an internal role for ranking and follow-ups.

## 9. Set-level Concierge Writer

The writer sees the full ranked set, not isolated cards.

Inputs:

```json
{
  "user_query": "...",
  "frame": {},
  "ranked_cards": [],
  "evidence_dossiers": [],
  "card_roles": [],
  "trip_context": {}
}
```

Outputs:

```json
{
  "summary": "one concise top-level concierge summary",
  "cards": [
    {
      "place_id": "...",
      "role": "best_overall",
      "display_note": "optional one-sentence note",
      "best_for": "...",
      "tradeoff": "optional",
      "evidence_ids": ["..."],
      "writer_confidence": "strong|acceptable|weak"
    }
  ]
}
```

Rules:

- One fast set-level call, not N per-card calls.
- Notes must be concise, comparative, and useful.
- Notes must not restate rating/review count/category/address unless that fact is genuinely part of a higher-value judgment.
- If the writer cannot produce a useful note, return no note for that card.

## 10. LLM Concierge Reviewer Gate

Regex and deterministic validators remain as cheap guardrails, but they are not enough. Add an LLM reviewer that reads the user query, frame, final ranked set, evidence dossier, role, and proposed note.

The reviewer grades each note on:

1. **Groundedness**: every claim is supported by provided evidence.
2. **Usefulness**: would this help the user choose this place?
3. **Comparative value**: does this explain why this card belongs relative to others?
4. **Specificity**: is it about this place, not the generic category?
5. **Query-fit**: does it answer the actual ask?
6. **Non-obviousness**: does it add value beyond rating, review count, category, address, or name?
7. **Premium tone**: does it sound like a sharp concierge, not a database?
8. **Embarrassment test**: would we be comfortable showing this to the wife knowing she can click Google Maps in one second?

Reviewer output:

```json
{
  "place_id": "...",
  "decision": "approve|rewrite_once|hide",
  "quality": "strong|acceptable|hide",
  "reason_codes": [],
  "approved_note": "optional"
}
```

Visible note rule:

```text
show only if reviewer quality is strong or acceptable
hide if weak, unsafe, missing, timed_out, fallback, or reviewer=hide
```

No visible fallback note should ever be generated.

## 11. Frontend display contract

The frontend should render:

- 5-7 premium cards;
- role badges when available;
- ratings/review counts in the existing subheader only;
- `Concierge Note` only when approved by reviewer;
- no note block at all when hidden;
- a clear `More options` action backed by the result pool.

Do not show:

- “lack of evidence” notes;
- “verify yourself” as a fallback note;
- rating/review-volume prose;
- name/category/address decoding;
- placeholder notes;
- deterministic fallback notes.

## 12. Observability that measures product quality

Current `reasoning_success=true` can be misleading because a note can be contract-valid but useless. Add product-quality telemetry:

```text
turn_total_ms
stage_timings
final_card_count
first_return_card_limit
visible_note_count
hidden_note_count
reviewer_quality_distribution
reviewer_hide_reason_counts
writer_timed_out
reviewer_timed_out
fallback_note_visible_count // must always be 0
cards_without_notes
card_role_distribution
evidence_sources_used_per_note
review_theme_count_per_card
provider_timeout_counts
cache_hit_summary
more_options_cursor_present
```

Certification must fail if `fallback_note_visible_count > 0`.

## 13. Updated delivery plan

Do not UI-test or product-pivot between these PRs. Review code, tests, logs, and contracts only until the sequence is complete.

### PR #256 — North-star artifact + workflow reset

Add this amendment and update workflow docs so every implementation agent knows this supersedes the stale parts of the PDF.

Acceptance:

- v2 amendment exists in `artifacts/`.
- HANDOFF/progress log identify this as the binding north star.
- No app behavior changes.

### PR #257 — SLA + result cap + no visible fallback contract

Implement deadline manager and response limits:

- target <=3s, soft <=4s, hard <=6s;
- first response default 6 cards, allowed 5-7;
- reason generation is optional under budget;
- no visible fallback notes.

### PR #258 — Parallel retrieval and critical/non-critical path split

Google retrieval/verification is critical. Yelp/Foursquare/editorial/web evidence is parallel and deadline-bound. No non-critical enrichment can block the response.

### PR #259 — Evidence Dossier v1 + review-theme extraction

Normalize evidence for top cards only. Extract review/vibe/theme signals, not review counts. Prove via logs/tests what evidence reaches the writer.

### PR #260 — Curated ranker + card roles

Add pairwise/diversity curation and card-role output before note writing.

### PR #261 — Set-level Concierge Writer

Replace isolated per-card note generation with one set-level writer over final cards + dossiers + roles.

### PR #262 — LLM Reviewer Gate

Add reviewer that approves/rewrite-once/hides based on usefulness, groundedness, specificity, comparative value, query-fit, non-obviousness, and premium tone.

### PR #263 — Frontend display contract

Render role badges and approved notes only. Hide weak notes entirely. Preserve addable card UX.

### PR #264 — End-to-end SLA, quality certification, and production telemetry

Certification suite checks speed, card count, verified addability, note approval, hidden-note behavior, more-options cursor, provider timeouts, and logs.

Only after PR #264 should the user perform full UI testing.

## 14. Certification queries

Use these after the full sequence, not between PRs:

```text
breweries near the river
taprooms with a view
izakayas
listening bars
tea houses with a garden
natural wine bars near the water
kaiseki spots
quiet cocktail bars for a date night
romantic tapas but not too loud
nice sushi restaurants with a waterfront view
upscale seafood but not touristy
best brunch near our hotel
```

Pass criteria:

```text
p50 <= 2500ms
p75 <= 3000ms
p95 <= 4000ms
hard cutoff <= 6000ms
first cards between 5 and 7
Google-verified addable cards only
fallback_note_visible_count == 0
weak notes hidden
visible notes pass reviewer
visible notes are comparative and useful
no literal name/category/address decoding
no review-count/rating-volume reasoning
more-options cursor works
stage timing logs emitted
reviewer quality distribution emitted
```

## 15. Stop conditions

Stop and reclassify before coding further if any implementation PR:

- requires increasing the hard cutoff beyond 6s;
- makes visible fallback notes necessary;
- adds per-card LLM loops;
- mints addable cards from non-Google sources;
- depends on category keyword patches for production behavior;
- skips the reviewer gate;
- removes Google verification strictness;
- changes the frontend to mask backend reasoning weakness;
- causes broad UI testing before PR #264 certification.

## 16. Final north-star statement

The AI Concierge should feel like a fast, opinionated, trustworthy local expert who knows the trip context and returns a small set of excellent, addable choices. It should never feel like a slow Google Maps wrapper, a keyword search app, or an LLM trying to justify a place from its name.

Build the full amended architecture. Validate it once, end-to-end, after the sequence is complete.
