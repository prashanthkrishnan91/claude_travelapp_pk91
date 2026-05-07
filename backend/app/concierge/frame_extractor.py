"""ExperienceFrame extractor — open-vocabulary deterministic phase.

Converts a natural-language place ask into a structured ExperienceFrame without
relying on a closed category enum. The primary subtype concept is extracted from
the user's literal words, not matched against a fixed list.

Venue-head preservation: geography hints, ambience/style preferences, value
signals, and ambiguity flags are detected first, and the tokens that produced
them are excluded from primary-concept candidates. This ensures, for example,
"waterfront breweries" yields venue=brewery + modifier=waterfront (not the
other way around).

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
    r"good\s+for|great\s+for|perfect\s+for|ideal\s+for|nice\s+for|"
    r"except|without|unless)\b",
    re.IGNORECASE,
)

# Location-anchored modifier phrases. After modifier-split, the trailing clause
# may contain a real-world location anchor like "Fulton Street", "the West Loop",
# "Riverwalk", etc. We capture these as location_modifiers so the retrieval
# planner can include them in queries.
#
# Pattern 1: capitalized multi-word location names (e.g., "Fulton Street" typed
# with capitals as originally written by PR-2 tests).
_LOCATION_ANCHOR_RE = re.compile(
    r"\b(?:in|on|near|around|by|along|close\s+to|next\s+to)\s+"
    r"(?:the\s+)?"
    r"(?P<loc>[A-Z][A-Za-z'\-]+(?:\s+[A-Z][A-Za-z'\-]+){0,4})"
)

# Known street/district suffix tokens — used to identify lowercase location
# names like "fulton street" or "river north" typed without capital letters.
_STREET_SUFFIXES = frozenset({
    "street", "st", "avenue", "ave", "boulevard", "blvd", "road", "rd",
    "lane", "ln", "drive", "dr", "way", "place", "court", "row", "alley",
    "loop", "market", "plaza", "square", "district", "park", "parkway", "pkwy",
    "promenade", "walk", "path", "trail", "esplanade", "embankment",
    "north", "south", "east", "west",
})

# Pattern 2: lowercase/mixed location names identified by known street suffixes.
# Captures "fulton street", "river north", "west loop", "fulton market", etc.
_LOCATION_ANCHOR_LOWERCASE_RE = re.compile(
    r"\b(?:in|on|near|around|by|along|close\s+to|next\s+to)\s+"
    r"(?:the\s+)?"
    r"(?P<loc>[a-z][a-z'\-]+(?:\s+[a-z][a-z'\-]+){0,3}"
    r"(?:\s+(?:street|st|avenue|ave|boulevard|blvd|road|rd|lane|ln|drive|dr|"
    r"way|place|court|row|alley|loop|market|plaza|square|district|park|parkway|"
    r"promenade|walk|path|trail|esplanade|embankment|north|south|east|west)))",
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

# Tokens that look like geo/style modifiers and should NOT win primary-concept
# extraction over a real venue noun. If the user asks "waterfront breweries",
# the venue head ("brewery") must beat the modifier ("waterfront").
_GEO_MODIFIER_TOKENS = frozenset({
    "waterfront", "riverwalk", "riverview", "lakefront", "rooftop",
    "outdoor", "indoor", "patio", "terrace", "river", "lake", "ocean",
    "sea", "bay", "harbor", "harbour", "coast", "coastline", "beachfront",
    "waterside", "view", "views", "shoreline", "marina", "pier",
    "downtown", "uptown", "midtown",
})

_AMBIENCE_MODIFIER_TOKENS = frozenset({
    "romantic", "intimate", "cozy", "cosy", "casual", "quiet", "lively",
    "trendy", "hip", "fancy", "upscale", "luxury", "luxe", "premium",
    "modern", "elegant", "classic", "lovely", "charming", "vibrant",
    "buzzing", "busy", "energetic", "relaxed", "peaceful", "serene",
    "instagrammable",
})

# Nouns that act as soft preference descriptors in compound travel phrases
# ("hidden gem", "local secret", "neighborhood haunt") and must NOT win as the
# venue head when an explicit venue noun is present.  When the user asks for
# "hidden gem restaurants", the venue head is "restaurant", not "gem".
_TRAVEL_PREFERENCE_NOUNS: frozenset = frozenset({
    "gem", "gems",
    "find", "finds",
    "haunt", "haunts",
    "sleeper", "sleepers",
    "discovery", "discoveries",
    "treasure", "treasures",
    "jewel", "jewels",
    "diamond", "diamonds",
})

_USE_CASE_TOKENS = frozenset({
    "reading", "studying", "working", "remote", "wifi", "laptop",
    "groups", "group", "couples", "solo", "kids", "children",
    "dates", "anniversary", "celebration", "birthday",
})

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

# Patterns that signal a hidden-gem / local-favorite / low-profile preference.
# Detected from query text to complement suppressed_preference_nouns (which only
# catches nouns like "gem"/"haunt"). Covers phrasing like "local favorite", "underrated",
# "off the beaten path", "neighborhood" + qualifier.
_HIDDEN_GEM_CONTEXT_PATTERN = re.compile(
    r"\bhidden\s+gem\b"
    r"|\blocal\s+(?:favorite|favourite|gem|secret|haunt|find|spot)\b"
    r"|\bneighborhood\s+(?:haunt|gem|find|favorite|favourite|spot)\b"
    r"|\bunderrated\b"
    r"|\bunder[-\s](?:the[-\s])?radar\b"
    r"|\boff[-\s](?:the[-\s])?beaten\b"
    r"|\bundiscovered\b"
    r"|\blow[-\s]?profile\b",
    re.I,
)

# Detects view/outdoor preference when NOT already captured as a geo_hint.
# Used to add "view_or_geo" to normalized_soft_preferences for queries like
# "taprooms with a view" where bare "view" doesn't match _GEO_PATTERNS.
_VIEW_PREFERENCE_PATTERN = re.compile(
    r"\bwith\s+(?:a\s+)?views?\b"
    r"|\brooftop\b"
    r"|\bpatio\b"
    r"|\bterrace\b"
    r"|\boutdoor(?:\s+seating)?\b",
    re.I,
)

# Temporal preference patterns — mapped to canonical labels.
_TEMPORAL_PATTERNS: List[tuple] = [
    (re.compile(r"\blate[-\s]?night\b|\bopen\s+late\b|\bafter\s+hours?\b|\bnight\s+owl\b", re.I), "late_night"),
]

# Temporal qualifier words that act as time modifiers in compound phrases
# ("late night izakayas") and must NOT win as the primary venue concept.
# These are the individual tokens that make up temporal phrases — they are
# excluded from concept extraction via _classified_modifier_tokens so that
# "late night izakayas" yields venue_head="izakaya", not "late".
_TEMPORAL_QUALIFIER_TOKENS: frozenset = frozenset({
    "late", "night", "midnight", "after", "hours", "hour",
    "early", "morning", "dawn", "dusk", "evening",
    "open", "owl", "hours",
})

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
    (re.compile(r"\bwaterfront\b|\bwater\s*view\b|\briver\s*view\b|\blake\s*view\b|\bocean\s*view\b"
                r"|\bwith\s+a\s+view\b|\ba\s+view\b|\bviews?\b", re.I),
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

    # Geography (abstract: "waterfront", "riverwalk", "rooftop", etc.)
    geography_hints: List[str] = field(default_factory=list)

    # Concrete location modifiers parsed from the user's query
    # (e.g., "Fulton Street", "West Loop", "Riverwalk").
    location_modifiers: List[str] = field(default_factory=list)

    # Use-case / occasion signals ("reading", "groups", "date night")
    use_cases: List[str] = field(default_factory=list)

    # Temporal / value
    temporal_constraints: List[str] = field(default_factory=list)
    value_signals: List[str] = field(default_factory=list)

    # Ambiguity flags — attributes explicitly asked for that cannot be structurally verified
    ambiguity_flags: List[str] = field(default_factory=list)

    # Did the open-class place-ask detector fire for this query?
    # When True, semantic retrieval is eligible even if legacy intent is GENERAL.
    open_class_place_detected: bool = False

    # Frame finalization telemetry (backend-only — never surfaced to UI).
    # Preference modifier nouns that were found in the query but suppressed so
    # a concrete venue head could win (e.g. "gem" from "hidden gem restaurants").
    suppressed_preference_nouns: List[str] = field(default_factory=list)

    # Normalized soft preferences (canonical labels) derived from suppressed_preference_nouns,
    # soft_preferences, temporal_constraints, and explicit query patterns.
    # Used by retrieval_planner for preference-aware query generation and by ranker
    # for preference-fit scoring. Examples: "hidden_gem", "romantic", "late_night", "view_or_geo".
    # Backend-only telemetry — never surfaced to UI.
    normalized_soft_preferences: List[str] = field(default_factory=list)

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


def _extract_location_modifiers(query: str, destination: str) -> List[str]:
    """Capture concrete location anchors like "Fulton Street" or "West Loop".

    Looks for phrases following location prepositions in the user's query.
    Handles both capitalized ("Fulton Street") and lowercase ("fulton street")
    input — the second via street-suffix detection. The destination is excluded
    so we don't echo the trip city back as a modifier.
    """
    if not query:
        return []
    dest_lower = (destination or "").strip().lower()
    found: List[str] = []
    seen: set = set()

    def _accept(loc: str) -> None:
        if not loc:
            return
        loc_lower = loc.lower()
        if dest_lower and (loc_lower == dest_lower or loc_lower in dest_lower):
            return
        if loc_lower in _GEO_MODIFIER_TOKENS:
            return
        if loc_lower in seen:
            return
        seen.add(loc_lower)
        # Normalize to title-case for consistent downstream use.
        found.append(loc.title())

    # Pattern 1: capitalized location names
    for match in _LOCATION_ANCHOR_RE.finditer(query):
        _accept(match.group("loc").strip())

    # Pattern 2: lowercase names with known street/district suffixes.
    # Skip if already found via pattern 1 to avoid duplicates.
    for match in _LOCATION_ANCHOR_LOWERCASE_RE.finditer(query):
        _accept(match.group("loc").strip())

    return found


def _extract_use_cases(query: str) -> List[str]:
    """Detect use-case / occasion tokens ("reading", "groups", "dates")."""
    if not query:
        return []
    tokens = _tokenize_words(query)
    found: List[str] = []
    seen: set = set()
    for tok in tokens:
        if tok in _USE_CASE_TOKENS and tok not in seen:
            found.append(tok)
            seen.add(tok)
    return found


def _classified_modifier_tokens(
    query: str,
    geo_hints: List[str],
    soft_prefs: List[str],
    value_signals: List[str],
    use_cases: List[str],
    temporal_constraints: Optional[List[str]] = None,
) -> set:
    """Return the set of tokens already classified as modifiers.

    Any token in this set must NOT be selected as the primary venue concept
    (otherwise "waterfront breweries" picks "waterfront" as the venue head,
    or "late night izakayas" picks "late" as the venue head).
    """
    classified: set = set()
    classified |= _GEO_MODIFIER_TOKENS
    classified |= _AMBIENCE_MODIFIER_TOKENS
    classified |= _USE_CASE_TOKENS
    classified |= _TRAVEL_PREFERENCE_NOUNS
    classified |= _TEMPORAL_QUALIFIER_TOKENS
    # Add geo hint labels themselves (already lowercase)
    for hint in geo_hints:
        for tok in _tokenize_words(hint):
            classified.add(tok)
    for pref in soft_prefs:
        for tok in _tokenize_words(pref.replace("_", " ")):
            classified.add(tok)
    for sig in value_signals:
        for tok in _tokenize_words(sig.replace("_", " ")):
            classified.add(tok)
    for uc in use_cases:
        classified.add(uc.lower())
    for tc in (temporal_constraints or []):
        for tok in _tokenize_words(tc.replace("_", " ")):
            classified.add(tok)
    return classified


def _find_suppressed_preference_nouns(query: str) -> List[str]:
    """Return travel-preference nouns found in the query's main clause.

    These nouns were classified as soft-preference modifiers (not venue heads)
    by _classified_modifier_tokens, so they never win primary-concept extraction
    when a concrete venue noun is present.  Returned for telemetry only — the
    list is backend-internal and never surfaced in UI.
    """
    q = query.strip()
    parts = _MODIFIER_SPLIT_RE.split(q, maxsplit=1)
    main_clause = parts[0].strip()
    tokens = _tokenize_words(main_clause)
    found: List[str] = []
    seen: set = set()
    for tok in tokens:
        if tok in _TRAVEL_PREFERENCE_NOUNS and tok not in seen:
            found.append(tok)
            seen.add(tok)
    return found


def _extract_temporal_constraints(query: str) -> List[str]:
    """Detect temporal preferences in a user query (late night, open late, etc.)."""
    if not query:
        return []
    constraints: List[str] = []
    for pattern, label in _TEMPORAL_PATTERNS:
        if pattern.search(query):
            constraints.append(label)
    return constraints


def _extract_normalized_soft_preferences(
    query: str,
    suppressed_preference_nouns: List[str],
    soft_prefs: List[str],
    temporal_constraints: List[str],
    geo_hints: List[str],
) -> List[str]:
    """Normalize raw preference signals into canonical labels for retrieval and ranking.

    Returns deduplicated canonical labels:
    - hidden_gem: suppressed preference nouns present OR hidden/local/underrated patterns
    - romantic: soft_pref "romantic" detected
    - intimate: soft_pref "intimate" detected
    - late_night: temporal constraint "late_night" detected
    - view_or_geo: view/outdoor pattern detected AND not already covered by geo_hints

    Backend-only — never surfaced to UI.
    """
    result: List[str] = []
    seen: set = set()

    def _add(label: str) -> None:
        if label not in seen:
            result.append(label)
            seen.add(label)

    # hidden_gem: from suppressed preference nouns OR explicit hidden/local/underrated patterns
    if suppressed_preference_nouns or _HIDDEN_GEM_CONTEXT_PATTERN.search(query):
        _add("hidden_gem")

    # romantic: from existing soft_prefs detection
    if "romantic" in soft_prefs:
        _add("romantic")

    # intimate: from soft_prefs
    if "intimate" in soft_prefs:
        _add("intimate")

    # late_night: from temporal constraints
    if "late_night" in temporal_constraints:
        _add("late_night")

    # view_or_geo: only when not already covered by geo_hints (which handle waterfront/rooftop/etc.)
    if not geo_hints and _VIEW_PREFERENCE_PATTERN.search(query):
        _add("view_or_geo")

    return result


def _extract_primary_concepts(query: str, modifier_tokens: Optional[set] = None) -> List[SubtypeConcept]:
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

    # Remove tokens that are already classified as geo/ambience/use-case modifiers.
    # This is the venue-head preservation step: "waterfront breweries" must yield
    # concept=brewery, not concept=waterfront.
    if modifier_tokens:
        venue_candidates = [t for t in meaningful if t not in modifier_tokens]
    else:
        venue_candidates = list(meaningful)

    # Remove generic place nouns (restaurant, bar, etc.) to keep the concept
    # But keep them if they ARE the only meaningful token
    non_generic = [t for t in venue_candidates if t not in _GENERIC_PLACE_NOUNS]
    if not non_generic and venue_candidates:
        non_generic = venue_candidates[:1]  # keep first generic if nothing else
    if not non_generic and meaningful:
        # All meaningful tokens were modifier-classified — fall back to the
        # original meaningful tokens minus generic nouns. This keeps concept
        # extraction working for queries like "waterfront" alone.
        non_generic = [t for t in meaningful if t not in _GENERIC_PLACE_NOUNS] or meaningful[:1]

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
    location_modifiers = _extract_location_modifiers(q, destination)
    use_cases = _extract_use_cases(q)
    temporal_constraints = _extract_temporal_constraints(q)

    # Build the set of tokens already classified as modifiers, so they are
    # excluded from primary-concept candidates (venue-head preservation).
    modifier_tokens = _classified_modifier_tokens(
        q, geo_hints, soft_prefs, value_signals, use_cases,
        temporal_constraints=temporal_constraints,
    )

    # Open-vocabulary concept extraction (core of this module)
    subtype_concepts = _extract_primary_concepts(q, modifier_tokens=modifier_tokens)
    place_kind_hints = _derive_place_kind_hints(subtype_concepts)

    # Frame finalization telemetry: track which travel-preference nouns were
    # found in the query and suppressed so a concrete venue head could win.
    suppressed_preference_nouns = _find_suppressed_preference_nouns(q)

    # Normalized soft preferences: canonical labels for retrieval and ranking.
    normalized_soft_preferences = _extract_normalized_soft_preferences(
        q, suppressed_preference_nouns, soft_prefs, temporal_constraints, geo_hints,
    )

    # Normalized ask: lowercase, remove extra whitespace
    normalized = re.sub(r"\s+", " ", q.lower()).strip()

    # Answer mode heuristics
    answer_mode = "place_list"
    if re.search(r"\b(best one|single best|top pick|top choice|one recommendation)\b", q, re.I):
        answer_mode = "single_best"
    elif re.search(r"\b(compare|versus|vs\.?|difference between)\b", q, re.I):
        answer_mode = "comparison"

    # Open-class place ask detection runs against the literal query plus the
    # extracted concept; it allows queries with unfamiliar venue nouns
    # (izakaya, dessert bars, record stores) to enter semantic retrieval
    # without pre-listing them in a closed eligibility bucket.
    open_class_detected = is_open_class_place_ask(q, subtype_concepts)

    # Confidence: lower when no strong concept extracted
    confidence = 0.9 if subtype_concepts and subtype_concepts[0].confidence >= 0.8 else 0.7

    logger.debug(
        "frame_extractor: query=%r destination=%r concepts=%r geo=%r locs=%r prefs=%r "
        "neg=%r use_cases=%r temporal=%r open_class=%s suppressed_pref_nouns=%r normalized_soft_prefs=%r",
        q, destination,
        [(c.label, c.confidence) for c in subtype_concepts],
        geo_hints, location_modifiers, soft_prefs, negative_constraints,
        use_cases, temporal_constraints, open_class_detected,
        suppressed_preference_nouns, normalized_soft_preferences,
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
        location_modifiers=location_modifiers,
        use_cases=use_cases,
        temporal_constraints=temporal_constraints,
        value_signals=value_signals,
        ambiguity_flags=ambiguity_flags,
        open_class_place_detected=open_class_detected,
        suppressed_preference_nouns=suppressed_preference_nouns,
        normalized_soft_preferences=normalized_soft_preferences,
        confidence=confidence,
        needs_provider_call=True,
    )


def _minimal_fallback_frame(
    user_query: str, destination: str, follow_up_mode: str
) -> ExperienceFrame:
    """Minimal frame used when extraction fails. Still enables provider search."""
    q = (user_query or "").strip()
    fallback_concepts = (
        [SubtypeConcept(label=q.lower()[:32], confidence=0.5, source="fallback")]
        if q
        else []
    )
    return ExperienceFrame(
        literal_ask=q,
        normalized_ask=q.lower(),
        destination=destination,
        answer_mode="place_list",
        follow_up_mode=follow_up_mode,
        subtype_concepts=fallback_concepts,
        place_kind_hints=["food_and_drink"],
        open_class_place_detected=is_open_class_place_ask(q, fallback_concepts),
        confidence=0.4,
        needs_provider_call=True,
    )


# ── Open-class place-ask detector ────────────────────────────────────────────

# Negative triggers — phrases that signal the query is NOT a venue-recommendation
# ask. These keep flights, packing, weather, currency, itinerary, and similar
# requests out of the semantic retrieval path.
_NON_PLACE_NEGATIVE_PATTERNS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\bflight(s)?\b",
        r"\bairfare\b",
        r"\bairline(s)?\b",
        r"\bairport(s)?\s+(transfer|shuttle|pickup)\b",
        r"\bweather\b",
        r"\bforecast\b",
        r"\bclimate\b",
        r"\btemperature\b",
        r"\bwhat\s+to\s+pack\b",
        r"\bpacking\s+list\b",
        r"\bpacking\s+tips\b",
        r"\bvisa\b",
        r"\bpassport\b",
        r"\bcurrency\b",
        r"\bexchange\s+rate\b",
        r"\btip(s|ping)\b\s+(etiquette|culture|amount|in\b)",
        r"\blanguage\s+phrase(s)?\b",
        r"\btranslat(e|ion)\b",
        r"\bpoints?\s+(redemption|transfer|earn)\b",
        r"\bmiles?\s+(redemption|transfer|earn)\b",
        r"\baward\s+flight\b",
        r"\btransfer\s+partner\b",
        r"\bbudget\s+(plan|breakdown|estimate|calculator)\b",
        r"\bitinerary\s+(edit|edit\s+to|update|move|swap)\b",
        r"\bplan\s+(my\s+)?day\b",
        r"\bnumber\s+of\s+days\b",
        r"\bhow\s+(many|long)\b.*\b(days|hours)\b",
    ]
]

# Positive triggers — open-class place-recommendation indicators. These do NOT
# require a known venue noun; they recognize the shape of a place ask.
_PLACE_ASK_POSITIVE_TRIGGERS: List[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # "best/top/great X", "X spots/places/joints", "any good X"
        r"\b(best|top|great|good|nice|favorite|favourite|popular|famous)\b\s+\w+",
        r"\bany\s+good\b",
        r"\bwhere\s+(to|can\s+i|should\s+i)\s+(eat|drink|grab|find|hang|go|shop|visit)\b",
        r"\b(recommend|suggestion|suggestions|recommendations|ideas)\b",
        r"\b(eat|dine|drink|grab\s+(a|some)|hang\s+out|go\s+out)\b",
        r"\b(hidden\s+gem|local\s+favorite|local\s+secret|off\s+the\s+beaten)\b",
        r"\b(things|stuff)\s+to\s+(do|see|try)\b",
        r"\b(spot|spots|joint|joints|hangout|hangouts|hang\-?outs)\b",
        r"\bplaces?\s+(to|for)\b",
        r"\bvenues?\b",
        # Plural noun ending — "izakayas", "tea houses", "dessert bars",
        # "record stores", "arcades", "speakeasies", etc.
        r"\b[a-z]{3,}(?:s|es|ies|ays)\b\s*(?:in|on|near|around|by|along|at|$)",
        # Single venue noun + locator
        r"\b\w{3,}\s+(in|on|near|around|by|along|at)\s+\w+",
    ]
]


def is_open_class_place_ask(
    query: str,
    subtype_concepts: Optional[List[SubtypeConcept]] = None,
) -> bool:
    """Detect whether ``query`` is an open-language place-recommendation ask.

    The goal is high recall on real-world venue / activity asks while keeping
    out clearly non-place requests like flights, packing, weather, budget math,
    or generic itinerary edits.

    This is intentionally permissive on positive matches because the downstream
    Semantic Retrieval v1 pipeline still verifies every card via Google Places.
    Returning ``True`` here only means "let semantic retrieval try"; it does not
    mint cards on its own.
    """
    if not query:
        return False
    q = query.strip()
    if not q:
        return False

    # Hard negatives: clear non-place asks must never enter semantic retrieval
    for pat in _NON_PLACE_NEGATIVE_PATTERNS:
        if pat.search(q):
            return False

    # Positive triggers: any match qualifies the query as a place-like ask
    for pat in _PLACE_ASK_POSITIVE_TRIGGERS:
        if pat.search(q):
            return True

    # If the extracted concept survived modifier filtering and is not pure
    # filler / single-letter junk, treat it as a place-like ask.
    if subtype_concepts:
        primary = subtype_concepts[0]
        label = (primary.label or "").strip().lower()
        if (
            label
            and primary.confidence >= 0.7
            and primary.source != "fallback"
            and label not in _FILLER_WORDS
            and label not in _GEO_MODIFIER_TOKENS
            and label not in _AMBIENCE_MODIFIER_TOKENS
            and len(label) >= 3
        ):
            return True

    return False
