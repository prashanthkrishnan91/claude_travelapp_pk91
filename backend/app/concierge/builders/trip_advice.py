"""Trip advice builder for non-place concierge prompts."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class AdviceCitation(BaseModel):
    label: str
    url: str


class AdviceSection(BaseModel):
    heading: str
    body_markdown: str


class TripAdvicePayload(BaseModel):
    response: str
    advice_sections: List[AdviceSection] = Field(default_factory=list)
    citations: List[AdviceCitation] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _mentions(text: str, *keywords: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def build_trip_advice_payload(user_query: str) -> TripAdvicePayload:
    """Generate structured advice sections for rewards/trip strategy prompts.

    This intentionally uses deterministic, structured guidance so the trip-advice
    mode remains useful even when no external provider is configured.
    """
    query = (user_query or "").strip()
    query_lower = query.lower()

    section_1 = AdviceSection(
        heading="Points vs cash decision framework",
        body_markdown=(
            "### Quick rule of thumb\n"
            "Use points when your redemption value beats your personal floor value (often around **1.3–1.8 cents/point** for flexible currencies). "
            "Pay cash when fares are cheap and save points for expensive travel windows.\n\n"
            "### Fast math\n"
            "`CPP = (cash price - taxes on award) / points required`\n\n"
            "| Scenario | Typical move | Why |\n"
            "|---|---|---|\n"
            "| Low cash fare + high points price | Pay cash | Preserve points for high-value redemptions |\n"
            "| Peak season cash fare + reasonable award price | Use points | Locks in value during surge pricing |\n"
            "| Transfer bonus available | Usually points | Effective CPP jumps if award seats exist |"
        ),
    )

    section_2 = AdviceSection(
        heading="How to compare options before booking",
        body_markdown=(
            "1. Price both paths on the same itinerary (including baggage, seat fees, and resort/destination fees).\n"
            "2. Check cancellation flexibility: award bookings are often easier to change, but partner programs vary.\n"
            "3. Estimate opportunity cost: if you pay cash, will you earn points/status that narrow the gap?\n"
            "4. Decide based on **total trip value**, not only headline fare."
        ),
    )

    section_3 = AdviceSection(
        heading="Practical booking plan for this trip",
        body_markdown=(
            f"For your prompt (**{query or 'trip planning'}**), start with two side-by-side searches: one cash, one award. "
            "If the award option is only marginally better, keep points for a harder-to-pay trip (premium cabin, holidays, or last-minute travel). "
            "If you find strong award space now, lock it in and set a fare alert for cash repricing."
        ),
    )

    sections = [section_1, section_2, section_3]

    if _mentions(query_lower, "transfer", "partner", "miles"):
        sections.append(
            AdviceSection(
                heading="Transfer partner guardrails",
                body_markdown=(
                    "Only transfer once you confirm live award space. Transfers are frequently one-way and irreversible. "
                    "When possible, hold award seats first or validate that transfer time is near-instant for your program pair."
                ),
            )
        )

    citations = [
        AdviceCitation(label="TPG: How to decide points vs cash", url="https://thepointsguy.com/guide/when-to-use-points-vs-cash/"),
        AdviceCitation(label="NerdWallet: Point value calculators", url="https://www.nerdwallet.com/travel/learn/airline-miles-and-hotel-points-valuations"),
    ]

    if _mentions(query_lower, "insurance", "cancel", "cancellation"):
        citations.append(
            AdviceCitation(label="DOT: Airline customer protections", url="https://www.transportation.gov/airconsumer")
        )

    return TripAdvicePayload(
        response=(
            "Here are practical points-vs-cash recommendations you can apply immediately. "
            "I focused on decision quality, flexibility, and preserving high-value redemptions."
        ),
        advice_sections=sections[:4],
        citations=citations,
        metadata={"builder": "trip_advice_v1", "section_count": min(len(sections), 4)},
    )
