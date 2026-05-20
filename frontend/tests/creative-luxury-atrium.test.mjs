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

  test("B3. The atrium composes a broad hero + a folio/concierge spread", () => {
    // v3+ : the greeting is a broad .atrium-hero; the active folio +
    // concierge sit in a .atelier-atrium-spread row below it.
    assert.match(
      dashboardClient,
      /className=["'][^"']*atrium-hero/,
      "Greeting must use the broad .atrium-hero welcome",
    );
    assert.match(
      dashboardClient,
      /className=["'][^"']*atelier-atrium-spread/,
      "Active folio + concierge must sit in the .atelier-atrium-spread row",
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
    // Flex-stacked cover content (title) + glass-scrim rail. No corporate
    // corner flag and no orphan brass plate (both removed per direction).
    assert.ok(
      block.includes("atelier-dossier-cover-content-flex"),
      "ContinuePlanningStrip must carry the flex-stacked cover content",
    );
    assert.ok(
      block.includes("atelier-dossier-rail"),
      "ContinuePlanningStrip must carry the glass-scrim metadata rail",
    );
    assert.ok(
      !block.includes("atelier-dossier-flag"),
      "ContinuePlanningStrip must NOT carry the corporate corner flag (removed)",
    );
  });

  test("B6. ConciergeEntry is an atmospheric salon portal (warm paper, not a SaaS box)", () => {
    const start = dashboardClient.indexOf("function ConciergeEntry");
    const end = dashboardClient.indexOf("function ContinuePlanningStrip");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-concierge-portal"),
      "ConciergeEntry must compose .atelier-concierge-portal (atmospheric salon, not a pale box)",
    );
    assert.ok(
      block.includes("atelier-concierge-scenery"),
      "ConciergeEntry must paint a salon scenery layer",
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

  test("B8. JourneyShelfTeaser is a physical shelf of dynamic folio cards", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-archive-spines"),
      "JourneyShelfTeaser must carry the .atelier-archive-spines shelf container",
    );
    assert.ok(
      block.includes("atelier-archive-folio") && block.includes("atelier-archive-folio-title"),
      "JourneyShelfTeaser must render folio cards with horizontal titles",
    );
    // Folios are generated from the real trips array (dynamic, not static).
    assert.ok(
      block.includes("spines.map") && block.includes("trip.title"),
      "Archive folios must be generated from the real trips array",
    );
  });

  test("B9. EmptyAtelierHome reads as an atmospheric blank folio (no SaaS empty state)", () => {
    const start = dashboardClient.indexOf("function EmptyAtelierHome");
    const end = dashboardClient.indexOf("// ── Rooms in the house");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-empty-folio"),
      "EmptyAtelierHome must compose the .atelier-empty-folio object",
    );
    // No corporate "TRP · WAITING" status flag in the empty state.
    assert.ok(
      !block.includes("WAITING"),
      "EmptyAtelierHome must NOT show a corporate 'WAITING' status flag",
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
  test("F10. Dossier integrates dates/travelers/Open Folio in a glass-scrim rail (no status pill)", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-dossier-rail"),
      "Dossier must integrate metadata via the .atelier-dossier-rail glass-scrim band",
    );
    // The corporate "Planned" status pill must NOT be rendered on the
    // cover (regression guard — it was explicitly removed).
    assert.ok(
      !block.includes("TripStatusBadge"),
      "Dossier rail must NOT render TripStatusBadge — the status pill was removed per direction",
    );
    // Dates + travelers + Open Folio action must all live in the rail.
    assert.ok(
      block.includes("dateLine") && block.includes("partyLine") && block.includes("Open folio"),
      "Dossier rail must surface dates + travelers + Open folio action",
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

  test("F11. Archive shelf renders portrait folio cards (image + scrim + centered title)", () => {
    // v8: the vertical book-spine metaphor (cropped vertical ciphers +
    // brass rail underline) was replaced with portrait folio CARDS that
    // mirror the room portals — world image behind a centered title.
    assert.match(globalsCss, /\.atelier-archive-folio\b/, ".atelier-archive-folio card must exist");
    assert.match(globalsCss, /\.atelier-archive-folio-image/, ".atelier-archive-folio-image (world image layer) must exist");
    assert.match(globalsCss, /\.atelier-archive-folio-scrim/, ".atelier-archive-folio-scrim (contrast scrim) must exist");
    assert.match(globalsCss, /\.atelier-archive-folio-title/, ".atelier-archive-folio-title (centered horizontal title) must exist");
    // The title must NOT use vertical writing-mode (no cropping).
    const idx = globalsCss.indexOf(".atelier-archive-folio-title");
    const block = globalsCss.slice(idx, idx + 600);
    assert.doesNotMatch(
      block,
      /writing-mode:\s*vertical/,
      ".atelier-archive-folio-title must render horizontally (no vertical writing-mode cropping)",
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

  test("F13. Greeting is rendered as a broad atrium hero (atrium-hero / atrium-hero-display)", () => {
    // v3: the greeting is now a broad editorial welcome, not a widget. The
    // WorldGlassSurface wrapper remains (folio direction contract) but its
    // visual treatment is overridden by .atrium-hero-surface so it reads as
    // an open page, not a floating card.
    assert.match(globalsCss, /\.atrium-hero-display/, "globals.css must define .atrium-hero-display (broad editorial display)");
    assert.match(globalsCss, /\.atrium-hero-surface/, "globals.css must define .atrium-hero-surface (overrides WorldGlassSurface card chrome)");
    const start = dashboardClient.indexOf("function AtelierGreeting");
    const end = dashboardClient.indexOf("function ConciergeEntry");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atrium-hero-surface"),
      "AtelierGreeting WorldGlassSurface must adopt .atrium-hero-surface to break out of widget styling",
    );
    assert.ok(
      block.includes("atrium-hero-display"),
      "AtelierGreeting h1 must adopt .atrium-hero-display (broad editorial scale)",
    );
    // The greeting display reads at editorial cover scale (clamp upper bound
    // must reach at least 3rem to qualify as a hero, not a widget heading).
    const idx = globalsCss.indexOf(".atrium-hero-display");
    const cssBlock = globalsCss.slice(idx, idx + 600);
    assert.match(
      cssBlock,
      /font-size:\s*clamp\([^)]*?(?:4|5|6)(?:\.\d+)?rem\)/,
      ".atrium-hero-display must clamp font-size to a hero scale (≥3rem upper bound)",
    );
  });
});

// ── G. Atrium v3 — contrast engine + typography portals + physical archive

describe("Atrium v3: dynamic contrast engine", () => {
  const worldData = readSrc("lib/worldData.ts");
  const worldTsx = readSrc("components/ui/World.tsx");

  test("G1. LocationData.WorldVisualLayer declares contrastTone", () => {
    assert.match(
      worldData,
      /contrastTone\?:\s*["']light["']\s*\|\s*["']dark["']/,
      "WorldVisualLayer must declare `contrastTone?: 'light' | 'dark'` for the luminance-aware scenic text contract",
    );
  });

  test("G2. Curated worlds declare contrastTone (Portland=light, Santorini=dark, Atelier=dark)", () => {
    const portlandIdx = worldData.indexOf('location: "Portland"');
    assert.ok(portlandIdx > -1);
    const portlandBlock = worldData.slice(portlandIdx, portlandIdx + 2200);
    assert.match(
      portlandBlock,
      /contrastTone:\s*["']light["']/,
      "Portland (dark forest) must declare contrastTone: 'light' so text becomes cream",
    );
    const santoriniIdx = worldData.indexOf('location: "Santorini"');
    const santoriniBlock = worldData.slice(santoriniIdx, santoriniIdx + 2200);
    assert.match(
      santoriniBlock,
      /contrastTone:\s*["']dark["']/,
      "Santorini (bright sun + caldera) must declare contrastTone: 'dark' so text becomes ink",
    );
    const atelierIdx = worldData.indexOf('location: "Atelier"');
    const atelierBlock = worldData.slice(atelierIdx, atelierIdx + 2200);
    assert.match(
      atelierBlock,
      /contrastTone:\s*["']dark["']/,
      "Atelier (warm paper foyer) must declare contrastTone: 'dark'",
    );
  });

  test("G3. worldStyleVars emits --world-on-scenery, --world-on-scenery-muted, --world-scenery-scrim", () => {
    for (const v of [
      "--world-on-scenery",
      "--world-on-scenery-muted",
      "--world-scenery-scrim",
      "--world-contrast-tone",
    ]) {
      assert.ok(
        worldData.includes(v),
        `worldStyleVars must publish ${v} for the dynamic contrast engine`,
      );
    }
  });

  test("G4. Dossier scenic text consumes --world-on-scenery (no dark-on-dark)", () => {
    // The dossier title/place/caption rendered over destination scenery must
    // read from --world-on-scenery so it adapts per-world.
    assert.match(
      globalsCss,
      /\.atelier-dossier-title[\s\S]*?var\(--world-on-scenery/,
      ".atelier-dossier-title must consume var(--world-on-scenery) — no hardcoded dark text over scenery",
    );
    assert.match(
      globalsCss,
      /\.atelier-dossier-caption[\s\S]*?var\(--world-on-scenery-muted/,
      ".atelier-dossier-caption must consume var(--world-on-scenery-muted)",
    );
  });

  test("G5. WorldCanvas + WorldPortal expose data-scenery-tone for per-tone styling", () => {
    assert.match(worldTsx, /data-scenery-tone=/);
    // Both root WorldCanvas and inner WorldPortal must emit the attribute.
    const count = (worldTsx.match(/data-scenery-tone=/g) ?? []).length;
    assert.ok(count >= 2, `data-scenery-tone must appear on both WorldCanvas and WorldPortal (got ${count})`);
  });

  test("G6. FolioScene root on DashboardClient carries data-scenery-tone", () => {
    assert.match(
      dashboardClient,
      /data-scenery-tone=\{world\.visualLayer\.contrastTone[\s\S]*?\}/,
      "DashboardClient FolioScene must expose data-scenery-tone from the active world",
    );
  });
});

describe("Atrium v3: typography-first portals", () => {
  test("G7. Portal eyebrow is sr-only (typography-first, no eyebrow + label + whisper trio)", () => {
    const worldTsx = readSrc("components/ui/World.tsx");
    // The eyebrow remains in the DOM for assistive tech, but the visible
    // surface is title + descriptor only.
    assert.match(
      worldTsx,
      /world-portal-eyebrow[\s\S]{0,20}sr-only/,
      ".world-portal-eyebrow must carry sr-only — portals lead with the label, not a redundant eyebrow",
    );
  });

  test("G8. globals.css gives portals a typographic glow halo (atmosphere behind type)", () => {
    // Within the doorway shelf, the portal must paint a soft halo BEHIND
    // the typography so the surface is not a flat color block.
    assert.match(
      globalsCss,
      /\.atelier-doorway-shelf\s*\.world-portal::before[\s\S]*?radial-gradient/,
      ".atelier-doorway-shelf .world-portal::before must paint a radial halo behind the typography",
    );
  });

  test("G9. Portal label scale is editorial (≥2rem upper bound)", () => {
    // Find the doorway-shelf-scoped label rule and check the clamp upper bound.
    const idx = globalsCss.indexOf(".atelier-doorway-shelf .world-portal-label");
    assert.ok(idx > -1, ".atelier-doorway-shelf .world-portal-label must exist");
    const block = globalsCss.slice(idx, idx + 600);
    assert.match(
      block,
      /font-size:\s*clamp\([^)]*?(?:2|3)(?:\.\d+)?rem\)/,
      ".atelier-doorway-shelf .world-portal-label must clamp font-size to an editorial display scale (≥2rem upper bound)",
    );
  });

  test("G10. ROOM_CATALOGUE descriptors are full editorial phrases, not redundant 'the foo' labels", () => {
    const worldData = readSrc("lib/worldData.ts");
    // The whispers must be real descriptors that don't echo the label.
    assert.match(
      worldData,
      /whisper:\s*["']Private dining, stays, and local intelligence\./,
      "Concierge whisper must read as an editorial descriptor",
    );
    assert.match(
      worldData,
      /whisper:\s*["']Shape the journey\./,
      "Planning whisper must read as an editorial descriptor",
    );
    assert.match(
      worldData,
      /whisper:\s*["']Your private archive\./,
      "Saved whisper must read as an editorial descriptor",
    );
    // None of the whispers should be the redundant "the foo" pattern.
    assert.doesNotMatch(
      worldData,
      /whisper:\s*["']the (?:private salon|observatory|drafting atelier|scrapbook library)["']/,
      "ROOM_CATALOGUE whispers must not be redundant 'the foo' echoes of the label",
    );
  });
});

describe("Atrium v3: physical archive + engraved actions", () => {
  test("G11. Archive section renders dynamic folio cards from real trips", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    for (const cls of [
      "atelier-archive-spines",
      "atelier-archive-folio",
      "atelier-archive-folio-image",
      "atelier-archive-folio-scrim",
      "atelier-archive-folio-title",
      "atelier-archive-plate",
    ]) {
      assert.ok(
        block.includes(cls),
        `JourneyShelfTeaser must render .${cls} (folio-card archive contract)`,
      );
    }
    // Folio cards are driven by the real trips array (dynamic count + title).
    assert.ok(
      block.includes("trips.slice") && block.includes("trip.title"),
      "Archive folios must be generated from the real trips array (dynamic content)",
    );
    // Each folio inherits its destination world via pickWorldFromDestination.
    assert.ok(
      block.includes("pickWorldFromDestination(trip.destination)"),
      "Each folio must resolve its destination world for the cover image + palette",
    );
  });

  test("G12. Archive folio title is horizontal + image-backed (no vertical cropping, no dead rail)", () => {
    // The trip title sits front-and-center over the world image.
    assert.match(globalsCss, /\.atelier-archive-folio-title/, ".atelier-archive-folio-title must exist");
    // The dead brass rail under the spines must be removed.
    assert.match(
      globalsCss,
      /\.atelier-archive-rail\s*\{[^}]*display:\s*none/,
      ".atelier-archive-rail must be removed (display: none) — the dead linen underline is gone",
    );
    // The folio image layer reads the destination world image var.
    const idx = globalsCss.indexOf(".atelier-archive-folio-image");
    const block = globalsCss.slice(idx, idx + 400);
    assert.match(
      block,
      /var\(--spine-image/,
      ".atelier-archive-folio-image must paint the destination world image via --spine-image",
    );
  });

  test("G13. New trip + View all use the engraved-tab pattern (tactile, accessible)", () => {
    const start = dashboardClient.indexOf("function JourneyShelfTeaser");
    const end = dashboardClient.indexOf("function EmptyAtelierHome");
    const block = dashboardClient.slice(start, end);
    assert.ok(
      block.includes("atelier-engraved-tab"),
      "New trip + View all must adopt .atelier-engraved-tab (no longer buried inline links)",
    );
    // CSS must define the tab with the brass treatment + min-height 44px.
    const idx = globalsCss.indexOf(".atelier-engraved-tab {");
    assert.ok(idx > -1, ".atelier-engraved-tab must be defined in globals.css");
    const cssBlock = globalsCss.slice(idx, idx + 1600);
    assert.match(cssBlock, /min-height:\s*44px/, ".atelier-engraved-tab must enforce a 44px touch target");
    assert.match(cssBlock, /--ds-ember-brass/, ".atelier-engraved-tab must consume brass tokens");
  });

  test("G14. Engraved-tab respects prefers-reduced-motion", () => {
    assert.match(
      globalsCss,
      /@media \(prefers-reduced-motion:\s*reduce\)\s*\{[\s\S]*?\.atelier-engraved-tab[\s\S]*?transition:\s*none/,
      ".atelier-engraved-tab must disable transitions under prefers-reduced-motion",
    );
  });
});

describe("Atrium v3: silent footer (no Portland · Misty forest narration)", () => {
  test("G15. WorldWayfinder footer is sr-only — class names remain for the wayfinder-quiet contract", () => {
    // The visible page must NOT narrate the destination at the bottom.
    // Class names stay in source so prior contracts pass, but the actual
    // wayfinder is rendered inside an sr-only footer.
    assert.match(
      dashboardClient,
      /atelier-atrium-signature[\s\S]{0,40}sr-only/,
      "The atelier-atrium-signature footer must carry sr-only so the Portland · Misty forest line is no longer visible",
    );
    // The WorldWayfinder + world-wayfinder-quiet class are still referenced.
    assert.match(dashboardClient, /world-wayfinder-quiet/);
    assert.match(dashboardClient, /WorldWayfinder/);
  });
});

describe("Atrium I: no excessive bottom dead space on Home", () => {
  // Guards against the flex: 1 1 auto / min-height: 100vh combination that
  // caused atelier-atrium-neutral to grow beyond its content, leaving a blank
  // neutral-background void below the Travel Archive section (PR #448 residual).

  test("I1. atelier-atrium-neutral sets flex: none (not flex: 1) as its final rule", () => {
    // The override must appear AFTER the flex: 1 1 auto rule so CSS source-
    // order gives it priority within the same @layer specificity.
    const lastFlex1Pos = globalsCss.lastIndexOf("flex: 1 1 auto");
    const lastFlexNonePos = globalsCss.lastIndexOf("flex: none");
    assert.ok(lastFlex1Pos !== -1, "atelier-atrium-neutral flex: 1 1 auto rule must still exist (v4 intent preserved)");
    assert.ok(lastFlexNonePos !== -1, "a flex: none override must exist to prevent atrium expanding beyond content");
    assert.ok(
      lastFlexNonePos > lastFlex1Pos,
      "flex: none must appear AFTER flex: 1 1 auto in globals.css so it wins the cascade",
    );
  });

  test("I2. home-edge-bleed padding-bottom is overridden to 0 (desktop) to remove mobile-nav-spacer redundancy", () => {
    // The mobile-nav-spacer class adds 88px on mobile — redundant once
    // atelier-atrium-content provides its own nav clearance.  The home-edge-
    // bleed rule must neutralise it via a later same-specificity rule.
    const allMatches = [...globalsCss.matchAll(/\.home-edge-bleed\s*\{([^}]*)\}/g)];
    const hasZeroPb = allMatches.some(m => /padding-bottom:\s*0\b/.test(m[1]));
    assert.ok(hasZeroPb, ".home-edge-bleed must declare padding-bottom: 0 to neutralise the outer mobile-nav-spacer gap");
  });

  test("I3. atelier-atrium-content includes mobile nav clearance on mobile breakpoint", () => {
    // The inner content container now owns mobile nav clearance so the outer
    // home-edge-bleed wrapper can be zero-padded.
    assert.match(
      globalsCss,
      /max-width:\s*1023px[\s\S]*?\.atelier-atrium-content[\s\S]*?padding-bottom:\s*max\(3\.5rem/,
      "A @media (max-width: 1023px) block must set atelier-atrium-content padding-bottom to max(3.5rem,...) for mobile nav clearance",
    );
  });

  test("I4. atelier-atrium padding-bottom is forced to 0 (no extra outer space below content)", () => {
    assert.match(
      globalsCss,
      /\.atelier-atrium\s*\{\s*padding-bottom:\s*0\s*!important/,
      ".atelier-atrium must have padding-bottom: 0 !important to prevent double-counting with atelier-atrium-content",
    );
  });

  test("I5. atelier-atrium-content has editorial pb on desktop (clamp, no oversized mob pad)", () => {
    assert.match(
      globalsCss,
      /\.atelier-atrium-content\s*\{\s*padding-bottom:\s*clamp\(28px/,
      ".atelier-atrium-content must use clamp(28px,...) editorial padding-bottom on desktop",
    );
  });

  test("I6. home-edge-bleed final min-height rule is 0 — overrides both the 100vh desktop and mobile calc rules", () => {
    // The v6 CSS added min-height: 100vh (and calc(100vh-3.5rem) on mobile) to
    // home-edge-bleed. After setting flex:none on the atrium, the flex container
    // retains that min-height floor, leaving dead space below the content.
    // The override at the end of the same @layer block must set min-height: 0.
    const allMatches = [...globalsCss.matchAll(/\.home-edge-bleed\s*\{([^}]*)\}/g)];
    const lastMatch = allMatches[allMatches.length - 1];
    assert.ok(lastMatch != null, ".home-edge-bleed must appear in globals.css");
    // Walk backward: the final instance that declares min-height must be 0.
    const minHeightBlocks = allMatches.filter(m => /min-height/.test(m[1]));
    assert.ok(minHeightBlocks.length > 0, "At least one .home-edge-bleed block must declare min-height");
    const last = minHeightBlocks[minHeightBlocks.length - 1];
    assert.match(
      last[1],
      /min-height:\s*0\b/,
      "The last .home-edge-bleed block declaring min-height must set it to 0 (content-sized floor)"
    );
  });

  test("I7. archive section wrappers have no min-height: 100vh/dvh/svh", () => {
    // Archive wrappers must never claim a full-screen height on their own.
    const archiveBlock = (() => {
      const start = globalsCss.indexOf(".atelier-archive-section");
      const end = globalsCss.indexOf(".atelier-engraved-tab");
      return start !== -1 && end !== -1 ? globalsCss.slice(start, end) : globalsCss;
    })();
    assert.doesNotMatch(
      archiveBlock,
      /\.atelier-archive[\w-]*\s*\{[^}]*min-height:\s*100(?:vh|dvh|svh)/,
      "Archive wrapper classes must not set min-height: 100vh/dvh/svh — archive must be content-height"
    );
  });

  test("I8. atelier-atrium-signature sr-only footer has no layout height (no padding/margin reserving space)", () => {
    // The sr-only class collapses the element; the signature footer must not add
    // its own padding/margin that re-introduces dead space.
    const start = globalsCss.indexOf(".atelier-atrium-signature");
    if (start === -1) return; // class may live solely via sr-only Tailwind
    const block = globalsCss.slice(start, start + 400);
    assert.doesNotMatch(
      block,
      /padding(?:-top|-bottom)?:\s*(?:[1-9]\d*(?:px|rem|vh|dvh))/,
      ".atelier-atrium-signature must not reserve layout space with padding (it is sr-only)"
    );
  });

  test("I9. home-edge-bleed retains overflow-x-clip (no horizontal overflow bleed)", () => {
    // The overflow-x: clip on home-edge-bleed keeps horizontal containment;
    // it must survive the min-height fix.
    assert.match(
      globalsCss,
      /\.home-edge-bleed[\s\S]*?overflow-x:\s*clip/,
      ".home-edge-bleed must retain overflow-x: clip for horizontal containment"
    );
  });

  test("I10. atelier-atrium-content has overflow:clip (not just overflow-x) to contain decorative blob scroll overflow", () => {
    // Root cause of the mobile blank-space bug (PR #449):
    //   folio-living-canvas::after is position:absolute with bottom:-22%,
    //   which extends 22% of the canvas height BELOW the content area.
    //   Without overflow-y containment, this blob propagates into main's
    //   overflow-y:auto scroll container, creating a large blank scrollable
    //   region after the final archive section. DevTools identifies `main`
    //   as the element in the blank area because no DOM box covers that region.
    //   overflow:clip (not overflow:hidden) is used because it does not create
    //   a new block formatting context — sticky positioning and margin collapsing
    //   inside atelier-atrium-content are unaffected.
    const matches = [...globalsCss.matchAll(/\.atelier-atrium-content\s*\{([^}]*)\}/g)];
    const hasOverflowClip = matches.some(m =>
      /overflow\s*:\s*clip\b/.test(m[1]) ||
      (/overflow-x\s*:\s*clip\b/.test(m[1]) && /overflow-y\s*:\s*clip\b/.test(m[1]))
    );
    assert.ok(
      hasOverflowClip,
      "atelier-atrium-content must have overflow:clip (or overflow-x:clip + overflow-y:clip) to contain the decorative blob and prevent blank scroll area in main"
    );
    // Confirm NOT overflow:hidden (would create BFC side-effects)
    const hasOverflowHidden = matches.some(m => /overflow\s*:\s*hidden\b/.test(m[1]));
    assert.ok(
      !hasOverflowHidden,
      "atelier-atrium-content must NOT use overflow:hidden — use overflow:clip to avoid BFC side-effects"
    );
  });
});

describe("Atrium v9: guaranteed-readable text + reusable brand mark", () => {
  const navArtifact = readSrc("components/layout/AtelierNavArtifact.tsx");
  const sidebar = readSrc("components/layout/Sidebar.tsx");
  const brandMark = readSrc("components/layout/BrandMark.tsx");

  test("H1. Dossier title + dates + travelers + Open Folio share ONE dark panel", () => {
    const start = dashboardClient.indexOf("function ContinuePlanningStrip");
    const end = dashboardClient.indexOf("function JourneyShelfTeaser");
    const block = dashboardClient.slice(start, end);
    // All metadata is consolidated into the cover-content panel — there is
    // no separate fragile rail div anymore.
    assert.ok(
      block.includes("atelier-dossier-cover-content-flex") &&
        block.includes("atelier-dossier-meta") &&
        block.includes("atelier-dossier-meta-action"),
      "Dossier title + meta row must live in the cover-content panel",
    );
    assert.ok(
      block.includes("dateLine") && block.includes("partyLine") && block.includes("Open folio"),
      "Dossier panel must surface dates + travelers + Open Folio",
    );
  });

  test("H2. Dossier panel forces cream text on its dark plate (no dark-on-dark / contrast-tone trap)", () => {
    // The panel is always dark (world-ink gradient), so its text must be
    // unconditionally cream — overriding the [data-scenery-tone] contrast
    // engine via higher specificity + !important.
    assert.match(
      globalsCss,
      /\.atelier-dossier-cover-flex \.atelier-dossier-cover-content-flex \.atelier-dossier-title[\s\S]*?color:\s*var\(--ds-warm-paper\)\s*!important/,
      "Dossier title must be forced cream on the dark panel",
    );
    assert.match(
      globalsCss,
      /\.atelier-dossier-cover-content\.atelier-dossier-cover-content-flex[\s\S]*?background:[\s\S]*?var\(--world-ink\)[\s\S]*?!important/,
      "Dossier panel must paint a guaranteed-dark world-ink plate",
    );
  });

  test("H3. Shelf folio title sits on a strong dark plate + cream type (readable on any image)", () => {
    // The folio carries a dedicated dark base band (::after) so the title
    // is readable even where the image is bright (city amber horizon, beach).
    assert.match(
      globalsCss,
      /\.atelier-archive-folio::after[\s\S]*?var\(--spine-ink/,
      ".atelier-archive-folio::after must paint a dark base plate behind the title",
    );
    assert.match(
      globalsCss,
      /\.atelier-archive-folio-title[\s\S]*?color:\s*var\(--ds-warm-paper\)\s*!important/,
      ".atelier-archive-folio-title must be forced cream",
    );
  });

  test("H4. Brand mark is a reusable component used by Sidebar AND the Home nav dock", () => {
    assert.match(brandMark, /export function BrandMark/, "BrandMark must be a reusable exported component");
    assert.match(brandMark, /bg-ds-marine-ink/, "BrandMark chip must be marine-ink");
    assert.match(brandMark, /text-ds-paper/, "BrandMark airplane must be cream/paper (white outline)");
    assert.ok(
      sidebar.includes("<BrandMark") && sidebar.includes('from "./BrandMark"'),
      "Sidebar must use the shared BrandMark",
    );
    assert.ok(
      navArtifact.includes("<BrandMark") && navArtifact.includes('from "./BrandMark"'),
      "AtelierNavArtifact (home dock + drawer) must use the shared BrandMark",
    );
    // The home dock must no longer hand-roll a Plane glyph that could go dark.
    assert.ok(
      !navArtifact.includes("<Plane"),
      "AtelierNavArtifact must not hand-roll a Plane icon — it uses the shared BrandMark",
    );
  });
});
