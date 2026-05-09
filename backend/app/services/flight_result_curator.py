from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Dict, List, Sequence, Tuple

from app.models.search import FlightResult

DEFAULT_RESULT_CAP = 12
MAX_RESULT_CAP = 20
ROUND_TRIP_LEG_CAP = 8
ROUND_TRIP_PAIR_CAP = 30


@dataclass(frozen=True)
class FlightCurationSummary:
    raw_count: int
    deduped_count: int
    returned_count: int


def _dedupe_key(row: FlightResult) -> Tuple:
    return (
        row.origin,
        row.destination,
        row.departure_time,
        row.arrival_time,
        row.airline,
        row.flight_number,
        row.stops,
        row.duration_minutes,
    )


def _cluster_key(row: FlightResult) -> Tuple:
    return (row.airline, row.flight_number, row.departure_time, row.arrival_time)


def _missing_critical_fields(row: FlightResult) -> int:
    return sum(
        1
        for v in (row.airline, row.flight_number, row.origin, row.destination)
        if not v
    )


def _quality_tuple(row: FlightResult, median_duration: float) -> Tuple:
    # Lower is better
    duration_penalty = max(0, row.duration_minutes - int(median_duration * 1.75))
    return (
        row.stops,
        _missing_critical_fields(row),
        duration_penalty,
        row.duration_minutes,
        row.price or float("inf"),
        row.id,
    )


def curate_flight_results(rows: Sequence[FlightResult], *, requested_limit: int | None = None) -> Tuple[List[FlightResult], FlightCurationSummary]:
    raw_count = len(rows)
    if not rows:
        return [], FlightCurationSummary(0, 0, 0)

    deduped: Dict[Tuple, FlightResult] = {}
    for r in rows:
        key = _dedupe_key(r)
        existing = deduped.get(key)
        if existing is None or (r.price or float("inf")) < (existing.price or float("inf")):
            deduped[key] = r

    deduped_rows = list(deduped.values())
    median_duration = float(median([r.duration_minutes for r in deduped_rows]))
    ranked = sorted(deduped_rows, key=lambda r: _quality_tuple(r, median_duration))

    cap = DEFAULT_RESULT_CAP if requested_limit is None else min(requested_limit, MAX_RESULT_CAP)

    selected: List[FlightResult] = []
    cluster_counts: Dict[Tuple, int] = {}
    for row in ranked:
        cluster = _cluster_key(row)
        if cluster_counts.get(cluster, 0) >= 2:
            continue
        selected.append(row)
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        if len(selected) >= cap:
            break

    return selected, FlightCurationSummary(raw_count=raw_count, deduped_count=len(deduped_rows), returned_count=len(selected))
