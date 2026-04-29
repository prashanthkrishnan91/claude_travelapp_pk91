# AI Handoff — Travel Concierge

## Last change (2026-04-29) — UI Design System: Dark Mode-First Foundation

Frontend-only visual upgrade to a premium boutique concierge aesthetic. No backend, API, or business-logic changes.

### Files touched
- `frontend/src/app/globals.css` — full dark theme: body background, `.card`, `.glass`, `.btn-primary` (→ warm gold), `.btn-ghost`, `.btn-emerald`, `.btn-gold`, form controls, badges, skeleton, nav items, color tokens (`--color-cream-*`, `--color-dark-*`, `--color-brand-*`)
- `frontend/src/components/layout/AppShell.tsx` — ambient glow blobs → warm gold/amber on dark bg; loading state → dark
- `frontend/src/components/layout/Sidebar.tsx` — brand icon → gold; borders → white/7%; nav section labels, user avatar
- `frontend/src/components/layout/MobileNav.tsx` — brand icon/active tabs → gold; drawer overlay → black/60%; borders → white/7%
- `frontend/src/components/layout/PageHeader.tsx` — h1 → cream-100; description → cream-500
- `frontend/src/components/ui/StatCard.tsx` — label/value/trend text → cream scale; default colorClass → brand gold
- `frontend/src/components/ui/EmptyState.tsx` — icon container → dark glass surface
- `frontend/src/components/dashboard/DashboardClient.tsx` — stat colorClass props → dark tinted variants
- `frontend/src/components/dashboard/RecentTrips.tsx` — all text/border/hover/link/icon classes → dark
- `frontend/src/components/dashboard/QuickActions.tsx` — action tile surfaces and text → dark
- `frontend/src/components/dashboard/PointsSummary.tsx` — surfaces, text, card color chips → dark
- `frontend/src/components/dashboard/DealsFeed.tsx` — hover/badge/text/link → dark with gold accent
- `frontend/src/app/trips/page.tsx` — modals: `bg-white` → `.card`; inputs → `.input`/`.label`; trip card text/border/button classes → dark

### Behavior change
Visual only. Layout, routing, data, auth, business logic: unchanged. All existing data continues to render identically.

### Design tokens introduced
- `--color-cream-{50–500}`: warm text scale (cream-100 = primary text on dark)
- `--color-dark-{50–500}`: dark surface scale
- `--color-brand-{300–700}`: warm gold accent (replaces sky-blue as primary CTA/accent)

### Known limitations
- Deep trip-detail pages (`/trips/[id]`, concierge panel, search results, cards page) still use light-era Tailwind classes — these pages will inherit the dark card/glass/body styles but inline text classes (`text-slate-*`) may appear dark-on-dark in some sections. Follow-up pass needed.
- Auth pages unchanged (already have a luxury dark background).

### Next likely task
- Page-by-page polish pass: `/trips/[id]` TripBuilder, AIConciergePanel, SearchResultCard, `/cards`, `/settings`
- Consider adding a `text-cream-100` default to `[data-page]` wrappers so any remaining `text-slate-900` elements fall back cleanly
- Validate on mobile (bottom nav gold active state, drawer)

### Supabase SQL required: No
### Backend touched: No

---

## Previous change — whyPick evidence enrichment
Enriched whyPick evidence quality by promoting venue-specific Foursquare tags, Tavily award signals, and Yelp "known for" patterns to structured differentiators (branch: claude/verify-whypick-pipeline-73XFm).

## Files touched
- `backend/app/concierge/evidence.py` — core evidence enrichment
- `backend/tests/test_evidence_normalization.py` — 8 new tests
- `backend/tests/test_whypick_differentiators.py` — 2 updated assertions, 8 new tests

## Behavior change
**Foursquare tag specificity filter** (`_foursquare_tag_is_specific`):
- Tags like "handmade tortillas", "craft cocktails", "zero-waste", "omakase" → `safe_for_copy=True`, `confidence=medium`
- Tags like "trendy", "date-night", "casual" → remain `safe_for_copy=False`
- Effect: venues with only Foursquare tags now surface as differentiators in `select_differentiators()` and reach the LLM prompt as anchors

**Tavily award extraction** (`_AWARD_SIGNAL_RE`):
- Tavily snippets mentioning Michelin stars, James Beard, award-winning → promote an `attribute` unit with `safe_for_copy=True`
- Enables LLM to anchor whyPick on awards even when no Michelin status was supplied explicitly

**Yelp "known for" extraction** (`_KNOWN_FOR_RE`):
- Yelp review excerpts with "known for X", "celebrated for X", "acclaimed for X" → promote an `attribute` unit with `safe_for_copy=True`
- Enables extraction of signature item signals from user reviews

**Before / After examples:**

| Venue | Before | After |
|-------|--------|-------|
| Kumiko (FS tags only, no editorial) | "A cocktail bar in West Loop, a reliable spot for evening drinks." | "Kumiko is a cocktail bar in West Loop known for japanese-inspired cocktails." |
| Mas Maiz (FS tags) | "Mas Maiz is a Mexican restaurant in Capitol Hill..." (rating fallback) | "Mas Maiz is a Mexican restaurant in Capitol Hill known for handmade tortillas." |

## Known issues
- LLM path still requires `ANTHROPIC_API_KEY` to be set; deterministic path is the active path in all test runs
- Foursquare tag content is lowercased in the deterministic copy builder (`specialty_tags[0].lower()`); proper-noun tags like "Japanese" become lowercase
- foursquare_category units remain `safe_for_copy=False` (category labels are not differentiators)

## Next likely task
- Fix lowercasing of specialty tag copy in `reasoning.py` (`_build_nightlife_display_why` / `_build_cuisine_restaurant_display_why`)
- Validate that real-world Foursquare tags returned by live API are specific enough to pass the filter (audit production data)
- Consider surfacing yelp_review_excerpt "known for" extraction also from editorial `source_reason` text for secondary attribute units

## Debug notes
- Test suite: 112 tests, 0 failures as of this change
- `_foursquare_tag_is_specific()` in `evidence.py:46` controls the promotion logic; extend `_GENERIC_FS_TAGS` if new generic tags appear in production
- Award regex: `_AWARD_SIGNAL_RE` in `evidence.py:74`; handles "Michelin stars" (plural) and "James Beard" variants
- All new evidence units preserve the `venue_name` anti-contamination field

## 2026-04-29 Hardening Follow-up (Post PR #164)

### Summary
- Extended generic Foursquare tag blocklist with: `cocktail bar`, `highly rated`, `good drinks`, `nightlife`.
- Added Yelp `known for X` generic-signal guard to reject service/praise-only matches (`great`, `customer`, `service`, `popular`, `nice`, `friendly`, `good food`, `good drinks`) while preserving specific differentiators.
- Threaded safe attribute-claim units (`yelp`/`tavily` attributes) into deterministic fallback specialty tags so fallback whyPick can use concrete non-Foursquare differentiators.

### Tests
- `backend/tests/test_evidence_normalization.py`
- `backend/tests/test_whypick_differentiators.py`
- `backend/tests/test_whypick_integration.py`

### Next Step
- Monitor production logs for fallback whyPick copy quality to confirm no drift toward generic language after adding attribute-driven specialty fallback.
