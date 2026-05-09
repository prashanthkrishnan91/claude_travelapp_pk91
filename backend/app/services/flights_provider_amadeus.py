"""Amadeus Flight Offers Search adapter — Flights v1.

Backend-only HTTP integration plugged behind the
``app.services.flights_provider.FlightProvider`` seam introduced in PR #297.
Honors the Flights Product Contract v1: never raises on transport / API
failures, never fabricates rows, and only emits ``FlightResult`` rows that
satisfy ``assert_persistable_flight``.

Env vars (read at provider construction):

- ``AMADEUS_CLIENT_ID``
- ``AMADEUS_CLIENT_SECRET``
- ``AMADEUS_BASE_URL`` (optional; defaults to test API)
- ``AMADEUS_FLIGHTS_ENABLED`` (optional; default false unless creds present
  AND the flag is explicitly truthy)

Security: all calls are server-side only; credentials are never exposed to
the frontend or persisted.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover - httpx in requirements.txt
    httpx = None  # type: ignore[assignment]

from app.contracts.flights import (
    FlightSourceStatus,
    assert_persistable_flight,
    FlightContractViolation,
)
from app.models.search import FlightResult, FlightSearchRequest
from app.services.flights_provider import FlightProviderResult


logger = logging.getLogger(__name__)


_DEFAULT_BASE_URL = "https://test.api.amadeus.com"
_TOKEN_PATH = "/v1/security/oauth2/token"
_OFFERS_PATH = "/v2/shopping/flight-offers"
_HTTP_TIMEOUT_SECONDS = 8.0
_TOKEN_REFRESH_LEEWAY_SECONDS = 60
_MAX_OFFERS = 8

_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


class AmadeusFlightProvider:
    """Adapter for Amadeus Self-Service Flight Offers Search.

    Construct via :func:`build_amadeus_provider_from_env` so credential and
    feature-flag checks live in one place.  The adapter caches the OAuth2
    token in process; it does not persist anything to Supabase.
    """

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = _DEFAULT_BASE_URL,
        http_client: Optional["httpx.Client"] = None,
        clock: Any = time.time,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("AmadeusFlightProvider requires non-empty credentials")
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/") or _DEFAULT_BASE_URL
        self._client = http_client
        self._owns_client = http_client is None
        self._clock = clock
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_http(self) -> "httpx.Client":
        if self._client is None:
            if httpx is None:  # pragma: no cover
                raise RuntimeError("httpx is not installed")
            self._client = httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS)
        return self._client

    def _token_valid(self) -> bool:
        return (
            self._token is not None
            and self._clock() < self._token_expires_at - _TOKEN_REFRESH_LEEWAY_SECONDS
        )

    def _fetch_token(self) -> Optional[str]:
        """Fetch a new client_credentials access token. Returns None on failure."""
        url = f"{self._base_url}{_TOKEN_PATH}"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        try:
            resp = self._get_http().post(
                url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except Exception as exc:
            logger.warning("[amadeus.token_fetch_error] %s", exc)
            return None
        if resp.status_code != 200:
            logger.warning(
                "[amadeus.token_fetch_status] status=%d body=%s",
                resp.status_code,
                (resp.text or "")[:200],
            )
            return None
        try:
            payload = resp.json()
        except Exception as exc:
            logger.warning("[amadeus.token_parse_error] %s", exc)
            return None
        access = payload.get("access_token")
        ttl = int(payload.get("expires_in") or 0)
        if not access:
            return None
        with self._lock:
            self._token = access
            self._token_expires_at = self._clock() + max(ttl, _TOKEN_REFRESH_LEEWAY_SECONDS + 1)
        return access

    def _ensure_token(self, *, force_refresh: bool = False) -> Optional[str]:
        if not force_refresh and self._token_valid():
            return self._token
        return self._fetch_token()

    # ------------------------------------------------------------------
    # Public seam
    # ------------------------------------------------------------------

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        """Run a Flight Offers Search and return a typed result.

        Never raises: transport / parse / contract failures translate into
        ``FlightProviderResult(status=ERROR, ...)``.  Empty Amadeus responses
        translate into ``EMPTY``.  Missing IATA codes (single-airport mode
        only) translate into ``EMPTY`` since multi-airport callers iterate
        upstream.
        """
        origin = (req.origin or "").upper()
        destination = (req.destination or "").upper()
        if not origin or not destination:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="missing origin or destination IATA",
            )

        token = self._ensure_token()
        if not token:
            return FlightProviderResult(
                status=FlightSourceStatus.UNAVAILABLE,
                rows=[],
                reason="amadeus token unavailable",
            )

        params: Dict[str, Any] = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": req.departure_date.isoformat(),
            "adults": max(int(req.passengers or 1), 1),
            "max": _MAX_OFFERS,
            "currencyCode": "USD",
        }
        if req.return_date:
            params["returnDate"] = req.return_date.isoformat()
        if req.cabin_class:
            cabin = _amadeus_cabin(req.cabin_class)
            if cabin:
                params["travelClass"] = cabin

        url = f"{self._base_url}{_OFFERS_PATH}"
        try:
            resp = self._get_http().get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        except Exception as exc:
            logger.warning("[amadeus.offers_request_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"transport error: {exc}",
            )

        # 401 → token may have expired between cache check and request; retry once.
        if resp.status_code == 401:
            token = self._ensure_token(force_refresh=True)
            if not token:
                return FlightProviderResult(
                    status=FlightSourceStatus.UNAVAILABLE,
                    rows=[],
                    reason="amadeus reauth failed",
                )
            try:
                resp = self._get_http().get(
                    url,
                    params=params,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except Exception as exc:
                logger.warning("[amadeus.offers_retry_error] %s", exc)
                return FlightProviderResult(
                    status=FlightSourceStatus.ERROR,
                    rows=[],
                    reason=f"transport error: {exc}",
                )

        if resp.status_code != 200:
            logger.warning(
                "[amadeus.offers_status] status=%d body=%s",
                resp.status_code,
                (resp.text or "")[:200],
            )
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"amadeus http {resp.status_code}",
            )

        try:
            payload = resp.json()
        except Exception as exc:
            logger.warning("[amadeus.offers_parse_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"parse error: {exc}",
            )

        offers = payload.get("data") or []
        if not offers:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="amadeus returned zero offers",
            )

        carriers_dict = (
            (payload.get("dictionaries") or {}).get("carriers") or {}
        )

        rows: List[FlightResult] = []
        skipped = 0
        for offer in offers:
            row = _map_offer_to_outbound(offer, carriers_dict, req.cabin_class)
            if row is None:
                skipped += 1
                continue
            try:
                assert_persistable_flight(row)
            except FlightContractViolation:
                skipped += 1
                continue
            rows.append(row)

        if not rows:
            logger.info(
                "[amadeus.offers_all_skipped] skipped=%d origin=%s dest=%s",
                skipped, origin, destination,
            )
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason=f"all {skipped} offers failed contract",
            )

        return FlightProviderResult(status=FlightSourceStatus.OK, rows=rows)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _amadeus_cabin(cabin_class: str) -> Optional[str]:
    return {
        "economy": "ECONOMY",
        "premium_economy": "PREMIUM_ECONOMY",
        "business": "BUSINESS",
        "first": "FIRST",
    }.get(cabin_class)


def _parse_iso_datetime(value: str):
    from datetime import datetime
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _parse_iso_duration(value: Optional[str]) -> Optional[int]:
    """ISO-8601 duration like ``PT5H30M`` → minutes."""
    if not value or not value.startswith("PT"):
        return None
    s = value[2:]
    hours = 0
    minutes = 0
    num = ""
    for ch in s:
        if ch.isdigit():
            num += ch
        elif ch == "H":
            hours = int(num or 0)
            num = ""
        elif ch == "M":
            minutes = int(num or 0)
            num = ""
        else:
            num = ""
    return hours * 60 + minutes if (hours or minutes) else None


def _map_offer_to_outbound(
    offer: Dict[str, Any],
    carriers_dict: Dict[str, str],
    cabin_class: str,
) -> Optional[FlightResult]:
    """Map an Amadeus flight offer to the contract-safe outbound ``FlightResult``.

    Returns ``None`` when required fields cannot be extracted; the caller
    counts skips and emits a typed ``EMPTY``/``OK`` result accordingly.
    """
    itineraries = offer.get("itineraries") or []
    if not itineraries:
        return None
    outbound_segments = (itineraries[0] or {}).get("segments") or []
    if not outbound_segments:
        return None

    first_seg = outbound_segments[0]
    last_seg = outbound_segments[-1]

    origin_code = ((first_seg.get("departure") or {}).get("iataCode") or "").upper()
    dest_code = ((last_seg.get("arrival") or {}).get("iataCode") or "").upper()
    dep_at = _parse_iso_datetime((first_seg.get("departure") or {}).get("at") or "")
    arr_at = _parse_iso_datetime((last_seg.get("arrival") or {}).get("at") or "")
    if not (origin_code and dest_code and dep_at and arr_at):
        return None

    carrier_code = (first_seg.get("carrierCode") or "").upper()
    airline_name = carriers_dict.get(carrier_code) or carrier_code
    if not airline_name:
        return None

    flight_number_raw = first_seg.get("number") or ""
    flight_number = f"{carrier_code}{flight_number_raw}" if carrier_code else str(flight_number_raw)
    if not flight_number:
        flight_number = carrier_code or "FL"

    duration_minutes = _parse_iso_duration((itineraries[0] or {}).get("duration"))
    if duration_minutes is None:
        try:
            duration_minutes = max(int((arr_at - dep_at).total_seconds() // 60), 0)
        except Exception:
            duration_minutes = 0

    stops = max(len(outbound_segments) - 1, 0)

    price_raw = ((offer.get("price") or {}).get("grandTotal")
                 or (offer.get("price") or {}).get("total"))
    try:
        price = float(price_raw) if price_raw is not None else None
    except Exception:
        price = None

    offer_id = str(offer.get("id") or "")
    row_id = f"amadeus-{offer_id}" if offer_id else f"amadeus-{carrier_code}{flight_number_raw}"

    return FlightResult(
        id=row_id,
        price=price,
        location=f"{origin_code} → {dest_code}",
        booking_url="",
        source="amadeus",
        booking_options=[],
        airline=airline_name,
        flight_number=flight_number,
        origin=origin_code,
        destination=dest_code,
        departure_time=dep_at,
        arrival_time=arr_at,
        duration_minutes=int(duration_minutes or 0),
        stops=stops,
        cabin_class=cabin_class or "economy",
    )


# ---------------------------------------------------------------------------
# Env-gated builder
# ---------------------------------------------------------------------------


def amadeus_enabled_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    env = env if env is not None else os.environ  # type: ignore[assignment]
    cid = env.get("AMADEUS_CLIENT_ID") or ""
    sec = env.get("AMADEUS_CLIENT_SECRET") or ""
    flag = env.get("AMADEUS_FLIGHTS_ENABLED")
    if not cid or not sec:
        return False
    return _truthy(flag)


def build_amadeus_provider_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[AmadeusFlightProvider]:
    env = env if env is not None else os.environ  # type: ignore[assignment]
    if not amadeus_enabled_from_env(env):
        return None
    base_url = env.get("AMADEUS_BASE_URL") or _DEFAULT_BASE_URL
    return AmadeusFlightProvider(
        client_id=env.get("AMADEUS_CLIENT_ID") or "",
        client_secret=env.get("AMADEUS_CLIENT_SECRET") or "",
        base_url=base_url,
    )


__all__ = [
    "AmadeusFlightProvider",
    "amadeus_enabled_from_env",
    "build_amadeus_provider_from_env",
]
