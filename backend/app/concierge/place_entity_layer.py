"""Verified Place Entity Layer — converts raw Google provider results to PlaceEntity records.

Hard gates (any failure → reject, log reason):
  - Missing Google place id
  - Non-OPERATIONAL business status (when status field is present)
  - Missing Google Maps URI
  - Duplicate stable identity keys

NOT rejected for:
  - Broad Google types (e.g., "establishment", "bar" instead of "brewery")
  - Lower rating than another candidate
  - Google type is "bar" when query is for "brewery"
  - Subtype not in any local enum

Deduplication uses stable identity keys (pid:, gmaps:, name_addr:) — the same
scheme as the existing _card_identity_keys() in routes/ai.py.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from app.concierge.provider_executor import ProviderQueryResult

logger = logging.getLogger(__name__)

_OPERATIONAL = "OPERATIONAL"

# Non-venue Google types — these indicate the result is a geographic/admin entity,
# not an actual venue. We reject them to avoid address/city results in card pool.
_NON_VENUE_TYPES = frozenset(
    {
        "country",
        "administrative_area_level_1",
        "administrative_area_level_2",
        "administrative_area_level_3",
        "locality",
        "sublocality",
        "neighborhood",
        "postal_code",
        "political",
        "route",
        "transit_station",
        "bus_station",
        "train_station",
        "subway_station",
        "airport",
        "parking",
        "car_rental",
        "car_wash",
        "gas_station",
        "atm",
        "bank",
        "pharmacy",
        "hospital",
        "doctor",
        "dentist",
        "police",
        "post_office",
        "school",
        "university",
        "library",
    }
)


@dataclass
class PlaceEntity:
    """Canonical verified place record from the Google provider."""

    place_id: str
    name: str
    formatted_address: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    business_status: str
    google_maps_uri: str
    types: List[str]
    primary_type: Optional[str]
    rating: Optional[float]
    user_rating_count: Optional[int]
    price_level: Optional[str]
    website_uri: Optional[str]
    # Identity keys for deduplication (same scheme as routes/ai.py)
    identity_keys: FrozenSet[str] = field(default_factory=frozenset)
    # Which retrieval query returned this entity
    source_query: str = ""


def _normalize_text(text: str) -> str:
    """Lowercase, remove accents, collapse whitespace — for identity keys."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_text = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _build_identity_keys(
    place_id: Optional[str],
    maps_uri: Optional[str],
    name: Optional[str],
    address: Optional[str],
) -> FrozenSet[str]:
    keys: Set[str] = set()
    if place_id:
        keys.add(f"pid:{_normalize_text(place_id)}")
    if maps_uri:
        keys.add(f"gmaps:{_normalize_text(maps_uri)}")
    n = _normalize_text(name or "")
    a = _normalize_text(address or "")
    if n and a:
        clean_a = re.sub(r"[^a-z0-9]+", " ", a).strip()
        clean_n = re.sub(r"[^a-z0-9]+", " ", n).strip()
        if clean_n and clean_a:
            keys.add(f"name_addr:{clean_n}|{clean_a}")
    return frozenset(keys)


def _parse_coords(location: Any) -> Tuple[Optional[float], Optional[float]]:
    if not isinstance(location, dict):
        return None, None
    return location.get("latitude"), location.get("longitude")


def _extract_name(raw: Dict[str, Any]) -> Optional[str]:
    display_name = raw.get("displayName")
    if isinstance(display_name, dict):
        return (display_name.get("text") or "").strip() or None
    if isinstance(display_name, str):
        return display_name.strip() or None
    return None


def _is_non_venue(types: List[str]) -> bool:
    types_lower = {(t or "").lower() for t in types}
    return bool(types_lower & _NON_VENUE_TYPES) and not (
        types_lower & {"restaurant", "food", "bar", "bar_and_grill",
                       "establishment", "point_of_interest"}
    )


@dataclass
class EntityLayerStats:
    raw_candidate_count: int = 0
    operational_rejected: int = 0
    missing_place_id_rejected: int = 0
    missing_maps_uri_rejected: int = 0
    non_venue_rejected: int = 0
    duplicate_rejected: int = 0
    verified_entity_count: int = 0


def build_entity_layer(
    results: List[ProviderQueryResult],
    prior_identity_keys: Optional[FrozenSet[str]] = None,
) -> Tuple[List[PlaceEntity], EntityLayerStats]:
    """Convert raw provider results into deduplicated, verified PlaceEntity records.

    Args:
        results: Raw ProviderQueryResult list from execute_fanout().
        prior_identity_keys: Identity keys of already-shown cards — deduped out.

    Returns:
        (entities, stats) — verified entities and rejection statistics.
    """
    stats = EntityLayerStats()
    prior_keys: FrozenSet[str] = prior_identity_keys or frozenset()
    seen_keys: Set[str] = set()
    entities: List[PlaceEntity] = []

    for result in results:
        for raw in result.places:
            stats.raw_candidate_count += 1

            # Gate 1: must have a Google place id
            place_id = (raw.get("id") or "").strip()
            if not place_id:
                stats.missing_place_id_rejected += 1
                logger.debug("entity_layer: reject missing_place_id name=%s", _extract_name(raw))
                continue

            # Gate 2: business status must be explicitly OPERATIONAL
            status = (raw.get("businessStatus") or "").upper()
            if status != _OPERATIONAL:
                stats.operational_rejected += 1
                logger.debug(
                    "entity_layer: reject non_operational_or_missing_status place_id=%s status=%s",
                    place_id, status or "<missing>",
                )
                continue

            # Gate 3: must have Google Maps URI
            maps_uri = (raw.get("googleMapsUri") or "").strip()
            if not maps_uri:
                stats.missing_maps_uri_rejected += 1
                logger.debug("entity_layer: reject missing_maps_uri place_id=%s", place_id)
                continue

            name = _extract_name(raw)
            if not name:
                stats.missing_place_id_rejected += 1  # no name = unusable
                continue

            types = [str(t) for t in (raw.get("types") or [])]
            primary_type = raw.get("primaryType") or (types[0] if types else None)

            # Gate 4: reject known non-venue types (geographic/admin entities)
            if _is_non_venue(types):
                stats.non_venue_rejected += 1
                logger.debug(
                    "entity_layer: reject non_venue place_id=%s name=%s types=%s",
                    place_id, name, types[:3],
                )
                continue

            address = (raw.get("formattedAddress") or "").strip() or None
            lat, lng = _parse_coords(raw.get("location"))
            rating = raw.get("rating")
            review_count = raw.get("userRatingCount")
            price_level = raw.get("priceLevel")
            website = (raw.get("websiteUri") or "").strip() or None

            identity_keys = _build_identity_keys(place_id, maps_uri, name, address)

            # Gate 5: dedup against already-seen keys (prior pool + current batch)
            if identity_keys & prior_keys:
                stats.duplicate_rejected += 1
                continue
            if identity_keys & seen_keys:
                stats.duplicate_rejected += 1
                continue

            seen_keys |= identity_keys

            entity = PlaceEntity(
                place_id=place_id,
                name=name,
                formatted_address=address,
                lat=lat,
                lng=lng,
                business_status=status,
                google_maps_uri=maps_uri,
                types=types,
                primary_type=primary_type,
                rating=rating,
                user_rating_count=review_count,
                price_level=price_level,
                website_uri=website,
                identity_keys=identity_keys,
                source_query=result.query,
            )
            entities.append(entity)

    stats.verified_entity_count = len(entities)

    logger.info(
        "entity_layer: raw=%d verified=%d rejected="
        "(no_id=%d non_op=%d no_uri=%d non_venue=%d dup=%d)",
        stats.raw_candidate_count,
        stats.verified_entity_count,
        stats.missing_place_id_rejected,
        stats.operational_rejected,
        stats.missing_maps_uri_rejected,
        stats.non_venue_rejected,
        stats.duplicate_rejected,
    )

    return entities, stats
