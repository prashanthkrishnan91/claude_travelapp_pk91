# AI Handoff — Travel Concierge

## Last change (2026-04-30) — Trip Ideas Triage v1

### Summary
Added priority/status triage and user notes to the Trip Ideas panel. Each saved idea now supports a `must_do | maybe | skipped` status and an optional short note. Skipped ideas are hidden from the default list with a "N skipped · show" toggle to reveal them. Status and notes persist to Supabase via the existing JSONB merge approach (no new table, no migration).

### Files touched
- `frontend/src/lib/api.ts` — added `updateIdeaMeta(itemId, currentDetails, patch)` which merges `{ ideaStatus?, userNote? }` into the existing details dict and calls the existing `PATCH /itinerary/items/{id}` endpoint; updated `saveToTripIdeas` to set `idea_status: "maybe"` as the default on new saves
- `frontend/src/components/trips/TripIdeasPanel.tsx` — added `STATUS_OPTIONS` (Must-do / Maybe / Skip); `IdeaCard` now renders a priority row with three pill buttons and an expandable note textarea (auto-debounced 800 ms); `TripIdeasPanel` filters visible ideas by `status !== "skipped"` by default and shows a "N skipped · show / hide" toggle when skipped ideas exist; added `handleUpdate` which optimistically updates local state and calls `updateIdeaMeta`
- `frontend/tests/trip-ideas.test.mjs` — added 3 new tests: `updateIdeaMeta` exported, `saveToTripIdeas` sets `idea_status: "maybe"`, TripIdeasPanel has Must-do/Maybe/Skip buttons
- `backend/tests/test_trip_ideas.py` — added 2 new tests: merged details update preserves `source_kind`, skipped ideas are still returned by the backend list (backend is status-agnostic; frontend filters)

### Behavior change
- New saved ideas default to `idea_status: "maybe"` stored in `details` JSONB
- Each Trip Idea card shows three priority pills: **Must-do** (emerald), **Maybe** (amber), **Skip** (slate)
- Clicking a pill immediately updates optimistically and persists via PATCH
- A **+ note** / **note ✎** button toggles an inline textarea; note is auto-saved 800 ms after last keystroke
- Ideas with `idea_status = "skipped"` are hidden by default; a small link at the bottom of the list reveals them
- Badge count on the Trip Ideas panel header reflects visible (non-skipped) count
- All previous behaviors preserved: Save from AI Concierge, immediate appearance, persist after refresh, assign to day, remove

### Data model
```
details.source_kind   = "concierge_idea"   (unchanged)
details.idea_status   = "must_do" | "maybe" | "skipped"   (new; default "maybe")
details.user_note     = string   (new; optional)
```
Frontend sends full merged details via existing `PATCH /itinerary/items/{id}`. Backend stores them as-is. No new endpoint, no migration.

### Known issues
- IdeaCard local `status`/`note` state is not synced back from props after an API failure (page refresh gives correct state). Acceptable for v1.
- `idea_status` for ideas saved before this PR will be treated as "maybe" by the frontend default logic.

### Next likely task
- Mobile viewport test: three-button status row on small screens
- Consider a subtle animation when status changes (e.g., card fades out on Skip)

### Supabase SQL: No
### Backend touched: No (tests only)

---

## Previous change (2026-04-30) — Trip Ideas UX Discoverability Fix

### Summary
UX patch on top of the Saved Shortlist feature: after saving, the concierge card now clearly shows "Saved to Ideas" (not just "Saved"), an auto-dismissing toast in the concierge drawer says "Saved to Trip Ideas — close this panel to schedule it.", and the Trip Ideas panel is always visible (never hidden when empty) with a subtitle explaining its purpose. Panel auto-expands whenever new ideas arrive.

### Files touched
- `frontend/src/components/trips/AIConciergePanel.tsx` — restored missing `inputRef`/`bottomRef` refs; added `setToast("Saved to Trip Ideas — close this panel to schedule it.")` call in `saveIdea` success path; changed saved button label from `Saved` to `Saved to Ideas`; auto-dismiss `useEffect` already in place
- `frontend/src/components/trips/TripIdeasPanel.tsx` — removed `if (!loading && ideas.length === 0) return null` guard; updated empty state text to "Save recommendations from AI Concierge and schedule them later."; added subtitle "Saved from AI Concierge · add to a day when ready" under heading; added `useEffect` to auto-expand (`setOpen(true)`) when ideas arrive

### Behavior change
- Concierge card saved state label: "Saved" → "Saved to Ideas"
- Toast fires inside concierge drawer after every successful save, auto-dismisses after 4 s
- Trip Ideas panel is always rendered (even empty), so users see where saved items will appear
- Panel auto-expands when the first idea is saved, surfacing it immediately

### Known issues
- Trip Ideas panel is always visible even on trips with no concierge activity — acceptable as it shows helpful onboarding empty state
- Toast position is fixed inside the concierge drawer overlay; visible only while drawer is open (intended — tells user to close and check the panel)

### Next likely task
- Mobile viewport test: two-button layout (Add to Day / Save) on small screens
- Consider a subtle animation when a new idea card appears in TripIdeasPanel

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-04-30) — Saved Trip Ideas / Unscheduled Shortlist

### Summary
Added a "Save to Ideas" flow that lets users save AI Concierge results to a trip without assigning them to a specific day. Saved ideas appear in a new **Trip Ideas** panel in the trip builder. Users can assign an idea to a day (removing it from the unscheduled list) or delete it.

### Files touched
- `backend/app/services/itinerary.py` — added `list_unscheduled_items(trip_id)`: returns items with `day_id IS NULL`
- `backend/app/routes/trips.py` — added `GET /trips/{trip_id}/ideas` endpoint
- `frontend/src/lib/api.ts` — added `fetchTripIdeas`, `saveToTripIdeas` (marks `source_kind: "concierge_idea"` in details), `assignIdeaToDay`, exported `ConciergeItemKind` type
- `frontend/src/components/trips/AIConciergePanel.tsx` — added "Save" button alongside "Add to Day"; `savedIdeaItems`/`savingIdeaItems` state; `saveIdea()` handler; `onIdeaSaved` prop; pre-populates saved state from existing ideas on panel open
- `frontend/src/components/trips/TripIdeasPanel.tsx` — NEW: collapsible panel listing concierge-saved ideas; per-idea "Add to Day" selector+button and remove button; fetches from `/trips/{trip_id}/ideas` filtered by `source_kind=concierge_idea`
- `frontend/src/components/trips/TripBuilder.tsx` — imports and renders `TripIdeasPanel` in right panel above day columns; accepts `ideasRefreshKey` and `onIdeaAssigned` props
- `frontend/src/app/trips/[id]/page.tsx` — adds `tripIdeasKey` state; passes `ideasRefreshKey` to TripBuilder; passes `onIdeaSaved` to AIConciergePanel; `onIdeaAssigned` refreshes itinerary days + TripBuilder
- `backend/tests/test_trip_ideas.py` — NEW: 7 backend unit tests
- `frontend/tests/trip-ideas.test.mjs` — NEW: 12 frontend renderer/contract tests

### Behavior change
- AI Concierge cards now show two actions: **Add to Day** (requires day selection, existing behavior) and **Save** (saves to trip without day assignment, new)
- A **Trip Ideas** section appears in the TripBuilder right panel above itinerary days, only when ideas exist
- Saved ideas are persisted to Supabase `itinerary_items` with `day_id = null` and `details.source_kind = "concierge_idea"`
- Duplicate protection: saving the same place to ideas twice returns the existing item
- Assigning an idea to a day updates `day_id` on the item and removes it from the unscheduled list
- Removing an idea deletes the item from `itinerary_items`

### Known issues
- No schema change: the existing `itinerary_items` table already supports `day_id = null`. The `source_kind` marker is stored in the `details` JSONB column (no migration needed).
- Flight/hotel candidate items (created at trip creation) are also `day_id = null` but are NOT marked `source_kind = "concierge_idea"`, so they remain invisible to the Trip Ideas panel.
- No drag-and-drop from Trip Ideas panel (v1 uses day selector dropdown, consistent with scope).

### Next likely task
- Monitor `source_kind` usage in production to confirm no flight/hotel candidates bleed into the Trip Ideas panel
- Consider adding a "notes" editable field for saved ideas
- Test on mobile: the two-button layout in ConciergeCard should be verified at small viewport widths

### Supabase SQL: No (no migration — existing schema supports `day_id = null` and `details` JSONB)
### Backend touched: Yes (`itinerary.py` service, `trips.py` route)

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
