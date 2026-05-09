"""Duffel Flights Offers adapter — Flights v1."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore[assignment]

from app.contracts.flights import (
    FlightContractViolation,
    FlightSourceStatus,
    assert_persistable_flight,
)
from app.models.search import FlightResult, FlightSearchRequest
from app.services.flights_provider import FlightProviderResult

logger = logging.getLogger(__name__)
_DEFAULT_BASE_URL = "https://api.duffel.com"
_OFFERS_PATH = "/air/offer_requests"
_HTTP_TIMEOUT_SECONDS = 8.0
_SUPPLIER_TIMEOUT_MS = 6000
_TRUTHY = {"1", "true", "yes", "on"}


def _truthy(value: Optional[str]) -> bool:
    return bool(value) and value.strip().lower() in _TRUTHY


class DuffelFlightProvider:
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = _DEFAULT_BASE_URL,
        http_client: Optional["httpx.Client"] = None,
    ) -> None:
        if not access_token:
            raise ValueError("DuffelFlightProvider requires non-empty access token")
        self._access_token = access_token
        self._base_url = base_url.rstrip("/") or _DEFAULT_BASE_URL
        self._client = http_client

    def _get_http(self) -> "httpx.Client":
        if self._client is None:
            if httpx is None:  # pragma: no cover
                raise RuntimeError("httpx is not installed")
            self._client = httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS)
        return self._client

    def search_flights(self, req: FlightSearchRequest) -> FlightProviderResult:
        origin = (req.origin or "").upper()
        destination = (req.destination or "").upper()
        if not origin or not destination:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="missing origin or destination IATA",
            )

        payload: Dict[str, Any] = {
            "data": {
                "slices": [
                    {
                        "origin": origin,
                        "destination": destination,
                        "departure_date": req.departure_date.isoformat(),
                    }
                ],
                "passengers": [
                    {"type": "adult"}
                    for _ in range(max(int(req.passengers or 1), 1))
                ],
                "cabin_class": req.cabin_class or "economy",
            }
        }

        try:
            resp = self._get_http().post(
                f"{self._base_url}{_OFFERS_PATH}",
                params={
                    "return_offers": "true",
                    "view": "offers",
                    "supplier_timeout": str(_SUPPLIER_TIMEOUT_MS),
                },
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Duffel-Version": "v2",
                    "Content-Type": "application/json",
                },
            )
        except Exception as exc:
            logger.warning("[duffel.offers_request_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"transport error: {exc}",
            )

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.warning("[duffel.offers_status] status=%d", resp.status_code)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"duffel http {resp.status_code}",
            )

        try:
            outer = resp.json() or {}
        except Exception as exc:
            logger.warning("[duffel.offers_parse_error] %s", exc)
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason=f"parse error: {exc}",
            )

        data = outer.get("data") or {}
        offers = data.get("offers") or []
        if not isinstance(offers, list):
            return FlightProviderResult(
                status=FlightSourceStatus.ERROR,
                rows=[],
                reason="duffel response missing offers list",
            )
        if not offers:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="duffel returned zero offers",
            )

        rows: List[FlightResult] = []
        for offer in offers:
            row = _map_offer_to_outbound(offer, req.cabin_class or "economy")
            if row is None:
                continue
            try:
                assert_persistable_flight(row)
            except FlightContractViolation:
                continue
            rows.append(row)

        if not rows:
            return FlightProviderResult(
                status=FlightSourceStatus.EMPTY,
                rows=[],
                reason="all offers failed contract",
            )
        return FlightProviderResult(status=FlightSourceStatus.OK, rows=rows)


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


def _parse_iso_duration_minutes(value: Optional[str]) -> int:
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


def _map_offer_to_outbound(
    offer: Dict[str, Any],
    cabin_class: str,
) -> Optional[FlightResult]:
    slices = offer.get("slices") or []
    if not slices:
        return None
    sl = slices[0] or {}
    segments = sl.get("segments") or []
    if not segments:
        return None
    first, last = segments[0], segments[-1]
    origin = (first.get("origin") or {}).get("iata_code")
    dest = (last.get("destination") or {}).get("iata_code")
    dep_at = _parse_iso_datetime(first.get("departing_at") or "")
    arr_at = _parse_iso_datetime(last.get("arriving_at") or "")
    if not (origin and dest and dep_at and arr_at):
        return None

    operating = (first.get("operating_carrier") or {})
    marketing = (first.get("marketing_carrier") or {})
    airline = (
        operating.get("name")
        or marketing.get("name")
        or operating.get("iata_code")
        or marketing.get("iata_code")
        or ""
    )
    carrier_code = (marketing.get("iata_code") or "").upper()
    num = str(first.get("marketing_carrier_flight_number") or "")
    flight_number = f"{carrier_code}{num}" if carrier_code else num
    if not airline or not flight_number:
        return None

    amount = offer.get("total_amount") or ""
    try:
        price = float(amount)
    except Exception:
        price = None

    row_id = f"duffel-{offer.get('id') or flight_number}"
    return FlightResult(
        id=row_id,
        price=price,
        location=f"{origin.upper()} → {dest.upper()}",
        booking_url="",
        source="duffel",
        booking_options=[],
        airline=airline,
        flight_number=flight_number,
        origin=origin.upper(),
        destination=dest.upper(),
        departure_time=dep_at,
        arrival_time=arr_at,
        duration_minutes=_parse_iso_duration_minutes(sl.get("duration")),
        stops=max(len(segments) - 1, 0),
        cabin_class=cabin_class,
    )


def duffel_enabled_from_env(env: Optional[Dict[str, str]] = None) -> bool:
    env = env if env is not None else os.environ  # type: ignore[assignment]
    return _truthy(env.get("DUFFEL_FLIGHTS_ENABLED")) and bool(env.get("DUFFEL_ACCESS_TOKEN"))


def build_duffel_provider_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[DuffelFlightProvider]:
    env = env if env is not None else os.environ  # type: ignore[assignment]
    if not duffel_enabled_from_env(env):
        return None
    return DuffelFlightProvider(
        access_token=env.get("DUFFEL_ACCESS_TOKEN") or "",
        base_url=env.get("DUFFEL_BASE_URL") or _DEFAULT_BASE_URL,
    )
