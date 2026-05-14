"""Duffel Flights adapter — Flights v1 search-only.

Activation requirements (all must be met):
  1. ``duffel_flights`` in provider_registry.py with production_allowed=True (done).
  2. ``DUFFEL_API_KEY`` set in backend env (server-side only; never NEXT_PUBLIC_).
  3. ``DUFFEL_FLIGHTS_ENABLED=1`` set in backend env.
  4. ``DUFFEL_BOOKING_ENABLED`` must NOT be set to a truthy value; booking/orders
     are out of scope for v1 and this adapter never creates Duffel orders.

Schedule trust certification gate:
  - ``DUFFEL_SCHEDULE_TRUST_CERTIFIED=1`` must be set before visible cards appear.
  - Default is uncertified: the adapter still calls Duffel and runs the full trust
    gate, but returns UNAVAILABLE with reason ``"Duffel schedule trust certification
    pending"`` rather than showing cards.
  - Set to ``1`` only after running one live smoke test with ``DUFFEL_DEBUG=true``
    and manually verifying all accepted-offer details (route, times, price) are
    correct.  Mirrors the Ignav safety gate.

Debug logging:
  - Set ``DUFFEL_DEBUG=true`` in backend env to log compact non-sensitive summaries
    of accepted mapped offers (offer index, price, outbound/return route, flight
    numbers, timestamps, stops).  Never logs API keys, passenger PII, or full
    payloads.  First ``_DEBUG_LOG_MAX_OFFERS`` accepted offers are logged at INFO
    level so they surface in production Railway logs without requiring global
    LOG_LEVEL=DEBUG.  Turn off after certification.

Direct-flight default (v1):
  - Each Duffel slice is sent with ``max_connections: 0`` to request direct
    flights only.  Stops filtering may be exposed as a user-selectable option
    in a future slice; do not remove this default without a product decision.

Response contract:
  - Returns ``FlightItineraryOffer`` rows (canonical provider shape).
  - booking_link is SEARCH_REDIRECT (Google Flights link-out) when a valid
    URL can be built for the query; falls back to UNAVAILABLE otherwise.
    The link is a search redirect only — no orders, no checkout.
  - Never returns mock/fabricated data; fails closed on any error.
  - ``live_cached_status`` is always ``LIVE``.
  - ``ai_score`` is None in v1.

Round-trip support:
  - When ``req.return_date`` is set, two slices are sent in the offer request.
  - Both outbound and return legs are mapped and returned in each offer.

Trust gate (applied per offer before mapping):
  - Each slice must have at least one segment.
  - First segment of each slice must have marketing_carrier iata_code + flight_number.
  - Each segment must have 3-letter IATA origin/destination airports.
  - Each segment must have departing_at and arriving_at timestamps.
  - total_amount must be parseable as a positive float.
  - Outbound leg origin/destination/date must match the search request exactly.
  - Return leg origin/destination/date must match the search request exactly.
  - Offers failing any check are skipped and logged at WARNING level.
  - If ALL offers fail the trust gate, returns UNAVAILABLE with reason.

No booking:
  - DUFFEL_BOOKING_ENABLED env var is checked; if truthy, it is IGNORED because
    booking is out of scope for v1.  The adapter never calls Duffel orders endpoints.
  - booking_link is SEARCH_REDIRECT (Google Flights) when a valid URL can be built,
    otherwise UNAVAILABLE.  Google Flights is a search redirect, NOT a booking path.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from app.contracts.flights import FlightSourceStatus
from app.contracts.flight_offer import (
    BookingLinkType,
    FlightBookingLink,
    FlightItineraryOffer,
    FlightOfferLeg,
    FlightPrice,
    FlightSegment,
    LiveCachedStatus,
    TripType,
)
from app.models.search import FlightSearchRequest
from app.services.flights_provider import FlightProviderResult
from app.services.google_flights_link import build_google_flights_url, get_city_group_token

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.duffel.com"
_OFFER_REQUESTS_PATH = "/air/offer_requests"
_HTTP_TIMEOUT_SECONDS = 12.0
_SUPPLIER_TIMEOUT_MS = 9000
_MAX_OFFERS_TO_MAP = 20
_DEBUG_LOG_MAX_OFFERS = 5
_TRUTHY = {"1", "true", "yes", "on"}

_UNAVAILABLE_BOOKING_LINK = FlightBookingLink(
    url="",
    link_type=BookingLinkType.UNAVAILABLE,
    provider_name="duffel_flights",
)


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


def _log_accepted_offer(offer: "FlightItineraryOffer", idx: int) -> None:
    """Log a compact non-sensitive summary of an accepted offer for manual cert review.

    Never logs API keys, passenger PII, full payloads, or tokens.
    """
    def _leg_summary(leg: "FlightOfferLeg") -> str:
        segs = ", ".join(
            f"{s.flight_number} {s.origin}→{s.destination} "
            f"dep={s.departure_time[:16]} arr={s.arrival_time[:16]} {s.duration_minutes}min"
            for s in leg.segments
        )
        return f"{leg.origin}→{leg.destination} stops={leg.stops} [{segs}]"

    ret_part = ""
    if offer.return_leg is not None:
        ret_part = f" | return: {_leg_summary(offer.return_leg)}"

    logger.info(
        "[duffel.accepted] #%d price=%s%s outbound: %s%s",
        idx + 1,
        offer.price.total_amount,
        offer.price.currency,
        _leg_summary(offer.outbound_leg),
        ret_part,
    )


def _now_utc_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        v = value
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _parse_iso_duration_minutes(value: Optional[str]) -> int:
    """Parse ISO 8601 duration string like PT8H30M → 510 minutes."""
    if not value or not value.startswith("PT"):
        return 0
    s, h, m, n = value[2:], 0, 0, ""
    for ch in s:
        if ch.isdigit():
            n += ch
        elif ch == "H":
            h, n = int(n or 0), ""
        elif ch == "M":
            m, n = int(n or 0), ""
    return (h * 60) + m


def _parse_positive_float(value: Any) -> Optional[float]:
    try:
        f = float(value)
        return f if f > 0 else None
    except Exception:
        return None


def _map_segment(seg: Dict[str, Any]) -> Optional[FlightSegment]:
    """Map a single Duffel segment dict to FlightSegment; returns None on trust failure."""
    origin_code = (seg.get("origin") or {}).get("iata_code") or ""
    dest_code = (seg.get("destination") or {}).get("iata_code") or ""
    if len(origin_code) != 3 or len(dest_code) != 3:
        return None

    marketing = seg.get("marketing_carrier") or {}
    carrier_iata = (marketing.get("iata_code") or "").upper()
    flight_num_raw = str(seg.get("marketing_carrier_flight_number") or "").strip()
    if not carrier_iata or not flight_num_raw:
        return None
    flight_number = f"{carrier_iata}{flight_num_raw}"

    operating = seg.get("operating_carrier") or {}
    airline_name = (
        operating.get("name")
        or marketing.get("name")
        or operating.get("iata_code")
        or carrier_iata
        or ""
    )
    if not airline_name:
        return None

    dep_str = seg.get("departing_at") or ""
    arr_str = seg.get("arriving_at") or ""
    dep_dt = _parse_iso_dt(dep_str)
    arr_dt = _parse_iso_dt(arr_str)
    if dep_dt is None or arr_dt is None:
        return None

    duration_raw = _parse_iso_duration_minutes(seg.get("duration"))
    if duration_raw <= 0:
        # Derive from timestamps when Duffel omits segment duration.
        delta = (arr_dt - dep_dt).total_seconds()
        duration_raw = max(int(delta // 60), 1)

    try:
        return FlightSegment(
            airline=airline_name,
            flight_number=flight_number,
            origin=origin_code.upper(),
            destination=dest_code.upper(),
            departure_time=dep_str,
            arrival_time=arr_str,
            duration_minutes=duration_raw,
            cabin_class=None,
        )
    except ValueError:
        return None


def _map_slice_to_leg(sl: Dict[str, Any]) -> Optional[FlightOfferLeg]:
    """Map one Duffel slice (outbound or return) to FlightOfferLeg."""
    segments_raw = sl.get("segments") or []
    if not segments_raw:
        return None

    mapped_segs: List[FlightSegment] = []
    for seg in segments_raw:
        s = _map_segment(seg)
        if s is None:
            return None  # any unmappable segment fails the whole leg
        mapped_segs.append(s)

    first_seg = mapped_segs[0]
    last_seg = mapped_segs[-1]

    leg_duration = _parse_iso_duration_minutes(sl.get("duration"))
    if leg_duration <= 0:
        dep_dt = _parse_iso_dt(first_seg.departure_time)
        arr_dt = _parse_iso_dt(last_seg.arrival_time)
        if dep_dt and arr_dt:
            leg_duration = max(int((arr_dt - dep_dt).total_seconds() // 60), 1)
        else:
            leg_duration = sum(s.duration_minutes for s in mapped_segs)

    stops = max(len(mapped_segs) - 1, 0)
    try:
        return FlightOfferLeg(
            origin=first_seg.origin,
            destination=last_seg.destination,
            departure_time=first_seg.departure_time,
            arrival_time=last_seg.arrival_time,
            duration_minutes=leg_duration,
            stops=stops,
            segments=tuple(mapped_segs),
        )
    except ValueError:
        return None


def _map_offer(
    offer: Dict[str, Any],
    *,
    req: FlightSearchRequest,
    fetched_at: str,
    booking_link: Optional[FlightBookingLink] = None,
) -> Optional[FlightItineraryOffer]:
    """Map a Duffel offer dict to FlightItineraryOffer; returns None on any trust failure."""
    slices = offer.get("slices") or []
    is_round_trip = req.return_date is not None
    expected_slices = 2 if is_round_trip else 1
    if len(slices) < expected_slices:
        logger.warning("[duffel.trust] offer %s: expected %d slices, got %d",
                       offer.get("id"), expected_slices, len(slices))
        return None

    outbound_leg = _map_slice_to_leg(slices[0])
    if outbound_leg is None:
        logger.warning("[duffel.trust] offer %s: outbound leg failed trust gate", offer.get("id"))
        return None

    return_leg: Optional[FlightOfferLeg] = None
    if is_round_trip:
        return_leg = _map_slice_to_leg(slices[1])
        if return_leg is None:
            logger.warning("[duffel.trust] offer %s: return leg failed trust gate", offer.get("id"))
            return None

    # Route/date validation — confirm segment data matches what the user requested.
    # A provider could return a different route or date; we must reject such offers
    # rather than display a wrong-route card as if it matched the search.
    req_origin = (req.origin or "").upper()
    req_dest = (req.destination or "").upper()

    if outbound_leg.origin != req_origin or outbound_leg.destination != req_dest:
        logger.warning(
            "[duffel.trust] offer %s: outbound route mismatch (got %s→%s, want %s→%s)",
            offer.get("id"), outbound_leg.origin, outbound_leg.destination, req_origin, req_dest,
        )
        return None

    outbound_dep_dt = _parse_iso_dt(outbound_leg.departure_time)
    if outbound_dep_dt is None or outbound_dep_dt.date() != req.departure_date:
        logger.warning(
            "[duffel.trust] offer %s: outbound departure date mismatch (got %s, want %s)",
            offer.get("id"),
            outbound_dep_dt.date() if outbound_dep_dt else None,
            req.departure_date,
        )
        return None

    if is_round_trip and return_leg is not None:
        if return_leg.origin != req_dest or return_leg.destination != req_origin:
            logger.warning(
                "[duffel.trust] offer %s: return route mismatch (got %s→%s, want %s→%s)",
                offer.get("id"), return_leg.origin, return_leg.destination, req_dest, req_origin,
            )
            return None
        return_dep_dt = _parse_iso_dt(return_leg.departure_time)
        if return_dep_dt is None or return_dep_dt.date() != req.return_date:
            logger.warning(
                "[duffel.trust] offer %s: return departure date mismatch (got %s, want %s)",
                offer.get("id"),
                return_dep_dt.date() if return_dep_dt else None,
                req.return_date,
            )
            return None

    amount = _parse_positive_float(offer.get("total_amount"))
    if amount is None:
        logger.warning("[duffel.trust] offer %s: missing or zero total_amount", offer.get("id"))
        return None
    currency = (offer.get("total_currency") or "USD").upper()

    origin = (req.origin or "").upper()
    destination = (req.destination or "").upper()
    if not origin or not destination:
        return None

    provider_offer_id = offer.get("id")
    provider_offer_id = str(provider_offer_id) if provider_offer_id else None

    try:
        return FlightItineraryOffer(
            provider="duffel_flights",
            fetched_at=fetched_at,
            provider_offer_id=provider_offer_id,
            live_cached_status=LiveCachedStatus.LIVE,
            trip_type=TripType.ROUND_TRIP if is_round_trip else TripType.ONE_WAY,
            origin=origin,
            destination=destination,
            departure_date=req.departure_date.isoformat(),
            return_date=req.return_date.isoformat() if req.return_date else None,
            passengers=max(int(req.passengers or 1), 1),
            cabin_class=req.cabin_class or "economy",
            outbound_leg=outbound_leg,
            return_leg=return_leg,
            price=FlightPrice(
                currency=currency,
                total_amount=amount,
                taxes_fees_included=None,
            ),
            booking_link=booking_link if booking_link is not None else _UNAVAILABLE_BOOKING_LINK,
            ai_score=None,
        )
    except (ValueError, TypeError) as exc:
        logger.warning("[duffel.trust] offer %s: contract violation: %s", offer.get("id"), exc)
        return None


class DuffelFlightProvider:
    """Duffel Flights search-only provider.

    Calls Duffel's offer-request endpoint and maps results to the canonical
    FlightItineraryOffer contract.  Never creates Duffel orders.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        http_client: Optional["httpx.Client"] = None,
        certified: bool = False,
    ) -> None:
        if not api_key:
            raise ValueError("DuffelFlightProvider requires non-empty api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/") or _DEFAULT_BASE_URL
        self._client = http_client
        self._certified = certified

    def _get_http(self) -> "httpx.Client":
        if self._client is None:
            if httpx is None:  # pragma: no cover
                raise RuntimeError("httpx is not installed")
            self._client = httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS)
        return self._client

    def _build_slices(self, req: FlightSearchRequest) -> List[Dict[str, Any]]:
        # City-group scope note: Duffel search always uses the single primary
        # airport (req.origin / req.destination). Multi-airport arrays from the
        # city resolver improve Google Flights link-out scope (mode-3 token) but
        # do NOT expand Duffel search into a cross-product — that would require
        # a bounded multi-slice strategy with hard caps and per-offer trust gates
        # that are out of scope for v1. Do not change without a product decision.
        origin = (req.origin or "").upper()
        destination = (req.destination or "").upper()
        slices: List[Dict[str, Any]] = [
            {
                "origin": origin,
                "destination": destination,
                "departure_date": req.departure_date.isoformat(),
                "max_connections": 0,
            }
        ]
        if req.return_date is not None:
            slices.append(
                {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": req.return_date.isoformat(),
                    "max_connections": 0,
                }
            )
        return slices

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        origin = (req.origin or "").upper()
        destination = (req.destination or "").upper()
        if not origin or not destination:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="missing origin or destination IATA",
            )
        if len(origin) != 3 or len(destination) != 3:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason=f"malformed IATA codes: {origin!r}, {destination!r}",
            )

        payload: Dict[str, Any] = {
            "data": {
                "slices": self._build_slices(req),
                "passengers": [
                    {"type": "adult"}
                    for _ in range(max(int(req.passengers or 1), 1))
                ],
                "cabin_class": req.cabin_class or "economy",
            }
        }

        try:
            resp = self._get_http().post(
                f"{self._base_url}{_OFFER_REQUESTS_PATH}",
                params={
                    "return_offers": "true",
                    "supplier_timeout": str(_SUPPLIER_TIMEOUT_MS),
                },
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Duffel-Version": "v2",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        except Exception as exc:
            logger.warning("[duffel.transport_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"transport error: {exc}",
            )

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.warning("[duffel.http_error] status=%d", resp.status_code)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"duffel http {resp.status_code}",
            )

        try:
            outer = resp.json() or {}
        except Exception as exc:
            logger.warning("[duffel.parse_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"json parse error: {exc}",
            )

        data = outer.get("data") or {}
        offers_raw = data.get("offers") or []
        if not isinstance(offers_raw, list):
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason="duffel response missing offers list",
            )
        if not offers_raw:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="duffel returned zero offers",
            )

        fetched_at = _now_utc_iso()

        # Build Google Flights search link-out for all offers from this query.
        # SEARCH_REDIRECT is a search redirect only — never a booking endpoint.
        # Use city-group tokens (mode 3) when the request covers multiple airports.
        _origin_group = get_city_group_token(origin) if len(req.all_origins) > 1 else None
        _dest_group = get_city_group_token(destination) if len(req.all_destinations) > 1 else None
        _google_url = build_google_flights_url(
            origin=origin,
            destination=destination,
            departure_date=req.departure_date,
            return_date=req.return_date,
            passengers=max(int(req.passengers or 1), 1),
            origin_group_token=_origin_group,
            destination_group_token=_dest_group,
        )
        _search_booking_link: FlightBookingLink = (
            FlightBookingLink(
                url=_google_url,
                link_type=BookingLinkType.SEARCH_REDIRECT,
                provider_name="google_flights",
            )
            if _google_url
            else _UNAVAILABLE_BOOKING_LINK
        )

        rows: List[FlightItineraryOffer] = []
        for offer in offers_raw[:_MAX_OFFERS_TO_MAP]:
            mapped = _map_offer(offer, req=req, fetched_at=fetched_at, booking_link=_search_booking_link)
            if mapped is not None:
                rows.append(mapped)

        if not rows:
            return FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[],
                reason="all duffel offers failed trust gate",
            )

        # Debug logging — compact non-sensitive summaries for manual cert review.
        # Logged at INFO so they surface in production Railway logs without
        # requiring global LOG_LEVEL=DEBUG. Never logs API key, PII, or payload.
        if _truthy(os.environ.get("DUFFEL_DEBUG")):
            logger.info("[duffel.debug] accepted-offer certification logging enabled")
            for idx, offer in enumerate(rows[:_DEBUG_LOG_MAX_OFFERS]):
                _log_accepted_offer(offer, idx)

        # Certification gate — prevent cards from surfacing until accepted payloads
        # are manually verified.  Set DUFFEL_SCHEDULE_TRUST_CERTIFIED=1 only after
        # running one live smoke test with DUFFEL_DEBUG=true and confirming all
        # accepted offer details (route, times, price) are correct.
        if not self._certified:
            logger.warning(
                "[duffel.cert] %d valid offer(s) mapped but DUFFEL_SCHEDULE_TRUST_CERTIFIED "
                "not set; returning UNAVAILABLE until schedule trust is manually verified",
                len(rows),
            )
            return FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[],
                reason="Duffel schedule trust certification pending",
            )

        return FlightProviderResult(status=FlightSourceStatus.OK, rows=rows)


def duffel_enabled_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    """Return True only when DUFFEL_API_KEY and DUFFEL_FLIGHTS_ENABLED are both set."""
    e = env if env is not None else os.environ  # type: ignore[assignment]
    return _truthy(e.get("DUFFEL_FLIGHTS_ENABLED")) and bool(e.get("DUFFEL_API_KEY"))


def duffel_certified_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    """Return True when DUFFEL_SCHEDULE_TRUST_CERTIFIED is truthy.

    Must be set to 1 only after running one live smoke test with DUFFEL_DEBUG=true
    and manually confirming all accepted offer details (route, times, price) are
    correct.  Default is False — prevents visible cards until certified.
    """
    e = env if env is not None else os.environ  # type: ignore[assignment]
    return _truthy(e.get("DUFFEL_SCHEDULE_TRUST_CERTIFIED"))


def build_duffel_provider_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[DuffelFlightProvider]:
    """Build a DuffelFlightProvider from env vars; returns None when not enabled."""
    e = env if env is not None else os.environ  # type: ignore[assignment]
    if not duffel_enabled_from_env(e):
        return None
    return DuffelFlightProvider(
        api_key=e.get("DUFFEL_API_KEY") or "",
        base_url=e.get("DUFFEL_BASE_URL") or _DEFAULT_BASE_URL,
        certified=duffel_certified_from_env(e),
    )
