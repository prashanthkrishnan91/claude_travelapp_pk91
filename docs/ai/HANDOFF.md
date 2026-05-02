# AI Handoff — Travel Concierge

## Last change (2026-05-02) — Provider Result Cache v1

Added a soft-TTL in-memory provider result cache for the `LiveResearchService.fetch()` path (Tavily/Brave/Serper), with a quality gate to avoid serving stale/weak results.

### Files touched
- `backend/app/services/provider_cache.py` — NEW: `ProviderResultCache` class, `is_live_research_payload_quality_sufficient()` quality gate, module-level singleton + reset helper
- `backend/app/services/live_research.py` — `_TTLCache.get_with_status()` compat shim; `_GLOBAL_CACHE` upgraded from `_TTLCache(1800)` to `ProviderResultCache()`; `fetch()` updated with soft-TTL read logic, quality gate on both read and store, structured log events; `reset_global_cache()` updated
- `backend/tests/test_provider_cache.py` — NEW: 46 focused tests covering all cache paths

### Behavior change
**Before:** `LiveResearchService` used a 30-minute hard-expiry `_TTLCache`. On expiry the result was silently discarded and the live provider was called.

**After:** Three-tier soft TTL:
- `0–6h` (FRESH): return from cache; skip live provider
- `6–24h` (STALE): return from cache only if quality gate passes; otherwise fall through to live provider
- `24h+` (EXPIRED): bypass cache, force live provider call

**Quality gate (read + write):**
- Payload must be a non-empty dict
- `cache_version` must match `CONCIERGE_CACHE_VERSION`
- `source_status` must not be `error`/`unavailable`/`none`
- Intent-aware minimum: restaurant intents require ≥1 restaurant OR research_sources; attraction intents require ≥1 attraction OR research_sources; hotel intents require ≥1 hotel OR research_sources; general intents require any non-zero total
- Truly empty payloads (all buckets zero) are never stored or reused

**Log events added:**
- `live_research_cache hit` — FRESH cache reuse
- `live_research_cache stale_reuse` — STALE cache reuse (quality ok)
- `live_research_cache weak_bypass` — cache found but quality gate failed
- `live_research_cache miss` — no cache entry (or expired/bypassed)
- `live_research_cache stored` — result stored after live provider call
- `live_research_cache not_stored` — live result not stored (weak quality)
- `live_research_cache read_error` / `write_error` — cache exception, logged and ignored

**Cache failures are non-fatal:** both `get_with_status()` and `set()` are wrapped in try/except; any exception falls through to the live provider path.

**Backward compatible:** existing tests that inject `_TTLCache(0)` (disabled cache) continue to work via the `get_with_status()` compatibility shim. No Supabase SQL required. No response schema changes. No frontend changes.

### Cache contract for future AI agents
- Cache singleton: `backend/app/services/provider_cache._PROVIDER_CACHE`
- Import: `from app.services.provider_cache import ProviderResultCache, get_provider_cache, reset_provider_cache`
- Cache key: produced by `_make_cache_key(intent, destination, query, dates)` in `live_research.py` — normalizes whitespace/case; includes intent, destination, derived_category, location_anchor
- TTL constants: `FRESH_SECONDS = 21600`, `STALE_SECONDS = 86400` — can be adjusted in `provider_cache.py`
- Quality gate function: `is_live_research_payload_quality_sufficient(payload, intent=..., cache_version=...)` — import from `provider_cache`
- Test helper: `reset_provider_cache()` clears the singleton; `reset_global_cache()` in `live_research.py` calls it automatically

### Known issues
- `ProviderResultCache` is in-memory only: restarts clear the cache. For persistence across restarts, a future v2 could use Redis or Supabase with the existing `research_cache` table.
- STALE tier TTL (6–24h) means popular searches on a busy day will be served stale data for up to 18h when quality is ok. This is intentional (cost reduction) but should be monitored.

### Next likely task
- Monitor `live_research_cache stale_reuse` and `weak_bypass` log rates in production to tune FRESH/STALE thresholds
- Consider a `?refresh=true` query param on `/ai/concierge/search` to force bypass (already has a `DELETE /ai/concierge/cache` endpoint for manual clear)
- Provider result cache v2: Redis or Supabase persistence for cross-restart cache warmth

### Supabase SQL required: No
### Backend touched: Yes (`live_research.py`, new `provider_cache.py`)
### Frontend touched: No

---

## Previous change (2026-04-29) — UI Design System: Dark Mode-First Foundation

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
