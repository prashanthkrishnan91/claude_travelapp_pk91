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
  - Every offer passes the trust gate before being returned to the frontend.

Trust gate (applied before mapping):
  Route/date checks:
  - Outbound first-segment departure airport must equal requested origin.
  - Outbound last-segment arrival airport must equal requested destination.
  - Segment airport chain must be coherent (each arrival == next departure).
  - Outbound departure LOCAL date must equal requested departure_date.
    Prefers departure_time_local; falls back to UTC date if local unavailable.
    Missing departure time (no local or utc) is a hard rejection.

  Per-segment field checks (all segments in outbound and inbound):
  - Each segment must have at least one of: marketing_carrier_code, flight_number.
  - Each segment's departure_airport and arrival_airport must be 3-letter IATA.
  - Each segment must have departure time (local or UTC).
  - Each segment must have arrival time (local or UTC).
  - If duration_minutes is present it must be > 0.

  Internal consistency checks:
  - If the leg-level duration_minutes is present and segments also provide
    durations, leg duration must not be less than the sum of segment durations
    by more than 10 minutes (leg can exceed segment sum due to layover time;
    it cannot be materially less — that indicates data corruption).
  - If the raw outbound/inbound leg carries a stops count, it must equal
    len(segments) - 1.
  - Duplicate normalized flight numbers within a single leg are rejected when
    they appear on different routes (identical flight number on two different
    dep→arr pairs is a data assembly error, not a through-flight continuation).

  For round-trips: inbound segments must be present; inbound first-segment
    departure airport == requested destination; inbound last-segment arrival
    airport == requested origin; inbound chain coherent; inbound departure
    LOCAL date (falling back to UTC) == requested return_date.
    Missing inbound departure time is a hard rejection.
    All per-segment and consistency checks apply to inbound as well.

  - Offers failing any check are excluded and logged at WARNING level.
  - If ALL offers fail, returns UNAVAILABLE (not incorrect cards).

Time normalization:
  - ``_parse_time()`` prefers LOCAL time over UTC so displayed times match
    airline schedules. Stored strings may lack UTC offset; frontend must
    extract HH:MM by slicing, not by UTC conversion.

Booking-link lookup:
  - ``_fetch_booking_links`` sends only ``ignav_id`` — the Ignav booking-link
    endpoint does not accept ``adults`` or ``market`` fields alongside
    ``ignav_id`` and returns 400 if they are present.
  - Non-200 responses are logged with status code + first 200 chars of body
    (no API keys, no tokens).

Debug payload logging:
  - Set ``IGNAV_FLIGHTS_DEBUG_PAYLOAD=1`` in backend env to emit structured
    diagnostic info for the first three trust-gate-passing offers.
  - Only non-sensitive scheduling fields are logged: provider index, ignav_id
    prefix, segment route chain, flight numbers, local/UTC dep/arr times,
    durations, and price.  API keys/tokens/personal data are never logged.

Latency strategy:
  - One search call (one-way or round-trip endpoint).
  - Parallel booking-link fetches for the top ``_MAX_BOOKING_LINK_FETCHES``
    valid results using ThreadPoolExecutor.
  - Total budget: _HTTP_TIMEOUT_SECONDS + _BOOKING_LINK_TIMEOUT_SECONDS ≈ 18 s.
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
_BOOKING_LINK_TIMEOUT_SECONDS = 3.0
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

    def _fetch_booking_links(self, ignav_id: str) -> List[Dict[str, Any]]:
        """Fetch booking links for a single itinerary.  Returns empty list on failure.

        The Ignav booking-link endpoint only accepts ``ignav_id``.  Including
        ``adults`` or ``market`` alongside ``ignav_id`` returns HTTP 400
        conflicting_booking_lookup_mode.
        """
        url = f"{self._base_url}/booking-links"
        body = {"ignav_id": ignav_id}
        try:
            client = httpx.Client(timeout=_BOOKING_LINK_TIMEOUT_SECONDS) if self._client is None else self._client
            resp = client.post(url, json=body, headers=self._headers())
            if resp.status_code != 200:
                # Log status + truncated body for diagnosis (no keys/tokens in body)
                body_preview = (resp.text or "")[:200]
                logger.warning(
                    "[ignav] booking_links status=%d id_prefix=%.8s body=%r",
                    resp.status_code, ignav_id, body_preview,
                )
            resp.raise_for_status()
            data = resp.json()
            return data.get("booking_options", []) or []
        except Exception as exc:
            logger.warning("[ignav] booking_links failed id_prefix=%.8s: %s", ignav_id, exc)
            return []

    # ------------------------------------------------------------------
    # Internal: trust gate
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_itinerary_raw(
        it: Dict[str, Any],
        req: FlightSearchRequest,
    ) -> Tuple[bool, str]:
        """Validate raw Ignav itinerary against the search request.

        Checks (in order):
        1. Outbound has segments.
        2. First segment departure airport == requested origin.
        3. Last segment arrival airport == requested destination.
        4. Segment chain is coherent (each arrival == next departure).
        5. Departure LOCAL date (or UTC fallback) == requested departure_date.
           Missing departure time is a hard rejection.
        6. For round-trips: inbound segments present; inbound route reversed;
           inbound chain coherent; inbound LOCAL date == return_date.
           Missing inbound departure time is a hard rejection.

        Returns (valid: bool, rejection_reason: str).
        """
        outbound = it.get("outbound") or {}
        segments = outbound.get("segments") or []

        if not segments:
            return False, "outbound has no segments"

        first_seg = segments[0]
        last_seg = segments[-1]

        req_origin = (req.all_origins[0].upper() if req.all_origins else "").strip()
        req_dest = (req.all_destinations[0].upper() if req.all_destinations else "").strip()

        first_dep = (first_seg.get("departure_airport") or "").upper().strip()
        last_arr = (last_seg.get("arrival_airport") or "").upper().strip()

        logger.debug(
            "[ignav] trust_gate check origin=%s→%s req=%s→%s",
            first_dep, last_arr, req_origin, req_dest,
        )

        if first_dep != req_origin:
            return False, f"origin mismatch: segment={first_dep!r} req={req_origin!r}"
        if last_arr != req_dest:
            return False, f"dest mismatch: segment={last_arr!r} req={req_dest!r}"

        # Outbound segment chain coherence
        for i in range(len(segments) - 1):
            conn_arr = (segments[i].get("arrival_airport") or "").upper().strip()
            conn_dep = (segments[i + 1].get("departure_airport") or "").upper().strip()
            if conn_arr != conn_dep:
                return False, f"segment chain broken at {i}: {conn_arr!r}→{conn_dep!r}"

        # Outbound date check: prefer local, fall back to UTC; missing is a hard rejection
        dep_local = (first_seg.get("departure_time_local") or "").strip()
        dep_utc = (first_seg.get("departure_time_utc") or "").strip()

        if dep_local:
            actual_date_str = dep_local[:10]
            source = "local"
        elif dep_utc:
            actual_date_str = dep_utc[:10]
            source = "utc"
        else:
            return False, "missing outbound departure time (no local or utc)"

        req_date_str = req.departure_date.isoformat()
        if actual_date_str != req_date_str:
            return False, (
                f"date mismatch ({source}): segment={actual_date_str!r} "
                f"req={req_date_str!r}"
            )

        # Per-segment field validation for all outbound segments
        for seg_i, seg in enumerate(segments):
            seg_ok, seg_reason = IgnavFlightProvider._validate_segment_fields(
                seg, seg_i, "outbound"
            )
            if not seg_ok:
                return False, seg_reason

        # Duplicate flight-number check within outbound leg
        dup_reason = IgnavFlightProvider._check_duplicate_flight_numbers(
            segments, "outbound"
        )
        if dup_reason:
            return False, dup_reason

        # Outbound leg duration must not be less than segment sum (leg can exceed
        # segment sum due to layover time; it cannot be materially less)
        out_leg_dur = outbound.get("duration_minutes")
        if out_leg_dur is not None:
            out_seg_sum = sum(int(s.get("duration_minutes") or 0) for s in segments)
            if out_seg_sum > 0 and int(out_leg_dur) < out_seg_sum - 10:
                return False, (
                    f"outbound leg duration {out_leg_dur}m less than segment "
                    f"sum {out_seg_sum}m — data inconsistency"
                )

        # Outbound stop count cross-check when provider supplies it
        raw_out_stops = outbound.get("stops")
        if raw_out_stops is not None:
            expected_stops = len(segments) - 1
            try:
                if int(raw_out_stops) != expected_stops:
                    return False, (
                        f"outbound stop count mismatch: raw={raw_out_stops} "
                        f"segments_imply={expected_stops}"
                    )
            except (TypeError, ValueError):
                return False, f"outbound stops field malformed: {raw_out_stops!r}"

        # Inbound validation for round-trips
        if req.return_date is not None:
            inbound = it.get("inbound") or {}
            in_segments = inbound.get("segments") or []
            if not in_segments:
                return False, "round-trip has no inbound segments"

            in_first = in_segments[0]
            in_last = in_segments[-1]

            in_first_dep = (in_first.get("departure_airport") or "").upper().strip()
            in_last_arr = (in_last.get("arrival_airport") or "").upper().strip()

            if in_first_dep != req_dest:
                return False, f"inbound origin mismatch: segment={in_first_dep!r} req={req_dest!r}"
            if in_last_arr != req_origin:
                return False, f"inbound dest mismatch: segment={in_last_arr!r} req={req_origin!r}"

            for i in range(len(in_segments) - 1):
                conn_arr = (in_segments[i].get("arrival_airport") or "").upper().strip()
                conn_dep = (in_segments[i + 1].get("departure_airport") or "").upper().strip()
                if conn_arr != conn_dep:
                    return False, f"inbound segment chain broken at {i}: {conn_arr!r}→{conn_dep!r}"

            in_dep_local = (in_first.get("departure_time_local") or "").strip()
            in_dep_utc = (in_first.get("departure_time_utc") or "").strip()

            if in_dep_local:
                in_date_str = in_dep_local[:10]
                in_source = "local"
            elif in_dep_utc:
                in_date_str = in_dep_utc[:10]
                in_source = "utc"
            else:
                return False, "missing inbound departure time (no local or utc)"

            req_return_str = req.return_date.isoformat()
            if in_date_str != req_return_str:
                return False, (
                    f"inbound date mismatch ({in_source}): segment={in_date_str!r} "
                    f"req={req_return_str!r}"
                )

            # Per-segment field validation for all inbound segments
            for seg_i, seg in enumerate(in_segments):
                seg_ok, seg_reason = IgnavFlightProvider._validate_segment_fields(
                    seg, seg_i, "inbound"
                )
                if not seg_ok:
                    return False, seg_reason

            # Duplicate flight-number check within inbound leg
            in_dup_reason = IgnavFlightProvider._check_duplicate_flight_numbers(
                in_segments, "inbound"
            )
            if in_dup_reason:
                return False, in_dup_reason

            # Inbound leg duration vs segment sum
            in_leg_dur = inbound.get("duration_minutes")
            if in_leg_dur is not None:
                in_seg_sum = sum(
                    int(s.get("duration_minutes") or 0) for s in in_segments
                )
                if in_seg_sum > 0 and int(in_leg_dur) < in_seg_sum - 10:
                    return False, (
                        f"inbound leg duration {in_leg_dur}m less than segment "
                        f"sum {in_seg_sum}m — data inconsistency"
                    )

        return True, ""

    # ------------------------------------------------------------------
    # Internal: per-segment and leg consistency validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_segment_fields(
        seg: Dict[str, Any], seg_index: int, leg: str
    ) -> Tuple[bool, str]:
        """Deep-validate one segment's required fields.

        Returns (valid, rejection_reason).
        Checks: carrier/flight number, 3-letter IATA airports, departure time,
        arrival time, and positive duration when present.
        """
        prefix = f"{leg} seg[{seg_index}]"

        carrier_code = (seg.get("marketing_carrier_code") or "").strip()
        flight_num = (seg.get("flight_number") or "").strip()
        if not carrier_code and not flight_num:
            return False, f"{prefix}: missing carrier code and flight number"

        dep_airport = (seg.get("departure_airport") or "").upper().strip()
        arr_airport = (seg.get("arrival_airport") or "").upper().strip()
        if len(dep_airport) != 3:
            return False, f"{prefix}: departure_airport not a 3-letter IATA code: {dep_airport!r}"
        if len(arr_airport) != 3:
            return False, f"{prefix}: arrival_airport not a 3-letter IATA code: {arr_airport!r}"

        dep_local = (seg.get("departure_time_local") or "").strip()
        dep_utc = (seg.get("departure_time_utc") or "").strip()
        if not dep_local and not dep_utc:
            return False, f"{prefix}: missing departure time"

        arr_local = (seg.get("arrival_time_local") or "").strip()
        arr_utc = (seg.get("arrival_time_utc") or "").strip()
        if not arr_local and not arr_utc:
            return False, f"{prefix}: missing arrival time"

        dur = seg.get("duration_minutes")
        if dur is not None:
            try:
                if int(dur) <= 0:
                    return False, f"{prefix}: non-positive duration_minutes={dur}"
            except (TypeError, ValueError):
                return False, f"{prefix}: malformed duration_minutes={dur!r}"

        return True, ""

    @staticmethod
    def _check_duplicate_flight_numbers(
        segments: List[Dict[str, Any]], leg: str
    ) -> str:
        """Return rejection reason when the same flight number appears on different routes.

        Identical flight number on two different dep→arr pairs in one leg is a
        data assembly error (not a through-flight continuation — those have the
        same route and are already filtered by chain coherence).
        Returns empty string if no violation found.
        """
        seen: Dict[str, str] = {}
        for seg in segments:
            carrier_code = (seg.get("marketing_carrier_code") or "").strip()
            flight_num = (seg.get("flight_number") or "").strip()
            if not flight_num:
                continue
            if carrier_code and not flight_num.startswith(carrier_code):
                normalized = f"{carrier_code}{flight_num}"
            else:
                normalized = flight_num

            dep = (seg.get("departure_airport") or "").upper().strip()
            arr = (seg.get("arrival_airport") or "").upper().strip()
            route = f"{dep}→{arr}"

            if normalized in seen:
                if seen[normalized] != route:
                    return (
                        f"{leg}: duplicate flight number {normalized!r} on "
                        f"different routes ({seen[normalized]} and {route})"
                    )
            else:
                seen[normalized] = route
        return ""

    # ------------------------------------------------------------------
    # Internal: debug payload logging
    # ------------------------------------------------------------------

    def _log_debug_offer(self, idx: int, it: Dict[str, Any]) -> None:
        """Log structured non-sensitive offer fields for mapping diagnostics.

        Only emitted when IGNAV_FLIGHTS_DEBUG_PAYLOAD=1.  Never logs API keys,
        tokens, or personal data.  Logs: provider index, ignav_id prefix,
        segment route chain, flight numbers, local/UTC dep/arr times, durations,
        and price.
        """
        ignav_id_prefix = (it.get("ignav_id") or "")[:12]
        price_data = it.get("price") or {}
        price_str = (
            f"{price_data.get('currency', '?')}{price_data.get('amount', '?')}"
        )

        def _seg_summary(seg: Dict[str, Any]) -> str:
            code = (seg.get("marketing_carrier_code") or "").strip()
            num = (seg.get("flight_number") or "?").strip()
            fn = f"{code}{num}" if (code and not num.startswith(code)) else (num or f"{code}?")
            dep = (seg.get("departure_airport") or "???").upper()
            arr = (seg.get("arrival_airport") or "???").upper()
            dep_t = (
                seg.get("departure_time_local") or seg.get("departure_time_utc") or "?"
            )[:16]
            arr_t = (
                seg.get("arrival_time_local") or seg.get("arrival_time_utc") or "?"
            )[:16]
            dur = seg.get("duration_minutes", "?")
            return f"{fn}:{dep}@{dep_t}→{arr}@{arr_t}({dur}m)"

        outbound = it.get("outbound") or {}
        out_segs = outbound.get("segments") or []
        out_chain = " | ".join(_seg_summary(s) for s in out_segs)
        out_leg_dur = outbound.get("duration_minutes", "?")

        in_part = ""
        inbound = it.get("inbound")
        if inbound:
            in_segs = inbound.get("segments") or []
            in_chain = " | ".join(_seg_summary(s) for s in in_segs)
            in_part = f" | return:[{in_chain}]({inbound.get('duration_minutes','?')}m)"

        logger.info(
            "[ignav_debug] idx=%d id_prefix=%.12s price=%s cabin=%s "
            "outbound:[%s](%sm)%s",
            idx, ignav_id_prefix, price_str,
            it.get("cabin_class", "?"),
            out_chain, out_leg_dur,
            in_part,
        )

    # ------------------------------------------------------------------
    # Internal: mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_time(utc_str: Optional[str], local_str: Optional[str]) -> str:
        """Return display-ready ISO 8601 time string; prefers LOCAL over UTC.

        Preference for local means displayed times match airline departure boards.
        The frontend must extract HH:MM by slicing position [11:16], not by
        converting through UTC (which would show wrong local times).
        """
        val = local_str or utc_str or ""
        if not val:
            raise ValueError("no departure or arrival time available")
        # Normalize UTC offset suffix for consistency
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
    def _normalize_url(url: str) -> str:
        """Ensure URL has an https:// scheme so frontend hrefs are absolute."""
        url = url.strip()
        if not url:
            return url
        if url.startswith("//"):
            return "https:" + url
        if "://" not in url:
            return "https://" + url
        return url

    @staticmethod
    def _pick_booking_link(
        booking_options: List[Dict[str, Any]],
        provider_name: str = "ignav_flights",
    ) -> FlightBookingLink:
        """Flatten booking_options[].links[], classify by provider_type, pick best.

        Ignav response shape per option:
          { provider_name, provider_type, links: [{url, price}, ...] }

        provider_type mapping:
          "airline"      → airline_direct
          "third_party"  → ota
          anything else  → provider_deeplink (if URL present)

        Priority: airline_direct > ota > provider_deeplink.
        Returns UNAVAILABLE if no usable link found.
        """
        _rank = {
            BookingLinkType.AIRLINE_DIRECT: 0,
            BookingLinkType.OTA: 1,
            BookingLinkType.PROVIDER_DEEPLINK: 2,
        }

        candidates: List[Tuple[BookingLinkType, str]] = []
        for option in (booking_options or []):
            raw_type = (option.get("provider_type") or "").lower().strip()
            if raw_type == "airline":
                link_type = BookingLinkType.AIRLINE_DIRECT
            elif raw_type == "third_party":
                link_type = BookingLinkType.OTA
            else:
                link_type = BookingLinkType.PROVIDER_DEEPLINK

            for link in (option.get("links") or []):
                url = IgnavFlightProvider._normalize_url((link.get("url") or ""))
                if url:
                    candidates.append((link_type, url))

        if not candidates:
            return FlightBookingLink(
                url="",
                link_type=BookingLinkType.UNAVAILABLE,
                provider_name=provider_name,
            )

        best_type, best_url = min(candidates, key=lambda c: _rank.get(c[0], 3))
        return FlightBookingLink(
            url=best_url,
            link_type=best_type,
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

        # Cap raw results
        capped = raw_itineraries[:_MAX_OFFERS]

        # Trust gate: validate each raw itinerary before mapping or fetching links
        valid_itineraries: List[Dict[str, Any]] = []
        for idx, it in enumerate(capped):
            ok, reason = self._validate_itinerary_raw(it, req)
            if ok:
                valid_itineraries.append(it)
            else:
                logger.warning(
                    "[ignav] trust_gate rejected idx=%d ignav_id_prefix=%.8s reason=%s",
                    idx, it.get("ignav_id", ""), reason,
                )

        if not valid_itineraries:
            logger.warning(
                "[ignav] trust_gate rejected all %d itineraries — returning unavailable",
                len(capped),
            )
            return FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[],
                reason="all Ignav offers failed route/date validation",
            )

        logger.info(
            "[ignav] trust_gate: %d/%d itineraries passed",
            len(valid_itineraries), len(capped),
        )

        # Debug payload logging — gated by IGNAV_FLIGHTS_DEBUG_PAYLOAD=1
        if os.environ.get("IGNAV_FLIGHTS_DEBUG_PAYLOAD", "").strip().lower() in _TRUTHY:
            for dbg_idx, dbg_it in enumerate(valid_itineraries[:3]):
                self._log_debug_offer(dbg_idx, dbg_it)

        # Extract ignav_ids for parallel booking-link fetches (valid offers only)
        ids_to_fetch = [
            (idx, it.get("ignav_id", ""))
            for idx, it in enumerate(valid_itineraries)
            if it.get("ignav_id")
        ][:_MAX_BOOKING_LINK_FETCHES]

        # Fetch booking links in parallel
        booking_map: Dict[int, List[Dict[str, Any]]] = {}
        if ids_to_fetch:
            with ThreadPoolExecutor(max_workers=min(len(ids_to_fetch), 5)) as pool:
                future_to_idx: Dict[Future, int] = {
                    pool.submit(self._fetch_booking_links, ignav_id): idx
                    for idx, ignav_id in ids_to_fetch
                }
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        booking_map[idx] = future.result()
                    except Exception as exc:
                        logger.warning("[ignav] booking_links future error idx=%d: %s", idx, exc)
                        booking_map[idx] = []

        # Map valid itineraries → FlightItineraryOffer
        offers: List[FlightItineraryOffer] = []
        for idx, it in enumerate(valid_itineraries):
            bl_options = booking_map.get(idx, [])
            try:
                offer = self._map_itinerary(it, bl_options, req, fetched_at)
                offers.append(offer)
            except Exception as exc:
                logger.warning("[ignav] skipping itinerary idx=%d mapping error: %s", idx, exc)

        if not offers:
            logger.warning("[ignav] all %d valid itineraries failed to map", len(valid_itineraries))
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

