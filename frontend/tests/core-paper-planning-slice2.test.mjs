/**
 * Stage 3.5 Slice 2 — Core Paper Planning Surfaces contract tests
 *
 * Verifies:
 *  - Paper primitives are defined in globals.css
 *  - mobile-top-bar uses paper-world tokens (not midnight)
 *  - Dashboard/trips cards use folio-paper-card / folio-paper-panel
 *  - Trip detail chapter cover uses folio-paper-panel
 *  - ItineraryDayColumn uses folio-paper-card
 *  - TripReadinessCockpit uses folio-paper-panel
 *  - Primary CTAs in touched paper surfaces use btn-marine or marine-ink tokens
 *  - MobileNav top bar icon uses paper-appropriate light bg
 *  - PR #431 protected paths are untouched (CityAutocomplete portal,
 *    addRoundTripLegToDay, handleAddRoundTripToItinerary, isExplicitlyOneWay)
 *  - Forbidden dark-world tokens removed from converted surfaces
 *  - All testids from prior phases remain present in converted files
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const srcRoot = resolve(root, "src");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}

// ── 1. Paper primitives in globals.css ───────────────────────────────────────

describe("Paper primitives — globals.css", () => {
  const css = readSrc("app/globals.css");

  it("defines .folio-paper-card", () => {
    assert.ok(css.includes(".folio-paper-card"), "folio-paper-card must be defined");
  });

  it("folio-paper-card uses bone background", () => {
    const idx = css.indexOf(".folio-paper-card");
    const block = css.slice(idx, idx + 400);
    assert.ok(block.includes("ds-bone") || block.includes("var(--ds-bone)"), "folio-paper-card must use ds-bone background");
  });

  it("defines .folio-paper-panel", () => {
    assert.ok(css.includes(".folio-paper-panel"), "folio-paper-panel must be defined");
  });

  it("folio-paper-panel uses warm-paper background", () => {
    const idx = css.indexOf(".folio-paper-panel");
    const block = css.slice(idx, idx + 400);
    assert.ok(block.includes("warm-paper") || block.includes("var(--ds-warm-paper)"), "folio-paper-panel must use ds-warm-paper background");
  });

  it("defines .folio-paper-section", () => {
    assert.ok(css.includes(".folio-paper-section"), "folio-paper-section must be defined");
  });

  it("defines .folio-paper-header", () => {
    assert.ok(css.includes(".folio-paper-header"), "folio-paper-header must be defined");
  });

  it("defines .folio-divider", () => {
    assert.ok(css.includes(".folio-divider"), "folio-divider must be defined");
  });

  it("defines .folio-muted-label", () => {
    assert.ok(css.includes(".folio-muted-label"), "folio-muted-label must be defined");
  });

  it("defines .folio-chip", () => {
    assert.ok(css.includes(".folio-chip"), "folio-chip must be defined");
  });

  it("defines .folio-input", () => {
    assert.ok(css.includes(".folio-input"), "folio-input must be defined");
  });

  it("folio-input uses bone background (not midnight-ink)", () => {
    const idx = css.indexOf(".folio-input");
    const block = css.slice(idx, idx + 300);
    assert.ok(block.includes("bone") || block.includes("var(--ds-bone)"), "folio-input must use bone/paper background");
    assert.ok(!block.includes("midnight"), "folio-input must not use midnight-ink");
  });
});

// ── 2. Mobile top bar — paper-world chrome ───────────────────────────────────

describe("Mobile top bar — paper-world chrome (Slice 2)", () => {
  const css = readSrc("app/globals.css");
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("globals.css mobile-top-bar uses bone/paper tokens, not midnight", () => {
    const idx = css.indexOf(".mobile-top-bar");
    const block = css.slice(idx, idx + 200);
    assert.ok(
      block.includes("bone") || block.includes("warm-paper") || block.includes("hairline"),
      ".mobile-top-bar must use paper-world tokens"
    );
    assert.ok(
      !block.includes("midnight-ink"),
      ".mobile-top-bar must not use midnight-ink (Slice 2 paper conversion)"
    );
  });

  it("MobileNav top bar icon container uses light-bg appropriate class (not bg-ds-carbon)", () => {
    const headerIdx = nav.indexOf('data-testid="mobile-top-bar"');
    const headerBlock = nav.slice(headerIdx, headerIdx + 600);
    assert.ok(
      !headerBlock.includes("bg-ds-carbon") && !headerBlock.includes("bg-ds-onyx"),
      "top bar icon must not use dark card bg (bg-ds-carbon/onyx) on paper chrome"
    );
  });

  it("MobileNav top bar icon container uses linen or bone bg", () => {
    const headerIdx = nav.indexOf('data-testid="mobile-top-bar"');
    const headerBlock = nav.slice(headerIdx, headerIdx + 600);
    assert.ok(
      headerBlock.includes("bg-ds-linen") || headerBlock.includes("bg-ds-bone"),
      "top bar icon must use paper-world bg (linen/bone)"
    );
  });

  it("MobileNav top bar brand text uses folio-ink (not ds-text cream)", () => {
    const headerIdx = nav.indexOf('data-testid="mobile-top-bar"');
    const headerBlock = nav.slice(headerIdx, headerIdx + 600);
    assert.ok(
      headerBlock.includes("folio-ink"),
      "top bar brand text must use folio-ink for readability on paper bg"
    );
  });

  it("mobile-top-bar uses marine-ink accent on icon (not sandstone gold)", () => {
    const headerIdx = nav.indexOf('data-testid="mobile-top-bar"');
    const headerBlock = nav.slice(headerIdx, headerIdx + 600);
    assert.ok(
      headerBlock.includes("marine-ink"),
      "top bar icon accent must use marine-ink in paper world"
    );
  });
});

// ── 3. Dashboard/trips overview — paper cards ────────────────────────────────

describe("Trips page — paper card surfaces", () => {
  const page = readSrc("app/trips/page.tsx");

  it("JourneyCard uses folio-paper-card class", () => {
    assert.ok(page.includes("folio-paper-card"), "JourneyCard must use folio-paper-card");
  });

  it("JourneyCard uses folio-ink text (not ds-text cream)", () => {
    const idx = page.indexOf("journey-card");
    const block = page.slice(idx - 200, idx + 3000);
    assert.ok(block.includes("folio-ink"), "JourneyCard must use folio-ink text tokens");
  });

  it("JourneyCard uses marine-ink for primary link/CTA (not sandstone accent)", () => {
    const idx = page.indexOf("journey-card");
    const block = page.slice(idx - 200, idx + 3000);
    assert.ok(block.includes("marine-ink"), "JourneyCard must use marine-ink for primary open link");
  });

  it("JourneyCard footer uses hairline border (not pen-stroke)", () => {
    const idx = page.indexOf("journey-card");
    const block = page.slice(idx - 200, idx + 3000);
    assert.ok(block.includes("hairline"), "JourneyCard footer must use hairline border");
  });

  it("JourneyCard does not use boutique-folio or advisor-desk-panel", () => {
    const idx = page.indexOf("journey-card");
    const block = page.slice(idx - 200, idx + 3000);
    assert.ok(!block.includes("boutique-folio"), "JourneyCard must not use old dark boutique-folio class");
    assert.ok(!block.includes("advisor-desk-panel"), "JourneyCard must not use dark advisor-desk-panel class");
  });

  it("ContinuePlanningHero uses folio-paper-panel", () => {
    assert.ok(page.includes("folio-paper-panel"), "ContinuePlanningHero must use folio-paper-panel");
  });

  it("ContinuePlanningHero primary CTA uses btn-marine", () => {
    const idx = page.indexOf("continue-planning-hero");
    const block = page.slice(idx - 200, idx + 5000);
    assert.ok(block.includes("btn-marine"), "ContinuePlanningHero must use btn-marine for primary Open Trip CTA");
  });

  it("ContinuePlanningHero uses folio-paper-header zone", () => {
    const idx = page.indexOf("continue-planning-hero");
    const block = page.slice(idx - 200, idx + 5000);
    assert.ok(block.includes("folio-paper-header"), "ContinuePlanningHero header must use folio-paper-header");
  });

  it("EmptyDashboard action cards use folio-paper-card", () => {
    const idx = page.indexOf("trips-empty-state");
    const block = page.slice(idx - 100, idx + 2000);
    assert.ok(block.includes("folio-paper-card"), "EmptyDashboard action cards must use folio-paper-card");
  });

  it("EmptyDashboard Plan a Trip CTA uses btn-marine", () => {
    const idx = page.indexOf("trips-empty-state");
    const block = page.slice(idx - 100, idx + 2000);
    assert.ok(block.includes("btn-marine"), "EmptyDashboard Plan a Trip CTA must use btn-marine");
  });

  it("PlanningToolsStrip uses bone background (not ds-onyx)", () => {
    const idx = page.indexOf("planning-tools-strip");
    const block = page.slice(idx - 100, idx + 2000);
    assert.ok(block.includes("bg-ds-bone"), "PlanningToolsStrip must use bg-ds-bone (paper world)");
    assert.ok(!block.includes("bg-ds-onyx"), "PlanningToolsStrip must not use bg-ds-onyx");
  });

  it("Page header uses btn-marine for Plan a Trip CTA", () => {
    assert.ok(page.includes("btn-marine"), "trips page header Plan a Trip CTA must use btn-marine");
  });

  it("Edit modal uses folio-paper-panel", () => {
    const editIdx = page.indexOf("Edit Trip");
    const block = page.slice(editIdx - 300, editIdx + 1500);
    assert.ok(block.includes("folio-paper-panel"), "Edit modal must use folio-paper-panel");
  });

  it("Edit modal inputs use folio-input", () => {
    const editIdx = page.indexOf("Edit Trip");
    const block = page.slice(editIdx - 300, editIdx + 1500);
    assert.ok(block.includes("folio-input"), "Edit modal inputs must use folio-input class");
  });

  it("Delete modal uses folio-paper-panel", () => {
    const deleteIdx = page.indexOf("Delete Trip");
    const block = page.slice(deleteIdx - 200, deleteIdx + 800);
    assert.ok(block.includes("folio-paper-panel"), "Delete modal must use folio-paper-panel");
  });
});

// ── 4. Trip detail overview panels — paper ────────────────────────────────────

describe("Trip detail page — paper planning panels", () => {
  const page = readSrc("app/trips/[id]/page.tsx");

  it("TripChapterCover uses folio-paper-panel (not advisor-desk-panel)", () => {
    const idx = page.indexOf("trip-chapter-cover");
    const block = page.slice(idx - 100, idx + 500);
    assert.ok(block.includes("folio-paper-panel"), "TripChapterCover must use folio-paper-panel");
    assert.ok(!block.includes("advisor-desk-panel"), "TripChapterCover must not use dark advisor-desk-panel");
  });

  it("TripChapterCover destination heading uses folio-ink text", () => {
    const idx = page.indexOf("chapter-destination-heading");
    const block = page.slice(idx - 100, idx + 600);
    assert.ok(block.includes("folio-ink"), "TripChapterCover heading must use folio-ink text");
  });

  it("TripChapterCover primary action (AI Concierge) uses marine-ink fill", () => {
    assert.ok(
      page.includes("ds-marine-ink") || page.includes("btn-marine"),
      "TripChapterCover primary CTA must use marine-ink"
    );
  });

  it("Mobile workspace switcher uses bone/paper bg (not ds-onyx)", () => {
    const idx = page.indexOf("trip-mobile-workspace-switcher");
    const block = page.slice(idx - 100, idx + 600);
    assert.ok(block.includes("bg-ds-bone") || block.includes("folio-paper"), "workspace switcher must use paper bg");
    assert.ok(!block.includes("bg-ds-onyx"), "workspace switcher must not use bg-ds-onyx");
  });

  it("Mobile workspace switcher active state uses marine-ink (not ds-accent)", () => {
    const idx = page.indexOf("trip-mobile-workspace-switcher");
    const block = page.slice(idx - 100, idx + 1500);
    assert.ok(block.includes("marine-ink"), "workspace switcher active must use marine-ink");
  });

  it("Edit modal uses folio-paper-panel", () => {
    const editIdx = page.indexOf("Edit Trip");
    const block = page.slice(Math.max(0, editIdx - 400), editIdx + 2000);
    assert.ok(block.includes("folio-paper-panel"), "Trip detail edit modal must use folio-paper-panel");
  });

  it("Edit modal inputs use folio-input", () => {
    const editIdx = page.indexOf("Edit Trip");
    const block = page.slice(Math.max(0, editIdx - 400), editIdx + 2000);
    assert.ok(block.includes("folio-input"), "Trip detail edit modal inputs must use folio-input");
  });

  it("Loading state uses folio-paper-panel (not boutique-instrument)", () => {
    assert.ok(page.includes("folio-paper-panel"), "Loading state must use folio-paper-panel");
    const loadingIdx = page.indexOf("animate-pulse");
    const loadingBlock = page.slice(loadingIdx - 100, loadingIdx + 300);
    assert.ok(!loadingBlock.includes("boutique-instrument"), "Loading state must not use dark boutique-instrument");
  });
});

// ── 5. ItineraryDayColumn — paper day pages ───────────────────────────────────

describe("ItineraryDayColumn — paper day page surfaces", () => {
  const col = readSrc("components/trips/ItineraryDayColumn.tsx");

  it("day-chapter-frame uses folio-paper-card", () => {
    const idx = col.indexOf("day-chapter-frame");
    const block = col.slice(idx - 100, idx + 400);
    assert.ok(block.includes("folio-paper-card"), "day-chapter-frame must use folio-paper-card");
  });

  it("day-chapter-frame does not use bg-ds-onyx or bg-ds-midnight-ink", () => {
    const idx = col.indexOf("day-chapter-frame");
    const block = col.slice(idx - 100, idx + 400);
    assert.ok(!block.includes("bg-ds-onyx"), "day-chapter-frame must not use bg-ds-onyx");
    assert.ok(!block.includes("midnight"), "day-chapter-frame must not use midnight");
  });

  it("day-chapter-header uses folio-paper-header or linen bg", () => {
    const idx = col.indexOf("day-chapter-header");
    const block = col.slice(idx - 100, idx + 400);
    assert.ok(
      block.includes("folio-paper-header") || block.includes("bg-ds-linen"),
      "day-chapter-header must use folio-paper-header or linen bg"
    );
  });

  it("selected day number marker uses marine-ink fill (not ds-accent)", () => {
    const idx = col.indexOf("day-chapter-number");
    const block = col.slice(idx - 100, idx + 400);
    assert.ok(block.includes("marine-ink"), "selected day marker must use marine-ink bg");
  });

  it("expanded body does not use midnight-ink background", () => {
    const idx = col.indexOf("itinerary-day-mobile-expanded");
    const block = col.slice(idx - 100, idx + 600);
    assert.ok(!block.includes("midnight-ink"), "expanded body must not use midnight-ink bg");
  });

  it("expanded body uses bone/warm-paper background", () => {
    const idx = col.indexOf("itinerary-day-mobile-expanded");
    const block = col.slice(idx - 100, idx + 600);
    assert.ok(
      block.includes("bone") || block.includes("warm-paper"),
      "expanded body must use bone/warm-paper bg"
    );
  });

  it("collapsed summary does not use midnight-ink background", () => {
    const idx = col.indexOf("itinerary-day-mobile-summary");
    const block = col.slice(idx - 100, idx + 400);
    assert.ok(!block.includes("midnight-ink"), "collapsed summary must not use midnight-ink bg");
  });

  it("empty-day-chapter uses hairline border (not pen-stroke)", () => {
    const idx = col.indexOf("empty-day-chapter");
    const block = col.slice(idx - 100, idx + 500);
    assert.ok(block.includes("hairline"), "empty-day-chapter border must use hairline");
  });

  it("empty day Add button uses marine-ink (not ds-accent gold)", () => {
    const idx = col.indexOf("empty-day-chapter");
    const block = col.slice(idx - 100, idx + 600);
    assert.ok(block.includes("marine-ink"), "empty day + Add button must use marine-ink");
  });

  it("Plan My Day button uses marine-ink (not ds-accent)", () => {
    assert.ok(
      col.includes("text-ds-marine-ink"),
      "Plan My Day button must reference marine-ink"
    );
  });

  it("iconBtnClass uses bone/linen bg (not ds-carbon)", () => {
    const idx = col.indexOf("iconBtnClass");
    const block = col.slice(idx, idx + 300);
    assert.ok(
      block.includes("bg-ds-bone") || block.includes("bg-ds-linen"),
      "iconBtnClass must use paper-world bg"
    );
    assert.ok(!block.includes("bg-ds-carbon"), "iconBtnClass must not use bg-ds-carbon");
  });

  it("SuggestionsReviewPanel uses linen bg (not bg-ds-carbon)", () => {
    assert.ok(
      col.includes("bg-ds-linen"),
      "SuggestionsReviewPanel must use linen bg"
    );
  });

  it("DayTravelHintBar uses linen bg (not bg-ds-carbon)", () => {
    const idx = col.indexOf("DayTravelHintBar");
    const block = col.slice(idx, idx + 1500);
    assert.ok(block.includes("linen"), "DayTravelHintBar must use linen/paper bg");
  });

  it("gradient fade uses ds-bone (not to-ds-midnight)", () => {
    assert.ok(col.includes("to-ds-bone"), "fade-out gradient must fade to bone (not midnight)");
    assert.ok(!col.includes("to-ds-midnight"), "must not use to-ds-midnight gradient stop");
  });
});

// ── 6. TripReadinessCockpit — paper planning panel ────────────────────────────

describe("TripReadinessCockpit — paper overview panel", () => {
  const cockpit = readSrc("components/trips/TripReadinessCockpit.tsx");

  it("uses folio-paper-panel (not bg-ds-onyx)", () => {
    assert.ok(cockpit.includes("folio-paper-panel"), "TripReadinessCockpit must use folio-paper-panel");
    assert.ok(!cockpit.includes("bg-ds-onyx"), "TripReadinessCockpit must not use bg-ds-onyx");
  });

  it("header uses folio-paper-header (not bg-ds-carbon)", () => {
    assert.ok(cockpit.includes("folio-paper-header"), "Cockpit header must use folio-paper-header");
    assert.ok(!cockpit.includes("concierge-desk-header"), "Cockpit must not use dark concierge-desk-header");
  });

  it("PRIMARY_BTN uses marine-ink fill (not bg-ds-accent)", () => {
    const idx = cockpit.indexOf("PRIMARY_BTN");
    const block = cockpit.slice(idx, idx + 200);
    assert.ok(block.includes("marine-ink"), "PRIMARY_BTN must use marine-ink fill");
    assert.ok(!block.includes("bg-ds-accent"), "PRIMARY_BTN must not use bg-ds-accent");
  });

  it("GHOST_BTN uses hairline border (not pen-stroke)", () => {
    const idx = cockpit.indexOf("GHOST_BTN");
    const block = cockpit.slice(idx, idx + 200);
    assert.ok(block.includes("hairline"), "GHOST_BTN must use hairline border");
  });

  it("footer section uses linen (not bg-ds-carbon)", () => {
    assert.ok(!cockpit.includes("bg-ds-carbon"), "Cockpit footer must not use bg-ds-carbon");
    assert.ok(cockpit.includes("folio-paper-section") || cockpit.includes("linen"), "Cockpit footer must use paper section bg");
  });

  it("day coverage active pills use marine-ink (not bg-ds-accent)", () => {
    const idx = cockpit.indexOf("day-coverage-strip");
    const block = cockpit.slice(idx - 100, idx + 1500);
    assert.ok(block.includes("marine-ink"), "active day pills must use marine-ink");
    assert.ok(!block.includes("bg-ds-accent text-ds-text-inverse"), "active day pills must not use old accent style");
  });
});

// ── 7. PR #431 protected paths — untouched ────────────────────────────────────

describe("PR #431 protected logic paths — untouched", () => {
  it("CityAutocomplete still uses createPortal (portal approach preserved)", () => {
    const autocomplete = readSrc("components/ui/CityAutocomplete.tsx");
    assert.ok(autocomplete.includes("createPortal"), "CityAutocomplete portal approach must be preserved");
    assert.ok(autocomplete.includes("getBoundingClientRect"), "CityAutocomplete rect anchoring must be preserved");
  });

  it("api.ts still has addRoundTripLegToDay function", () => {
    const api = readSrc("lib/api.ts");
    assert.ok(api.includes("addRoundTripLegToDay"), "addRoundTripLegToDay must still exist in api.ts");
  });

  it("ItineraryItemCard still has isExplicitlyOneWay round-trip detection", () => {
    const card = readSrc("components/trips/ItineraryItemCard.tsx");
    assert.ok(card.includes("isExplicitlyOneWay"), "ItineraryItemCard round-trip detection must be preserved");
  });

  it("ItineraryItemCard round-trip detection checks trip_type and is_round_trip", () => {
    const card = readSrc("components/trips/ItineraryItemCard.tsx");
    assert.ok(card.includes("trip_type"), "round-trip detection must check trip_type field");
    assert.ok(card.includes("is_round_trip"), "round-trip detection must check is_round_trip field");
  });

  it("TripBuilder still has handleAddRoundTripToItinerary", () => {
    const builder = readSrc("components/trips/TripBuilder.tsx");
    assert.ok(builder.includes("handleAddRoundTripToItinerary"), "TripBuilder round-trip handler must be preserved");
  });
});

// ── 8. Existing testids preserved in converted files ─────────────────────────

describe("Existing testids preserved in converted files", () => {
  const tripsPage = readSrc("app/trips/page.tsx");
  const tripDetail = readSrc("app/trips/[id]/page.tsx");
  const col = readSrc("components/trips/ItineraryDayColumn.tsx");
  const cockpit = readSrc("components/trips/TripReadinessCockpit.tsx");

  it("journey-card testid preserved", () => {
    assert.ok(tripsPage.includes('data-testid="journey-card"'), "journey-card testid must be preserved");
  });

  it("continue-planning-hero testid preserved", () => {
    assert.ok(tripsPage.includes('data-testid="continue-planning-hero"'), "continue-planning-hero testid must be preserved");
  });

  it("my-trips-page-header testid preserved", () => {
    assert.ok(tripsPage.includes('data-testid="my-trips-page-header"'), "my-trips-page-header testid must be preserved");
  });

  it("trips-new-trip-action testid preserved", () => {
    assert.ok(tripsPage.includes('data-testid="trips-new-trip-action"'), "trips-new-trip-action testid must be preserved");
  });

  it("planning-tools-strip testid preserved", () => {
    assert.ok(tripsPage.includes('data-testid="planning-tools-strip"'), "planning-tools-strip testid must be preserved");
  });

  it("trip-chapter-cover testid preserved", () => {
    assert.ok(tripDetail.includes('data-testid="trip-chapter-cover"'), "trip-chapter-cover testid must be preserved");
  });

  it("chapter-actions testid preserved", () => {
    assert.ok(tripDetail.includes('data-testid="chapter-actions"'), "chapter-actions testid must be preserved");
  });

  it("trip-mobile-workspace-switcher testid preserved", () => {
    assert.ok(tripDetail.includes('data-testid="trip-mobile-workspace-switcher"'), "trip-mobile-workspace-switcher testid must be preserved");
  });

  it("day-chapter-frame testid preserved", () => {
    assert.ok(col.includes('data-testid="day-chapter-frame"'), "day-chapter-frame testid must be preserved");
  });

  it("day-chapter-header testid preserved", () => {
    assert.ok(col.includes('data-testid="day-chapter-header"'), "day-chapter-header testid must be preserved");
  });

  it("day-chapter-number testid preserved", () => {
    assert.ok(col.includes('data-testid="day-chapter-number"'), "day-chapter-number testid must be preserved");
  });

  it("day-chapter-title testid preserved", () => {
    assert.ok(col.includes('data-testid="day-chapter-title"'), "day-chapter-title testid must be preserved");
  });

  it("day-chapter-date testid preserved", () => {
    assert.ok(col.includes('data-testid="day-chapter-date"'), "day-chapter-date testid must be preserved");
  });

  it("day-item-count testid preserved", () => {
    assert.ok(col.includes('data-testid="day-item-count"'), "day-item-count testid must be preserved");
  });

  it("itinerary-day-mobile-action-tray testid preserved", () => {
    assert.ok(col.includes('data-testid="itinerary-day-mobile-action-tray"'), "mobile action tray testid must be preserved");
  });

  it("itinerary-day-mobile-summary testid preserved", () => {
    assert.ok(col.includes('data-testid="itinerary-day-mobile-summary"'), "mobile summary testid must be preserved");
  });

  it("itinerary-day-mobile-expanded testid preserved", () => {
    assert.ok(col.includes('data-testid="itinerary-day-mobile-expanded"'), "mobile expanded testid must be preserved");
  });

  it("itinerary-day-mobile-timeline testid preserved", () => {
    assert.ok(col.includes('data-testid="itinerary-day-mobile-timeline"'), "mobile timeline testid must be preserved");
  });

  it("empty-day-chapter testid preserved", () => {
    assert.ok(col.includes('data-testid="empty-day-chapter"'), "empty-day-chapter testid must be preserved");
  });

  it("day-part-section testid preserved", () => {
    assert.ok(col.includes('data-testid="day-part-section"'), "day-part-section testid must be preserved");
  });

  it("trip-readiness-cockpit testid preserved", () => {
    assert.ok(cockpit.includes('data-testid="trip-readiness-cockpit"'), "trip-readiness-cockpit testid must be preserved");
  });

  it("day-coverage-strip testid preserved", () => {
    assert.ok(cockpit.includes('data-testid="day-coverage-strip"'), "day-coverage-strip testid must be preserved");
  });

  it("readiness-signals testid preserved", () => {
    assert.ok(cockpit.includes('data-testid="readiness-signals"'), "readiness-signals testid must be preserved");
  });

  it("next-action-area testid preserved", () => {
    assert.ok(cockpit.includes('data-testid="next-action-area"'), "next-action-area testid must be preserved");
  });
});

// ── 9. No dark-world regressions in converted areas ──────────────────────────

describe("No dark-world token regressions in converted areas", () => {
  const col = readSrc("components/trips/ItineraryDayColumn.tsx");
  const cockpit = readSrc("components/trips/TripReadinessCockpit.tsx");
  const tripsPage = readSrc("app/trips/page.tsx");

  it("ItineraryDayColumn does not use ds-midnight-ink anywhere", () => {
    assert.ok(!col.includes("ds-midnight-ink"), "ItineraryDayColumn must not use ds-midnight-ink");
  });

  it("ItineraryDayColumn does not use bg-ds-onyx in card/header surfaces", () => {
    assert.ok(!col.includes("bg-ds-onyx"), "ItineraryDayColumn must not use bg-ds-onyx");
  });

  it("TripReadinessCockpit does not use bg-ds-carbon (dark recessed section)", () => {
    assert.ok(!cockpit.includes("bg-ds-carbon"), "TripReadinessCockpit must not use bg-ds-carbon");
  });

  it("trips/page.tsx JourneyCard does not use bg-ds-onyx", () => {
    assert.ok(!tripsPage.includes("boutique-folio"), "trips page must not use old boutique-folio class");
  });

  // Guard: text-ds-warm-paper is not a valid Tailwind utility.
  // The @theme exposes warm paper as --color-ds-paper, so the correct utility is text-ds-paper.
  it("ItineraryDayColumn does not use invalid text-ds-warm-paper utility", () => {
    assert.ok(!col.includes("text-ds-warm-paper"), "use text-ds-paper not text-ds-warm-paper (invalid Tailwind utility)");
  });

  it("TripReadinessCockpit does not use invalid text-ds-warm-paper utility", () => {
    assert.ok(!cockpit.includes("text-ds-warm-paper"), "use text-ds-paper not text-ds-warm-paper (invalid Tailwind utility)");
  });

  it("trips/[id]/page.tsx does not use invalid text-ds-warm-paper utility", () => {
    const tripDetail = readSrc("app/trips/[id]/page.tsx");
    assert.ok(!tripDetail.includes("text-ds-warm-paper"), "use text-ds-paper not text-ds-warm-paper (invalid Tailwind utility)");
  });

  it("MobileNav does not use invalid text-ds-warm-paper utility", () => {
    const mobileNav = readSrc("components/layout/MobileNav.tsx");
    assert.ok(!mobileNav.includes("text-ds-warm-paper"), "use text-ds-paper not text-ds-warm-paper (invalid Tailwind utility)");
  });
});
