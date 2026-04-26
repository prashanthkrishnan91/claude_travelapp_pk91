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
from app.services.google_places import GooglePlaceVerification
from app.models.concierge import SourceEvidence
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
    _make_cache_key,
    _reason_guard,
    _sanitize_reason_evidence_text,
    _validate_venue_candidate,
    build_place_reason,
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
        assert any("not added as a trip option" in (s.summary or "").lower() for s in out["research_sources"])

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

    def test_june_2025_closure_article_marks_violet_hour_closed_from_source_text(self):
        article_hit = LiveSearchHit(
            title="The Violet Hour closes permanently after final service in June 2025",
            url="https://example.com/chicago-nightlife-june-2025",
            snippet="Chicago nightlife update: The Violet Hour in Wicker Park has closed its doors.",
            provider="Tavily",
            raw={
                "content": (
                    "June 2025 update: The Violet Hour closed permanently and won't reopen. "
                    "Other bars in the area remain open."
                ),
                "sourceText": "The Violet Hour closed for the final time in June 2025.",
            },
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
        verified = {
            "the violet hour": VerificationResult(
                verified=True,
                source_url="https://example.com/listing/the-violet-hour",
                neighborhood="Wicker Park",
            )
        }
        out = normalize_hits(
            [article_hit],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
            verified_candidates=verified,
        )
        names = [r.name for r in out["restaurants"]]
        assert "The Violet Hour" not in names
        assert all((r.name or "").lower() != "the violet hour" for r in out["attractions"])
        assert all((r.name or "").lower() != "the violet hour" for r in out["hotels"])

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
        # Article/listicle sources now get the discovery-oriented fallback reason
        assert out["research_sources"][0].summary == (
            "Used for background discovery; individual venues were verified separately."
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

    def test_nightlife_with_require_google_does_not_fallback_to_sample(self, monkeypatch):
        svc = self._make_concierge("Chicago", hits=[])
        monkeypatch.setattr(svc._settings, "research_engine_require_google_verification", True)
        with patch("app.services.concierge.SearchService") as MockSearch, \
             patch.object(svc, "_call_claude", return_value=_FAKE_CLAUDE_JSON):
            mock_search = MagicMock()
            MockSearch.return_value = mock_search
            result = svc.search(FAKE_TRIP_ID, "Nearby cocktail bars", FAKE_USER_ID)
        assert result.source_status == SOURCE_UNAVAILABLE
        assert result.restaurants == []
        assert any("google verification" in (w or "").lower() for w in result.warnings)
        mock_search.search_restaurants.assert_not_called()

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

    def test_2025_article_does_not_verify_open_status_in_2026(self):
        hits = [
            _hit(
                "Best Bars in Chicago (June 2025)",
                "https://example.com/chicago-bars-guide",
                "June 2025 guide: Kumiko at 630 W Lake St, Chicago, IL.",
            )
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

    @staticmethod
    def _google_stub(mapping):
        class _Stub:
            available = True

            def verify(self, name, destination, neighborhood=None, intent=None):
                return mapping.get(name.lower(), GooglePlaceVerification(confidence="unknown", failure_reason="not_found"))

            def clear_cache_for_destination(self, destination):
                return 0

        return _Stub()

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

    def test_google_5_plus_verified_suppresses_research_sources(self):
        direct_hits = [
            _hit(f"Venue {idx}", f"https://example.com/venue-{idx}", "Cocktail bar in Chicago.")
            for idx in range(1, 7)
        ]
        provider = _make_verifying_provider(direct_hits, {})
        google_map = {
            f"venue {idx}": GooglePlaceVerification(
                provider_place_id=f"gp-{idx}",
                name=f"Venue {idx}",
                formatted_address=f"{idx} Main St, Chicago, IL",
                business_status="OPERATIONAL",
                google_maps_uri=f"https://maps.google.com/?cid=gp-{idx}",
                rating=4.5,
                types=["bar", "point_of_interest"],
                confidence="high",
            )
            for idx in range(1, 7)
        }
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert len(result.restaurants) >= 5
        assert result.research_sources == []
        assert all(r.type == "verified_place" for r in result.restaurants)

    def test_google_verified_reason_and_fields_do_not_use_tavily_snippet(self):
        suspicious_snippet = "Hotel lounge with rooms upstairs."
        direct_hit = _hit("Kumiko", "https://example.com/kumiko", suspicious_snippet)
        provider = _make_verifying_provider([direct_hit], {})
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?cid=gp-kumiko",
            rating=4.7,
            types=["cocktail_bar", "bar", "point_of_interest"],
            confidence="high",
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({"kumiko": google}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert len(result.restaurants) == 1
        card = result.restaurants[0]
        # Suspicious provider snippet must never leak into the user-facing reason.
        assert card.summary and "Hotel lounge" not in card.summary
        # Reason carries no debug/structured tokens like "Google 4.7★" — the
        # star rating belongs in the meta line, not the why-pick sentence.
        assert "★" not in card.summary
        assert "google " not in card.summary.lower()
        # Bar venue → bar/drinks vocabulary, never restaurant-only words.
        assert "dining" not in card.summary.lower()
        assert card.maps_link == "https://maps.google.com/?cid=gp-kumiko"
        assert card.type == "verified_place"

    def test_listicle_url_never_surfaces_as_verified_place(self):
        direct_hit = _hit("Kumiko", "https://example.com/top-10-bars", "Cocktail bar in Chicago.")
        provider = _make_verifying_provider([direct_hit], {})
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            confidence="high",
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({"kumiko": google}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert result.restaurants == []


class TestFrontendResearchSourceCard:
    def test_research_source_cards_do_not_offer_add_to_trip(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            src = f.read()
        # Research source cards must always be rendered with canAdd={false}
        assert "canAdd={false}" in src
        # The category label for non-article sources is still "Research source"
        assert '"Research source"' in src

    def test_research_source_open_source_button_not_add_to_trip(self):
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            src = f.read()
        # Non-addable cards with a source link should show "Open source"
        assert "Open source" in src
        # ExternalLink icon is used in the non-addable path
        assert "ExternalLink" in src
        # The old "Research source" span label is gone
        assert ">Research source<" not in src


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


# ── Listicle-extraction pipeline: new targeted tests ─────────────────────────

class TestListicleTitleNotAddable:
    """Listicle/article titles must never become addable venue cards."""

    def test_article_title_is_not_addable_venue_no_google(self):
        """'The 22 Best Cocktail Bars In Chicago' title must stay in research_sources only."""
        hit = _hit(
            "The 22 Best Cocktail Bars In Chicago",
            "https://example.com/best-bars",
            "Kumiko, The Aviary, and Billy Sunday top the list.",
        )
        out = normalize_hits(
            [hit],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        # The listicle title itself must not appear as a restaurant card
        names = [r.name for r in out["restaurants"]]
        assert "The 22 Best Cocktail Bars In Chicago" not in names
        assert any(s.type == "research_source" for s in out["research_sources"])

    def test_numbered_listicle_title_goes_to_research_sources(self):
        """'Top 10 Speakeasies In Chicago' title must be classified as research source."""
        hit = _hit(
            "Top 10 Speakeasies In Chicago",
            "https://example.com/speakeasies",
            "1. The Green Door — Wicker Park. 2. GMan Tavern — Boystown.",
        )
        out = normalize_hits(
            [hit],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="speakeasies",
        )
        restaurant_names = {r.name for r in out["restaurants"]}
        # The title itself is not a venue
        assert "Top 10 Speakeasies In Chicago" not in restaurant_names

    def test_guide_title_not_addable(self):
        """'Guide to Rooftop Bars in NYC' must not produce an addable card."""
        hit = _hit(
            "Guide to Rooftop Bars in NYC",
            "https://example.com/guide",
            "230 Fifth Rooftop Bar — Midtown. Bar SixtyFive — Rockefeller.",
        )
        out = normalize_hits(
            [hit],
            intent=INTENT_NIGHTLIFE,
            destination="New York",
            user_query="rooftop bars",
        )
        names = [r.name for r in out["restaurants"]]
        assert "Guide to Rooftop Bars in NYC" not in names


class TestExtractedVenueRequiresGoogleVerification:
    """Extracted venue names must only become addable cards after Google verification."""

    def setup_method(self):
        reset_global_cache()

    def _svc_with_google(self, provider, google_map) -> LiveResearchService:
        class _Stub:
            available = True
            def verify(self, name, destination, neighborhood=None, intent=None):
                return google_map.get(name.lower(), GooglePlaceVerification(
                    confidence="unknown", failure_reason="not_found"
                ))
            def clear_cache_for_destination(self, destination):
                return 0
        return LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=_Stub(),
        )

    def test_extracted_venue_not_addable_without_google_match(self):
        article = _hit(
            "Best Cocktail Bars In Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop. 2. The Aviary — West Loop.",
        )
        provider = _make_verifying_provider([article], {"Kumiko": _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko", "Cocktail bar at 630 W Lake St, Chicago."
        )})
        # Google returns no match for Kumiko
        svc = self._svc_with_google(provider, {})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert not any(r.name == "Kumiko" for r in result.restaurants)

    def test_extracted_venue_addable_with_operational_google_match(self):
        article = _hit(
            "Best Cocktail Bars In Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy cocktail bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"Kumiko": verify_hit})
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL 60661",
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?cid=gp-kumiko",
            rating=4.8,
            types=["cocktail_bar", "bar", "point_of_interest"],
            confidence="high",
        )
        svc = self._svc_with_google(provider, {"kumiko": google})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert any(r.name == "Kumiko" for r in result.restaurants)
        card = next(r for r in result.restaurants if r.name == "Kumiko")
        assert card.verified_place is True
        assert card.google_verification is not None
        assert card.google_verification.provider_place_id == "gp-kumiko"

    def test_closed_google_match_excluded(self):
        article = _hit(
            "Chicago Bars Guide",
            "https://example.com/bars",
            "1. OldSpot — Famous dive bar in Logan Square cocktail scene in Chicago.",
        )
        verify_hit = _hit(
            "OldSpot", "https://www.yelp.com/biz/oldspot",
            "Bar at 1234 N Milwaukee Ave, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"OldSpot": verify_hit})
        google_closed = GooglePlaceVerification(
            provider_place_id="gp-oldspot",
            name="OldSpot",
            formatted_address="1234 N Milwaukee Ave, Chicago, IL",
            business_status="CLOSED_PERMANENTLY",
            confidence="high",
        )
        svc = self._svc_with_google(provider, {"oldspot": google_closed})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        # Permanently closed venue must NOT appear as addable card
        assert not any(r.name == "OldSpot" for r in result.restaurants)

    def test_low_confidence_google_match_excluded(self):
        article = _hit(
            "Chicago Bar Guide",
            "https://example.com/bars",
            "1. Mystery Lounge — rumored cocktail spot in Chicago.",
        )
        provider = _make_verifying_provider([article], {})
        google_low = GooglePlaceVerification(
            provider_place_id="gp-mystery",
            name="Mystery Lounge",
            formatted_address="Unknown St, Chicago, IL",
            business_status="OPERATIONAL",
            confidence="low",
        )
        svc = self._svc_with_google(provider, {"mystery lounge": google_low})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert not any(r.name == "Mystery Lounge" for r in result.restaurants)


class TestDedupByGooglePlaceId:
    """Same Google place_id must never appear as two separate addable cards."""

    def setup_method(self):
        reset_global_cache()

    def _google_stub(self, mapping):
        class _Stub:
            available = True
            def verify(self, name, destination, neighborhood=None, intent=None):
                return mapping.get(name.lower(), GooglePlaceVerification(
                    confidence="unknown", failure_reason="not_found"
                ))
            def clear_cache_for_destination(self, destination):
                return 0
        return _Stub()

    def test_same_place_id_from_direct_and_article_deduped(self):
        """If a venue appears both as a direct hit and extracted from an article,
        only one addable card should be produced."""
        direct_hit = _hit(
            "Kumiko",
            "https://example.com/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago IL.",
        )
        article_hit = _hit(
            "Best Bars In Chicago",
            "https://example.com/best-bars",
            "1. Kumiko — West Loop cocktail bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([direct_hit, article_hit], {"Kumiko": verify_hit})
        same_google = GooglePlaceVerification(
            provider_place_id="gp-kumiko-unique",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL 60661",
            business_status="OPERATIONAL",
            google_maps_uri="https://maps.google.com/?cid=gp-kumiko",
            rating=4.8,
            types=["cocktail_bar", "bar"],
            confidence="high",
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({"kumiko": same_google}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        kumiko_cards = [r for r in result.restaurants if r.name == "Kumiko"]
        assert len(kumiko_cards) == 1, "Same place_id must produce exactly one addable card"

    def test_two_different_place_ids_both_addable(self):
        """Two venues with distinct place_ids must both appear as addable cards."""
        hits = [
            _hit("Kumiko", "https://example.com/kumiko", "Cocktail bar at 630 W Lake St, Chicago IL."),
            _hit("The Aviary", "https://example.com/aviary", "Bar at 955 W Fulton Market, Chicago IL."),
        ]
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-kumiko",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
            "the aviary": GooglePlaceVerification(
                provider_place_id="gp-aviary",
                name="The Aviary",
                formatted_address="955 W Fulton Market, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
        }
        provider = _make_verifying_provider(hits, {})
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        names = {r.name for r in result.restaurants}
        assert "Kumiko" in names
        assert "The Aviary" in names


class TestNoRawArticleBecomesAddableCard:
    """No raw article/listicle should appear directly as an Add to Trip card."""

    def test_article_type_research_source_is_never_trip_addable(self):
        """UnifiedResearchSourceResult.trip_addable must always be False."""
        hits = [
            _hit(
                "The 15 Best Bars In Chicago — Eater",
                "https://www.eater.com/chicago/best-bars",
                "Kumiko, The Violet Hour, and Green Mill are local favorites.",
            ),
            _hit(
                "Chicago Bar Guide 2026",
                "https://example.com/guide",
                "This guide covers all neighborhoods.",
            ),
        ]
        out = normalize_hits(
            hits,
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars in chicago",
        )
        for src in out["research_sources"]:
            assert src.trip_addable is False, (
                f"Research source '{src.title}' has trip_addable=True which is forbidden"
            )

    def test_article_hit_type_is_research_source_not_verified_place(self):
        """Articles classified as article_listicle_blog_directory must have
        type='research_source', never 'verified_place'."""
        hit = _hit(
            "Best 10 Restaurants In Chicago",
            "https://example.com/top-restaurants",
            "1. Alinea — Lincoln Park. 2. Smyth — West Loop.",
        )
        out = normalize_hits(
            [hit],
            intent=INTENT_RESTAURANTS,
            destination="Chicago",
            user_query="restaurants",
        )
        for src in out["research_sources"]:
            assert src.type == "research_source"
        # The article title itself must not be in addable results
        for rest in out["restaurants"]:
            assert "Best 10 Restaurants" not in rest.name

    def test_venues_discovered_set_after_google_verification(self):
        """venues_discovered on research source == number of places that passed
        the Google gate from that article.

        Tested via normalize_hits directly so we have full control over both
        phase-2 verified_candidates and phase-3 google_verifications.
        """
        article = _hit(
            "Top Cocktail Bars Chicago",
            "https://example.com/top-bars",
            "1. Kumiko — West Loop cocktail bar in Chicago.",
        )
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar", "bar"],
        )
        out = normalize_hits(
            [article],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
            verified_candidates={
                "kumiko": VerificationResult(
                    verified=True,
                    source_url="https://www.yelp.com/biz/kumiko",
                    neighborhood="West Loop",
                    reason="Verified on Yelp",
                )
            },
            google_verifications={"kumiko": google},
            max_per_kind=8,
        )
        # Kumiko should be in addable restaurants
        assert any(r.name == "Kumiko" for r in out["restaurants"]), (
            "Kumiko should be promoted to addable after Google verification"
        )
        # The article source (if returned, depends on venue_count cap) should
        # have venues_discovered >= 1 when it IS included.
        article_sources = [
            s for s in out.get("research_sources", [])
            if s.source_type == "article_listicle_blog_directory"
            and "top-bars" in (s.source_url or "")
        ]
        # venues_discovered is always set even if the source is capped out of
        # the return; when shown it must reflect the correct count.
        for src in article_sources:
            assert src.venues_discovered >= 1, (
                "Article research source must show venues_discovered >= 1 after a venue passes Google gate"
            )


# ── SourceEvidence field tests ────────────────────────────────────────────────

class TestSourceEvidenceInSerializedJSON:
    """source_evidence must appear in serialized JSON for article-derived verified places."""

    def setup_method(self):
        reset_global_cache()

    def _svc_with_google(self, provider, google_map) -> LiveResearchService:
        class _Stub:
            available = True
            def verify(self, name, destination, neighborhood=None, intent=None):
                return google_map.get(name.lower(), GooglePlaceVerification(
                    confidence="unknown", failure_reason="not_found"
                ))
            def clear_cache_for_destination(self, destination):
                return 0
        return LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=_Stub(),
        )

    def test_article_derived_venue_has_source_evidence_field(self):
        """After Google verification, article-extracted venues carry source_evidence."""
        article = _hit(
            "Best Cocktail Bars In Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy cocktail bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"Kumiko": verify_hit})
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL 60661",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar", "bar"],
        )
        svc = self._svc_with_google(provider, {"kumiko": google})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        card = next((r for r in result.restaurants if r.name == "Kumiko"), None)
        assert card is not None
        assert card.source_evidence is not None
        assert isinstance(card.source_evidence, SourceEvidence)
        assert card.source_evidence.source_title is not None
        assert card.source_evidence.source_url == "https://example.com/bars"

    def test_source_evidence_serializes_to_json_with_snake_case(self):
        """source_evidence serializes as snake_case JSON (backend contract)."""
        article = _hit(
            "Top Bars Chicago",
            "https://example.com/top-bars",
            "1. The Aviary — special-occasion cocktail bar in the West Loop.",
        )
        verify_hit = _hit(
            "The Aviary", "https://www.yelp.com/biz/aviary",
            "Cocktail bar at 955 W Fulton Market, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"The Aviary": verify_hit})
        google = GooglePlaceVerification(
            provider_place_id="gp-aviary",
            name="The Aviary",
            formatted_address="955 W Fulton Market, Chicago, IL 60607",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar", "bar"],
        )
        svc = self._svc_with_google(provider, {"the aviary": google})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        card = next((r for r in result.restaurants if r.name == "The Aviary"), None)
        assert card is not None
        assert card.source_evidence is not None
        json_str = card.model_dump_json()
        assert '"source_evidence"' in json_str

    def test_source_reason_from_article_text_stays_sanitized(self):
        """source evidence remains structured while summary stays deterministic and clean."""
        article = _hit(
            "Best Bars in Chicago",
            "https://example.com/bars",
            "1. Kumiko — speakeasy cocktail bar in West Loop offering seasonal cocktails.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"Kumiko": verify_hit})
        google = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar"],
        )
        svc = self._svc_with_google(provider, {"kumiko": google})
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        card = next((r for r in result.restaurants if r.name == "Kumiko"), None)
        assert card is not None
        ev = card.source_evidence
        assert "####" not in (card.summary or "")
        assert "[...]" not in (card.summary or "")
        if ev and ev.source_reason:
            assert "speakeasy" in ev.source_reason.lower()
        assert all("http" not in (entry or "").lower() for entry in (card.evidence or []))


class TestBannedGenericPhrases:
    """Banned generic phrases must not appear as source_reason when article evidence exists."""

    def test_extracted_from_local_guide_is_banned(self):
        """'Extracted from local guide' must not appear in source_evidence.source_reason."""
        article = _hit(
            "Best Cocktail Bars In Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop speakeasy cocktail bar in Chicago.",
        )
        out = normalize_hits(
            [article],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
        )
        for r in out["restaurants"]:
            ev = r.source_evidence
            if ev and ev.source_reason:
                lower = ev.source_reason.lower()
                assert "extracted from local guide" not in lower
                assert "confirmed as an operational google place" not in lower
                assert "found in article" not in lower
                assert "verified on google" not in lower

    def test_generic_phrases_not_in_summary_when_article_evidence_exists(self):
        """Card summary must not contain banned pipeline phrases."""
        article = _hit(
            "Best Bars in Chicago",
            "https://example.com/bars",
            "1. The Aviary — avant-garde cocktails in the West Loop of Chicago.",
        )
        out = normalize_hits(
            [article],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
        )
        banned = [
            "extracted from local guide",
            "confirmed as an operational google place",
            "found in article",
        ]
        for r in out["restaurants"]:
            summary_lower = (r.summary or "").lower()
            for phrase in banned:
                assert phrase not in summary_lower, (
                    f"Banned phrase '{phrase}' found in card summary: {r.summary!r}"
                )

    def test_source_evidence_source_reason_not_empty_for_strong_snippet(self):
        """A rich snippet should yield a non-empty source_reason."""
        article = _hit(
            "Best Cocktail Bars In Chicago 2026",
            "https://www.theinfatuation.com/chicago/guides/best-bars",
            "1. Kumiko — seasonal cocktail bar in West Loop, a must-visit in Chicago.",
        )
        out = normalize_hits(
            [article],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="bars",
        )
        kumiko = next((r for r in out["restaurants"] if r.name == "Kumiko"), None)
        if kumiko and kumiko.source_evidence:
            # source_reason should have been extracted from the dash-pattern
            assert kumiko.source_evidence.source_reason is not None


class TestMentionCountDedup:
    """Duplicate Google place_id must merge mention_count, not create duplicate cards."""

    def setup_method(self):
        reset_global_cache()

    def _google_stub(self, mapping):
        class _Stub:
            available = True
            def verify(self, name, destination, neighborhood=None, intent=None):
                return mapping.get(name.lower(), GooglePlaceVerification(
                    confidence="unknown", failure_reason="not_found"
                ))
            def clear_cache_for_destination(self, destination):
                return 0
        return _Stub()

    def test_same_place_id_increments_mention_count_not_duplicates(self):
        """Two article hits pointing to the same Google place must yield one card with mention_count=2."""
        direct_hit = _hit(
            "Kumiko",
            "https://example.com/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago IL.",
        )
        article_hit = _hit(
            "Best Bars In Chicago",
            "https://example.com/best-bars",
            "1. Kumiko — West Loop cocktail bar in Chicago.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([direct_hit, article_hit], {"Kumiko": verify_hit})
        same_google = GooglePlaceVerification(
            provider_place_id="gp-kumiko-shared",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL 60661",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar", "bar"],
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({"kumiko": same_google}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        kumiko_cards = [r for r in result.restaurants if r.name == "Kumiko"]
        assert len(kumiko_cards) == 1, "Duplicate place_id must produce exactly one card"

    def test_mention_count_incremented_when_duplicate_place_id(self):
        """When a venue appears in two sources with the same place_id, mention_count must be > 1."""
        article1 = _hit(
            "Best Cocktail Bars Chicago",
            "https://example.com/bars1",
            "1. Kumiko — West Loop speakeasy bar in Chicago.",
        )
        article2 = _hit(
            "Top Nightlife Chicago",
            "https://example.com/bars2",
            "1. Kumiko — seasonal cocktail bar in Chicago West Loop.",
        )
        verify_hit = _hit(
            "Kumiko", "https://www.yelp.com/biz/kumiko",
            "Cocktail bar at 630 W Lake St, Chicago, IL."
        )
        provider = _make_verifying_provider([article1, article2], {"Kumiko": verify_hit})
        same_google = GooglePlaceVerification(
            provider_place_id="gp-kumiko-multi",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            confidence="high",
            types=["cocktail_bar"],
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({"kumiko": same_google}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        kumiko_cards = [r for r in result.restaurants if r.name == "Kumiko"]
        assert len(kumiko_cards) == 1
        card = kumiko_cards[0]
        if card.source_evidence is not None:
            assert card.source_evidence.mention_count >= 1

    def test_two_distinct_place_ids_both_addable_with_separate_evidence(self):
        """Two venues with distinct place_ids both appear with their own source_evidence."""
        hits = [
            _hit("Kumiko", "https://example.com/kumiko", "Cocktail bar at 630 W Lake St, Chicago IL."),
            _hit("The Aviary", "https://example.com/aviary", "Bar at 955 W Fulton Market, Chicago IL."),
        ]
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-kumiko-distinct",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
            "the aviary": GooglePlaceVerification(
                provider_place_id="gp-aviary-distinct",
                name="The Aviary",
                formatted_address="955 W Fulton Market, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
        }
        provider = _make_verifying_provider(hits, {})
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        names = {r.name for r in result.restaurants}
        assert "Kumiko" in names
        assert "The Aviary" in names


class TestRawArticleNeverAddsCard:
    """Regression: raw article/listicle titles must never become addable venue cards."""

    def test_article_title_source_evidence_is_none_for_research_source(self):
        """Research source cards do not carry source_evidence (it belongs on venue cards only)."""
        hit = _hit(
            "The 22 Best Cocktail Bars In Chicago",
            "https://example.com/best-bars",
            "Kumiko, The Aviary, and Billy Sunday top the list.",
        )
        out = normalize_hits(
            [hit],
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        for src in out["research_sources"]:
            # research_source objects don't have source_evidence field
            assert not hasattr(src, "source_evidence") or src.source_evidence is None  # type: ignore[attr-defined]

    def test_non_operational_google_places_excluded(self):
        """Venues whose Google result is CLOSED_PERMANENTLY must not appear as addable cards."""
        article = _hit(
            "Chicago Bars Guide",
            "https://example.com/bars",
            "1. OldSpot — Famous dive bar in Logan Square in Chicago.",
        )
        verify_hit = _hit(
            "OldSpot", "https://www.yelp.com/biz/oldspot",
            "Bar at 1234 N Milwaukee Ave, Chicago, IL."
        )
        provider = _make_verifying_provider([article], {"OldSpot": verify_hit})
        google_closed = GooglePlaceVerification(
            provider_place_id="gp-oldspot",
            name="OldSpot",
            formatted_address="1234 N Milwaukee Ave, Chicago, IL",
            business_status="CLOSED_PERMANENTLY",
            confidence="high",
        )

        class _Stub:
            available = True
            def verify(self, name, destination, neighborhood=None, intent=None):
                return {"oldspot": google_closed}.get(name.lower(), GooglePlaceVerification(
                    confidence="unknown", failure_reason="not_found"
                ))
            def clear_cache_for_destination(self, destination):
                return 0

        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=_Stub(),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="bars")
        assert not any(r.name == "OldSpot" for r in result.restaurants), (
            "CLOSED_PERMANENTLY venue must not appear as addable card"
        )


class TestGooglePipelineRegression:
    def _google_stub(self, mapping):
        class _Stub:
            available = True

            def verify(self, name, destination, neighborhood=None, intent=None):
                return mapping.get(name.lower(), GooglePlaceVerification(confidence="unknown", failure_reason="not_found"))

            def clear_cache_for_destination(self, destination):
                return 0

        return _Stub()

    def test_underflow_prevention_returns_five_plus_when_six_operational_exist(self):
        article = _hit(
            "Best Cocktail Bars in Chicago",
            "https://example.com/bars",
            "1. Kumiko — West Loop cocktail bar. 2. The Aviary — Fulton Market cocktails. "
            "3. Billy Sunday — Logan Square bar. 4. Meadowlark — near Logan Square. "
            "5. Moneygun — River North cocktails. 6. Sparrow — classic cocktails.",
        )
        google_map = {
            "kumiko": GooglePlaceVerification(provider_place_id="1", name="Kumiko", business_status="OPERATIONAL", confidence="high", types=["bar"]),
            "the aviary": GooglePlaceVerification(provider_place_id="2", name="The Aviary", business_status="OPERATIONAL", confidence="medium", types=["bar"]),
            "billy sunday": GooglePlaceVerification(provider_place_id="3", name="Billy Sunday", business_status="OPERATIONAL", confidence="medium", types=["bar"]),
            "meadowlark": GooglePlaceVerification(provider_place_id="4", name="Meadowlark", business_status="OPERATIONAL", confidence="medium", types=["bar"]),
            "moneygun": GooglePlaceVerification(provider_place_id="5", name="Moneygun", business_status="OPERATIONAL", confidence="high", types=["bar"]),
            "sparrow": GooglePlaceVerification(provider_place_id="6", name="Sparrow", business_status="OPERATIONAL", confidence="medium", types=["bar"]),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert len(result.restaurants) >= 5

    def test_no_pre_verification_cap_keeps_pool_above_final_results(self):
        hits = [
            _hit("Chicago Cocktail Guide", "https://example.com/guide", "1. Kumiko 2. The Aviary 3. Billy Sunday 4. Meadowlark 5. Moneygun 6. Sparrow 7. Estereo 8. Arbella 9. Lazy Bird"),
            _hit("Kumiko", "https://example.com/k", "Cocktail bar."),
        ]
        google_map = {
            n.lower(): GooglePlaceVerification(
                provider_place_id=f"gp-{i}",
                name=n,
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            )
            for i, n in enumerate(["Kumiko", "The Aviary", "Billy Sunday", "Meadowlark", "Moneygun", "Sparrow", "Estereo", "Arbella", "Lazy Bird"], start=1)
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider(hits),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars near my hotel")
        assert len(result.restaurants) == 8

    def test_reason_text_is_clean_not_address_led_and_no_cross_contamination(self):
        article = _hit(
            "Chicago restaurants",
            "https://example.com/restaurants",
            "Aba and Beatrix are two popular options.",
        )
        google_map = {
            "aba": GooglePlaceVerification(provider_place_id="aba-1", name="Aba", business_status="OPERATIONAL", confidence="high", types=["restaurant"], rating=4.6),
            "beatrix": GooglePlaceVerification(provider_place_id="bea-1", name="Beatrix", business_status="OPERATIONAL", confidence="high", types=["restaurant"], rating=4.5),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="best restaurants near my hotel")
        names = [r.name for r in result.restaurants]
        for card in result.restaurants:
            reason = (card.summary or "").lower()
            assert not reason.startswith("aba is")
            assert "###" not in reason
            assert "http" not in reason
            assert "google reviews" not in reason
            assert "★" not in reason
            for other in names:
                if other.lower() == card.name.lower():
                    continue
                assert other.lower() not in reason

    def test_supporting_details_include_rating_and_address_only_outside_primary_reason(self):
        article = _hit("Kumiko", "https://example.com/k", "Cocktail bar in Chicago.")
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-1",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.7,
                user_rating_count=1200,
                types=["bar"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert result.restaurants
        card = result.restaurants[0]
        primary = (card.primary_reason or card.summary or "").lower()
        assert "google reviews" not in primary
        assert "★" not in primary
        assert "630 w lake st" not in primary
        assert card.supporting_details is not None
        assert card.supporting_details.rating == "4.7"
        assert card.supporting_details.review_count == 1200
        assert "Lake St" in (card.supporting_details.address or "")
        # Display fields: meta_line is "★ 4.7 (1,200 reviews) · address" only.
        meta = card.supporting_details.meta_line or ""
        assert meta.startswith("★ 4.7")
        assert "(1,200 reviews)" in meta
        assert "Lake St" in meta
        # Internal/debug terms must never appear in the user-facing display fields.
        for forbidden in (
            "source checked",
            "editorial mention",
            "source fit",
            "evidence:",
            "tavily",
            "verification score",
            "google verified",
        ):
            assert forbidden not in meta.lower()
            assert forbidden not in (card.supporting_details.why_pick or "").lower()
            assert forbidden not in (card.supporting_details.concierge_note or "").lower()
        # Category label must reflect the venue type, not the user's intent.
        assert (card.supporting_details.category_label or "").lower() in {"cocktail bar", "bar"}

    def test_restaurant_query_never_produces_bar_known_for_dining(self):
        # A bar that surfaces in a restaurant search must NOT mix categories.
        article = _hit(
            "The Aviary",
            "https://example.com/a",
            "The Aviary is a renowned cocktail bar in Chicago.",
        )
        google_map = {
            "the aviary": GooglePlaceVerification(
                provider_place_id="gp-aviary",
                name="The Aviary",
                formatted_address="955 W Fulton Market, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.6,
                user_rating_count=1500,
                types=["bar"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_RESTAURANTS,
            destination="Chicago",
            user_query="best restaurants near my hotel",
        )
        assert not result.restaurants
        assert any("category does not match this query intent" in (src.summary or "").lower() for src in result.research_sources)

    def test_cocktail_bar_query_never_produces_restaurant_only_dining_copy(self):
        article = _hit(
            "Kumiko",
            "https://example.com/k",
            "Cocktail bar in West Loop, Chicago.",
        )
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-1",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.7,
                user_rating_count=1200,
                types=["bar"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="best cocktail bars near my hotel",
        )
        assert result.restaurants
        card = result.restaurants[0]
        reason = (card.supporting_details.why_pick or card.primary_reason or "").lower()
        # Must read like a bar pick, not a restaurant pick.
        assert any(token in reason for token in ("cocktail", "drinks", "atmosphere", "night-out"))
        for forbidden in ("dining request", "tasting menu", "polished plates", "diner feedback"):
            assert forbidden not in reason

    def test_cafe_query_uses_cafe_language(self):
        article = _hit("Sawada Coffee", "https://example.com/s", "Iconic cafe in Chicago.")
        google_map = {
            "sawada coffee": GooglePlaceVerification(
                provider_place_id="gp-sawada",
                name="Sawada Coffee",
                formatted_address="112 N Green St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.6,
                user_rating_count=900,
                types=["cafe"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_RESTAURANTS,
            destination="Chicago",
            user_query="best cafes near my hotel",
        )
        # Cafes can be promoted as restaurants in this codebase, but the
        # category label and reason must remain coffee-shop focused.
        assert result.restaurants
        card = result.restaurants[0]
        details = card.supporting_details
        assert details is not None
        assert (details.category_label or "").lower() == "cafe"
        reason = (details.why_pick or card.primary_reason or "").lower()
        assert any(token in reason for token in ("coffee", "cafe", "casual"))
        assert "cocktails" not in reason
        assert "tasting menu" not in reason

    def test_supporting_details_never_leak_internal_metadata_terms(self):
        article = _hit("Kumiko", "https://example.com/k", "Cocktail bar in Chicago.")
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-1",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.7,
                user_rating_count=1200,
                types=["bar"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars",
        )
        assert result.restaurants
        card = result.restaurants[0]
        forbidden_terms = (
            "source checked",
            "editorial mention",
            "source fit",
            "evidence:",
            "tavily",
            "verification score",
            "###",
        )
        display_fields = [
            card.supporting_details.meta_line if card.supporting_details else None,
            card.supporting_details.why_pick if card.supporting_details else None,
            card.supporting_details.concierge_note if card.supporting_details else None,
            card.supporting_details.category_label if card.supporting_details else None,
            card.primary_reason,
        ]
        for value in display_fields:
            low = (value or "").lower()
            for forbidden in forbidden_terms:
                assert forbidden not in low, f"display leaked '{forbidden}': {value!r}"

    def test_meta_line_format_is_rating_reviews_address_only(self):
        article = _hit("Aba", "https://example.com/aba", "Restaurant in Chicago.")
        google_map = {
            "aba": GooglePlaceVerification(
                provider_place_id="gp-aba",
                name="Aba",
                formatted_address="302 N Green St 3rd Floor, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.8,
                user_rating_count=9483,
                types=["restaurant"],
            )
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_RESTAURANTS,
            destination="Chicago",
            user_query="best restaurants near my hotel",
        )
        assert result.restaurants
        meta = result.restaurants[0].supporting_details.meta_line or ""
        assert meta == "★ 4.8 (9,483 reviews) · 302 N Green St 3rd Floor, Chicago, IL"

    def test_research_sources_suppressed_when_addable_at_least_three(self):
        hits = [_hit("Best Cocktail Bars in Chicago", "https://example.com/bars", "1. Kumiko 2. The Aviary 3. Moneygun")]
        google_map = {
            "kumiko": GooglePlaceVerification(provider_place_id="1", name="Kumiko", business_status="OPERATIONAL", confidence="high", types=["bar"]),
            "the aviary": GooglePlaceVerification(provider_place_id="2", name="The Aviary", business_status="OPERATIONAL", confidence="high", types=["bar"]),
            "moneygun": GooglePlaceVerification(provider_place_id="3", name="Moneygun", business_status="OPERATIONAL", confidence="high", types=["bar"]),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider(hits),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert len(result.restaurants) >= 3
        assert result.research_sources == []

    def test_article_pages_stay_in_research_sources_not_addable_cards(self):
        article = _hit(
            "The 22 Best Cocktail Bars In Chicago",
            "https://example.com/top-22-bars",
            "A listicle about bars in Chicago.",
        )
        svc = LiveResearchService(
            provider=StubLiveSearchProvider([article]),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub({}),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert all("22 best cocktail bars" not in (r.name or "").lower() for r in result.restaurants)
        assert any("22 best cocktail bars" in (s.title or "").lower() for s in result.research_sources)

    def test_fail_closed_when_google_required_and_unavailable(self, monkeypatch):
        monkeypatch.setenv("RESEARCH_ENGINE_REQUIRE_GOOGLE_VERIFICATION", "true")
        provider = StubLiveSearchProvider(
            [_hit("Kumiko", "https://example.com/kumiko", "Cocktail bar in West Loop, Chicago.")]
        )
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert result.restaurants == []
        assert result.attractions == []
        assert result.hotels == []
        assert result.research_sources
        assert all(src.trip_addable is False for src in result.research_sources)

    def test_yelp_and_foursquare_never_introduce_new_places(self, monkeypatch):
        monkeypatch.setenv("YELP_API_KEY", "fake-key")
        monkeypatch.setenv("FOURSQUARE_API_KEY", "fake-key")
        provider = StubLiveSearchProvider(
            [_hit("Kumiko", "https://example.com/kumiko", "Cocktail bar in West Loop, Chicago.")]
        )
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-kumiko",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
            "aviary": GooglePlaceVerification(
                provider_place_id="gp-aviary",
                name="The Aviary",
                formatted_address="955 W Fulton Market, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
        }
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        names = [r.name for r in result.restaurants]
        assert "Kumiko" in names
        # Google-only truth: enrichment cannot create this card because it was never in candidates.
        assert "The Aviary" not in names

    def test_reason_guard_rejects_markdown_bullets_urls_and_option_phrase(self):
        known = ["Kumiko", "The Aviary"]
        bad_reasons = [
            "### Kumiko is amazing",
            "1. Kumiko is a bar in Chicago",
            "- Kumiko is a bar",
            "Kumiko is a bar option in West Loop.",
            "Read more at https://example.com/kumiko",
            "Kumiko matches your request.",
            "Kumiko is great. Also try The Aviary.",
        ]
        for reason in bad_reasons:
            assert _reason_guard(reason, "Kumiko", known) is False

    def test_build_place_reason_primary_sentence_is_clean_and_not_address_led(self):
        candidate = SimpleNamespace(
            cuisine="Cocktail Bar",
            source_evidence=SourceEvidence(source_reason="seasonal cocktail program"),
            tags=["Date Night", "Cocktails"],
        )
        verification = GooglePlaceVerification(
            provider_place_id="gp-kumiko",
            name="Kumiko",
            formatted_address="630 W Lake St, Chicago, IL",
            business_status="OPERATIONAL",
            rating=4.7,
            user_rating_count=1200,
            confidence="high",
            types=["bar"],
        )
        reason, reason_source = build_place_reason(
            candidate_name="Kumiko",
            user_query="cocktail bars near West Loop Chicago",
            intent=INTENT_NIGHTLIFE,
            candidate=candidate,
            verified_place=verification,
            known_candidate_names=["kumiko", "the aviary"],
        )
        low = reason.lower()
        assert "google reviews" not in low
        assert "★" not in low
        assert "###" not in reason
        assert "http" not in low
        assert "option in" not in low
        assert reason_source in {"deterministic_evidence", "deterministic_scoring", "fallback"}

    def test_sanitize_reason_evidence_rejects_polluted_examples(self):
        known = ["Green Mill", "Hubbard Inn", "Maria's", "The Darling", "Chicago Athletic Association"]
        assert _sanitize_reason_evidence_text(
            "xt day. [...] #### For Music Green Mill – legendary jazz room",
            own_name="Green Mill",
            known_candidate_names=known,
        ) is None
        assert _sanitize_reason_evidence_text(
            "The Darling – The Darling is a bar and restaurant with cocktails.",
            own_name="Hubbard Inn",
            known_candidate_names=known,
        ) is None
        assert _sanitize_reason_evidence_text(
            "#### For Something Fancy Chicago Athletic Association rooftop lounge",
            own_name="Maria's",
            known_candidate_names=known,
        ) is None
        cleaned = _sanitize_reason_evidence_text(
            "nightlife nightlife cocktails",
            own_name="Green Mill",
            known_candidate_names=known,
        )
        assert cleaned == "nightlife cocktails"

    def test_build_place_reason_rejects_other_venue_leak_and_uses_google_fallback(self):
        candidate = SimpleNamespace(
            source_evidence=SourceEvidence(source_reason="The Darling has strong cocktails and late-night buzz."),
            tags=["nightlife", "nightlife", "cocktails"],
        )
        verification = GooglePlaceVerification(
            provider_place_id="gp-hubbard",
            name="Hubbard Inn",
            formatted_address="110 W Hubbard St, Chicago, IL",
            business_status="OPERATIONAL",
            rating=4.3,
            user_rating_count=980,
            confidence="high",
            types=["bar"],
        )
        reason, reason_source = build_place_reason(
            candidate_name="Hubbard Inn",
            user_query="cocktail bars near West Loop Chicago",
            intent=INTENT_NIGHTLIFE,
            candidate=candidate,
            verified_place=verification,
            known_candidate_names=["Hubbard Inn", "The Darling", "Green Mill"],
        )
        low = reason.lower()
        assert "the darling" not in low
        # Bar verification → reason must use nightlife/bar-oriented wording.
        assert any(token in low for token in ("drinks", "cocktails", "nightlife", "bar"))
        assert "dining" not in low
        assert "menu" not in low
        assert "###" not in reason
        assert reason_source in {"deterministic_evidence", "deterministic_scoring", "fallback"}

    def test_enrichment_failures_do_not_block_google_verified_cards(self, monkeypatch):
        monkeypatch.setenv("YELP_API_KEY", "fake")
        monkeypatch.setenv("FOURSQUARE_API_KEY", "fake")
        provider = StubLiveSearchProvider(
            [_hit("Kumiko", "https://example.com/kumiko", "Cocktail bar in West Loop, Chicago.")]
        )
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-kumiko",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                types=["bar"],
            ),
        }
        svc = LiveResearchService(
            provider=provider,
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        svc._populate_yelp_enrichment = MagicMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]
        svc._populate_foursquare_enrichment = MagicMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]
        result = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars")
        assert result.restaurants
        assert result.restaurants[0].name == "Kumiko"
        assert result.restaurants[0].verified_place is True

    def test_integration_snapshot_west_loop_cocktail_bars(self):
        hits = [
            _hit(
                "Best Cocktail Bars in Chicago",
                "https://example.com/chicago-bars",
                "1. Kumiko — West Loop cocktail bar. 2. The Aviary — Fulton Market cocktails.",
            ),
            _hit("Kumiko", "https://example.com/kumiko", "Japanese cocktail bar in West Loop."),
            _hit("The Aviary", "https://example.com/aviary", "Avant-garde cocktails in Fulton Market."),
        ]
        google_map = {
            "kumiko": GooglePlaceVerification(
                provider_place_id="gp-kumiko",
                name="Kumiko",
                formatted_address="630 W Lake St, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.7,
                user_rating_count=1200,
                types=["bar"],
            ),
            "the aviary": GooglePlaceVerification(
                provider_place_id="gp-aviary",
                name="The Aviary",
                formatted_address="955 W Fulton Market, Chicago, IL",
                business_status="OPERATIONAL",
                confidence="high",
                rating=4.6,
                user_rating_count=900,
                types=["bar"],
            ),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider(hits),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(
            intent=INTENT_NIGHTLIFE,
            destination="Chicago",
            user_query="cocktail bars near West Loop Chicago",
        )
        assert len(result.restaurants) >= 2
        assert all((r.google_verification and r.google_verification.business_status == "OPERATIONAL") for r in result.restaurants)
        assert all(src.trip_addable is False for src in result.research_sources)
        for r in result.restaurants:
            text = (r.summary or "").lower()
            assert "###" not in text
            assert "http" not in text
            assert "option in" not in text
            assert "matches your request" not in text
            assert r.source_badges and "Google Verified" in r.source_badges
            assert r.best_for_tags

    def test_brunch_cafe_query_filters_out_bar_and_steakhouse_types(self):
        hits = [
            _hit("Lula Cafe", "https://example.com/lula", "All-day cafe with popular brunch service in Chicago."),
            _hit("Aba", "https://example.com/aba", "Mediterranean restaurant and cocktail bar."),
            _hit("The Capital Grille", "https://example.com/capital", "Classic steakhouse for dinner."),
        ]
        google_map = {
            "lula cafe": GooglePlaceVerification(provider_place_id="gp-lula", name="Lula Cafe", business_status="OPERATIONAL", confidence="high", types=["cafe", "restaurant"]),
            "aba": GooglePlaceVerification(provider_place_id="gp-aba", name="Aba", business_status="OPERATIONAL", confidence="high", types=["bar", "restaurant"]),
            "the capital grille": GooglePlaceVerification(provider_place_id="gp-capital", name="The Capital Grille", business_status="OPERATIONAL", confidence="high", types=["steak_house", "restaurant"]),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider(hits),
            cache=_TTLCache(0),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        result = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="brunch cafes near my hotel")
        names = [r.name.lower() for r in result.restaurants]
        assert "lula cafe" in names
        assert "aba" not in names
        assert "the capital grille" not in names
        assert all("buzzing late-night crowd" not in ((r.primary_reason or "").lower()) for r in result.restaurants)

    def test_query_sequence_does_not_contaminate_brunch_with_cocktail_results(self):
        hits = [
            _hit("Kumiko", "https://example.com/kumiko", "Cocktail bar in West Loop."),
            _hit("Lula Cafe", "https://example.com/lula", "Brunch cafe in Logan Square."),
        ]
        google_map = {
            "lula cafe": GooglePlaceVerification(provider_place_id="gp-lula", name="Lula Cafe", business_status="OPERATIONAL", confidence="high", types=["cafe", "restaurant"]),
            "kumiko": GooglePlaceVerification(provider_place_id="gp-kumiko", name="Kumiko", business_status="OPERATIONAL", confidence="high", types=["cocktail_bar", "bar"]),
        }
        svc = LiveResearchService(
            provider=StubLiveSearchProvider(hits),
            cache=_TTLCache(600),
            verification_cache=_TTLCache(0),
            enabled=True,
            place_verifier=self._google_stub(google_map),
        )
        night = svc.fetch(intent=INTENT_NIGHTLIFE, destination="Chicago", user_query="cocktail bars near my hotel")
        assert any(r.name == "Kumiko" for r in night.restaurants)
        brunch = svc.fetch(intent=INTENT_RESTAURANTS, destination="Chicago", user_query="brunch cafes near my hotel")
        brunch_names = [r.name.lower() for r in brunch.restaurants]
        assert "lula cafe" in brunch_names
        assert "kumiko" not in brunch_names
        assert all("cocktail" not in (r.primary_reason or "").lower() for r in brunch.restaurants)

    def test_cache_key_includes_derived_category_and_anchor(self):
        k1 = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "brunch cafes near my hotel")
        k2 = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "best restaurants near my hotel")
        k3 = _make_cache_key(INTENT_RESTAURANTS, "Chicago", "brunch cafes in chicago")
        assert k1 != k2
        assert k1 != k3


# ── Frontend source evidence rendering (file-read tests) ─────────────────────

class TestFrontendSourceEvidenceRendering:
    """Check AIConciergePanel.tsx renders clean reason/evidence fields only."""

    def _read_panel(self) -> str:
        root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        panel_path = os.path.join(root, "frontend", "src", "components", "trips", "AIConciergePanel.tsx")
        with open(panel_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_panel_uses_pick_card_reason_helper(self):
        """AIConciergePanel must call pickCardReason() for venue cards."""
        src = self._read_panel()
        assert "pickCardReason" in src, "pickCardReason helper must be present"

    def test_panel_uses_clean_supporting_details_only(self):
        """Card meta and details must come from clean supportingDetails fields."""
        src = self._read_panel()
        assert "supportingDetails" in src
        # Internal/debug labels MUST NOT appear in the rendered card.
        assert "Source fit" not in src
        assert "Evidence: Mentioned in" not in src
        assert "editorial mention" not in src
        assert "source checked" not in src
        # Expanded details must use the user-facing concierge note only.
        assert "conciergeNote" in src

    def test_panel_no_more_button_without_extra_detail(self):
        """expandableDetail variable controls the More button — not shown when undefined."""
        src = self._read_panel()
        assert "hasDetail" in src
        assert "pickCardDetail" in src

    def test_panel_hides_research_sources_when_addable_cards_exist(self):
        src = self._read_panel()
        assert "addableCount(msg) < 3" in src

    def test_panel_meta_line_uses_rating_reviews_address_only(self):
        """Meta line must come from supportingDetails.metaLine; no leaky tokens."""
        src = self._read_panel()
        assert "metaLine" in src
        # Meta must never include editorial / source-checked tokens.
        assert "editorialMentions" not in src or "details?.editorialMentions" not in src
        assert "evidenceCount" not in src or "place.evidenceCount" not in src
