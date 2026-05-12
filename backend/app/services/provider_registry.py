"""Provider Registry v1 — Provider Policy Source of Truth.

This module is the single, canonical policy for every provider this app may
call at runtime.  Scattered per-adapter env checks consult this registry so
that:

- Provider activation policy lives in one place.
- Disallowed/quarantined providers cannot accidentally activate in production.
- Addable-card authority is explicit and centrally enforced.
- Future providers are added by registering an entry here + writing an adapter,
  not by editing random files.

Approved provider stack (production_allowed=True):
  - google_places  : canonical place identity / addable cards
  - anthropic      : reasoning, Concierge notes, card copy only
  - tavily         : optional research context only
  - yelp           : optional enrichment/corroboration only
  - openweather    : optional trip/weather ambience only

Active flight provider (production_allowed=True, search-only):
  - duffel_flights : live cash flight search via Duffel offer requests;
                     SEARCH ONLY — no booking/orders; gated by DUFFEL_API_KEY
                     + DUFFEL_FLIGHTS_ENABLED; DUFFEL_BOOKING_ENABLED must be 0.

Disabled (production_allowed=False):
  - ignav_flights  : Flights v1 schedule trust NOT certified (external schedule
                     times incorrect in production smoke test); disabled until
                     separately re-certified.
  - duffel_stays   : stays/hotel scaffold; quarantined pending re-approval
  - amadeus        : booking/OTA path; disabled
  - brave          : quarantined; use Tavily instead
  - serper         : quarantined; use Tavily instead
  - foursquare     : disabled; enrichment covered by Yelp
  - skyscanner_flights : pending; access rejected; remains disabled
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class ProviderRole(str, Enum):
    CANONICAL = "canonical"        # place identity + card minting (Google Places only)
    REASONING = "reasoning"        # LLM copy / notes; cannot mint cards (Anthropic)
    RESEARCH = "research"          # optional search context (Tavily)
    ENRICHMENT = "enrichment"      # optional corroboration, no card minting (Yelp)
    WEATHER = "weather"            # trip/weather context only (OpenWeather)
    LINK_OUT = "link_out"          # external link destination; no data ingestion
    DISABLED = "disabled"          # explicitly off; not approved for production
    QUARANTINED = "quarantined"    # previously scaffolded; suspended pending re-approval
    PENDING = "pending"            # preferred candidate; awaiting API key / access confirmation
    EVALUATION = "evaluation"      # provisional backup candidate; must pass validation before promotion


@dataclass(frozen=True)
class ProviderEntry:
    provider_id: str
    display_name: str
    role: ProviderRole
    required_env_vars: Tuple[str, ...] = field(default_factory=tuple)
    production_allowed: bool = False
    can_create_addable_cards: bool = False
    can_enrich_only: bool = False
    supported_verticals: Tuple[str, ...] = field(default_factory=tuple)
    cost_notes: str = ""


PROVIDER_REGISTRY: dict[str, ProviderEntry] = {
    # ── Approved providers ────────────────────────────────────────────────────
    "google_places": ProviderEntry(
        provider_id="google_places",
        display_name="Google Places",
        role=ProviderRole.CANONICAL,
        required_env_vars=("GOOGLE_PLACES_API_KEY",),
        production_allowed=True,
        can_create_addable_cards=True,
        can_enrich_only=False,
        supported_verticals=("restaurant", "attraction", "hotel", "place"),
        cost_notes="Pay-per-call; required for all addable place cards.",
    ),
    "anthropic": ProviderEntry(
        provider_id="anthropic",
        display_name="Anthropic Claude",
        role=ProviderRole.REASONING,
        required_env_vars=("ANTHROPIC_API_KEY",),
        production_allowed=True,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=(),
        cost_notes="Reasoning, Concierge notes, and card copy only. Cannot mint place cards.",
    ),
    "tavily": ProviderEntry(
        provider_id="tavily",
        display_name="Tavily Search",
        role=ProviderRole.RESEARCH,
        required_env_vars=("TAVILY_API_KEY",),
        production_allowed=True,
        can_create_addable_cards=False,
        can_enrich_only=True,
        supported_verticals=(),
        cost_notes="Optional research context only; free-tier limits apply.",
    ),
    "yelp": ProviderEntry(
        provider_id="yelp",
        display_name="Yelp",
        role=ProviderRole.ENRICHMENT,
        required_env_vars=("YELP_API_KEY",),
        production_allowed=True,
        can_create_addable_cards=False,
        can_enrich_only=True,
        supported_verticals=("restaurant", "attraction"),
        cost_notes="Optional enrichment/corroboration only; free base-plan limits apply.",
    ),
    "openweather": ProviderEntry(
        provider_id="openweather",
        display_name="OpenWeather",
        role=ProviderRole.WEATHER,
        required_env_vars=("OPENWEATHER_API_KEY",),
        production_allowed=True,
        can_create_addable_cards=False,
        can_enrich_only=True,
        supported_verticals=(),
        cost_notes="Trip/weather ambience context only.",
    ),
    # ── Disabled / quarantined providers ─────────────────────────────────────
    # These entries fail closed: no API calls, no mock data, no user-visible
    # rates or availability.  Re-approval in this registry is required before
    # any adapter can activate them.
    "duffel_flights": ProviderEntry(
        provider_id="duffel_flights",
        display_name="Duffel Flights",
        role=ProviderRole.LINK_OUT,
        required_env_vars=("DUFFEL_API_KEY", "DUFFEL_FLIGHTS_ENABLED"),
        production_allowed=True,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=("flight",),
        cost_notes=(
            "Active Flights v1 provider (search-only). "
            "Returns live Duffel offer data (route, times, price); NO booking/orders. "
            "Requires DUFFEL_API_KEY + DUFFEL_FLIGHTS_ENABLED=1 in backend env. "
            "DUFFEL_BOOKING_ENABLED must be 0 (or absent); booking is out of scope for v1. "
            "Key is server-side only; never NEXT_PUBLIC_."
        ),
    ),
    "duffel_stays": ProviderEntry(
        provider_id="duffel_stays",
        display_name="Duffel Stays",
        role=ProviderRole.QUARANTINED,
        required_env_vars=("DUFFEL_STAYS_API_KEY", "DUFFEL_STAYS_ENABLED"),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=("hotel",),
        cost_notes=(
            "Quarantined scaffold. Blocked on credentials. "
            "Explicit re-approval in this registry required before activation."
        ),
    ),
    "amadeus": ProviderEntry(
        provider_id="amadeus",
        display_name="Amadeus",
        role=ProviderRole.DISABLED,
        required_env_vars=(
            "AMADEUS_CLIENT_ID",
            "AMADEUS_CLIENT_SECRET",
            "AMADEUS_FLIGHTS_ENABLED",
        ),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=("flight", "hotel"),
        cost_notes=(
            "Disabled. Booking/OTA path not active. "
            "Explicit re-approval in this registry required before activation."
        ),
    ),
    "brave": ProviderEntry(
        provider_id="brave",
        display_name="Brave Search",
        role=ProviderRole.QUARANTINED,
        required_env_vars=("BRAVE_SEARCH_API_KEY",),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=(),
        cost_notes="Quarantined. Not in approved research stack. Use Tavily instead.",
    ),
    "serper": ProviderEntry(
        provider_id="serper",
        display_name="Serper",
        role=ProviderRole.QUARANTINED,
        required_env_vars=("SERPER_API_KEY",),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=(),
        cost_notes="Quarantined. Not in approved research stack. Use Tavily instead.",
    ),
    "foursquare": ProviderEntry(
        provider_id="foursquare",
        display_name="Foursquare",
        role=ProviderRole.DISABLED,
        required_env_vars=("FOURSQUARE_API_KEY",),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=(),
        cost_notes=(
            "Disabled. Enrichment use case is covered by Yelp. "
            "Explicit re-approval in this registry required before activation."
        ),
    ),
    # ── Flight provider candidates (scaffold / evaluation — not yet active) ───
    # Neither entry has production_allowed=True; both fail is_provider_active().
    # Promotion requires: (1) update this entry to production_allowed=True and
    # an active role, (2) confirm API key/access, (3) implement live adapter
    # call, (4) pass validation tests.  No live API calls are made at this stage.
    "skyscanner_flights": ProviderEntry(
        provider_id="skyscanner_flights",
        display_name="Skyscanner Live Prices",
        role=ProviderRole.PENDING,
        required_env_vars=("SKYSCANNER_API_KEY", "SKYSCANNER_FLIGHTS_ENABLED"),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=("flight",),
        cost_notes=(
            "Access rejected by Skyscanner. Remains PENDING/disabled. "
            "Ignav is the active Flights v1 provider. "
            "Re-evaluate Skyscanner only if access is granted in the future."
        ),
    ),
    "ignav_flights": ProviderEntry(
        provider_id="ignav_flights",
        display_name="Ignav Flights",
        role=ProviderRole.DISABLED,
        required_env_vars=("IGNAV_API_KEY", "IGNAV_FLIGHTS_ENABLED"),
        production_allowed=False,
        can_create_addable_cards=False,
        can_enrich_only=False,
        supported_verticals=("flight",),
        cost_notes=(
            "DISABLED. Schedule trust NOT certified: production smoke test revealed "
            "externally incorrect schedule times. Must not serve visible flight cards. "
            "Duffel is the active Flights v1 provider. Ignav may be re-evaluated only "
            "after a separate manual schedule-trust certification pass."
        ),
    ),
}


# ── Public accessors ──────────────────────────────────────────────────────────

def get_provider(provider_id: str) -> Optional[ProviderEntry]:
    """Return the registry entry for *provider_id*, or None if unknown."""
    return PROVIDER_REGISTRY.get(provider_id)


def is_production_allowed(provider_id: str) -> bool:
    """Return True only when the provider is explicitly approved for production."""
    entry = PROVIDER_REGISTRY.get(provider_id)
    return entry is not None and entry.production_allowed


def can_create_addable_cards(provider_id: str) -> bool:
    """Return True only for providers authorised to mint addable place cards.

    Google Places is the only provider that may return True.
    """
    entry = PROVIDER_REGISTRY.get(provider_id)
    return entry is not None and entry.can_create_addable_cards


def is_provider_active(provider_id: str) -> bool:
    """Return True only when a provider is production-allowed AND not disabled/quarantined.

    Callers (adapter factories, provider-selection functions) should gate on
    this before attempting to build a live provider instance.
    """
    entry = PROVIDER_REGISTRY.get(provider_id)
    if entry is None:
        return False
    return (
        entry.production_allowed
        and entry.role not in (
            ProviderRole.DISABLED,
            ProviderRole.QUARANTINED,
            ProviderRole.PENDING,
            ProviderRole.EVALUATION,
        )
    )


# Frozenset of provider IDs authorised to create addable place cards.
# Any addable-card flow should assert its provider_id is in this set.
ADDABLE_CARD_PROVIDERS: FrozenSet[str] = frozenset(
    pid for pid, entry in PROVIDER_REGISTRY.items() if entry.can_create_addable_cards
)


__all__ = [
    "ADDABLE_CARD_PROVIDERS",
    "PROVIDER_REGISTRY",
    "ProviderEntry",
    "ProviderRole",
    "can_create_addable_cards",
    "get_provider",
    "is_production_allowed",
    "is_provider_active",
]
