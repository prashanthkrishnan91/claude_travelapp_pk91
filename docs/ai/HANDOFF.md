# AI Handoff — Travel Concierge

## Last change (2026-05-01) — Concierge metadata preservation for Trip Ideas + Day add

### Summary
Persisted optional Google verification metadata when saving AI Concierge results to Trip Ideas and when adding them directly to an itinerary day. Both flows now preserve `details.lat`, `details.lng`, `details.provider_place_id`, `details.formatted_address`, and `details.google_maps_uri` when present, while skipping null/undefined/empty values.

### Files touched
- `frontend/src/lib/api.ts` — added `normalizeGoogleVerificationDetails(item)` helper; wired it into both `addStructuredConciergeItemToTrip` and `saveToTripIdeas` detail payloads so Google verification metadata is merged without overwriting existing fields with empty values
- `frontend/tests/trip-ideas.test.mjs` — added focused contract tests confirming both save/add flows include the metadata helper and that the helper safely no-ops when `googleVerification` is missing

### Behavior change
- AI Concierge → Trip Ideas now persists Google metadata into `details` when available
- AI Concierge → Day now persists Google metadata into `details` when available
- Existing fields (`location`, `address`, `dayPart`, `timeLabel`, notes/status/priority, etc.) remain preserved because this change only appends non-empty metadata keys
- Trip Ideas ↔ Day movement remains day_id-only and continues to preserve `details` as-is

### Known issues / v1 limits
- Metadata persistence is source-dependent: if a card has no `googleVerification`, no new metadata fields are added (expected behavior)

### Next likely task
- Use persisted `details.lat/lng` + place metadata for Travel Time Hints v1 calculations (no UI yet)

### Supabase SQL: No
### Backend touched: No

## Last change (2026-05-01) — Smart Day Timeline AI Planning v1

### Summary
Added a "Suggest Timing" button to each itinerary day column. When clicked for a day that has items, the feature gathers those items and calls a new `POST /ai/timeline/suggest` backend endpoint to suggest `details.dayPart` and optional `details.timeLabel` for each item. The user reviews the suggestions in a compact inline panel and clicks "Apply All Suggestions" to persist them via the existing `updateItemTimeline` / `PATCH /itinerary/items/{id}` path. A deterministic client-side fallback runs when the backend is unreachable or no AI key is configured.

### Files touched
- `frontend/src/lib/dayPlanner.ts` — NEW: exports `DayPlannerSuggestion` type and `suggestTimelineFallback(items)` deterministic rule-based planner; classification rules: breakfast/brunch/cafe → morning, dinner/cocktail bar → evening, lunch → afternoon, generic meal → afternoon, generic activity → morning, flight/hotel → unscheduled; preserves existing `details.dayPart` when already set; `timeLabel` is always `undefined` (not blank string) when not strongly implied
- `frontend/src/lib/api.ts` — added `TimelineSuggestion` interface and `suggestDayTimeline(items)` export; calls `POST /ai/timeline/suggest`; on any error falls back to `suggestTimelineFallback` imported lazily from `dayPlanner.ts`
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — added `suggestingTimeline`, `timelineSuggestions`, `applyingTimeline` state; `handleSuggestTimeline()` handler calls `suggestDayTimeline`, stores suggestions; `handleApplyTimeline()` calls `updateItemTimeline` for each suggestion in parallel, updates `itemOverrides` for optimistic section movement, clears suggestion state; new `SuggestionsReviewPanel` sub-component: shows item → dayPart + timeLabel rows, "Apply All Suggestions" button, and "Dismiss" X button; "Suggest Timing" button added to day header (visible when day has ≥1 item), coloured slate (distinct from amber "Plan My Day"); imports `suggestDayTimeline`, `updateItemTimeline`, `TimelineSuggestion` from `@/lib/api`; imports `Check`, `X` icons from lucide-react
- `backend/app/routes/ai.py` — added Pydantic models `_TimelineItem`, `_TimelineSuggestion`, `_TimelineSuggestRequest`, `_TimelineSuggestResponse`; added `_classify_deterministic()` with same keyword rules as the TS fallback; added `_build_claude_prompt()` and `_parse_claude_suggestions()` for the AI path; added `POST /ai/timeline/suggest` route: uses Claude (`claude-haiku-4-5-20251001`) if `ANTHROPIC_API_KEY` is set, otherwise runs deterministic fallback; safe to call in local/dev/test with no API key; returns `provider: "claude"|"deterministic"` in response
- `frontend/tests/smart-timeline.test.mjs` — NEW: 29 renderer/contract tests covering: `suggestTimelineFallback` export and shape, breakfast→morning, cafe→morning, dinner→evening, lunch→afternoon, flight/hotel→unscheduled, activity→morning, meal→afternoon, explicit dayPart preservation, timeLabel read-through, timeLabel defaults to undefined, day_id never touched, `suggestDayTimeline` export and fallback, backend endpoint path, `TimelineSuggestion` fields, `SuggestionsReviewPanel` controls, no day_id mutation in apply handler

### Behavior change
- Each expanded itinerary day column (when the day has ≥1 item) now shows a "Suggest Timing" button (Clock icon, slate style) in the day header
- Clicking "Suggest Timing" fires `POST /ai/timeline/suggest` with the day's items; a loading spinner appears on the button while the request is in flight
- On success, a `SuggestionsReviewPanel` appears above the timeline sections showing each item with its suggested dayPart and timeLabel
- "Apply All Suggestions" persists each suggestion via the existing `PATCH /itinerary/items/{id}` endpoint (same path as manual timeline controls); items move to the correct section optimistically
- "Dismiss" (X icon) clears the suggestions without applying them
- No items are duplicated, no day_id is changed, no items are moved to Trip Ideas
- Fallback path (no API key, network error) runs entirely in the browser with deterministic rules — feature remains usable in local/dev/test

### AI planner rules (both backend and fallback)
```
breakfast/brunch → morning (timeLabel: "Breakfast")
coffee/cafe/bakery → morning (timeLabel: "Morning coffee")
dinner/supper → evening (timeLabel: "Dinner")
cocktail/bar → evening (timeLabel: "Evening drinks")
nightlife → evening (timeLabel: "Night out")
lunch/midday/noon → afternoon (timeLabel: "Lunch")
generic meal → afternoon (timeLabel: "Lunch")
generic activity → morning (no timeLabel)
flight / hotel → unscheduled (no timeLabel)
already has details.dayPart → preserve (no change)
unsure → unscheduled
```

### Known issues / v1 limits
- Suggestion panel is only shown after user clicks the button; it does not auto-apply. This is by design (requires confirmation).
- If the backend call fails AND the dynamic import of `dayPlanner.ts` also fails (unlikely), the `suggestDayTimeline` promise would reject — callers in `ItineraryDayColumn` guard with `try/finally` so the loading state is cleared.
- Suggestion panel does not persist between page navigations (dismissed on unmount). Applied suggestions do persist via Supabase.
- `SuggestionsReviewPanel` does not support per-item override — it's apply-all or dismiss. Per-item editing is a v2 scope.

### Next likely task
- Wire `onUpdateTimeline` callback up through TripBuilder → page if full parent refresh is desired after apply
- Add per-item suggestion editing (v2 scope)
- Consider auto-expanding day when "Suggest Timing" is triggered from the collapsed view

### Supabase SQL: No
### Backend touched: Yes (`backend/app/routes/ai.py` — new endpoint, no DB writes)

---

## Previous change (2026-05-01) — Manual Timeline Controls v1

### Summary
Added simple manual controls so a user can set or adjust an itinerary day item's timeline placement (Morning / Afternoon / Evening / Unscheduled) and optional freeform timeLabel. Items immediately move to the correct section after saving without a full refresh. No AI scheduling, routing, or map optimization added.

### Files touched
- `frontend/src/lib/api.ts` — added `updateItemTimeline(itemId, currentDetails, { dayPart, timeLabel })`: merges `dayPart` and optional `timeLabel` into existing `details` JSONB and PATCHes via existing `PATCH /itinerary/items/{id}` endpoint; clears `timeLabel` from details when empty
- `frontend/src/components/trips/ItineraryItemCard.tsx` — added `DAY_PARTS` constant (4 options); `onTimelineUpdated` prop; `timelineOpen` / `selectedPart` / `timeLabelInput` / `saving` local state; `handleOpenTimeline` (pre-fills from `item.details`); `handleSaveTimeline` (calls `updateItemTimeline`, fires callback, closes panel); a Clock icon trigger button (hover-only unless already scheduled); inline timeline editor panel (day-part pills + timeLabel input + Save); displays `details.timeLabel` as a small badge when set and no `startTime` exists; imports `updateItemTimeline` from `@/lib/api`
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — updated `getItemDayPart` to explicitly handle `"unscheduled"` value (bypasses `startTime` classification); added `onUpdateTimeline` prop to `ItineraryDayColumnProps`, `TimelineSectionsProps`, and `renderItemsWithConnectors`; added `itemOverrides` local state in `ItineraryDayColumn`; `handleTimelineUpdated` stores updated item in overrides and bubbles to parent; `visibleItems` useMemo applies overrides so the item moves to the correct section immediately; threaded `onUpdateTimeline={handleTimelineUpdated}` into `TimelineSections`
- `frontend/tests/itinerary-timeline.test.mjs` — added 12 new renderer/contract tests (tests 14–25) covering: `updateItemTimeline` export, `dayPart`/`timeLabel` persistence, `onTimelineUpdated` prop, timeline trigger button, 4 day-part options in card, `timeLabelInput` state, `handleSaveTimeline`, `onUpdateTimeline` threading, `itemOverrides` state, details spread for field preservation, explicit unscheduled override, single timeline button

### Behavior change
- Each itinerary day item now shows a Clock icon button (hover-visible, always-visible when already scheduled)
- Clicking the Clock icon opens an inline panel with 4 day-part pills (Morning/Afternoon/Evening/Unscheduled) and an optional timeLabel input
- Saving persists `details.dayPart` and `details.timeLabel` via the existing PATCH endpoint
- Item immediately moves to the correct timeline section without page refresh (optimistic via `itemOverrides`)
- Explicitly setting "Unscheduled" overrides any `startTime`-derived section (new `getItemDayPart` branch)
- If `details.timeLabel` is set and no `startTime` exists, the timeLabel is shown as a small clock badge on the card
- All existing behaviors preserved: drag/drop, Trip Ideas ↔ Day, notes/status/priority, concierge item identity

### Timeline persistence model
```
details.dayPart   = "morning" | "afternoon" | "evening" | "unscheduled"
details.timeLabel = string  (optional, freeform, e.g. "9:00 AM", "After lunch")
```
Frontend merges patch into existing details (preserving all other detail fields). No migration needed.

### Known issues
- `itemOverrides` in `ItineraryDayColumn` resets on full itinerary reload (e.g., after move-to-ideas or parent refresh). This is acceptable for v1 — the server-persisted value will be correct after reload.
- Timeline editor is hover-triggered on desktop; on mobile it becomes accessible when the item already has a schedule (clock icon is always visible at reduced opacity in that case).

### Next likely task
- Wire `onUpdateTimeline` callback up through TripBuilder → page if full parent refresh is desired after timeline changes
- Add `details.dayPart` hint to the AI Concierge → save-to-ideas flow so AI-recommended items can optionally carry a section hint

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-05-01) — Smart Day Timeline v1 Foundation

### Summary
Converted each itinerary day's expanded view from a plain item list into a timeline-grouped layout. Items are now bucketed into **Morning / Afternoon / Evening / Unscheduled** sections based on available time metadata, with no AI scheduling, routing, or time generation added.

### Files touched
- `frontend/src/components/trips/ItineraryDayColumn.tsx` — added `DayPart` type, `DAY_PART_META` config, `getItemDayPart()` helper (reads `details.dayPart`, `details.timeLabel`, then `startTime` hour), `groupByDayPart()`, `renderItemsWithConnectors()` extracted function, and `TimelineSections` sub-component that renders section headers + item cards per bucket; existing travel-time connectors preserved within sections; drag/drop (`SortableContext`, `useDroppable`) unchanged
- `frontend/tests/itinerary-timeline.test.mjs` — NEW: 13 renderer contract tests covering classification signals, section labels, Unscheduled fallback, drag/drop preservation, move-to-ideas guard, and travel connectors

### Behavior change
- Day expanded view: items grouped into Morning / Afternoon / Evening / Unscheduled sections
- If **all** items are unscheduled → single "Unscheduled · N items" header shown (clean fallback)
- If **any** item is timed → section headers (Morning amber, Afternoon sky, Evening violet, Unscheduled slate) appear for non-empty buckets
- Travel-time connectors between adjacent items within the same section are preserved
- All existing behaviors preserved: Trip Ideas → Day, Day → Trip Ideas, drag/drop between days, notes/status/priority, move-to-ideas for concierge items only
- No changes to data model, no migration, no Supabase SQL

### Timeline metadata resolution order
1. `item.details.dayPart` — explicit override ("morning" | "afternoon" | "evening")
2. `item.details.timeLabel` — keyword match (e.g., "Morning", "afternoon stroll", "evening dinner")
3. `item.startTime` — ISO datetime or HH:MM; hour → section boundary
4. Default → `"unscheduled"`

### Section hour boundaries
- Morning: 5:00–11:59
- Afternoon: 12:00–16:59
- Evening: 17:00+

### Known issues
- The collapsed-view preview (first item title + "+N more") does not show section context — acceptable for v1
- `PREVIEW_ITEM_LIMIT = 4` still limits visible items before "Show all N items" is clicked; section grouping applies only to visible items

### Next likely task
- Add optional time input to the "Add item" form so users can assign times and see items move into the correct section
- Add `details.dayPart` to the concierge-to-ideas flow so AI-recommended items can optionally carry a section hint

### Supabase SQL: No
### Backend touched: No

---

## Previous change (2026-04-30) — Trip Ideas Triage v1

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
