// Stage 3.5 Unified Folio/Cinema UI Architecture — guardrail contracts.
//
// These tests assert the canonical primitives exist and that screenshot-visible
// paper-world surfaces stop mixing cream-text-on-paper class soup. They are
// architecture tests: they protect the world boundary, not the specific
// pixel-level styling. Specific styling lives in CSS classes (globals.css);
// these tests prevent regression to the failure mode where feature files
// build dark-mode class stacks on paper backgrounds.
//
// Failure modes blocked here:
//   • text-ds-text / text-ds-text-secondary / text-ds-text-tertiary on
//     paper-world surfaces (cream text invisible on bone/linen)
//   • bg-ds-onyx / bg-ds-carbon orphan dark cards on paper canvases
//   • Missing canonical Folio*/Cinema* React primitives

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const read = (rel) => readFileSync(path.resolve(root, rel), "utf-8");

// ── 1. Canonical primitives exist ───────────────────────────────────────────

const folio = read("src/components/ui/Folio.tsx");

test("Folio.tsx exports canonical paper-world primitives", () => {
  for (const name of [
    "FolioPage",
    "FolioPanel",
    "FolioCard",
    "FolioSectionHeader",
    "FolioInput",
    "FolioChip",
    "FolioButton",
  ]) {
    assert.match(folio, new RegExp(`export function ${name}\\b`), `missing export ${name}`);
  }
});

test("Folio.tsx exports canonical cinema-world primitives", () => {
  for (const name of ["CinemaPage", "CinemaPanel", "CinemaCard", "CinemaChip"]) {
    assert.match(folio, new RegExp(`export function ${name}\\b`), `missing export ${name}`);
  }
});

test("Folio primitives carry data-folio-world marker for runtime auditability", () => {
  // Every primitive tags its surface with data-folio-world so screenshot
  // diffs and DOM inspection can verify world assignment without re-reading CSS.
  const paperCount = (folio.match(/data-folio-world="paper"/g) || []).length;
  const cinemaCount = (folio.match(/data-folio-world="cinema"/g) || []).length;
  assert.ok(paperCount >= 5, `expected ≥5 paper-world markers, found ${paperCount}`);
  assert.ok(cinemaCount >= 3, `expected ≥3 cinema-world markers, found ${cinemaCount}`);
});

// ── 2. Paper-world surfaces — no cream-text leaks ───────────────────────────

const paperWorldFiles = [
  "src/components/trips/TripBuilder.tsx",
  "src/components/trips/TripIdeasPanel.tsx",
  "src/components/trips/ItineraryDayColumn.tsx",
  "src/components/trips/ItineraryItemCard.tsx",
  "src/components/trips/SearchResultCard.tsx",
  "src/components/dashboard/DashboardClient.tsx",
];

// Per-file ceilings. Anything above the ceiling means cream text leaked into a
// paper-world card. TripBuilder hits its ceiling on purpose: the Compare Bar
// and the Toast at the bottom of the file are floating dark overlays where
// cream text is correct. (Slice 5 converted the AddNoteModal to paper-world,
// dropping the ceiling from 19 to 8.)
const paperWorldCreamCeiling = {
  "src/components/trips/TripBuilder.tsx": 8,
  "src/components/trips/TripIdeasPanel.tsx": 0,
  "src/components/trips/ItineraryDayColumn.tsx": 0,
  "src/components/trips/ItineraryItemCard.tsx": 0,
  "src/components/trips/SearchResultCard.tsx": 0,
  "src/components/dashboard/DashboardClient.tsx": 0,
};

for (const rel of paperWorldFiles) {
  const src = read(rel);
  // text-ds-text-inverse is allowed (dark text on brass buttons).
  const matches = src.match(/text-ds-text(?:-secondary|-tertiary)?(?![\w-])/g) || [];
  const ceiling = paperWorldCreamCeiling[rel];
  test(`paper-world file has minimal cream-on-paper leaks: ${rel}`, () => {
    assert.ok(
      matches.length <= ceiling,
      `${rel} has ${matches.length} text-ds-text* uses (ceiling ${ceiling}). Paper-world surfaces must use text-ds-folio-ink / -soft / -mist; ceiling >0 only for files with floating dark overlays.`,
    );
  });
}

// Tight check: TripBuilder candidate-card region (lines 1–2520, before the
// Compare Bar/Toast/AddNoteModal floating dark overlays) must be 100% clean
// of cream text. This is the region the user saw rendering invisibly on paper.
test("TripBuilder candidate-card region (pre-overlay) has zero cream text", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  const candidateRegion = tb.split("\n").slice(0, 2520).join("\n");
  const leaks = candidateRegion.match(/text-ds-text(?:-secondary|-tertiary)?(?![\w-])/g) || [];
  assert.equal(
    leaks.length,
    0,
    `TripBuilder candidate-card region (lines 1–2520) contains ${leaks.length} cream-text leaks. All paper-world candidate cards must use folio-ink tokens.`,
  );
});

// ── 3. Paper-world surfaces use folio-ink text tokens ───────────────────────

for (const rel of paperWorldFiles) {
  const src = read(rel);
  test(`paper-world file uses folio-ink token: ${rel}`, () => {
    assert.match(
      src,
      /text-ds-folio-ink(?:-soft|-mist)?(?![\w-])/,
      `${rel} must use text-ds-folio-ink / -soft / -mist for paper-world text hierarchy`,
    );
  });
}

// ── 4. No orphan dark cards in paper-world surfaces ─────────────────────────
//
// "Orphan dark card" = bg-ds-onyx / bg-ds-carbon used as a standalone card
// inside a paper page. Floating overlays (toast bottom-right, compare bar)
// are allowed because their dark surface is deliberate UI separation, not a
// paper/cinema confusion.

const orphanCheckFiles = [
  "src/components/trips/TripIdeasPanel.tsx",
  "src/components/trips/ItineraryDayColumn.tsx",
  "src/components/trips/ItineraryItemCard.tsx",
  "src/components/trips/SearchResultCard.tsx",
];

for (const rel of orphanCheckFiles) {
  const src = read(rel);
  test(`no orphan dark cards in paper-world surface: ${rel}`, () => {
    assert.doesNotMatch(
      src,
      /\bbg-ds-onyx\b/,
      `${rel} must not use bg-ds-onyx — paper-world cards use bg-ds-bone/linen or folio-paper-card`,
    );
    assert.doesNotMatch(
      src,
      /\bbg-ds-carbon\b/,
      `${rel} must not use bg-ds-carbon — paper-world secondary surfaces use bg-ds-linen`,
    );
  });
}

// ── 5. Cinema-world surfaces — use cream text + cinema primitives ───────────

const exploreShell = read("src/components/explore/ExploreShell.tsx");
const savedShell = read("src/components/saved/SavedShell.tsx");
const conciergePage = read("src/components/concierge/ConciergePage.tsx");

test("ExploreShell (cinema world) uses folio-cinema-lounge canonical wrapper", () => {
  assert.match(exploreShell, /folio-cinema-lounge/);
});

// Saved was reclassified from cinema to the PAPER world (Private Folio v1):
// per Design Implementation Contract §26 (Saved Ideas = paper/scrapbook tone),
// Saved is a light folio resting on a warm desk, not another dark room.
test("SavedShell (paper world) uses folio-private-desk + data-folio-world=paper", () => {
  assert.match(savedShell, /folio-private-desk/);
  assert.match(savedShell, /data-folio-world="paper"/);
});

test("ConciergePage (cinema world) uses folio-cinema-desk canonical wrapper", () => {
  assert.match(conciergePage, /folio-cinema-desk/);
});

// ── 6. Cinema-world surfaces are not allowed to use folio-paper-* primitives
//      inside their main surface scope ──────────────────────────────────────

test("cinema-world files do not adopt paper-world surface primitives", () => {
  // ExploreShell, SavedShell, ConciergePage should not wrap themselves in
  // folio-paper-panel / folio-paper-card on the OUTER cinema canvas.
  // (Search result cards inside Explore intentionally remain dark via the
  // Card primitive `tone="dark"`.)
  // SavedShell is paper-world now and is intentionally excluded here.
  for (const src of [exploreShell, conciergePage]) {
    assert.doesNotMatch(
      src,
      /folio-paper-panel\b/,
      "cinema-world shell uses paper-panel primitive (mixed world)",
    );
  }
});

// ── 7. PR #431 protected paths — autocomplete portal + round-trip seam ──────
//
// PR #431 hardened CityAutocomplete (createPortal) and round-trip leg add
// logic. This PR is a visual architecture refactor and must not touch those
// behavior paths — the test guards against accidental edits to that seam.

test("PR #431: CityAutocomplete continues to use createPortal", () => {
  const auto = read("src/components/ui/CityAutocomplete.tsx");
  assert.match(auto, /createPortal/);
});

test("PR #431: addRoundTripLegToDay continues to live in api.ts", () => {
  const api = read("src/lib/api.ts");
  assert.match(api, /addRoundTripLegToDay/);
});

test("PR #431: handleAddRoundTripToItinerary continues to live in TripBuilder.tsx", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  assert.match(tb, /handleAddRoundTripToItinerary/);
});

test("PR #431: ItineraryItemCard preserves explicit one-way detection", () => {
  const iic = read("src/components/trips/ItineraryItemCard.tsx");
  // The explicit one-way detection guard lives in this file. Specific token
  // names ("is_round_trip" / "leg_of_round_trip") locked by PR #431.
  assert.match(iic, /is_round_trip|isRoundTrip/);
});

// ── 8. Screenshot-driven surface coverage — visible bugs are fixed ──────────

test("TripBuilder Round-Trip card no longer uses invisible cream-on-paper text", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  // The "Round-Trip" header line and "Outbound + Return pair" subtitle
  // previously rendered as text-ds-text on bg-ds-bone — invisible.
  // Verify the header line now uses folio-ink token.
  assert.match(tb, /text-ds-folio-ink leading-tight">Round-Trip</);
});

test("TripBuilder Add-to day selector is removed (canonical active day owns the target)", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  // The target-day dropdown ("Add to Day 1 · 2026-05-21") is gone in the Journey
  // Desk patch — the Dayboard/itinerary active day is the single source, used by
  // the "Add to Day X" button. No orphan dark pill (and no dropdown) on paper.
  assert.ok(
    !tb.includes('focus-within:outline-ds-accent'),
    "the redundant Add-to target-day dropdown wrapper must be removed",
  );
});

test("TripBuilder Sort pills are paper-world chips (not orphan dark)", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  // SortControl unselected variant used to be bg-ds-carbon text-ds-text-secondary
  // on paper. Now uses paper-world tokens.
  assert.match(tb, /bg-ds-linen text-ds-folio-ink-soft border-ds-hairline/);
});

test("TripIdeasPanel chips use paper-world tokens (Must-do / Maybe / Skip readable on paper)", () => {
  const tip = read("src/components/trips/TripIdeasPanel.tsx");
  // The unselected chip variant previously rendered as text-ds-text-tertiary
  // with a near-invisible ring-ds-pen-stroke/40 — now uses paper-world tokens.
  assert.match(tip, /text-ds-folio-ink-soft ring-ds-hairline/);
});

// ── 9. Canonical Card primitive still owns explore cards (cinema) ───────────

test("Cinema-world AttractionCard continues to use Card primitive tone='dark'", () => {
  const att = read("src/components/explore/AttractionExploreFlow.tsx");
  assert.match(att, /Card tone="dark"/);
});

test("Cinema-world RestaurantCard continues to use Card primitive tone='dark'", () => {
  const rest = read("src/components/explore/RestaurantExploreFlow.tsx");
  assert.match(rest, /tone="dark"/);
});

// ── 10. CSS primitives back the React primitives — no dangling class names ──
//
// FolioPage emits className "folio-page" and CinemaPage emits "cinema-page".
// If those classes don't exist in globals.css, the primitive renders to a
// no-op selector — the unified architecture would have a hole. Guard.

test("globals.css defines .folio-page so FolioPage primitive renders to a real class", () => {
  const css = read("src/app/globals.css");
  assert.match(
    css,
    /\.folio-page\s*\{/,
    "globals.css must declare .folio-page (FolioPage primitive emits this class)",
  );
});

test("globals.css defines .cinema-page so CinemaPage primitive renders to a real class", () => {
  const css = read("src/app/globals.css");
  assert.match(
    css,
    /\.cinema-page\s*\{/,
    "globals.css must declare .cinema-page (CinemaPage primitive emits this class)",
  );
});

// ── 11. Real adoption: feature files import + use the canonical primitives ──
//
// A primitive layer that no one imports is a no-op. These tests enforce that
// real screenshot-visible paper-world surfaces actually pull from Folio.tsx,
// not just live next to it.

const folioImporters = [
  "src/components/dashboard/DashboardClient.tsx",
  "src/components/trips/TripIdeasPanel.tsx",
  "src/components/trips/ItineraryDayColumn.tsx",
  "src/components/trips/TripBuilder.tsx",
  "src/app/trips/page.tsx",
];

for (const rel of folioImporters) {
  const src = read(rel);
  test(`feature file imports from @/components/ui/Folio: ${rel}`, () => {
    assert.match(
      src,
      /from\s+["']@\/components\/ui\/Folio["']/,
      `${rel} must import at least one primitive from the canonical Folio layer`,
    );
  });
}

test("DashboardClient adopts FolioPanel on ConciergeEntry", () => {
  const src = read("src/components/dashboard/DashboardClient.tsx");
  assert.match(src, /<FolioPanel\b[^>]*concierge-advisor-desk/);
});

test("TripIdeasPanel adopts FolioPanel on the outer panel and FolioCard on IdeaCard", () => {
  const src = read("src/components/trips/TripIdeasPanel.tsx");
  assert.match(src, /<FolioPanel\b[^>]*trip-ideas-panel-root/);
  assert.match(src, /<FolioCard\b[^>]*trip-idea-card/);
});

test("TripIdeasPanel adopts FolioButton on Show more / Show less buttons", () => {
  const src = read("src/components/trips/TripIdeasPanel.tsx");
  const matches = src.match(/<FolioButton\b/g) || [];
  assert.ok(
    matches.length >= 2,
    `TripIdeasPanel must adopt FolioButton on at least 2 places (Show more, Show less). Found ${matches.length}.`,
  );
});

test("ItineraryDayColumn adopts FolioCard on day-chapter-frame", () => {
  const src = read("src/components/trips/ItineraryDayColumn.tsx");
  assert.match(src, /<FolioCard\b[^>]*day-chapter-frame/);
});

test("TripBuilder adopts FolioPanel on the Activities/research panel", () => {
  const src = read("src/components/trips/TripBuilder.tsx");
  assert.match(src, /<FolioPanel\b[^>]*trip-build-activities-panel/);
});

test("trips/page.tsx adopts the FolioCard primitive on the bound-volume card", () => {
  // Reading Room: the bound-volume JourneyCard is the canonical paper card of
  // My Journeys and is composed from the FolioCard primitive (real adoption on
  // the most screenshot-visible, repeated paper surface). The empty state is the
  // empty shelf (one primary + quiet links), so it no longer holds action cards.
  const src = read("src/app/trips/page.tsx");
  const matches = src.match(/<FolioCard\b/g) || [];
  assert.ok(
    matches.length >= 1,
    `trips/page.tsx must adopt the FolioCard primitive on the bound-volume card. Found ${matches.length}.`,
  );
});

// ── 12. No repeated raw paper-card class stack in migrated surfaces ─────────
//
// After adoption, raw `folio-paper-card` / `folio-paper-panel` literals should
// appear only where a primitive isn't appropriate (legacy or one-off layouts).
// Migrated files should have ≤1 raw use each — if they have more, the primitive
// hasn't replaced the local stack.

const rawCeiling = {
  "src/components/trips/TripIdeasPanel.tsx": { "folio-paper-panel": 0, "folio-paper-card": 1 },
  "src/components/dashboard/DashboardClient.tsx": { "folio-paper-panel": 0 },
};

for (const [rel, limits] of Object.entries(rawCeiling)) {
  const src = read(rel);
  for (const [literal, max] of Object.entries(limits)) {
    const count = (src.match(new RegExp(literal.replace(/-/g, "-"), "g")) || []).length;
    test(`${rel}: raw "${literal}" class usage ≤ ${max} (primitive should replace it)`, () => {
      assert.ok(
        count <= max,
        `${rel} has ${count} raw "${literal}" uses (ceiling ${max}). Adopt the React primitive instead.`,
      );
    });
  }
}

// ── 13. Slice 5: Planning-world AddNoteModal is paper-world, not orphan dark ─
//
// The Add Note modal lives inside Trip Itinerary / planning context (paper
// world). Slice 5 converted it from the dark onyx/carbon stack to a paper
// surface so it stops reading as a foreign dark slab inside the warm
// itinerary canvas. These tests guard against regression to dark classes.

test("AddNoteModal panel is tagged as paper-world", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  const addNoteIdx = tb.indexOf("function AddNoteModal");
  assert.ok(addNoteIdx > 0, "AddNoteModal not found");
  const modalSrc = tb.slice(addNoteIdx);
  assert.match(
    modalSrc,
    /data-testid="add-note-modal-panel"[^>]*data-folio-world="paper"|data-folio-world="paper"[^>]*data-testid="add-note-modal-panel"/,
    "AddNoteModal inner panel must carry data-folio-world=\"paper\"",
  );
});

test("AddNoteModal does not use orphan dark surface classes", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  const addNoteIdx = tb.indexOf("function AddNoteModal");
  const modalSrc = tb.slice(addNoteIdx);
  // The modal panel + inputs must not reach back to bg-ds-onyx / bg-ds-carbon /
  // border-ds-pen-stroke / text-ds-text — those are cinema-world tokens and
  // would re-introduce the dark planning-modal bug.
  for (const forbidden of [
    /\bbg-ds-onyx\b/,
    /\bbg-ds-carbon\b/,
    /\bborder-ds-pen-stroke\b/,
  ]) {
    assert.doesNotMatch(
      modalSrc,
      forbidden,
      `AddNoteModal must not use ${forbidden} — planning-world modals are paper, not dark`,
    );
  }
});

test("AddNoteModal title and inputs use paper-world tokens", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  const addNoteIdx = tb.indexOf("function AddNoteModal");
  const modalSrc = tb.slice(addNoteIdx);
  assert.match(modalSrc, /text-ds-folio-ink/, "AddNoteModal heading must use folio-ink text");
  assert.match(modalSrc, /folio-input/, "AddNoteModal inputs must use the canonical folio-input class");
  assert.match(modalSrc, /<FolioButton/, "AddNoteModal save/cancel must use the canonical FolioButton primitive");
});

test("AddNoteModal preserves PR #441 contract: testids, save/cancel, focus, validation", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  const addNoteIdx = tb.indexOf("function AddNoteModal");
  const modalSrc = tb.slice(addNoteIdx);
  // Behavior contract — must not be broken by the visual conversion.
  for (const testid of [
    'data-testid="add-note-modal"',
    'data-testid="add-note-title-input"',
    'data-testid="add-note-description-input"',
    'data-testid="add-note-save-btn"',
    'data-testid="add-note-cancel-btn"',
  ]) {
    assert.ok(modalSrc.includes(testid), `AddNoteModal must preserve ${testid}`);
  }
  assert.match(modalSrc, /titleRef\.current\?\.focus\(\)/, "AddNoteModal must preserve title focus-on-mount");
  assert.match(modalSrc, /disabled=\{!title\.trim\(\)\}/, "AddNoteModal save must remain disabled until title is non-empty");
});

// ── 14. Slice 5: Cinema-world page geometry is consistent across routes ─────
//
// Explore (lounge), Saved (collection), Concierge (desk) all live in the
// cinema world. They must share the same intentional container geometry —
// rounded frame, brass hairline, atmospheric shadow — so the three routes
// read as one architectural family on mobile. Slice 5 brought collection
// and desk in line with lounge.

const cssSrc = read("src/app/globals.css");

function classBlock(css, className) {
  const re = new RegExp(`\\.${className}\\s*\\{([\\s\\S]*?)\\}`);
  const match = css.match(re);
  return match ? match[1] : "";
}

for (const className of [
  "folio-cinema-lounge",
  "folio-cinema-collection",
  "folio-cinema-desk",
]) {
  const block = classBlock(cssSrc, className);
  test(`cinema-world shell .${className} declares unified rounded-frame geometry`, () => {
    assert.ok(block.length > 0, `globals.css must define .${className}`);
    assert.match(block, /border-radius:\s*1rem/, `.${className} must use the shared 1rem rounded-frame radius`);
    assert.match(block, /border:\s*1px solid rgba\(197, 148, 77/, `.${className} must use the shared brass hairline border`);
    assert.match(block, /box-shadow:[\s\S]*rgba\(0, 0, 0/, `.${className} must use the shared atmospheric shadow`);
  });
}
