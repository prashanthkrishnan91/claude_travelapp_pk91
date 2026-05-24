/**
 * Journey Desk mobile IA closeout — day-scoped Add-to-Day flow + inline
 * selected-day expansion.
 *
 * Corrected IA (post-review):
 *  1. Brief / Dayboard is read-only — no add controls.
 *  2. Add-to-Day (four verticals) lives in the Itinerary workspace.
 *  3. Selecting a day in Brief still expands its detail INLINE under that card.
 *  4. Build is retained as the internal search surface but hidden from mobile nav.
 *
 * Source-scan contract tests (no DOM/browser).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const root = new URL("../", import.meta.url);

const page = readFileSync(new URL("src/app/trips/[id]/page.tsx", root), "utf8");
const dayboard = readFileSync(new URL("src/components/trips/Dayboard.tsx", root), "utf8");
const panel = readFileSync(new URL("src/components/trips/ExpandedDayPanel.tsx", root), "utf8");
const drawer = readFileSync(new URL("src/components/trips/AddToDayDrawer.tsx", root), "utf8");
const builder = readFileSync(new URL("src/components/trips/TripBuilder.tsx", root), "utf8");
const itineraryColumn = readFileSync(new URL("src/components/trips/ItineraryDayColumn.tsx", root), "utf8");
const css = readFileSync(new URL("src/app/globals.css", root), "utf8");

// ── 1. AddToDayDrawer exists as a new file ──────────────────────────────────

test("AddToDayDrawer file exists", () => {
  assert.ok(existsSync(new URL("src/components/trips/AddToDayDrawer.tsx", root)));
});

// ── 2. Inline day expansion (selected day panel appears under that card) ─────

test("Dayboard accepts inlineDayPanel ReactNode prop", () => {
  assert.match(dayboard, /inlineDayPanel\?: ReactNode/);
});

test("Dayboard renders inlineDayPanel inline under the selected day — not after the full list", () => {
  // The inline panel must be rendered inside the per-day <li> when isSelected is true.
  assert.match(dayboard, /isSelected && inlineDayPanel/);
});

test("page passes ExpandedDayPanel as inlineDayPanel prop to Dayboard (inline under day card)", () => {
  assert.match(page, /inlineDayPanel=\{expandedDay \?/);
  assert.match(page, /<ExpandedDayPanel/);
});

test("page computes expandedDay via itineraryDays.find for the selected day", () => {
  assert.match(page, /expandedDay = selectedDayId \? itineraryDays\.find\(\(d\) => d\.id === selectedDayId\)/);
});

test("selected-day expanded panel no longer renders as a standalone block after the Dayboard list", () => {
  // The old pattern had ExpandedDayPanel AFTER the Dayboard in page source.
  // Now it is passed as inlineDayPanel; there must be no top-level standalone
  // ExpandedDayPanel block gated on selectedDayId outside of Dayboard.
  // Verify: the old `itineraryDays.find((d) => d.id === selectedDayId)!` with a
  // non-null assertion does not exist (it's now the expandedDay variable).
  assert.doesNotMatch(page, /day=\{itineraryDays\.find\(\(d\) => d\.id === selectedDayId\)!\}/);
});

// ── 3. Brief is read-only — no Add-to-Day controls ──────────────────────────

test("Brief Dayboard does not receive onAddToDay from page (Brief is read-only)", () => {
  // The <Dayboard> call in page.tsx must not pass onAddToDay — that prop belongs
  // in Itinerary, not Brief. The Dayboard component still supports the prop
  // (defensive), but page must not wire it up in the Brief section.
  // Strategy: check that onAddToDay= does not appear near the <Dayboard JSX.
  const dayboardJsxIdx = page.indexOf("<Dayboard");
  assert.ok(dayboardJsxIdx !== -1, "<Dayboard must exist in page");
  const dayboardJsxEnd = page.indexOf("/>", dayboardJsxIdx);
  const dayboardJsx = page.slice(dayboardJsxIdx, dayboardJsxEnd + 2);
  assert.doesNotMatch(dayboardJsx, /onAddToDay=/);
});

test("Brief inline ExpandedDayPanel does not receive onAddToDay (Brief is read-only)", () => {
  // The ExpandedDayPanel in the Brief inlineDayPanel prop must not pass onAddToDay.
  const panelJsxIdx = page.indexOf("<ExpandedDayPanel");
  assert.ok(panelJsxIdx !== -1, "<ExpandedDayPanel must exist in page");
  const panelJsxEnd = page.indexOf("/>", panelJsxIdx);
  const panelJsx = page.slice(panelJsxIdx, panelJsxEnd + 2);
  assert.doesNotMatch(panelJsx, /onAddToDay=/);
});

test("Dayboard component still supports onAddToDay prop (capability kept, just not wired in Brief)", () => {
  assert.match(dayboard, /onAddToDay\?: \(day: ItineraryDay\) => void/);
});

test("ExpandedDayPanel component still supports onAddToDay prop (capability kept)", () => {
  assert.match(panel, /onAddToDay\?: \(\) => void/);
});

// ── 4. AddToDayDrawer — 4 verticals, paper-world sheet ──────────────────────

test("AddToDayDrawer has a stable testid", () => {
  assert.match(drawer, /data-testid="add-to-day-drawer"/);
});

test("AddToDayDrawer offers Flight vertical with testid add-to-day-flight", () => {
  // testIds are in the VERTICALS array; buttons render data-testid={testId}
  assert.match(drawer, /testId: "add-to-day-flight"/);
  assert.match(drawer, /vertical: "flight"/);
  assert.match(drawer, /label: "Flight"/);
});

test("AddToDayDrawer offers Stay (hotel) vertical with testid add-to-day-hotel", () => {
  assert.match(drawer, /testId: "add-to-day-hotel"/);
  assert.match(drawer, /vertical: "hotel"/);
  assert.match(drawer, /label: "Stay"/);
});

test("AddToDayDrawer offers Dining (restaurant) vertical with testid add-to-day-dining", () => {
  assert.match(drawer, /testId: "add-to-day-dining"/);
  assert.match(drawer, /vertical: "restaurant"/);
  assert.match(drawer, /label: "Dining"/);
});

test("AddToDayDrawer offers Things to do (attraction) vertical with testid add-to-day-attraction", () => {
  assert.match(drawer, /testId: "add-to-day-attraction"/);
  assert.match(drawer, /vertical: "attraction"/);
  assert.match(drawer, /label: "Things to do"/);
});

test("AddToDayDrawer uses the shared journey-desk-tray CSS shell (paper, consistent with IdeasTray)", () => {
  assert.match(drawer, /journey-desk-tray/);
  assert.match(drawer, /jd-tray-enter/);
});

test("AddToDayDrawer calls onSelectVertical with the chosen vertical key", () => {
  assert.match(drawer, /onSelectVertical\(vertical\)/);
});

test("AddToDayDrawer supports Esc to close", () => {
  assert.match(drawer, /key === "Escape"/);
  assert.match(drawer, /onClose\(\)/);
});

test("AddToDayDrawer shows the target day number in the header", () => {
  assert.match(drawer, /Day \$\{day\.dayNumber\}/);
});

// ── 5. Build handoff — target day pre-selected in TripBuilder ────────────────

test("TripBuilder accepts focusDayId prop", () => {
  assert.match(builder, /focusDayId\?: string \| null/);
});

test("TripBuilder syncs selectedDayId to focusDayId via useEffect (no remount needed)", () => {
  assert.match(builder, /focusDayId && days\.some\(\(d\) => d\.id === focusDayId\)/);
  assert.match(builder, /setSelectedDayId\(focusDayId\)/);
});

test("page passes focusDayId={buildFocusDayId} to TripBuilder", () => {
  assert.match(page, /focusDayId=\{buildFocusDayId\}/);
});

test("page stores addToDayOpen and addToDayDayId state for the drawer", () => {
  assert.match(page, /const \[addToDayOpen,\s*setAddToDayOpen\]/);
  assert.match(page, /const \[addToDayDayId,\s*setAddToDayDayId\]/);
  assert.match(page, /const \[buildFocusDayId,\s*setBuildFocusDayId\]/);
});

test("handleOpenAddToDay sets the target day ID and opens the drawer", () => {
  assert.match(page, /function handleOpenAddToDay\(day: ItineraryDay\)/);
  assert.match(page, /setAddToDayDayId\(day\.id\)/);
  assert.match(page, /setAddToDayOpen\(true\)/);
});

test("handleAddToDaySelectVertical routes to Build workspace with target day locked", () => {
  assert.match(page, /function handleAddToDaySelectVertical/);
  assert.match(page, /setBuildFocusDayId\(addToDayDayId\)/);
  assert.match(page, /setActiveMobileWorkspace\("build"\)/);
});

// ── 6. Return affordance — "Back to Day N" ───────────────────────────────────

test("page shows 'Back to Day N' return banner in Build workspace when coming from Add-to-Day", () => {
  assert.match(page, /data-testid="jd-build-return-banner"/);
  assert.match(page, /data-testid="jd-build-return-btn"/);
  // Routes back to Itinerary (not Brief) and clears the focus
  assert.match(page, /setActiveMobileWorkspace\("itinerary"\)[\s\S]{0,60}setBuildFocusDayId\(null\)/);
});

test("return banner is mobile-only (lg:hidden)", () => {
  // The return banner must not appear on desktop where both panels are visible.
  const bannerIdx = page.indexOf('data-testid="jd-build-return-banner"');
  assert.ok(bannerIdx !== -1, "banner must exist");
  const surrounding = page.slice(Math.max(0, bannerIdx - 200), bannerIdx + 200);
  assert.match(surrounding, /lg:hidden/);
});

// ── 7. No fabricated data ────────────────────────────────────────────────────

test("AddToDayDrawer contains no fake coordinates, pins, or place data", () => {
  assert.doesNotMatch(drawer, /lat|lng|goldenSpread|Nominatim|geocode/i);
});

test("AddToDayDrawer does not create new provider or search endpoints", () => {
  assert.doesNotMatch(drawer, /fetch\(|api\.|searchHotels|searchAttractions|searchRestaurants/i);
});

// ── 8. Mobile nav and Build surface ──────────────────────────────────────────

test("Mobile workspace nav does not expose Build as a visible tab", () => {
  // Build is hidden from mobile nav; it is the internal search surface used by
  // the Add-to-Day handoff. WORKSPACE_TABS must not include the build tab testid.
  assert.doesNotMatch(page, /trip-mobile-tab-build/);
});

test("Itinerary and Ideas tabs remain in mobile nav", () => {
  assert.match(page, /trip-mobile-tab-itinerary/);
  assert.match(page, /trip-mobile-tab-ideas/);
});

test("Build panel is still present in TripBuilder as internal surface (not deleted)", () => {
  assert.match(builder, /trip-mobile-panel-build/);
  assert.match(page, /<TripBuilder/);
});

// ── 9. Itinerary workspace owns Add-to-Day entry ─────────────────────────────

test("ItineraryDayColumn accepts onAddToDay prop", () => {
  assert.match(itineraryColumn, /onAddToDay\?: \(day: ItineraryDay\) => void/);
});

test("ItineraryDayColumn renders 'Add to this day' button with stable testid itinerary-add-to-day-btn", () => {
  assert.match(itineraryColumn, /data-testid="itinerary-add-to-day-btn"/);
  assert.match(itineraryColumn, /Add to this day/);
  assert.match(itineraryColumn, /onAddToDay\(day\)/);
});

test("TripBuilder passes onAddToDay to ItineraryDayColumn", () => {
  assert.match(builder, /onAddToDay\?: \(day: ItineraryDay\) => void/);
  assert.match(builder, /onAddToDay={onAddToDay}/);
});

test("page passes onAddToDay={handleOpenAddToDay} to TripBuilder", () => {
  assert.match(page, /onAddToDay=\{handleOpenAddToDay\}/);
});

// ── 10. CSS primitives for the new flow ──────────────────────────────────────

test("jd-day-add-btn CSS class is defined in globals.css", () => {
  assert.match(css, /\.jd-day-add-btn \{/);
});

test("jd-vertical-target CSS class is defined in globals.css", () => {
  assert.match(css, /\.jd-vertical-target \{/);
});

test("jd-day-add-btn and jd-vertical-target have reduced-motion guards", () => {
  // Both classes must appear inside a prefers-reduced-motion block in the full CSS source.
  // Find the IA closeout section and verify both classes are guarded there.
  const section = css.slice(css.indexOf("Journey Desk mobile IA closeout"), css.indexOf("Journey Desk v2C"));
  assert.ok(section.length > 0, "IA closeout CSS section must exist");
  assert.match(section, /prefers-reduced-motion: reduce/);
  assert.match(section, /jd-day-add-btn/);
  assert.match(section, /jd-vertical-target/);
});

// ── 10. Vertical threading — selected vertical opens matching Build section ───

test("page stores buildFocusVertical state", () => {
  assert.match(page, /const \[buildFocusVertical,\s*setBuildFocusVertical\]/);
});

test("handleAddToDaySelectVertical accepts vertical argument and stores it", () => {
  // The handler must call setBuildFocusVertical with the chosen vertical.
  assert.match(page, /function handleAddToDaySelectVertical\(vertical/);
  assert.match(page, /setBuildFocusVertical\(vertical\)/);
});

test("page passes focusVertical={buildFocusVertical} to TripBuilder", () => {
  assert.match(page, /focusVertical=\{buildFocusVertical\}/);
});

test("return banner handler clears buildFocusVertical on return", () => {
  assert.match(page, /setBuildFocusVertical\(null\)/);
});

test("TripBuilder accepts focusVertical prop", () => {
  assert.match(builder, /focusVertical\?: string \| null/);
});

test("TripBuilder has panel-level refs for all four verticals", () => {
  assert.match(builder, /flightPanelRef\s*=\s*useRef/);
  assert.match(builder, /hotelPanelRef\s*=\s*useRef/);
  assert.match(builder, /attractionPanelRef\s*=\s*useRef/);
  assert.match(builder, /restaurantPanelRef\s*=\s*useRef/);
});

test("TripBuilder useEffect opens Flights panel when focusVertical is 'flight'", () => {
  assert.match(builder, /focusVertical === "flight"/);
  assert.match(builder, /setFlightPanelOpen\(true\)/);
  assert.match(builder, /flightPanelRef\.current\?\.scrollIntoView/);
});

test("TripBuilder useEffect opens Hotels panel when focusVertical is 'hotel'", () => {
  assert.match(builder, /focusVertical === "hotel"/);
  assert.match(builder, /setHotelPanelOpen\(true\)/);
  assert.match(builder, /hotelPanelRef\.current\?\.scrollIntoView/);
});

test("TripBuilder useEffect switches to list view and opens Attractions panel when focusVertical is 'attraction'", () => {
  assert.match(builder, /focusVertical === "attraction"/);
  assert.match(builder, /setAttractionPanelOpen\(true\)/);
  assert.match(builder, /attractionPanelRef\.current\?\.scrollIntoView/);
});

test("TripBuilder useEffect switches to list view and opens Restaurants panel when focusVertical is 'restaurant'", () => {
  assert.match(builder, /focusVertical === "restaurant"/);
  assert.match(builder, /setRestaurantPanelOpen\(true\)/);
  assert.match(builder, /restaurantPanelRef\.current\?\.scrollIntoView/);
});

test("TripBuilder vertical-focus useEffect switches to list view for attraction/restaurant (panels live in list branch)", () => {
  // viewMode must be set to "list" for attraction and restaurant since their
  // CandidatePanels only render in the list view branch.
  const effectStart = builder.indexOf('focusVertical === "attraction"');
  const effectEnd = builder.indexOf('focusVertical === "restaurant"') + 200;
  const effectSlice = builder.slice(effectStart, effectEnd);
  assert.match(effectSlice, /setViewMode\("list"\)/);
});

// ── 11. Parent itinerary refresh after Add-to-Day add ────────────────────────

test("TripBuilder exposes onItineraryChanged callback prop", () => {
  assert.match(builder, /onItineraryChanged\?: \(\) => void/);
});

test("TripBuilder calls onItineraryChanged after successful candidate (flight/hotel) add", () => {
  // The call must appear inside the try block, after showToast, before the catch block.
  // Strategy: find the candidate handler and check it contains onItineraryChanged?.()
  // with the catch block present afterward (meaning it's in the success path only).
  const handlerStart = builder.indexOf("handleAddCandidateToItinerary = useCallback");
  const handlerEnd = builder.indexOf("}, [days, selectedDayId, tripId, showToast, onItineraryChanged])", handlerStart);
  const handlerSlice = builder.slice(handlerStart, handlerEnd);
  assert.match(handlerSlice, /onItineraryChanged\?\.\(\)/);
  // Must be in the success path (before catch)
  const catchIdx = handlerSlice.indexOf("} catch {");
  const callIdx = handlerSlice.indexOf("onItineraryChanged?.()");
  assert.ok(callIdx < catchIdx, "onItineraryChanged must fire before catch block");
});

test("TripBuilder calls onItineraryChanged after successful attraction add", () => {
  const handlerStart = builder.indexOf("handleAddAttractionToItinerary = useCallback");
  const handlerEnd = builder.indexOf("}, [days, selectedDayId, tripId, showToast, onItineraryChanged])", handlerStart);
  const slice = builder.slice(handlerStart, handlerEnd);
  assert.match(slice, /onItineraryChanged\?\.\(\)/);
  const catchIdx = slice.indexOf("} catch {");
  const callIdx = slice.indexOf("onItineraryChanged?.()");
  assert.ok(callIdx < catchIdx, "onItineraryChanged must fire before catch block");
});

test("TripBuilder calls onItineraryChanged after successful restaurant add", () => {
  const handlerStart = builder.indexOf("handleAddRestaurantToItinerary = useCallback");
  const handlerEnd = builder.indexOf("}, [days, selectedDayId, tripId, showToast, onItineraryChanged])", handlerStart);
  const slice = builder.slice(handlerStart, handlerEnd);
  assert.match(slice, /onItineraryChanged\?\.\(\)/);
  const catchIdx = slice.indexOf("} catch {");
  const callIdx = slice.indexOf("onItineraryChanged?.()");
  assert.ok(callIdx < catchIdx, "onItineraryChanged must fire before catch block");
});

test("TripBuilder calls onItineraryChanged after successful round-trip flight add", () => {
  const handlerStart = builder.indexOf("handleAddRoundTripToItinerary = useCallback");
  const handlerEnd = builder.indexOf("}, [days, tripId, showToast, extractLegDepartureDate, resolveItineraryDayByDate, onItineraryChanged])", handlerStart);
  const slice = builder.slice(handlerStart, handlerEnd);
  assert.match(slice, /onItineraryChanged\?\.\(\)/);
  // The success-path callback appears after showToast(msg) and before the outer catch
  // (which matches "Failed to add round-trip"). The outer catch is the LAST catch block.
  const outerCatchIdx = slice.lastIndexOf("} catch {");
  const callIdx = slice.lastIndexOf("onItineraryChanged?.()");
  assert.ok(callIdx < outerCatchIdx, "onItineraryChanged must fire before outer catch block");
});

test("TripBuilder does not call onItineraryChanged inside the outer (failure) catch blocks", () => {
  // Outer catch blocks all follow the pattern: } catch {\n      showToast("Failed
  // Check that none of those blocks contain onItineraryChanged?.().
  const outerCatchRe = /\} catch \{\s*\n\s*showToast\("Failed[^}]+\}/g;
  let m;
  let found = 0;
  while ((m = outerCatchRe.exec(builder)) !== null) {
    found++;
    assert.doesNotMatch(m[0], /onItineraryChanged\?\.\(\)/, "onItineraryChanged must not fire in failure catch");
  }
  assert.ok(found > 0, "should have found at least one outer catch block to verify");
});

test("page.tsx has refreshParentItinerary that calls setItineraryDays without setTripBuilderKey", () => {
  assert.match(page, /function refreshParentItinerary/);
  const fnStart = page.indexOf("function refreshParentItinerary");
  const fnEnd = page.indexOf("\n  }", fnStart) + 4;
  const fnSlice = page.slice(fnStart, fnEnd);
  assert.match(fnSlice, /setItineraryDays/);
  assert.doesNotMatch(fnSlice, /setTripBuilderKey/);
});

test("page passes onItineraryChanged={refreshParentItinerary} to TripBuilder", () => {
  assert.match(page, /onItineraryChanged=\{refreshParentItinerary\}/);
});

// ── 12. Desktop coherence — no double-render of day detail ──────────────────

test("Desktop coherence: ExpandedDayPanel appears only once in page source (via inlineDayPanel)", () => {
  // Count occurrences of <ExpandedDayPanel in page.tsx — should be exactly 1
  // Count occurrences of <ExpandedDayPanel in page.tsx — should be exactly 1
  // (inside the inlineDayPanel prop, not also as a standalone after-list block).
  const occurrences = (page.match(/<ExpandedDayPanel/g) ?? []).length;
  assert.strictEqual(occurrences, 1, `Expected 1 <ExpandedDayPanel in page, found ${occurrences}`);
});
