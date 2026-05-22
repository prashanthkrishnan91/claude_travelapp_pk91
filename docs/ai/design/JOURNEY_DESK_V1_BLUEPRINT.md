# Journey Desk v1 — Build Blueprint

**Status:** Blueprint / pre-implementation. No code is authorized by this doc.
**Stage:** 3.5 — design adoption across the Atelier rooms (next visible-adoption surface: trip detail / Journey Desk).
**Source of truth:** the approved prototype (`index.html` + the three reference screenshots: mobile A–D, desktop E–F, build-notes card).
**Aligns with:** `CLAUDE.md`, `docs/ai/HANDOFF.md`, `docs/ai/design/PRIVATE_TRAVEL_ATELIER_DIRECTION.md` (The Folio), `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md`, `docs/product/DESIGN_BIBLE_ADDENDUM_V1_1.md`.

This blueprint is the durable reference a future slice prompt points to when it says "build Journey Desk v1." It does not replace the Folio direction or the implementation contract — it specializes them for the trip-detail surface.

---

## 1. Product role

Journey Desk is the **final planning workspace** of the Travel Concierge surface system. It is where a trip stops being a pile of saved ideas and becomes a *day-by-day plan you can read in one glance*.

It is the fourth Atelier room, downstream of the discovery rooms:

- **Concierge Salon (v2)** — conversational discovery (dark).
- **Explore Observatory (v1)** — vertical discovery/search (dark).
- **Saved · Private Folio (v1)** — kept collection + notes (light paper).
- **Journey Desk (this surface)** — the planning desk where Saved / Trip Ideas become a real itinerary (light paper).

What it **must not** be:

- Not a utility timeline or itinerary database.
- Not a generic project/SaaS dashboard (no KPI tiles, progress rings, completion %, streaks).
- Not a fifth discovery surface — it does not search providers; it *places* what discovery already produced.

The mental model is a **private travel desk, not a database**. Three questions answered at a glance: *where am I going · what is already fixed · what still needs choosing*. The Ideas Tray exists to **place** things, not to list them.

---

## 2. V1 scope

V1 ships the calm planning desk end to end on mobile, then adapts to desktop. Exactly:

1. **Trip cover / Brief** — dark cinematic cover hero (the one signature panel) + a calm "Brief": one fixed line, one pending line, one summary count ("N still to decide"), and a "placed" progress read ("11 of 16 placed").
2. **Mobile-first collapsed Dayboard** — every day as a calm collapsed card (numeral, date, where-line, weather-if-real, a placed count, a small still-deciding dot). Tapping expands.
3. **Expanded day view** — day brief + decision strip + items grouped into **Morning / Afternoon / Evening / Logistics** (presentation grouping derived from item times, *not* a new data model — see §8).
4. **Calm decision strip** — one brass-dot paper strip per day summarizing what is unresolved, with a quiet link into the Ideas Tray filtered to that day. Never a red banner.
5. **Ideas Tray** — mobile bottom sheet + desktop right rail. Placement-first cards (one bold primary action), contextual secondary actions in a quiet text-link row, filter chips by kind.
6. **Notes hierarchy** — three typed layers (private marginalia / concierge reason / provider facts), one note line by default (§9).
7. **Contextual compare / map / details actions** — surfaced only where the data already exists (hotel compare, flight compare/booking, place map/details). No new providers (§5, §10).
8. **Desktop adaptation** — same three-zone structure (left context · center Dayboard · right Ideas Tray rail). Adapts from mobile; does not redefine the product.

---

## 3. Explicit v1 out-of-scope

These are deliberately deferred. A v1 PR that builds any of them is over-scoped and should stop.

- **Map Fold-Out** and all map *lenses* (trip lens / day lens / idea lens). The map drawer is v2 (§4). V1 ships only the per-item map link that already exists.
- **AI organize / polish day** ("Ask concierge to draft Day 4–6 in the same key" is a *visual affordance only* in v1, not wired).
- **Route optimization** / travel-time computation / sequencing intelligence.
- **Drag-and-drop** reordering or drag-to-place. Placement in v1 is via the Ideas Tray primary action (a real write), not dragging.
- **Collaboration / voting / multi-traveller editing.**
- **New providers or new API calls.** No new search, no new backend endpoint required by v1 (placement uses the existing assign path — see §10).
- **Fake weather / fabricated ambience.** Weather, distance, hours, ratings render only when real data exists; otherwise omitted.
- **Broad design-system rewrite.** No token renames, no Folio primitive refactor, no cross-surface cleanup. Compose existing `Folio*` primitives and existing `--ds-*` tokens.

---

## 4. V2 seam — Map Fold-Out

The Map Fold-Out is *wanted*, but intentionally v2. V1 must leave a clean seam and must not implement the drawer.

- **Where the map action appears in v1:** a single quiet **"Day map" / "Trip map"** affordance (text-link weight) in the day header and/or trip header. In v1 it routes to the *existing* per-trip map view (`TripMapView`) or opens the existing per-item Google Maps link — it does **not** open a new fold-out drawer.
- **Avoid hard-coding against future lenses:** the map entry point should accept a *scope* concept (`trip` | `day` | `idea`) as a parameter shape only, defaulting to `trip` in v1. Do not bake "trip-only" assumptions into the call site, and do not build per-lens UI. The v2 drawer (the prototype's `Trip · Day · Idea` segmented control + numbered pins) slots in behind this same entry point later.
- **What the v2 drawer will eventually need (record only, do not build):** geocoded coordinates per placed item and per idea; a pin/order model (numbered stops); a "where the trip lives" summary count (pins · stays · places · dining · ideas); a paper/dark map theme per Design Implementation Contract §10. V1 must not fabricate coordinates or pin data to fill this.
- **Hard rule:** v1 must not implement the map drawer, the lens switcher, or numbered-pin rendering. Shipping a non-functional drawer shell is also out of scope.

---

## 5. Mobile IA

Mobile is the primary target. The prototype frames A–D are the reference.

**First-viewport goals (the 10-second read):** on a ~390–402px phone the user should see, without scrolling, the trip cover + the Brief + the start of the collapsed Dayboard, plus the Ideas Tray pill. The three questions (*where · fixed · to decide*) are answered above the fold.

**Trip cover / Brief behavior:**
- The dark cinematic cover is the *one* signature panel on the screen (folio serial, destination as serif display title, italic lede, a quiet meta row: dates · party · status). It is hero only — never the page chrome.
- The **Brief** sits directly under the cover on warm paper: a placed progress read ("11 of 16 placed"), one **fixed** line (e.g. "Flight booked · UA 837 · SFO→KIX"), one **pending** line carrying a single contextual action ("Hotel pending · Compare hotels"), and one **summary** line ("3 still to decide · Review"). No more than these; calm white space over density.

**Dayboard collapsed card behavior:**
- One card per day: large day numeral, weekday + date, italic where-line, weather chip *only if real*, a placed-count, and a small brass still-deciding dot when the day has unresolved decisions.
- Default state is collapsed. Tap expands in place (or routes to the expanded day) — no accordion that hides the rest of the board jarringly.

**Expanded day behavior:**
- Day brief (numeral, date, italic where-line, weather-if-real) → **decision strip** (§11) → items grouped under Morning / Afternoon / Evening / Logistics, each item a paper card with time, title, one note line, and a contextual action row (§10).
- Item separators are dashed hairlines, not card borders (Folio §13). Empty time groups are silent — no ghost "add" rows.

**Ideas Tray bottom-sheet behavior:**
- A paper sheet rising from the bottom with a grab handle and a brass hairline top edge. Header: "Place one in." + an honest count ("6 candidates") + an italic provenance line ("From your Private Folio. Each card suggests where it fits.").
- Filter chips by kind (All · Hotels · Flights · Dining · Places) with real counts. Dismiss by handle/backdrop/Esc.
- The tray opens from an off-centre pill (out of the bottom-tab thumb path), not from the centre nav.

**One-tap placement behavior:**
- Each card's primary action states the exact placement ("Add to Day 2 · Dinner", "Add as Hotel anchor", "Keep as Maybe"). One tap performs a real write via the existing assign path (§10), then acknowledges calmly (card recedes / count updates) — no disruptive modal, no toast spam.
- If a card has no confidently suggested slot, the primary action is the safe honest one ("Keep as Maybe" / "Add to Day…") rather than a fabricated slot (§10).

**Bottom-nav considerations:**
- The existing 4-item paper bottom nav (Home · Explore · Trips · Saved / Concierge) is preserved. The Ideas Tray pill floats above it, off-centre, never under the primary thumb arc. No new nav structure, no route changes.

**Wife-mobile success criteria:**
- In one glance she knows where the trip is, what is locked, and what still needs a decision.
- Placing an idea into a day is one calm tap, and the plan visibly updates.
- The screen reads like a private travel magazine spread, never a database or a SaaS board. Nothing is red, nothing is urgent, nothing shouts.

---

## 6. Desktop IA

Desktop adapts the mobile product into a three-zone editorial spread (prototype frames E–F). It must **adapt from mobile, not redefine the product**.

- **Left context / nav zone:** quiet rail — wordmark, the outside-trip surfaces (Salon / Observatory / Private Folio / Journey Desk), and a "This trip" mini index (trip name, dates, day list). Context and navigation only; no controls dump.
- **Center Dayboard workspace:** the cover/brief, the open-decisions summary, a compact day strip (selectable days), then the expanded day with its decision strip and Morning/Afternoon/Evening groups. This is the writing surface.
- **Right Ideas Tray rail:** the placement-first tray persistently docked (same cards as mobile, same primary action). Filter chips lose their icons on the desktop rail (calmer), per the prototype.
- **Map is not permanent:** the map is a fold-out invoked from the day/trip header (v2), never a permanent fourth column. V1 desktop shows no map panel — the "Day map / Trip map" link routes to the existing map view.
- **Adapt, don't redefine:** same components, same data, same primary action as mobile. No desktop-only feature, no four-column "zoo," no dense tables, no tiny desktop-grade controls leaking onto mobile.

---

## 7. Component hierarchy

Proposed names and responsibilities. These are implementation-friendly intents, not verified current filenames — verify against the codebase before coding, and reuse existing `Folio*` primitives and existing trip components (`TripIdeasPanel`, `ItineraryDayColumn`, `ItineraryItemCard`, `TripMapView`, `CompareModal`) rather than re-implementing them.

- **JourneyDeskPage** — route-level container for trip detail. Owns trip + days + ideas data load and the mobile/desktop layout switch. No provider/search logic.
- **JourneyDeskHeader / TripBrief** — the dark cover hero + the calm Brief (fixed / pending / summary lines, placed progress). Pending line carries one contextual action.
- **Dayboard** — the collapsed list of days; owns expand/collapse and day selection.
- **DayCard** — a single collapsed day (numeral, date, where-line, weather-if-real, placed count, still-deciding dot).
- **ExpandedDayPanel** — expanded day: day brief + DayDecisionStrip + period groups (Morning / Afternoon / Evening / Logistics). Reuses `ItineraryDayColumn` / `ItineraryItemCard` where possible.
- **DayDecisionStrip** — the brass-dot "still deciding" strip with a deep-link into the Ideas Tray filtered to the day (§11).
- **IdeasTray** — mobile bottom sheet + desktop right rail shell; owns filter chips and the candidate list. Built on / replacing the placement surface of `TripIdeasPanel`.
- **IdeasTrayCard** — one candidate; placement-first primary action + ContextualActionRow + one NoteMarginalia line + provider meta.
- **NoteMarginalia** — renders the typed note hierarchy (private / concierge / provider), clamped to one line by default (§9).
- **ContextualActionRow** — the quiet text-link row of secondary actions (Map / Compare / Details / Keep-as-Maybe), surfaced contextually by item kind (§10).
- **MapEntryPoint** (seam only) — the "Day map / Trip map" affordance that routes to the existing map view with a `scope` param; not the v2 drawer (§4).

---

## 8. Data mapping

Map the prototype onto data the app already has. **Do not fabricate missing data; missing fields produce premium empty states (omit, never `N/A`/`—`/placeholder).**

- **Trip metadata** → `Trip` (`destination`, dates, `status`, `notes`). Cover title = destination; meta row = dates · party · status. No invented party size if absent — omit.
- **Itinerary items (placed)** → `ItineraryItem` with a `dayId`, grouped by `ItineraryDay` (`dayNumber`, `date`, `title`, `summary`, `items`). Time/period from `startTime`/`endTime`.
- **Period grouping (Morning / Afternoon / Evening / Logistics)** is a **presentation grouping derived from item times**, not a new schema field and not a new time-of-day data model (respects Design Implementation Contract §26 / Addendum §3 — "days are not boxes," no new time-of-day blocks in data). Logistics = transit/flight/hotel-checkin-type items. Items without a time fall into a calm "Anytime"/Logistics bucket, not a fabricated slot.
- **Trip Ideas (candidates)** → unassigned `ItineraryItem`s (no `dayId`), `itemType` ∈ {`activity`→Places, `meal`→Dining, `hotel`→Hotels, `flight`→Flights}, with `ideaStatus` ∈ {`must_do`, `maybe`, `skipped`} and `details.*` (rating, address, category, etc.). This is the Ideas Tray source — already what `TripIdeasPanel` reads.
- **Saved-derived notes** → `details.userNote` (carried through from Saved via the merged-and-tested carryover: `addSavedItemToTrip`, `seedSavedFlightAsItineraryItem`, `createTripFromSavedItem`). The Ideas Tray and item cards render this as private marginalia (§9). Notes must carry through if available; never invent a note.
- **Compare links** → reuse existing compare: client-side compare set / `CompareModal` for places; `buildHotelCompareUrl` for hotels; flight compare/booking via existing `bookingLink` / `googleFlightsSearchUrl` on `details`. No new compare backend.
- **Map / details links** → existing per-item `details.googleMapsUri` (and `TripMapView`). No new geocoding.
- **Item types** → `flight` / `hotel` / `meal` (restaurant) / `activity` (attraction/place) / `transit` / `note`. Contextual actions are chosen by type (§10).

**Hard rules:**
- Existing **add-to-trip / create-trip / compare** flows must not regress (these are the merged Saved→Trip paths and the compare set).
- The merged **Saved → Trip Ideas note carryover** must still work and surface in the tray/cards.
- No new fields, no new endpoints, no schema/SQL change required for v1.

---

## 9. Notes hierarchy

Three layers, never mixed. One note line by default; expanded views may reveal the full text.

1. **User saved note (private marginalia)** — `details.userNote`. Rendered as **italic serif** with a subtle **brass hairline** accent. This is the user's voice. Quiet, personal, never quote-styled like a pull-quote.
2. **Concierge / search reason** — muted **sans helper** text with a small sparkle glyph. The reason a card surfaced. Never rendered as a quote, never fabricated; shown only when the backend supplied it.
3. **Provider facts** — small metadata on the `.meta` line only (rating, price, distance, hours) — and only when real. These never mix into the note lines.

Cards clamp notes to **one line** by default (CSS line-clamp); the expanded day or a detail view reveals full text. If a layer is absent, it is omitted — no empty label, no placeholder.

---

## 10. Placement-first Ideas Tray

The Ideas Tray is **not another Saved list**. Its reason to exist is to *place* a candidate into the plan.

- **Suggested fit:** each card shows where it could go *when that can be inferred honestly* (e.g. a dinner-time restaurant → "Add to Day 2 · Dinner"; a hotel → "Add as Hotel anchor"). The suggestion is a calm hint, not a fabricated certainty.
- **Primary action = placement.** One bold, full-width marine-ink primary action per card stating the exact placement. Tap performs a real write.
- **The durable placement write path exists:** assigning an unassigned idea to a day is the existing `assignIdeaToDay` path used by `TripIdeasPanel` (status/note via `updateIdeaMeta`). V1 wires the primary action to this real write — it is not faked.
- **Where a confident slot can't be derived,** the primary action falls back to a safe real action ("Add to Day…" picker, or "Keep as Maybe" via `ideaStatus`) — never a fabricated slot write. If any specific placement target (e.g. an exact named meal slot) has **no** durable write contract, v1 must not fake it: expose the safe existing action and **document the missing contract** in the PR rather than simulating persistence.
- **Secondary actions** (Map / Compare / Details / Keep-as-Maybe) collapse into a single quiet **text-link row** (ContextualActionRow), contextual by kind (§12 / §10): hotels → Compare hotels; flights → Compare flights / booking; restaurants & attractions → Map / Details. A card carries Compare only when its kind warrants it.

---

## 11. Decision strip

"Unresolved planning" in v1 = a day (or the trip) that still has open choices: a pending anchor (hotel not chosen), or candidate ideas not yet placed for that day, or an explicitly flagged still-deciding item.

- **Rendering:** below each day brief, a calm paper strip with **one brass dot**, an italic summary of what's open ("Still deciding: dinner · rainy-day backup"), and a quiet link — **"Add from Ideas Tray"** — that deep-links to the Ideas Tray filtered to that day.
- **Read-only in v1:** the strip summarizes and links; it does not itself resolve decisions. The tap deep-links into the tray (the placement surface).
- **Calm premium styling, never a warning:** brass dot on warm paper, never red, never an alert banner, never an urgency badge. A single small "Decision" marker may remain on the *pending* Brief row only.

---

## 12. Visual contract

Enforceable translation of the prototype into rules (specializes the Folio direction and Design Implementation Contract §§3–9, 26, 31 for this surface):

- **Warm paper world is the default chrome** — background, Brief, Dayboard, day cards, Ideas Tray sheet/rail, decision strip are all paper (linen/bone, never `#FFFFFF`).
- **Dark cinematic cover only as the hero / folio accent** — exactly one cinematic panel (the trip cover); never the page shell, never a dark card grid.
- **Brass used sparingly** — hairlines, the decision dot, serials, editorial ornaments. Never a button fill. One accent per surface.
- **Marine ink is the primary action** — the placement CTA and primary actions in paper world.
- **No dense SaaS dashboard** — no KPI tiles, progress rings, completion %, streaks, badges.
- **No giant tables** and **no four-column desktop "zoo"** — desktop is three calm zones (context · Dayboard · Ideas rail), not a control panel.
- **No tiny desktop controls on mobile** — controls are thumb-sized (≥44pt); the desktop rail's denser chrome does not leak to phone.
- **One primary action per card** — exactly one bold action; everything else is a quiet text-link.
- At least one **editorial serif** element per screen; italic serif is the product's voice (captions, day numerals, where-lines, private notes).
- Respect `prefers-reduced-motion` (Design Implementation Contract §7/§12): no transform/scale entrances under reduced motion; calm fades only.

---

## 13. Acceptance criteria

A v1 implementation is accepted only if all apply:

- [ ] On a ~390–402px phone, the first viewport answers *where · what's fixed · what's to decide* (cover + Brief + start of Dayboard) without scrolling.
- [ ] The Brief shows real placed progress, one fixed line, one pending line with a contextual action, and a real "N to decide" count — no fabricated counts.
- [ ] Dayboard renders collapsed day cards; tapping expands to Morning/Afternoon/Evening/Logistics groups derived from item times (no new time-of-day schema).
- [ ] Each day shows a calm brass-dot decision strip (never red) linking into the Ideas Tray filtered to that day.
- [ ] The Ideas Tray opens as a mobile bottom sheet and as a desktop right rail, with kind filter chips and real counts.
- [ ] Each Ideas Tray card has exactly one bold primary placement action wired to the real assign write (`assignIdeaToDay` / `updateIdeaMeta`); secondary actions collapse into one quiet text-link row, contextual by kind.
- [ ] Where no durable placement contract exists for a specific slot, v1 exposes a safe existing action and the PR documents the gap — nothing fake is persisted.
- [ ] Notes render in three typed layers (private italic-serif + brass hairline / concierge muted-sans helper / provider meta), clamped to one line by default.
- [ ] Compare / Map / Details surface only where real data exists; hotels show compare-hotels, flights show compare/booking, places show map/details.
- [ ] Desktop is three zones (context · Dayboard · Ideas rail); the map is not a permanent column.
- [ ] No map fold-out / lens switcher / numbered pins shipped (v2 seam only).
- [ ] Weather, distance, hours, ratings, party size omitted when not real — no `N/A`/`—`/placeholder.
- [ ] Existing Saved→Trip add/create/compare flows and the Saved→Trip Ideas note carryover are not regressed.
- [ ] Warm paper is dominant; exactly one dark cinematic cover; brass is foil-only; one marine primary action per card.
- [ ] `prefers-reduced-motion` respected.

---

## 14. Validation plan

- **Mobile screenshot/preview validation:** capture the overview (cover + Brief + Dayboard), an expanded day (decision strip + period groups), and the Ideas Tray bottom sheet at ~390–402px; compare against prototype frames A–C.
- **Desktop screenshot/preview validation:** capture the three-zone workspace; compare against frame E. Confirm the map is not a permanent column (frame F's fold-out is v2).
- **Carryover regression:** verify a Saved item with a note, added to / used to create a trip, still surfaces its note in the Ideas Tray and on the placed card (the merged carryover tests must stay green).
- **Compare/detail preservation:** verify hotel compare URL, flight booking/compare links, place map links, and the compare set / `CompareModal` all still work.
- **No fake data:** grep/spot-check that weather/distance/rating/party fields are omitted when absent; no placeholder strings.
- **No map drawer in v1:** confirm no fold-out drawer, lens switcher, or numbered-pin component shipped.
- **Tests to run/update (per `docs/ai/TEST_ROUTING.md`, default Tier 1–2 for this design surface):** the existing trip-ideas / itinerary / Saved→Trip carryover contract tests; add focused tests for the Brief composition, the decision-strip render, and the placement primary action wiring. State test tier and why it was sufficient in the PR.
- **Supabase SQL:** none expected for v1 — state "no SQL/migration" in the PR summary.

---

## 15. Build order

Ship as one coherent capability slice if it stays calm and bounded; otherwise split along these seams (each adds visible value, none touches backend/providers):

- **v1A — Shell + Trip Brief + Dayboard:** JourneyDeskPage layout, dark cover hero, the calm Brief, collapsed DayCards. The 10-second mobile read.
- **v1B — Ideas Tray + Notes:** the bottom-sheet/right-rail tray, placement-first cards wired to the real assign write, ContextualActionRow, and the three-layer NoteMarginalia.
- **v1C — Expanded Day + Decision Strip:** ExpandedDayPanel with Morning/Afternoon/Evening/Logistics grouping and the brass-dot decision strip deep-linking into the tray.
- **v1D — Desktop adaptation + polish:** three-zone desktop spread, rail chips lose icons, reduced-motion and visual-contract polish.
- **v2 (deferred) — Map Fold-Out:** the trip/day/idea lens drawer with numbered pins, behind the v1 MapEntryPoint seam (§4). Not part of v1.

---

*This blueprint specializes the Folio direction and the Design Implementation Contract for the Journey Desk surface. A future slice prompt should read this file plus the prototype, and must not re-explain the visual direction or broaden scope beyond §2.*
