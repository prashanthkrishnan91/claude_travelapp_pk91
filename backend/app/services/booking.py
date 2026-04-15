"""Booking link generator — produce provider deep-links from an ItineraryItem.

Generates pre-filled booking URLs for each supported provider based on the
item type and available metadata (title, location, dates).  The URLs use the
mock ``book.example.com`` domain; swap in real partner SDK calls when live
API keys are available.
"""

from typing import List
from urllib.parse import quote_plus

from app.models import ItineraryItem, ItineraryItemType
from app.models.search import BookingOption


def _slug(text: str) -> str:
    """Convert arbitrary text to a URL-safe slug."""
    return quote_plus(text.lower().replace(" ", "-").replace(",", "").replace("&", "and"))


def generate_booking_links(item: ItineraryItem) -> List[BookingOption]:
    """Return booking options for *item* based on its type and metadata.

    Each option carries a ``provider`` label and a ``url`` deep-link.
    Options are ordered: direct providers first, then points portals.
    """
    title = _slug(item.title)
    location = _slug(item.location or "")

    # Build date query params when available
    date_params = ""
    if item.start_time:
        date_params += f"&checkin={item.start_time.date().isoformat()}"
    if item.end_time:
        date_params += f"&checkout={item.end_time.date().isoformat()}"

    if item.item_type == ItineraryItemType.FLIGHT:
        return [
            BookingOption(
                provider="google_flights",
                url=f"https://book.example.com/flights/google/{title}{date_params}",
            ),
            BookingOption(
                provider="kayak",
                url=f"https://book.example.com/flights/kayak/{title}{date_params}",
            ),
            BookingOption(
                provider="expedia",
                url=f"https://book.example.com/flights/expedia/{title}{date_params}",
            ),
            BookingOption(
                provider="chase_portal",
                url=f"https://book.example.com/flights/chase/{title}{date_params}",
            ),
            BookingOption(
                provider="amex_travel",
                url=f"https://book.example.com/flights/amex/{title}{date_params}",
            ),
        ]

    if item.item_type == ItineraryItemType.HOTEL:
        return [
            BookingOption(
                provider="booking_com",
                url=f"https://book.example.com/hotels/booking/{title}?location={location}{date_params}",
            ),
            BookingOption(
                provider="expedia",
                url=f"https://book.example.com/hotels/expedia/{title}?location={location}{date_params}",
            ),
            BookingOption(
                provider="hotels_com",
                url=f"https://book.example.com/hotels/hotels-com/{title}?location={location}{date_params}",
            ),
            BookingOption(
                provider="chase_portal",
                url=f"https://book.example.com/hotels/chase/{location}{date_params}",
            ),
            BookingOption(
                provider="amex_travel",
                url=f"https://book.example.com/hotels/amex/{location}{date_params}",
            ),
        ]

    # activity / meal / transit / note — use experiences platforms
    return [
        BookingOption(
            provider="viator",
            url=f"https://book.example.com/activities/viator/{title}?location={location}{date_params}",
        ),
        BookingOption(
            provider="getyourguide",
            url=f"https://book.example.com/activities/gyg/{title}?location={location}{date_params}",
        ),
        BookingOption(
            provider="klook",
            url=f"https://book.example.com/activities/klook/{location}{date_params}",
        ),
    ]
