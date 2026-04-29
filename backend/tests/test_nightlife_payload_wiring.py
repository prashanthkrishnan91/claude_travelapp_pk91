from app.models.concierge import GoogleVerification, UnifiedRestaurantResult
from app.services.concierge import _clean_reason_text
from app.services.live_research import _build_supporting_details, _is_obvious_non_venue
from app.concierge.contracts import PlaceRecommendationsResponse


def test_supporting_details_and_top_level_reason_can_be_aligned():
    gv = GoogleVerification(name="Scotch Lodge", formatted_address="215 SE 9th Ave, Portland, OR", types=["cocktail_bar", "bar"], rating=4.6, user_rating_count=1200)
    venue = UnifiedRestaurantResult(name="Scotch Lodge", cuisine="Cocktail Bar")
    details = _build_supporting_details(venue, gv, why_pick="A well-regarded cocktail bar with serious spirit depth.", intent="nightlife", user_query="cocktail bars")
    assert details.why_pick is not None


def test_non_venue_candidate_guard_blocks_obvious_noise():
    assert _is_obvious_non_venue("Eater Portland\nPEARL DISTRICT", "Portland")
    assert _is_obvious_non_venue("Kerns", "Portland")
    assert _is_obvious_non_venue("Here is the current menu", "Portland")


def test_place_response_parses_bars_without_restaurant_cuisine():
    payload = {
        "response": "bars",
        "suggestions": [],
        "restaurants": [
            {
                "type": "verified_place",
                "name": "Scotch Lodge",
                "source": "Live search",
                "cuisine": None,
                "why_pick": "A well-regarded cocktail bar.",
                "primary_reason": "A well-regarded cocktail bar.",
                "supporting_details": {"why_pick": "A well-regarded cocktail bar."},
                "display": {"display_name": "Scotch Lodge", "display_category": "Cocktail Bar", "display_why": "A well-regarded cocktail bar.", "display_badges": []},
            }
        ],
        "attractions": [],
        "hotels": [],
        "areas": [],
        "research_sources": [],
        "source_status": "live_search",
        "retrieval_used": True,
        "intent": "nightlife",
    }
    parsed = PlaceRecommendationsResponse(**payload)
    assert parsed.restaurants[0].cuisine is None


def test_tiny_proof_payload_has_consistent_reason_fields():
    reason = "A well-regarded cocktail bar with deep local praise."
    payload = {
        "name": "Scotch Lodge",
        "whyPick": reason,
        "supportingDetails": {"whyPick": reason},
        "display": {"displayWhy": reason},
    }
    assert isinstance(payload["whyPick"], str)
    assert payload["whyPick"] == payload["supportingDetails"]["whyPick"] == payload["display"]["displayWhy"]


def test_banned_fragments_are_removed_from_user_facing_reasons():
    raw = (
        "Precision cocktails... Sample bar research data · verify hours and current status before booking. "
        "Static sample profile; verify current hours and status.."
    )
    cleaned = _clean_reason_text(
        text=raw,
        name="Kumiko",
        category="Speakeasy",
        rating=4.7,
        review_count=1200,
        neighborhood="West Loop",
        intent="nightlife",
    )
    low = cleaned.lower()
    for fragment in (
        "sample",
        "static sample",
        "research data",
        "verify hours",
        "verify current status",
        "before booking",
        "..",
    ):
        assert fragment not in low
