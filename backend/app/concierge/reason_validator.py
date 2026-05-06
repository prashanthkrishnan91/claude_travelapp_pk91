"""ReasonValidator — validates LLM-generated concierge notes before use.

Rejects notes that:
- Claim unsupported location modifiers as confirmed facts
- Mention waterfront/view/quiet/romantic/Michelin/awards/price/hours unless evidence supports
- Are generic/repetitive boilerplate
- Expose internal metric names or debug fields
- Fabricate facts not present in the evidence bundle
- Contradict explicit caveats in the evidence bundle

Used by BatchedReasonBuilder before accepting LLM output. On rejection the
caller falls back to the deterministic SafeReasonBuilder output.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.concierge.frame_extractor import ExperienceFrame
from app.concierge.ranker import MinimalEvidenceBundle


# ── Banned claim patterns ─────────────────────────────────────────────────────

# Claims about physical attributes we cannot verify from Google structured fields.
_UNSUPPORTED_ATTRIBUTE_RE = re.compile(
    # NOTE: Compound view/front terms use \s+ (one or more spaces) to avoid
    # false-matching Chicago neighborhood names like "Lakeview" (no space).
    # The standalone compound forms (waterfront, riverwalk, lakefront) are kept
    # as-is and handled via entity-name context in _evidence_supports_claim.
    r"\b(waterfront|water\s+front|riverwalk|river\s+walk|lakefront|lake\s+front"
    r"|water\s+views?|river\s+views?|lake\s+views?|ocean\s+views?|sea\s+views?"
    r"|rooftop\s+views?|stunning\s+views?|beautiful\s+views?|panoramic"
    r"|michelin|bib\s+gourmand|james\s+beard|award[-\s]winning"
    r"|quiet\s+atmosphere|peaceful\s+atmosphere|romantic\s+atmosphere"
    r"|intimate\s+atmosphere|cozy\s+atmosphere|guaranteed\s+quiet"
    r"|perfect\s+for\s+(?:dates?|romance|couples?)"
    r"|opening\s+hours?|open\s+(?:until|from|daily|monday|tuesday|wednesday"
    r"|thursday|friday|saturday|sunday)"
    r"|reservations?\s+(?:required|recommended|available)"
    r"|price\s+range|per\s+person|budget-friendly|upscale\s+dining"
    r"|\$+\d|\bpricey\b|\bexpensive\b|\bcheap\b|\baffordable\b)\b",
    re.IGNORECASE,
)

# Internal metric / debug field names that must never appear in user-visible text.
_INTERNAL_FIELD_RE = re.compile(
    r"\b(subtype_fit|geo_fit|rank_score|quality_signal|evidence_strength"
    r"|diversity_signal|popularity_signal|trip_context_fit|value_fit"
    r"|source_query|place_entity|provider_result|entity_stats|ranker_stats"
    r"|raw_candidate|verified_entity|trust_gate|pipeline_version"
    r"|semantic_retrieval|reason_source|deterministic_safe|batched_grounded"
    r"|OPERATIONAL|PGRST|place_id|provider_place_id|google_places_api)\b",
    re.IGNORECASE,
)

# Generic boilerplate phrases that convey no useful information.
_GENERIC_BOILERPLATE_RE = re.compile(
    r"(?:"
    r"popular\s+(?:place|spot|restaurant|bar)\s+with\s+(?:many|lots\s+of)\s+reviews"
    r"|great\s+(?:food|drinks?|service)\s+and\s+(?:great|good|nice)\s+(?:atmosphere|vibe|ambiance)"
    r"|well[-\s]known\s+(?:spot|place|restaurant)\s+in\s+\w+"
    r"|good\s+choice\s+for\s+(?:your|a)\s+(?:trip|visit|night\s+out)"
    r"|worth\s+(?:a\s+)?visit"
    r"|definitely\s+(?:check\s+(?:it\s+)?out|worth\s+(?:a\s+)?visit)"
    r"|highly\s+recommended\s+(?:by|for)\s+(?:locals?|tourists?|visitors?)"
    r"|top\s+pick\s+(?:for|because|among|in)\b"
    r"|worth\s+considering\s+for\s+your\s+trip"
    r"|a\s+well[-\s]regarded\s+local\s+pick"
    r"|a\s+great\s+(?:spot|place|choice)\s+for\s+\w+\s+lovers?"
    r"|perfect\s+for\s+(?:\w+\s+)?enthusiasts?"
    r"|\bstrong\s+local\s+following\b"
    r"|\bconsistent\s+quality\b"
    r"|\bchicago\s+institution\b"
    r"|\bconsistent\s+crowd\s+draw\b"
    r"|\bstrong\s+flagship\s+choice\b"
    r"|\bestablished\s+reputation\b"
    r")",
    re.IGNORECASE,
)

# Odd address-fragment-as-reason patterns.
# Catches things like "Strong izakaya match in Lower Level."
_ADDRESS_FRAGMENT_RE = re.compile(
    r"\b(?:in|at|on|near)\s+"
    r"(?:lower\s+level|upper\s+level|ground\s+floor|ground\s+level"
    r"|lobby\s+level|basement\s+level|mezzanine|concourse level"
    r"|terminal\s+\w|gate\s+\w|room\s+\d+|suite\s+\d+)\b",
    re.IGNORECASE,
)

# Distance/direction claims we cannot verify.
# Note: "directly on X street" is NOT included here because it is handled
# by the location modifier contradiction check, which also permits
# "not directly on X street" as an honest caveat.
_DISTANCE_CLAIM_RE = re.compile(
    r"\b(\d+\s*(?:feet|ft|meters?|metres?|miles?|km|blocks?)\s+"
    r"(?:from|away|north|south|east|west|of)"
    r"|steps?\s+(?:from|away\s+from))",
    re.IGNORECASE,
)

# Repetitive concept match phrasing (pre-existing bad pattern from v1)
_REPETITIVE_MATCH_RE = re.compile(
    r"\b(Strong|Good|Great)\s+\w+\s+match\s+in\s+"
    r"(?:Lower\s+Level|Upper\s+Level|Ground\s+Floor|Lobby|Basement|Mezzanine|Concourse)\b",
    re.IGNORECASE,
)

# Generic "Strong/Good/Great X match in Y" boilerplate.
# These phrases convey no verified information and MUST be rejected whether
# produced by the deterministic path or the LLM. Examples:
#   "Strong izakaya match in Chicago."
#   "Good brewery match in Milwaukee."
#   "Strong brewery match in Chicago, near waterfront."
_GENERIC_MATCH_IN_RE = re.compile(
    r"\b(Strong|Good|Great|Solid|Excellent)\s+\w+\s+match\b",
    re.IGNORECASE,
)

# Template-shaped "Verified {category} with {rating}★ across {N} reviews." pattern.
# This is a fill-in-the-blank note that provides no card-specific differentiation.
# It does NOT vary by card and must be rejected from both deterministic and LLM paths.
# Examples:
#   "Verified Brewery with 4.5★ across 1,234 Google reviews."
#   "Verified Japanese Restaurant with 4.3★ across 210 reviews."
#   "Verified Bar with 4.1★."
_VERIFIED_TEMPLATE_RE = re.compile(
    r"\bVerified\s+\w[\w\s]*\s+with\s+\d[\d.]*\s*★",
    re.IGNORECASE,
)

# Name-only + rating templates: the entire note is just "{Name} — {rating}★ ..."
# with no additional content. These repeat only fields already visible on the card.
#
# Examples that MUST be rejected:
#   "The Izakaya — 4.8★ from 1,028 reviews."
#   "Goose Island Taproom on Fulton Street — 4.8★ from 1,159 reviews."
#   "Izakaya Shinya on North Avenue — 4.6★ from 1,143 reviews."
#   "Half Acre — 4.7★."
#
# Examples that must NOT be rejected (additional content beyond name+rating):
#   "Half Acre on Lincoln Ave — 4.7★. No waterfront proximity confirmed from address."
#   "Izakaya Shinya — 4.6★. Not directly on Fulton Street — nearest match in the area."
#
# The regex anchors to the end-of-string ($) to catch ONLY complete notes with
# no further sentences. A note with additional clauses after the period does not match.
_NAME_RATING_ONLY_RE = re.compile(
    r"""^
    [A-Za-z0-9''’\-&, ()]{3,120}     # name, possibly with "on Street"
    \s*[—–\-]{1,3}\s*                       # em-dash or hyphen separator
    \d{1,2}[\d.]*\s*★                       # rating★
    (?:                                      # optional review count suffix
        \s+from\s+[\d,]+\s+(?:reviews?|Google\s+reviews?)
        |\s+with\s+[\d,]+\s+(?:reviews?|Google\s+reviews?)
        |\s+across\s+[\d,]+\s+(?:reviews?|Google\s+reviews?)
        |\s*\([\d,]+\s+reviews?\)
    )?
    \s*\.?\s*$                               # period and end — no further sentences
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)


def validate_reason(
    reason: str,
    frame: ExperienceFrame,
    evidence: MinimalEvidenceBundle,
) -> Tuple[bool, str]:
    """Validate a concierge note before it is shown to the user.

    Args:
        reason: The candidate reason string (from LLM or deterministic path).
        frame: ExperienceFrame for the current query.
        evidence: MinimalEvidenceBundle for the entity this reason describes.

    Returns:
        (is_valid, rejection_reason) — is_valid=True means the note passes.
        rejection_reason is empty when valid.
    """
    if not reason or not reason.strip():
        return False, "empty_reason"

    # 1. Address-fragment-only reasons (e.g., "Strong izakaya match in Lower Level")
    if _ADDRESS_FRAGMENT_RE.search(reason):
        return False, "address_fragment_as_location"

    if _REPETITIVE_MATCH_RE.search(reason):
        return False, "match_in_non_neighborhood_fragment"

    # 1b. Generic "Strong/Good X match" boilerplate — rejected regardless of city.
    # These notes provide no grounded information (city name is not evidence).
    if _GENERIC_MATCH_IN_RE.search(reason):
        return False, "generic_match_boilerplate"

    # 1c. "Verified {category} with {rating}★" template — fill-in-the-blank, no differentiation.
    if _VERIFIED_TEMPLATE_RE.search(reason):
        return False, "verified_category_template"

    # 1d. Pure name+rating templates: notes whose ENTIRE content is just
    # "{Name} — {rating}★ from {N} reviews." with no further insight.
    # These repeat only fields already visible on the card (title + meta line).
    # Notes that add a caveat or second sentence (honest modifier disclosure,
    # geo note, etc.) do NOT match this regex and are allowed.
    if _NAME_RATING_ONLY_RE.match(reason):
        return False, "name_rating_only_template"

    # 2. Unsupported physical attribute claims.
    # Allow when (a) evidence bundle confirms it, or (b) the term appears
    # inside an explicit negation/caveat ("not confirmed", "cannot be verified").
    unsupported_match = _UNSUPPORTED_ATTRIBUTE_RE.search(reason)
    if unsupported_match:
        claim = unsupported_match.group(0)
        if not _evidence_supports_claim(claim, evidence):
            if not _claim_is_negated(reason, unsupported_match.start()):
                return False, f"unsupported_attribute_claim:{claim.lower()}"

    # 3. Internal metric / debug fields leaked into user text
    internal_match = _INTERNAL_FIELD_RE.search(reason)
    if internal_match:
        return False, f"internal_field_in_reason:{internal_match.group(0).lower()}"

    # 4. Generic boilerplate
    if _GENERIC_BOILERPLATE_RE.search(reason):
        return False, "generic_boilerplate"

    # 5. Distance claims (we cannot verify distance)
    if _DISTANCE_CLAIM_RE.search(reason):
        return False, "unverifiable_distance_claim"

    # 6. Location modifier contradiction: if evidence says modifier not confirmed,
    #    the reason must not claim the entity IS on that modifier.
    location_modifiers = getattr(frame, "location_modifiers", []) or []
    for modifier in location_modifiers[:1]:
        mod_flag = f"location_modifier_not_confirmed:{modifier}"
        if mod_flag in evidence.uncertainty_flags:
            # Check if reason falsely claims the modifier is confirmed
            if _reason_claims_modifier_confirmed(reason, modifier):
                return False, f"claimed_unconfirmed_location_modifier:{modifier}"

    return True, ""


def _evidence_supports_claim(claim: str, evidence: MinimalEvidenceBundle) -> bool:
    """Return True when the evidence bundle contains a fact supporting this claim.

    Checks structured_facts AND the entity's verified Google name/address (listing context).
    This allows notes to safely mention 'Riverwalk' when the verified Google listing
    name itself contains 'Riverwalk' — it is not a fabricated scenic claim, it is a
    literal listing name fact. The same logic applies to any term in the verified name.

    A note claiming "riverfront views" or "waterfront seating" is still blocked
    because those tokens ('views', 'seating') are not in the entity name/address.
    """
    claim_lower = claim.lower()
    tokens = [tok for tok in re.findall(r"[a-z]+", claim_lower) if len(tok) > 4]
    if not tokens:
        return False
    # Check structured_facts (existing behavior)
    for fact in evidence.structured_facts:
        fact_tokens = set(re.findall(r"[a-z]+", fact.lower()))
        if all(tok in fact_tokens for tok in tokens):
            return True
    # Check entity's verified name and address (listing context).
    # Uses word-boundary tokenization so "riverwalk" in the name does NOT
    # accidentally support the token "river" from a "river view" claim.
    entity = getattr(evidence, "entity", None)
    if entity is not None:
        name_tokens = set(re.findall(r"[a-z]+", (getattr(entity, "name", "") or "").lower()))
        addr_tokens = set(re.findall(r"[a-z]+", (getattr(entity, "formatted_address", "") or "").lower()))
        combined = name_tokens | addr_tokens
        if all(tok in combined for tok in tokens):
            return True
    return False


# Negation/caveat patterns that indicate the term is being DENIED, not asserted.
_NEGATION_CONTEXT_RE = re.compile(
    r"\b(not confirmed|not verified|cannot be|cannot verify|is not|isn't|"
    r"doesn't|don't|no\s+(?:waterfront|view|river|lake|water|riverwalk)|"
    r"never|without|unconfirmed|not available|not in|not directly|"
    r"not confirmed|cannot be structurally)\b",
    re.IGNORECASE,
)


def _claim_is_negated(reason: str, match_start: int) -> bool:
    """Return True when the matched attribute appears inside a negation/caveat.

    Checks both before and after the match position within an 80-char window.
    This allows phrases like "waterfront setting is not confirmed" and
    "requested waterfront cannot be verified" to pass validation.
    """
    window_start = max(0, match_start - 80)
    window_end = min(len(reason), match_start + 80)
    context = reason[window_start:window_end]
    return bool(_NEGATION_CONTEXT_RE.search(context))


def _reason_claims_modifier_confirmed(reason: str, modifier: str) -> bool:
    """Return True when the reason asserts the place IS on/at the given modifier."""
    reason_lower = reason.lower()
    mod_lower = modifier.lower()
    # Patterns like "on Fulton Street", "located on Fulton", "in Fulton Market"
    # but NOT "not directly on Fulton" or "not on Fulton"
    patterns = [
        rf"\b(?:on|at|in|along)\s+{re.escape(mod_lower)}",
        rf"\blocated\s+(?:on|in|at)\s+{re.escape(mod_lower)}",
    ]
    # Also reject if modifier appears as if confirmed without a "not" guard
    mod_tokens = mod_lower.split()
    if mod_tokens:
        first_tok = re.escape(mod_tokens[0])
        # Look for the modifier token in the reason without a preceding "not"
        match = re.search(rf"\b{first_tok}\b", reason_lower)
        if match:
            # Check if there's a negation within a few words before it
            prefix = reason_lower[max(0, match.start() - 20):match.start()]
            if re.search(r"\b(not|isn't|doesn't|no|never|without)\b", prefix):
                return False
            return True
    return False


def validate_reasons_batch(
    reasons: "dict[str, str]",
    frame: ExperienceFrame,
    evidence_by_key: "dict[str, MinimalEvidenceBundle]",
) -> "dict[str, tuple[bool, str]]":
    """Validate a batch of reasons. Returns dict of key → (is_valid, rejection)."""
    results = {}
    for key, reason in reasons.items():
        ev = evidence_by_key.get(key)
        if ev is None:
            results[key] = (False, "no_evidence_bundle")
            continue
        results[key] = validate_reason(reason, frame, ev)
    return results
