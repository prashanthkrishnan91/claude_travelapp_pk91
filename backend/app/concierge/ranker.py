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
# _W_PREFERENCE_FIT added (PR #266); _W_POPULARITY and _W_TRIP_CONTEXT and _W_VALUE
# reduced to keep the sum at 1.0.  Popularity deliberately reduced so raw review
# volume has less dominance, especially for hidden_gem preference queries.
_W_SUBTYPE_FIT = 0.34
_W_GEO_FIT = 0.22
_W_QUALITY = 0.12
_W_EVIDENCE = 0.10
_W_DIVERSITY = 0.08
_W_POPULARITY = 0.04   # reduced from 0.06 — raw review volume less dominant
_W_PREFERENCE_FIT = 0.06  # new — soft preference alignment
_W_TRIP_CONTEXT = 0.02   # reduced from 0.04 — neutral placeholder
_W_VALUE = 0.02          # reduced from 0.04 — still active when value signals present

# Wrong-category penalty applied when the user named a strong venue type and
# the entity matches a clearly different, unrelated category. This is a soft
# penalty (not a hard reject) so the pipeline can still degrade gracefully
# when no on-concept results are available.
_WRONG_CATEGORY_PENALTY = 0.30

# Destination mismatch penalty: applied when the entity's formatted_address
# contains no token from the destination city/destination words. This ensures
# that a Milwaukee brewery cannot rank above Chicago breweries for a Chicago
# request simply because it has higher ratings or review counts.
_DESTINATION_MISMATCH_PENALTY = 0.45

# State abbreviations and country codes to skip when parsing address segments
# for destination validation.
_ADDRESS_SKIP_TOKENS = frozenset({
    "usa", "us", "uk",
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
    "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
    "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
    "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
    "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy",
})

# Subtype-fit threshold below which an entity is treated as wrong-category
# when the user named a confident venue concept. Above this, no penalty.
_WRONG_CATEGORY_SUBTYPE_FIT_MAX = 0.30
_STRONG_CONCEPT_CONFIDENCE_MIN = 0.85

# On-concept threshold: at or above this subtype_fit, the entity is considered
# a real category match for the user's venue head. Below it, the entity is
# off-concept (only matched via weak signals like the source query echoing the
# concept token). Used by the post-rank wrong-category drop filter.
_ON_CONCEPT_SUBTYPE_FIT_MIN = 0.45

# Minimum number of on-concept candidates required before the post-rank filter
# drops off-concept entries entirely. With fewer than this, we keep some
# off-concept candidates so the response degrades gracefully instead of going
# empty for no good reason.
_MIN_ON_CONCEPT_FOR_HARD_DROP = 3

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
    frozenset({"izakaya", "izakayas"}),
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
    preference_fit: float = 0.5   # neutral when no soft preference active
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
            "preference_fit": round(self.preference_fit, 4),
            "trip_context_fit": round(self.trip_context_fit, 4),
            "value_fit": round(self.value_fit, 4),
            "penalties": round(self.penalties, 4),
        }


@dataclass
class MinimalEvidenceBundle:
    """Lightweight structured evidence for one verified entity.

    evidence_adequacy grades how much grounding is available for LLM reasoning:
      STRONG — at least one specific differentiator beyond name/type/address/rating
               (editorial summary, amenity flags, or strong name-concept + high review count)
      OK     — concept fit confirmed + useful location context (geo proximity or modifier)
      THIN   — only name/type/address/rating/review-count visible on card
      UNSAFE — evidence conflicts with requested modifier (e.g. address contradicts claim)

    enrichment_facts hold Place Details fields (editorial_summary, amenity flags,
    review_snippets) when available. Empty list when enrichment was not fetched.
    """
    entity: PlaceEntity
    structured_facts: List[str] = field(default_factory=list)
    geo_note: Optional[str] = None
    uncertainty_flags: List[str] = field(default_factory=list)
    evidence_adequacy: str = "THIN"           # STRONG | OK | THIN | UNSAFE
    enrichment_facts: List[str] = field(default_factory=list)  # from Place Details


@dataclass
class RankerStats:
    """Side-channel diagnostics from rank_entities for the venue-head filter."""
    total_input: int = 0
    on_concept_count: int = 0
    off_concept_dropped: int = 0
    primary_label: str = ""
    concept_is_recognized: bool = False
    has_strong_concept: bool = False
    destination_penalized_count: int = 0


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

        # Query match: the source query contained the concept.
        # Weak evidence — proves the planner targeted the concept, NOT that
        # this specific entity is on-concept. Kept BELOW the wrong-category
        # threshold so a brewery-targeted query returning a generic waterfront
        # restaurant cannot escape the wrong-category penalty by association.
        query_match = 0.0
        if concept_tokens & query_tokens:
            query_match = 0.20
        for syn in all_synonyms:
            if _token_set(syn) & query_tokens:
                query_match = max(query_match, 0.20)
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


def _preference_fit(entity: PlaceEntity, frame: ExperienceFrame) -> float:
    """Soft preference alignment score: 0.0–1.0.

    Active only when frame.normalized_soft_preferences is non-empty.
    Returns 0.5 (neutral) when no preference is active or the preference
    cannot be assessed without richer evidence.

    hidden_gem: prefers moderate-visibility (local-scale) places over mega-popular
        ones.  Does NOT penalise quality — a well-reviewed local restaurant still
        scores well.  Places with review counts suggesting national-brand scale
        receive a mild penalty; moderate-count local-scale places receive a bonus.

    romantic / intimate: boosts only when name contains explicit romantic
        vocabulary (cozy, date, intimate, romantic, candlelight).  Conservative
        without evidence so we do not overclaim.

    late_night: boosts only when the name contains explicit late-night indicators
        ("Late Night", "Midnight", "After Hours", "All Night", "24 Hour", "Open
        Late").  "2AM" in a business name does NOT trigger a boost — the task
        spec explicitly prohibits inferring hours from name tokens that happen to
        resemble a time.

    view_or_geo: geo_fit already carries the view/outdoor signal; this function
        returns neutral (0.5) so as not to double-count.

    Design invariants:
    - subtype_fit (weight 0.34) >> preference_fit (weight 0.06): preference can
      reorder within same-concept candidates but cannot override category trust.
    - Google operational/addable trust gate is upstream of ranking — this function
      only runs on already-verified entities.
    - No new LLM calls; no new provider calls.
    """
    normalized_prefs: List[str] = getattr(frame, "normalized_soft_preferences", []) or []
    if not normalized_prefs:
        return 0.5  # neutral — no active preference

    name_lower = entity.name.lower()
    score = 0.5

    # ── hidden_gem ────────────────────────────────────────────────────────────
    if "hidden_gem" in normalized_prefs:
        review_count = entity.user_rating_count or 0
        if review_count > 0:
            if review_count < 20:
                # Very few reviews → likely low evidence quality; slight penalty
                score += -0.05
            elif review_count <= 500:
                # Local-scale visibility — well-suited for hidden-gem preference
                score += 0.10
            elif review_count <= 2000:
                # Moderate visibility — acceptable
                score += 0.03
            else:
                # High review volume signals mass-popular place — mild penalty
                score += -0.05

    # ── romantic / intimate ───────────────────────────────────────────────────
    if "romantic" in normalized_prefs or "intimate" in normalized_prefs:
        romantic_terms = {"romantic", "intimate", "cozy", "date", "candlelight", "lovers"}
        if any(t in name_lower for t in romantic_terms):
            score += 0.08

    # ── late_night ────────────────────────────────────────────────────────────
    if "late_night" in normalized_prefs:
        # Only boost with EXPLICIT late-night indicators in the name.
        # "2AM" in a business name is intentionally excluded (per task spec —
        # inferring hours from a name token is unsupported without actual hours
        # evidence).
        explicit_late = {
            "late night", "midnight", "after hours", "all night",
            "24 hour", "24hr", "open late", "24-hour", "24 hours",
        }
        if any(t in name_lower for t in explicit_late):
            score += 0.08

    # ── view_or_geo ───────────────────────────────────────────────────────────
    # geo_fit already carries the view/outdoor evidence signal; no double-count.

    return max(0.0, min(1.0, score))


def _destination_penalty(entity: PlaceEntity, frame: ExperienceFrame) -> float:
    """Return a score penalty when the entity is confirmed not in the destination.

    Checks whether any token from the destination city appears in the entity's
    formatted_address. If the address exists but contains no destination token
    AND contains at least one other city-shaped segment (non-digit, non-state,
    len > 2), the entity is likely in a different city and gets a heavy penalty.

    This prevents a Milwaukee brewery from outranking Chicago breweries for a
    Chicago request simply because of higher ratings.

    Returns 0.0 (no penalty) when:
    - No destination is set
    - No formatted_address available
    - Destination token appears in the address (in-destination confirmed)
    - Address is too short to make a determination

    Returns _DESTINATION_MISMATCH_PENALTY when address confirms a different city.
    """
    dest = (frame.destination or "").lower().strip()
    if not dest:
        return 0.0

    address = (entity.formatted_address or "").lower()
    if not address:
        return 0.0

    dest_words = set(dest.split())

    # If any non-trivial destination word appears anywhere in the address → no penalty
    if any(word in address for word in dest_words if len(word) > 2):
        return 0.0

    # Destination not found. Check whether the address has a city-shaped segment
    # that is clearly a different city.
    parts = [p.strip().lower() for p in address.split(",")]
    has_other_city = False
    for part in parts:
        if not part:
            continue
        if any(c.isdigit() for c in part):
            continue  # street number or zip — skip
        if len(part) <= 2:
            continue  # state abbreviation
        if part in _ADDRESS_SKIP_TOKENS:
            continue
        # This segment looks like a city or neighborhood name.
        # If it contains any destination word, confirm in-destination.
        if any(word in part for word in dest_words if len(word) > 2):
            return 0.0
        has_other_city = True

    if has_other_city:
        return _DESTINATION_MISMATCH_PENALTY

    return 0.0


# ── Evidence bundle ───────────────────────────────────────────────────────────

def _location_modifier_confirmed(modifier: str, entity: PlaceEntity) -> bool:
    """Return True when the entity's address/name strongly indicates the modifier."""
    if not modifier:
        return False
    mod_tokens = set(re.findall(r"[a-z]+", modifier.lower()))
    if not mod_tokens:
        return False
    address_text = (entity.formatted_address or "").lower()
    name_text = entity.name.lower()
    # Remove very common words that add noise ("the", "of", "and")
    stop = {"the", "of", "and", "a", "an", "in", "on", "at", "by"}
    sig_tokens = mod_tokens - stop
    if not sig_tokens:
        return False
    # Confirmed if majority of significant modifier tokens appear in address
    hits = sum(1 for t in sig_tokens if t in address_text or t in name_text)
    return hits >= max(1, len(sig_tokens) // 2 + len(sig_tokens) % 2)


def build_evidence_bundle(
    entity: PlaceEntity,
    frame: ExperienceFrame,
    rank_score: RankScore,
    enrichment: "Optional[Any]" = None,  # Optional[PlaceDetailsResult] — avoids import cycle
) -> MinimalEvidenceBundle:
    """Build a reliable evidence bundle for a verified entity.

    Args:
        enrichment: Optional PlaceDetailsResult from the Place Details provider.
                    When provided, enrichment_facts are populated and evidence_adequacy
                    can upgrade from THIN to OK/STRONG.
    """
    facts: List[str] = []
    uncertainty_flags: List[str] = []
    geo_note: Optional[str] = None
    enrichment_facts: List[str] = []

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

    # Location modifier fit: explicit street/neighborhood the user named.
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    for modifier in location_modifiers[:1]:
        confirmed = _location_modifier_confirmed(modifier, entity)
        if confirmed:
            facts.append(f"Address confirms {modifier} area")
        else:
            uncertainty_flags.append(f"location_modifier_not_confirmed:{modifier}")

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

    # ── Place Details enrichment (EvidencePack v3) ────────────────────────────
    if enrichment is not None:
        editorial = getattr(enrichment, "editorial_summary", None)
        if editorial:
            enrichment_facts.append(f"Editorial summary: {editorial[:160]}")
        for snippet in (getattr(enrichment, "review_snippets", None) or [])[:2]:
            if snippet:
                enrichment_facts.append(f"Review mention: {snippet[:120]}")
        amenity_map = {
            "serves_beer": "serves beer",
            "outdoor_seating": "outdoor seating available",
            "live_music": "live music listed",
            "good_for_groups": "good for groups",
        }
        for attr, label in amenity_map.items():
            val = getattr(enrichment, attr, None)
            if val is True:
                enrichment_facts.append(f"Amenity confirmed: {label}")

    # ── Evidence adequacy grading ─────────────────────────────────────────────
    # STRONG: has at least one concrete differentiator beyond name/type/address/rating/reviews.
    #         Only enrichment_facts (editorial summary, amenity flags, review snippets)
    #         qualify — rating and review count alone NEVER make evidence STRONG.
    # OK    : concept fit confirmed (subtype_fit >= 0.6) or name/address contains a
    #         user-requested modifier term (listing-context match).
    # THIN  : only name/type/address/rating/review-count — nothing extra.
    # UNSAFE: not used here (conflicts handled by validator uncertainty_flags).
    adequacy = "THIN"
    has_location_context = bool(geo_note) or any(
        "confirms" in f for f in facts
    )

    # Check whether the entity name/address contains a user-requested modifier term.
    # This upgrades adequacy to OK (listing context) even without enrichment.
    name_addr_lower = (
        (entity.name or "").lower() + " " + (entity.formatted_address or "").lower()
    )
    modifier_in_name = any(
        mod_tok in name_addr_lower
        for modifier in (location_modifiers or []) + (frame.geography_hints or [])
        for mod_tok in re.findall(r"[a-z]+", modifier.lower())
        if len(mod_tok) > 3
    )

    if enrichment_facts:
        # Concrete differentiator available (editorial, amenity, review snippet)
        adequacy = "STRONG"
    elif rank_score.subtype_fit >= 0.6 and (has_location_context or modifier_in_name):
        adequacy = "OK"
    elif rank_score.subtype_fit >= 0.6:
        adequacy = "OK"

    return MinimalEvidenceBundle(
        entity=entity,
        structured_facts=facts,
        geo_note=geo_note,
        uncertainty_flags=uncertainty_flags,
        evidence_adequacy=adequacy,
        enrichment_facts=enrichment_facts,
    )


# ── Ranker ───────────────────────────────────────────────────────────────────

def _has_known_synonym_set(label: str) -> bool:
    """True when ``label`` belongs to a recognized venue-head synonym set.

    Used by the post-rank filter to decide whether an empty on-concept pool
    should yield zero cards (recognized concept like "brewery" or "tapas")
    versus keeping degraded off-concept results (truly open-vocabulary head
    like "izakaya" where we have no synonym set to confirm category fit).
    """
    return _concept_synonym_set(label.lower()) is not None


def rank_entities(
    entities: List[PlaceEntity],
    frame: ExperienceFrame,
    top_n: int = 10,
) -> List[Tuple[PlaceEntity, RankScore]]:
    """Rank PlaceEntity list by the semantic scoring formula.

    Returns top_n ranked entities with their score breakdowns.
    Diversity signal is computed incrementally (each entity scored relative
    to already-accepted entities, avoiding near-duplicate stacking).

    Venue-head-over-modifier contract:
    - When the user named a strong venue concept, modifier-only matches do
      not get to dominate the candidate pool. The wrong-category penalty
      pushes them down in score, and the post-rank filter drops them
      entirely when enough on-concept candidates are available, or when
      the venue concept is recognized but no on-concept candidate verified.
    """
    ranked, _stats = rank_entities_with_stats(entities, frame, top_n=top_n)
    return ranked


def rank_entities_with_stats(
    entities: List[PlaceEntity],
    frame: ExperienceFrame,
    top_n: int = 10,
) -> Tuple[List[Tuple[PlaceEntity, RankScore]], RankerStats]:
    """Same as rank_entities but also returns RankerStats for observability."""
    stats = RankerStats(total_input=len(entities))
    if not entities:
        return [], stats

    # Score all entities
    scored: List[Tuple[float, PlaceEntity, RankScore]] = []
    accepted: List[Tuple[PlaceEntity, RankScore]] = []

    primary_concept = (
        frame.subtype_concepts[0] if frame.subtype_concepts else None
    )
    has_strong_concept = bool(
        primary_concept
        and primary_concept.confidence >= _STRONG_CONCEPT_CONFIDENCE_MIN
    )
    primary_label = (primary_concept.label if primary_concept else "").lower()
    concept_is_recognized = (
        has_strong_concept
        and primary_label
        and _has_known_synonym_set(primary_label)
    )

    dest_penalized_count = 0

    for entity in entities:
        sf = _subtype_fit(entity, frame)
        gf = _geo_fit(entity, frame)
        qs = _quality_signal(entity)
        es = _evidence_strength(entity)
        ds = _diversity_signal(entity, accepted)
        ps = _popularity_signal(entity)
        pf = _preference_fit(entity, frame)
        tc = 0.5  # neutral trip context (Phase 1 — no hotel plumbing)
        vf = _value_fit(entity, frame)
        pen = 0.0

        # Wrong-category penalty: when the user named a high-confidence venue
        # type and the entity has very low subtype_fit, suppress the score
        # so generic restaurants/parks don't dominate brewery/sushi asks.
        if has_strong_concept and sf < _WRONG_CATEGORY_SUBTYPE_FIT_MAX:
            pen += _WRONG_CATEGORY_PENALTY

        # Destination discipline: penalize entities whose address confirms a
        # different city than the requested destination. A Milwaukee brewery
        # must not outrank Chicago breweries for a Chicago request.
        dest_pen = _destination_penalty(entity, frame)
        if dest_pen > 0:
            pen += dest_pen
            dest_penalized_count += 1

        total = (
            _W_SUBTYPE_FIT * sf
            + _W_GEO_FIT * gf
            + _W_QUALITY * qs
            + _W_EVIDENCE * es
            + _W_DIVERSITY * ds
            + _W_POPULARITY * ps
            + _W_PREFERENCE_FIT * pf
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
            preference_fit=pf,
            trip_context_fit=tc,
            value_fit=vf,
            penalties=pen,
        )

        scored.append((total, entity, rs))

    # Sort descending by total score
    scored.sort(key=lambda x: x[0], reverse=True)

    on_concept_total = sum(
        1 for _t, _e, rs in scored if rs.subtype_fit >= _ON_CONCEPT_SUBTYPE_FIT_MIN
    )

    # Post-rank filter: when the user named a strong venue concept, drop
    # off-concept entries (modifier-only matches such as parks or generic
    # waterfront restaurants for a brewery ask) once we have enough verified
    # on-concept candidates. If the concept is recognized but the on-concept
    # pool is empty, return nothing rather than wrong-category cards.
    dropped_off_concept = 0
    if has_strong_concept:
        on_concept = [t for t in scored if t[2].subtype_fit >= _ON_CONCEPT_SUBTYPE_FIT_MIN]
        off_concept = [t for t in scored if t[2].subtype_fit < _ON_CONCEPT_SUBTYPE_FIT_MIN]
        if len(on_concept) >= _MIN_ON_CONCEPT_FOR_HARD_DROP:
            dropped_off_concept = len(off_concept)
            scored = on_concept
        elif not on_concept and concept_is_recognized:
            # Recognized venue concept (brewery/tapas/sushi/etc.) but no
            # candidate matched the category. Return no cards rather than
            # filling with modifier-only off-concept matches.
            dropped_off_concept = len(off_concept)
            scored = []

    result: List[Tuple[PlaceEntity, RankScore]] = []
    for _total, entity, rs in scored[:top_n]:
        result.append((entity, rs))

    stats.has_strong_concept = has_strong_concept
    stats.primary_label = primary_label
    stats.concept_is_recognized = bool(concept_is_recognized)
    stats.on_concept_count = on_concept_total
    stats.off_concept_dropped = dropped_off_concept
    stats.destination_penalized_count = dest_penalized_count

    logger.debug(
        "ranker: entities=%d ranked=%d off_concept_dropped=%d "
        "top_score=%.4f top_subtype_fit=%.4f top_geo_fit=%.4f "
        "primary_concept=%r recognized_concept=%s",
        len(entities),
        len(result),
        dropped_off_concept,
        result[0][1].total if result else 0,
        result[0][1].subtype_fit if result else 0,
        result[0][1].geo_fit if result else 0,
        primary_label,
        concept_is_recognized,
    )

    return result, stats
