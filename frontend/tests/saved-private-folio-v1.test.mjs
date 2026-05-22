/**
 * Saved Private Folio v1 — light paper-folio surface contract.
 *
 * Saved is reclassified from the dark cinema world to the PAPER world: a light
 * folio resting on a warm desk (Design Implementation Contract §26). This suite
 * locks the NEW behaviours added in this slice — source labels, why-it-mattered,
 * client-side compare (places only, max 4), the dedicated flight card, and the
 * disabled (not faked) Day grouping — plus the honesty constraints.
 *
 * Source-grep tests (no DOM) — consistent with the rest of tests/.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const read = (p) => readFileSync(new URL(`../${p}`, import.meta.url), "utf8");
const savedShell = read("src/components/saved/SavedShell.tsx");
const appShell = read("src/components/layout/AppShell.tsx");
const globals = read("src/app/globals.css");

// ── Paper-world identity ─────────────────────────────────────────────────────

test("SavedShell is the paper-world folio desk (not a dark room)", () => {
  assert.match(savedShell, /folio-private-desk/);
  assert.match(savedShell, /data-folio-world="paper"/);
  assert.match(savedShell, /folio-private-folio/);
  assert.match(savedShell, /folio-private-meridian/);
  assert.doesNotMatch(savedShell, /folio-cinema-collection/);
  assert.doesNotMatch(savedShell, /folio-collection-card/);
});

test("Private Folio framing copy preserved", () => {
  assert.ok(savedShell.includes("Private Folio"), 'eyebrow must read "Private Folio"');
  assert.ok(savedShell.includes("Places you"), 'heading must read "Places you’ve kept"');
});

test("globals.css defines the folio primitives with design tokens (no raw hex)", () => {
  for (const cls of [
    ".folio-private-desk",
    ".folio-private-folio",
    ".folio-private-meridian",
    ".folio-dossier-card",
    ".folio-dossier-plate",
    ".folio-flight-card",
    ".folio-flight-band",
    ".folio-compare-tray",
    ".folio-compare-sheet",
    ".folio-pick",
  ]) {
    assert.ok(globals.includes(cls), `globals.css must define ${cls}`);
  }
  // The new section is token-built (no raw hex literals).
  const secStart = globals.indexOf("SAVED PRIVATE FOLIO");
  const secEnd = globals.indexOf("@layer", secStart) > -1 ? globals.length : globals.length;
  const section = globals.slice(secStart, secEnd);
  assert.doesNotMatch(section.split("Reduced-motion")[0], /#[0-9a-fA-F]{3,6}\b/, "no raw hex in folio section");
});

// ── Source labels are honest (real provenance only) ──────────────────────────

test("source labels derive from real provenance, nothing fabricated", () => {
  assert.ok(savedShell.includes("outside_concierge"), "must map outside_concierge → From Concierge");
  assert.ok(savedShell.includes("explore_shell"), "must map explore_shell → From Explore");
  assert.ok(savedShell.includes('"From Concierge"') && savedShell.includes('"From Explore"'));
  // Unknown provenance returns null (omitted, not guessed).
  assert.match(savedShell, /function sourceLabel[\s\S]*return null;/);
});

// ── "Why it mattered" is the real saved query, omitted when absent ───────────

test("why-it-mattered uses the real searchContext.query, never invented", () => {
  assert.match(savedShell, /function whyItMattered[\s\S]*ctxStr\(item, "query"\)/);
  assert.ok(savedShell.includes('data-testid="saved-item-why"'));
  // rendered only when present
  assert.match(savedShell, /\{why && \(/);
});

// ── Compare: places only, capped at 4 ────────────────────────────────────────

test("compare is capped at 4 and excludes flights", () => {
  assert.ok(savedShell.includes("COMPARE_MAX = 4"), "max compare is 4");
  assert.match(savedShell, /PLACE_VERTICALS[\s\S]*"restaurant", "attraction", "hotel"/);
  assert.ok(!/PLACE_VERTICALS.*flight/.test(savedShell), "flight must not be a place vertical");
  // toggle guards both the place-only and the cap rules
  assert.match(savedShell, /PLACE_VERTICALS\.includes\(item\.vertical\)/);
  assert.match(savedShell, /next\.size >= COMPARE_MAX/);
});

test("compare tray appears conditionally and gates the open button at 2", () => {
  assert.ok(savedShell.includes('data-testid="compare-tray"'));
  assert.ok(savedShell.includes('data-testid="compare-open-btn"'));
  // tray renders nothing when empty
  assert.match(savedShell, /if \(items\.length === 0\) return null;/);
  // open disabled until 2 picked
  assert.match(savedShell, /const ready = items\.length >= 2;/);
  assert.match(savedShell, /disabled=\{!ready\}/);
  // tray clears the floating nav + safe area
  assert.match(globals, /\.folio-compare-tray[\s\S]*env\(safe-area-inset-bottom/);
});

test("compare sheet shows only saved facts — no invented price/score", () => {
  const sheetStart = savedShell.indexOf("function CompareSheet");
  const sheetEnd = savedShell.indexOf("function GroupSection");
  const sheet = savedShell.slice(sheetStart, sheetEnd);
  assert.ok(sheet.includes("Where") && sheet.includes("Saved"), "shows where + saved date");
  assert.ok(!/priceLevel|\bscore\b|Best value|recommended/i.test(sheet), "no invented ranking fields");
});

// ── Dedicated flight card ─────────────────────────────────────────────────────

test("flights use a dedicated boarding-pass card, not the place layout", () => {
  assert.match(savedShell, /function FlightCard/);
  assert.ok(savedShell.includes("folio-flight-card"));
  assert.ok(savedShell.includes('data-testid="flight-route-band"'));
  // route from real searchContext origin/destination
  assert.match(savedShell, /const origin = ctxStr\(item, "origin"\)/);
  // flights are dispatched to FlightCard via the canAddToTrip guard
  assert.match(savedShell, /canAddToTrip = props\.item\.vertical !== "flight"/);
});

test("flight route codes never crop/wrap mid-token (CSS guard)", () => {
  assert.match(globals, /\.folio-flight-ap\s*\{[\s\S]*white-space:\s*nowrap/);
  // route band spans full card width
  assert.match(globals, /\.folio-flight-band\s*\{[\s\S]*width:\s*100%/);
});

test("flight card has no Compare and no Map", () => {
  const flStart = savedShell.indexOf("function FlightCard");
  const flEnd = savedShell.indexOf("function SavedItemCard");
  const flight = savedShell.slice(flStart, flEnd);
  assert.ok(!flight.includes("compare-pick"), "flight has no compare pick");
  assert.ok(!flight.includes("googleMapsUri"), "flight has no map link");
  assert.ok(flight.includes('data-testid="create-trip-btn"'), "flight keeps Create Trip");
  assert.ok(flight.includes('data-testid="remove-saved-btn"'), "flight keeps Remove");
});

// ── Day grouping disabled (no real data), not faked ──────────────────────────

test("Day grouping is disabled, never fabricated", () => {
  assert.match(savedShell, /type GroupMode = "recent" \| "city" \| "category"/);
  assert.match(savedShell, /key: "day", label: "Day", disabled: true/);
  assert.ok(savedShell.includes("saved-group-${opt.key}"), "group buttons use a testid template");
});

// ── Immersive shell wiring ───────────────────────────────────────────────────

test("AppShell makes /saved an immersive paper room", () => {
  assert.match(appShell, /isSavedRoute = pathname === "\/saved"/);
  assert.match(appShell, /isImmersiveRoom = isHomePage \|\| isSalonRoute \|\| isExploreRoute \|\| isSavedRoute/);
  assert.match(appShell, /isSavedRoute \? "saved"/);
  assert.match(appShell, /isSavedRoute && <AtelierNavArtifact/);
  assert.match(globals, /\[data-atelier-shell="saved"\] \.folio-sidebar/);
});

// ── No backend / provider / new deps drift ───────────────────────────────────

test("SavedShell adds no backend, provider, or search imports", () => {
  for (const bad of ["callConciergeSearch", "searchRestaurants", "TripBuilder", "provider_registry"]) {
    assert.ok(!savedShell.includes(bad), `must not import ${bad}`);
  }
  // preserved real saved actions
  for (const fn of ["listSavedItems", "deleteSavedItem", "fetchTrips", "addSavedItemToTrip"]) {
    assert.ok(savedShell.includes(fn), `${fn} must be preserved`);
  }
});
