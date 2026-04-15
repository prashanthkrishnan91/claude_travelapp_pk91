# routes-item

## Overview

Directory-based community: backend/app/routes

- **Size**: 26 nodes
- **Cohesion**: 0.2963
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| list_cards | Function | /home/user/claude_travelapp_pk91/backend/app/routes/cards.py | 14-19 |
| create_card | Function | /home/user/claude_travelapp_pk91/backend/app/routes/cards.py | 23-25 |
| get_card | Function | /home/user/claude_travelapp_pk91/backend/app/routes/cards.py | 29-31 |
| update_card | Function | /home/user/claude_travelapp_pk91/backend/app/routes/cards.py | 35-37 |
| delete_card | Function | /home/user/claude_travelapp_pk91/backend/app/routes/cards.py | 41-43 |
| compare_items | Function | /home/user/claude_travelapp_pk91/backend/app/routes/compare.py | 20-60 |
| list_days | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 25-27 |
| create_day | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 35-37 |
| get_day | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 41-43 |
| update_day | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 47-51 |
| delete_day | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 57-59 |
| list_items | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 69-71 |
| create_item | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 79-83 |
| get_item | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 87-89 |
| update_item | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 93-97 |
| delete_item | Function | /home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py | 101-103 |
| search_flights | Function | /home/user/claude_travelapp_pk91/backend/app/routes/search.py | 22-29 |
| search_hotels | Function | /home/user/claude_travelapp_pk91/backend/app/routes/search.py | 33-40 |
| search_attractions | Function | /home/user/claude_travelapp_pk91/backend/app/routes/search.py | 44-51 |
| list_trips | Function | /home/user/claude_travelapp_pk91/backend/app/routes/trips.py | 14-16 |
| create_trip | Function | /home/user/claude_travelapp_pk91/backend/app/routes/trips.py | 20-22 |
| get_trip | Function | /home/user/claude_travelapp_pk91/backend/app/routes/trips.py | 26-28 |
| update_trip | Function | /home/user/claude_travelapp_pk91/backend/app/routes/trips.py | 32-34 |
| delete_trip | Function | /home/user/claude_travelapp_pk91/backend/app/routes/trips.py | 38-40 |
| score_item | Function | /home/user/claude_travelapp_pk91/backend/app/routes/value.py | 21-45 |
| score_batch | Function | /home/user/claude_travelapp_pk91/backend/app/routes/value.py | 49-54 |

## Execution Flows

- **compare_items** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `/home/user/claude_travelapp_pk91/backend/app/services/__init__.py::ItineraryService` (10 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/__init__.py::CardsService` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/__init__.py::TripsService` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py::SearchService` (3 edge(s))
- `score` (2 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py::ValueEngineV2Request` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py::ItemV2` (1 edge(s))
- `append` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py::CompareResult` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py::CompareResponse` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py::BatchValueScoreResponse` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/backend/app/routes/itinerary.py` (10 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/cards.py` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/trips.py` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/search.py` (3 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/value.py` (2 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/compare.py` (1 edge(s))
