"""Ignav Flights adapter — Flights v1 live cash prices + booking links.

Ignav is a REST API for live flight fares and booking deep-links.
Docs: https://ignav.com/docs

Activation requirements (all must be met):
  1. ``ignav_flights`` in provider_registry.py with production_allowed=True (done).
  2. ``IGNAV_API_KEY`` set in backend env (server-side only; never NEXT_PUBLIC_).
  3. ``IGNAV_FLIGHTS_ENABLED=1`` set in backend env.

Response contract:
  - Returns ``FlightItineraryOffer`` rows (canonical provider shape).
  - Never returns mock/fabricated data; fails closed on any error.
  - ``live_cached_status`` is always ``LIVE`` (real-time Ignav call).
  - ``ai_score`` is None in v1 (no scoring pipeline wired yet).

Latency strategy:
  - One search call (one-way or round-trip endpoint).
  - Parallel booking-link fetches for the top ``_MAX_BOOKING_LINK_FETCHES``
    results using ThreadPoolExecutor.
  - Total budget: _HTTP_TIMEOUT_SECONDS + _BOOKING_LINK_TIMEOUT_SECONDS ≈ 20 s.
    Acceptable for flight search; tuned below.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
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
from app.services.flights_provider import FlightProvider, FlightProviderResult
from app.models.search import FlightSearchRequest

logger = logging.getLogger(__name__)

_IGNAV_BASE_URL = "https://ignav.com/api/fares"
_HTTP_TIMEOUT_SECONDS = 15.0
_BOOKING_LINK_TIMEOUT_SECONDS = 5.0
_MAX_OFFERS = 10           # cap results returned to frontend
_MAX_BOOKING_LINK_FETCHES = 5   # parallel limit for booking-link calls
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def ignav_enabled_from_env() -> bool:
    """True only when both the feature flag AND API key are present."""
    flag = os.environ.get("IGNAV_FLIGHTS_ENABLED", "").strip()
    key = os.environ.get("IGNAV_API_KEY", "").strip()
    return bool(flag and flag.lower() in _TRUTHY and key)


class IgnavFlightProvider:
    """Live adapter for Ignav Flights (cash prices + booking links).

    Implements the ``FlightProvider`` protocol.  Never raises — all transport
    failures are translated to ``FlightProviderResult(status=ERROR|UNAVAILABLE)``.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _IGNAV_BASE_URL,
        http_client: Optional["httpx.Client"] = None,
    ) -> None:
        if not api_key:
            raise ValueError("IgnavFlightProvider requires a non-empty api_key")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = http_client

    def _get_http(self) -> "httpx.Client":
        if self._client is None:
            if httpx is None:  # pragma: no cover
                raise RuntimeError("httpx is not installed")
            self._client = httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS)
        return self._client

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Api-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # Internal: Ignav API calls
    # ------------------------------------------------------------------

    def _fetch_search(self, req: FlightSearchRequest) -> Dict[str, Any]:
        """Call Ignav one-way or round-trip search endpoint."""
        origins = req.all_origins
        destinations = req.all_destinations
        if not origins or not destinations:
            raise ValueError("origin and destination IATA codes are required")

        origin = origins[0].upper()
        destination = destinations[0].upper()
        is_round_trip = req.return_date is not None

        body: Dict[str, Any] = {
            "origin": origin,
            "destination": destination,
            "departure_date": req.departure_date.isoformat(),
            "adults": max(int(req.passengers or 1), 1),
            "cabin_class": req.cabin_class or "economy",
        }
        if is_round_trip:
            body["return_date"] = req.return_date.isoformat()  # type: ignore[union-attr]

        endpoint = "round-trip" if is_round_trip else "one-way"
        url = f"{self._base_url}/{endpoint}"

        logger.info(
            "[ignav] search %s origin=%s dest=%s dep=%s ret=%s adults=%d cabin=%s",
            endpoint, origin, destination,
            req.departure_date, req.return_date, body["adults"], body["cabin_class"],
        )

        resp = self._get_http().post(url, json=body, headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def _fetch_booking_links(self, ignav_id: str, adults: int) -> List[Dict[str, Any]]:
        """Fetch booking links for a single itinerary.  Returns empty list on failure."""
        url = f"{self._base_url}/booking-links"
        body = {"ignav_id": ignav_id, "adults": adults}
        try:
            client = httpx.Client(timeout=_BOOKING_LINK_TIMEOUT_SECONDS) if self._client is None else self._client
            resp = client.post(url, json=body, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            return data.get("booking_options", []) or []
        except Exception as exc:
            logger.warning("[ignav] booking_links failed for %s: %s", ignav_id, exc)
            return []

    # ------------------------------------------------------------------
    # Internal: mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_time(utc_str: Optional[str], local_str: Optional[str]) -> str:
        """Return best available ISO 8601 time string; prefers UTC."""
        val = utc_str or local_str or ""
        if not val:
            raise ValueError("no departure or arrival time available")
        # Ensure it ends with Z if it looks UTC
        if val.endswith("+00:00"):
            val = val[:-6] + "Z"
        return val

    @staticmethod
    def _map_segment(seg: Dict[str, Any]) -> FlightSegment:
        carrier_code = (seg.get("marketing_carrier_code") or "").strip()
        flight_number = (seg.get("flight_number") or "").strip()
        airline = (
            seg.get("operating_carrier_name")
            or seg.get("marketing_carrier_name")
            or carrier_code
            or "Unknown"
        ).strip()

        # Avoid duplicating carrier code prefix if it's already in flight_number
        if carrier_code and not flight_number.startswith(carrier_code):
            full_flight_number = f"{carrier_code}{flight_number}"
        else:
            full_flight_number = flight_number or f"{carrier_code}?"

        dep_time = IgnavFlightProvider._parse_time(
            seg.get("departure_time_utc"), seg.get("departure_time_local")
        )
        arr_time = IgnavFlightProvider._parse_time(
            seg.get("arrival_time_utc"), seg.get("arrival_time_local")
        )

        return FlightSegment(
            airline=airline,
            flight_number=full_flight_number,
            origin=(seg.get("departure_airport") or "").upper(),
            destination=(seg.get("arrival_airport") or "").upper(),
            departure_time=dep_time,
            arrival_time=arr_time,
            duration_minutes=int(seg.get("duration_minutes") or 0),
            aircraft_type=seg.get("aircraft_type") or None,
        )

    @staticmethod
    def _map_leg(leg_data: Dict[str, Any]) -> FlightOfferLeg:
        raw_segments = leg_data.get("segments") or []
        if not raw_segments:
            raise ValueError("Ignav leg has no segments")

        segments = tuple(IgnavFlightProvider._map_segment(s) for s in raw_segments)
        first = segments[0]
        last = segments[-1]

        return FlightOfferLeg(
            origin=first.origin,
            destination=last.destination,
            departure_time=first.departure_time,
            arrival_time=last.arrival_time,
            duration_minutes=int(leg_data.get("duration_minutes") or sum(s.duration_minutes for s in segments)),
            stops=len(segments) - 1,
            segments=segments,
        )

    @staticmethod
    def _pick_booking_link(options: List[Dict[str, Any]], provider_name: str = "ignav_flights") -> FlightBookingLink:
        """Pick the best booking link from options list.

        Priority: airline_direct > ota > provider_deeplink > unavailable.
        Returns UNAVAILABLE booking link if no usable option is found.
        """
        if not options:
            return FlightBookingLink(
                url="",
                link_type=BookingLinkType.UNAVAILABLE,
                provider_name=provider_name,
            )

        _rank = {
            "airline_direct": 0,
            "ota": 1,
            "provider_deeplink": 2,
        }

        def option_key(opt: Dict[str, Any]) -> int:
            lt = (opt.get("link_type") or "").lower()
            return _rank.get(lt, 3)

        best = min(options, key=option_key)
        url = (best.get("url") or "").strip()
        raw_lt = (best.get("link_type") or "").lower()

        if not url:
            return FlightBookingLink(
                url="",
                link_type=BookingLinkType.UNAVAILABLE,
                provider_name=provider_name,
            )

        if raw_lt == "airline_direct":
            link_type = BookingLinkType.AIRLINE_DIRECT
        elif raw_lt == "ota":
            link_type = BookingLinkType.OTA
        else:
            # Ignav-generated link; classify as provider_deeplink
            link_type = BookingLinkType.PROVIDER_DEEPLINK

        return FlightBookingLink(
            url=url,
            link_type=link_type,
            provider_name=provider_name,
        )

    @staticmethod
    def _map_itinerary(
        it: Dict[str, Any],
        booking_options: List[Dict[str, Any]],
        req: FlightSearchRequest,
        fetched_at: str,
    ) -> FlightItineraryOffer:
        """Map a single Ignav itinerary dict to FlightItineraryOffer."""
        price_data = it.get("price") or {}
        price = FlightPrice(
            currency=(price_data.get("currency") or "USD").upper(),
            total_amount=float(price_data.get("amount") or 0),
        )

        outbound_data = it.get("outbound") or {}
        outbound_leg = IgnavFlightProvider._map_leg(outbound_data)

        inbound_data = it.get("inbound")
        return_leg: Optional[FlightOfferLeg] = None
        if inbound_data:
            return_leg = IgnavFlightProvider._map_leg(inbound_data)

        is_round_trip = req.return_date is not None
        trip_type = TripType.ROUND_TRIP if is_round_trip else TripType.ONE_WAY

        # For round-trip, ensure return_leg is present; fail if not
        if trip_type is TripType.ROUND_TRIP and return_leg is None:
            raise ValueError("round-trip itinerary has no inbound leg")

        origins = req.all_origins
        destinations = req.all_destinations

        booking_link = IgnavFlightProvider._pick_booking_link(booking_options)

        return FlightItineraryOffer(
            provider="ignav_flights",
            fetched_at=fetched_at,
            live_cached_status=LiveCachedStatus.LIVE,
            trip_type=trip_type,
            origin=(origins[0].upper() if origins else outbound_leg.origin),
            destination=(destinations[0].upper() if destinations else outbound_leg.destination),
            departure_date=req.departure_date.isoformat(),
            return_date=(req.return_date.isoformat() if req.return_date else None),
            passengers=max(int(req.passengers or 1), 1),
            cabin_class=(it.get("cabin_class") or req.cabin_class or "economy"),
            outbound_leg=outbound_leg,
            return_leg=return_leg,
            price=price,
            booking_link=booking_link,
            ai_score=None,
        )

    # ------------------------------------------------------------------
    # Public: FlightProvider protocol
    # ------------------------------------------------------------------

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        fetched_at = datetime.now(timezone.utc).isoformat()
        adults = max(int(req.passengers or 1), 1)

        try:
            data = self._fetch_search(req)
        except httpx.TimeoutException as exc:
            logger.warning("[ignav] search timed out: %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[],
                reason="Ignav flight search timed out",
            )
        except httpx.HTTPStatusError as exc:
            logger.error("[ignav] search HTTP error %s: %s", exc.response.status_code, exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"Ignav HTTP {exc.response.status_code}",
            )
        except Exception as exc:
            logger.exception("[ignav] search unexpected error: %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"Ignav search error: {type(exc).__name__}",
            )

        raw_itineraries: List[Dict[str, Any]] = data.get("itineraries") or []
        if not raw_itineraries:
            logger.info("[ignav] search returned 0 itineraries")
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="no itineraries returned by Ignav",
            )

        # Cap and extract ignav_ids for parallel booking-link fetches
        capped = raw_itineraries[:_MAX_OFFERS]
        ids_to_fetch = [
            (idx, it.get("ignav_id", ""))
            for idx, it in enumerate(capped)
            if it.get("ignav_id")
        ][:_MAX_BOOKING_LINK_FETCHES]

        # Fetch booking links in parallel
        booking_map: Dict[int, List[Dict[str, Any]]] = {}
        if ids_to_fetch:
            with ThreadPoolExecutor(max_workers=min(len(ids_to_fetch), 5)) as pool:
                future_to_idx: Dict[Future, int] = {
                    pool.submit(self._fetch_booking_links, ignav_id, adults): idx
                    for idx, ignav_id in ids_to_fetch
                }
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        booking_map[idx] = future.result()
                    except Exception as exc:
                        logger.warning("[ignav] booking_links future error idx=%d: %s", idx, exc)
                        booking_map[idx] = []

        # Map itineraries → FlightItineraryOffer
        offers: List[FlightItineraryOffer] = []
        for idx, it in enumerate(capped):
            bl_options = booking_map.get(idx, [])
            try:
                offer = self._map_itinerary(it, bl_options, req, fetched_at)
                offers.append(offer)
            except Exception as exc:
                logger.warning("[ignav] skipping itinerary idx=%d mapping error: %s", idx, exc)

        if not offers:
            logger.warning("[ignav] all %d itineraries failed to map", len(capped))
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="all itineraries failed contract mapping",
            )

        logger.info("[ignav] returning %d offers", len(offers))
        return FlightProviderResult(
            status=FlightSourceStatus.OK,
            rows=offers,
        )


def build_ignav_provider_from_env() -> Optional[FlightProvider]:
    """Factory: returns an ``IgnavFlightProvider`` only when fully enabled.

    Returns ``None`` when env vars are absent so ``get_flight_provider``
    falls through to ``NullFlightProvider``.
    """
    if not ignav_enabled_from_env():
        return None
    api_key = os.environ.get("IGNAV_API_KEY", "").strip()
    if not api_key:
        return None
    return IgnavFlightProvider(api_key=api_key)


__all__ = [
    "IgnavFlightProvider",
    "build_ignav_provider_from_env",
    "ignav_enabled_from_env",
]
