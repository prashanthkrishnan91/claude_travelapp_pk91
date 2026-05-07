"""Semantic Retrieval v1 — end-to-end verified-card pipeline.

Feature flag: CONCIERGE_SEMANTIC_RETRIEVAL_V1_ENABLED (default False)

Pipeline (when flag ON, new_search, place-recommendation asks):
  1. ExperienceFrame extraction (open-vocabulary, deterministic)
  2. RetrievalPlanner → 1–3 Google Text Search queries
  3. Provider fanout (parallel, per-call deadlines)
  4. Verified Place Entity Layer (Google place id + OPERATIONAL + maps URI gates)
  5. SemanticRanker v1 (subtype_fit dominates, no hard category gate)
  6. MinimalEvidenceBundle per entity
  7. SafeReasonBuilder v1 (honest, ask-anchored, no hallucinated facts)
  8. TrustGate final pass (redundant safety check before card return)
  9. Structured observability log (one line, debuggable in one pass)
  10. Return LiveResearchResult with verified UnifiedRestaurantResult cards

When flag OFF: this module is never called. Existing pipeline is unchanged.
No Tavily, editorial, Yelp, or Foursquare calls in this module.
No SQL. No frontend changes. No personalization. No vector search.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, FrozenSet, List, Optional, Set

logger = logging.getLogger(__name__)

PROVIDER_NAME = "semantic_retrieval_v1"
PIPELINE_VERSION = "semantic_retrieval_v1"
_MAX_CARDS = 8  # pool/ranking size; first response is capped separately by SLA config

# SLA contract (v2 amendment §4 and §6)
from app.concierge.deadline_manager import RequestDeadline, DEFAULT_SLA, clamp_first_card_limit


def run_semantic_retrieval_v1(
    user_query: str,
    destination: str,
    prior_identity_keys: Optional[FrozenSet[str]] = None,
    api_key: Optional[str] = None,
    timeout: float = 5.0,
    max_cards: int = _MAX_CARDS,
) -> "LiveResearchResult":  # type: ignore[name-defined]
    """Run the full Semantic Retrieval v1 pipeline for one concierge turn.

    Args:
        user_query: User's natural-language place ask.
        destination: Trip destination city.
        prior_identity_keys: Already-shown card keys (for dedup).
        api_key: Google Places API key (falls back to env var).
        timeout: Per-provider-call deadline in seconds.
        max_cards: Maximum cards to return.

    Returns:
        LiveResearchResult with verified restaurant cards, or empty result
        if the pipeline fails or returns no verified entities.
        Never raises — falls back to empty on any unhandled error.
    """
    from app.services.live_research import LiveResearchResult
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE, SOURCE_UNAVAILABLE

    t_pipeline_start = time.monotonic()

    if not destination:
        logger.warning("semantic_retrieval_v1: empty destination, skipping")
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    _api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY", "")
    if not _api_key:
        logger.warning("semantic_retrieval_v1: no GOOGLE_PLACES_API_KEY configured")
        return LiveResearchResult(source_status=SOURCE_UNAVAILABLE, provider_name=PROVIDER_NAME)

    try:
        return _run_pipeline(
            user_query=user_query,
            destination=destination,
            prior_identity_keys=prior_identity_keys or frozenset(),
            api_key=_api_key,
            timeout=timeout,
            max_cards=max_cards,
            t_pipeline_start=t_pipeline_start,
        )
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - t_pipeline_start) * 1000)
        logger.exception(
            "semantic_retrieval_v1: unhandled pipeline error "
            "query=%r destination=%r elapsed_ms=%d error=%s",
            user_query, destination, elapsed_ms, exc,
        )
        from app.services.live_research import LiveResearchResult
        from app.models.concierge import SOURCE_NONE
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)


def _run_pipeline(
    *,
    user_query: str,
    destination: str,
    prior_identity_keys: FrozenSet[str],
    api_key: str,
    timeout: float,
    max_cards: int,
    t_pipeline_start: float,
) -> "LiveResearchResult":  # type: ignore[name-defined]
    from app.services.live_research import LiveResearchResult
    from app.models.concierge import SOURCE_LIVE_SEARCH, SOURCE_NONE, SOURCE_UNAVAILABLE

    # ── SLA deadline: governs all remaining stages ───────────────────────────
    deadline = RequestDeadline(sla=DEFAULT_SLA, t_start=t_pipeline_start)
    first_card_limit = clamp_first_card_limit(DEFAULT_SLA.first_card_limit)

    latency: Dict[str, int] = {}

    # ── Step 1: ExperienceFrame extraction ───────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.frame_extractor import extract_frame
    frame = extract_frame(user_query, destination)
    latency["frame_ms"] = int((time.monotonic() - t0) * 1000)

    logger.debug(
        "semantic_retrieval_v1.frame query=%r concepts=%r geo=%r locs=%r prefs=%r neg=%r open_class=%s",
        user_query,
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts],
        frame.geography_hints,
        getattr(frame, "location_modifiers", []),
        frame.soft_preferences,
        frame.negative_constraints,
        getattr(frame, "open_class_place_detected", False),
    )

    # ── Step 2: RetrievalPlanner ─────────────────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.retrieval_planner import plan_queries
    queries = plan_queries(frame)
    latency["plan_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 3: Critical path — Google Text Search fanout (deadline-bounded) ──
    # Uses remaining deadline budget to bound per-call timeout so the critical
    # path cannot overrun the SLA hard cutoff.
    from app.concierge.parallel_retrieval import (
        run_critical_google_fanout,
        run_non_critical_enrichment,
    )
    critical_result = run_critical_google_fanout(
        queries, api_key=api_key, deadline=deadline, timeout=timeout
    )
    provider_results = critical_result.provider_results
    latency["provider_ms"] = critical_result.elapsed_ms

    provider_call_count = len(provider_results)
    provider_success_count = sum(1 for r in provider_results if r.succeeded)
    per_query_latencies = {r.query: r.latency_ms for r in provider_results}
    google_critical_candidate_count = sum(
        len(r.places) for r in provider_results if r.succeeded
    )

    # If all providers failed: return honest no-card result
    if provider_success_count == 0:
        logger.warning(
            "semantic_retrieval_v1: all_provider_queries_failed "
            "query=%r destination=%r queries=%r",
            user_query, destination, queries,
        )
        _log_semantic_turn(
            user_query=user_query,
            frame=frame,
            queries=queries,
            latency=latency,
            provider_call_count=provider_call_count,
            provider_success_count=0,
            raw_candidate_count=0,
            deduped_candidate_count=0,
            verified_entity_count=0,
            rejection_stats={},
            final_card_count=0,
            t_pipeline_start=t_pipeline_start,
            outcome="all_providers_failed",
        )
        return LiveResearchResult(source_status=SOURCE_UNAVAILABLE, provider_name=PROVIDER_NAME)

    # ── Step 4: Verified Place Entity Layer ──────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.place_entity_layer import build_entity_layer
    entities, entity_stats = build_entity_layer(provider_results, prior_identity_keys)
    latency["entity_ms"] = int((time.monotonic() - t0) * 1000)

    raw_count = entity_stats.raw_candidate_count
    verified_count = entity_stats.verified_entity_count

    if not entities:
        logger.warning(
            "semantic_retrieval_v1: no_verified_entities "
            "query=%r destination=%r raw=%d stats=%s",
            user_query, destination, raw_count, vars(entity_stats),
        )
        _log_semantic_turn(
            user_query=user_query,
            frame=frame,
            queries=queries,
            latency=latency,
            provider_call_count=provider_call_count,
            provider_success_count=provider_success_count,
            raw_candidate_count=raw_count,
            deduped_candidate_count=verified_count,
            verified_entity_count=0,
            rejection_stats=vars(entity_stats),
            final_card_count=0,
            t_pipeline_start=t_pipeline_start,
            outcome="no_verified_entities",
        )
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    # ── Step 5: SemanticRanker v1 ────────────────────────────────────────────
    t0 = time.monotonic()
    from app.concierge.ranker import rank_entities_with_stats, build_evidence_bundle
    ranked, ranker_stats = rank_entities_with_stats(entities, frame, top_n=max_cards)
    latency["rank_ms"] = int((time.monotonic() - t0) * 1000)

    # Critical path ends here — capture total time through Google + entity + rank.
    critical_path_ms = deadline.elapsed_ms()

    # ── Step 5.5: Non-critical enrichment (deadline-bounded, skipped if low budget) ─
    # Google Place Details enrichment improves note reasoning evidence only.
    # Skipped when remaining deadline budget is insufficient (< 500 ms reserve).
    # Cannot change card identity or addable status — those are critical-path only.
    # Fixes prior silent bug: enrich_top_cards was never called due to _api_key NameError.
    t0 = time.monotonic()
    remaining_budget_before_enrichment_ms = deadline.remaining_ms()
    enrich_result = run_non_critical_enrichment(
        [e for e, _ in ranked],
        api_key=api_key,
        deadline=deadline,
        budget_n=4,
    )
    enrichment_map = enrich_result.enrichment_map
    latency["enrich_ms"] = enrich_result.elapsed_ms

    # ── Step 5.6: Evidence Dossier v1 (PR #259) ─────────────────────────────
    # Build structured dossiers for top cards using critical + enrichment data.
    # Does not block card return. Minimal dossiers built if budget is too low.
    t0 = time.monotonic()
    from app.concierge.evidence_dossier import (
        DOSSIER_BUDGET_RESERVE_MS,
        EvidenceDossierTelemetry,
        build_dossiers_for_ranked_cards,
        get_dossier_telemetry,
    )
    dossiers = []
    try:
        _primary_concept = (
            frame.subtype_concepts[0].label if frame.subtype_concepts else ""
        )
        low_budget = deadline.remaining_ms() < DOSSIER_BUDGET_RESERVE_MS
        skipped_due_to_budget = 0
        if low_budget:
            for entity, _ in ranked[:first_card_limit]:
                if enrichment_map.get(entity.place_id) is not None:
                    skipped_due_to_budget += 1
        dossiers = build_dossiers_for_ranked_cards(
            ranked=ranked,
            frame=frame,
            enrichment_map=enrichment_map,
            deadline=deadline,
            top_n=first_card_limit,
            category_fn=lambda e: _derive_display_category(
                e.types, e.primary_type, _primary_concept
            ),
        )
        dossier_tel = get_dossier_telemetry(
            dossiers,
            skipped_due_to_budget=skipped_due_to_budget,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: dossier_build_failed query=%r error=%s",
            user_query,
            exc,
        )
        dossier_tel = EvidenceDossierTelemetry()
    latency["dossier_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 5.7: Card Role + Curated Set Ranker v1 (PR #260) ───────────────
    # Assigns internal roles and computes curation scores using dossier data.
    # Optionally reorders the first-response set within conservative bounds.
    # Does not change visible card payload, note generation, or card cap.
    # Failure is fully isolated: original ranked order is preserved on error.
    t0 = time.monotonic()
    from app.concierge.card_curator import (
        CuratedSetResult,
        curate_cards,
    )
    curator_tel: dict = {"curated_fallback_to_original_order": True, "curated_ms": 0}
    curated_result: Optional[CuratedSetResult] = None
    try:
        curated_result = curate_cards(
            ranked=ranked,
            dossiers=dossiers,
            first_card_limit=first_card_limit,
        )
        if curated_result.reordered_count > 0:
            # Rebuild ranked: curated order for the dossier-covered cap, original
            # order for the rest (entries beyond dossier coverage are unchanged).
            n_curated = curated_result.output_count
            curated_entities = [
                (cc.entity, cc.rank_score) for cc in curated_result.curated_cards
            ]
            ranked = curated_entities + ranked[n_curated:]
        curator_tel = curated_result.as_telemetry_dict(
            elapsed_ms=int((time.monotonic() - t0) * 1000)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "semantic_retrieval_v1: curator_failed query=%r error=%s — "
            "falling back to original ranked order",
            user_query,
            exc,
        )
    latency["curator_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 5.8: Set-Level Writer v1 (PR #261) ──────────────────────────────
    # Uses CuratedSetResult + PlaceEvidenceDossier to generate evidence-grounded,
    # set-aware notes. Runs before the deadline check and before Step 6 evidence
    # bundles so it can use richer dossier evidence.
    # Falls back to the existing batched_reason_builder path on any failure.
    # Never blocks card return.
    t0 = time.monotonic()
    from app.concierge.set_level_writer import (
        SetWriterResult,
        write_set_notes,
    )
    set_writer_result: Optional[SetWriterResult] = None
    set_writer_tel: Dict[str, Any] = {"set_writer_fallback_to_existing_path": True}
    if curated_result is not None and curated_result.output_count > 0:
        try:
            set_writer_result = write_set_notes(
                curated_result=curated_result,
                frame=frame,
                deadline=deadline,
                first_card_limit=first_card_limit,
            )
            set_writer_tel = set_writer_result.as_telemetry_dict(
                elapsed_ms=int((time.monotonic() - t0) * 1000)
            )
            set_writer_tel["set_writer_fallback_to_existing_path"] = (
                set_writer_result.timed_out
                or set_writer_result.visible_note_count == 0
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "semantic_retrieval_v1: set_writer_failed query=%r error=%s — "
                "falling back to existing note path",
                user_query,
                exc,
            )
            set_writer_result = None
            set_writer_tel = {"set_writer_fallback_to_existing_path": True}
    latency["set_writer_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 6: Evidence bundles + deterministic SafeReasonBuilder ───────────
    t0 = time.monotonic()
    from app.concierge.safe_reason_builder import build_safe_reason
    from app.concierge.reason_validator import validate_reason

    # Build evidence bundles, deterministic reasons, and validate each one.
    # A deterministic reason that fails validation (e.g., pure name+rating template)
    # is replaced with "" — no note is better than a template. The LLM path will
    # attempt to produce a better note; if it also fails, the card gets no note.
    cards_data: List[Any] = []  # (entity, evidence, rank_score, det_reason)
    det_reason_rejected_count = 0

    for entity, rank_score in ranked:
        enrichment = enrichment_map.get(entity.place_id)
        evidence = build_evidence_bundle(entity, frame, rank_score, enrichment=enrichment)
        det_reason = build_safe_reason(entity, evidence, frame, rank_score)

        # Validate the deterministic reason using the same validator applied to
        # LLM output. If rejected (e.g., pure name+rating template), use ""
        # so the card assembles with no note rather than a template.
        is_valid, rejection = validate_reason(det_reason, frame, evidence)
        if not is_valid:
            logger.warning(
                "semantic_retrieval_v1: det_reason_rejected "
                "name=%s rejection=%s reason=%r",
                entity.name, rejection, det_reason,
            )
            det_reason = ""  # absent note > template
            det_reason_rejected_count += 1

        cards_data.append((entity, evidence, rank_score, det_reason))

    latency["det_reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 7: Note generation — set-level writer (primary) or three-pass LLM ─
    # Primary path: use set-writer notes when the writer ran and produced results.
    # Fallback: existing three-pass build_reasons_with_retry cascade.
    # Budget gate: skip all note generation when past the SLA soft ceiling.
    t0 = time.monotonic()
    from app.concierge.batched_reason_builder import (
        build_reasons_with_retry,
        CardReason,
        ReasoningResultV2,
        SOURCE_OMITTED,
    )

    # Check SLA before committing to LLM note generation.
    remaining_budget_before_reasoning_ms = deadline.remaining_ms()
    note_generation_budget_s = deadline.budget_for_note_generation_s()
    note_generation_timed_out = note_generation_budget_s <= 0.0

    set_writer_primary_active = False  # set True only in the set-writer primary branch
    if note_generation_timed_out:
        # Past soft ceiling — skip note generation entirely.
        # Cards will be assembled without notes; the frontend must not render
        # a Concierge Note block when display_why_validated=False.
        logger.warning(
            "semantic_retrieval_v1: note_generation_skipped_past_soft_ceiling "
            "query=%r elapsed_ms=%d soft_ceiling_ms=%d",
            user_query, deadline.elapsed_ms(), deadline.sla.soft_ceiling_ms,
        )
        card_reasons: Dict[str, CardReason] = {}
        n_cards = len(cards_data)
        reasoning_result = ReasoningResultV2(
            attempted=False,
            failure_reason="skipped_past_soft_ceiling",
            final_card_count=n_cards,
            final_note_omitted_count=n_cards,
        )
    elif (
        set_writer_result is not None
        and not set_writer_result.timed_out
        and set_writer_result.visible_note_count > 0
    ):
        # ── Set-writer primary path ───────────────────────────────────────────
        # Convert set-writer notes to the existing CardReason dict format.
        # Cards with hidden notes (validated=False) are also added so Step 8
        # can include them without a note block — preserving the contract:
        # "hide invalid notes, not valid Google-verified cards."
        set_writer_primary_active = True
        card_reasons = {}
        for idx, (entity, _ev, _rs, _det) in enumerate(cards_data, 1):
            pid = getattr(entity, "place_id", None)
            sw_note = set_writer_result.notes_by_place_id.get(pid) if pid else None
            if sw_note and sw_note.validated:
                card_reasons[str(idx)] = CardReason(
                    note=sw_note.note,
                    source=sw_note.source,
                    validated=True,
                    attempt_count=1,
                    model_used="set_level_writer_v1",
                )
            else:
                # Note hidden but card is still Google-verified — keep the slot
                # so Step 8 can include the card without a note rather than
                # dropping it from the response.
                card_reasons[str(idx)] = CardReason(
                    note="",
                    source="set_level_writer_v1",
                    validated=False,
                    attempt_count=1,
                    model_used="set_level_writer_v1",
                )

        n = len(cards_data)
        accepted = sum(1 for cr in card_reasons.values() if cr.validated)
        src_counts: Dict[str, int] = {}
        for cr in card_reasons.values():
            if cr.validated:
                src_counts[cr.source] = src_counts.get(cr.source, 0) + 1

        reasoning_result = ReasoningResultV2(
            attempted=True,
            success=(accepted == n),
            accepted_count=accepted,
            final_card_count=n,
            final_note_omitted_count=n - accepted,
            deterministic_visible_count=0,  # invariant: always 0
            failure_reason=(
                None if accepted == n
                else f"set_writer_partial:{n - accepted}_missing"
            ),
            model="set_level_writer_v1",
            fallback_model="",
            visible_note_source_counts=src_counts,
        )
        logger.info(
            "semantic_retrieval_v1: set_writer_primary accepted=%d/%d",
            accepted, n,
        )
    else:
        # ── Fallback: existing three-pass cascade ─────────────────────────────
        card_reasons, reasoning_result = build_reasons_with_retry(
            cards_data, frame, timeout_s=note_generation_budget_s
        )
    latency["batched_reason_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 8: Assemble final cards ─────────────────────────────────────────
    cards, rank_debug, excluded_unvalidated, visible_note_count, cards_without_notes_count = (
        _assemble_card_set(
            cards_data=cards_data,
            card_reasons=card_reasons,
            frame=frame,
            note_generation_timed_out=note_generation_timed_out,
            set_writer_primary_active=set_writer_primary_active,
        )
    )

    latency["reason_ms"] = latency["det_reason_ms"] + latency["batched_reason_ms"]

    # ── Step 8.5: Per-card observability log ─────────────────────────────────
    _log_per_card_notes(user_query, cards_data, card_reasons, frame)

    # ── Step 9: TrustGate final pass ─────────────────────────────────────────
    t0 = time.monotonic()
    cards, trust_rejected = _trust_gate(cards)
    latency["trust_gate_ms"] = int((time.monotonic() - t0) * 1000)

    # ── Step 9.5: First-response card cap (v2 amendment §4 invariant 3) ──────
    # Cap at first_card_limit (default 6, range 5–7) for the first response.
    # The upstream ranked pool of up to _MAX_CARDS remains available for
    # continuation/more-options turns via the result pool (managed by router).
    # fallback_note_visible_count is always 0 — enforced structurally because
    # reason_validated=False hides the note block; no deterministic text is
    # ever written with reason_validated=True.
    pre_cap_count = len(cards)
    cards = cards[:first_card_limit]
    final_card_count = len(cards)

    # Recount note counts post-cap to match returned card set.
    if note_generation_timed_out:
        visible_note_count = 0
        cards_without_notes_count = final_card_count
    else:
        # Recalculate for the capped set (cards with validated notes only).
        visible_note_count = sum(
            1 for c in cards
            if getattr(getattr(c, "display", None), "display_why_validated", False)
        )
        cards_without_notes_count = final_card_count - visible_note_count

    # ── Step 10: Structured observability ────────────────────────────────────
    # Wrong-category fit diagnostics: count entities whose subtype_fit fell
    # below the wrong-category threshold (used for visibility into ranker
    # behavior, not for any hard gate). off_concept_dropped reports the
    # entities removed by the post-rank venue-head filter — i.e., modifier-only
    # matches discarded so a brewery ask doesn't surface parks or riverwalk
    # attractions that just happen to satisfy the geo modifier.
    wrong_category_count = sum(
        1 for _, rs in ranked if rs.subtype_fit < 0.30
    )
    top_card_name = cards[0].name if cards else ""
    top_card_city = ""
    if cards:
        # Extract city/area from the top card's formatted address.
        # Filter out building fragments (Lower Level, Suite, Floor, etc.) so that
        # "Lower Level, Chicago, IL" returns "Chicago", not "Lower Level".
        from app.concierge.safe_reason_builder import _NON_NEIGHBORHOOD_FRAGMENTS
        addr = getattr(cards[0], "neighborhood", "") or ""
        addr_parts = [p.strip() for p in addr.split(",")]
        _ADDR_SKIP = frozenset({"usa", "us", "il", "ny", "ca", "tx", "fl", "wa"})
        for part in addr_parts:
            p_lower = part.strip().lower()
            if not part or any(c.isdigit() for c in part) or len(part) <= 2:
                continue
            if p_lower in _ADDR_SKIP:
                continue
            # Skip building fragments — never report them as city
            if p_lower in _NON_NEIGHBORHOOD_FRAGMENTS:
                continue
            if any(p_lower.startswith(frag) for frag in _NON_NEIGHBORHOOD_FRAGMENTS if len(frag) > 4):
                continue
            top_card_city = part.strip()
            break

    rejection_stats = {
        **vars(entity_stats),
        "trust_gate_rejected": trust_rejected,
        "wrong_category_low_subtype_fit": wrong_category_count,
        "off_concept_dropped": ranker_stats.off_concept_dropped,
        "on_concept_count": ranker_stats.on_concept_count,
        "venue_head_recognized": ranker_stats.concept_is_recognized,
        "destination_penalized_count": ranker_stats.destination_penalized_count,
        "det_reason_rejected_count": det_reason_rejected_count,
        # Truthful telemetry: Reasoning Reliability v2 fields.
        "reasoning_attempted": reasoning_result.attempted,
        "reasoning_model": reasoning_result.model,
        "reasoning_success": reasoning_result.success,
        "reasoning_failure_reason": reasoning_result.failure_reason,
        "llm_accepted_count": reasoning_result.accepted_count,
        "retry_recovered_count": reasoning_result.retry_recovered_count,
        "fallback_model_used_count": reasoning_result.fallback_model_used_count,
        "deterministic_visible_count": 0,  # invariant: always 0
        "final_note_omitted_count": reasoning_result.final_note_omitted_count,
        "excluded_unvalidated_count": excluded_unvalidated,
        "prompt_builder_error": reasoning_result.prompt_error,
        "diversity_flagged": reasoning_result.diversity_flagged,
        "visible_note_source_counts": reasoning_result.visible_note_source_counts,
        # Legacy fields for compatibility with existing log parsers
        "grounded_reason_attempted": reasoning_result.attempted,
        "grounded_reason_success": reasoning_result.success,
        # PR #261 set-level writer
        "set_writer_used": (
            set_writer_result is not None
            and not set_writer_result.timed_out
            and set_writer_result.visible_note_count > 0
        ),
        "set_writer_visible_note_count": (
            set_writer_result.visible_note_count
            if set_writer_result is not None else 0
        ),
        # Honest card-count telemetry (split into distinct signals):
        # - insufficient_verified_candidates: true when Google returned too few
        #   verified places before note assembly — genuinely not enough supply.
        # - below_first_card_limit: true when the returned set is smaller than
        #   the configured default (may be caused by note validation, cap, or
        #   trust gate — not necessarily insufficient Google supply).
        "insufficient_verified_candidates": verified_count < 5,
        "below_first_card_limit": final_card_count < first_card_limit,
        "pre_assembly_verified_count": verified_count,
    }
    _log_semantic_turn(
        user_query=user_query,
        frame=frame,
        queries=queries,
        latency=latency,
        provider_call_count=provider_call_count,
        provider_success_count=provider_success_count,
        raw_candidate_count=raw_count,
        deduped_candidate_count=verified_count,
        verified_entity_count=verified_count,
        rejection_stats=rejection_stats,
        final_card_count=final_card_count,
        t_pipeline_start=t_pipeline_start,
        outcome="ok" if final_card_count > 0 else "no_cards_after_trust_gate",
        rank_top3=rank_debug[:3],
        reason_source=reasoning_result.visible_note_source_counts and "llm_evidence_pack_v2" or "none",
        top_card_name=top_card_name,
        top_card_city=top_card_city,
        # SLA telemetry (v2 amendment §12)
        target_response_ms=DEFAULT_SLA.target_ms,
        soft_ceiling_ms=DEFAULT_SLA.soft_ceiling_ms,
        hard_cutoff_ms=DEFAULT_SLA.hard_cutoff_ms,
        first_return_card_limit=first_card_limit,
        pre_cap_card_count=pre_cap_count,
        visible_note_count=visible_note_count,
        hidden_note_count=cards_without_notes_count,
        fallback_note_visible_count=0,  # structural invariant: always 0
        note_generation_timed_out=note_generation_timed_out,
        cards_without_notes=cards_without_notes_count,
        more_options_cursor_present=False,  # cursor lives in router layer
        # PR #258 parallel retrieval telemetry
        critical_path_ms=critical_path_ms,
        non_critical_enrichment_ms=enrich_result.elapsed_ms,
        provider_fanout_ms=latency["provider_ms"],
        provider_timeout_counts=critical_result.timeout_count,
        provider_skipped_due_to_budget_counts=enrich_result.skipped_count if enrich_result.skip_reason else 0,
        google_critical_success=critical_result.success,
        google_critical_candidate_count=google_critical_candidate_count,
        google_verified_count=verified_count,
        non_critical_enrichment_used_count=enrich_result.used_count,
        non_critical_enrichment_skipped_count=enrich_result.skipped_count,
        remaining_budget_before_reasoning_ms=remaining_budget_before_reasoning_ms,
        # PR #259 evidence dossier telemetry
        dossier_telemetry=dossier_tel,
        # PR #260 curator telemetry
        curator_telemetry=curator_tel,
        # PR #261 set-level writer telemetry
        set_writer_telemetry=set_writer_tel,
        # PR this: semantic frame finalization telemetry
        frame_finalization_telemetry={
            "raw_concepts": [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts],
            "finalized_venue_head": frame.subtype_concepts[0].label if frame.subtype_concepts else "",
            "suppressed_preference_nouns": getattr(frame, "suppressed_preference_nouns", []),
            "soft_preferences": getattr(frame, "soft_preferences", []),
            "normalized_soft_preferences": getattr(frame, "normalized_soft_preferences", []),
            "hidden_gem_preference_active": "hidden_gem" in getattr(frame, "normalized_soft_preferences", []),
            "temporal_constraints": getattr(frame, "temporal_constraints", []),
            "geography_hints": getattr(frame, "geography_hints", []),
            "retrieval_queries": queries,
            "insufficient_verified_candidates": verified_count < 5,
            "below_first_card_limit": final_card_count < first_card_limit,
            "pre_assembly_verified_count": verified_count,
            "final_card_count": final_card_count,
        },
    )

    if not cards:
        return LiveResearchResult(source_status=SOURCE_NONE, provider_name=PROVIDER_NAME)

    return LiveResearchResult(
        restaurants=cards,
        source_status=SOURCE_LIVE_SEARCH,
        provider_name=PROVIDER_NAME,
    )


def _minimal_safe_note(entity: Any) -> str:
    """Previously used as a last-resort fallback. Now returns "" (no note).

    The format "Name — rating★ from N reviews." is rejected by the validator
    (name_rating_only_template) because it repeats only visible card fields.
    An absent note is better than a generic template.

    This function is retained for API compatibility but must not be called
    for visible output. The caller in _run_pipeline now uses "" directly.
    """
    return ""


def _trust_gate(cards: List[Any]) -> tuple:
    """Final trust validation: assert every card has place_id, OPERATIONAL, maps URI."""
    passed = []
    rejected = 0
    for card in cards:
        gv = getattr(card, "google_verification", None)
        if gv is None:
            logger.warning("semantic_retrieval_v1.trust_gate: rejected no_google_verification name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        if not getattr(gv, "provider_place_id", None):
            logger.warning("semantic_retrieval_v1.trust_gate: rejected missing_place_id name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        status = (getattr(gv, "business_status", None) or "").upper()
        if status and status != "OPERATIONAL":
            logger.warning("semantic_retrieval_v1.trust_gate: rejected non_operational name=%s status=%s",
                           getattr(card, "name", "?"), status)
            rejected += 1
            continue
        if not getattr(gv, "google_maps_uri", None):
            logger.warning("semantic_retrieval_v1.trust_gate: rejected missing_maps_uri name=%s",
                           getattr(card, "name", "?"))
            rejected += 1
            continue
        passed.append(card)
    return passed, rejected


def _assemble_card_set(
    cards_data: List[Any],
    card_reasons: Dict[str, Any],
    frame: Any,
    note_generation_timed_out: bool,
    set_writer_primary_active: bool,
) -> tuple:
    """Assemble the final ordered card list from ranked entities and note reasons.

    Extracted from Step 8 so it can be unit-tested independently.

    Rules:
    - Deadline-exceeded path: include all entities without a note block.
    - Set-writer primary path: include all entities; hide note block for any
      card whose set-writer note failed validation (validated=False).  Do NOT
      drop the card — "hide invalid notes, not valid cards."
    - LLM fallback path: exclude entities without a validated note so that
      unvalidated cards flow to the more-options pool instead.

    Returns:
        (cards, rank_debug, excluded_unvalidated, visible_note_count,
         cards_without_notes_count)
    """
    from app.concierge.batched_reason_builder import CardReason
    cards: List[Any] = []
    rank_debug: List[Dict[str, Any]] = []
    excluded_unvalidated = 0
    visible_note_count = 0
    cards_without_notes_count = 0
    for i, (entity, _evidence, rank_score, _det_reason) in enumerate(cards_data, 1):
        if note_generation_timed_out:
            # Include card; note is absent — frontend must not render note block.
            card = _entity_to_card(
                entity, "", frame,
                reason_source="timed_out",
                reason_validated=False,
            )
            cards_without_notes_count += 1
        else:
            cr = card_reasons.get(str(i), CardReason())
            if not cr.validated:
                if set_writer_primary_active:
                    # Card is Google-verified; set-writer note was hidden.
                    # Include the card without a note rather than dropping it.
                    card = _entity_to_card(
                        entity, "", frame,
                        reason_source="set_level_writer_v1",
                        reason_validated=False,
                    )
                    cards_without_notes_count += 1
                else:
                    excluded_unvalidated += 1
                    continue
            else:
                card = _entity_to_card(
                    entity, cr.note, frame,
                    reason_source=cr.source,
                    reason_validated=True,
                )
                if card is not None:
                    visible_note_count += 1
        if card is not None:
            cards.append(card)
            rank_debug.append({
                "name": entity.name,
                "score": rank_score.as_dict(),
            })
    return cards, rank_debug, excluded_unvalidated, visible_note_count, cards_without_notes_count


def _entity_to_card(
    entity: "PlaceEntity",  # type: ignore[name-defined]
    reason: str,
    frame: "ExperienceFrame",  # type: ignore[name-defined]
    reason_source: str = "deterministic_safe_v1",
    reason_validated: bool = False,
) -> Optional[Any]:
    """Convert a verified PlaceEntity to a UnifiedRestaurantResult card."""
    try:
        from app.models.concierge import (
            ConciergeDisplayFields,
            GoogleVerification,
            PlaceSupportingDetails,
            UnifiedRestaurantResult,
        )

        # Derive display category from types + frame concept
        primary_concept = frame.subtype_concepts[0].label if frame.subtype_concepts else ""
        display_category = _derive_display_category(entity.types, entity.primary_type, primary_concept)

        # Preserve Google native rating scale (0–5) for display.
        rating_display = float(entity.rating) if entity.rating is not None else None
        meta_line: Optional[str] = None
        if rating_display is not None and entity.user_rating_count:
            meta_line = f"★ {rating_display:.1f} ({entity.user_rating_count:,} reviews)"
        elif rating_display is not None:
            meta_line = f"★ {rating_display:.1f}"

        gv = GoogleVerification(
            provider="google_places",
            provider_place_id=entity.place_id,
            name=entity.name,
            formatted_address=entity.formatted_address,
            lat=entity.lat,
            lng=entity.lng,
            business_status=entity.business_status,
            google_maps_uri=entity.google_maps_uri,
            website_uri=entity.website_uri,
            rating=entity.rating,
            user_rating_count=entity.user_rating_count,
            types=entity.types,
            confidence="high",
            score=1.0,
        )

        fallback_map = (
            f"https://maps.google.com/?q="
            f"{entity.name.replace(' ', '+')}+"
            f"{frame.destination.replace(' ', '+')}"
        )

        return UnifiedRestaurantResult(
            name=entity.name,
            source="Google Places",
            cuisine=display_category,
            neighborhood=entity.formatted_address,
            rating=rating_display,
            review_count=entity.user_rating_count,
            summary=reason,
            primary_reason=reason,
            reason_source=reason_source,
            why_pick=reason,
            verified_place=True,
            google_verification=gv,
            supporting_details=PlaceSupportingDetails(
                why_pick=reason,
                meta_line=meta_line,
                address=entity.formatted_address,
                category_label=display_category,
            ),
            display=ConciergeDisplayFields(
                display_name=entity.name,
                display_category=display_category,
                display_meta_line=meta_line,
                display_why=reason,
                display_badges=[],
                addability="addable",
                display_why_source=reason_source,
                display_why_validated=reason_validated,
            ),
            maps_link=entity.google_maps_uri or fallback_map,
            booking_link=entity.website_uri,
            tags=[],
        )
    except Exception as exc:
        logger.warning("semantic_retrieval_v1: card_build_failed name=%s error=%s", entity.name, exc)
        return None


def _derive_display_category(
    types: List[str],
    primary_type: Optional[str],
    concept_label: str,
) -> str:
    """Derive a user-facing category label from Google types and extracted concept."""
    _TYPE_LABELS = {
        "brewery": "Brewery / Taproom",
        "bar": "Bar",
        "cocktail_bar": "Cocktail Bar",
        "wine_bar": "Wine Bar",
        "night_club": "Nightclub",
        "restaurant": "Restaurant",
        "cafe": "Café",
        "coffee_shop": "Coffee Shop",
        "bakery": "Bakery",
        "sushi_restaurant": "Sushi Restaurant",
        "japanese_restaurant": "Japanese Restaurant",
        "ramen_restaurant": "Ramen Restaurant",
        "spanish_restaurant": "Spanish Restaurant",
        "mexican_restaurant": "Mexican Restaurant",
        "italian_restaurant": "Italian Restaurant",
        "french_restaurant": "French Restaurant",
        "chinese_restaurant": "Chinese Restaurant",
        "thai_restaurant": "Thai Restaurant",
        "indian_restaurant": "Indian Restaurant",
        "korean_restaurant": "Korean Restaurant",
        "vietnamese_restaurant": "Vietnamese Restaurant",
        "mediterranean_restaurant": "Mediterranean Restaurant",
        "greek_restaurant": "Greek Restaurant",
        "steak_house": "Steakhouse",
        "seafood_restaurant": "Seafood Restaurant",
        "pizza_restaurant": "Pizza Restaurant",
        "brunch_restaurant": "Brunch Spot",
        "breakfast_restaurant": "Breakfast Spot",
        "american_restaurant": "American Restaurant",
    }

    # First try primary_type
    if primary_type:
        label = _TYPE_LABELS.get((primary_type or "").lower())
        if label:
            return label

    # Then try types list
    for t in (types or []):
        label = _TYPE_LABELS.get((t or "").lower())
        if label:
            return label

    # Fall back to concept label if meaningful
    if concept_label and len(concept_label) >= 3:
        # Capitalise and add a suffix
        c = concept_label.strip().title()
        # If it's a drink-type concept (brewery, bar, etc.)
        drink_concepts = {"brewery", "taproom", "brewpub", "bar", "pub", "winery", "distillery"}
        if concept_label.lower() in drink_concepts:
            return c
        return f"{c} Restaurant"

    return "Restaurant"


def _log_per_card_notes(
    user_query: str,
    cards_data: List[Any],
    card_reasons: Dict[str, Any],
    frame: Any,
) -> None:
    """Emit one structured log line per card with exact visible note and evidence quality.

    Log key: semantic_retrieval_v1.per_card_notes
    Fields per card:
      - card_index (1-based)
      - card_name
      - evidence_adequacy (STRONG/OK/THIN)
      - modifier_status (confirmed/not_confirmed/none)
      - display_why_validated (bool)
      - display_why_source (str)
      - visible_note (first 220 chars of the accepted note, or "" if omitted)
    """
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    geo_hints = getattr(frame, "geography_hints", []) or []
    # Use location_modifiers first; fall back to geography_hints (e.g. "river" from geo)
    primary_modifier = location_modifiers[0] if location_modifiers else (geo_hints[0] if geo_hints else "")

    # Generic modifier evidence term sets — used ONLY for telemetry/observability.
    # These are NOT retrieval eligibility gates, candidate inclusion filters, or ranking
    # signals. They simply expand the listing-context check for known geographic/setting
    # synonym clusters so per-card modifier_status telemetry is accurate.
    # New clusters can be added here without touching retrieval, routing, or ranking.
    _WATER_GEO_MODIFIER_TERMS = frozenset({
        "river", "riverwalk", "riverfront", "riverbank", "riverside",
        "waterfront", "lakefront", "waterside",
    })
    _SCENIC_VIEW_MODIFIER_TERMS = frozenset({
        "view", "rooftop", "panoramic", "scenic", "terrace", "overlook",
    })
    _GARDEN_MODIFIER_TERMS = frozenset({
        "garden", "courtyard", "patio", "terrace", "outdoor",
    })
    mod_lower = primary_modifier.lower()
    # Map modifier → synonym cluster for listing-context evidence check.
    # This is a generic pattern: modifier → related terms that might appear in
    # the venue's verified listing name or address.
    if any(r in mod_lower for r in ("river", "waterfront", "riverwalk", "waterside")):
        _geo_check_terms = _WATER_GEO_MODIFIER_TERMS
    elif any(r in mod_lower for r in ("view", "scenic", "rooftop", "panoramic", "overlook")):
        _geo_check_terms = _SCENIC_VIEW_MODIFIER_TERMS
    elif any(r in mod_lower for r in ("garden", "courtyard", "terrace", "patio")):
        _geo_check_terms = _GARDEN_MODIFIER_TERMS
    else:
        # For any other modifier, do a simple word-token match against the modifier itself
        _geo_check_terms = frozenset(w for w in mod_lower.split() if len(w) >= 3)

    per_card_entries = []
    for i, (entity, evidence, _rank_score, _det_reason) in enumerate(cards_data, 1):
        cr = card_reasons.get(str(i))
        if cr is None:
            continue

        # Modifier status for this card — distinguishes listing-context from unknown
        modifier_status = "none"
        if primary_modifier:
            # Check structured_facts first (explicit location_modifier_confirmed)
            loc_confirmed = any(
                "confirms" in f and primary_modifier.lower() in f.lower()
                for f in (evidence.structured_facts or [])
            )
            loc_not_confirmed = any(
                f.startswith(f"location_modifier_not_confirmed:{primary_modifier}")
                for f in (evidence.uncertainty_flags or [])
            )
            if loc_confirmed:
                modifier_status = "confirmed"
            elif loc_not_confirmed:
                modifier_status = "not_confirmed"
            elif _geo_check_terms:
                # For geo hints (river, view, etc.), check entity name/address
                name_lower = (getattr(entity, "name", "") or "").lower()
                addr_lower = (getattr(entity, "formatted_address", "") or "").lower()
                if any(term in name_lower for term in _geo_check_terms):
                    modifier_status = "confirmed_listing_context"
                elif any(term in addr_lower for term in _geo_check_terms):
                    modifier_status = "confirmed_address_context"
                else:
                    modifier_status = "unknown"
            else:
                modifier_status = "unknown"

        per_card_entries.append({
            "i": i,
            "name": entity.name,
            "adequacy": getattr(evidence, "evidence_adequacy", "THIN"),
            "modifier_status": modifier_status,
            "validated": cr.validated,
            "source": cr.source,
            "note": cr.note[:220] if cr.note else "",
        })

    logger.info(
        "semantic_retrieval_v1.per_card_notes "
        "query=%r cards=%r",
        user_query,
        per_card_entries,
    )


def _log_semantic_turn(
    *,
    user_query: str,
    frame: Any,
    queries: List[str],
    latency: Dict[str, int],
    provider_call_count: int,
    provider_success_count: int,
    raw_candidate_count: int,
    deduped_candidate_count: int,
    verified_entity_count: int,
    rejection_stats: Dict[str, Any],
    final_card_count: int,
    t_pipeline_start: float,
    outcome: str,
    rank_top3: Optional[List[Dict]] = None,
    reason_source: str = "deterministic_safe_v1",
    top_card_name: str = "",
    top_card_city: str = "",
    # SLA telemetry (v2 amendment §12)
    target_response_ms: int = DEFAULT_SLA.target_ms,
    soft_ceiling_ms: int = DEFAULT_SLA.soft_ceiling_ms,
    hard_cutoff_ms: int = DEFAULT_SLA.hard_cutoff_ms,
    first_return_card_limit: int = DEFAULT_SLA.first_card_limit,
    pre_cap_card_count: int = 0,
    visible_note_count: int = 0,
    hidden_note_count: int = 0,
    fallback_note_visible_count: int = 0,  # must always be 0
    note_generation_timed_out: bool = False,
    cards_without_notes: int = 0,
    more_options_cursor_present: bool = False,
    # PR #258 parallel retrieval telemetry
    critical_path_ms: int = 0,
    non_critical_enrichment_ms: int = 0,
    provider_fanout_ms: int = 0,
    provider_timeout_counts: int = 0,
    provider_skipped_due_to_budget_counts: int = 0,
    google_critical_success: bool = True,
    google_critical_candidate_count: int = 0,
    google_verified_count: int = 0,
    non_critical_enrichment_used_count: int = 0,
    non_critical_enrichment_skipped_count: int = 0,
    remaining_budget_before_reasoning_ms: int = 0,
    # PR #259 evidence dossier telemetry
    dossier_telemetry: Optional[Any] = None,  # Optional[EvidenceDossierTelemetry]
    # PR #260 curator telemetry
    curator_telemetry: Optional[Dict[str, Any]] = None,
    # PR #261 set-level writer telemetry
    set_writer_telemetry: Optional[Dict[str, Any]] = None,
    # PR this: semantic frame finalization telemetry
    frame_finalization_telemetry: Optional[Dict[str, Any]] = None,
) -> None:
    """Log one structured semantic turn line for zero-card failure debugging."""
    total_ms = int((time.monotonic() - t_pipeline_start) * 1000)
    concepts_summary = (
        [(c.label, round(c.confidence, 2)) for c in frame.subtype_concepts]
        if hasattr(frame, "subtype_concepts") else []
    )
    venue_concept = (
        frame.subtype_concepts[0].label
        if getattr(frame, "subtype_concepts", None)
        else ""
    )
    logger.info(
        "semantic_retrieval_v1.turn "
        "pipeline_version=%s "
        "flag=on "
        "turn_mode=new_search "
        "query=%r "
        "destination=%r "
        "open_class_place_detected=%s "
        "venue_concept=%r "
        "concepts=%r "
        "geo_hints=%r "
        "location_modifiers=%r "
        "soft_preferences=%r "
        "negative_constraints=%r "
        "use_cases=%r "
        "value_signals=%r "
        "ambiguity_flags=%r "
        "retrieval_queries=%r "
        "provider_calls=%d "
        "provider_success=%d "
        "raw_candidates=%d "
        "deduped_candidates=%d "
        "verified_entities=%d "
        "rejection_stats=%r "
        "final_card_count=%d "
        "reason_source=%s "
        "grounded_reason_attempted=%s "
        "grounded_reason_success=%s "
        "destination_penalized=%d "
        "det_reason_rejected=%d "
        "top_card_name=%r "
        "top_card_city=%r "
        "latency_by_stage=%r "
        "total_ms=%d "
        "rank_top3=%r "
        "outcome=%s "
        "turn_total_ms=%d "
        "target_response_ms=%d "
        "soft_ceiling_ms=%d "
        "hard_cutoff_ms=%d "
        "first_return_card_limit=%d "
        "pre_cap_card_count=%d "
        "visible_note_count=%d "
        "hidden_note_count=%d "
        "fallback_note_visible_count=%d "
        "note_generation_timed_out=%s "
        "cards_without_notes=%d "
        "more_options_cursor_present=%s "
        "critical_path_ms=%d "
        "non_critical_enrichment_ms=%d "
        "provider_fanout_ms=%d "
        "provider_timeout_counts=%d "
        "provider_skipped_due_to_budget_counts=%d "
        "google_critical_success=%s "
        "google_critical_candidate_count=%d "
        "google_verified_count=%d "
        "non_critical_enrichment_used_count=%d "
        "non_critical_enrichment_skipped_count=%d "
        "remaining_budget_before_reasoning_ms=%d",
        PIPELINE_VERSION,
        user_query,
        getattr(frame, "destination", ""),
        getattr(frame, "open_class_place_detected", False),
        venue_concept,
        concepts_summary,
        getattr(frame, "geography_hints", []),
        getattr(frame, "location_modifiers", []),
        getattr(frame, "soft_preferences", []),
        getattr(frame, "negative_constraints", []),
        getattr(frame, "use_cases", []),
        getattr(frame, "value_signals", []),
        getattr(frame, "ambiguity_flags", []),
        queries,
        provider_call_count,
        provider_success_count,
        raw_candidate_count,
        deduped_candidate_count,
        verified_entity_count,
        rejection_stats,
        final_card_count,
        reason_source,
        rejection_stats.get("grounded_reason_attempted", False),
        rejection_stats.get("grounded_reason_success", False),
        rejection_stats.get("destination_penalized_count", 0),
        rejection_stats.get("det_reason_rejected_count", 0),
        top_card_name,
        top_card_city,
        latency,
        total_ms,
        rank_top3 or [],
        outcome,
        # SLA telemetry — appended last for backwards-compatible log parsing
        total_ms,
        target_response_ms,
        soft_ceiling_ms,
        hard_cutoff_ms,
        first_return_card_limit,
        pre_cap_card_count,
        visible_note_count,
        hidden_note_count,
        fallback_note_visible_count,
        note_generation_timed_out,
        cards_without_notes,
        more_options_cursor_present,
        # PR #258 parallel retrieval telemetry values
        critical_path_ms,
        non_critical_enrichment_ms,
        provider_fanout_ms,
        provider_timeout_counts,
        provider_skipped_due_to_budget_counts,
        google_critical_success,
        google_critical_candidate_count,
        google_verified_count,
        non_critical_enrichment_used_count,
        non_critical_enrichment_skipped_count,
        remaining_budget_before_reasoning_ms,
    )
    # PR #259 dossier telemetry — separate log line to preserve turn-line parsers.
    if dossier_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.dossier_telemetry %r",
            dossier_telemetry.as_log_dict(),
        )
    # PR #260 curator telemetry — separate log line.
    if curator_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.curated_set_telemetry %r",
            curator_telemetry,
        )
    # PR #261 set-level writer telemetry — separate log line.
    if set_writer_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.set_writer_telemetry %r",
            set_writer_telemetry,
        )
    # PR this: frame finalization telemetry — separate log line (backend-only).
    if frame_finalization_telemetry is not None:
        logger.info(
            "semantic_retrieval_v1.frame_finalization_telemetry %r",
            frame_finalization_telemetry,
        )
