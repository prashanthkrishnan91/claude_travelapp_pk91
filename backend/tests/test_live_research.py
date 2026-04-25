"""Tests for the Live Research Layer v1."""

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

# Allow imports from backend/app without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.models.concierge import (
    INTENT_ATTRACTIONS,
    INTENT_HIDDEN_GEMS,
    INTENT_HOTELS,
    INTENT_LUXURY_VALUE,
    INTENT_MICHELIN_RESTAURANTS,
    INTENT_NIGHTLIFE,
    INTENT_RESTAURANTS,
    SOURCE_LIVE_SEARCH,
    SOURCE_MIXED,
    SOURCE_NONE,
    SOURCE_SAMPLE_DATA,
    SOURCE_UNAVAILABLE,
)
from app.services.concierge import ConciergeService
from app.services.live_research import (
    LiveResearchResult,
    LiveResearchService,
    LiveSearchHit,
    StubLiveSearchProvider,
    VerificationResult,
    _NoopProvider,
    _TTLCache,
    _VERIFICATION_CACHE,
    _build_verification_query,
    _check_verification_hits,
    _extract_venue_names_from_text,
    _final_hard_filter_closed_venues,
    _is_obvious_non_venue,
    _validate_venue_candidate,
    normalize_hits,
    reset_global_cache,
    select_default_provider,
)

FAKE_TRIP_ID = UUID("00000000-0000-0000-0000-000000000001")
FAKE_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

import json
_FAKE_CLAUDE_JSON = json.dumps({"response": "ok", "suggestions": []})


# ── Provider selection ───────────────────────────────────────────────────────

class TestProviderSelection:
    def test_no_keys_returns_noop(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        provider = select_default_provider()
        assert isinstance(provider, _NoopProvider)
        assert provider.available is False
        assert provider.search("anything") == []

    def test_tavily_key_selected_first(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-fake")
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-fake")
        provider = select_default_provider()
        assert provider.name == "Tavily"
        assert provider.available is True

    def test_brave_picked_when_no_tavily(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "brave-fake")
        provider = select_default_provider()
        assert provider.name == "Brave Search"

    def test_serper_picked_when_only_serper(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.setenv("SERPER_API_KEY", "serper-fake")
        provider = select_default_provider()
        assert provider.name.startswith("Google")


# ── Normalization ────────────────────────────────────────────────────────────

def _hit(title: str, url: str = "https://example.com", snippet: str = "", *, fetched_at=None):
    return LiveSearchHit(
        title=title,
        url=url,
        snippet=snippet,
        provider="Tavily",
        fetched_at=fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


class TestNormalization:
    def test_restaurant_intent_produces_restaurant_cards(self):
        hits = [
            _hit("Boka — Lincoln Park", "https://example.com/boka", "Modern American dining."),
            _hit("Smyth | West Loop", "https://example.com/smyth", "Tasting menu."),
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")
        assert len(out["restaurants"]) == 2
        assert out["restaurants"][0].name == "Boka"  # publisher suffix stripped
        assert out["restaurants"][0].source.startswith("Live search")
        assert out["restaurants"][0].source_url == "https://example.com/boka"
        assert out["restaurants"][0].last_verified_at
        assert out["restaurants"][0].confidence in {"high", "medium", "low", "unknown"}
        assert out["attractions"] == []
        assert out["hotels"] == []

    def test_nightlife_intent_tags_cocktail_bar(self):
        hits = [_hit("The Office at The Aviary", "https://ex.com/aviary", "Cocktail destination in West Loop.")]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert len(out["restaurants"]) == 1
        card = out["restaurants"][0]
        assert card.cuisine == "Cocktail Bar"
        assert "Nightlife" in (card.tags or [])

    def test_attraction_intent_produces_attraction_cards(self):
        hits = [_hit("Millennium Park", "https://ex.com/mp", "Iconic downtown park.")]
        out = normalize_hits(hits, intent=INTENT_ATTRACTIONS, destination="Chicago", user_query="things to do")
        assert len(out["attractions"]) == 1
        assert out["attractions"][0].source_url == "https://ex.com/mp"
        assert out["restaurants"] == []

    def test_hotel_intent_produces_hotel_cards(self):
        hits = [_hit("Pendry Chicago", "https://ex.com/pendry", "Luxury hotel near Magnificent Mile.")]
        out = normalize_hits(hits, intent=INTENT_HOTELS, destination="Chicago", user_query="best hotels")
        assert len(out["hotels"]) == 1
        assert out["hotels"][0].source_url == "https://ex.com/pendry"
        assert out["hotels"][0].source.startswith("Live search")

    def test_permanently_closed_venues_filtered(self):
        hits = [
            _hit("The Violet Hour", snippet="The Violet Hour has permanently closed in 2024."),
            _hit("Three Dots and a Dash", snippet="Beloved tiki bar still serving rum drinks."),
            _hit("Old Spot", snippet="This restaurant is closed permanently following a fire."),
            _hit("Grace", snippet="Grace shut down years ago."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        names = [r.name for r in out["restaurants"]]
        assert "The Violet Hour" not in names
        assert "Old Spot" not in names
        assert "Grace" not in names
        assert "Three Dots and a Dash" in names

    def test_violet_hour_closed_for_final_time_is_not_addable(self):
        hits = [
            _hit(
                "Chicago Cocktail News",
                "https://example.com/chicago-cocktail-news",
                "The Violet Hour closed for the final time after a decade run in Wicker Park.",
            ),
            _hit("Kumiko", "https://example.com/kumiko", "Cocktail bar at 630 W Lake St, Chicago."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        names = [r.name for r in out["restaurants"]]
        assert "The Violet Hour" not in names
        assert "Kumiko" in names
        assert any("appears closed" in (s.summary or "").lower() for s in out["research_sources"])

    def test_violet_hour_closed_signal_in_raw_text_never_returns_live_addable_card(self):
        research_sources = []
        venues = [{
            "name": "The Violet Hour",
            "source": "Live search · Tavily",
            "sourceText": "The Violet Hour has closed for good and won't reopen.",
            "sourceUrl": "https://example.com/violet-hour-update",
            "confidence": "high",
        }]
        filtered = _final_hard_filter_closed_venues(
            venues,
            kind_label="venue",
            research_sources=research_sources,
        )
        assert filtered == []
        assert len(research_sources) == 1
        assert research_sources[0].trip_addable is False

    def test_freshness_confidence_high_for_recent(self):
        recent = datetime.now(timezone.utc).isoformat(timespec="seconds")
        old = (datetime.now(timezone.utc) - timedelta(days=720)).isoformat(timespec="seconds")
        hits = [
            _hit("Recent Pick", snippet="Great spot.", fetched_at=recent),
            _hit("Old Pick", snippet="Great spot.", fetched_at=old),
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="x")
        confidences = {r.name: r.confidence for r in out["restaurants"]}
        assert confidences["Recent Pick"] == "high"
        assert confidences["Old Pick"] == "low"

    def test_no_fabricated_ratings_or_reviews(self):
        hits = [_hit("Mystery Spot", snippet="No rating or review count visible.")]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="x")
        card = out["restaurants"][0]
        assert card.rating is None
        assert card.review_count is None

    def test_listicle_title_not_trip_addable_venue(self):
        hits = [
            _hit(
                "The Best Clubs in Chicago 2026",
                "https://example.com/best-clubs-chicago",
                "Roundup of nightlife picks across the city.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="clubs")
        assert out["restaurants"] == []
        assert len(out["research_sources"]) == 1
        assert out["research_sources"][0].source_type == "article_listicle_blog_directory"
        assert out["research_sources"][0].trip_addable is False

    def test_timeout_listicle_stays_research_source_not_trip_addable(self):
        hits = [
            _hit(
                "Time Out Chicago",
                "https://www.timeout.com/chicago/bars/best-bars-in-chicago",
                "Best bars in Chicago: The Violet Hour, Broken Shaker, and more.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="nightlife")
        assert out["restaurants"] == []
        assert out["research_sources"]
        assert out["research_sources"][0].source_type == "article_listicle_blog_directory"
        assert out["research_sources"][0].trip_addable is False

    def test_broken_shaker_at_robey_can_be_addable_without_violet_robey_mixup(self):
        hits = [
            _hit(
                "Best Bars in Chicago",
                "https://example.com/nightlife-guide",
                (
                    "1. Broken Shaker — at The Robey in Wicker Park with rooftop cocktails. "
                    "2. The Violet Hour — in Wicker Park closed for the final time in 2024."
                ),
            )
        ]
        verified = {
            "broken shaker": VerificationResult(
                verified=True,
                source_url="https://example.com/broken-shaker",
                neighborhood="The Robey",
            ),
            "the violet hour": VerificationResult(verified=False),
        }
        out = normalize_hits(
            hits,
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
            verified_candidates=verified,
        )
        names = [r.name for r in out["restaurants"]]
        assert "Broken Shaker" in names
        assert "The Violet Hour" not in names
        shaker = next(r for r in out["restaurants"] if r.name == "Broken Shaker")
        assert (shaker.neighborhood or "").lower() == "the robey"

    def test_real_venue_with_location_signal_remains_trip_addable(self):
        hits = [
            _hit(
                "Gus' Sip & Dip",
                "https://example.com/gus",
                "Cocktail bar at 123 N Clark St in River North, Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert len(out["restaurants"]) == 1
        assert out["restaurants"][0].name == "Gus' Sip & Dip"
        assert out["research_sources"] == []

    def test_research_snippet_markdown_and_boilerplate_are_sanitized(self):
        hits = [
            _hit(
                "Best Restaurants in Chicago",
                "https://example.com/listicle",
                "##### Gaylord India Restaurant ... Subscribe now!!! Advertising",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert out["research_sources"]
        assert out["research_sources"][0].summary == (
            "This source may contain relevant background, but it is not a confirmed venue."
        )

    def test_research_sources_are_capped_when_venues_exist(self):
        hits = [
            _hit("Avec", "https://example.com/avec", "Restaurant in Chicago."),
            _hit("Top 10 Bars", "https://example.com/top-bars", "Guide to bars."),
            _hit("Neighborhood Guide", "https://example.com/hoods", "Where to stay and eat."),
            _hit("Best Rooftops", "https://example.com/rooftops", "Listicle roundup."),
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert len(out["restaurants"]) == 1
        assert len(out["research_sources"]) == 2

    # ── Venue extraction from listicles ───────────────────────────────────────

    def test_extract_venue_names_numbered_list(self):
        text = "1. Kumiko — West Loop speakeasy. 2. The Aviary — Avant-garde cocktails. 3. Billy Sunday — Logan Square."
        names = _extract_venue_names_from_text(text)
        assert "Kumiko" in names
        assert "The Aviary" in names
        assert "Billy Sunday" in names

    def test_extract_venue_names_deduplicates(self):
        text = "1. Kumiko — West Loop. Kumiko — great bar."
        names = _extract_venue_names_from_text(text)
        assert names.count("Kumiko") == 1

    def test_validate_venue_candidate_accepts_real_venue(self):
        context = "Kumiko is a speakeasy cocktail bar in Chicago West Loop."
        is_valid, normalized, _ = _validate_venue_candidate(
            "Kumiko",
            context,
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            title="Best Cocktail Bars in Chicago",
            url="https://www.timeout.com/chicago/bars/best-bars-in-chicago",
            snippet="1. Kumiko — West Loop speakeasy cocktail bar in Chicago.",
        )
        assert is_valid is True
        assert normalized == "Kumiko"

    def test_validate_venue_candidate_rejects_generic_phrase(self):
        context = "Best bars in Chicago guide."
        assert _validate_venue_candidate("Best Bars", context, intent=INTENT_NIGHTLIFE, destination="Chicago")[0] is False
        assert _validate_venue_candidate("Food & Drink", context, intent=INTENT_RESTAURANTS, destination="Chicago")[0] is False
        assert _validate_venue_candidate("Nightlife Guide", context, intent=INTENT_NIGHTLIFE, destination="Chicago")[0] is False

    def test_validate_venue_candidate_rejects_article_like_name(self):
        context = "Guide to restaurants in Chicago."
        assert _validate_venue_candidate("Guide to Chicago Eats", context, intent=INTENT_RESTAURANTS, destination="Chicago")[0] is False

    def test_validate_venue_candidate_requires_category_or_location(self):
        # No category signal, no location — should fail
        assert _validate_venue_candidate("Mystery Spot", "Random text here.", intent=INTENT_NIGHTLIFE, destination="")[0] is False
        # Venue-like name + destination context (2 strong signals) — should pass
        assert (
            _validate_venue_candidate(
                "Mystery Spot",
                "Mystery Spot in Chicago with no nightlife category context.",
                intent=INTENT_NIGHTLIFE,
                destination="Chicago",
                title="Chicago Places",
                url="https://example.com/guide",
                snippet="Mystery Spot in Chicago.",
            )[0]
            is True
        )

    def test_for_music_green_mill_phrase_not_promoted(self):
        hits = [
            _hit(
                "Travel Guide To Nightlife In Chicago (2026)",
                "https://example.com/nightlife-guide",
                "1. For Music Green Mill — Uptown jazz cocktail bar in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="nightlife")
        names = [r.name for r in out["restaurants"]]
        assert "For Music Green Mill" not in names

    def test_for_music_green_mill_recovery_promotes_green_mill_with_context(self):
        hits = [
            _hit(
                "Best Jazz Bars in Chicago",
                "https://www.timeout.com/chicago/bars/best-jazz-bars",
                "1. For Music Green Mill — Uptown jazz cocktail bar in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="jazz bars")
        names = [r.name for r in out["restaurants"]]
        assert "Green Mill" in names
        assert "For Music Green Mill" not in names

    def test_single_word_lime_rejected_without_strong_corroboration(self):
        hits = [
            _hit(
                "Travel Guide To Nightlife In Chicago (2026)",
                "https://example.com/nightlife-guide",
                "1. Lime — Featured in this nightlife guide and roundup.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="nightlife")
        assert "Lime" not in [r.name for r in out["restaurants"]]

    def test_listicle_with_numbered_venues_extracts_candidates(self):
        hits = [
            _hit(
                "Best Cocktail Bars in Chicago 2026",
                "https://example.com/best-bars",
                "1. Kumiko — West Loop speakeasy. 2. The Aviary — Avant-garde cocktails. 3. Billy Sunday — Logan Square.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        names = [r.name for r in out["restaurants"]]
        assert "Kumiko" in names
        assert "The Aviary" in names
        # Article becomes research_source (secondary)
        assert any(s.source_type == "article_listicle_blog_directory" for s in out["research_sources"]) or len(out["restaurants"]) >= 3

    def test_generic_article_titles_not_addable(self):
        hits = [
            _hit("Food & Drink", "https://example.com/fd", "Dining roundup with no specific venues."),
            _hit("Best Restaurants in Chicago", "https://example.com/best", "Top picks list overview."),
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert out["restaurants"] == []
        for rs in out["research_sources"]:
            assert rs.trip_addable is False

    def test_direct_venue_ranks_before_extracted_venue(self):
        hits = [
            _hit(
                "Top Bars Chicago",
                "https://ex.com/guide",
                "1. Kumiko — West Loop speakeasy bar in Chicago.",
            ),
            _hit("Gus' Sip & Dip", "https://ex.com/gus", "Cocktail bar at 123 N Clark St in Chicago."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        names = [r.name for r in out["restaurants"]]
        assert "Gus' Sip & Dip" in names
        assert "Kumiko" in names
        # Direct hit (ai_score=1.0) should sort before extracted hits.
        gus_idx = names.index("Gus' Sip & Dip")
        kumiko_idx = names.index("Kumiko")
        assert gus_idx < kumiko_idx

    def test_research_sources_hidden_when_three_or_more_venues(self):
        hits = [
            _hit(
                "Top Cocktail Bars Chicago",
                "https://ex.com/guide",
                "1. Kumiko — West Loop speakeasy. 2. The Aviary — Avant-garde cocktails. 3. Billy Sunday — Logan Square.",
            ),
            _hit("More Bar Picks", "https://ex.com/g2", "Another nightlife guide roundup article."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert len(out["restaurants"]) >= 3
        assert out["research_sources"] == []

    def test_extracted_venue_card_is_trip_addable(self):
        hits = [
            _hit(
                "Best Cocktail Bars in Chicago 2026",
                "https://example.com/best-bars",
                "1. Kumiko — West Loop speakeasy bar in Chicago. 2. Three Dots — Tiki bar in River North.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        for r in out["restaurants"]:
            # Venue cards are addable (they're restaurant/attraction/hotel, not research_source)
            assert r.source_url is not None
            assert r.last_verified_at is not None

    def test_extracted_venue_summary_references_source_article(self):
        hits = [
            _hit(
                "Best Bars in Chicago",
                "https://example.com/best-bars",
                "1. Kumiko — West Loop speakeasy bar in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        kumiko = next((r for r in out["restaurants"] if r.name == "Kumiko"), None)
        assert kumiko is not None
        assert (kumiko.summary or "") == "Mentioned in current nightlife research, but details need confirmation."
        assert "Featured in" not in (kumiko.summary or "")
        forbidden = [
            "venue-like proper noun",
            "category signal",
            "location signal",
            "neighborhood signal",
            "corroborated",
        ]
        assert not any(term in (kumiko.summary or "").lower() for term in forbidden)

    def test_user_facing_extracted_reason_omits_internal_validation_terms(self):
        hits = [
            _hit(
                "Chicago Cocktail Guide",
                "https://example.com/cocktails",
                "1. Billy Sunday — cocktail bar in Logan Square, Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        forbidden = [
            "venue-like proper noun",
            "category signal",
            "location signal",
            "neighborhood signal",
            "corroborated",
            "trusted source signal",
            "clean list pattern",
        ]
        for r in out["restaurants"]:
            summary = (r.summary or "").lower()
            assert not any(term in summary for term in forbidden)

    def test_source_title_cleanup_normalizes_all_caps_and_updated_suffix(self):
        hits = [
            _hit(
                "THE 10 BEST FINE DINING RESTAURANTS IN CHICAGO (UPDATED 2026)",
                "https://example.com/best-fine-dining",
                "Roundup of fine dining options in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="fine dining")
        assert out["research_sources"]
        assert out["research_sources"][0].title == "The 10 Best Fine Dining Restaurants In Chicago"

    def test_extracted_editorial_source_ranks_above_generic_top_list(self):
        hits = [
            _hit(
                "Top 10 Chicago Cocktail Bars",
                "https://example.com/top-10-cocktail-bars",
                "1. Kumiko — cocktail bar in West Loop, Chicago.",
            ),
            _hit(
                "Best Bars in Chicago",
                "https://www.eater.com/chicago/best-bars",
                "1. Meadowlark — cocktail bar in Logan Square, Chicago.",
            ),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        cards = {r.name: r for r in out["restaurants"]}
        assert cards["Meadowlark"].ai_score > cards["Kumiko"].ai_score

    def test_weak_extracted_source_gets_lower_score_and_verify_caveat(self):
        hits = [
            _hit(
                "Top 10 Chicago Cocktail Bars",
                "https://example.com/top-10-cocktail-bars",
                "1. Kumiko — cocktail bar.",
            ),
            _hit(
                "Best Chicago Bars",
                "https://www.theinfatuation.com/chicago/guides/best-bars",
                "1. Meadowlark — cocktail bar in Logan Square, Chicago.",
            ),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        cards = {r.name: r for r in out["restaurants"]}
        assert cards["Kumiko"].ai_score < cards["Meadowlark"].ai_score
        assert (cards["Kumiko"].summary or "").lower().startswith("mentioned in current nightlife research")

    def test_generic_extracted_reason_never_mentions_appears_to_be_restaurant(self):
        hits = [
            _hit(
                "Best Dining in Chicago",
                "https://example.com/chicago-dining",
                "1. La Grande Boucherie — restaurant in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        summaries = [r.summary or "" for r in out["restaurants"]]
        assert all("appears to be a restaurant" not in summary.lower() for summary in summaries)

    def test_weak_extracted_venue_without_specific_detail_is_not_addable(self):
        hits = [
            _hit(
                "Best Restaurants in Chicago",
                "https://example.com/list",
                "1. La Grande Boucherie — restaurant in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert "La Grande Boucherie" not in [r.name for r in out["restaurants"]]

    def test_luxury_value_extracted_requires_price_luxury_or_editorial_signal(self):
        hits = [
            _hit(
                "Top Luxury Value Dining Chicago",
                "https://example.com/luxury",
                "1. The Capital Grille — steakhouse in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_LUXURY_VALUE, destination="Chicago", user_query="luxury value dining")
        assert out["restaurants"] == []

    def test_maman_zari_price_tasting_menu_remains_addable_with_strong_reason(self):
        hits = [
            _hit(
                "Best Value Tasting Menus in Chicago",
                "https://www.theinfatuation.com/chicago/guides/value-tasting-menus",
                "1. Maman Zari — in Albany Park, a tasting menu around $90 with strong value for an 8-course experience.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_LUXURY_VALUE, destination="Chicago", user_query="luxury value dining")
        maman = next((r for r in out["restaurants"] if r.name == "Maman Zari"), None)
        assert maman is not None
        assert "value or pricing context" in (maman.summary or "").lower()
        assert "albany park" in (maman.summary or "").lower()

    def test_chain_restaurant_ranked_below_distinctive_local_pick(self):
        hits = [
            _hit(
                "Best Luxury Value Restaurants in Chicago",
                "https://www.theinfatuation.com/chicago/guides/luxury-value-restaurants",
                "1. Maman Zari — Albany Park tasting menu around $90 and strong value. 2. The Capital Grille — steakhouse in Chicago Loop.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_LUXURY_VALUE, destination="Chicago", user_query="luxury value dining")
        names = [r.name for r in out["restaurants"]]
        assert "Maman Zari" in names
        assert "The Capital Grille" in names
        assert names.index("Maman Zari") < names.index("The Capital Grille")

    def test_fine_dining_intent_creates_fine_dining_reasoning(self):
        hits = [
            _hit(
                "MICHELIN Chicago Picks",
                "https://guide.michelin.com/us/en/illinois/chicago/restaurants",
                "1. Smyth — Michelin dining in West Loop, Chicago.",
            )
        ]
        out = normalize_hits(
            hits,
            intent=INTENT_MICHELIN_RESTAURANTS,
            destination="Chicago",
            user_query="fine dining chicago",
        )
        smyth = next((r for r in out["restaurants"] if r.name == "Smyth"), None)
        assert smyth is not None
        assert "michelin" in (smyth.summary or "").lower()

    def test_research_source_cards_secondary_when_venues_present(self):
        hits = [
            _hit("Gus' Sip & Dip", "https://ex.com/gus", "Cocktail bar on Clark St in Chicago."),
            _hit("Best Bars List", "https://ex.com/list", "Guide to nightlife in Chicago."),
            _hit("Chicago Nightlife Guide", "https://ex.com/guide", "Article about Chicago bar scene."),
            _hit("Top Spots Roundup", "https://ex.com/roundup", "Listicle covering bars and clubs."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert len(out["restaurants"]) >= 1
        assert len(out["research_sources"]) <= 2

    def test_hybrid_research_source_type_is_article_listicle(self):
        hits = [
            _hit("Gus' Sip & Dip", "https://ex.com/gus", "Cocktail bar in Chicago River North."),
            _hit("Best Bars in Chicago", "https://ex.com/list", "A roundup guide of bars."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert any(s.source_type == "article_listicle_blog_directory" for s in out["research_sources"])

    def test_weak_extracted_candidates_do_not_create_trip_addable_cards(self):
        hits = [
            _hit(
                "Nightlife Roundup",
                "https://example.com/nightlife-roundup",
                "For music, Green Mill is iconic. With vibes, Lime can be fun.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert out["restaurants"] == []

    def test_direct_venue_hits_still_pass(self):
        hits = [
            _hit("Green Mill", "https://example.com/green-mill", "Cocktail bar in Uptown Chicago."),
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert [r.name for r in out["restaurants"]] == ["Green Mill"]
        assert out["restaurants"][0].ai_score == 1.0

    def test_glued_candidate_is_not_shown_as_single_venue(self):
        hits = [
            _hit(
                "Chicago Restaurants",
                "https://example.com/chicago-restaurants",
                "1. Gaylord India Restaurant Bub City — restaurant picks in Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        assert "Gaylord India Restaurant Bub City" not in [r.name for r in out["restaurants"]]

    def test_when_short_clean_candidate_exists_keep_it_over_glued_long_candidate(self):
        hits = [
            _hit(
                "Best Restaurants in Chicago",
                "https://example.com/chicago-restaurants",
                "1. Gaylord India Restaurant Bub City — restaurant picks in Chicago. 2. Bub City — bbq bar in River North, Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_RESTAURANTS, destination="Chicago", user_query="restaurants")
        names = [r.name for r in out["restaurants"]]
        assert "Bub City" in names
        assert "Gaylord India Restaurant Bub City" not in names

    def test_overlap_prefers_cleaner_shorter_name(self):
        hits = [
            _hit(
                "Chicago Nightlife Guide",
                "https://example.com/nightlife",
                "1. Kumiko The Aviary — cocktail bars in Chicago. 2. The Aviary — cocktail bar in West Loop, Chicago.",
            )
        ]
        out = normalize_hits(hits, intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        names = [r.name for r in out["restaurants"]]
        assert "The Aviary" in names
        assert "Kumiko The Aviary" not in names


# ── LiveResearchService behavior ────────────────────────────────────────────

class TestLiveResearchService:
    def setup_method(self):
        reset_global_cache()

    def test_disabled_service_returns_empty_result(self):
        provider = StubLiveSearchProvider([_hit("Should Not See Me")])
        svc = LiveResearchService(provider=provider, enabled=False, cache=_TTLCache(0))
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="foo")
        assert result.has_data() is False
        assert result.source_status == SOURCE_NONE

    def test_noop_provider_returns_empty_result(self):
        svc = LiveResearchService(provider=_NoopProvider(), cache=_TTLCache(0))
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="foo")
        assert result.has_data() is False
        assert result.source_status == SOURCE_NONE
        assert svc.is_live_capable is False

    def test_returns_live_search_status_when_provider_returns_hits(self):
        provider = StubLiveSearchProvider(
            [_hit("Boka", "https://ex.com/boka", "Modern American dining.")]
        )
        svc = LiveResearchService(provider=provider, cache=_TTLCache(0))
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")
        assert result.has_data()
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert result.cached is False
        assert result.provider_name == "stub"
        assert result.source_url == "https://ex.com/boka"

    def test_source_label_live_and_cached_preserved_for_non_place_sources(self):
        provider = MagicMock()
        provider.name = "stub"
        provider.available = True
        provider.search.return_value = [
            _hit("The Best Clubs in Chicago 2026", "https://ex.com/best-clubs", "Nightlife roundup.")
        ]
        svc = LiveResearchService(provider=provider, cache=_TTLCache(60))
        first = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="clubs")
        assert first.source_status == SOURCE_LIVE_SEARCH
        assert first.cached is False
        assert first.research_sources
        assert first.restaurants == []
        second = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="clubs")
        assert second.source_status == SOURCE_LIVE_SEARCH
        assert second.cached is True
        assert second.research_sources

    def test_unsupported_intent_skips_live_search(self):
        provider = StubLiveSearchProvider([_hit("X")])
        svc = LiveResearchService(provider=provider, cache=_TTLCache(0))
        # INTENT_GENERAL is not in the live-enabled set
        from app.models.concierge import INTENT_GENERAL
        result = svc.fetch(intent=INTENT_GENERAL, destination="Chicago", user_query="weather?")
        assert result.has_data() is False
        assert result.source_status == SOURCE_NONE

    def test_cache_hit_marks_cached_true_and_skips_provider(self):
        provider = MagicMock()
        provider.name = "stub"
        provider.available = True
        provider.search.return_value = [_hit("Boka", "https://ex.com/boka", "Modern American.")]
        svc = LiveResearchService(provider=provider, cache=_TTLCache(60))
        first = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")
        assert first.cached is False
        assert provider.search.call_count == 1
        second = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants")
        assert second.cached is True
        # Cached responses must still keep the live source label, not relabel as sample/db.
        assert second.source_status == SOURCE_LIVE_SEARCH
        assert second.provider_name == "stub"
        assert provider.search.call_count == 1

    def test_destination_required_for_live_search(self):
        provider = StubLiveSearchProvider([_hit("X")])
        svc = LiveResearchService(provider=provider, cache=_TTLCache(0))
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="", user_query="best food")
        assert result.has_data() is False
        assert result.source_status == SOURCE_NONE

    def test_provider_exception_returns_empty_does_not_raise(self):
        broken = MagicMock()
        broken.name = "broken"
        broken.available = True
        broken.search.side_effect = RuntimeError("network down")
        svc = LiveResearchService(provider=broken, cache=_TTLCache(0))
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="x")
        assert result.has_data() is False
        assert result.source_status == SOURCE_NONE


# ── ConciergeService integration with live research ────────────────────────

def _make_mock_db(destination: str = "Chicago") -> MagicMock:
    mock_db = MagicMock()
    chain = mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value
    chain.execute.return_value.data = [
        {
            "id": str(FAKE_TRIP_ID),
            "destination": destination,
            "start_date": "2026-06-01",
            "end_date": "2026-06-07",
            "title": "Test Trip",
            "user_id": str(FAKE_USER_ID),
        }
    ]
    return mock_db


def _live_svc_with(hits):
    provider = StubLiveSearchProvider(hits)
    return LiveResearchService(provider=provider, cache=_TTLCache(0), enabled=True)


class TestConciergeWithLiveResearch:
    def setup_method(self):
        reset_global_cache()

    def _make_concierge(self, destination: str, hits) -> ConciergeService:
        return ConciergeService(_make_mock_db(destination), live_research=_live_svc_with(hits))

    def test_nightlife_uses_live_results_when_available(self):
        live_hits = [
            _hit("Kumiko", "https://ex.com/kumiko", "Speakeasy in West Loop."),
            _hit("Three Dots and a Dash", "https://ex.com/3dots", "Tiki bar in River North."),
        ]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert result.live_provider == "stub"
        assert result.cached is False

    def test_nightlife_filters_listicles_into_research_sources_only(self):
        live_hits = [
            _hit("The Best Clubs in Chicago 2026", "https://ex.com/best-clubs", "Roundup list."),
            _hit("Gus' Sip & Dip", "https://ex.com/gus", "Cocktail bar at 123 N Clark St in River North."),
        ]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "best nightlife in chicago", FAKE_USER_ID)
        assert result.intent == INTENT_NIGHTLIFE
        assert [r.name for r in result.restaurants] == ["Gus' Sip & Dip"]
        assert result.research_sources
        assert result.research_sources[0].source_type == "article_listicle_blog_directory"
        # Live cards must carry a source URL and verification timestamp.
        for r in result.restaurants:
            assert r.source_url
            assert r.last_verified_at

    def test_nightlife_falls_back_to_sample_when_live_unavailable(self):
        svc = self._make_concierge("Chicago", hits=[])
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        # Sample fallback is honest: it MUST NOT be relabeled as live.
        assert result.source_status == SOURCE_SAMPLE_DATA
        assert result.live_provider is None
        assert result.restaurants  # sample bars
        assert all("verify hours" in (r.summary or "").lower() for r in result.restaurants)

    def test_unsupported_city_nightlife_with_no_live_returns_unavailable(self):
        svc = self._make_concierge("Paris", hits=[])  # sample only supports Chicago
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.source_status == SOURCE_UNAVAILABLE
        assert result.warnings
        assert result.restaurants == []

    def test_restaurants_intent_uses_live_results(self):
        live_hits = [_hit("Avec", "https://ex.com/avec", "Mediterranean small plates.")]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_search = MagicMock()
            mock_search.search_restaurants.return_value = []
            MockSearch.return_value = mock_search
            result = svc.search(FAKE_TRIP_ID, "best restaurants in Chicago", FAKE_USER_ID)
        assert result.intent == INTENT_RESTAURANTS
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert any(r.name == "Avec" for r in result.restaurants)
        # When live succeeds we must not have called the sample restaurant DB.
        mock_search.search_restaurants.assert_not_called()

    def test_attractions_intent_uses_live_results(self):
        live_hits = [_hit("Art Institute of Chicago", "https://ex.com/aic", "World-class museum.")]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_search = MagicMock()
            mock_search.search_attractions.return_value = []
            MockSearch.return_value = mock_search
            result = svc.search(FAKE_TRIP_ID, "things to do in Chicago", FAKE_USER_ID)
        assert result.intent == INTENT_ATTRACTIONS
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert any(a.name == "Art Institute of Chicago" for a in result.attractions)
        mock_search.search_attractions.assert_not_called()

    def test_hotels_intent_uses_live_results(self):
        live_hits = [_hit("Pendry Chicago", "https://ex.com/pendry", "Luxury hotel near Mag Mile.")]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_search = MagicMock()
            mock_search.search_hotels.return_value = []
            MockSearch.return_value = mock_search
            result = svc.search(FAKE_TRIP_ID, "best hotels in Chicago", FAKE_USER_ID)
        assert result.intent == INTENT_HOTELS
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert any(h.name == "Pendry Chicago" for h in result.hotels)
        mock_search.search_hotels.assert_not_called()

    def test_michelin_unavailable_destination_uses_live_results_when_present(self):
        live_hits = [_hit("Dill", "https://ex.com/dill", "Tasting menu in Reykjavik.")]
        svc = self._make_concierge("Reykjavik", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Michelin restaurants in Reykjavik", FAKE_USER_ID)
        assert result.intent == INTENT_MICHELIN_RESTAURANTS
        assert result.source_status == SOURCE_LIVE_SEARCH
        assert any(r.name == "Dill" for r in result.restaurants)

    def test_compare_intent_does_not_use_live_results(self):
        # Compare intent is intentionally curated-only; live results must not
        # leak into restaurant/attraction lists.
        live_hits = [_hit("Some Spot", "https://ex.com/x", "should be ignored")]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Compare River North vs West Loop", FAKE_USER_ID)
        assert result.restaurants == []
        assert result.attractions == []
        assert len(result.area_comparisons) >= 2

    def test_default_concierge_without_live_keys_does_not_relabel_sample_as_live(self, monkeypatch):
        # No env keys → noop provider → live unavailable. Existing nightlife
        # sample fallback must keep its sample_data label.
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("BRAVE_SEARCH_API_KEY", raising=False)
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        svc = ConciergeService(_make_mock_db("Chicago"))
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.source_status == SOURCE_SAMPLE_DATA
        assert result.live_provider is None
        assert result.cached is False

    def test_live_research_sources_only_do_not_report_sample_fallback(self):
        live_hits = [
            _hit("Best Cocktail Bars in Chicago", "https://ex.com/listicle", "Top picks and guide.")
        ]
        svc = self._make_concierge("Chicago", live_hits)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.research_sources
        assert result.source_status == SOURCE_MIXED
        assert result.live_provider == "stub"

    def test_sample_fallback_status_only_when_sample_is_used(self):
        svc = self._make_concierge("Chicago", hits=[])
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            MockSearch.return_value = MagicMock()
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.source_status == SOURCE_SAMPLE_DATA


# ── Cache TTL behavior ───────────────────────────────────────────────────────

class TestTTLCache:
    def test_zero_ttl_disables_cache(self):
        cache = _TTLCache(0)
        cache.set("k", "v")
        assert cache.get("k") is None

    def test_entries_expire(self, monkeypatch):
        cache = _TTLCache(60)
        clock = [1000.0]
        monkeypatch.setattr(time, "monotonic", lambda: clock[0])
        cache.set("k", "v")
        clock[0] = 1059.0
        assert cache.get("k") == "v"
        clock[0] = 1061.0
        assert cache.get("k") is None


# ── Verify-before-add pipeline ───────────────────────────────────────────────

def _make_verifying_provider(
    initial_hits: list,
    verified_by_name: dict,  # {"CandidateName": LiveSearchHit or None}
) -> MagicMock:
    """Provider that returns initial_hits for broad queries and targeted hits
    for verification queries (which contain the candidate name in quotes)."""
    provider = MagicMock()
    provider.name = "verifying-stub"
    provider.available = True

    def _search(query: str, *, max_results: int = 10) -> list:
        for name, hit in verified_by_name.items():
            if f'"{name}"' in query:
                return [hit] if hit else []
        return initial_hits

    provider.search.side_effect = _search
    return provider


class TestIsObviousNonVenue:
    def test_rejects_united_states(self):
        assert _is_obvious_non_venue("United States", "Chicago") is True

    def test_rejects_north_america(self):
        assert _is_obvious_non_venue("North America", "Chicago") is True

    def test_rejects_launch_special(self):
        assert _is_obvious_non_venue("Launch Special", "Chicago") is True

    def test_rejects_summer_guide(self):
        assert _is_obvious_non_venue("Summer Guide", "Chicago") is True

    def test_rejects_destination_explore_pattern(self):
        assert _is_obvious_non_venue("Chicago Explore", "Chicago") is True

    def test_rejects_destination_guide_pattern(self):
        assert _is_obvious_non_venue("Chicago Guide", "Chicago") is True

    def test_rejects_name_equal_to_destination(self):
        assert _is_obvious_non_venue("Chicago", "Chicago") is True

    def test_allows_real_venue_names(self):
        assert _is_obvious_non_venue("Kumiko", "Chicago") is False
        assert _is_obvious_non_venue("The Aviary", "Chicago") is False
        assert _is_obvious_non_venue("Green Mill", "Chicago") is False
        assert _is_obvious_non_venue("Billy Sunday", "Chicago") is False

    def test_empty_name_rejected(self):
        assert _is_obvious_non_venue("", "Chicago") is True


class TestCheckVerificationHits:
    def test_yelp_url_verifies_candidate(self):
        hits = [
            _hit("Kumiko", "https://www.yelp.com/biz/kumiko-chicago", "Cocktail bar at 630 W Lake St, Chicago, IL.")
        ]
        vr = _check_verification_hits("Kumiko", "Chicago", hits)
        assert vr.verified is True
        assert vr.source_url == "https://www.yelp.com/biz/kumiko-chicago"

    def test_tripadvisor_url_verifies_candidate(self):
        hits = [
            _hit("The Aviary", "https://www.tripadvisor.com/restaurant-aviary", "Bar in West Loop, Chicago.")
        ]
        vr = _check_verification_hits("The Aviary", "Chicago", hits)
        assert vr.verified is True

    def test_address_plus_city_verifies_candidate(self):
        hits = [
            _hit("Billy Sunday", "https://example.com/billy-sunday", "Bar at 3143 W Logan Blvd, Chicago, IL.")
        ]
        vr = _check_verification_hits("Billy Sunday", "Chicago", hits)
        assert vr.verified is True

    def test_no_match_for_candidate_name_not_verified(self):
        hits = [
            _hit("Unrelated Spot", "https://yelp.com/unrelated", "A bar in Chicago.")
        ]
        vr = _check_verification_hits("Kumiko", "Chicago", hits)
        assert vr.verified is False

    def test_empty_hits_not_verified(self):
        vr = _check_verification_hits("Kumiko", "Chicago", [])
        assert vr.verified is False

    def test_article_url_without_address_not_verified(self):
        # A listicle URL and no address = not enough for verification
        hits = [
            _hit("Best Bars in Chicago", "https://example.com/best-bars", "Kumiko is a great bar.")
        ]
        vr = _check_verification_hits("Kumiko", "Chicago", hits)
        assert vr.verified is False


class TestVerifyBeforeAdd:
    """Tests for the full verify-before-add pipeline via LiveResearchService."""

    def setup_method(self):
        reset_global_cache()

    def _svc(self, provider) -> LiveResearchService:
        return LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
        )

    def test_obvious_non_venue_names_never_become_cards(self):
        """United States / Launch Special / Chicago Explore are pre-filtered."""
        article_hit = _hit(
            "Chicago Nightlife 2026",
            "https://example.com/guide",
            "1. United States — national overview. 2. Launch Special — promotion. "
            "3. Chicago Explore — discover the city.",
        )
        provider = _make_verifying_provider([article_hit], {})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        names = [r.name for r in result.restaurants]
        assert "United States" not in names
        assert "Launch Special" not in names
        assert "Chicago Explore" not in names
        # Article still appears as research source
        assert len(result.research_sources) >= 1

    def test_article_alone_does_not_create_addable_card(self):
        """Candidate extracted from article is NOT addable when verification fails."""
        article_hit = _hit(
            "Best Cocktail Bars in Chicago 2026",
            "https://example.com/best-bars",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        # Verification search returns nothing useful
        provider = _make_verifying_provider([article_hit], {"Kumiko": None})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars"
        )
        assert result.restaurants == []
        # Article still appears as research source
        assert len(result.research_sources) >= 1

    def test_candidate_only_becomes_addable_after_verification_hit(self):
        """Same candidate: unverified → no card; verified → card present."""
        article_hit = _hit(
            "Best Bars in Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko",
            "https://www.yelp.com/biz/kumiko-chicago",
            "Cocktail bar at 630 W Lake St, Chicago, IL.",
        )

        # Without verification
        no_verify_provider = _make_verifying_provider([article_hit], {"Kumiko": None})
        result_no = self._svc(no_verify_provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        assert result_no.restaurants == []

        # With verification
        yes_verify_provider = _make_verifying_provider([article_hit], {"Kumiko": verify_hit})
        result_yes = self._svc(yes_verify_provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        assert any(r.name == "Kumiko" for r in result_yes.restaurants)

    def test_verified_venue_has_source_url_and_reason(self):
        """Verified card carries the verification source URL and a summary."""
        article_hit = _hit(
            "Best Bars in Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko",
            "https://www.yelp.com/biz/kumiko-chicago",
            "Cocktail bar at 630 W Lake St, Chicago, IL.",
        )
        provider = _make_verifying_provider([article_hit], {"Kumiko": verify_hit})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        card = next((r for r in result.restaurants if r.name == "Kumiko"), None)
        assert card is not None
        assert card.source_url is not None
        assert card.summary is not None
        assert card.verified_place is True

    def test_unverified_candidate_not_in_venue_cards(self):
        """Candidates whose verification returns no useful hits are excluded."""
        article_hit = _hit(
            "Top Chicago Bars",
            "https://example.com/top-bars",
            "1. Meadowlark — Logan Square cocktail bar in Chicago.",
        )
        # No useful verification hit → empty list
        provider = _make_verifying_provider([article_hit], {"Meadowlark": None})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        assert all(r.name != "Meadowlark" for r in result.restaurants)

    def test_kumiko_aviary_green_mill_pass_after_verification(self):
        """Established venues still become addable cards when verification succeeds."""
        article_hit = _hit(
            "Best Cocktail Bars in Chicago 2026",
            "https://example.com/best-bars",
            "1. Kumiko — West Loop speakeasy. "
            "2. The Aviary — Avant-garde cocktails. "
            "3. Green Mill — jazz bar in Uptown.",
        )
        verified_names = {
            "Kumiko": _hit("Kumiko", "https://www.yelp.com/biz/kumiko", "Cocktail bar at 630 W Lake St, Chicago, IL."),
            "The Aviary": _hit("The Aviary", "https://www.tripadvisor.com/aviary", "Bar in West Loop, Chicago."),
            "Green Mill": _hit("Green Mill Cocktail Lounge", "https://www.yelp.com/biz/green-mill", "Jazz club at 4802 N Broadway Ave, Chicago, IL."),
        }
        provider = _make_verifying_provider([article_hit], verified_names)
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars"
        )
        names = [r.name for r in result.restaurants]
        assert "Kumiko" in names
        assert "The Aviary" in names
        assert "Green Mill" in names
        for r in result.restaurants:
            assert r.verified_place is True

    def test_verified_venue_uses_verification_source_url_not_article_url(self):
        """Card source_url should point to the verification hit, not the article."""
        article_hit = _hit(
            "Best Bars Chicago",
            "https://example.com/article",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko",
            "https://www.yelp.com/biz/kumiko-chicago",
            "Cocktail bar at 630 W Lake St, Chicago, IL.",
        )
        provider = _make_verifying_provider([article_hit], {"Kumiko": verify_hit})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        card = next((r for r in result.restaurants if r.name == "Kumiko"), None)
        assert card is not None
        assert card.source_url == "https://www.yelp.com/biz/kumiko-chicago"

    def test_verification_results_cached(self):
        """Second fetch with same params uses result cache; provider not called again."""
        article_hit = _hit(
            "Best Bars Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko",
            "https://www.yelp.com/biz/kumiko-chicago",
            "Cocktail bar at 630 W Lake St, Chicago, IL.",
        )
        provider = _make_verifying_provider([article_hit], {"Kumiko": verify_hit})
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(ttl_seconds=1800),       # result cache enabled
            verification_cache=_TTLCache(ttl_seconds=1800),
            enabled=True,
        )
        # First fetch — populates both result and verification caches.
        r1 = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert r1.cached is False
        call_count_after_first = provider.search.call_count
        assert call_count_after_first >= 2  # initial + verification query

        # Second fetch with identical params — must hit the result cache.
        r2 = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert r2.cached is True
        assert provider.search.call_count == call_count_after_first  # no new calls

    def test_direct_venue_hit_is_trip_addable_without_verification(self):
        """A direct venue_place hit is always addable (verified_place=True)."""
        direct_hit = _hit(
            "Gus' Sip & Dip",
            "https://ex.com/gus",
            "Cocktail bar at 123 N Clark St in River North, Chicago.",
        )
        provider = _make_verifying_provider([direct_hit], {})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        assert len(result.restaurants) == 1
        assert result.restaurants[0].name == "Gus' Sip & Dip"
        assert result.restaurants[0].verified_place is True

    def test_fallback_to_research_sources_when_no_verified_venues(self):
        """When no candidates verify, only research_sources are returned."""
        article_hit = _hit(
            "Chicago Bar Guide 2026",
            "https://example.com/guide",
            "1. Meadowlark — Logan Square cocktail bar in Chicago.",
        )
        provider = _make_verifying_provider([article_hit], {"Meadowlark": None})
        result = self._svc(provider).fetch(
            intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars"
        )
        assert result.restaurants == []
        assert result.research_sources  # Article still appears as background source


class TestFrontendResearchSourceCard:
    def test_research_source_cards_do_not_offer_add_to_trip(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "category=\"Research source\"" in src
        assert "canAdd={false}" in src


class TestFrontendConciergeClearChat:
    def test_clear_chat_uses_reload_guard_and_keeps_itinerary_state(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "const skipReloadRef = useRef(false);" in src
        assert "if (skipReloadRef.current) return;" in src
        assert "skipReloadRef.current = true;" in src
        handle_clear_block = src.split("async function handleClearChat() {", 1)[1].split("}", 1)[0]
        assert "setTripDays([]);" not in handle_clear_block
        assert "setItineraryItems([]);" not in handle_clear_block
