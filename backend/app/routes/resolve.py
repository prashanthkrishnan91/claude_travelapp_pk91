"""Resolve endpoints — city/airport name to IATA code lookup."""

import re
import unicodedata
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/resolve", tags=["resolve"])

# ---------------------------------------------------------------------------
# Static city → airport mapping (MVP)
# ---------------------------------------------------------------------------

_CITY_AIRPORT_MAP = [
    # United States
    {"city": "New York",       "country": "US", "airports": ["JFK", "LGA", "EWR"]},
    {"city": "Los Angeles",    "country": "US", "airports": ["LAX", "BUR", "LGB", "ONT", "SNA"]},
    {"city": "Chicago",        "country": "US", "airports": ["ORD", "MDW"]},
    {"city": "San Francisco",  "country": "US", "airports": ["SFO", "OAK", "SJC"]},
    {"city": "Seattle",        "country": "US", "airports": ["SEA", "PAE"]},
    {"city": "Miami",          "country": "US", "airports": ["MIA", "FLL", "PBI"]},
    {"city": "Boston",         "country": "US", "airports": ["BOS"]},
    {"city": "Washington DC",  "country": "US", "airports": ["DCA", "IAD", "BWI"]},
    {"city": "Dallas",         "country": "US", "airports": ["DFW", "DAL"]},
    {"city": "Atlanta",        "country": "US", "airports": ["ATL"]},
    {"city": "Denver",         "country": "US", "airports": ["DEN"]},
    {"city": "Las Vegas",      "country": "US", "airports": ["LAS"]},
    {"city": "Phoenix",        "country": "US", "airports": ["PHX", "AZA"]},
    {"city": "Houston",        "country": "US", "airports": ["IAH", "HOU"]},
    {"city": "Orlando",        "country": "US", "airports": ["MCO", "SFB"]},
    {"city": "Minneapolis",    "country": "US", "airports": ["MSP"]},
    {"city": "Detroit",        "country": "US", "airports": ["DTW"]},
    {"city": "Portland",       "country": "US", "airports": ["PDX"]},
    {"city": "San Diego",      "country": "US", "airports": ["SAN"]},
    {"city": "Nashville",      "country": "US", "airports": ["BNA"]},
    {"city": "Austin",         "country": "US", "airports": ["AUS"]},
    {"city": "Charlotte",      "country": "US", "airports": ["CLT"]},
    {"city": "New Orleans",    "country": "US", "airports": ["MSY"]},
    {"city": "Salt Lake City", "country": "US", "airports": ["SLC"]},
    {"city": "Tampa",          "country": "US", "airports": ["TPA"]},
    {"city": "Kansas City",    "country": "US", "airports": ["MCI"]},
    {"city": "Philadelphia",   "country": "US", "airports": ["PHL"]},
    {"city": "Pittsburgh",     "country": "US", "airports": ["PIT"]},
    {"city": "Raleigh",        "country": "US", "airports": ["RDU"]},
    {"city": "Cincinnati",     "country": "US", "airports": ["CVG"]},
    {"city": "Indianapolis",   "country": "US", "airports": ["IND"]},
    {"city": "Columbus",       "country": "US", "airports": ["CMH"]},
    {"city": "Cleveland",      "country": "US", "airports": ["CLE"]},
    {"city": "Memphis",        "country": "US", "airports": ["MEM"]},
    {"city": "Oklahoma City",  "country": "US", "airports": ["OKC"]},
    {"city": "Boise",          "country": "US", "airports": ["BOI"]},
    {"city": "Albuquerque",    "country": "US", "airports": ["ABQ"]},
    {"city": "Sacramento",     "country": "US", "airports": ["SMF"]},
    {"city": "Honolulu",       "country": "US", "airports": ["HNL"]},
    {"city": "Anchorage",      "country": "US", "airports": ["ANC"]},
    {"city": "Buffalo",        "country": "US", "airports": ["BUF"]},
    # Canada
    {"city": "Toronto",        "country": "CA", "airports": ["YYZ", "YTZ"]},
    {"city": "Vancouver",      "country": "CA", "airports": ["YVR"]},
    {"city": "Montreal",       "country": "CA", "airports": ["YUL"]},
    {"city": "Calgary",        "country": "CA", "airports": ["YYC"]},
    {"city": "Ottawa",         "country": "CA", "airports": ["YOW"]},
    {"city": "Edmonton",       "country": "CA", "airports": ["YEG"]},
    {"city": "Halifax",        "country": "CA", "airports": ["YHZ"]},
    # United Kingdom / Ireland
    {"city": "London",         "country": "GB", "airports": ["LHR", "LGW", "LCY", "STN", "LTN"]},
    {"city": "Manchester",     "country": "GB", "airports": ["MAN"]},
    {"city": "Edinburgh",      "country": "GB", "airports": ["EDI"]},
    {"city": "Birmingham",     "country": "GB", "airports": ["BHX"]},
    {"city": "Glasgow",        "country": "GB", "airports": ["GLA"]},
    {"city": "Dublin",         "country": "IE", "airports": ["DUB"]},
    # France
    {"city": "Paris",          "country": "FR", "airports": ["CDG", "ORY"]},
    {"city": "Nice",           "country": "FR", "airports": ["NCE"]},
    {"city": "Lyon",           "country": "FR", "airports": ["LYS"]},
    {"city": "Marseille",      "country": "FR", "airports": ["MRS"]},
    # Germany
    {"city": "Frankfurt",      "country": "DE", "airports": ["FRA"]},
    {"city": "Munich",         "country": "DE", "airports": ["MUC"]},
    {"city": "Berlin",         "country": "DE", "airports": ["BER"]},
    {"city": "Hamburg",        "country": "DE", "airports": ["HAM"]},
    {"city": "Dusseldorf",     "country": "DE", "airports": ["DUS"]},
    # Netherlands
    {"city": "Amsterdam",      "country": "NL", "airports": ["AMS"]},
    # Switzerland
    {"city": "Zurich",         "country": "CH", "airports": ["ZRH"]},
    {"city": "Geneva",         "country": "CH", "airports": ["GVA"]},
    # Spain
    {"city": "Barcelona",      "country": "ES", "airports": ["BCN"]},
    {"city": "Madrid",         "country": "ES", "airports": ["MAD"]},
    {"city": "Malaga",         "country": "ES", "airports": ["AGP"]},
    {"city": "Ibiza",          "country": "ES", "airports": ["IBZ"]},
    # Italy
    {"city": "Rome",           "country": "IT", "airports": ["FCO", "CIA"]},
    {"city": "Milan",          "country": "IT", "airports": ["MXP", "LIN", "BGY"]},
    {"city": "Venice",         "country": "IT", "airports": ["VCE"]},
    {"city": "Florence",       "country": "IT", "airports": ["FLR"]},
    {"city": "Naples",         "country": "IT", "airports": ["NAP"]},
    # Portugal
    {"city": "Lisbon",         "country": "PT", "airports": ["LIS"]},
    {"city": "Porto",          "country": "PT", "airports": ["OPO"]},
    # Scandinavia
    {"city": "Stockholm",      "country": "SE", "airports": ["ARN", "BMA"]},
    {"city": "Copenhagen",     "country": "DK", "airports": ["CPH"]},
    {"city": "Oslo",           "country": "NO", "airports": ["OSL"]},
    {"city": "Helsinki",       "country": "FI", "airports": ["HEL"]},
    # Eastern Europe / Turkey / Greece
    {"city": "Istanbul",       "country": "TR", "airports": ["IST", "SAW"]},
    {"city": "Athens",         "country": "GR", "airports": ["ATH"]},
    {"city": "Moscow",         "country": "RU", "airports": ["SVO", "DME", "VKO"]},
    {"city": "Warsaw",         "country": "PL", "airports": ["WAW"]},
    {"city": "Prague",         "country": "CZ", "airports": ["PRG"]},
    {"city": "Vienna",         "country": "AT", "airports": ["VIE"]},
    {"city": "Budapest",       "country": "HU", "airports": ["BUD"]},
    {"city": "Bucharest",      "country": "RO", "airports": ["OTP"]},
    # Middle East
    {"city": "Dubai",          "country": "AE", "airports": ["DXB", "DWC"]},
    {"city": "Abu Dhabi",      "country": "AE", "airports": ["AUH"]},
    {"city": "Doha",           "country": "QA", "airports": ["DOH"]},
    {"city": "Riyadh",         "country": "SA", "airports": ["RUH"]},
    {"city": "Jeddah",         "country": "SA", "airports": ["JED"]},
    {"city": "Tel Aviv",       "country": "IL", "airports": ["TLV"]},
    {"city": "Amman",          "country": "JO", "airports": ["AMM"]},
    # Asia — East
    {"city": "Tokyo",          "country": "JP", "airports": ["NRT", "HND"]},
    {"city": "Osaka",          "country": "JP", "airports": ["KIX", "ITM"]},
    {"city": "Seoul",          "country": "KR", "airports": ["ICN", "GMP"]},
    {"city": "Beijing",        "country": "CN", "airports": ["PEK", "PKX"]},
    {"city": "Shanghai",       "country": "CN", "airports": ["PVG", "SHA"]},
    {"city": "Hong Kong",      "country": "HK", "airports": ["HKG"]},
    {"city": "Taipei",         "country": "TW", "airports": ["TPE", "TSA"]},
    # Asia — Southeast
    {"city": "Singapore",      "country": "SG", "airports": ["SIN"]},
    {"city": "Bangkok",        "country": "TH", "airports": ["BKK", "DMK"]},
    {"city": "Kuala Lumpur",   "country": "MY", "airports": ["KUL"]},
    {"city": "Jakarta",        "country": "ID", "airports": ["CGK"]},
    {"city": "Manila",         "country": "PH", "airports": ["MNL"]},
    {"city": "Bali",           "country": "ID", "airports": ["DPS"]},
    {"city": "Hanoi",          "country": "VN", "airports": ["HAN"]},
    {"city": "Ho Chi Minh City","country": "VN", "airports": ["SGN"]},
    {"city": "Chiang Mai",     "country": "TH", "airports": ["CNX"]},
    {"city": "Phuket",         "country": "TH", "airports": ["HKT"]},
    # Asia — South
    {"city": "Mumbai",         "country": "IN", "airports": ["BOM"]},
    {"city": "Delhi",          "country": "IN", "airports": ["DEL"]},
    {"city": "Bengaluru",      "country": "IN", "airports": ["BLR"]},
    {"city": "Chennai",        "country": "IN", "airports": ["MAA"]},
    {"city": "Hyderabad",      "country": "IN", "airports": ["HYD"]},
    {"city": "Kolkata",        "country": "IN", "airports": ["CCU"]},
    {"city": "Colombo",        "country": "LK", "airports": ["CMB"]},
    {"city": "Kathmandu",      "country": "NP", "airports": ["KTM"]},
    {"city": "Karachi",        "country": "PK", "airports": ["KHI"]},
    {"city": "Lahore",         "country": "PK", "airports": ["LHE"]},
    {"city": "Islamabad",      "country": "PK", "airports": ["ISB"]},
    # Australia / Pacific
    {"city": "Sydney",         "country": "AU", "airports": ["SYD"]},
    {"city": "Melbourne",      "country": "AU", "airports": ["MEL"]},
    {"city": "Brisbane",       "country": "AU", "airports": ["BNE"]},
    {"city": "Perth",          "country": "AU", "airports": ["PER"]},
    {"city": "Adelaide",       "country": "AU", "airports": ["ADL"]},
    {"city": "Auckland",       "country": "NZ", "airports": ["AKL"]},
    {"city": "Wellington",     "country": "NZ", "airports": ["WLG"]},
    # Latin America
    {"city": "Mexico City",    "country": "MX", "airports": ["MEX"]},
    {"city": "Cancun",         "country": "MX", "airports": ["CUN"]},
    {"city": "Guadalajara",    "country": "MX", "airports": ["GDL"]},
    {"city": "Buenos Aires",   "country": "AR", "airports": ["EZE", "AEP"]},
    {"city": "Sao Paulo",      "country": "BR", "airports": ["GRU", "CGH"]},
    {"city": "Rio de Janeiro", "country": "BR", "airports": ["GIG", "SDU"]},
    {"city": "Santiago",       "country": "CL", "airports": ["SCL"]},
    {"city": "Lima",           "country": "PE", "airports": ["LIM"]},
    {"city": "Bogota",         "country": "CO", "airports": ["BOG"]},
    {"city": "Medellin",       "country": "CO", "airports": ["MDE"]},
    {"city": "Panama City",    "country": "PA", "airports": ["PTY"]},
    {"city": "Havana",         "country": "CU", "airports": ["HAV"]},
    # Africa
    {"city": "Cairo",          "country": "EG", "airports": ["CAI"]},
    {"city": "Cape Town",      "country": "ZA", "airports": ["CPT"]},
    {"city": "Johannesburg",   "country": "ZA", "airports": ["JNB"]},
    {"city": "Nairobi",        "country": "KE", "airports": ["NBO"]},
    {"city": "Lagos",          "country": "NG", "airports": ["LOS"]},
    {"city": "Casablanca",     "country": "MA", "airports": ["CMN"]},
    {"city": "Addis Ababa",    "country": "ET", "airports": ["ADD"]},
    {"city": "Zanzibar",       "country": "TZ", "airports": ["ZNZ"]},
]

# Build a flat lookup: IATA code → entry (for direct code search)
_IATA_INDEX: dict = {}
for _entry in _CITY_AIRPORT_MAP:
    for _code in _entry["airports"]:
        _IATA_INDEX[_code] = _entry


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AirportResolveRequest(BaseModel):
    query: str


class AirportMatch(BaseModel):
    city: str
    country: str
    airports: List[str]


class AirportResolveResponse(BaseModel):
    matches: List[AirportMatch]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip diacritics, keep only alphanumeric + spaces."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]", "", ascii_str).strip()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/airports", response_model=AirportResolveResponse)
def resolve_airports(payload: AirportResolveRequest) -> AirportResolveResponse:
    """Resolve a city name or partial string to IATA airport codes.

    Returns up to 10 matching cities with their airport codes.
    Also matches if the query is a direct 3-letter IATA code.
    """
    raw = payload.query.strip()
    if len(raw) < 2:
        return AirportResolveResponse(matches=[])

    q = _normalize(raw)
    iata_upper = raw.upper()

    seen: set = set()
    exact: list = []
    partial: list = []

    for entry in _CITY_AIRPORT_MAP:
        key = f"{entry['city']}|{entry['country']}"
        if key in seen:
            continue

        city_norm = _normalize(entry["city"])

        # Direct IATA code match
        if len(iata_upper) == 3 and iata_upper in entry["airports"]:
            exact.append(entry)
            seen.add(key)
            continue

        # City prefix match (highest priority)
        if city_norm.startswith(q):
            exact.append(entry)
            seen.add(key)
            continue

        # Substring match
        if q in city_norm:
            partial.append(entry)
            seen.add(key)

    combined = exact + partial
    matches = [
        AirportMatch(city=e["city"], country=e["country"], airports=e["airports"])
        for e in combined[:10]
    ]
    return AirportResolveResponse(matches=matches)
