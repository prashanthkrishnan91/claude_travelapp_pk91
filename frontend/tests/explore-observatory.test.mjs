/**
 * Explore Observatory v1 — outside-trip /explore premium reskin.
 * Static source-file contract tests (no DOM, no network), matching the
 * repo's existing salon/explore test style. Asserts the Observatory CSS +
 * shell + per-vertical card reskin without changing behavior, providers,
 * data contracts, saved-item behavior, or the app shell.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { test, describe } from "node:test";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const read = (p) => readFileSync(join(root, p), "utf8");

const globalsCss = read("src/app/globals.css");
const shell = read("src/components/explore/ExploreShell.tsx");
const appShell = read("src/components/layout/AppShell.tsx");
const observatoryCard = read("src/components/explore/ObservatoryCard.tsx");
const restaurant = read("src/components/explore/RestaurantExploreFlow.tsx");
const attraction = read("src/components/explore/AttractionExploreFlow.tsx");
const hotel = read("src/components/explore/HotelExploreFlow.tsx");
const flight = read("src/components/explore/FlightExploreFlow.tsx");

// ── Section A: OBSERVATORY CSS primitives ───────────────────────────────────

describe("Explore Observatory: CSS primitives", () => {
  for (const cls of [
    ".obs-meridian",
    ".obs-meridian--banner",
    ".obs-meridian-scene",
    ".obs-meridian-bloom",
    ".obs-meridian-grain",
    ".obs-meridian-horizon",
    ".obs-meridian-vignette",
    ".obs-meridian-copy",
    ".obs-meridian-title",
    ".obs-vert-card",
    ".obs-index-head",
    ".obs-card",
    ".obs-card-frame",
    ".obs-card-plate",
    ".obs-card-body",
    ".obs-card-name",
  ]) {
    test(`defines ${cls}`, () => {
      assert.ok(globalsCss.includes(cls), `globals.css must define ${cls}`);
    });
  }

  test("A2. meridian is a wide band with isolation + overflow hidden", () => {
    const block = globalsCss.slice(
      globalsCss.indexOf(".obs-meridian {"),
      globalsCss.indexOf(".obs-meridian--banner"),
    );
    assert.ok(block.includes("isolation: isolate"), "meridian isolates stacking context");
    assert.ok(block.includes("overflow: hidden"), "meridian clips its depth layers");
  });

  test("A3. new motion is reduced-motion guarded", () => {
    // The Observatory keyframes must each have a reduced-motion override that
    // disables animation, plus hover-transform overrides.
    const rmBlocks = globalsCss.match(/@media \(prefers-reduced-motion: reduce\) \{[\s\S]*?\n  \}/g) || [];
    const joined = rmBlocks.join("\n");
    assert.ok(joined.includes(".obs-meridian-scene"), "obs-meridian-scene animation disabled under reduced-motion");
    assert.ok(joined.includes(".obs-meridian-bloom"), "obs-meridian-bloom animation disabled under reduced-motion");
    assert.ok(
      joined.includes(".obs-card:hover") || joined.includes(".obs-card-frame:hover"),
      "obs-card hover transform removed under reduced-motion",
    );
  });

  test("A4. tokens only — no raw hex in OBSERVATORY section", () => {
    const start = globalsCss.indexOf("EXPLORE OBSERVATORY");
    assert.ok(start !== -1, "OBSERVATORY section present");
    const section = globalsCss.slice(start);
    // The scene gradient legitimately uses rgb()/rgba() (matching the salon
    // dusk scene). What must NOT appear is raw #hex color literals.
    const hex = section.match(/#[0-9a-fA-F]{3,8}\b/g);
    assert.equal(hex, null, `OBSERVATORY CSS must not use raw hex (found: ${hex})`);
  });
});

// ── Section B: ExploreShell remains vertical-first, testids preserved ───────

describe("Explore Observatory: shell composition", () => {
  test("B1. landing renders the meridian hero with preserved header testid", () => {
    assert.ok(shell.includes("ObsMeridian"), "shell renders the ObsMeridian band");
    assert.ok(shell.includes('data-testid="explore-home"'), "explore-home preserved");
    assert.ok(shell.includes('explore-lounge-header'), "explore-lounge-header preserved");
    assert.ok(shell.includes('data-testid="explore-vertical-grid"'), "explore-vertical-grid preserved");
  });

  test("B2. all four vertical entry cards preserved (vertical-first)", () => {
    assert.ok(shell.includes("vertical-card-${"), "vertical card testid built per vertical id");
    for (const id of ["flights", "hotels", "restaurants", "attractions"]) {
      assert.ok(shell.includes(`id: "${id}"`), `${id} vertical preserved in VERTICALS`);
    }
    assert.ok(shell.includes("obs-vert-card"), "entry cards use obs-vert-card");
  });

  test("B3. selecting a vertical still drives setActive (no lifted controller)", () => {
    assert.ok(shell.includes("setActive(v.id)"), "vertical cards call setActive");
    assert.ok(shell.includes("setActive(null)"), "breadcrumb returns to landing");
    assert.ok(shell.includes('data-testid="explore-vertical-flow"'), "active flow view preserved");
    assert.ok(shell.includes('data-testid="explore-lounge-breadcrumb"'), "breadcrumb preserved");
    assert.ok(shell.includes('data-testid="explore-instrument-header"'), "instrument header preserved");
  });

  test("B4. mobile 2x2 / desktop 4-up grid for verticals", () => {
    assert.ok(
      shell.includes("grid-cols-2") && shell.includes("lg:grid-cols-4"),
      "vertical grid is 2-up mobile, 4-up desktop",
    );
  });

  test("B5. vertical mood banner shows identity/mood only — no destination state lifted", () => {
    assert.ok(shell.includes("VERTICAL_MOODS"), "banner uses static per-vertical mood lines");
    // Guard against accidental cross-vertical destination controller.
    assert.ok(!/destination[,)]/.test(shell), "ExploreShell holds no destination state");
    assert.ok(!shell.includes("searchRestaurants") && !shell.includes("searchHotelsExplore"), "shell does not call vertical search APIs");
  });
});

// ── Section C: place-card reskin preserves behavior + actions ───────────────

describe("Explore Observatory: place card reskin", () => {
  test("C1. ObservatoryPlate is the honest typeset fallback (no image element)", () => {
    assert.ok(observatoryCard.includes("obs-card-plate"), "plate uses obs-card-plate");
    assert.ok(!/<img\b/.test(observatoryCard), "plate renders no <img> — honest typeset fallback");
    assert.ok(!/next\/image|background-image|url\(/i.test(observatoryCard), "plate wires no image source");
  });

  for (const [name, src, results] of [
    ["restaurants", restaurant, "restaurant-results"],
    ["attractions", attraction, "attraction-results"],
    ["hotels", hotel, "hotel-results"],
  ]) {
    test(`C2-${name}. uses obs-card + ObservatoryPlate, preserves results + actions`, () => {
      assert.ok(src.includes("ObservatoryPlate"), `${name} uses the editorial plate`);
      assert.ok(src.includes('className="obs-card"'), `${name} card uses obs-card frame`);
      assert.ok(src.includes("obs-card-body"), `${name} wraps body in obs-card-body`);
      assert.ok(src.includes("obs-index-head"), `${name} restyles the index head`);
      assert.ok(src.includes(`data-testid="${results}"`), `${name} results testid preserved`);
      assert.ok(src.includes('data-testid="explore-results-header"'), `${name} results header testid preserved`);
      assert.ok(src.includes("ResultActionSheet"), `${name} keeps Save via ResultActionSheet`);
      assert.ok(src.includes("TrustStrip"), `${name} keeps Source via TrustStrip`);
      assert.ok(src.includes("googleMapsUri"), `${name} keeps the Map link-out`);
    });
  }

  test("C3. hotels remain discovery-only — no price/currency/availability rendered", () => {
    // No price fields, currency formatting, or availability claims in the hotel flow.
    for (const banned of ["priceLevel", "totalPrice", "Intl.NumberFormat", "formatPrice", "isAvailable"]) {
      assert.ok(!hotel.includes(banned), `hotel flow must not reference ${banned}`);
    }
    assert.ok(hotel.includes('data-testid="hotel-compare-cta"'), "hotel compare CTA preserved");
    assert.ok(hotel.includes("compareLink"), "hotel compare link preserved");
  });
});

// ── Section D: flights preserved exactly ────────────────────────────────────

describe("Explore Observatory: flights preserved", () => {
  test("D1. CityAutocomplete + airport/submit logic intact", () => {
    assert.ok(flight.includes("CityAutocomplete"), "CityAutocomplete preserved (PR #431 frozen)");
    assert.ok(flight.includes("searchFlightsExplore"), "flight search call preserved");
    assert.ok(flight.includes("airports[0]"), "primary airport logic preserved");
  });

  test("D2. all four status states preserved", () => {
    for (const t of [
      "flight-results-list",
      "flight-empty-state",
      "flight-unavailable-state",
      "flight-error-state",
    ]) {
      assert.ok(flight.includes(t), `${t} preserved`);
    }
  });

  test("D3. price rendered only from offer.price (live provider)", () => {
    assert.ok(flight.includes("offer.price.totalAmount"), "price comes from offer.price only");
    assert.ok(flight.includes("liveCachedStatus"), "live/cached status preserved");
    assert.ok(flight.includes("flight-card"), "flight card testid preserved");
    assert.ok(flight.includes("obs-card-frame"), "flight card wears the Observatory frame");
  });
});

// ── Section F: immersive outside-trip shell + full-page room ────────────────

describe("Explore Observatory: immersive shell integration", () => {
  test("F1. AppShell defines isExploreRoute for /explore", () => {
    assert.ok(appShell.includes('pathname === "/explore"'), "AppShell detects the /explore route");
  });

  test("F2. AppShell sets data-atelier-shell='explore' (sidebar suppressed via CSS)", () => {
    assert.ok(appShell.includes('"explore"') && appShell.includes("data-atelier-shell"), "explore shell hook set");
    assert.ok(
      globalsCss.includes('[data-atelier-shell="explore"] .folio-sidebar'),
      "globals.css hides .folio-sidebar on the explore route",
    );
  });

  test("F3. AppShell renders the floating AtelierNavArtifact for explore", () => {
    assert.ok(appShell.includes("isExploreRoute && <AtelierNavArtifact"), "floating nav rendered for explore");
  });

  test("F4. explore uses the edge-bleed immersive wrapper (not the max-w-7xl box)", () => {
    assert.ok(appShell.includes("isExploreRoute"), "explore participates in the immersive branch");
    assert.ok(appShell.includes("home-edge-bleed"), "edge-bleed wrapper preserved");
    // Legacy padded shell + home sidebar ternary must stay intact.
    assert.ok(appShell.includes("isHomePage ? null : <Sidebar />"), "home sidebar ternary preserved (8J)");
    assert.ok(appShell.includes("max-w-7xl mx-auto px-4 sm:px-6 lg:px-8"), "non-immersive routes keep max-w-7xl");
  });

  test("F5. ExploreShell is a light field with a floating dark room (Concierge-family composition)", () => {
    assert.ok(shell.includes("obs-field"), "ExploreShell uses the light outer obs-field");
    assert.ok(shell.includes('className="obs-room folio-cinema-lounge"'), "the floating dark room is obs-room + folio-cinema-lounge");
    assert.ok(globalsCss.includes(".obs-field"), "globals.css defines the light outer field");
    assert.ok(globalsCss.includes(".obs-room.folio-cinema-lounge"), "globals.css gives the floating room roomy padding");
    // The field must be light (warm paper), not a full-bleed black page.
    const fieldBlock = globalsCss.slice(globalsCss.indexOf(".obs-field {"), globalsCss.indexOf(".obs-room {"));
    assert.ok(fieldBlock.includes("--ds-warm-paper"), "the outer field is a light atelier canvas, not black");
    assert.ok(globalsCss.includes(".obs-meridian--hero"), "landing hero meridian defined");
    assert.ok(shell.includes("<ObsMeridian hero>"), "landing renders the hero meridian");
  });

  test("F6. hero copy is plain user-facing (no internal trip-state language)", () => {
    assert.ok(shell.includes("Browse flights, hotels, restaurants, and attractions"), "plain browse copy present");
    assert.ok(!shell.includes("no trip required"), "internal 'no trip required' framing removed");
  });
});

// ── Section G: mobile first-load fit (≤640px) ───────────────────────────────

describe("Explore Observatory: mobile first-load fit", () => {
  test("G1. each vertical has a short mobile cue; cards render obs-vert-cue", () => {
    for (const [id, cue] of [
      ["flights", "Live routes"],
      ["hotels", "Verified stays"],
      ["restaurants", "Dining ideas"],
      ["attractions", "Places to see"],
    ]) {
      assert.ok(shell.includes(`cue: "${cue}"`), `${id} has the short mobile cue "${cue}"`);
    }
    assert.ok(shell.includes("obs-vert-cue"), "cards render the mobile cue element");
  });

  test("G2. desktop keeps full descriptions; cue is hidden by default", () => {
    assert.ok(shell.includes("obs-vert-desc"), "full description still rendered (desktop)");
    const cueBlock = globalsCss.slice(globalsCss.indexOf(".obs-vert-cue {"), globalsCss.indexOf(".obs-vert-cue {") + 120);
    assert.ok(cueBlock.includes("display: none"), "cue hidden by default (desktop unchanged)");
  });

  test("G3. mobile media block compacts the landing without forced full-height", () => {
    const mq = globalsCss.slice(globalsCss.indexOf("Mobile first-load fit"));
    assert.ok(mq.includes("@media (max-width: 640px)"), "mobile-fit media query present");
    const block = mq.slice(0, mq.indexOf("Reduced-motion: Observatory"));
    assert.ok(/\.obs-field\s*\{[^}]*min-height:\s*auto/.test(block), "obs-field sizes to content on mobile (no forced 100svh)");
    assert.ok(block.includes(".obs-meridian--hero") && /min-height:\s*clamp\(156px/.test(block), "hero compact-but-breathing on mobile");
    assert.ok(/\.obs-meridian--hero\s+\.obs-meridian-horizon\s*\{\s*top:\s*78%/.test(block), "horizon line dropped below the subtitle (collision fix)");
    assert.ok(/\.obs-meridian--hero\s+\.obs-meridian-copy\s*\{[^}]*justify-content:\s*flex-start/.test(block), "hero copy clusters at the top so the lower band stays clear");
    assert.ok(/\.obs-vert-cue\s*\{\s*display:\s*block/.test(block), "mobile shows the short cue");
    assert.ok(/\.obs-vert-desc\s*\{\s*display:\s*none/.test(block), "mobile hides the long description");
    assert.ok(/\.obs-vert-go\s*\{\s*display:\s*none/.test(block), "mobile hides the Browse cue line to save height");
  });
});

// ── Section E: no prototype/demo strings leaked into production ──────────────

describe("Explore Observatory: no prototype/demo data", () => {
  const sources = [shell, observatoryCard, restaurant, attraction, hotel, flight, globalsCss];
  const banned = [
    "Taberna do Mercado",
    "A Cevicheria",
    "O Velho Eurico",
    "Memmo Alfama",
    "Mosteiro dos Jer",
    "from $640",
    "Source photo",
    "Typeset · no photo",
    "data-v=",
    "Sample ·",
  ];
  for (const phrase of banned) {
    test(`does not contain prototype string: ${phrase}`, () => {
      for (const src of sources) {
        assert.ok(!src.includes(phrase), `production source must not contain "${phrase}"`);
      }
    });
  }
});
