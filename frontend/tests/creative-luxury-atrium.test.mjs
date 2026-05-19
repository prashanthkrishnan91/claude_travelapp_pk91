/**
 * Creative Luxury UX — Atelier Atrium
 *
 * Verifies the destination-world atrium composition:
 *   A. AppShell opts the home page out of the max-w-7xl box so the
 *      destination scenery can extend edge-to-edge.
 *   B. DashboardClient adopts the atelier-atrium composition (atrium
 *      content wrapper, hero spread, concierge threshold, doorway
 *      shelf, curio shelf, atrium signature).
 *   C. New globals.css primitives exist for the atrium, dossier,
 *      concierge threshold, doorway shelf, and curio shelf — each
 *      reads from --world-* variables and respects reduced-motion.
 *   D. The active trip renders as a folio dossier (not a plain card),
 *      with scenery clipped inside its cover.
 *   E. Room portals inside the doorway shelf are tall and cinematic;
 *      labels live on small plaques, scenery does orientation work.
 *   F. Anti-regression: no SaaS dashboard energy, no destination strings
 *      hardcoded in components, no orphan tiles, no shrunken portals.
 */

import test, { describe } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function readSrc(rel) {
  return readFileSync(new URL(`../src/${rel}`, import.meta.url), "utf8");
}

const appShell        = readSrc("components/layout/AppShell.tsx");
const dashboardClient = readSrc("components/dashboard/DashboardClient.tsx");
const globalsCss      = readSrc("app/globals.css");
const worldTsx        = readSrc("components/ui/World.tsx");

// ── A. AppShell edge-bleed escape hatch ──────────────────────────────────────

describe("Atrium: AppShell edge-bleed escape hatch", () => {
  test("A1. AppShell detects the home route via pathname === '/'", () => {
    assert.match(
      appShell,
      /pathname\s*===\s*["']\/["']/,
      "AppShell must detect the home page so it can opt out of the max-w-7xl box",
    );
  });

  test("A2. AppShell renders home content without the max-w-7xl wrapper", () => {
    // The home branch must lack max-w-7xl (so scenery extends edge-to-edge)
    // while still keeping mobile-nav-spacer + atelier-transition.
    assert.match(
      appShell,
      /home-edge-bleed/,
      "AppShell must apply the home-edge-bleed class on the home branch",
    );
    assert.match(
      appShell,
      /data-home-edge-bleed="true"/,
      "AppShell must mark the home branch with data-home-edge-bleed=true for runtime debugging",
    );
  });

  test("A3. Non-home routes still keep the centered max-w-7xl page shell", () => {
    assert.match(
      appShell,
      /max-w-7xl mx-auto px-4 sm:px-6 lg:px-8/,
      "AppShell must keep max-w-7xl on non-home routes",
    );
  });

  test("A4. Phase 8J / 8M contracts preserved on both branches", () => {
    // mobile-nav-spacer + atelier-transition + mobile-page-content testid
    // must appear on the home branch too — those are non-negotiable.
    assert.ok(
      (appShell.match(/mobile-nav-spacer/g) ?? []).length >= 2,
      "AppShell must keep mobile-nav-spacer on both home and non-home branches",
    );
    assert.ok(
      (appShell.match(/atelier-transition/g) ?? []).length >= 2,
      "AppShell must keep atelier-transition on both branches",
    );
    assert.ok(
      (appShell.match(/mobile-page-content/g) ?? []).length >= 2,
      "AppShell must keep mobile-page-content testid on both branches",
    );
  });
});

// ── B. DashboardClient atrium adoption ───────────────────────────────────────

describe("Atrium: DashboardClient composition", () => {
  test("B1. FolioScene root carries the atelier-atrium class", () => {
    assert.match(
      dashboardClient,
      /<FolioScene[\s\S]*?atelier-atrium/,
      "DashboardClient FolioScene must carry the atelier-atrium class for edge-bleed composition",
    );
  });

  test("B2. FolioLivingCanvas adopts the atelier-atrium-content wrapper class", () => {
    assert.match(
      dashboardClient,
      /<FolioLivingCanvas[\s\S]*?atelier-atrium-content/,
      "FolioLivingCanvas inside DashboardClient must carry atelier-atrium-content",
    );
  });

  test("B3. The hero spread is wrapped in .atelier-atrium-hero", () => {
    assert.match(
      dashboardClient,
      /className=["'][^"']*atelier-atrium-hero/,
      "Hero spread must use atelier-atrium-hero to compose greeting + dossier",
    );
  });

  test("B4. AtelierGreeting still mounts WorldGlassSurface and uses atelier-hero-greeting modifier", () => {
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(block.includes("WorldGlassSurface"));
    assert.ok(
      block.includes("atelier-hero-greeting"),
      "AtelierGreeting WorldGlassSurface must adopt atelier-hero-greeting modifier",
    );
  });

  test("B5. ContinuePlanningStrip article becomes a folio dossier (atelier-dossier)", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-dossier"),
      "ContinuePlanningStrip article must carry the atelier-dossier class",
    );
    assert.ok(
      block.includes("atelier-dossier-cover"),
      "ContinuePlanningStrip must carry a dossier cover (scenery clipped inside)",
    );
    assert.ok(
      block.includes("atelier-dossier-scenery"),
      "ContinuePlanningStrip must carry a dossier scenery layer (decorative)",
    );
    assert.ok(
      block.includes("atelier-dossier-plate"),
      "ContinuePlanningStrip must carry a brass date plate (integrated, not orphan)",
    );
    assert.ok(
      block.includes("atelier-dossier-flag"),
      "ContinuePlanningStrip must carry a folded folio-serial flag",
    );
  });

  test("B6. ConciergeEntry uses the concierge threshold (full-width salon doorway)", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-concierge-threshold"),
      "ConciergeEntry must compose atelier-concierge-threshold for the salon doorway",
    );
  });

  test("B7. AtelierPlanningStrip is the cinematic doorway shelf", () => {
    const start = dashboardClient.indexOf("function AtelierPlanningStrip");
    const end = dashboardClient.indexOf("// ── Main component");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-doorway-shelf"),
      "AtelierPlanningStrip must carry atelier-doorway-shelf — tall doorways, not labeled tiles",
    );
    // The room switcher is still the four-room contract from the world
    // system; the doorway shelf re-skins it spatially.
    assert.ok(
      block.includes("WorldRoomSwitcher"),
      "AtelierPlanningStrip must keep mounting WorldRoomSwitcher",
    );
  });

  test("B8. JourneyShelfTeaser becomes a curio shelf with three book spines", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-curio-shelf"),
      "JourneyShelfTeaser must carry atelier-curio-shelf — a physical shelf object",
    );
    const spines = (block.match(/atelier-curio-spine\b/g) ?? []).length;
    assert.ok(
      spines >= 3,
      `JourneyShelfTeaser must render at least 3 book-spine layers (got ${spines})`,
    );
  });

  test("B9. EmptyAtelierHome reads as a blank dossier (same dossier object, no SaaS empty state)", () => {
    const start = dashboardClient.indexOf("function EmptyAtelierHome");
    const end = dashboardClient.indexOf("// ── Rooms in the house");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-dossier"),
      "EmptyAtelierHome must compose the dossier object so first-run still reads as a folio",
    );
  });

  test("B10. The page closes with the quiet atrium signature, not a loud overline", () => {
    assert.match(
      dashboardClient,
      /atelier-atrium-signature/,
      "DashboardClient must end with the atelier-atrium-signature footer",
    );
    assert.match(
      dashboardClient,
      /world-wayfinder-quiet/,
      "Closing wayfinder must remain the quiet editorial signature",
    );
  });

  test("B11. FolioReveal staggers preserved (2, 3, 4)", () => {
    assert.match(
      dashboardClient,
      /stagger=\{2\}/,
      "FolioReveal stagger=2 must wrap ConciergeEntry",
    );
    assert.match(
      dashboardClient,
      /stagger=\{3\}/,
      "FolioReveal stagger=3 must wrap ContinuePlanningStrip / EmptyAtelierHome",
    );
    assert.match(
      dashboardClient,
      /stagger=\{4\}/,
      "FolioReveal stagger=4 must wrap the doorway shelf / curio shelf",
    );
  });
});

// ── C. globals.css atrium primitives ────────────────────────────────────────

describe("Atrium: globals.css primitives", () => {
  test("C1. .home-edge-bleed exists for the AppShell escape hatch", () => {
    assert.ok(
      globalsCss.includes(".home-edge-bleed"),
      "globals.css must define .home-edge-bleed to let the home page bleed edge-to-edge",
    );
  });

  test("C2. .atelier-atrium and .atelier-atrium-content exist", () => {
    assert.ok(globalsCss.includes(".atelier-atrium {"));
    assert.ok(globalsCss.includes(".atelier-atrium-content"));
    const idx = globalsCss.indexOf(".atelier-atrium-content");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("padding-inline"),
      ".atelier-atrium-content must own its internal gutters",
    );
  });

  test("C3. .atelier-atrium-hero composes a 2-column desktop spread", () => {
    assert.ok(globalsCss.includes(".atelier-atrium-hero"));
    const idx = globalsCss.indexOf(".atelier-atrium-hero");
    const block = globalsCss.slice(idx, idx + 1200);
    assert.ok(
      /min-width:\s*1024px/.test(block) && /grid-template-columns:\s*minmax/.test(block),
      ".atelier-atrium-hero must define a desktop 2-column grid",
    );
  });

  test("C4. .atelier-dossier ships cover + scenery + plate + flag + body + footer", () => {
    for (const cls of [
      ".atelier-dossier",
      ".atelier-dossier-cover",
      ".atelier-dossier-scenery",
      ".atelier-dossier-plate",
      ".atelier-dossier-flag",
      ".atelier-dossier-body",
      ".atelier-dossier-footer",
    ]) {
      assert.ok(globalsCss.includes(cls + " "), `globals.css must define ${cls}`);
    }
  });

  test("C5. .atelier-dossier-scenery reads its image from --world-scenery-image (no hardcoded URL)", () => {
    const idx = globalsCss.indexOf(".atelier-dossier-scenery");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("var(--world-scenery-image"),
      ".atelier-dossier-scenery must read its image via --world-scenery-image",
    );
    assert.ok(
      block.includes("var(--world-scenery)"),
      ".atelier-dossier-scenery must fall back to the painted --world-scenery stack",
    );
  });

  test("C6. .atelier-dossier transitions use luxury cubic-bezier easing", () => {
    const idx = globalsCss.indexOf(".atelier-dossier {");
    const block = globalsCss.slice(idx, idx + 1200);
    assert.ok(
      block.includes("cubic-bezier(0.16, 1, 0.3, 1)"),
      ".atelier-dossier must use luxury cubic-bezier(0.16, 1, 0.3, 1)",
    );
  });

  test("C7. Dossier respects prefers-reduced-motion", () => {
    const re = /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\.atelier-dossier[\s\S]*?transition:\s*none/;
    assert.ok(
      re.test(globalsCss),
      ".atelier-dossier transitions must be disabled under prefers-reduced-motion",
    );
  });

  test("C8. .atelier-concierge-threshold paints the salon interior in its right half", () => {
    assert.ok(globalsCss.includes(".atelier-concierge-threshold"));
    const idx = globalsCss.indexOf(".atelier-concierge-threshold {");
    const block = globalsCss.slice(idx, idx + 1600);
    assert.ok(
      block.includes("--world-ink"),
      ".atelier-concierge-threshold must read interior shadow from --world-ink",
    );
    assert.ok(
      block.includes("--world-accent"),
      ".atelier-concierge-threshold must read warm lantern light from --world-accent",
    );
  });

  test("C9. .atelier-doorway-shelf scopes the room switcher to taller, cinematic portals", () => {
    assert.ok(globalsCss.includes(".atelier-doorway-shelf"));
    // The doorway shelf must enlarge the room portal min-height beyond the
    // default tile-sized 168px so they read as actual doorways, not labels.
    assert.ok(
      /\.atelier-doorway-shelf[\s\S]*?\.world-portal[\s\S]*?min-height:\s*clamp\(\s*340px/.test(globalsCss),
      ".atelier-doorway-shelf must give portals min-height clamp(340px,...) — no more tiny tile syndrome",
    );
  });

  test("C10. .atelier-curio-shelf is a physical shelf with spines + brass strip", () => {
    assert.ok(globalsCss.includes(".atelier-curio-shelf"));
    assert.ok(globalsCss.includes(".atelier-curio-spines"));
    assert.ok(globalsCss.includes(".atelier-curio-spine"));
    // Brass shelf strip at the base
    const idx = globalsCss.indexOf(".atelier-curio-shelf::after");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("--world-accent"),
      ".atelier-curio-shelf::after must read its brass colour from --world-accent",
    );
  });

  test("C11. Atrium primitives read from world variables, not hardcoded hex", () => {
    // Pull the atrium block and ensure it does not hardcode raw hex
    // destination colors — must flow through --world-* variables.
    const start = globalsCss.indexOf("ATELIER ATRIUM");
    const end = globalsCss.lastIndexOf("}");
    const block = globalsCss.slice(start, end);
    assert.doesNotMatch(
      block,
      /#3F5546|#B68A5A|#1F4256|#E0B888|#9B4A2E/,
      "Atrium CSS must not embed Portland/Santorini/Marrakech hex — must flow through --world-* variables",
    );
  });
});

// ── D. Anti-regression: scenery containment ─────────────────────────────────

describe("Atrium: scenery containment + portal depth", () => {
  test("D1. Dossier scenery is clipped inside the dossier cover (overflow hidden)", () => {
    const idx = globalsCss.indexOf(".atelier-dossier-cover");
    const block = globalsCss.slice(idx, idx + 400);
    assert.ok(
      block.includes("overflow: hidden"),
      ".atelier-dossier-cover must clip its scenery — no leak into the page",
    );
    assert.ok(
      block.includes("isolation: isolate"),
      ".atelier-dossier-cover must own its stacking context so scenery cannot leak",
    );
  });

  test("D2. World room switcher still ships the existing portal scenery/doorframe contract", () => {
    // Ensure the World system still owns the portal scenery — the atrium
    // doorway shelf only re-skins composition, never reintroduces a tile.
    assert.ok(worldTsx.includes("WorldPortal"));
    assert.ok(worldTsx.includes("world-portal-scenery"));
    assert.ok(worldTsx.includes("world-portal-doorframe"));
    assert.ok(worldTsx.includes("world-portal-light"));
  });

  test("D3. Components remain world-agnostic — no destination strings in DashboardClient", () => {
    assert.doesNotMatch(
      dashboardClient,
      /\bPortland\b|\bSantorini\b|\bKyoto\b|\bMarrakech\b|\bLisbon\b/,
      "DashboardClient must not name destinations directly — they live in worldData",
    );
  });

  test("D4. No legacy artifact tiles re-introduced via sr-only", () => {
    assert.doesNotMatch(
      dashboardClient,
      /data-legacy-artifact|FolioArtifactTile/,
      "DashboardClient must not preserve legacy artifact tiles via sr-only",
    );
  });
});

// ── E. Behavior preservation ────────────────────────────────────────────────

describe("Atrium: behavior preserved", () => {
  test("E1. All canonical home testids preserved", () => {
    for (const id of [
      "atelier-home",
      "atelier-greeting",
      "concierge-entry",
      "concierge-advisor-desk",
      "atelier-continue-planning",
      "journey-shelf-teaser",
      "atelier-planning-strip",
      "home-new-trip-action",
    ]) {
      assert.match(
        dashboardClient,
        new RegExp(`data-testid="${id}"`),
        `data-testid="${id}" must remain in DashboardClient`,
      );
    }
  });

  test("E2. Routes preserved (/concierge, /trips, /trips/new, /trips/{id})", () => {
    assert.match(dashboardClient, /href="\/concierge"/);
    assert.match(dashboardClient, /href="\/trips"/);
    assert.match(dashboardClient, /href="\/trips\/new"/);
    assert.match(dashboardClient, /href=\{`\/trips\/\$\{trip\.id\}`\}/);
  });

  test("E3. Editorial primitives preserved (folio-display, folio-issue-eyebrow, folio-heading, btn-marine, mapline-rule)", () => {
    for (const cls of [
      "folio-display",
      "folio-issue-eyebrow",
      "folio-heading",
      "btn-marine",
      "mapline-rule",
      "editorial-scene",
      "folio-paper-card",
    ]) {
      assert.ok(
        dashboardClient.includes(cls),
        `DashboardClient must keep ${cls} — folio direction contract`,
      );
    }
  });

  test("E4. Real trip data bindings preserved (no mocks)", () => {
    assert.match(dashboardClient, /trip\.title/);
    assert.match(dashboardClient, /trip\.destination/);
    assert.match(dashboardClient, /trip\.startDate/);
    assert.match(dashboardClient, /trip\.endDate/);
    assert.match(dashboardClient, /trip\.travelers/);
    assert.doesNotMatch(dashboardClient, /mock|fake|sample|dummy/i);
  });

  test("E5. World is still derived from continuePlanning.destination", () => {
    assert.match(
      dashboardClient,
      /pickWorldFromDestination\(continuePlanning\?\.destination\)/,
    );
  });
});

// ── F. Atrium v2 — silent navigation + contained scenery + integrated metadata

describe("Atrium v2: silent navigation (sidebar hidden on Home)", () => {
  const navArtifact = readSrc("components/layout/AtelierNavArtifact.tsx");

  test("F1. AppShell hides the SaaS Sidebar on the Home immersive shell", () => {
    // The Sidebar import + substring stay (Phase 8J contract), but the JSX
    // render must be gated by the isHomePage branch so it does not display.
    assert.match(
      appShell,
      /isHomePage\s*\?\s*null\s*:\s*<Sidebar/,
      "AppShell must hide <Sidebar /> when on the home route — `isHomePage ? null : <Sidebar />`",
    );
  });

  test("F2. AppShell mounts the AtelierNavArtifact floating dock on Home only", () => {
    assert.match(
      appShell,
      /isHomePage\s*&&\s*<AtelierNavArtifact/,
      "AppShell must mount <AtelierNavArtifact /> only when isHomePage is true",
    );
    assert.match(
      appShell,
      /import\s*\{\s*AtelierNavArtifact\s*\}\s*from\s*["'][^"']*AtelierNavArtifact/,
      "AppShell must import AtelierNavArtifact from its layout module",
    );
  });

  test("F3. AtelierNavArtifact exports a dock + drawer, keyboard accessible", () => {
    assert.match(
      navArtifact,
      /export function AtelierNavArtifact/,
      "AtelierNavArtifact must export a React component",
    );
    assert.match(navArtifact, /data-testid="atelier-nav-artifact"/);
    assert.match(navArtifact, /data-testid="atelier-nav-dock"/);
    assert.match(navArtifact, /data-testid="atelier-nav-drawer"/);
    assert.ok(
      navArtifact.includes("Escape"),
      "AtelierNavArtifact must close on Escape (keyboard accessibility)",
    );
    assert.ok(
      navArtifact.includes("aria-expanded"),
      "AtelierNavArtifact dock must expose aria-expanded for accessibility",
    );
  });

  test("F4. AtelierNavArtifact carries the full navigation surface (primary + secondary + sign-out)", () => {
    // Routes must remain reachable from the immersive nav.
    for (const href of [
      '"/"',
      '"/explore"',
      '"/concierge"',
      '"/saved"',
      '"/trips"',
      '"/trips/new"',
      '"/cards"',
      '"/settings"',
    ]) {
      assert.ok(
        navArtifact.includes(`href: ${href}`),
        `AtelierNavArtifact must keep href ${href} in its nav catalogue`,
      );
    }
    assert.ok(
      navArtifact.includes("handleSignOut") && navArtifact.includes("Sign out"),
      "AtelierNavArtifact must expose Sign out via supabase.auth.signOut()",
    );
  });

  test("F5. globals.css ships the atelier-nav-artifact-root + dock + drawer classes", () => {
    for (const cls of [
      ".atelier-nav-artifact-root",
      ".atelier-nav-dock",
      ".atelier-nav-drawer",
      ".atelier-nav-scrim",
      ".atelier-nav-drawer-head",
    ]) {
      assert.ok(globalsCss.includes(cls), `globals.css must define ${cls}`);
    }
    // Drawer entrance animation must respect prefers-reduced-motion.
    assert.ok(
      /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\.atelier-nav-drawer[\s\S]*?animation:\s*none/.test(globalsCss),
      ".atelier-nav-drawer entrance must be disabled under prefers-reduced-motion",
    );
  });
});

describe("Atrium v2: destination scenery is contained, not page wallpaper", () => {
  test("F6. DashboardClient does NOT mount page-wide WorldScenery (no destination wallpaper)", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.doesNotMatch(
      ret,
      /<WorldScenery\b/,
      "DashboardClient must NOT mount a page-wide <WorldScenery /> — destination scenery must live inside the active folio cover and the room portals only",
    );
  });

  test("F7. DashboardClient does NOT import WorldScenery any more", () => {
    assert.doesNotMatch(
      dashboardClient,
      /\bWorldScenery\b/,
      "DashboardClient must no longer import WorldScenery — scenery is contained inside artifacts via --world-scenery* CSS vars",
    );
  });

  test("F8. The atrium root uses the neutral Alabaster background, not the destination --world-bg", () => {
    const ret = dashboardClient.slice(dashboardClient.indexOf("return ("));
    assert.match(
      ret,
      /atelier-atrium-neutral/,
      "DashboardClient must apply atelier-atrium-neutral on the FolioScene so the page is a quiet Alabaster room",
    );
    // CSS must declare the neutral background variant (warm-paper/bone tokens, not destination --world-bg).
    const idx = globalsCss.indexOf(".atelier-atrium-neutral");
    const block = globalsCss.slice(idx, idx + 1000);
    assert.ok(
      block.includes("--ds-warm-paper") && block.includes("--ds-bone"),
      ".atelier-atrium-neutral must paint a paper-warm Alabaster base from --ds-warm-paper + --ds-bone",
    );
    assert.ok(
      !block.includes("var(--world-bg)"),
      ".atelier-atrium-neutral must NOT consume var(--world-bg) — the page is neutral, not a destination wallpaper",
    );
  });

  test("F9. Active folio dossier still owns the destination scenery via --world-scenery vars", () => {
    // The dossier cover is the only allowed home for the destination scenery.
    const idx = globalsCss.indexOf(".atelier-dossier-scenery");
    const block = globalsCss.slice(idx, idx + 800);
    assert.ok(
      block.includes("var(--world-scenery-image") && block.includes("var(--world-scenery)"),
      ".atelier-dossier-scenery must consume --world-scenery* CSS vars (contained scenery)",
    );
  });
});

describe("Atrium v2: integrated metadata + cinematic shelf + physical archive", () => {
  test("F10. Dossier integrates status/dates/travelers in a glass-scrim metadata band", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-dossier-scrim"),
      "Dossier must integrate metadata via the .atelier-dossier-scrim band",
    );
    assert.ok(
      block.includes("TripStatusBadge"),
      "Dossier scrim must include the trip status badge (no orphan metadata outside)",
    );
    // The dossier must own its destination scenery layer.
    assert.ok(
      block.includes("atelier-dossier-scenery"),
      "Dossier must paint destination scenery inside .atelier-dossier-scenery",
    );
    // No orphan two-column dates/party grid outside the dossier scrim.
    assert.ok(
      !block.includes("grid-cols-2 gap-x-6"),
      "Dossier must not expose dates/party as a separate two-column grid outside the scrim",
    );
  });

  test("F11. Curio shelf is a layered book-edge object (three folio spines)", () => {
    // CSS contract — spine bands paint a brass title band per spine.
    assert.match(globalsCss, /\.atelier-curio-spine-band/, ".atelier-curio-spine-band must exist (brass title band on each spine)");
    // Shelf must paint a brass shelf rail along the bottom (cabinet trim).
    assert.match(
      globalsCss,
      /\.atelier-curio-shelf::after[\s\S]*?--ds-(?:ember-brass|sandstone-gold)/,
      ".atelier-curio-shelf::after must paint a brass shelf rail",
    );
  });

  test("F12. Doorway shelf paints a brass shelf rail above the room portals", () => {
    assert.match(globalsCss, /\.atelier-doorway-shelf-rail/, "globals.css must define .atelier-doorway-shelf-rail");
    assert.match(
      dashboardClient,
      /atelier-doorway-shelf-rail/,
      "AtelierPlanningStrip must render the .atelier-doorway-shelf-rail brass rail",
    );
  });

  test("F13. Greeting is rendered as a quiet whisper, not a giant dashboard hero", () => {
    // The whisper modifier must scope the greeting CSS and reduce the display.
    assert.match(globalsCss, /\.atelier-greeting-display/, "globals.css must define .atelier-greeting-display");
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-greeting-whisper"),
      "AtelierGreeting must adopt .atelier-greeting-whisper modifier",
    );
    assert.ok(
      block.includes("atelier-greeting-display"),
      "AtelierGreeting display must adopt .atelier-greeting-display (quiet scale)",
    );
  });
});
