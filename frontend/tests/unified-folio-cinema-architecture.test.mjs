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
// paper-world card. TripBuilder hits its ceiling on purpose: the Compare Bar,
// the Toast, and the AddNoteModal at the bottom of the file are floating
// dark overlays where cream text is correct.
const paperWorldCreamCeiling = {
  "src/components/trips/TripBuilder.tsx": 19,
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

test("SavedShell (cinema world) uses folio-cinema-collection canonical wrapper", () => {
  assert.match(savedShell, /folio-cinema-collection/);
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
  for (const src of [exploreShell, savedShell, conciergePage]) {
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

test("TripBuilder Add-to day selector is no longer an orphan dark pill on paper", () => {
  const tb = read("src/components/trips/TripBuilder.tsx");
  // The target day selector ("Add to Day 1 · 2026-05-21") was bg-ds-carbon /
  // border-ds-pen-stroke / text-ds-text — fully dark on paper. Now paper.
  assert.match(tb, /bg-ds-linen rounded-xl border border-ds-hairline px-3[^"]*"[\s\S]{0,400}Add to/);
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
