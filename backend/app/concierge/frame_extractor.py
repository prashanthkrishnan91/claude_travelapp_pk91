"""ExperienceFrame extractor — open-vocabulary deterministic phase.

Converts a natural-language place ask into a structured ExperienceFrame without
relying on a closed category enum. The primary subtype concept is extracted from
the user's literal words, not matched against a fixed list.

Phase 1: fully deterministic. No LLM calls. If LLM extraction is added later,
deterministic fallback must still be the path when LLM is unavailable.

Fallback guarantee: this module never raises. On any internal error it returns
a minimal frame from the literal query so the retrieval pipeline can still
attempt a provider search.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Open-vocabulary support structures ───────────────────────────────────────

# Words that do not carry subtype meaning — removed before concept extraction.
_FILLER_WORDS: frozenset = frozenset(
    {
        "best", "top", "great", "nice", "good", "some", "find", "get", "show",
        "popular", "famous", "well-known", "favorite", "favourite", "local",
        "authentic", "a", "an", "the", "some", "any", "want", "looking",
        "for", "me", "us", "our", "my", "give", "recommend", "suggestion",
        "suggestions", "what", "where", "which", "go", "visit", "experience",
        "try", "really", "very", "super", "quite", "pretty", "nearby",
        "around", "close", "within", "please", "help", "need", "i",
        "looking", "place", "places", "spot", "spots", "option", "options",
        "type", "types", "kind", "kinds", "few", "couple",
        # Vibe/preference words — these are soft signals, not place-type concepts.
        # Keeping them out of concept extraction ensures "romantic tapas" → concept=tapas.
        "romantic", "intimate", "cozy", "cosy", "casual", "quiet", "lively",
        "trendy", "hip", "fancy", "upscale", "cool", "lovely", "wonderful",
        "amazing", "excellent", "incredible", "awesome", "perfect", "ideal",
        "unique", "special", "fun", "relaxing", "vibrant", "classy",
        "family", "kid", "hidden", "secret", "undiscovered", "off-the-beaten",
        "outdoor", "indoor", "open",
    }
)

# Prepositions / conjunctions that introduce modifying clauses.
# Splitting on these isolates the primary concept in the first clause.
_MODIFIER_SPLIT_RE = re.compile(
    r"\b(along|near|with|but|and(?:\s+not)?|at|in|on|close\s+to|by|next\s+to|"
    r"from|towards?|having|featuring|that\s+has|which\s+has|where|"
    r"except|without|unless)\b",
    re.IGNORECASE,
)

# Geography concept patterns — waterfront, riverwalk, lake, etc.
_GEO_PATTERNS: List[tuple] = [
    (re.compile(r"\bwaterfront\b", re.I), "waterfront"),
    (re.compile(r"\briverwalk\b", re.I), "riverwalk"),
    (re.compile(r"\briverview\b", re.I), "river view"),
    (re.compile(r"\blakefront\b", re.I), "lakefront"),
    (re.compile(r"\blake\s*view\b", re.I), "lake view"),
    (re.compile(r"\bocean\s*view\b", re.I), "ocean view"),
    (re.compile(r"\bsea\s*view\b", re.I), "sea view"),
    (re.compile(r"\bwaterside\b", re.I), "waterside"),
    (re.compile(r"\bbeachfront\b", re.I), "beachfront"),
    (re.compile(r"\bharbour?(?:\s*side|front)?\b", re.I), "harbour"),
    (re.compile(r"\brivera?\b", re.I), "river"),
    (re.compile(r"\blake\b", re.I), "lake"),
    (re.compile(r"\bocean\b", re.I), "ocean"),
    (re.compile(r"\bcoastline?\b", re.I), "coast"),
    (re.compile(r"\bwater\s+view\b", re.I), "water view"),
    (re.compile(r"\bview\s+of\s+(?:the\s+)?(?:water|lake|river|bay|ocean)\b", re.I), "water view"),
    (re.compile(r"\brooftop\b", re.I), "rooftop"),
    (re.compile(r"\boutdoor\b", re.I), "outdoor"),
    (re.compile(r"\bpatio\b", re.I), "patio"),
    (re.compile(r"\bterrace\b", re.I), "terrace"),
]

# Geo hints that are NOT structurally verifiable from Google data alone.
_WEAK_GEO_ATTRIBUTES = frozenset({"waterfront", "river view", "lake view", "ocean view",
                                   "sea view", "water view", "harbour", "riverwalk"})

# Soft preference patterns
_SOFT_PREF_PATTERNS: List[tuple] = [
    (re.compile(r"\bromantic\b|\bdate\s+night\b|\banniversary\b|\bhoneymoon\b", re.I), "romantic"),
    (re.compile(r"\bintimate\b|\bcozy\b|\bcosy\b", re.I), "intimate"),
    (re.compile(r"\bupscale\b|\bfancy\b|\bfine\s+dining\b|\belegant\b|\bluxury\b|\bupmarket\b", re.I), "upscale"),
    (re.compile(r"\bcasual\b|\brelaxed\b|\blaid[-\s]?back\b", re.I), "casual"),
    (re.compile(r"\bfamily[-\s]?friendly\b|\bkid[-\s]?friendly\b|\bgood\s+for\s+kids\b", re.I), "family_friendly"),
    (re.compile(r"\btrendy\b|\bhip\b|\bmodern\b|\binstagrammable\b", re.I), "trendy"),
    (re.compile(r"\blively\b|\bbuzzing\b|\bbusy\b|\benergetic\b", re.I), "lively"),
    (re.compile(r"\bquiet\b|\bpeaceful\b|\bserene\b", re.I), "quiet"),
    (re.compile(r"\bunique\b|\bspecial\b|\bunusual\b|\buncommon\b", re.I), "unique"),
    (re.compile(r"\bwell[-\s]?known\b|\bpopular\b|\biconic\b", re.I), "popular"),
]

# Negative constraint patterns
_NEGATIVE_PATTERNS: List[tuple] = [
    (re.compile(r"\bnot\s+too\s+loud\b|\bnot\s+loud\b|\bnon[-\s]?loud\b", re.I), "not_loud"),
    (re.compile(r"\bnot\s+too\s+crowded\b|\bnot\s+crowded\b", re.I), "not_crowded"),
    (re.compile(r"\bnot\s+too\s+touristy\b|\bnot\s+touristy\b", re.I), "not_touristy"),
    (re.compile(r"\bnot\s+too\s+expensive\b|\bnot\s+expensive\b|\baffordable\b|\bcheap\b|\bbudget\b", re.I), "not_expensive"),
    (re.compile(r"\bnot\s+too\s+fancy\b|\bnot\s+formal\b", re.I), "not_formal"),
    (re.compile(r"\bno\s+chains?\b|\bnot\s+(?:a\s+)?chain\b", re.I), "no_chains"),
]

# Value signal patterns
_VALUE_PATTERNS: List[tuple] = [
    (re.compile(r"\bluxury\b|\bluxe\b|\bpremium\b|\bsplurge\b|\bhigh[-\s]?end\b", re.I), "luxury"),
    (re.compile(r"\baffordable\b|\bbargain\b|\bbudget\b|\bcheap\b|\bvalue\b|\binexpensive\b", re.I), "budget"),
    (re.compile(r"\bbest\s+value\b|\bgood\s+value\b|\bvalue\s+for\s+money\b", re.I), "value_for_money"),
]

# Words that look like plural place types — not part of concept
_GENERIC_PLACE_NOUNS = frozenset(
    {"restaurants", "restaurant", "bar", "bars", "cafe", "cafes", "café", "cafés",
     "place", "places", "spot", "spots", "venue", "venues", "lounge", "lounges",
     "establishment", "establishment", "eatery", "eateries", "joint", "joints"}
)

# Simple singularization rules: (pattern, replacement)
_SINGULARIZE_RULES = [
    (re.compile(r"eries$"), "ery"),   # breweries → brewery, bakeries → bakery
    (re.compile(r"ies$"), "y"),        # taperies → tapery (edge)
    (re.compile(r"ves$"), "f"),        # shelves → shelf (edge)
    (re.compile(r"ses$"), "se"),       # classes → class (edge)
    (re.compile(r"xes$"), "x"),        # boxes → box (edge)
    (re.compile(r"ches$"), "ch"),      # beaches → beach
    (re.compile(r"shes$"), "sh"),      # dishes → dish
    (re.compile(r"s$"), ""),           # generic plural → remove s
]

# Words that end in 's' but are already singular (do NOT strip 's')
_KEEP_S_WORDS = frozenset(
    {"tapas", "hummus", "couscous", "oasis", "bonus", "focus", "status",
     "campus", "virus", "circus", "celsius", "glass", "grass", "mass",
     "class", "pass", "bass", "brass", "cross", "loss", "moss", "toss"}
)

# Ambiguity flags: attributes the user may ask for that cannot be structurally verified
_AMBIGUITY_PATTERNS: List[tuple] = [
    (re.compile(r"\bwaterfront\b|\bwater\s*view\b|\briver\s*view\b|\blake\s*view\b|\bocean\s*view\b", re.I),
     "view_not_structurally_verifiable"),
    (re.compile(r"\bquiet\b|\bnot\s+too\s+loud\b|\bpeaceful\b", re.I),
     "noise_level_not_verifiable"),
    (re.compile(r"\bromantic\b|\bintimate\b|\bcozy\b", re.I),
     "ambiance_not_verifiable"),
    (re.compile(r"\bvibe\b|\batmosphere\b|\bfeel\b", re.I),
     "vibe_not_verifiable"),
]


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class SubtypeConcept:
    label: str               # e.g. "brewery", "tapas", "sushi"
    confidence: float        # 0.0–1.0
    source: str              # "literal_primary" | "literal_secondary" | "inferred"


@dataclass
class ExperienceFrame:
    """Open-vocabulary structured representation of a place ask."""

    literal_ask: str
    normalized_ask: str
    destination: str

    # How the user expects the answer
    answer_mode: str = "place_list"  # "place_list" | "single_best" | "comparison"
    follow_up_mode: str = "new_search"  # "new_search" | "refine" | "more_options"

    # Core concept — open vocabulary, not a closed enum
    subtype_concepts: List[SubtypeConcept] = field(default_factory=list)

    # Weak Google category hints derived from concept (used as query builder hints)
    place_kind_hints: List[str] = field(default_factory=list)

    # Constraints and preferences (all open strings)
    must_have: List[str] = field(default_factory=list)
    soft_preferences: List[str] = field(default_factory=list)
    negative_constraints: List[str] = field(default_factory=list)

    # Geography
    geography_hints: List[str] = field(default_factory=list)

    # Temporal / value
    temporal_constraints: List[str] = field(default_factory=list)
    value_signals: List[str] = field(default_factory=list)

    # Ambiguity flags — attributes explicitly asked for that cannot be structurally verified
    ambiguity_flags: List[str] = field(default_factory=list)

    # Meta
    confidence: float = 0.8
    needs_provider_call: bool = True


# ── Helpers ──────────────────────────────────────────────────────────────────

def _singularize(word: str) -> str:
    """Best-effort singularization for English place/food nouns."""
    w = word.lower().strip()
    if w in _KEEP_S_WORDS:
        return w
    if len(w) <= 3:
        return w
    for pattern, repl in _SINGULARIZE_RULES:
        candidate = pattern.sub(repl, w)
        if candidate != w and len(candidate) >= 3:
            return candidate
    return w


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"\b[a-z][a-z-]*[a-z]\b|\b[a-z]{2,}\b", text.lower())


def _extract_geo_hints(query: str) -> List[str]:
    hints = []
    seen = set()
    for pattern, label in _GEO_PATTERNS:
        if pattern.search(query) and label not in seen:
            hints.append(label)
            seen.add(label)
    return hints


def _extract_soft_preferences(query: str) -> List[str]:
    prefs = []
    for pattern, label in _SOFT_PREF_PATTERNS:
        if pattern.search(query):
            prefs.append(label)
    return prefs


def _extract_negative_constraints(query: str) -> List[str]:
    constraints = []
    for pattern, label in _NEGATIVE_PATTERNS:
        if pattern.search(query):
            constraints.append(label)
    return constraints


def _extract_value_signals(query: str) -> List[str]:
    signals = []
    for pattern, label in _VALUE_PATTERNS:
        if pattern.search(query):
            signals.append(label)
    return signals


def _extract_ambiguity_flags(query: str) -> List[str]:
    flags = []
    seen = set()
    for pattern, label in _AMBIGUITY_PATTERNS:
        if pattern.search(query) and label not in seen:
            flags.append(label)
            seen.add(label)
    return flags


def _extract_primary_concepts(query: str) -> List[SubtypeConcept]:
    """Extract open-vocabulary subtype concepts from the user's literal ask.

    Strategy:
    1. Split query at modifier-introducing prepositions/conjunctions.
    2. Take the first clause (contains the primary concept).
    3. Remove filler words and generic place nouns.
    4. The remaining tokens are candidate concept labels.
    5. Singularize and score.

    This is deliberately open-vocabulary: no fixed enum lookup.
    If the user says "breweries", we extract "brewery".
    If the user says "distilleries", we extract "distillery".
    No predefined list required.
    """
    q = query.strip()
    # Split at first preposition / conjunction that introduces a modifier clause
    parts = _MODIFIER_SPLIT_RE.split(q, maxsplit=1)
    main_clause = parts[0].strip()

    tokens = _tokenize_words(main_clause)

    # Remove filler words
    meaningful = [t for t in tokens if t not in _FILLER_WORDS]

    # Remove generic place nouns (restaurant, bar, etc.) to keep the concept
    # But keep them if they ARE the only meaningful token
    non_generic = [t for t in meaningful if t not in _GENERIC_PLACE_NOUNS]
    if not non_generic and meaningful:
        non_generic = meaningful[:1]  # keep first generic if nothing else

    if not non_generic:
        # Nothing found — fall back to first meaningful token from full query
        all_tokens = _tokenize_words(q)
        non_generic = [t for t in all_tokens if t not in _FILLER_WORDS and len(t) > 3][:2]

    concepts: List[SubtypeConcept] = []
    seen_labels: set = set()

    for i, token in enumerate(non_generic[:3]):
        singular = _singularize(token)
        if singular and singular not in seen_labels and len(singular) >= 3:
            confidence = 0.95 if i == 0 else max(0.5, 0.75 - i * 0.15)
            source = "literal_primary" if i == 0 else "literal_secondary"
            concepts.append(SubtypeConcept(label=singular, confidence=confidence, source=source))
            seen_labels.add(singular)
            # Also add the raw (plural) form if different
            if token != singular and token not in seen_labels and len(token) >= 3:
                concepts.append(SubtypeConcept(label=token, confidence=confidence * 0.9, source=source))
                seen_labels.add(token)

    return concepts


def _derive_place_kind_hints(concepts: List[SubtypeConcept]) -> List[str]:
    """Derive weak Google Places category hints from extracted concepts.

    These are hints for query construction — NOT hard gates for eligibility.
    """
    hints = ["food_and_drink"]  # baseline: any place that serves food/drink
    for concept in concepts:
        label = concept.label.lower()
        # Common patterns — extensible without being a closed enum
        if any(w in label for w in ("brew", "taproom", "beer", "ale", "lager", "ipa")):
            hints.extend(["brewery", "bar"])
        elif any(w in label for w in ("wine", "winery", "vineyard", "oenoph")):
            hints.extend(["wine_bar", "winery"])
        elif any(w in label for w in ("distill", "whiskey", "whisky", "spirit", "bourbon")):
            hints.extend(["bar", "distillery"])
        elif any(w in label for w in ("coffee", "cafe", "espresso", "latte")):
            hints.extend(["cafe", "coffee_shop"])
        elif any(w in label for w in ("bakery", "pastry", "croissant", "bread")):
            hints.extend(["bakery"])
        elif any(w in label for w in ("bar", "cocktail", "speakeasy", "lounge")):
            hints.extend(["bar", "cocktail_bar"])
        elif any(w in label for w in ("club", "nightclub", "nightlife")):
            hints.extend(["night_club"])
        else:
            hints.append("restaurant")
    # Deduplicate preserving order
    seen = set()
    deduped = []
    for h in hints:
        if h not in seen:
            deduped.append(h)
            seen.add(h)
    return deduped


# ── Public API ────────────────────────────────────────────────────────────────

def extract_frame(user_query: str, destination: str, follow_up_mode: str = "new_search") -> ExperienceFrame:
    """Extract an ExperienceFrame from a natural-language place ask.

    Deterministic. Never raises. Falls back to a minimal frame on any error.

    Args:
        user_query: The user's raw natural-language ask.
        destination: The trip destination (city name).
        follow_up_mode: "new_search" | "refine" | "more_options".

    Returns:
        ExperienceFrame with open-vocabulary subtype concepts and modifiers.
    """
    try:
        return _extract_frame_impl(user_query, destination, follow_up_mode)
    except Exception as exc:
        logger.warning(
            "frame_extractor: extraction failed, using minimal fallback: %s", exc
        )
        return _minimal_fallback_frame(user_query, destination, follow_up_mode)


def _extract_frame_impl(
    user_query: str, destination: str, follow_up_mode: str
) -> ExperienceFrame:
    q = (user_query or "").strip()
    if not q:
        return _minimal_fallback_frame(user_query, destination, follow_up_mode)

    # Extract all modifiers
    geo_hints = _extract_geo_hints(q)
    soft_prefs = _extract_soft_preferences(q)
    negative_constraints = _extract_negative_constraints(q)
    value_signals = _extract_value_signals(q)
    ambiguity_flags = _extract_ambiguity_flags(q)

    # Open-vocabulary concept extraction (core of this module)
    subtype_concepts = _extract_primary_concepts(q)
    place_kind_hints = _derive_place_kind_hints(subtype_concepts)

    # Normalized ask: lowercase, remove extra whitespace
    normalized = re.sub(r"\s+", " ", q.lower()).strip()

    # Answer mode heuristics
    answer_mode = "place_list"
    if re.search(r"\b(best one|single best|top pick|top choice|one recommendation)\b", q, re.I):
        answer_mode = "single_best"
    elif re.search(r"\b(compare|versus|vs\.?|difference between)\b", q, re.I):
        answer_mode = "comparison"

    # Confidence: lower when no strong concept extracted
    confidence = 0.9 if subtype_concepts and subtype_concepts[0].confidence >= 0.8 else 0.7

    logger.debug(
        "frame_extractor: query=%r destination=%r concepts=%r geo=%r prefs=%r neg=%r",
        q, destination,
        [(c.label, c.confidence) for c in subtype_concepts],
        geo_hints, soft_prefs, negative_constraints,
    )

    return ExperienceFrame(
        literal_ask=q,
        normalized_ask=normalized,
        destination=destination,
        answer_mode=answer_mode,
        follow_up_mode=follow_up_mode,
        subtype_concepts=subtype_concepts,
        place_kind_hints=place_kind_hints,
        must_have=[],
        soft_preferences=soft_prefs,
        negative_constraints=negative_constraints,
        geography_hints=geo_hints,
        temporal_constraints=[],
        value_signals=value_signals,
        ambiguity_flags=ambiguity_flags,
        confidence=confidence,
        needs_provider_call=True,
    )


def _minimal_fallback_frame(
    user_query: str, destination: str, follow_up_mode: str
) -> ExperienceFrame:
    """Minimal frame used when extraction fails. Still enables provider search."""
    q = (user_query or "").strip()
    return ExperienceFrame(
        literal_ask=q,
        normalized_ask=q.lower(),
        destination=destination,
        answer_mode="place_list",
        follow_up_mode=follow_up_mode,
        subtype_concepts=[SubtypeConcept(label=q.lower()[:32], confidence=0.5, source="fallback")]
        if q
        else [],
        place_kind_hints=["food_and_drink"],
        confidence=0.4,
        needs_provider_call=True,
    )
