from .user import User, UserCreate, UserUpdate
from .travel_card import TravelCard, TravelCardCreate, TravelCardUpdate
from .transfer_partner import (
    TransferPartner,
    TransferPartnerCreate,
    TransferPartnerUpdate,
)
from .trip import Trip, TripCreate, TripUpdate, TripStatus
from .itinerary import (
    ItineraryDay,
    ItineraryDayCreate,
    ItineraryDayUpdate,
    ItineraryItem,
    ItineraryItemCreate,
    ItineraryItemDirectCreate,
    ItineraryItemUpdate,
    ItineraryItemType,
    BestOption,
)
from .research_cache import ResearchCache, ResearchCacheCreate
from .preferences import (
    UserPreferences,
    UserPreferencesCreate,
    UserPreferencesUpdate,
    TransferBonus,
    TransferBonusCreate,
)
from .search import (
    BookingOption,
    SearchResult,
    FlightSearchRequest,
    FlightResult,
    HotelSearchRequest,
    HotelResult,
    AttractionSearchRequest,
    AttractionResult,
    SearchCacheEntry,
)

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "TravelCard",
    "TravelCardCreate",
    "TravelCardUpdate",
    "TransferPartner",
    "TransferPartnerCreate",
    "TransferPartnerUpdate",
    "Trip",
    "TripCreate",
    "TripUpdate",
    "TripStatus",
    "ItineraryDay",
    "ItineraryDayCreate",
    "ItineraryDayUpdate",
    "ItineraryItem",
    "ItineraryItemCreate",
    "ItineraryItemDirectCreate",
    "ItineraryItemUpdate",
    "ItineraryItemType",
    "BestOption",
    "ResearchCache",
    "ResearchCacheCreate",
    "BookingOption",
    "SearchResult",
    "FlightSearchRequest",
    "FlightResult",
    "HotelSearchRequest",
    "HotelResult",
    "AttractionSearchRequest",
    "AttractionResult",
    "SearchCacheEntry",
    "UserPreferences",
    "UserPreferencesCreate",
    "UserPreferencesUpdate",
    "TransferBonus",
    "TransferBonusCreate",
]
