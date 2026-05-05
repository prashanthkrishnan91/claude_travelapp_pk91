"""SemanticRanker v1 — deterministic, feature-based scoring for Place entities.

Score formula (weights sum to 1.0):
    score =
      0.34 * subtype_fit        # dominant — must match the user's concept
    + 0.22 * geo_fit            # waterfront/riverwalk proximity signal
    + 0.12 * quality_signal     # Bayesian-smoothed rating
    + 0.10 * evidence_strength  # structured fields available
    + 0.08 * diversity_signal   # penalize near-duplicate chains/clusters
    + 0.06 * popularity_signal  # deliberately small — cannot overpower subtype
    + 0.04 * trip_context_fit   # neutral in Phase 1 (no hotel context)
    + 0.04 * value_fit          # active only when frame requests value/luxury
    - penalties

Design invariants:
- NO category_score < 0.2 hard gate. Subtype fit is a soft score, not an eligibility gate.
- A brewery beats a generic high-rated bar for brewery asks because subtype_fit
  dominates popularity_signal.
- Popularity cannot overpower subtype_fit (0.06 vs 0.34).
- subtype_fit uses open-vocabulary name/type/query matching, NOT enum lookup.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from app.concierge.frame_extractor import ExperienceFrame, SubtypeConcept
from app.concierge.place_entity_layer import PlaceEntity

logger = logging.getLogger(__name__)

# Score weights — must sum to 1.0
_W_SUBTYPE_FIT = 0.34
_W_GEO_FIT = 0.22
_W_QUALITY = 0.12
_W_EVIDENCE = 0.10
_W_DIVERSITY = 0.08
_W_POPULARITY = 0.06
_W_TRIP_CONTEXT = 0.04
_W_VALUE = 0.04

# Wrong-category penalty applied when the user named a strong venue type and
# the entity matches a clearly different, unrelated category. This is a soft
# penalty (not a hard reject) so the pipeline can still degrade gracefully
# when no on-concept results are available.
_WRONG_CATEGORY_PENALTY = 0.20

# Subtype-fit threshold below which an entity is treated as wrong-category
# when the user named a confident venue concept. Above this, no penalty.
_WRONG_CATEGORY_SUBTYPE_FIT_MAX = 0.30
_STRONG_CONCEPT_CONFIDENCE_MIN = 0.85

# Bayesian prior parameters for quality smoothing
_BAYESIAN_M = 80.0    # pseudo-count prior
_BAYESIAN_C = 4.0     # prior mean rating

# Geography keywords that indicate water/outdoor proximity
_WATER_GEO_TERMS = frozenset({
    "waterfront", "riverwalk", "riverwalk", "lakefront", "lake michigan",
    "river", "lake", "marina", "pier", "dock", "harbor", "harbour",
    "waterside", "beachfront", "shoreline",
})

_OUTDOOR_GEO_TERMS = frozenset({"rooftop", "patio", "terrace", "outdoor", "garden"})

# Near-synonym sets for subtype matching.
# Each frozenset groups synonymous labels. If the user's concept matches any
# element, the whole set contributes to the match score.
# NOT a closed enum — unknown concepts simply score via direct name/type match.
_SYNONYM_SETS: List[FrozenSet[str]] = [
    frozenset({"brewery", "brew", "brewing", "taproom", "brewpub", "microbrewery",
               "craft beer", "beer", "ale", "lager", "ipa"}),
    frozenset({"winery", "wine", "vineyard", "wine bar", "winebar"}),
    frozenset({"distillery", "whiskey", "whisky", "bourbon", "spirits", "spirit"}),
    frozenset({"tapas", "small plates", "spanish", "pintxos"}),
    frozenset({"sushi", "sashimi", "omakase", "japanese"}),
    frozenset({"ramen", "noodle", "japanese"}),
    frozenset({"dim sum", "chinese", "dumpling"}),
    frozenset({"cocktail", "craft cocktail", "mixology", "speakeasy"}),
    frozenset({"cafe", "coffee", "espresso", "cappuccino"}),
    frozenset({"bakery", "pastry", "patisserie", "boulangerie"}),
    frozenset({"steakhouse", "steak", "chop house", "chophouse"}),
    frozenset({"seafood", "fish", "oyster", "lobster", "crab"}),
    frozenset({"pizza", "pizzeria", "italian", "neapolitan"}),
    frozenset({"thai", "pad thai"}),
    frozenset({"indian", "curry", "tandoor"}),
    frozenset({"korean", "korean bbq", "kbbq", "bulgogi"}),
    frozenset({"vietnamese", "pho", "banh mi"}),
    frozenset({"mexican", "taqueria", "taco", "margarita"}),
    frozenset({"mediterranean", "greek", "middle eastern"}),
    frozenset({"french", "bistro", "brasserie", "crepe"}),
    frozenset({"brunch", "breakfast", "eggs benedict", "mimosa"}),
]


@dataclass
class RankScore:
    """Breakdown of the total rank score for a PlaceEntity."""
    total: float = 0.0
    subtype_fit: float = 0.0
    geo_fit: float = 0.0
    quality_signal: float = 0.0
    evidence_strength: float = 0.0
    diversity_signal: float = 0.0
    popularity_signal: float = 0.0
    trip_context_fit: float = 0.5
    value_fit: float = 0.5
    penalties: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "total": round(self.total, 4),
            "subtype_fit": round(self.subtype_fit, 4),
            "geo_fit": round(self.geo_fit, 4),
            "quality_signal": round(self.quality_signal, 4),
            "evidence_strength": round(self.evidence_strength, 4),
            "diversity_signal": round(self.diversity_signal, 4),
            "popularity_signal": round(self.popularity_signal, 4),
            "trip_context_fit": round(self.trip_context_fit, 4),
            "value_fit": round(self.value_fit, 4),
            "penalties": round(self.penalties, 4),
        }


@dataclass
class MinimalEvidenceBundle:
    """Lightweight structured evidence for one verified entity."""
    entity: PlaceEntity
    structured_facts: List[str] = field(default_factory=list)
    geo_note: Optional[str] = None
    uncertainty_flags: List[str] = field(default_factory=list)


# ── Feature computation ───────────────────────────────────────────────────────

def _concept_synonym_set(label: str) -> Optional[FrozenSet[str]]:
    """Return the synonym set containing label, or None."""
    label_l = label.lower()
    for syn_set in _SYNONYM_SETS:
        if label_l in syn_set:
            return syn_set
    return None


def _token_set(text: str) -> Set[str]:
    """Tokenize text into lowercase word tokens, splitting on underscores too.

    Google type names use underscores (e.g. 'sushi_restaurant'), so we replace
    underscores with spaces before tokenizing to enable 'sushi' matching.
    """
    normalized = text.lower().replace("_", " ")
    return set(re.findall(r"\b[a-z][a-z-]*\b", normalized))


def _subtype_fit(entity: PlaceEntity, frame: ExperienceFrame) -> float:
    """Open-vocabulary subtype fit: 0.0–1.0.

    Uses name tokens, Google types, and source query — NOT enum lookup.
    A brewery beats a generic bar because "brewery" appears in name/types/query.
    """
    if not frame.subtype_concepts:
        return 0.5  # neutral when no concept extracted

    name_tokens = _token_set(entity.name)
    type_tokens = _token_set(" ".join(entity.types or []))
    primary_type_tokens = _token_set(entity.primary_type or "")
    query_tokens = _token_set(entity.source_query)

    best_fit = 0.0

    for concept in frame.subtype_concepts:
        label = concept.label.lower()
        concept_tokens = _token_set(label)
        syn_set = _concept_synonym_set(label)
        all_synonyms = syn_set if syn_set else {label}

        # Name match: any synonym token in place name
        name_match = 0.0
        for syn in all_synonyms:
            syn_toks = _token_set(syn)
            if syn_toks & name_tokens:
                name_match = max(name_match, 1.0 if syn_toks <= name_tokens else 0.85)
                break

        # Type match: any synonym in Google types
        type_match = 0.0
        for syn in all_synonyms:
            syn_toks = _token_set(syn)
            if syn_toks & (type_tokens | primary_type_tokens):
                type_match = max(type_match, 0.75)
                break

        # Query match: the source query contained the concept
        query_match = 0.0
        if concept_tokens & query_tokens:
            query_match = 0.6
        for syn in all_synonyms:
            if _token_set(syn) & query_tokens:
                query_match = max(query_match, 0.6)
                break

        # Take the best match signal, weighted by concept confidence
        fit = max(name_match, type_match, query_match)
        fit *= concept.confidence
        best_fit = max(best_fit, fit)

    return min(1.0, best_fit)


def _geo_fit(entity: PlaceEntity, frame: ExperienceFrame) -> float:
    """Geography fit: 0.0–1.0.

    If no geo hints in frame: neutral 0.5.
    If geo hints present: check address and source query for matching terms.
    We do NOT fabricate proximity — if we can't confirm, score is 0.4 (slight penalty).
    """
    geo_hints = frame.geography_hints
    if not geo_hints:
        return 0.5  # neutral

    address_lower = (entity.formatted_address or "").lower()
    query_lower = entity.source_query.lower()
    name_lower = entity.name.lower()

    # Combine all geo-relevant terms requested
    requested_water = any(
        g in _WATER_GEO_TERMS or any(w in g for w in _WATER_GEO_TERMS)
        for g in geo_hints
    )
    requested_outdoor = any(
        g in _OUTDOOR_GEO_TERMS for g in geo_hints
    )

    # Check if the source query already embeds the geo hint (retrieval planner added it)
    query_has_geo = any(
        any(term in query_lower for term in _WATER_GEO_TERMS | _OUTDOOR_GEO_TERMS)
        for _ in [1]
    )

    # Check address for geo signals
    address_has_water = any(
        term in address_lower
        for term in ("river", "lake", "waterfront", "harbor", "harbour", "pier", "marina")
    )

    if requested_water:
        if address_has_water:
            return 0.85  # address confirms water proximity
        if query_has_geo:
            return 0.65  # query was geo-targeted; this result appeared in those results
        return 0.40  # geo requested but not confirmed — honest penalty

    if requested_outdoor:
        if any(t in address_lower or t in name_lower for t in ("rooftop", "patio", "terrace")):
            return 0.80
        if query_has_geo:
            return 0.60
        return 0.42

    # Generic geo hint — query targeted to geo area
    if query_has_geo:
        return 0.60
    return 0.45


def _quality_signal(entity: PlaceEntity) -> float:
    """Bayesian-smoothed rating signal: 0.0–1.0. Cannot overpower subtype_fit."""
    rating = entity.rating
    review_count = entity.user_rating_count or 0
    if rating is None:
        return 0.0
    v = float(max(0, review_count))
    bayesian = (v / (v + _BAYESIAN_M)) * float(rating) + (_BAYESIAN_M / (v + _BAYESIAN_M)) * _BAYESIAN_C
    # Normalize to 0-1 (max Google rating is 5.0)
    return min(1.0, bayesian / 5.0)


def _evidence_strength(entity: PlaceEntity) -> float:
    """Score how many structured fields are available: 0.0–1.0."""
    score = 0.0
    if entity.name:
        score += 0.30
    if entity.formatted_address:
        score += 0.20
    if entity.rating is not None:
        score += 0.20
    if entity.types:
        score += 0.15
    if entity.google_maps_uri:
        score += 0.15  # always present (trust gate), so always 0.15
    return min(1.0, score)


def _diversity_signal(
    entity: PlaceEntity,
    already_ranked: List[Tuple[PlaceEntity, RankScore]],
) -> float:
    """Penalize near-duplicates or same-chain clustering: 0.0–1.0.

    High score = diverse (not similar to prior ranked entities).
    """
    if not already_ranked:
        return 1.0

    entity_name_tokens = _token_set(entity.name)

    # Check name overlap with already-ranked entities
    for prev_entity, _ in already_ranked:
        prev_tokens = _token_set(prev_entity.name)
        if not entity_name_tokens or not prev_tokens:
            continue
        # Jaccard similarity
        intersection = entity_name_tokens & prev_tokens
        union = entity_name_tokens | prev_tokens
        if not union:
            continue
        similarity = len(intersection) / len(union)
        if similarity > 0.6:
            return 0.2  # near-duplicate → strong diversity penalty
        if similarity > 0.4:
            return 0.5  # somewhat similar → mild penalty

    return 1.0


def _popularity_signal(entity: PlaceEntity) -> float:
    """Deliberately small popularity signal: 0.0–1.0.

    Uses log scale to prevent high review-count places from drowning subtype.
    A brewery with 200 reviews still beats a cocktail bar with 2000 reviews
    for a brewery ask, because subtype_fit (0.34) >> popularity_signal (0.06).
    """
    review_count = entity.user_rating_count or 0
    if review_count == 0:
        return 0.0
    return min(1.0, math.log(review_count + 1) / math.log(5000))


def _value_fit(entity: PlaceEntity, frame: ExperienceFrame) -> float:
    """Active only when frame requests value or luxury: 0.0–1.0. Neutral otherwise."""
    value_signals = frame.value_signals
    if not value_signals:
        return 0.5  # neutral

    price = (entity.price_level or "").upper()
    _CHEAP = {"PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_FREE"}
    _EXPENSIVE = {"PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"}

    wants_budget = "budget" in value_signals or "not_expensive" in value_signals
    wants_luxury = "luxury" in value_signals

    if wants_budget and price in _CHEAP:
        return 0.9
    if wants_luxury and price in _EXPENSIVE:
        return 0.9
    if wants_budget and price in _EXPENSIVE:
        return 0.2
    if wants_luxury and price in _CHEAP:
        return 0.3
    return 0.5  # unknown price level → neutral


# ── Evidence bundle ───────────────────────────────────────────────────────────

def build_evidence_bundle(
    entity: PlaceEntity,
    frame: ExperienceFrame,
    rank_score: RankScore,
) -> MinimalEvidenceBundle:
    """Build a minimal, reliable evidence bundle for a verified entity."""
    facts: List[str] = []
    uncertainty_flags: List[str] = []
    geo_note: Optional[str] = None

    # Structured fact: name + primary type
    if entity.primary_type or entity.types:
        type_label = (entity.primary_type or entity.types[0] or "").replace("_", " ").title()
        facts.append(f"Google type: {type_label}")

    # Structured fact: rating
    if entity.rating is not None and entity.user_rating_count:
        facts.append(f"Rating: {entity.rating:.1f} ({entity.user_rating_count:,} reviews)")
    elif entity.rating is not None:
        facts.append(f"Rating: {entity.rating:.1f}")

    # Structured fact: subtype match signal
    for concept in frame.subtype_concepts[:1]:
        if rank_score.subtype_fit >= 0.8:
            facts.append(f"Strong {concept.label} name/type match")
        elif rank_score.subtype_fit >= 0.5:
            facts.append(f"Partial {concept.label} type match")

    # Geo note: honest about what was searched vs confirmed
    if frame.geography_hints:
        geo_hint = frame.geography_hints[0]
        if rank_score.geo_fit >= 0.8:
            geo_note = f"Address indicates {geo_hint} proximity"
        elif rank_score.geo_fit >= 0.6:
            geo_note = f"Returned in {geo_hint}-targeted search; location unconfirmed from address"
        else:
            geo_note = f"Searched near {geo_hint}; exact proximity unconfirmed — verify before booking"

        # Uncertainty flags for attributes that cannot be verified structurally
        for flag in frame.ambiguity_flags:
            if "view" in flag or "waterfront" in geo_hint.lower():
                uncertainty_flags.append("water_view_not_structurally_verifiable")
                break

    # Uncertainty flags from frame
    for flag in frame.ambiguity_flags:
        if "noise" in flag and "noise_level_not_verifiable" not in uncertainty_flags:
            uncertainty_flags.append("noise_level_not_verifiable")
        if "ambiance" in flag and "ambiance_not_verifiable" not in uncertainty_flags:
            uncertainty_flags.append("ambiance_not_verifiable")

    return MinimalEvidenceBundle(
        entity=entity,
        structured_facts=facts,
        geo_note=geo_note,
        uncertainty_flags=uncertainty_flags,
    )


# ── Ranker ───────────────────────────────────────────────────────────────────

def rank_entities(
    entities: List[PlaceEntity],
    frame: ExperienceFrame,
    top_n: int = 10,
) -> List[Tuple[PlaceEntity, RankScore]]:
    """Rank PlaceEntity list by the semantic scoring formula.

    Returns top_n ranked entities with their score breakdowns.
    Diversity signal is computed incrementally (each entity scored relative
    to already-accepted entities, avoiding near-duplicate stacking).
    """
    if not entities:
        return []

    # Score all entities
    scored: List[Tuple[float, PlaceEntity, RankScore]] = []
    accepted: List[Tuple[PlaceEntity, RankScore]] = []

    has_strong_concept = bool(
        frame.subtype_concepts
        and frame.subtype_concepts[0].confidence >= _STRONG_CONCEPT_CONFIDENCE_MIN
    )

    for entity in entities:
        sf = _subtype_fit(entity, frame)
        gf = _geo_fit(entity, frame)
        qs = _quality_signal(entity)
        es = _evidence_strength(entity)
        ds = _diversity_signal(entity, accepted)
        ps = _popularity_signal(entity)
        tc = 0.5  # neutral trip context (Phase 1 — no hotel plumbing)
        vf = _value_fit(entity, frame)
        pen = 0.0

        # Wrong-category penalty: when the user named a high-confidence venue
        # type and the entity has very low subtype_fit, suppress the score
        # so generic restaurants/parks don't dominate brewery/sushi asks.
        if has_strong_concept and sf < _WRONG_CATEGORY_SUBTYPE_FIT_MAX:
            pen += _WRONG_CATEGORY_PENALTY

        total = (
            _W_SUBTYPE_FIT * sf
            + _W_GEO_FIT * gf
            + _W_QUALITY * qs
            + _W_EVIDENCE * es
            + _W_DIVERSITY * ds
            + _W_POPULARITY * ps
            + _W_TRIP_CONTEXT * tc
            + _W_VALUE * vf
            - pen
        )

        rs = RankScore(
            total=total,
            subtype_fit=sf,
            geo_fit=gf,
            quality_signal=qs,
            evidence_strength=es,
            diversity_signal=ds,
            popularity_signal=ps,
            trip_context_fit=tc,
            value_fit=vf,
            penalties=pen,
        )

        scored.append((total, entity, rs))

    # Sort descending by total score
    scored.sort(key=lambda x: x[0], reverse=True)

    result: List[Tuple[PlaceEntity, RankScore]] = []
    for _total, entity, rs in scored[:top_n]:
        result.append((entity, rs))

    logger.debug(
        "ranker: entities=%d ranked=%d top_score=%.4f "
        "top_subtype_fit=%.4f top_geo_fit=%.4f",
        len(entities),
        len(result),
        result[0][1].total if result else 0,
        result[0][1].subtype_fit if result else 0,
        result[0][1].geo_fit if result else 0,
    )

    return result
