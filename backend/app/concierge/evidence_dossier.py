"""Evidence Dossier v1 — structured place intelligence for AI Concierge cards.

PR #259: Normalizes available evidence into compact, typed dossiers for use by
the future card-role writer and set-level reviewer (PR #260+).

This PR builds and logs the dossier contract. It does not yet change note
generation or card roles — those are PR #260+.

Architecture invariants:
- Dossier is internal reasoning evidence only. NEVER expose internal_evidence_gaps
  or dossier contents as visible note prose.
- View/patio/waterfront themes require explicit enrichment evidence (amenity flags,
  editorial text, review snippets). Formatted_address containing "Riverwalk" does
  NOT populate the view_patio_waterfront theme; it is listing context only.
- Source confidence reflects actual data availability — not fabricated confidence.
- No Yelp/Foursquare/Tavily data exists in this pipeline today. Those buckets are
  not stubbed as empty stubs (which would be misleading); they are simply absent.
- Review count is a visible card stat, not a theme signal.
- Dossier building is CPU-only. Budget reserve is 100 ms (generous for pure Python).
- Do not block card return on dossier completeness.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum remaining budget (ms) to attempt full dossier build.
# Below this threshold dossiers are built from critical-path data only
# (no enrichment look-up) and marked is_minimal=True.
DOSSIER_BUDGET_RESERVE_MS: int = 100

# DossierConfidence string constants (not Enum for easy JSON serialization).
CONFIDENCE_STRONG = "strong"
CONFIDENCE_MIXED = "mixed"
CONFIDENCE_WEAK = "weak"


# ── Theme extraction keyword sets ─────────────────────────────────────────────
# Used ONLY for deterministic extraction from editorial summaries and review
# snippets. NOT applied to formatted_address or google_types for theme inference.
# Conservative: false positives erode downstream reasoning trust.

_FOOD_DRINK_KEYWORDS: frozenset = frozenset({
    "food", "menu", "beer", "cocktail", "wine", "drink", "cuisine", "dish",
    "burger", "pizza", "steak", "seafood", "sushi", "brunch", "breakfast",
    "lunch", "dinner", "chef", "kitchen", "craft", "seasonal", "fresh",
    "house-made", "housemade", "brew", "brewing", "taproom", "distillery",
    "spirits", "whiskey", "bourbon", "sake", "miso", "ramen", "noodle",
    "dumpling", "taco", "thai", "indian", "mediterranean", "italian",
    "french", "japanese", "chinese", "korean", "vietnamese", "oyster",
    "lobster", "crab", "sashimi", "omakase", "sommelier", "tasting",
    "pairing", "flight", "ipa", "lager", "ale", "draft", "tap",
})

_AMBIANCE_KEYWORDS: frozenset = frozenset({
    "vibe", "atmosphere", "ambiance", "ambience", "cozy", "intimate",
    "lively", "upscale", "casual", "trendy", "rustic", "elegant", "stylish",
    "hip", "warm", "inviting", "modern", "classic", "vintage", "historic",
    "industrial", "relaxed", "energetic", "buzzy", "chill", "relaxing",
    "romantic", "sophisticated", "charming", "welcoming", "festive",
    "vibrant", "laid-back",
})

_SERVICE_KEYWORDS: frozenset = frozenset({
    "service", "staff", "friendly", "knowledgeable", "attentive", "helpful",
    "server", "waiter", "bartender", "host", "professional", "experienced",
})

_CROWD_NOISE_KEYWORDS: frozenset = frozenset({
    "loud", "noisy", "quiet", "packed", "crowded", "busy", "rowdy",
    "neighborhood", "regulars", "locals", "sports", "college", "late night",
})

# View/outdoor terms: extracted ONLY from explicit enrichment evidence
# (amenity flags, editorial text, review snippets).
# Name matches → "listing_context:" prefix (lower trust).
# Address matches → NOT used for this theme at all.
_VIEW_OUTDOOR_KEYWORDS: frozenset = frozenset({
    "view", "rooftop", "patio", "outdoor", "terrace", "waterfront",
    "riverwalk", "garden", "balcony", "deck", "scenic", "skyline",
    "lake view", "river view", "lakefront", "riverfront", "al fresco",
})

_OCCASION_KEYWORDS: frozenset = frozenset({
    "date", "anniversary", "birthday", "celebration", "romantic",
    "special occasion", "business", "family", "happy hour",
})

_NEGATIVE_KEYWORDS: frozenset = frozenset({
    "expensive", "overpriced", "disappointing", "inconsistent",
    "mediocre", "skip", "not worth", "overcrowded", "terrible",
    "cold food", "dry", "bland",
})

# Name tokens that indicate outdoor/view listing context (not enrichment proof).
_VIEW_NAME_TOKENS: frozenset = frozenset({
    "rooftop", "patio", "terrace", "outdoor", "waterfront", "riverwalk",
    "lakefront", "riverfront", "balcony", "deck",
})


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class QueryFitEvidence:
    """Evidence of how well this place fits the user's query."""

    concept_fit: float           # 0.0–1.0 from rank_score.subtype_fit
    modifier_fit: Optional[str]  # "confirmed" | "not_confirmed" | "none" | None
    geo_fit: float               # 0.0–1.0 from rank_score.geo_fit
    vibe_fit: Optional[str]      # "waterfront" | "outdoor" | "view" | None


@dataclass
class ProviderEvidenceItem:
    """Evidence from one specific data source."""

    source: str                       # "google_places" | "google_place_details"
    facts: List[str] = field(default_factory=list)


@dataclass
class ReviewThemeEvidence:
    """Structured theme signals extracted from explicit text evidence only.

    All fields contain evidence strings derived from enrichment data or
    explicit name listing context. review_count is NEVER a theme here.

    view_patio_waterfront is populated ONLY from:
    - outdoor_seating=True amenity flag
    - "rooftop"/"patio"/"waterfront" etc. in editorial or review snippets
    - Entity name containing a view token → marked as "listing_context:<token>"
    NOT populated from formatted_address (even if it contains "Riverwalk").
    """

    food_drink: List[str] = field(default_factory=list)
    ambiance: List[str] = field(default_factory=list)
    service: List[str] = field(default_factory=list)
    crowd_noise: List[str] = field(default_factory=list)
    view_patio_waterfront: List[str] = field(default_factory=list)
    occasion_fit: List[str] = field(default_factory=list)
    negative_caveats: List[str] = field(default_factory=list)

    def total_theme_count(self) -> int:
        return (
            len(self.food_drink) + len(self.ambiance) + len(self.service)
            + len(self.crowd_noise) + len(self.view_patio_waterfront)
            + len(self.occasion_fit) + len(self.negative_caveats)
        )

    def as_counts_dict(self) -> Dict[str, int]:
        return {
            "food_drink": len(self.food_drink),
            "ambiance": len(self.ambiance),
            "service": len(self.service),
            "crowd_noise": len(self.crowd_noise),
            "view_patio_waterfront": len(self.view_patio_waterfront),
            "occasion_fit": len(self.occasion_fit),
            "negative_caveats": len(self.negative_caveats),
        }


@dataclass
class PlaceEvidenceDossier:
    """Compact structured evidence dossier for one AI Concierge card.

    Internal reasoning context for PR #260+ writer/reviewer.
    NEVER expose internal_evidence_gaps as visible note prose.
    NEVER use review_count as a theme signal (use only as a card stat).
    NEVER mint addable cards from non-Google evidence (structural invariant).
    """

    # Google identity (from critical path only)
    place_id: str
    name: str
    category: Optional[str]          # derived display category
    primary_type: Optional[str]       # raw Google primary_type
    google_types: List[str]           # all Google types
    neighborhood: Optional[str]       # formatted_address
    lat: Optional[float]
    lng: Optional[float]

    # Query fit signals from semantic ranker
    query_fit: QueryFitEvidence

    # Provider evidence: google_places always present; google_place_details
    # when enrichment ran. No Yelp/Foursquare/editorial buckets today.
    provider_evidence: List[ProviderEvidenceItem] = field(default_factory=list)

    # Review/theme evidence from explicit text fields
    review_themes: ReviewThemeEvidence = field(default_factory=ReviewThemeEvidence)

    # Overall data confidence
    source_confidence: str = CONFIDENCE_WEAK  # "strong" | "mixed" | "weak"

    # Internal gaps — NEVER convert to visible note text
    internal_evidence_gaps: List[str] = field(default_factory=list)

    # Aggregated counts for telemetry
    evidence_source_counts: Dict[str, int] = field(default_factory=dict)
    theme_counts: Dict[str, int] = field(default_factory=dict)

    # True when built from critical-path data only (no place_details enrichment)
    is_minimal: bool = False


@dataclass
class EvidenceDossierTelemetry:
    """Aggregated telemetry from a batch of dossiers for one pipeline turn."""

    dossier_built_count: int = 0
    dossier_confidence_counts: Dict[str, int] = field(default_factory=dict)
    dossier_source_counts: Dict[str, int] = field(default_factory=dict)
    dossier_theme_counts: Dict[str, int] = field(default_factory=dict)
    dossier_with_place_details_count: int = 0
    dossier_minimal_count: int = 0
    dossier_skipped_due_to_budget_count: int = 0
    review_theme_count_per_card: List[int] = field(default_factory=list)
    evidence_sources_used_per_card: List[List[str]] = field(default_factory=list)

    def as_log_dict(self) -> Dict[str, Any]:
        return {
            "dossier_built_count": self.dossier_built_count,
            "dossier_confidence_counts": self.dossier_confidence_counts,
            "dossier_source_counts": self.dossier_source_counts,
            "dossier_theme_counts": self.dossier_theme_counts,
            "dossier_with_place_details_count": self.dossier_with_place_details_count,
            "dossier_minimal_count": self.dossier_minimal_count,
            "dossier_skipped_due_to_budget_count": self.dossier_skipped_due_to_budget_count,
        }


# ── Internal helpers ──────────────────────────────────────────────────────────

def _text_tokens(text: str) -> frozenset:
    """Tokenize text to a frozenset of lowercase word tokens."""
    return frozenset(re.findall(r"[a-z][a-z\-']+", text.lower()))


def _extract_text_themes(text: str, themes: ReviewThemeEvidence) -> None:
    """Extract theme signals from one text string into themes in-place.

    Multi-word keywords are checked against raw text_lower.
    Single-word keywords are checked against token set.
    Per-text per-theme cap of 3 matches prevents over-stuffing.
    """
    text_lower = text.lower()
    tokens = _text_tokens(text)

    def _hits(keywords: frozenset) -> List[str]:
        found: List[str] = []
        for kw in keywords:
            if len(found) >= 3:
                break
            kw_toks = _text_tokens(kw)
            if not kw_toks:
                continue
            if " " in kw:
                # Multi-word: check raw text
                if kw in text_lower:
                    found.append(kw)
            else:
                # Single-word: exact token match OR prefix match for plurals
                # e.g., "cocktail" matches "cocktails", "beer" matches "beers"
                kw_word = next(iter(kw_toks))
                if kw_word in tokens or any(
                    t.startswith(kw_word) for t in tokens if len(t) > len(kw_word)
                ):
                    found.append(kw)
        return found

    fd = _hits(_FOOD_DRINK_KEYWORDS)
    if fd:
        themes.food_drink.extend(fd)

    amb = _hits(_AMBIANCE_KEYWORDS)
    if amb:
        themes.ambiance.extend(amb)

    svc = _hits(_SERVICE_KEYWORDS)
    if svc:
        themes.service.extend(svc)

    noise = _hits(_CROWD_NOISE_KEYWORDS)
    if noise:
        themes.crowd_noise.extend(noise)

    view = _hits(_VIEW_OUTDOOR_KEYWORDS)
    if view:
        themes.view_patio_waterfront.extend(view)

    occ = _hits(_OCCASION_KEYWORDS)
    if occ:
        themes.occasion_fit.extend(occ)

    neg = _hits(_NEGATIVE_KEYWORDS)
    if neg:
        themes.negative_caveats.extend(neg)


def _compute_source_confidence(
    rank_score: Any,
    has_enrichment: bool,
    has_differentiating_content: bool,
) -> str:
    """Compute overall source confidence from available data.

    STRONG: enrichment with differentiating content AND good concept fit.
    MIXED:  enrichment available or good concept fit without enrichment.
    WEAK:   name/type/rating only, low concept fit.
    """
    subtype_fit: float = getattr(rank_score, "subtype_fit", 0.0)

    if has_enrichment and has_differentiating_content and subtype_fit >= 0.5:
        return CONFIDENCE_STRONG
    if (has_enrichment and has_differentiating_content) or subtype_fit >= 0.6:
        return CONFIDENCE_MIXED
    if subtype_fit >= 0.4 or has_enrichment:
        return CONFIDENCE_MIXED
    return CONFIDENCE_WEAK


def _build_evidence_gaps(
    entity: Any,
    enrichment: Optional[Any],
) -> List[str]:
    """Identify what evidence is missing. Internal only — never surface as prose."""
    gaps: List[str] = []
    if enrichment is None:
        gaps.append("no_place_details_enrichment")
    else:
        if not getattr(enrichment, "editorial_summary", None):
            gaps.append("no_editorial_summary")
        if not getattr(enrichment, "review_snippets", None):
            gaps.append("no_review_snippets")
        amenity_all_none = all(
            getattr(enrichment, attr, None) is None
            for attr in (
                "serves_beer", "serves_wine", "serves_cocktails",
                "outdoor_seating", "live_music", "good_for_groups",
            )
        )
        if amenity_all_none:
            gaps.append("no_amenity_flags")

    if getattr(entity, "rating", None) is None:
        gaps.append("no_rating")
    if not getattr(entity, "price_level", None):
        gaps.append("no_price_level")

    return gaps


# ── Public API ────────────────────────────────────────────────────────────────

def extract_review_themes(
    enrichment: Optional[Any],
    entity_name: str = "",
    google_types: Optional[List[str]] = None,
) -> ReviewThemeEvidence:
    """Deterministic conservative theme extraction from available fields.

    Sources used (in trust order):
    1. Amenity flags from Place Details — explicit, highest trust.
    2. Editorial summary from Place Details — explicit, high trust.
    3. Review snippets from Place Details — explicit, moderate trust.
    4. Entity name — listing context only, marked "listing_context:<token>".

    NOT used as theme evidence:
    - formatted_address (address context ≠ enrichment proof)
    - review_count (card stat only)
    - google_types (category signal, not theme)
    """
    themes = ReviewThemeEvidence()
    if enrichment is None:
        # No enrichment: check entity name for listing context only.
        name_lower = entity_name.lower()
        for tok in _VIEW_NAME_TOKENS:
            if tok in name_lower:
                themes.view_patio_waterfront.append(f"listing_context:{tok}")
                break
        return themes

    # ── Amenity flags (explicit, boolean) ────────────────────────────────────
    if getattr(enrichment, "serves_beer", None) is True:
        themes.food_drink.append("serves beer (amenity)")
    if getattr(enrichment, "serves_wine", None) is True:
        themes.food_drink.append("serves wine (amenity)")
    if getattr(enrichment, "serves_cocktails", None) is True:
        themes.food_drink.append("serves cocktails (amenity)")
    if getattr(enrichment, "outdoor_seating", None) is True:
        themes.view_patio_waterfront.append("outdoor seating (amenity)")
    if getattr(enrichment, "live_music", None) is True:
        themes.ambiance.append("live music (amenity)")
    if getattr(enrichment, "good_for_groups", None) is True:
        themes.occasion_fit.append("good for groups (amenity)")

    # ── Text evidence: editorial + review snippets ────────────────────────────
    editorial: str = getattr(enrichment, "editorial_summary", None) or ""
    if editorial:
        _extract_text_themes(editorial, themes)

    for snippet in (getattr(enrichment, "review_snippets", None) or []):
        if snippet:
            _extract_text_themes(snippet, themes)

    # ── Entity name: listing context only ────────────────────────────────────
    name_lower = entity_name.lower()
    for tok in _VIEW_NAME_TOKENS:
        if tok in name_lower:
            # Already have explicit evidence; only add listing context if not
            # covered by enrichment to avoid double-counting.
            explicit_present = any(
                "amenity" in e or tok in e.lower()
                for e in themes.view_patio_waterfront
            )
            if not explicit_present:
                themes.view_patio_waterfront.append(f"listing_context:{tok}")
            break

    return themes


def build_place_evidence_dossier(
    entity: Any,
    frame: Any,
    rank_score: Any,
    enrichment: Optional[Any] = None,
    category: Optional[str] = None,
) -> PlaceEvidenceDossier:
    """Build one PlaceEvidenceDossier for a verified ranked entity.

    Args:
        entity:     Verified PlaceEntity from the critical Google path.
        frame:      ExperienceFrame (query signals).
        rank_score: RankScore from semantic ranker.
        enrichment: Optional PlaceDetailsResult from non-critical enrichment.
        category:   Derived display category (from _derive_display_category).

    Returns:
        PlaceEvidenceDossier with all available evidence structured.
        Never raises — caller catches any exception.
    """
    # ── Query fit ──────────────────────────────────────────────────────────────
    subtype_fit: float = getattr(rank_score, "subtype_fit", 0.0)
    geo_fit: float = getattr(rank_score, "geo_fit", 0.0)

    location_modifiers: List[str] = getattr(frame, "location_modifiers", []) or []
    modifier_fit: Optional[str] = "none" if not location_modifiers else None

    if location_modifiers:
        # Lazy import to avoid circular at module load time.
        from app.concierge.ranker import _location_modifier_confirmed
        for modifier in location_modifiers[:1]:
            modifier_fit = (
                "confirmed"
                if _location_modifier_confirmed(modifier, entity)
                else "not_confirmed"
            )

    geo_hints: List[str] = getattr(frame, "geography_hints", []) or []
    vibe_fit: Optional[str] = None
    if geo_hints:
        geo_lower = " ".join(geo_hints).lower()
        if any(w in geo_lower for w in ("river", "waterfront", "lakefront", "lake")):
            vibe_fit = "waterfront"
        elif any(w in geo_lower for w in ("rooftop", "patio", "outdoor", "terrace")):
            vibe_fit = "outdoor"
        elif any(w in geo_lower for w in ("view", "scenic", "panoramic", "overlook")):
            vibe_fit = "view"

    query_fit = QueryFitEvidence(
        concept_fit=subtype_fit,
        modifier_fit=modifier_fit,
        geo_fit=geo_fit,
        vibe_fit=vibe_fit,
    )

    # ── Provider evidence: Google Places identity ─────────────────────────────
    google_facts: List[str] = []

    raw_type = entity.primary_type or (entity.types[0] if entity.types else None)
    if raw_type:
        google_facts.append(f"type:{raw_type.replace('_', ' ')}")

    if entity.rating is not None:
        google_facts.append(f"rating:{entity.rating:.1f}")
    if entity.user_rating_count:
        google_facts.append(f"review_count:{entity.user_rating_count}")
    if entity.price_level:
        google_facts.append(f"price_level:{entity.price_level}")
    if entity.business_status:
        google_facts.append(f"status:{entity.business_status}")
    if entity.google_maps_uri:
        google_facts.append("google_maps_uri:present")
    if entity.website_uri:
        google_facts.append("website_uri:present")

    provider_evidence: List[ProviderEvidenceItem] = [
        ProviderEvidenceItem(source="google_places", facts=google_facts)
    ]

    # ── Provider evidence: Google Place Details ────────────────────────────────
    details_facts: List[str] = []
    has_enrichment = enrichment is not None
    has_differentiating = (
        has_enrichment
        and getattr(enrichment, "has_differentiating_content", lambda: False)()
    )

    if enrichment is not None:
        editorial = getattr(enrichment, "editorial_summary", None)
        if editorial:
            details_facts.append(f"editorial_summary:{editorial[:80]}")

        for i, snippet in enumerate((getattr(enrichment, "review_snippets", None) or [])[:2]):
            details_facts.append(f"review_snippet_{i + 1}:{snippet[:80]}")

        for flag_name in (
            "serves_beer", "serves_wine", "serves_cocktails",
            "outdoor_seating", "live_music", "good_for_groups",
        ):
            val = getattr(enrichment, flag_name, None)
            if val is not None:
                details_facts.append(f"{flag_name}:{val}")

        if details_facts:
            provider_evidence.append(
                ProviderEvidenceItem(source="google_place_details", facts=details_facts)
            )

    # ── Review themes ──────────────────────────────────────────────────────────
    review_themes = extract_review_themes(
        enrichment=enrichment,
        entity_name=entity.name,
        google_types=entity.types,
    )

    # ── Source confidence ──────────────────────────────────────────────────────
    source_confidence = _compute_source_confidence(rank_score, has_enrichment, has_differentiating)

    # ── Evidence gaps (internal — never surface as prose) ────────────────────
    internal_evidence_gaps = _build_evidence_gaps(entity, enrichment)

    # ── Telemetry counts ──────────────────────────────────────────────────────
    evidence_source_counts: Dict[str, int] = {
        "google_places": len(google_facts),
        "google_place_details": len(details_facts),
    }
    theme_counts = review_themes.as_counts_dict()

    return PlaceEvidenceDossier(
        place_id=entity.place_id,
        name=entity.name,
        category=category,
        primary_type=entity.primary_type,
        google_types=list(entity.types or []),
        neighborhood=entity.formatted_address,
        lat=entity.lat,
        lng=entity.lng,
        query_fit=query_fit,
        provider_evidence=provider_evidence,
        review_themes=review_themes,
        source_confidence=source_confidence,
        internal_evidence_gaps=internal_evidence_gaps,
        evidence_source_counts=evidence_source_counts,
        theme_counts=theme_counts,
        is_minimal=(not has_enrichment),
    )


def build_dossiers_for_ranked_cards(
    ranked: List[Tuple[Any, Any]],
    frame: Any,
    enrichment_map: Dict[str, Any],
    deadline: Optional[Any] = None,
    top_n: int = 6,
    category_fn: Optional[Callable[[Any], str]] = None,
) -> List[PlaceEvidenceDossier]:
    """Build PlaceEvidenceDossier for the top-N ranked cards.

    Respects deadline: when remaining budget < DOSSIER_BUDGET_RESERVE_MS,
    enrichment_map lookups are skipped and all dossiers are built from
    critical-path data only (is_minimal=True).

    Never blocks card return. Any per-dossier exception is caught and logged.

    Args:
        ranked:        List of (PlaceEntity, RankScore) in ranked order.
        frame:         ExperienceFrame for query signals.
        enrichment_map: place_id → PlaceDetailsResult from non-critical enrichment.
        deadline:      Optional RequestDeadline. None = no budget check.
        top_n:         Maximum dossiers to build (default 6).
        category_fn:   Optional callable(entity) → display category string.

    Returns:
        List of PlaceEvidenceDossier in ranked order, at most top_n entries.
    """
    if not ranked:
        return []

    targets = ranked[:top_n]

    low_budget = (
        deadline is not None
        and deadline.remaining_ms() < DOSSIER_BUDGET_RESERVE_MS
    )

    dossiers: List[PlaceEvidenceDossier] = []
    for entity, rank_score in targets:
        enrichment = None if low_budget else enrichment_map.get(entity.place_id)
        category = category_fn(entity) if category_fn is not None else None

        try:
            dossier = build_place_evidence_dossier(
                entity=entity,
                frame=frame,
                rank_score=rank_score,
                enrichment=enrichment,
                category=category,
            )
            dossiers.append(dossier)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "evidence_dossier: build_failed name=%s error=%s",
                getattr(entity, "name", "?"),
                exc,
            )

    minimal_count = sum(1 for d in dossiers if d.is_minimal)
    conf_dist = {
        CONFIDENCE_STRONG: sum(1 for d in dossiers if d.source_confidence == CONFIDENCE_STRONG),
        CONFIDENCE_MIXED: sum(1 for d in dossiers if d.source_confidence == CONFIDENCE_MIXED),
        CONFIDENCE_WEAK: sum(1 for d in dossiers if d.source_confidence == CONFIDENCE_WEAK),
    }
    avg_themes = (
        sum(d.review_themes.total_theme_count() for d in dossiers) / len(dossiers)
        if dossiers else 0.0
    )

    logger.info(
        "evidence_dossier: built count=%d minimal_count=%d "
        "low_budget=%s confidence_dist=%r avg_themes=%.1f",
        len(dossiers),
        minimal_count,
        low_budget,
        conf_dist,
        avg_themes,
    )

    return dossiers


def get_dossier_telemetry(
    dossiers: List[PlaceEvidenceDossier],
    skipped_due_to_budget: int = 0,
) -> EvidenceDossierTelemetry:
    """Aggregate telemetry from a batch of dossiers for one pipeline turn.

    The returned EvidenceDossierTelemetry.as_log_dict() should be included
    in _log_semantic_turn for structured observability.
    """
    if not dossiers:
        return EvidenceDossierTelemetry(
            dossier_built_count=0,
            dossier_skipped_due_to_budget_count=skipped_due_to_budget,
        )

    confidence_counts: Dict[str, int] = {
        CONFIDENCE_STRONG: 0,
        CONFIDENCE_MIXED: 0,
        CONFIDENCE_WEAK: 0,
    }
    all_source_counts: Dict[str, int] = {}
    all_theme_counts: Dict[str, int] = {}
    with_details_count = 0
    minimal_count = 0
    review_theme_counts_per_card: List[int] = []
    evidence_sources_per_card: List[List[str]] = []

    for d in dossiers:
        confidence_counts[d.source_confidence] = (
            confidence_counts.get(d.source_confidence, 0) + 1
        )
        for src, cnt in d.evidence_source_counts.items():
            all_source_counts[src] = all_source_counts.get(src, 0) + cnt
        for theme, cnt in d.theme_counts.items():
            all_theme_counts[theme] = all_theme_counts.get(theme, 0) + cnt
        if any(p.source == "google_place_details" for p in d.provider_evidence):
            with_details_count += 1
        if d.is_minimal:
            minimal_count += 1
        review_theme_counts_per_card.append(d.review_themes.total_theme_count())
        evidence_sources_per_card.append([p.source for p in d.provider_evidence])

    return EvidenceDossierTelemetry(
        dossier_built_count=len(dossiers),
        dossier_confidence_counts=confidence_counts,
        dossier_source_counts=all_source_counts,
        dossier_theme_counts=all_theme_counts,
        dossier_with_place_details_count=with_details_count,
        dossier_minimal_count=minimal_count,
        dossier_skipped_due_to_budget_count=skipped_due_to_budget,
        review_theme_count_per_card=review_theme_counts_per_card,
        evidence_sources_used_per_card=evidence_sources_per_card,
    )
