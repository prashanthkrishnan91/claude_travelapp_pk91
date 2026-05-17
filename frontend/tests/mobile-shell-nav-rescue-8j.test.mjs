/**
 * Phase 8J — Mobile Shell / Nav Rescue contract tests
 *
 * Verifies:
 *  - MOBILE_DESIGN_LANGUAGE.md exists with required rule sections
 *  - Bottom nav has exactly 4 primary tabs (Home, Discover, Saved, My Trips)
 *  - Giant center "New Trip" bottom-nav action is gone
 *  - Contextual New Trip is present on Home and My Trips pages
 *  - Bottom nav uses safe-area-inset-bottom via CSS
 *  - Bottom nav touch targets are 44px+
 *  - Top bar uses boutique midnight surface + preserves brand/menu
 *  - Mobile page content wrapper includes mobile-nav-spacer clearance
 *  - No backend/provider imports in touched shell/nav files
 *  - No fake/mock/sample data or hardcoded city prompts
 *  - No raw hex / raw rgba / focus:ring in touched shell/nav files
 *  - All non-submit buttons in touched files have type="button"
 *  - Existing route hrefs and nav labels remain valid
 *  - AppShell uses mobile-nav-spacer (not pb-24 hard-coded)
 *  - globals.css defines the mobile-nav-spacer, mobile-bottom-nav, mobile-tab-item utilities
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const srcRoot = resolve(root, "src");
const docsRoot = resolve(root, "..", "docs");

function readSrc(relPath) {
  return readFileSync(resolve(srcRoot, relPath), "utf8");
}
function readDocs(relPath) {
  return readFileSync(resolve(docsRoot, relPath), "utf8");
}
function srcExists(relPath) {
  return existsSync(resolve(srcRoot, relPath));
}
function docsExists(relPath) {
  return existsSync(resolve(docsRoot, relPath));
}

// ── 1. MOBILE_DESIGN_LANGUAGE.md ─────────────────────────────────────────────

describe("MOBILE_DESIGN_LANGUAGE.md exists and defines required rules", () => {
  it("file exists at docs/product/MOBILE_DESIGN_LANGUAGE.md", () => {
    assert.ok(
      docsExists("product/MOBILE_DESIGN_LANGUAGE.md"),
      "MOBILE_DESIGN_LANGUAGE.md must exist"
    );
  });

  it("defines one screen one primary job principle", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("one screen") || src.includes("one primary job"),
      "must define one-screen-one-job principle"
    );
  });

  it("specifies 4-tab bottom nav rule", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("4-tab") || src.includes("4 primary destinations"),
      "must specify 4-tab nav"
    );
  });

  it("documents contextual primary action pattern", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("contextual") && (src.includes("New Trip") || src.includes("primary action")),
      "must document contextual primary action"
    );
  });

  it("specifies 44px minimum touch target rule", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(src.includes("44"), "must specify 44px touch target minimum");
  });

  it("specifies bottom-safe-area rules", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("safe-area") || src.includes("safe area"),
      "must document safe-area inset handling"
    );
  });

  it("defines mobile page spacing rules", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("mobile-nav-spacer") || src.includes("clearance") || src.includes("padding"),
      "must define mobile page spacing rules"
    );
  });

  it("documents boutique visual principles", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("midnight") || src.includes("atelier"),
      "must document warm dark atelier visual principles"
    );
  });

  it("references section/tray/bottom-sheet language for future phases", () => {
    const src = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      src.includes("tray") || src.includes("bottom-sheet") || src.includes("section"),
      "must include tray/bottom-sheet language for future phases"
    );
  });
});

// ── 2. Bottom nav — 4 tabs, no giant center New ──────────────────────────────

describe("MobileNav — bottom tab bar has exactly 4 destinations", () => {
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("tabLinks array has exactly 4 items", () => {
    // Count items in tabLinks — look for href entries in the array literal
    const tabLinksMatch = nav.match(/const tabLinks\s*=\s*\[([\s\S]*?)\];/);
    assert.ok(tabLinksMatch, "tabLinks array must exist");
    const tabLinksBody = tabLinksMatch[1];
    const hrefCount = (tabLinksBody.match(/href:/g) || []).length;
    assert.equal(hrefCount, 4, `Expected 4 tabLinks, got ${hrefCount}`);
  });

  it("tab links include Home (/)", () => {
    assert.ok(nav.includes('href: "/"') || nav.includes("href: '/'"), "must include Home tab");
  });

  it("tab links include Discover/Explore (/explore)", () => {
    assert.ok(
      nav.includes('href: "/explore"') || nav.includes("href: '/explore'"),
      "must include Explore/Discover tab"
    );
  });

  it("tab links include Saved (/saved)", () => {
    assert.ok(
      nav.includes('href: "/saved"') || nav.includes("href: '/saved'"),
      "must include Saved tab"
    );
  });

  it("tab links include My Trips (/trips)", () => {
    assert.ok(
      nav.includes('href: "/trips"') || nav.includes("href: '/trips'"),
      "must include My Trips tab"
    );
  });
});

describe("MobileNav — giant center New Trip button is removed from bottom nav", () => {
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("tabLinks does NOT include /trips/new", () => {
    const tabLinksMatch = nav.match(/const tabLinks\s*=\s*\[([\s\S]*?)\];/);
    assert.ok(tabLinksMatch, "tabLinks array must exist");
    const tabLinksBody = tabLinksMatch[1];
    assert.ok(
      !tabLinksBody.includes("/trips/new"),
      "tabLinks must NOT contain /trips/new (removed from bottom nav)"
    );
  });

  it("no isNew elevated-center-button pattern in bottom nav render", () => {
    // The old pattern used isNew with special -mt-4 negative margin for center elevation
    assert.ok(
      !nav.includes("-mt-4"),
      "elevated center button (-mt-4) must not appear in MobileNav"
    );
  });

  it("no 'New Trip' label in tabLinks", () => {
    const tabLinksMatch = nav.match(/const tabLinks\s*=\s*\[([\s\S]*?)\];/);
    assert.ok(tabLinksMatch, "tabLinks must exist");
    const tabLinksBody = tabLinksMatch[1];
    assert.ok(
      !tabLinksBody.includes("New Trip"),
      "tabLinks must not have 'New Trip' label — it was removed from bottom nav"
    );
  });

  it("no isNew variable or special new-button logic in the file", () => {
    assert.ok(
      !nav.includes("isNew"),
      "'isNew' variable must be removed (no special center New button)"
    );
  });
});

// ── 3. Contextual New Trip on Home and Trips pages ──────────────────────────

describe("Contextual New Trip is available on Home (DashboardClient) via real Link", () => {
  const dashboard = readSrc("components/dashboard/DashboardClient.tsx");

  it("home-new-trip-action testid exists in DashboardClient", () => {
    assert.ok(
      dashboard.includes('data-testid="home-new-trip-action"'),
      "DashboardClient must have data-testid='home-new-trip-action' on a New Trip link"
    );
  });

  it("home-new-trip-action links to /trips/new", () => {
    const pattern = /data-testid="home-new-trip-action"[\s\S]{0,200}\/trips\/new|\/trips\/new[\s\S]{0,200}data-testid="home-new-trip-action"/;
    assert.ok(
      pattern.test(dashboard),
      "home-new-trip-action must link to /trips/new"
    );
  });

  it("no backend imports in DashboardClient", () => {
    assert.ok(
      !dashboard.includes('from "@/backend') && !dashboard.includes("from '../backend"),
      "DashboardClient must not import backend modules"
    );
  });
});

describe("Contextual New Trip is available on My Trips page via real Link", () => {
  const tripsPage = readSrc("app/trips/page.tsx");

  it("trips-new-trip-action testid exists in trips/page.tsx", () => {
    assert.ok(
      tripsPage.includes('data-testid="trips-new-trip-action"'),
      "trips/page.tsx must have data-testid='trips-new-trip-action' on a New Trip link"
    );
  });

  it("trips-new-trip-action links to /trips/new", () => {
    const pattern = /data-testid="trips-new-trip-action"[\s\S]{0,300}\/trips\/new|\/trips\/new[\s\S]{0,300}data-testid="trips-new-trip-action"/;
    assert.ok(
      pattern.test(tripsPage),
      "trips-new-trip-action must link to /trips/new"
    );
  });
});

// ── 4. Bottom nav safe-area and touch targets ────────────────────────────────

describe("Bottom nav — safe-area inset handling", () => {
  it("MobileNav uses mobile-bottom-nav class (CSS handles safe-area)", () => {
    const nav = readSrc("components/layout/MobileNav.tsx");
    assert.ok(
      nav.includes("mobile-bottom-nav"),
      "bottom nav must use mobile-bottom-nav CSS class"
    );
  });

  it("globals.css mobile-tab-item uses env(safe-area-inset-bottom)", () => {
    const css = readSrc("app/globals.css");
    assert.ok(
      css.includes("mobile-tab-item") && css.includes("safe-area-inset-bottom"),
      "mobile-tab-item must include env(safe-area-inset-bottom) for safe area"
    );
  });

  it("globals.css mobile-bottom-nav is defined", () => {
    const css = readSrc("app/globals.css");
    assert.ok(css.includes(".mobile-bottom-nav"), "globals.css must define .mobile-bottom-nav");
  });
});

describe("Bottom nav — touch targets are 44px+", () => {
  it("globals.css mobile-tab-item has min-height calc including 3.5rem (56px) base", () => {
    const css = readSrc("app/globals.css");
    // 3.5rem = 56px which exceeds 44px minimum
    assert.ok(
      css.includes("mobile-tab-item") && css.includes("3.5rem"),
      "mobile-tab-item must have min-height of at least 3.5rem (56px)"
    );
  });

  it("mobile-tab-icon has min width for 44px horizontal touch coverage", () => {
    const css = readSrc("app/globals.css");
    assert.ok(
      css.includes("mobile-tab-icon") && css.includes("2.75rem"),
      "mobile-tab-icon must be 2.75rem (44px) wide"
    );
  });
});

// ── 5. Top bar — boutique surface and brand preserved ────────────────────────

describe("Top shell/header — boutique surface with brand preserved", () => {
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("mobile-top-bar CSS class is used on the header", () => {
    assert.ok(
      nav.includes("mobile-top-bar"),
      "top bar must use mobile-top-bar CSS class"
    );
  });

  it("globals.css defines .mobile-top-bar with midnight base", () => {
    const css = readSrc("app/globals.css");
    assert.ok(
      css.includes(".mobile-top-bar"),
      "globals.css must define .mobile-top-bar"
    );
    const topBarIdx = css.indexOf(".mobile-top-bar");
    const topBarBlock = css.slice(topBarIdx, topBarIdx + 200);
    assert.ok(
      topBarBlock.includes("midnight") || topBarBlock.includes("ds-midnight-ink"),
      ".mobile-top-bar must use midnight-ink background token"
    );
  });

  it("brand Plane icon is rendered in top bar", () => {
    assert.ok(nav.includes("Plane"), "top bar must include the Plane brand icon");
  });

  it("Travel Concierge brand label is in top bar", () => {
    assert.ok(
      nav.includes("Travel Concierge"),
      "top bar must include the Travel Concierge brand label"
    );
  });

  it("hamburger menu button (Toggle menu) is preserved", () => {
    assert.ok(
      nav.includes('"Toggle menu"') || nav.includes("Toggle menu"),
      "top bar must preserve the hamburger menu button (aria-label Toggle menu)"
    );
  });

  it("top bar data-testid is present for testability", () => {
    assert.ok(
      nav.includes('data-testid="mobile-top-bar"'),
      "top bar must have data-testid='mobile-top-bar'"
    );
  });
});

// ── 6. Mobile page content — bottom nav clearance ────────────────────────────

describe("Mobile page content wrapper includes bottom nav clearance", () => {
  const shell = readSrc("components/layout/AppShell.tsx");
  const css = readSrc("app/globals.css");

  it("AppShell content wrapper uses mobile-nav-spacer class", () => {
    assert.ok(
      shell.includes("mobile-nav-spacer"),
      "AppShell content div must include mobile-nav-spacer CSS class"
    );
  });

  it("AppShell no longer uses raw pb-24 hard-coded bottom clearance", () => {
    assert.ok(
      !shell.includes("pb-24"),
      "AppShell must not use pb-24 — mobile-nav-spacer handles clearance"
    );
  });

  it("globals.css mobile-nav-spacer is defined with max() / calc()", () => {
    assert.ok(
      css.includes(".mobile-nav-spacer"),
      "globals.css must define .mobile-nav-spacer"
    );
    const idx = css.indexOf(".mobile-nav-spacer");
    const block = css.slice(idx, idx + 200);
    assert.ok(
      block.includes("max(") || block.includes("calc("),
      "mobile-nav-spacer must use max() or calc() for dynamic clearance"
    );
  });

  it("globals.css mobile-nav-spacer has desktop override at lg breakpoint", () => {
    const css2 = readSrc("app/globals.css");
    assert.ok(
      css2.includes("mobile-nav-spacer") && css2.includes("min-width: 1024px"),
      "mobile-nav-spacer must have @media (min-width: 1024px) override"
    );
  });

  it("AppShell content wrapper has mobile-page-content testid", () => {
    assert.ok(
      shell.includes('data-testid="mobile-page-content"'),
      "AppShell content wrapper must have data-testid='mobile-page-content'"
    );
  });
});

// ── 7. No backend/provider imports in touched shell/nav files ─────────────────

describe("No backend or provider imports in touched shell/nav files", () => {
  const files = [
    "components/layout/MobileNav.tsx",
    "components/layout/AppShell.tsx",
    "components/dashboard/DashboardClient.tsx",
  ];

  const forbiddenImportPatterns = [
    /from ['"]@\/backend/,
    /from ['"]\.\.\/backend/,
    /from ['"]\.\.\/services/,
    /from ['"]@\/services/,
    /tavily/i,
    /duffel/i,
    /provider_registry/i,
  ];

  for (const file of files) {
    it(`${file} has no backend/provider imports`, () => {
      const src = readSrc(file);
      for (const pattern of forbiddenImportPatterns) {
        assert.ok(
          !pattern.test(src),
          `${file} must not import backend/provider modules (found: ${pattern})`
        );
      }
    });
  }
});

// ── 8. No fake/mock data or hardcoded city prompts ───────────────────────────

describe("No fake/mock/sample visible data or hardcoded city prompts in shell/nav", () => {
  const mobileNavSrc = readSrc("components/layout/MobileNav.tsx");

  it("MobileNav has no hardcoded city names", () => {
    const fakeCities = ["Paris", "Tokyo", "Barcelona", "Bali", "New York", "London"];
    for (const city of fakeCities) {
      assert.ok(
        !mobileNavSrc.includes(city),
        `MobileNav must not contain hardcoded city name: ${city}`
      );
    }
  });

  it("MobileNav has no placeholder luxury copy", () => {
    const forbiddenPhrases = ["e.g.", "example", "lorem ipsum", "placeholder", "sample"];
    for (const phrase of forbiddenPhrases) {
      assert.ok(
        !mobileNavSrc.toLowerCase().includes(phrase),
        `MobileNav must not contain placeholder copy: ${phrase}`
      );
    }
  });
});

// ── 9. No raw hex / raw rgba / focus:ring in touched shell/nav files ──────────

describe("No raw hex, raw rgba, or focus:ring in newly touched shell/nav surfaces", () => {
  const filesToCheck = [
    "components/layout/MobileNav.tsx",
    "components/layout/AppShell.tsx",
  ];

  for (const file of filesToCheck) {
    it(`${file} has no focus:ring- legacy pattern`, () => {
      const src = readSrc(file);
      assert.ok(
        !src.includes("focus:ring-"),
        `${file} must not use focus:ring- (use focus-visible:outline)`
      );
    });
  }

  it("globals.css mobile nav section has no raw hex in new CSS classes", () => {
    const css = readSrc("app/globals.css");
    // Find the Phase 8J block
    const phaseBlockStart = css.indexOf("Phase 8J");
    assert.ok(phaseBlockStart !== -1, "globals.css must contain Phase 8J mobile nav section");
    const phaseBlock = css.slice(phaseBlockStart);
    // Should not have bare hex values — tokens like var(--ds-...) are fine
    const rawHexPattern = /(?<!var\([^)]*?)(?<!color-mix[^)]*?)#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])/;
    assert.ok(
      !rawHexPattern.test(phaseBlock),
      "Phase 8J CSS block must not contain raw hex values — use ds-tokens"
    );
  });
});

// ── 10. All non-submit buttons have type="button" in touched files ────────────

describe("All non-submit buttons have type='button' in touched nav/shell files", () => {
  it("MobileNav hamburger button has type='button'", () => {
    const nav = readSrc("components/layout/MobileNav.tsx");
    // Count all <button elements, then check those that are not type="submit" all have type="button"
    const buttonElements = nav.match(/<button[^>]*>/g) || [];
    for (const btn of buttonElements) {
      if (!btn.includes('type="submit"')) {
        assert.ok(
          btn.includes('type="button"'),
          `Button in MobileNav must have type="button": ${btn.slice(0, 80)}`
        );
      }
    }
  });

  it("MobileNav sign-out button has type='button'", () => {
    const nav = readSrc("components/layout/MobileNav.tsx");
    assert.ok(
      nav.includes('aria-label="Sign out"') && nav.includes('type="button"'),
      "sign-out button must have type='button'"
    );
  });
});

// ── 11. Existing routes, testids, and nav labels remain valid ─────────────────

describe("Existing routes and drawer nav labels are preserved", () => {
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("drawer nav includes /explore route", () => {
    assert.ok(nav.includes('href: "/explore"'), "drawer must include /explore");
  });

  it("drawer nav includes /concierge route", () => {
    assert.ok(nav.includes('href: "/concierge"'), "drawer must include /concierge");
  });

  it("drawer nav includes /saved route", () => {
    assert.ok(nav.includes('href: "/saved"'), "drawer must include /saved");
  });

  it("drawer nav includes /trips route", () => {
    assert.ok(nav.includes('href: "/trips"'), "drawer must include /trips");
  });

  it("drawer nav includes /trips/new route", () => {
    assert.ok(nav.includes('href: "/trips/new"'), "drawer must still include /trips/new");
  });

  it("drawer nav includes /cards route", () => {
    assert.ok(nav.includes('href: "/cards"'), "drawer must include /cards");
  });

  it("drawer nav includes /settings route", () => {
    assert.ok(nav.includes('href: "/settings"'), "drawer must include /settings");
  });

  it("bottom tab has data-testid mobile-nav-tab-home", () => {
    assert.ok(
      nav.includes('data-testid="mobile-nav-tab-home"') ||
        nav.includes("mobile-nav-tab-home"),
      "bottom nav tab must have testid for home tab"
    );
  });

  it("bottom tab has data-testid mobile-nav-tab-discover", () => {
    assert.ok(
      nav.includes("mobile-nav-tab-discover"),
      "bottom nav tab must have testid for discover tab"
    );
  });

  it("bottom tab has data-testid mobile-nav-tab-saved", () => {
    assert.ok(
      nav.includes("mobile-nav-tab-saved"),
      "bottom nav tab must have testid for saved tab"
    );
  });

  it("bottom tab has data-testid mobile-nav-tab-my-trips", () => {
    assert.ok(
      nav.includes("mobile-nav-tab-my-trips"),
      "bottom nav tab must have testid for my-trips tab"
    );
  });

  it("mobile-bottom-nav testid is present on the nav element", () => {
    assert.ok(
      nav.includes('data-testid="mobile-bottom-nav"'),
      "bottom nav element must have data-testid='mobile-bottom-nav'"
    );
  });
});

// ── 12. Drawer auth behavior preserved ───────────────────────────────────────

describe("Sign-out and drawer auth behavior preserved", () => {
  const nav = readSrc("components/layout/MobileNav.tsx");

  it("handleSignOut calls supabase.auth.signOut", () => {
    assert.ok(
      nav.includes("supabase.auth.signOut"),
      "sign-out handler must call supabase.auth.signOut"
    );
  });

  it("drawer uses mobile-drawer testid", () => {
    assert.ok(
      nav.includes('data-testid="mobile-drawer"'),
      "slide-out drawer must have data-testid='mobile-drawer'"
    );
  });
});

// ── 13. AppShell preserves auth checks and sidebar ───────────────────────────

describe("AppShell preserves auth, sidebar, and session behavior", () => {
  const shell = readSrc("components/layout/AppShell.tsx");

  it("AppShell imports and renders Sidebar", () => {
    assert.ok(
      shell.includes("Sidebar") && shell.includes("<Sidebar"),
      "AppShell must import and render Sidebar component"
    );
  });

  it("AppShell imports and renders MobileNav", () => {
    assert.ok(
      shell.includes("MobileNav") && shell.includes("<MobileNav"),
      "AppShell must import and render MobileNav"
    );
  });

  it("AppShell redirects unauthenticated users to /auth/login", () => {
    assert.ok(
      shell.includes("/auth/login"),
      "AppShell must redirect to /auth/login when no session"
    );
  });
});

// ── 14. globals.css mobile section completeness check ───────────────────────

describe("globals.css defines all required mobile shell utility classes", () => {
  const css = readSrc("app/globals.css");

  const requiredClasses = [
    ".mobile-top-bar",
    ".mobile-bottom-nav",
    ".mobile-tab-item",
    ".mobile-tab-active-dot",
    ".mobile-tab-icon",
    ".mobile-tab-icon-active",
    ".mobile-tab-label",
    ".mobile-tab-label-active",
    ".mobile-nav-spacer",
  ];

  for (const cls of requiredClasses) {
    it(`globals.css defines ${cls}`, () => {
      assert.ok(css.includes(cls), `globals.css must define ${cls}`);
    });
  }
});

// ── 15. MOBILE_DESIGN_LANGUAGE.md references mobile-nav-spacer ───────────────

describe("MOBILE_DESIGN_LANGUAGE.md references the CSS utility contract", () => {
  it("doc mentions mobile-nav-spacer class or equivalent", () => {
    const doc = readDocs("product/MOBILE_DESIGN_LANGUAGE.md");
    assert.ok(
      doc.includes("mobile-nav-spacer"),
      "MOBILE_DESIGN_LANGUAGE.md must reference the mobile-nav-spacer CSS utility"
    );
  });
});
