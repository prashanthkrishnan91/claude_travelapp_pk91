/**
 * Create Trip from Saved Item — Stage 3 v3
 *
 * Focused structural tests verifying:
 *  1. createTripFromSavedItem helper exported from api.ts.
 *  2. Helper composes existing POST /trips + POST /itinerary/items
 *     (no new backend route).
 *  3. Helper calls createTrip BEFORE seeding itinerary item.
 *  4. Flight path: safe details only — no booking/rate/price fields.
 *  5. Non-flight path: reuses Stage 3 v2 addSavedItemToTrip mapping.
 *  6. SavedShell wires Create Trip button and modal for all verticals.
 *  7. Modal builds prefill per contract for each vertical.
 *  8. Modal requires title/destination/start/end before submit.
 *  9. Hotel one-date-missing → both date fields blank.
 * 10. Flight one-way → endDate defaults to departureDate.
 * 11. Flight round-trip → endDate = returnDate.
 * 12. Restaurant/attraction → dates blank (user-entered).
 * 13. Restaurant/attraction missing destination → destination blank.
 * 14. No provider/concierge/search calls. No ResultActionSheet wiring.
 * 15. No TripBuilder/tripCandidates imports.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

function read(rel) {
  return readFileSync(path.join(root, rel), "utf8");
}

const apiTs = read("src/lib/api.ts");
const modal = read("src/components/saved/CreateTripFromSavedModal.tsx");
const savedShell = read("src/components/saved/SavedShell.tsx");

// ── 1–3. createTripFromSavedItem helper ──────────────────────────────────────

test("api.ts exports createTripFromSavedItem", () => {
  assert.ok(
    apiTs.includes("export async function createTripFromSavedItem"),
    "createTripFromSavedItem must be exported from api.ts"
  );
});

test("createTripFromSavedItem composes createTripWithSearch then itinerary seed", () => {
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 2000);
  const createWithSearchIdx = fnBody.indexOf("createTripWithSearch(");
  const seedFlightIdx = fnBody.indexOf("seedSavedFlightAsItineraryItem");
  const addSavedIdx = fnBody.indexOf("addSavedItemToTrip");
  assert.ok(createWithSearchIdx > -1, "must call createTripWithSearch");
  assert.ok(
    seedFlightIdx > createWithSearchIdx && addSavedIdx > createWithSearchIdx,
    "trip creation must happen before itinerary seed"
  );
});

test("createTripFromSavedItem does not call plain createTrip for the complete flow", () => {
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 2000);
  // The complete-flow helper must use createTripWithSearch — not the bare
  // /trips POST — so the new trip is fully seeded with candidates.
  assert.ok(
    !/\bcreateTrip\s*\(/.test(fnBody.replace(/createTripWithSearch\s*\(/g, "")),
    "must not invoke plain createTrip(...)"
  );
});

test("createTripFromSavedItem requires origin/destination/dates before submit", () => {
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 2000);
  assert.ok(
    fnBody.includes("!originCity") &&
      fnBody.includes("!destinationCity") &&
      fnBody.includes("!startDate") &&
      fnBody.includes("!endDate"),
    "must reject missing required inputs"
  );
});

test("createTripFromSavedItem does not introduce a new backend route", () => {
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 1500);
  // No new combined route invented
  assert.ok(!fnBody.includes("create-trip-from-saved"), "no new combined route");
  assert.ok(!fnBody.includes("/trips/from-saved"), "no new combined route");
});

// ── 4. Flight seed: safe details only ────────────────────────────────────────

test("seedSavedFlightAsItineraryItem posts to /itinerary/items with flight type", () => {
  const fnStart = apiTs.indexOf("async function seedSavedFlightAsItineraryItem");
  assert.ok(fnStart > -1, "helper must exist");
  const fnBody = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('"/itinerary/items"'), "must POST to /itinerary/items");
  assert.ok(fnBody.includes('item_type: "flight"'), "must set item_type flight");
});

test("flight seed details carry no booking/rate/price fields", () => {
  const fnStart = apiTs.indexOf("async function seedSavedFlightAsItineraryItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 2500);
  for (const banned of [
    "bookingUrl",
    "booking_url",
    "totalPrice",
    "total_price",
    "price",
    "fare",
    "nightly_rate",
    "availability",
  ]) {
    assert.ok(!fnBody.includes(banned), `flight seed must not include ${banned}`);
  }
});

test("flight seed carries source:saved_item + savedItemId provenance", () => {
  const fnStart = apiTs.indexOf("async function seedSavedFlightAsItineraryItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 2500);
  assert.ok(fnBody.includes('source: "saved_item"'), "must carry source provenance");
  assert.ok(fnBody.includes("savedItemId"), "must carry savedItemId provenance");
});

// ── 5. Non-flight: reuse addSavedItemToTrip ──────────────────────────────────

test("createTripFromSavedItem reuses addSavedItemToTrip for non-flight verticals", () => {
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 1500);
  assert.ok(
    fnBody.includes("addSavedItemToTrip("),
    "non-flight path must reuse Stage 3 v2 helper"
  );
});

// ── 6. SavedShell wires Create Trip ──────────────────────────────────────────

test("SavedShell imports CreateTripFromSavedModal", () => {
  assert.ok(savedShell.includes("CreateTripFromSavedModal"), "must import modal");
});

test("SavedShell has create-trip-btn for cards", () => {
  assert.ok(savedShell.includes("create-trip-btn"), "must have create-trip-btn testid");
});

test("SavedShell uses next/navigation router for navigation", () => {
  assert.ok(savedShell.includes("next/navigation"), "must use next router");
  assert.ok(savedShell.includes("router.push(`/trips/"), "must navigate to /trips/:id");
});

test("Create Trip button is rendered for all verticals (not flight-gated)", () => {
  // Stage 3 v3: all four verticals are enabled. Button rendering must not be
  // gated by item.vertical (the modal handles destination prefill conditions).
  const sectionStart = savedShell.indexOf('data-testid="create-trip-section"');
  assert.ok(sectionStart > -1, "create-trip-section must exist");
  const window = savedShell.slice(Math.max(0, sectionStart - 300), sectionStart + 300);
  assert.ok(
    !window.includes('vertical !== "flight"') && !window.includes("vertical !== 'flight'"),
    "create-trip must not exclude flight vertical"
  );
});

// ── 7. Modal exports buildTripPrefillFromSavedItem ───────────────────────────

test("modal exports CreateTripFromSavedModal and prefill helper", () => {
  assert.ok(
    modal.includes("export function CreateTripFromSavedModal"),
    "must export modal"
  );
  assert.ok(
    modal.includes("export function buildTripPrefillFromSavedItem"),
    "must export prefill helper for testability"
  );
});

// ── 8. Required-field validation ─────────────────────────────────────────────

test("modal requires title, origin, destination, start/end dates before submit", () => {
  // canSubmit gate checks all five required fields are non-empty
  assert.ok(modal.includes("title.trim().length > 0"), "title required");
  assert.ok(modal.includes("origin.trim().length > 0"), "origin required");
  assert.ok(modal.includes("destination.trim().length > 0"), "destination required");
  assert.ok(modal.includes("startDate.length > 0"), "startDate required");
  assert.ok(modal.includes("endDate.length > 0"), "endDate required");
});

test("modal renders Origin field for ALL verticals (not flight-gated)", () => {
  // Stage 3 exit: Origin must be visible regardless of vertical so the
  // full create-with-search flow can run for hotels/restaurants/attractions.
  assert.ok(modal.includes('data-testid="ct-origin"'), "must render ct-origin input");
  assert.ok(
    !modal.includes('isFlight && (\n            <div>'),
    "Origin must not be hidden behind isFlight gate"
  );
  assert.ok(
    !/item\.vertical\s*===\s*"flight"[^}]*ct-origin/s.test(modal),
    "ct-origin must not be flight-gated"
  );
});

test("modal does not silently create — always shows confirmation form", () => {
  assert.ok(modal.includes("Create a new trip"), "form title per contract");
  assert.ok(modal.includes("Create trip"), "submit label per contract");
});

// ── Behavioral tests of prefill helper ────────────────────────────────────────
// We import via a Node ESM-friendly path through a dynamic require shim by
// re-evaluating the helper via a TS-stripped fragment. Simpler: directly test
// the source for known branches.

test("flight one-way: endDate falls back to departureDate", () => {
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  assert.ok(
    body.includes("ret || dep"),
    "flight endDate must fall back to dep when ret is missing"
  );
});

test("flight round-trip: endDate uses returnDate when present", () => {
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  // ret takes precedence in `ret || dep`
  assert.ok(
    body.includes("ret || dep"),
    "round-trip uses returnDate via ret || dep precedence"
  );
});

test("hotel: missing either date leaves BOTH date fields blank", () => {
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  assert.ok(body.includes("bothDates"), "must gate both dates together");
  assert.ok(
    body.includes('startDate: bothDates ? ci : ""'),
    "startDate blank when either missing"
  );
  assert.ok(
    body.includes('endDate: bothDates ? co : ""'),
    "endDate blank when either missing"
  );
});

test("restaurant/attraction: dates always blank (user-entered)", () => {
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  // Last branch (after hotel) sets startDate: "" and endDate: ""
  const lastBranch = body.slice(body.lastIndexOf("// restaurant"));
  assert.ok(lastBranch.includes('startDate: ""'), "restaurant/attraction startDate blank");
  assert.ok(lastBranch.includes('endDate: ""'), "restaurant/attraction endDate blank");
});

test("restaurant/attraction: destination falls back to displaySnapshot.destination", () => {
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  const lastBranch = body.slice(body.lastIndexOf("// restaurant"));
  assert.ok(
    lastBranch.includes('ctxStr(item, "destination") || snapStr(item, "destination")'),
    "destination falls back to displaySnapshot.destination"
  );
});

test("restaurant/attraction: destination missing → blank (user must fill)", () => {
  // If neither searchContext nor displaySnapshot have destination, helper returns "".
  // The form already requires destination to be non-empty before submit.
  const helperStart = modal.indexOf("export function buildTripPrefillFromSavedItem");
  const helperEnd = modal.indexOf("// ── Modal", helperStart);
  const body = modal.slice(helperStart, helperEnd);
  assert.ok(
    !body.includes("'unknown'") && !body.includes('"unknown"'),
    "no fabricated destination"
  );
  // canSubmit gate enforces non-empty destination
  assert.ok(modal.includes("destination.trim().length > 0"), "submit gated on destination");
});

// ── 14. No provider/concierge/search wiring ──────────────────────────────────

test("modal does not call /search/* routes", () => {
  assert.ok(!modal.includes("/search/"), "modal must not call /search/*");
});

test("modal does not call callConcierge or providers", () => {
  assert.ok(!modal.includes("callConcierge"), "modal must not call concierge");
  assert.ok(!modal.includes("ResultActionSheet"), "modal must not wire ResultActionSheet");
});

// ── 15. Forbidden scope ──────────────────────────────────────────────────────

test("modal does not import TripBuilder or tripCandidates", () => {
  assert.ok(!modal.includes("TripBuilder.tsx"), "must not import TripBuilder");
  assert.ok(!modal.includes("tripCandidates"), "must not import tripCandidates");
});

test("SavedShell does not introduce a new ResultActionSheet wiring", () => {
  assert.ok(
    !savedShell.includes("ResultActionSheet"),
    "Stage 3 v3 wires SavedShell only — no ResultActionSheet"
  );
});

// ── 16. Hotel itinerary seed via addSavedItemToTrip stays rate-safe ──────────

test("hotel path reuses addSavedItemToTrip — no rate fields introduced", () => {
  // Confirm that the createTripFromSavedItem helper does NOT introduce its own
  // hotel mapping path that could leak booking/rate fields.
  const fnStart = apiTs.indexOf("export async function createTripFromSavedItem");
  const fnBody = apiTs.slice(fnStart, fnStart + 1500);
  for (const banned of ["nightly_rate", "totalPrice", "bookingUrl", "availability"]) {
    assert.ok(!fnBody.includes(banned), `must not include ${banned}`);
  }
});
