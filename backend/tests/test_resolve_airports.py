from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_RESOLVE_PATH = Path(__file__).resolve().parents[1] / "app" / "routes" / "resolve.py"
_SPEC = spec_from_file_location("resolve_route_for_tests", _RESOLVE_PATH)
assert _SPEC and _SPEC.loader
_MOD = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

search_airport_matches = _MOD.search_airport_matches


def _cities_for(query: str) -> list[str]:
    return [m.city for m in search_airport_matches(query)]


def test_resolve_supports_maui_alias():
    cities = _cities_for("Maui")
    assert "Kahului" in cities


def test_resolve_supports_kahului_airport_alias():
    cities = _cities_for("Kahului Airport")
    assert "Kahului" in cities


def test_resolve_supports_ogg_iata():
    cities = _cities_for("OGG")
    assert "Kahului" in cities


def test_resolve_short_query_returns_empty_list():
    assert search_airport_matches("m") == []


def test_resolve_alias_substring_requires_minimum_length():
    cities = _cities_for("aw")
    assert "Kahului" not in cities
