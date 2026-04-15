# models-itinerary

## Overview

Directory-based community: backend/app/models

- **Size**: 61 nodes
- **Cohesion**: 0.0069
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ORMBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/base.py | 8-11 |
| TimestampedBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/base.py | 14-17 |
| ItineraryItemType | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 12-18 |
| BestOption | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 21-23 |
| ItineraryDayBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 28-32 |
| ItineraryDayCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 35-36 |
| ItineraryDayUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 39-43 |
| ItineraryDay | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 46-47 |
| ItineraryItemBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 52-68 |
| ItineraryItemCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 71-73 |
| ItineraryItemUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 76-91 |
| ItineraryItem | Class | /home/user/claude_travelapp_pk91/backend/app/models/itinerary.py | 94-96 |
| UserPreferences | Class | /home/user/claude_travelapp_pk91/backend/app/models/preferences.py | 10-21 |
| UserPreferencesCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/preferences.py | 24-31 |
| UserPreferencesUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/preferences.py | 34-40 |
| TransferBonus | Class | /home/user/claude_travelapp_pk91/backend/app/models/preferences.py | 43-53 |
| TransferBonusCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/preferences.py | 56-61 |
| ResearchCacheBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/research_cache.py | 10-15 |
| ResearchCacheCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/research_cache.py | 18-19 |
| ResearchCache | Class | /home/user/claude_travelapp_pk91/backend/app/models/research_cache.py | 22-24 |
| SearchResult | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 16-25 |
| FlightSearchRequest | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 32-38 |
| FlightResult | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 41-50 |
| HotelSearchRequest | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 57-62 |
| HotelResult | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 65-72 |
| AttractionSearchRequest | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 79-85 |
| AttractionResult | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 88-93 |
| SearchCacheEntry | Class | /home/user/claude_travelapp_pk91/backend/app/models/search.py | 100-107 |
| PartnerType | Class | /home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py | 10-12 |
| TransferPartnerBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py | 15-24 |
| TransferPartnerCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py | 27-28 |
| TransferPartnerUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py | 31-38 |
| TransferPartner | Class | /home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py | 41-42 |
| TravelCardBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/travel_card.py | 10-18 |
| TravelCardCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/travel_card.py | 21-22 |
| TravelCardUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/travel_card.py | 25-32 |
| TravelCard | Class | /home/user/claude_travelapp_pk91/backend/app/models/travel_card.py | 35-36 |
| TripStatus | Class | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 12-18 |
| TripBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 21-38 |
| _validate_dates | Function | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 35-38 |
| TripCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 41-42 |
| TripUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 45-56 |
| Trip | Class | /home/user/claude_travelapp_pk91/backend/app/models/trip.py | 59-60 |
| UserBase | Class | /home/user/claude_travelapp_pk91/backend/app/models/user.py | 9-14 |
| UserCreate | Class | /home/user/claude_travelapp_pk91/backend/app/models/user.py | 17-18 |
| UserUpdate | Class | /home/user/claude_travelapp_pk91/backend/app/models/user.py | 21-25 |
| User | Class | /home/user/claude_travelapp_pk91/backend/app/models/user.py | 28-29 |
| ValueScoreRequest | Class | /home/user/claude_travelapp_pk91/backend/app/models/value_score.py | 8-15 |
| ValueScoreResult | Class | /home/user/claude_travelapp_pk91/backend/app/models/value_score.py | 18-34 |
| BatchValueScoreRequest | Class | /home/user/claude_travelapp_pk91/backend/app/models/value_score.py | 37-40 |

*... and 11 more members.*

## Execution Flows

- **search_flights** (criticality: 0.45, depth: 2)
- **search_hotels** (criticality: 0.45, depth: 2)
- **search_attractions** (criticality: 0.45, depth: 2)
- **score_batch** (criticality: 0.45, depth: 2)
- **score_batch** (criticality: 0.45, depth: 2)
- **compare_items** (criticality: 0.36, depth: 1)

## Dependencies

### Outgoing

- `BaseModel` (24 edge(s))
- `ORMBase` (15 edge(s))
- `TimestampedBase` (6 edge(s))
- `str` (4 edge(s))
- `Enum` (4 edge(s))
- `SearchResult` (3 edge(s))
- `ItineraryDayBase` (2 edge(s))
- `ItineraryItemBase` (2 edge(s))
- `ResearchCacheBase` (2 edge(s))
- `TransferPartnerBase` (2 edge(s))
- `TravelCardBase` (2 edge(s))
- `TripBase` (2 edge(s))
- `UserBase` (2 edge(s))
- `ValueError` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/backend/app/models/value_score.py` (14 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/itinerary.py` (10 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/search.py` (8 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/preferences.py` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/transfer_partner.py` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/trip.py` (5 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/travel_card.py` (4 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/user.py` (4 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/routes/compare.py::compare_items` (4 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/research_cache.py` (3 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/models/base.py` (2 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py::_mock_attractions` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py::SearchService.search_attractions` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py::_mock_flights` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/services/search.py::SearchService.search_flights` (1 edge(s))
