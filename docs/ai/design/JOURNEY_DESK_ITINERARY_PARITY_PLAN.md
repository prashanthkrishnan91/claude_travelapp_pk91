# Journey Desk — Itinerary Parity Plan

**Last updated:** 2026-05-25 · tracking PR #483.
**Status:** Plan / audit only. No behavior change is authorized by this doc.
**Purpose:** Prove parity *before* any legacy-tab cleanup. The legacy **Itinerary** and legacy **Ideas** tabs MUST NOT be removed, hidden, renamed, or demoted until every capability below has a proven Journey Desk destination.
**Source-inspected:** `frontend/src/app/trips/[id]/page.tsx`, `TripBuilder.tsx`, `ItineraryDayColumn.tsx`, `ExpandedDayPanel.tsx`, `Dayboard.tsx`, `TripBrief.tsx`, `AddToDayDrawer.tsx`, `TripIdeasPanel.tsx`, `IdeasTray.tsx` (+ `lib/dayParts.ts`, `lib/travelHints.ts`, `lib/api.ts`).
**Aligns with:** `docs/ai/design/JOURNEY_DESK_V1_BLUEPRINT.md`, `docs/ai/design/PRIVATE_TRAVEL_ATELIER_DIRECTION.md`, `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md`.

---

## 1. Current Journey Desk IA ownership (locked)

| Surface | File | Role | Editing? | Entry points |
|---|---|---|---|---|
| **Brief** | `TripBrief.tsx` | Read-only at-a-glance: where · fixed anchors (first flight/stay) · count still to decide. | None. | "Review ideas" / "Choose" → `setActiveMobileWorkspace("ideas")` (Ideas tab). |
| **Itinerary** (legacy) | `ItineraryDayColumn.tsx` via `TripBuilder` `itinerary` workspace | Structured day editing — the only surface with full day-item editing today. | **Full**: remove, move-to-ideas, drag/reorder, Suggest Timing (day-part write), Plan My Day, travel hints, compare, add-note, Add Day. | Mobile "Itinerary" tab; desktop right column. |
| **Build** (hidden) | `TripBuilder.tsx` candidate panels | Internal provider search + add-to-itinerary (flights/hotels/dining/attractions). | Adds candidates to a target day. | **Omitted from mobile nav** (`WORKSPACE_TABS`); reached via Add-to-Day handoff (`focusDayId`/`focusVertical`) + desktop left column. |
| **Ideas tab** | `TripIdeasPanel.tsx` | **Canonical** idea management: status (must_do/maybe/skip), note editing, search/filter/sort, per-vertical grouping, assign-to-day, remove. | Idea-level editing. | Mobile "Ideas" tab; desktop within `TripBuilder` right area. |
| **IdeasTray** | `IdeasTray.tsx` | **Quick placement only** overlay: Add to Day / Keep as Maybe / note *preview* / Map / Google Flights / Manage in Ideas / Remove. No status chips, no note editor. | Placement + remove only. | Brief & ExpandedDay → `setIdeasTrayOpen(true)`. |
| **ExpandedDayPanel** | `ExpandedDayPanel.tsx` | Read-only selected-day workspace: items grouped Morning/Afternoon/Evening/Logistics/Anytime (via `lib/dayParts.groupJourneyDeskDay`), calm decision strip. | **None** (delegates to legacy via "Edit in Itinerary"). | Rendered inline under the selected Dayboard card. Has Add-to-Day + Add-from-Ideas + Edit-in-Itinerary. |
| **Dayboard** | `Dayboard.tsx` | Read-only collapsed day cards (10-sec read) + per-day Add-to-Day "+" + "Trip map" link. | None. | Renders `ExpandedDayPanel` inline for `selectedDayId`. |

**Locked IA (do not drift):** Brief = overview/read-only · Itinerary = structured day editing · Ideas tab = idea management · IdeasTray = quick placement · Build = hidden/internal add+search.

---

## 2. Itinerary parity matrix

Owner = where it lives today. "JD?" = does a Journey Desk surface (Brief/Dayboard/ExpandedDay/IdeasTray) already cover it. Mobile/Desktop = does the legacy capability work there today. Risk = severity if legacy tab were removed before parity.

| Capability | Owner (file) | JD covers? | Mobile | Desktop | Gap | Risk | Recommended JD destination |
|---|---|---|---|---|---|---|---|
| **Delete / remove item** | `ItineraryDayColumn`→`ItineraryItemCard.onRemove`→`TripBuilder.handleRemoveItem`→`deleteItem` | No (ExpandedDay read-only) | Yes | Yes | No per-item remove in ExpandedDay. (IdeasTray removes *unplaced* ideas; MapFoldOut removes placed.) | **High** | ExpandedDay per-item Remove (two-step confirm), reusing page `deleteItem`. |
| **Move item back to Ideas** | `ItineraryDayColumn`→`handleMoveItemToIdeas`→`moveIdeaToTripIdeas` | No (ExpandedDay) — but MapFoldOut has "Back to Ideas" via safer `unplaceItemToIdeas` | Yes | Yes | ExpandedDay has none; **legacy `moveIdeaToTripIdeas` has the documented orphan gap** (items without curated `source_kind` vanish). | **High** | ExpandedDay "Back to Ideas" reusing page `handleItemUnplace`/`unplaceItemToIdeas` (NOT the legacy path). |
| **Reorder / drag items** | `TripBuilder.handleDragEnd` + `ItineraryDayColumn` `useDroppable`/`SortableContext` (dnd-kit); writes `position` | No | Yes (long-press) | Yes | No drag/reorder anywhere in JD; position-write path only in `handleDragEnd`. | **High** | Deferred — heaviest slice; needs dnd + position persistence. Keep legacy. |
| **Day-part override** | `getItemDayPart` reads `details.dayPart`; written via `updateItemTimeline` (Suggest Timing apply); classifier duplicated in `lib/dayParts.ts` | Read-only grouping only | Yes | Yes | No manual day-part override UI in JD (ExpandedDay only *reads* the classifier). | **Medium** | ExpandedDay item-level day-part control, reusing `updateItemTimeline`. |
| **Add-to-Day** | Shared: Dayboard "+", ExpandedDay "Add to this day", `ItineraryDayColumn` mobile tray → `AddToDayDrawer` → Build vertical w/ `focusDayId` | **Yes (full)** | Yes | Yes | None. | **None** | Already JD-owned. |
| **AI Plan My Day** | `ItineraryDayColumn` header → `onPlanDay`→`handlePlanDay`→`fetchDayPlan`→`DayPlanModal` | No | Yes (mobile action tray) | Yes (`lg:flex`) | Only in legacy day header. | **High** | ExpandedDay header entry → reuse `fetchDayPlan` + `DayPlanModal`. |
| **Suggest Timing** | `ItineraryDayColumn.handleSuggestTimeline`→`suggestDayTimeline` + `updateItemTimeline` + `SuggestionsReviewPanel` | No | Yes (mobile action tray) | Yes (`lg:flex`) | Only in legacy. | **High** | ExpandedDay timing flow; reuse same helpers + review panel. |
| **Travel hints** | `ItineraryDayColumn` → `lib/travelHints` (`computeAdjacentHints`/`summarizeHints`) + inline connectors + `DayTravelHintBar` | No | Yes | Yes | No travel hints in ExpandedDay. | **Medium** | ExpandedDay read-only honest hints (omit when no location). No new compute. |
| **Day-level note / context** | `ItineraryDayColumn` "+"→`TripBuilder.onAddItem`/`handleAddToDay`→AddNote modal→`createItem` (itemType `note`) | Item notes read-only in ExpandedDay/Tray; no add-note | Yes | Yes | No add-note in JD. | **Low-Med** | Defer; later ExpandedDay add-note reusing `createItem`. |
| **Map / pin interactions** | `MapFoldOut` (Trip/Day/Ideas lens, real pins, Move/Back-to-Ideas/Remove); wired at page level | **Yes** | Yes | Yes | None — JD-native, not legacy. | **None** | Already JD-owned (Dayboard "Trip map"). |
| **Compare items** | `ItineraryDayColumn`/`TripBuilder` candidate cards → `onToggleCompare`/`compareSet`→`CompareModal` | No | Yes | Yes | No compare in JD day view. | **Medium** | Keep legacy/Build; compare is a power feature — defer. |

### Hidden legacy behaviors that break if the Itinerary tab is removed prematurely

- **Add Day** for date-less trips: `handleAddDay`→`createDay` lives **only** in the Itinerary chrome (`canManuallyAddExpectedDay`). Trips without start/end dates would lose the only way to add days. **High.**
- **Target-day "Add to" selector** drives the Build left-panel "+" adds (`selectedDayId`). Build-internal but coupled. **Medium.**
- **Day reorder** persistence (`handleDragEnd`) is the only writer of day/item `position`. **High.**
- **Optimistic renumbering** on remove/move (position re-index) lives in the legacy handlers. **Medium.**
- **Write-path divergence:** legacy uses `moveIdeaToTripIdeas` (latent orphan gap); MapFoldOut uses the corrected `unplaceItemToIdeas`. Any JD "Back to Ideas" must use the corrected path. **High.**
- **`note` itemType creation** (`createItem`) only reachable from the legacy "+". **Low-Med.**

---

## 3. Recommended next PR sequence

Ordered cheapest/safest first. Each is a **future** PR (not this one). Principle: surface read-only/honest reads and writes that *reuse durable handlers already wired at page level*, before touching dnd/position or AI-timing apply. **Legacy removal is the LAST step and is not authorized until Slices 1–5 prove parity.**

**Slice 1 — ExpandedDay per-item Remove + Back-to-Ideas. ✅ MERGED (#485).**
- Outcome: ExpandedDay items get a quiet overflow with two-step-confirm **Remove from trip** and non-destructive **Back to Ideas**, matching MapFoldOut's tone.
- Files: `ExpandedDayPanel.tsx`, `page.tsx` (pass existing `deleteItem` + `handleItemUnplace`/`unplaceItemToIdeas` handlers), `tests/journey-desk-expanded-day.test.mjs`.
- Risks: destructive delete must be confirm-gated; MUST reuse `unplaceItemToIdeas` (not legacy `moveIdeaToTripIdeas`) to avoid the orphan gap; honest copy ("Back to Ideas" ≠ "Remove").
- Validation: Tier 1 targeted — expanded-day suite asserts confirm gating, correct unplace path, no `deleteItem` without confirm. Source-scan no-fabrication.
- Model: **Sonnet** (reuses existing writes; mechanical wiring).

**Slice 2 — ExpandedDay read-only travel hints.**
- Outcome: ExpandedDay renders honest adjacency hints (omit when no location), reusing `lib/travelHints`. No writes.
- Files: `ExpandedDayPanel.tsx`, expanded-day test.
- Risks: low; must omit silently when data absent (no fabricated distances/times).
- Validation: Tier 1 targeted; assert hints omitted when no coords.
- Model: **Sonnet**.

**Slice 3 — ExpandedDay AI Plan My Day + Suggest Timing.**
- Outcome: ExpandedDay header gains Plan My Day (`fetchDayPlan` + `DayPlanModal`) and Suggest Timing (`suggestDayTimeline` + `updateItemTimeline` + review panel).
- Files: `ExpandedDayPanel.tsx`, `page.tsx`; consider extracting the shared timing/apply logic so it is **not duplicated** between `ItineraryDayColumn` and ExpandedDay.
- Risks: medium-high — shared classifier already duplicated (`lib/dayParts` vs `ItineraryDayColumn`); avoid a third copy; reuse `updateItemTimeline` exactly.
- Validation: Tier 1–2; assert reuse of existing helpers, optimistic update parity.
- Model: **Opus** (shared-logic extraction + apply flow).

**Slice 4 — ExpandedDay day-part override + within-day reorder.**
- Outcome: manual day-part change (`updateItemTimeline`) and within-day item reorder with `position` persistence.
- Files: `ExpandedDayPanel.tsx`, `page.tsx`, possibly `lib/dayParts.ts`; dnd-kit wiring.
- Risks: **High** — drag + `position` writes; this is the parity-blocker for removing legacy. Consider splitting (override first, then reorder).
- Validation: Tier 2; reorder persistence + day-part write asserted.
- Model: **Opus** (dnd + persistence).

**Slice 5 — Add Day (date-less trips) + day reorder reachable from JD.**
- Outcome: JD covers `createDay` (date-less) and day-level reorder so the Itinerary chrome is no longer the sole home.
- Files: `Dayboard.tsx`/`page.tsx`, tests.
- Risks: medium; date-locked vs manual logic must mirror `canManuallyAddExpectedDay`.
- Validation: Tier 1–2.
- Model: **Opus** (or Sonnet if reorder deferred).

**Slice 6 (gated, NOT now) — Retire/hide the legacy Itinerary tab.**
- Precondition: Slices 1–5 merged and parity verified against this matrix (incl. hidden behaviors).
- Outcome: hide/remove the legacy Itinerary workspace once every High/Medium row has a proven JD destination. Ideas tab decision is separate and also gated on IdeasTray-vs-Ideas-tab parity (currently **Ideas tab stays canonical**).
- Model: **Codex** for the mechanical removal + test updates, after a human/Opus parity sign-off.

---

## 4. Safe now vs deferred

- **Safe now (no parity risk):** Add-to-Day, Map/pin interactions, Brief read-only, Ideas tab management, IdeasTray quick placement. These are already JD-owned or unaffected.
- **Deferred until parity proven (keep legacy):** remove, back-to-ideas, reorder/drag, day-part override, Plan My Day, Suggest Timing, travel hints, compare, add-note, Add Day, day reorder.
- **Hard stop:** do NOT remove/hide/rename/demote the legacy Itinerary or Ideas tabs in any slice except Slice 6, and only after sign-off.

**Out of scope for every slice here:** backend, SQL, providers, MapTiler, Google Places, routing, search APIs; fake route optimization, fake pins, fake geocoding, unsupported timing, placeholder AI; duplicating functionality into Brief; overloading IdeasTray.
