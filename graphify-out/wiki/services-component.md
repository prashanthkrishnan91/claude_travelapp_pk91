# services-component

## Overview

Directory-based community: backend/app/services

- **Size**: 56 nodes
- **Cohesion**: 0.1791
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| CardsService | Class | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 12-76 |
| __init__ | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 13-14 |
| list_cards | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 20-29 |
| get_card | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 31-44 |
| create_card | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 50-56 |
| update_card | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 58-73 |
| delete_card | Function | /home/user/claude_travelapp_pk91/backend/app/services/cards.py | 75-76 |
| ItineraryService | Class | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 20-136 |
| __init__ | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 21-22 |
| list_days | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 28-36 |
| get_day | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 38-51 |
| create_day | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 53-59 |
| update_day | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 61-76 |
| delete_day | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 78-79 |
| list_items | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 85-93 |
| get_item | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 95-108 |
| create_item | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 110-116 |
| update_item | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 118-133 |
| delete_item | Function | /home/user/claude_travelapp_pk91/backend/app/services/itinerary.py | 135-136 |
| _cache_key | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 39-42 |
| _now_utc | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 45-46 |
| _mock_flights | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 53-102 |
| _mock_hotels | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 105-147 |
| _mock_attractions | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 150-219 |
| SearchService | Class | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 226-307 |
| __init__ | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 227-228 |
| search_flights | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 234-243 |
| search_hotels | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 245-254 |
| search_attractions | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 256-265 |
| _get_cache | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 271-288 |
| _set_cache | Function | /home/user/claude_travelapp_pk91/backend/app/services/search.py | 290-307 |
| TripsService | Class | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 12-75 |
| __init__ | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 13-14 |
| list_trips | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 20-28 |
| get_trip | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 30-43 |
| create_trip | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 49-55 |
| update_trip | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 57-72 |
| delete_trip | Function | /home/user/claude_travelapp_pk91/backend/app/services/trips.py | 74-75 |
| compute_cpp | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 48-52 |
| cpp_component | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 55-59 |
| rating_component | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 62-66 |
| partner_component | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 69-77 |
| compute_tags | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 80-89 |
| ValueEngine | Class | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 96-115 |
| score | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 99-111 |
| score_batch | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine.py | 113-115 |
| _base_cpp | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine_v2.py | 59-63 |
| _best_bonus_pct | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine_v2.py | 66-77 |
| _is_preferred | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine_v2.py | 80-86 |
| _cpp_component | Function | /home/user/claude_travelapp_pk91/backend/app/services/value_engine_v2.py | 89-93 |

*... and 6 more members.*

## Execution Flows

- **search_flights** (criticality: 0.45, depth: 2)
- **search_hotels** (criticality: 0.45, depth: 2)
- **search_attractions** (criticality: 0.45, depth: 2)
- **score_batch** (criticality: 0.45, depth: 2)
- **score_batch** (criticality: 0.45, depth: 2)
- **update_card** (criticality: 0.36, depth: 1)
- **update_day** (criticality: 0.36, depth: 1)
- **update_item** (criticality: 0.36, depth: 1)
- **update_trip** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `execute` (22 edge(s))
- `table` (22 edge(s))
- `append` (20 edge(s))
- `eq` (17 edge(s))
- `str` (16 edge(s))
- `model_dump` (14 edge(s))
- `round` (12 edge(s))
- `uniform` (10 edge(s))
- `select` (9 edge(s))
- `lower` (9 edge(s))
- `HTTPException` (8 edge(s))
- `min` (8 edge(s))
- `limit` (5 edge(s))
- `insert` (4 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/__init__.py::TravelCard` (4 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/backend/app/services/value_engine_v2.py` (8 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py` (6 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/value_engine.py` (6 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/cards.py` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/itinerary.py` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/search.py::search_flights` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/search.py::search_hotels` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/search.py::search_attractions` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/trips.py` (1 edge(s))
