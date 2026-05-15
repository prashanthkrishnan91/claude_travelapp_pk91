/**
 * Stage 3.5 Phase 2A — AI Concierge standalone page static contract tests.
 * Source-file assertions only — no DOM rendering, no network.
 */

import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { test } from "node:test";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const conciergePage = readFileSync(
  join(root, "src/components/concierge/ConciergePage.tsx"),
  "utf8",
);
const conciergeRoute = readFileSync(
  join(root, "src/app/concierge/page.tsx"),
  "utf8",
);
const sidebarSrc = readFileSync(
  join(root, "src/components/layout/Sidebar.tsx"),
  "utf8",
);
const mobileNavSrc = readFileSync(
  join(root, "src/components/layout/MobileNav.tsx"),
  "utf8",
);
const aiConciergePanelSrc = readFileSync(
  join(root, "src/components/trips/AIConciergePanel.tsx"),
  "utf8",
);

// ── Route existence ────────────────────────────────────────────────────────────

test("concierge route file exists", () => {
  assert.ok(
    existsSync(join(root, "src/app/concierge/page.tsx")),
    "src/app/concierge/page.tsx must exist",
  );
});

test("ConciergePage.tsx component file exists", () => {
  assert.ok(
    existsSync(join(root, "src/components/concierge/ConciergePage.tsx")),
    "src/components/concierge/ConciergePage.tsx must exist",
  );
});

test("concierge route imports ConciergePage", () => {
  assert.ok(
    conciergeRoute.includes("ConciergePage"),
    "concierge/page.tsx must import and render ConciergePage",
  );
});

// ── Nav discoverability ────────────────────────────────────────────────────────

test("Sidebar includes /concierge link", () => {
  assert.ok(
    sidebarSrc.includes('href: "/concierge"') ||
      sidebarSrc.includes("href: '/concierge'"),
    "Sidebar.tsx must include a /concierge nav link",
  );
});

test("Sidebar concierge link has a label", () => {
  assert.ok(
    sidebarSrc.includes('"Concierge"') || sidebarSrc.includes("'Concierge'"),
    "Sidebar.tsx concierge link must have a Concierge label",
  );
});

test("MobileNav drawer includes /concierge link", () => {
  assert.ok(
    mobileNavSrc.includes('href: "/concierge"') ||
      mobileNavSrc.includes("href: '/concierge'"),
    "MobileNav.tsx links (drawer) must include /concierge",
  );
});

// ── callConciergeSearch tripId=null path ──────────────────────────────────────

test("ConciergePage calls callConciergeSearch with null tripId", () => {
  assert.ok(
    conciergePage.includes("callConciergeSearch(null,"),
    "ConciergePage must call callConciergeSearch(null, ...) for standalone use",
  );
});

// ── No fabricated trust signals ────────────────────────────────────────────────

test("ConciergePage does not hardcode sourceCount in TrustStrip", () => {
  assert.ok(
    !conciergePage.includes("sourceCount={1}") &&
      !conciergePage.includes("sourceCount={2}") &&
      !conciergePage.includes("sourceCount={3}"),
    "TrustStrip must not render a hardcoded sourceCount — that would fabricate source evidence",
  );
});

test("ConciergePage does not set verified=true on TrustStrip", () => {
  assert.ok(
    !conciergePage.includes("verified={true}"),
    "TrustStrip verified={true} must never appear — no Verified by Google without explicit backend confirmation",
  );
});

test("ConciergePage TrustStrip uses actual backend confidence field", () => {
  assert.ok(
    conciergePage.includes("operationalConfidence"),
    "ConciergePage must derive TrustStrip confidence from actual googleVerification.confidence, not a hardcoded value",
  );
});

// ── Scope boundary: backend/provider unchanged ─────────────────────────────────

test("backend concierge.py file unchanged — no concierge route changes", () => {
  const backendSrc = readFileSync(
    join(root, "../backend/app/services/concierge.py"),
    "utf8",
  );
  // Spot-check: backend still has Optional[UUID] trip_id (pre-existing contract unchanged)
  assert.ok(
    backendSrc.includes("trip_id: Optional[UUID]"),
    "backend concierge.py must still have Optional[UUID] trip_id — no backend changes allowed",
  );
});

test("no Supabase migration files added for this feature", () => {
  const migrationDir = join(root, "../backend/db/migrations");
  // Only check that migration 006+ was not added by this PR (005 was pre-existing)
  assert.ok(
    !existsSync(join(migrationDir, "006_concierge_page.sql")),
    "No new Supabase migration should exist for the concierge page UI change",
  );
});

// ── AIConciergePanel untouched ────────────────────────────────────────────────

test("AIConciergePanel still declares CONCIERGE_CACHE_VERSION", () => {
  assert.ok(
    aiConciergePanelSrc.includes("CONCIERGE_CACHE_VERSION"),
    "AIConciergePanel.tsx must be untouched — CONCIERGE_CACHE_VERSION must still be present",
  );
});

test("AIConciergePanel still uses isRenderableVerifiedPlace gate", () => {
  assert.ok(
    aiConciergePanelSrc.includes("isRenderableVerifiedPlace"),
    "AIConciergePanel.tsx must be untouched — isRenderableVerifiedPlace must still be present",
  );
});

// ── ConciergePage does not render chatbot/debug patterns ─────────────────────

test("ConciergePage has no chatbot avatar or typing dots", () => {
  assert.ok(
    !conciergePage.includes("typing-dots") &&
      !conciergePage.includes("chat-bubble") &&
      !conciergePage.includes("avatar"),
    "ConciergePage must not render chatbot avatar or typing dots",
  );
});

test("ConciergePage has no model name or token count output", () => {
  assert.ok(
    !conciergePage.includes("model_name") &&
      !conciergePage.includes("token_count") &&
      !conciergePage.includes("debug"),
    "ConciergePage must not render model name, token count, or debug output",
  );
});
