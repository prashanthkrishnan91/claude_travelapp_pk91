from app.concierge.reasoning import BANNED_STRINGS_RE, build_why_pick, ensure_non_empty_evidence


def test_synthetic_payloads_all_pass_banned_strings_filter():
    for i in range(50):
        evidence = ensure_non_empty_evidence(
            [f"Mentioned by {i % 5 + 1} guides" if i % 2 == 0 else ""],
            rating=4.0 + ((i % 10) / 10.0),
            review_count=100 + i,
            neighborhood="West Loop" if i % 3 == 0 else None,
            tags=["cocktail bar", "late-night"],
        )
        payload = build_why_pick(
            place_name=f"Place {i}",
            evidence=evidence,
            rating=4.0 + ((i % 10) / 10.0),
            review_count=100 + i,
        )
        text = payload["why_pick"]["text"]
        assert text
        assert not BANNED_STRINGS_RE.search(text)


def test_template_selection_is_deterministic_for_evidence_shape():
    both = build_why_pick(
        place_name="Kumiko",
        evidence=["Rated 4.7 (1,200 reviews)", "Mentioned by 3 guides"],
        rating=4.7,
        review_count=1200,
    )
    assert both["template_id"] == "rating_and_editorial"

    editorial_only = build_why_pick(
        place_name="Alinea",
        evidence=["Mentioned by 4 guides"],
        rating=None,
        review_count=None,
    )
    assert editorial_only["template_id"] == "editorial_only"

    google_only = build_why_pick(
        place_name="Cloud Gate",
        evidence=["Rated 4.8 (20,121 reviews)"],
        rating=4.8,
        review_count=20121,
    )
    assert google_only["template_id"] == "google_only"
