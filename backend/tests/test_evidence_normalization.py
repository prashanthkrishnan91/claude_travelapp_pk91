"""Tests for evidence normalization pipeline."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.concierge.evidence import (
    EvidenceUnit,
    _WhyPickCache,
    _eid,
    evidence_cache_key,
    normalize_evidence,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_google_verification(
    rating=4.5,
    user_rating_count=1200,
    formatted_address="123 W Randolph St, Chicago, IL",
    types=None,
):
    return SimpleNamespace(
        rating=rating,
        user_rating_count=user_rating_count,
        formatted_address=formatted_address,
        types=types or ["cocktail_bar"],
    )


def _make_source_evidence(
    source_reason="Featured in a local guide for its inventive cocktails",
    source_evidence="Known for low-ABV options and seasonal menus",
    source_domain="eater.com",
    mention_count=2,
):
    return SimpleNamespace(
        source_reason=source_reason,
        source_evidence=source_evidence,
        source_domain=source_domain,
        mention_count=mention_count,
    )


def _make_enrichment(
    yelp_rating=4.4,
    yelp_review_count=980,
    yelp_review_excerpts=None,
    foursquare_categories=None,
    foursquare_tags=None,
):
    return SimpleNamespace(
        yelp_rating=yelp_rating,
        yelp_review_count=yelp_review_count,
        yelp_review_excerpts=yelp_review_excerpts or [],
        foursquare_categories=foursquare_categories or [],
        foursquare_tags=foursquare_tags or [],
    )


# ── EvidenceUnit structure ───────────────────────────────────────────────────

def test_normalize_evidence_google_creates_rating_unit():
    gv = _make_google_verification(rating=4.6, user_rating_count=2100)
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    rating_units = [u for u in units if u.claim_type == "rating"]
    assert len(rating_units) == 1
    assert "4.6" in rating_units[0].claim
    assert "2,100" in rating_units[0].claim
    assert rating_units[0].source_family == "google"
    assert rating_units[0].confidence == "high"
    assert rating_units[0].safe_for_copy is True


def test_normalize_evidence_google_creates_verified_unit():
    gv = _make_google_verification()
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    verified_units = [u for u in units if u.claim_type == "google_verified"]
    assert len(verified_units) == 1
    assert verified_units[0].safe_for_copy is True
    assert verified_units[0].confidence == "high"


def test_normalize_evidence_google_location_not_safe_for_copy():
    gv = _make_google_verification(formatted_address="123 W Randolph St, Chicago")
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    location_units = [u for u in units if u.claim_type == "location"]
    assert len(location_units) == 1
    assert location_units[0].safe_for_copy is False
    assert "123 W Randolph" in location_units[0].claim


def test_normalize_evidence_no_google_returns_no_google_units():
    units = normalize_evidence(venue_name="Place A", category="restaurant", google_verification=None)
    google_units = [u for u in units if u.source_family == "google"]
    assert google_units == []


def test_normalize_evidence_michelin_status():
    units = normalize_evidence(
        venue_name="Alinea",
        category="restaurant",
        michelin_status="3 Stars",
    )
    michelin_units = [u for u in units if u.claim_type == "michelin_status"]
    assert len(michelin_units) == 1
    assert "3 Stars" in michelin_units[0].claim
    assert michelin_units[0].confidence == "high"
    assert michelin_units[0].safe_for_copy is True


def test_normalize_evidence_editorial_source_reason():
    se = _make_source_evidence(source_reason="One of the best cocktail bars in West Loop")
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", source_evidence=se)
    editorial_units = [u for u in units if u.claim_type == "editorial_mention" and u.safe_for_copy]
    assert len(editorial_units) == 1
    assert "West Loop" in editorial_units[0].claim
    assert editorial_units[0].source_family == "editorial"
    assert editorial_units[0].confidence == "medium"


def test_normalize_evidence_editorial_raw_text_not_safe_for_copy():
    se = _make_source_evidence(
        source_reason="Featured in local guide",
        source_evidence="Some raw snippet text from article",
    )
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", source_evidence=se)
    unsafe_editorial = [u for u in units if u.claim_type == "editorial_mention" and not u.safe_for_copy]
    assert len(unsafe_editorial) == 1
    assert unsafe_editorial[0].confidence == "low"


def test_normalize_evidence_editorial_dedupes_when_reason_equals_evidence():
    se = _make_source_evidence(
        source_reason="Featured in local guide",
        source_evidence="Featured in local guide",  # same as source_reason
    )
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", source_evidence=se)
    editorial_units = [u for u in units if u.claim_type == "editorial_mention"]
    assert len(editorial_units) == 1


def test_normalize_evidence_yelp_not_safe_for_copy():
    enrichment = _make_enrichment(yelp_rating=4.3, yelp_review_count=500)
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", enrichment=enrichment)
    yelp_units = [u for u in units if u.claim_type == "yelp_rating"]
    assert len(yelp_units) == 1
    assert yelp_units[0].safe_for_copy is False
    assert yelp_units[0].source_family == "yelp"
    assert "4.3" in yelp_units[0].claim


def test_normalize_evidence_foursquare_generic_tags_not_safe_for_copy():
    # "trendy" and "date-night" are generic — must stay safe_for_copy=False.
    enrichment = _make_enrichment(
        foursquare_categories=["Cocktail Bar", "Lounge"],
        foursquare_tags=["trendy", "date-night"],
    )
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", enrichment=enrichment)
    fs_units = [u for u in units if u.source_family == "foursquare"]
    assert len(fs_units) > 0
    assert all(u.safe_for_copy is False for u in fs_units)


def test_normalize_evidence_specific_foursquare_tag_safe_for_copy():
    # "craft cocktails" is a venue-specific differentiator → safe_for_copy=True.
    enrichment = _make_enrichment(foursquare_tags=["craft cocktails"])
    units = normalize_evidence(venue_name="Boka Bar", category="bar", enrichment=enrichment)
    tag_units = [u for u in units if u.claim_type == "foursquare_tag"]
    assert len(tag_units) == 1
    assert tag_units[0].safe_for_copy is True
    assert tag_units[0].confidence == "medium"


def test_normalize_evidence_specific_foursquare_tags_mixed():
    # Specific tags become safe; generic tags stay unsafe.
    enrichment = _make_enrichment(
        foursquare_tags=["handmade tortillas", "trendy", "mezcal cocktails"],
    )
    units = normalize_evidence(venue_name="Mas Maiz", category="restaurant", enrichment=enrichment)
    tag_units = [u for u in units if u.claim_type == "foursquare_tag"]
    safe = [u for u in tag_units if u.safe_for_copy]
    unsafe = [u for u in tag_units if not u.safe_for_copy]
    assert len(safe) == 2   # handmade tortillas, mezcal cocktails
    assert len(unsafe) == 1  # trendy


def test_normalize_evidence_tavily_award_signal_extracted_as_attribute():
    # Tavily snippet containing "Michelin-starred" yields an attribute unit.
    snippets = ["Alinea is a three Michelin star restaurant serving avant-garde cuisine."]
    units = normalize_evidence(venue_name="Alinea", category="restaurant", tavily_snippets=snippets)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "tavily"]
    assert len(attr_units) == 1
    assert "Michelin" in attr_units[0].claim or "michelin" in attr_units[0].claim.lower()
    assert attr_units[0].safe_for_copy is True
    assert attr_units[0].confidence == "medium"


def test_normalize_evidence_tavily_no_award_no_attribute():
    # Generic Tavily snippet without award mention → no attribute unit.
    snippets = ["A great place to eat in Chicago with good food."]
    units = normalize_evidence(venue_name="Some Cafe", category="restaurant", tavily_snippets=snippets)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "tavily"]
    assert len(attr_units) == 0


def test_normalize_evidence_yelp_excerpt_known_for_extracted():
    # Yelp review excerpt with "known for X" yields an attribute unit.
    enrichment = _make_enrichment(
        yelp_review_excerpts=["This place is known for its handmade pasta and seasonal ingredients."]
    )
    units = normalize_evidence(venue_name="Dario's", category="restaurant", enrichment=enrichment)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "yelp"]
    assert len(attr_units) == 1
    assert "handmade pasta" in attr_units[0].claim
    assert attr_units[0].safe_for_copy is True




def test_normalize_evidence_foursquare_new_generic_tags_not_safe_for_copy():
    enrichment = _make_enrichment(foursquare_tags=["cocktail bar", "highly rated", "good drinks", "nightlife"])
    units = normalize_evidence(venue_name="Night Spot", category="bar", enrichment=enrichment)
    tag_units = [u for u in units if u.claim_type == "foursquare_tag"]
    assert len(tag_units) == 3  # capped at 3
    assert all(u.safe_for_copy is False for u in tag_units)


def test_normalize_evidence_yelp_known_for_generic_signal_rejected():
    enrichment = _make_enrichment(
        yelp_review_excerpts=["This place is known for good drinks and friendly service."]
    )
    units = normalize_evidence(venue_name="Some Bar", category="bar", enrichment=enrichment)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "yelp"]
    assert attr_units == []


def test_normalize_evidence_yelp_known_for_specific_signal_kept():
    enrichment = _make_enrichment(
        yelp_review_excerpts=["The bar is known for Japanese-inspired cocktails and a zero-waste program."]
    )
    units = normalize_evidence(venue_name="Kumiko", category="bar", enrichment=enrichment)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "yelp"]
    assert len(attr_units) == 1
    assert "japanese-inspired cocktails" in attr_units[0].claim.lower()
def test_normalize_evidence_yelp_excerpt_no_signal_no_attribute():
    # Generic Yelp excerpt without "known for" → no attribute unit.
    enrichment = _make_enrichment(yelp_review_excerpts=["Great service and delicious food!"])
    units = normalize_evidence(venue_name="Some Place", category="restaurant", enrichment=enrichment)
    attr_units = [u for u in units if u.claim_type == "attribute" and u.source_family == "yelp"]
    assert len(attr_units) == 0


def test_normalize_evidence_foursquare_capped_at_2_categories_3_tags():
    enrichment = _make_enrichment(
        foursquare_categories=["Cat1", "Cat2", "Cat3"],
        foursquare_tags=["t1", "t2", "t3", "t4"],
    )
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", enrichment=enrichment)
    cats = [u for u in units if u.claim_type == "foursquare_category"]
    tags = [u for u in units if u.claim_type == "foursquare_tag"]
    assert len(cats) == 2
    assert len(tags) == 3


def test_normalize_evidence_tavily_snippets_not_safe_for_copy():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        tavily_snippets=["A great bar with lots of unique cocktails", "Another snippet"],
    )
    tavily_units = [u for u in units if u.claim_type == "tavily_snippet"]
    assert len(tavily_units) == 2
    assert all(u.safe_for_copy is False for u in tavily_units)


def test_normalize_evidence_tavily_short_snippets_skipped():
    units = normalize_evidence(
        venue_name="Billy Sunday",
        category="bar",
        tavily_snippets=["ok", ""],
    )
    tavily_units = [u for u in units if u.claim_type == "tavily_snippet"]
    assert len(tavily_units) == 0


def test_normalize_evidence_venue_name_on_all_units():
    gv = _make_google_verification()
    se = _make_source_evidence()
    units = normalize_evidence(
        venue_name="The Aviary",
        category="bar",
        google_verification=gv,
        source_evidence=se,
    )
    assert all(u.venue_name == "The Aviary" for u in units)


def test_normalize_evidence_category_on_all_units():
    gv = _make_google_verification()
    units = normalize_evidence(venue_name="Au Cheval", category="restaurant", google_verification=gv)
    assert all(u.category == "restaurant" for u in units)


def test_normalize_evidence_ids_are_deterministic():
    gv = _make_google_verification()
    units1 = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    units2 = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    assert [u.id for u in units1] == [u.id for u in units2]


def test_normalize_evidence_all_none_inputs_returns_empty():
    units = normalize_evidence(venue_name="Place", category="restaurant")
    assert units == []


# ── evidence_cache_key ───────────────────────────────────────────────────────

def test_evidence_cache_key_is_deterministic():
    gv = _make_google_verification()
    units = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    k1 = evidence_cache_key("Billy Sunday", "Chicago", "nightlife", units)
    k2 = evidence_cache_key("Billy Sunday", "Chicago", "nightlife", units)
    assert k1 == k2


def test_evidence_cache_key_differs_by_venue():
    gv = _make_google_verification()
    units_a = normalize_evidence(venue_name="Billy Sunday", category="bar", google_verification=gv)
    units_b = normalize_evidence(venue_name="The Aviary", category="bar", google_verification=gv)
    # units differ because venue_name is in claim text for some types
    k_a = evidence_cache_key("Billy Sunday", "Chicago", "nightlife", units_a)
    k_b = evidence_cache_key("The Aviary", "Chicago", "nightlife", units_b)
    assert k_a != k_b


def test_evidence_cache_key_format():
    units = normalize_evidence(
        venue_name="Test Venue",
        category="bar",
        google_verification=_make_google_verification(),
    )
    key = evidence_cache_key("Test Venue", "Chicago", "nightlife", units)
    assert key.startswith("whypick:")
    parts = key.split(":")
    assert len(parts) == 5


def test_evidence_cache_key_empty_units():
    key = evidence_cache_key("Place", "City", "intent", [])
    assert key.startswith("whypick:")


# ── _WhyPickCache ────────────────────────────────────────────────────────────

def test_whypick_cache_set_and_get():
    cache = _WhyPickCache(ttl_seconds=10)
    cache.set("k1", {"whyPick": "test"})
    result = cache.get("k1")
    assert result == {"whyPick": "test"}


def test_whypick_cache_miss_returns_none():
    cache = _WhyPickCache(ttl_seconds=10)
    assert cache.get("nonexistent") is None


def test_whypick_cache_expired_returns_none():
    import time
    cache = _WhyPickCache(ttl_seconds=0)
    cache.set("k1", {"whyPick": "test"})
    time.sleep(0.01)
    assert cache.get("k1") is None


def test_whypick_cache_thread_safe_concurrent_sets():
    import threading
    cache = _WhyPickCache(ttl_seconds=60)
    errors = []

    def writer(i):
        try:
            cache.set(f"key_{i}", {"whyPick": f"result_{i}"})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    for i in range(20):
        assert cache.get(f"key_{i}") == {"whyPick": f"result_{i}"}
