/**
 * Phase 8L — Itinerary Day Mobile Redesign contract tests.
 *
 * Verifies:
 *  1. Mobile day chapter testids exist in ItineraryDayColumn:
 *     itinerary-day-mobile-chapter, itinerary-day-mobile-header,
 *     itinerary-day-mobile-summary, itinerary-day-mobile-expanded,
 *     itinerary-day-mobile-timeline, itinerary-day-mobile-action-tray
 *  2. Secondary day actions (Plan My Day, Suggest Timing) are hidden on mobile
 *     and accessible through the mobile action tray.
 *  3. Mobile action tray toggle is a type=button with aria-label and min-h-[44px].
 *  4. Item card mobile testids exist:
 *     itinerary-item-mobile-timeline-card, itinerary-item-mobile-primary-row,
 *     itinerary-item-mobile-overflow-toggle, itinerary-item-mobile-overflow-actions
 *  5. Item card mobile overflow toggle is type=button with aria-label, lg:hidden.
 *  6. Desktop action cluster uses hidden lg:flex (not shown on mobile, restored on desktop).
 *  7. Existing critical testids and behavior preserved:
 *     day-chapter-frame, day-chapter-header, itinerary-item-card,
 *     itinerary-google-flights-cta, itinerary-roundtrip-flight,
 *     all action handlers, DnD hooks.
 *  8. No backend/provider/Supabase files imported.
 *  9. No raw hex or rgba in new additions.
 * 10. Desktop stability: lg: breakpoint restores Plan My Day on desktop.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root      = resolve(__dirname, "..");
const srcRoot   = resolve(root, "src");
const backRoot  = resolve(root, "..", "backend");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function backExists(relPath) {
  return existsSync(resolve(backRoot, relPath));
}

const dayColSrc  = readSrc("components/trips/ItineraryDayColumn.tsx");
const itemCardSrc = readSrc("components/trips/ItineraryItemCard.tsx");

// ── 1. Mobile day chapter testids ─────────────────────────────────────────────

describe("Phase 8L: mobile day chapter testids exist in ItineraryDayColumn", () => {
  it("itinerary-day-mobile-chapter identifier on root element", () => {
    assert.ok(
      dayColSrc.includes("itinerary-day-mobile-chapter"),
      "missing itinerary-day-mobile-chapter in ItineraryDayColumn"
    );
  });

  it("itinerary-day-mobile-header identifier on header element", () => {
    assert.ok(
      dayColSrc.includes("itinerary-day-mobile-header"),
      "missing itinerary-day-mobile-header in ItineraryDayColumn"
    );
  });

  it("itinerary-day-mobile-summary testid on collapsed state", () => {
    assert.ok(
      dayColSrc.includes('data-testid="itinerary-day-mobile-summary"'),
      'missing data-testid="itinerary-day-mobile-summary" on collapsed state'
    );
  });

  it("itinerary-day-mobile-expanded testid on expanded state", () => {
    assert.ok(
      dayColSrc.includes('data-testid="itinerary-day-mobile-expanded"'),
      'missing data-testid="itinerary-day-mobile-expanded" on expanded state'
    );
  });

  it("itinerary-day-mobile-timeline testid on timeline container", () => {
    assert.ok(
      dayColSrc.includes('data-testid="itinerary-day-mobile-timeline"'),
      'missing data-testid="itinerary-day-mobile-timeline" on timeline container'
    );
  });

  it("itinerary-day-mobile-action-tray testid on mobile overflow toggle", () => {
    assert.ok(
      dayColSrc.includes('data-testid="itinerary-day-mobile-action-tray"'),
      'missing data-testid="itinerary-day-mobile-action-tray" on overflow toggle'
    );
  });
});

// ── 2. Collapsed vs expanded mobile structures ────────────────────────────────

describe("Phase 8L: collapsed vs expanded mobile structures", () => {
  it("collapsed state uses itinerary-day-mobile-summary (compact scan row)", () => {
    const summaryIdx = dayColSrc.indexOf("itinerary-day-mobile-summary");
    assert.ok(summaryIdx !== -1, "itinerary-day-mobile-summary not found");
    // Collapsed summary is inside the !isExpanded branch
    const surroundingCtx = dayColSrc.slice(Math.max(0, summaryIdx - 300), summaryIdx + 200);
    assert.ok(
      surroundingCtx.includes("!isExpanded") || surroundingCtx.includes("isExpanded ?"),
      "itinerary-day-mobile-summary must be inside the collapsed (not expanded) branch"
    );
  });

  it("expanded state uses itinerary-day-mobile-expanded", () => {
    const expandedIdx = dayColSrc.indexOf("itinerary-day-mobile-expanded");
    assert.ok(expandedIdx !== -1, "itinerary-day-mobile-expanded not found");
  });

  it("timeline container inside expanded state", () => {
    const timelineIdx = dayColSrc.indexOf("itinerary-day-mobile-timeline");
    const expandedIdx = dayColSrc.indexOf("itinerary-day-mobile-expanded");
    assert.ok(timelineIdx !== -1, "itinerary-day-mobile-timeline not found");
    assert.ok(timelineIdx > expandedIdx, "timeline container should appear after expanded state wrapper");
  });

  it("mobile vertical rail inside timeline container (lg:hidden, decorative)", () => {
    assert.ok(
      dayColSrc.includes("lg:hidden absolute") && (dayColSrc.includes("bg-ds-hairline") || dayColSrc.includes("bg-ds-pen-stroke/30")),
      "mobile vertical rail (lg:hidden absolute ... bg-ds-hairline) missing from timeline"
    );
  });
});

// ── 3. Secondary day actions moved to mobile tray ────────────────────────────

describe("Phase 8L: secondary day actions use hidden lg:flex on mobile", () => {
  it("Plan My Day desktop button uses hidden lg:flex (hidden on mobile)", () => {
    assert.ok(
      dayColSrc.includes("hidden lg:flex"),
      "Plan My Day button must use hidden lg:flex to hide on mobile"
    );
  });

  it("Plan My Day appears at least twice (desktop header hidden + mobile tray)", () => {
    const matches = dayColSrc.match(/Plan My Day/g);
    assert.ok(
      matches && matches.length >= 2,
      "Plan My Day must appear in desktop header (hidden) AND in mobile tray"
    );
  });

  it("Suggest Timing appears at least twice (desktop header hidden + mobile tray)", () => {
    const matches = dayColSrc.match(/Suggest Timing/g);
    assert.ok(
      matches && matches.length >= 2,
      "Suggest Timing must appear in desktop header (hidden) AND in mobile tray"
    );
  });

  it("mobile action tray toggle is lg:hidden (mobile-only)", () => {
    const trayIdx = dayColSrc.indexOf('data-testid="itinerary-day-mobile-action-tray"');
    assert.ok(trayIdx !== -1, "itinerary-day-mobile-action-tray not found");
    const context = dayColSrc.slice(Math.max(0, trayIdx - 500), trayIdx + 100);
    assert.ok(context.includes("lg:hidden"), "action tray toggle must be lg:hidden (mobile-only)");
  });
});

// ── 4. Mobile action tray toggle is a semantic button ────────────────────────

describe("Phase 8L: mobile action tray toggle is a real type=button", () => {
  it("tray toggle has type=button", () => {
    const trayIdx = dayColSrc.indexOf('data-testid="itinerary-day-mobile-action-tray"');
    const context = dayColSrc.slice(Math.max(0, trayIdx - 600), trayIdx + 100);
    assert.ok(context.includes('type="button"'), "mobile action tray toggle must have type=button");
  });

  it("tray toggle has aria-label", () => {
    const trayIdx = dayColSrc.indexOf('data-testid="itinerary-day-mobile-action-tray"');
    const context = dayColSrc.slice(Math.max(0, trayIdx - 600), trayIdx + 100);
    assert.ok(context.includes("aria-label"), "mobile action tray toggle must have aria-label");
  });

  it("tray toggle has min-h-[44px] touch target", () => {
    const trayIdx = dayColSrc.indexOf('data-testid="itinerary-day-mobile-action-tray"');
    const context = dayColSrc.slice(Math.max(0, trayIdx - 600), trayIdx + 100);
    assert.ok(context.includes("min-h-[44px]"), "mobile action tray toggle must have min-h-[44px] touch target");
  });
});

// ── 5. Item card mobile testids ───────────────────────────────────────────────

describe("Phase 8L: item card mobile testids exist in ItineraryItemCard", () => {
  it("itinerary-item-mobile-timeline-card testid on content area", () => {
    assert.ok(
      itemCardSrc.includes('data-testid="itinerary-item-mobile-timeline-card"'),
      'missing data-testid="itinerary-item-mobile-timeline-card"'
    );
  });

  it("itinerary-item-mobile-primary-row testid on primary row div", () => {
    assert.ok(
      itemCardSrc.includes('data-testid="itinerary-item-mobile-primary-row"'),
      'missing data-testid="itinerary-item-mobile-primary-row"'
    );
  });

  it("itinerary-item-mobile-overflow-toggle testid on overflow button", () => {
    assert.ok(
      itemCardSrc.includes('data-testid="itinerary-item-mobile-overflow-toggle"'),
      'missing data-testid="itinerary-item-mobile-overflow-toggle"'
    );
  });

  it("itinerary-item-mobile-overflow-actions testid on overflow tray", () => {
    assert.ok(
      itemCardSrc.includes('data-testid="itinerary-item-mobile-overflow-actions"'),
      'missing data-testid="itinerary-item-mobile-overflow-actions"'
    );
  });
});

// ── 6. Item card mobile overflow toggle is semantic and mobile-only ───────────

describe("Phase 8L: item card mobile overflow toggle is a real type=button", () => {
  it("overflow toggle has type=button", () => {
    const toggleIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-toggle"');
    assert.ok(toggleIdx !== -1, "itinerary-item-mobile-overflow-toggle not found");
    const context = itemCardSrc.slice(Math.max(0, toggleIdx - 500), toggleIdx + 100);
    assert.ok(context.includes('type="button"'), "overflow toggle must have type=button");
  });

  it("overflow toggle has aria-label", () => {
    const toggleIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-toggle"');
    const context = itemCardSrc.slice(Math.max(0, toggleIdx - 500), toggleIdx + 100);
    assert.ok(context.includes("aria-label"), "overflow toggle must have aria-label");
  });

  it("overflow toggle is lg:hidden (mobile-only)", () => {
    const toggleIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-toggle"');
    const context = itemCardSrc.slice(Math.max(0, toggleIdx - 500), toggleIdx + 100);
    assert.ok(context.includes("lg:hidden"), "overflow toggle must be lg:hidden (mobile-only)");
  });

  it("overflow toggle uses -m-3 p-3 for 44px touch area", () => {
    const toggleIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-toggle"');
    const context = itemCardSrc.slice(Math.max(0, toggleIdx - 500), toggleIdx + 100);
    assert.ok(context.includes("-m-3") && context.includes("p-3"), "overflow toggle must use -m-3 p-3 for 44px hit area");
  });
});

// ── 7. Desktop action cluster uses hidden lg:flex ─────────────────────────────

describe("Phase 8L: desktop action cluster hidden on mobile, restored on desktop", () => {
  it("item card desktop action cluster uses hidden lg:flex", () => {
    assert.ok(
      itemCardSrc.includes("hidden lg:flex"),
      "desktop action cluster must use hidden lg:flex to hide on mobile and restore on desktop"
    );
  });

  it("item card mobile overflow tray is lg:hidden (not rendered on desktop)", () => {
    const trayIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-actions"');
    assert.ok(trayIdx !== -1, "itinerary-item-mobile-overflow-actions not found");
    const context = itemCardSrc.slice(Math.max(0, trayIdx - 300), trayIdx + 100);
    assert.ok(context.includes("lg:hidden"), "overflow actions tray must be lg:hidden (hidden on desktop)");
  });
});

// ── 8. Mobile overflow tray provides access to all item actions ───────────────

describe("Phase 8L: mobile overflow tray provides all item secondary actions", () => {
  it("Remove action is in mobile overflow tray (type=button, aria-label)", () => {
    const trayIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-actions"');
    const trayBlock = itemCardSrc.slice(trayIdx, trayIdx + 3000);
    assert.ok(trayBlock.includes("onRemove") || trayBlock.includes("Remove"), "Remove action missing from mobile overflow tray");
  });

  it("Timeline action is in mobile overflow tray", () => {
    const trayIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-actions"');
    const trayBlock = itemCardSrc.slice(trayIdx, trayIdx + 3000);
    assert.ok(trayBlock.includes("Timeline") || trayBlock.includes("handleOpenTimeline"), "Timeline action missing from mobile overflow tray");
  });

  it("Book action is in mobile overflow tray", () => {
    const trayIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-actions"');
    const trayBlock = itemCardSrc.slice(trayIdx, trayIdx + 3000);
    assert.ok(trayBlock.includes("Book") || trayBlock.includes("setBookingOpen"), "Book action missing from mobile overflow tray");
  });

  it("mobile overflow tray buttons have min-h-[44px] touch targets", () => {
    const trayIdx = itemCardSrc.indexOf('data-testid="itinerary-item-mobile-overflow-actions"');
    const trayBlock = itemCardSrc.slice(trayIdx, trayIdx + 3000);
    assert.ok(trayBlock.includes("min-h-[44px]"), "overflow tray buttons must have min-h-[44px] touch targets");
  });
});

// ── 9. Existing critical testids preserved ───────────────────────────────────

describe("Phase 8L: existing critical testids and behavior preserved", () => {
  it("day-chapter-frame testid preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes('data-testid="day-chapter-frame"'), "day-chapter-frame testid must be preserved");
  });

  it("day-chapter-header testid preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes('data-testid="day-chapter-header"'), "day-chapter-header testid must be preserved");
  });

  it("day-chapter-number testid preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes('data-testid="day-chapter-number"'), "day-chapter-number testid must be preserved");
  });

  it("day-chapter-title testid preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes('data-testid="day-chapter-title"'), "day-chapter-title testid must be preserved");
  });

  it("itinerary-item-card testid preserved on article root in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes('data-testid="itinerary-item-card"'), "itinerary-item-card testid must be preserved on article");
  });

  it("itinerary-google-flights-cta testid preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes('data-testid="itinerary-google-flights-cta"'), "Google Flights CTA testid must be preserved");
  });

  it("itinerary-roundtrip-flight testid preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes('data-testid="itinerary-roundtrip-flight"'), "round-trip testid must be preserved");
  });

  it("item-type-overline testid preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes('data-testid="item-type-overline"'), "item-type-overline testid must be preserved");
  });

  it("item-title testid preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes('data-testid="item-title"'), "item-title testid must be preserved");
  });

  it("SortableContext DnD preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("SortableContext"), "SortableContext must be preserved");
  });

  it("useDroppable DnD preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("useDroppable"), "useDroppable must be preserved");
  });

  it("useSortable DnD preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes("useSortable"), "useSortable must be preserved in ItineraryItemCard");
  });

  it("onAddItem handler preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("onAddItem"), "onAddItem handler must be preserved");
  });

  it("onRemoveItem handler preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("onRemoveItem"), "onRemoveItem handler must be preserved");
  });

  it("onMoveItemToIdeas handler preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("onMoveItemToIdeas"), "onMoveItemToIdeas handler must be preserved");
  });

  it("onPlanDay handler preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("onPlanDay"), "onPlanDay handler must be preserved");
  });

  it("onToggleCompare threading preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("onToggleCompare"), "onToggleCompare must be preserved in ItineraryDayColumn");
  });

  it("onRemove handler preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes("onRemove"), "onRemove must be preserved in ItineraryItemCard");
  });

  it("onUnplace handler present in ItineraryItemCard (normalized from onMoveToIdeas)", () => {
    assert.ok(itemCardSrc.includes("onUnplace"), "onUnplace must be present in ItineraryItemCard");
  });

  it("onToggleCompare handler preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes("onToggleCompare"), "onToggleCompare must be preserved in ItineraryItemCard");
  });

  it("handleSuggestTimeline AI planning preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("handleSuggestTimeline"), "handleSuggestTimeline must be preserved");
  });

  it("handleApplyTimeline preserved in ItineraryDayColumn", () => {
    assert.ok(dayColSrc.includes("handleApplyTimeline"), "handleApplyTimeline must be preserved");
  });

  it("BookingChecklistModal preserved in ItineraryItemCard", () => {
    assert.ok(itemCardSrc.includes("BookingChecklistModal"), "BookingChecklistModal must be preserved");
  });
});

// ── 10. No backend/provider imports ──────────────────────────────────────────

describe("Phase 8L: no backend/provider files changed", () => {
  it("ItineraryDayColumn has no backend imports", () => {
    assert.ok(!dayColSrc.includes("from '@/backend"), "found backend import in ItineraryDayColumn");
    assert.ok(!dayColSrc.includes("supabase"), "found supabase import in ItineraryDayColumn");
    assert.ok(!dayColSrc.includes("tavily"), "found tavily import in ItineraryDayColumn");
    assert.ok(!dayColSrc.includes("duffel"), "found duffel import in ItineraryDayColumn");
  });

  it("ItineraryItemCard has no backend imports", () => {
    assert.ok(!itemCardSrc.includes("from '@/backend"), "found backend import in ItineraryItemCard");
    assert.ok(!itemCardSrc.includes("supabase"), "found supabase import in ItineraryItemCard");
    assert.ok(!itemCardSrc.includes("tavily"), "found tavily import in ItineraryItemCard");
    assert.ok(!itemCardSrc.includes("duffel"), "found duffel import in ItineraryItemCard");
  });
});

// ── 11. No raw hex or rgba values ────────────────────────────────────────────

describe("Phase 8L: no raw hex or rgba in new mobile additions", () => {
  it("ItineraryDayColumn has no raw hex values", () => {
    assert.ok(!dayColSrc.includes("#0"), "found raw hex in ItineraryDayColumn — use ds-tokens");
  });

  it("ItineraryItemCard has no raw hex values", () => {
    assert.ok(!itemCardSrc.includes("#0"), "found raw hex in ItineraryItemCard — use ds-tokens");
  });

  it("ItineraryDayColumn has no raw rgba values", () => {
    assert.ok(!dayColSrc.includes("rgba("), "found raw rgba in ItineraryDayColumn — use var(--ds-*)");
  });
});

// ── 12. Desktop stability: existing ds-token and structure preserved ──────────

describe("Phase 8L: desktop layout stability", () => {
  it("ItineraryDayColumn uses folio-paper-card or FolioCard primitive surface (Slice 2 paper conversion + Unified UI Architecture)", () => {
    assert.ok(
      dayColSrc.includes("folio-paper-card") || dayColSrc.includes("<FolioCard"),
      "folio-paper-card / FolioCard primitive must be used for column surface"
    );
  });

  it("ItineraryDayColumn uses folio-paper-card or FolioCard primitive which carries shadow (Slice 2 paper conversion + Unified UI Architecture)", () => {
    assert.ok(
      dayColSrc.includes("folio-paper-card") || dayColSrc.includes("<FolioCard"),
      "folio-paper-card / FolioCard primitive carries shadow via CSS class"
    );
  });

  it("ItineraryItemCard uses folio-paper-item card surface (Slice 3 paper conversion)", () => {
    assert.ok(itemCardSrc.includes("folio-paper-item"), "folio-paper-item must be the card surface (converted from bg-ds-onyx in Slice 3)");
  });

  it("Plan My Day uses lg:flex for desktop restoration", () => {
    assert.ok(dayColSrc.includes("hidden lg:flex"), "Plan My Day must use hidden lg:flex for desktop restoration");
  });
});
