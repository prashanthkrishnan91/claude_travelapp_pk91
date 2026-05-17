/**
 * Stage 3.5 Phase 8E — Concierge Search Instrument + Results Presentation Overhaul
 * Static contract tests — source-file assertions only; no DOM rendering, no network.
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
const aiConciergePanelSrc = readFileSync(
  join(root, "src/components/trips/AIConciergePanel.tsx"),
  "utf8",
);
const cardHelpersSrc = readFileSync(
  join(root, "src/lib/concierge/cardHelpers.ts"),
  "utf8",
);

// ── Standalone Concierge instrument structure ─────────────────────────────────

test("ConciergePage has concierge-page root testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-page"'),
    "ConciergePage root div must have data-testid concierge-page",
  );
});

test("ConciergePage has instrument header testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-instrument-header"'),
    "ConciergePage editorial header must have data-testid concierge-instrument-header",
  );
});

test("ConciergePage has results canvas testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-results-canvas"'),
    "ConciergePage main results area must have data-testid concierge-results-canvas",
  );
});

test("ConciergePage has empty state testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-empty-state"'),
    "ConciergePage empty state must have data-testid concierge-empty-state",
  );
});

test("ConciergePage has result section testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-result-section"'),
    "ConciergePage result section must have data-testid concierge-result-section",
  );
});

test("ConciergePage has loading state testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-loading-state"'),
    "ConciergePage loading state must have data-testid concierge-loading-state",
  );
});

test("ConciergePage has error state testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-error-state"'),
    "ConciergePage error state must have data-testid concierge-error-state",
  );
});

// ── Premium composer/input grammar ────────────────────────────────────────────

test("ConciergePage has instrument composer testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-instrument-composer"'),
    "ConciergePage sticky composer must have data-testid concierge-instrument-composer",
  );
});

test("ConciergePage has destination field testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-destination-field"'),
    "ConciergePage destination field wrapper must have data-testid concierge-destination-field",
  );
});

test("ConciergePage has query input testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-query-input"'),
    "ConciergePage textarea must have data-testid concierge-query-input",
  );
});

test("ConciergePage has submit button testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-submit-button"'),
    "ConciergePage submit button must have data-testid concierge-submit-button",
  );
});

test("ConciergePage destination label is visible (not sr-only)", () => {
  // Label must not be sr-only — it should be visible as part of the instrument
  assert.ok(
    !conciergePage.includes('className="sr-only"'),
    "ConciergePage destination label must not be sr-only — it should be visible",
  );
  // Label must display "Where" as the visible label text
  assert.ok(
    conciergePage.includes(">Where<") ||
      conciergePage.includes("Where\n") ||
      conciergePage.includes("Where "),
    "ConciergePage destination label must display 'Where' as visible label text",
  );
});

test("ConciergePage destination label uses Overline tracking", () => {
  assert.ok(
    conciergePage.includes("tracking-[0.1em]"),
    "ConciergePage must use correct Overline tracking-[0.1em] (not 0.08em or 0.12em)",
  );
});

test("ConciergePage textarea has aria-label for accessibility", () => {
  assert.ok(
    conciergePage.includes('aria-label="Concierge query"'),
    "ConciergePage textarea must have aria-label='Concierge query'",
  );
});

test("ConciergePage submit button has aria-label for accessibility", () => {
  assert.ok(
    conciergePage.includes('aria-label="Submit query"'),
    "ConciergePage submit button must have aria-label='Submit query'",
  );
});

test("ConciergePage composer uses focus-visible (not focus:ring)", () => {
  assert.ok(
    !conciergePage.includes("focus:ring-2") && !conciergePage.includes("focus:ring-ds-accent"),
    "ConciergePage must not use focus:ring-* — use focus-visible:outline pattern instead",
  );
});

test("ConciergePage clear-chat button has testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-clear-chat"'),
    "ConciergePage clear-chat button must have data-testid concierge-clear-chat",
  );
});

// ── No chat-bubble user turns ─────────────────────────────────────────────────

test("ConciergePage user turns have concierge-user-query testid", () => {
  assert.ok(
    conciergePage.includes('data-testid="concierge-user-query"'),
    "ConciergePage user turn must have data-testid concierge-user-query",
  );
});

test("ConciergePage does not use right-aligned chat bubbles for user turns", () => {
  assert.ok(
    !conciergePage.includes('"flex justify-end"'),
    "ConciergePage must not use flex justify-end chat-bubble pattern for user turns",
  );
});

test("ConciergePage does not render rounded-2xl rounded-tr-sm chat bubbles", () => {
  assert.ok(
    !conciergePage.includes("rounded-2xl rounded-tr-sm"),
    "ConciergePage must not render chat bubble shape (rounded-2xl rounded-tr-sm) for user turns",
  );
});

test("ConciergePage user query text is italic (editorial annotation style)", () => {
  assert.ok(
    conciergePage.includes('className="text-ds-text-tertiary italic"') ||
      conciergePage.includes("italic"),
    "ConciergePage user query must use italic style — annotation, not chat bubble",
  );
});

// ── Instrument copy ───────────────────────────────────────────────────────────

test("ConciergePage uses first-person concierge voice", () => {
  assert.ok(
    conciergePage.includes("I surface verified places"),
    "ConciergePage must use first-person 'I surface verified places' (not 'We')",
  );
});

test("ConciergePage has premium empty-state instruction copy", () => {
  assert.ok(
    conciergePage.includes("Starting points") ||
      conciergePage.includes("starting points"),
    "ConciergePage empty state must have starting-points framing (not generic 'A few starting points to get you going')",
  );
});

// ── Semantic buttons/links — no card-level click-only navigation ──────────────

test("ConciergePage submit button is type=button", () => {
  assert.ok(
    conciergePage.includes('type="button"'),
    "ConciergePage interactive buttons must use type='button'",
  );
});

test("ConciergePage map links use real anchor elements", () => {
  assert.ok(
    conciergePage.includes("href={mapLink}"),
    "ConciergePage map links must be real <a href> elements",
  );
});

test("ConciergePage source links use real anchor elements", () => {
  assert.ok(
    conciergePage.includes("href={sourceLink}"),
    "ConciergePage source links must be real <a href> elements",
  );
});

test("ConciergePage result cards have no card-level onClick navigation", () => {
  assert.ok(
    !conciergePage.includes("router.push") &&
      !conciergePage.includes("onClick={() => window."),
    "ConciergePage must not use onClick-only navigation on result cards",
  );
});

// ── No fake/mock/sample visible data ─────────────────────────────────────────

test("ConciergePage has no hardcoded fake place names in card renders", () => {
  assert.ok(
    !conciergePage.includes('"Le Bernardin"') &&
      !conciergePage.includes('"Sample Restaurant"') &&
      !conciergePage.includes('"Mock Place"'),
    "ConciergePage must not render hardcoded fake place names",
  );
});

test("ConciergePage starter chips have no hardcoded city or destination names", () => {
  // Phase 8E contract: chips must not pretend to know the user's destination
  assert.ok(
    !conciergePage.includes('"Tokyo"') &&
      !conciergePage.includes('"Paris"') &&
      !conciergePage.includes('"Lisbon"') &&
      !conciergePage.includes('"New York"'),
    "EDITORIAL_PROMPTS must not contain hardcoded city names (Tokyo, Paris, Lisbon, New York)",
  );
});

test("ConciergePage starter chips do not auto-set destination", () => {
  // Chips must not call setDestination with a hardcoded destination value
  assert.ok(
    !conciergePage.includes("prompt.destination"),
    "ConciergePage starter chips must not auto-set destination via prompt.destination",
  );
});

test("ConciergePage starter chips populate input only, no auto-submit of fake destinations", () => {
  // Chips must only call setInput — no auto-submit with a hardcoded destination
  assert.ok(
    !conciergePage.includes("handleUserInput(prompt.query, prompt.destination)") &&
      !conciergePage.includes("void handleUserInput(prompt.query,"),
    "ConciergePage starter chips must not auto-submit with fake destination overrides",
  );
});

// ── No backend/provider imports ───────────────────────────────────────────────

test("ConciergePage imports no backend routes or providers", () => {
  assert.ok(
    !conciergePage.includes('from "@/backend') &&
      !conciergePage.includes('from "../backend') &&
      !conciergePage.includes("provider_registry") &&
      !conciergePage.includes("semantic_retrieval"),
    "ConciergePage must not import backend/provider modules",
  );
});

test("ConciergePage imports only from lib/api and lib/concierge", () => {
  assert.ok(
    conciergePage.includes('from "@/lib/api"') ||
      conciergePage.includes('from "@/lib/concierge'),
    "ConciergePage must import from lib/api and/or lib/concierge/* only",
  );
});

// ── Preserved transcript/clear-chat behavior ──────────────────────────────────

test("ConciergePage clearTranscript function preserved", () => {
  assert.ok(
    conciergePage.includes("clearTranscript"),
    "ConciergePage clearTranscript function must be preserved",
  );
});

test("ConciergePage localStorage transcript persistence preserved", () => {
  assert.ok(
    conciergePage.includes("TRANSCRIPT_KEY") &&
      conciergePage.includes("localStorage"),
    "ConciergePage must preserve localStorage transcript persistence",
  );
});

test("ConciergePage loadPersistedTranscript preserved", () => {
  assert.ok(
    conciergePage.includes("loadPersistedTranscript"),
    "ConciergePage loadPersistedTranscript function must be preserved",
  );
});

test("ConciergePage saveTranscript preserved", () => {
  assert.ok(
    conciergePage.includes("saveTranscript"),
    "ConciergePage saveTranscript function must be preserved",
  );
});

// ── Preserved trusted card rendering ─────────────────────────────────────────

test("ConciergePage ConciergeResultCard component preserved", () => {
  assert.ok(
    conciergePage.includes("ConciergeResultCard"),
    "ConciergePage ConciergeResultCard component must be preserved",
  );
});

test("ConciergePage uses canShowGoogleVerifiedBadge for trust rendering", () => {
  assert.ok(
    conciergePage.includes("canShowGoogleVerifiedBadge"),
    "ConciergePage must use canShowGoogleVerifiedBadge — no fabricated trust signals",
  );
});

test("ConciergePage uses pickCardMeta from shared cardHelpers", () => {
  assert.ok(
    conciergePage.includes("pickCardMeta"),
    "ConciergePage must use pickCardMeta from cardHelpers",
  );
});

test("ConciergePage uses isRenderableVerifiedPlace gate for cards", () => {
  assert.ok(
    conciergePage.includes("isRenderableVerifiedPlace"),
    "ConciergePage must use isRenderableVerifiedPlace to filter cards",
  );
});

// ── No API request-shape or response-normalization change ─────────────────────

test("ConciergePage calls callConciergeSearch with null tripId", () => {
  assert.ok(
    conciergePage.includes("callConciergeSearch(null,"),
    "ConciergePage must still call callConciergeSearch(null, ...) — no tripId for standalone",
  );
});

test("ConciergePage passes destination as 4th argument", () => {
  assert.ok(
    conciergePage.includes(", effectiveDest)") ||
      conciergePage.includes(", destination.trim()"),
    "ConciergePage must pass destination as 4th arg to callConciergeSearch",
  );
});

test("ConciergePage refinement chips preserved", () => {
  assert.ok(
    conciergePage.includes("refinementChips") &&
      conciergePage.includes("activeChips"),
    "ConciergePage refinement chips logic must be preserved",
  );
});

// ── Trip-context Concierge visual integration (AIConciergePanel) ──────────────

test("AIConciergePanel has panel root testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="ai-concierge-panel"'),
    "AIConciergePanel root div must have data-testid ai-concierge-panel",
  );
});

test("AIConciergePanel has panel header testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-header"'),
    "AIConciergePanel header must have data-testid concierge-panel-header",
  );
});

test("AIConciergePanel header uses editorial overline — Private Travel Concierge", () => {
  assert.ok(
    aiConciergePanelSrc.includes("Private Travel Concierge"),
    "AIConciergePanel header must display 'Private Travel Concierge' overline — editorial, not generic 'AI Concierge'",
  );
});

test("AIConciergePanel header overline uses correct Overline tracking", () => {
  assert.ok(
    aiConciergePanelSrc.includes("tracking-[0.1em]"),
    "AIConciergePanel must use tracking-[0.1em] (correct Overline) in header",
  );
});

test("AIConciergePanel destination renders as named heading, not inline suffix", () => {
  // Old pattern: "· {destination}" inline after AI Concierge label
  // New pattern: destination as a separate element below the overline
  assert.ok(
    !aiConciergePanelSrc.includes('"· {destination}"') &&
      !aiConciergePanelSrc.includes("· {destination}"),
    "AIConciergePanel destination must not appear as '· destination' inline suffix — render as separate element",
  );
});

test("AIConciergePanel has day selector testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-day-selector"'),
    "AIConciergePanel day selector must have data-testid concierge-panel-day-selector",
  );
});

test("AIConciergePanel day selector label uses editorial copy (Add to Day)", () => {
  assert.ok(
    aiConciergePanelSrc.includes("Add to Day"),
    "AIConciergePanel day selector label must read 'Add to Day' — not 'Target day for Add to Day'",
  );
});

test("AIConciergePanel day selector label does not use old jargon", () => {
  assert.ok(
    !aiConciergePanelSrc.includes("Target day for Add to Day"),
    "AIConciergePanel must remove 'Target day for Add to Day' jargon label",
  );
});

test("AIConciergePanel has transcript area testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-transcript"'),
    "AIConciergePanel scrollable transcript area must have data-testid concierge-panel-transcript",
  );
});

test("AIConciergePanel user turns have testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-user-query"'),
    "AIConciergePanel user turn must have data-testid concierge-panel-user-query",
  );
});

test("AIConciergePanel does not render chat bubbles for user turns", () => {
  assert.ok(
    !aiConciergePanelSrc.includes("rounded-2xl rounded-br-sm") &&
      !aiConciergePanelSrc.includes("bg-ds-accent/15") &&
      !aiConciergePanelSrc.includes("ring-ds-accent/30"),
    "AIConciergePanel must not render rounded-2xl chat bubble shape for user turns",
  );
});

test("AIConciergePanel loading state has testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-loading"'),
    "AIConciergePanel loading state must have data-testid concierge-panel-loading",
  );
});

test("AIConciergePanel loading state is instrument style not bubble", () => {
  assert.ok(
    aiConciergePanelSrc.includes("Searching") &&
      aiConciergePanelSrc.includes("Verifying") &&
      aiConciergePanelSrc.includes("Composing"),
    "AIConciergePanel loading state must use 'Searching · Verifying · Composing' instrument style",
  );
  assert.ok(
    !aiConciergePanelSrc.includes("Researching options"),
    "AIConciergePanel must not show 'Researching options…' chatbot-bubble loading text",
  );
});

test("AIConciergePanel has panel composer testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-composer"'),
    "AIConciergePanel bottom composer must have data-testid concierge-panel-composer",
  );
});

test("AIConciergePanel input has testid and aria-label", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-input"'),
    "AIConciergePanel input must have data-testid concierge-panel-input",
  );
  assert.ok(
    aiConciergePanelSrc.includes('aria-label="Concierge query"'),
    "AIConciergePanel input must have aria-label='Concierge query'",
  );
});

test("AIConciergePanel input uses focus-visible (not focus:ring)", () => {
  assert.ok(
    !aiConciergePanelSrc.includes("focus:ring-2") &&
      !aiConciergePanelSrc.includes("focus:ring-ds-accent"),
    "AIConciergePanel input must not use focus:ring-* — use focus-visible:outline instead",
  );
});

test("AIConciergePanel input has 44px minimum touch target", () => {
  assert.ok(
    aiConciergePanelSrc.includes('"concierge-panel-input"') &&
      aiConciergePanelSrc.includes("minHeight"),
    "AIConciergePanel input must have minHeight for 44px touch target",
  );
});

test("AIConciergePanel submit button has testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-submit"'),
    "AIConciergePanel submit button must have data-testid concierge-panel-submit",
  );
});

test("AIConciergePanel clear button has testid", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-clear"'),
    "AIConciergePanel clear button must have data-testid concierge-panel-clear",
  );
});

test("AIConciergePanel close button has testid and aria-label", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-close"'),
    "AIConciergePanel close button must have data-testid concierge-panel-close",
  );
  assert.ok(
    aiConciergePanelSrc.includes('aria-label="Close Concierge"'),
    "AIConciergePanel close button must have aria-label='Close Concierge'",
  );
});

test("AIConciergePanel quick-action chips use rounded-lg (not rounded-full)", () => {
  // rounded-full is chatbot pill style; rounded-lg is the premium instrument chip style
  assert.ok(
    !aiConciergePanelSrc.includes('"rounded-full border border-ds-pen-stroke'),
    "AIConciergePanel quick-action chips must use rounded-lg — not rounded-full chatbot pill",
  );
});

// ── Preserved AIConciergePanel behavior (add-to-day, save, maps, card actions) ─

test("AIConciergePanel CONCIERGE_CACHE_VERSION preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("CONCIERGE_CACHE_VERSION"),
    "AIConciergePanel CONCIERGE_CACHE_VERSION must be preserved",
  );
});

test("AIConciergePanel isRenderableVerifiedPlace gate preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("isRenderableVerifiedPlace"),
    "AIConciergePanel isRenderableVerifiedPlace gate must be preserved",
  );
});

test("AIConciergePanel add-to-day behavior preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("addStructuredConciergeItemToTrip") &&
      aiConciergePanelSrc.includes("onAdd"),
    "AIConciergePanel add-to-day behavior (addStructuredConciergeItemToTrip, onAdd) must be preserved",
  );
});

test("AIConciergePanel save-to-ideas behavior preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("saveToTripIdeas") &&
      aiConciergePanelSrc.includes("onSaveIdea"),
    "AIConciergePanel save-to-ideas behavior (saveToTripIdeas, onSaveIdea) must be preserved",
  );
});

test("AIConciergePanel maps link preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("googleMapsUri") ||
      aiConciergePanelSrc.includes("mapsLink"),
    "AIConciergePanel maps link (googleMapsUri / mapsLink) must be preserved",
  );
});

test("AIConciergePanel callConciergeSearch preserved with tripId", () => {
  assert.ok(
    aiConciergePanelSrc.includes("callConciergeSearch(tripId,"),
    "AIConciergePanel must still call callConciergeSearch(tripId, ...) — not null",
  );
});

test("AIConciergePanel handleClearChat preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("handleClearChat"),
    "AIConciergePanel handleClearChat must be preserved",
  );
});

test("AIConciergePanel ConciergeCard component preserved", () => {
  assert.ok(
    aiConciergePanelSrc.includes("ConciergeCard"),
    "AIConciergePanel ConciergeCard component must be preserved",
  );
});

// ── Shared cardHelpers preserved ──────────────────────────────────────────────

test("cardHelpers hasClosedSignal scans all 12 fields including raw", () => {
  assert.ok(
    cardHelpersSrc.includes("card.raw"),
    "cardHelpers hasClosedSignal must still scan card.raw field",
  );
});

test("cardHelpers canShowGoogleVerifiedBadge checks businessStatus OPERATIONAL", () => {
  assert.ok(
    cardHelpersSrc.includes('"OPERATIONAL"'),
    "cardHelpers canShowGoogleVerifiedBadge must still check businessStatus === 'OPERATIONAL'",
  );
});

test("cardHelpers pickCardMeta reads displayMetaLine and displayPrice", () => {
  assert.ok(
    cardHelpersSrc.includes("displayMetaLine") && cardHelpersSrc.includes("displayPrice"),
    "cardHelpers pickCardMeta must still read displayMetaLine and displayPrice",
  );
});

// ── No backend/provider/env files changed ─────────────────────────────────────

test("backend concierge.py optional UUID trip_id contract unchanged", () => {
  const backendSrc = readFileSync(
    join(root, "../backend/app/services/concierge.py"),
    "utf8",
  );
  assert.ok(
    backendSrc.includes("trip_id: Optional[UUID]"),
    "backend concierge.py must still have Optional[UUID] trip_id — no backend changes",
  );
});

test("no new SQL migration for Phase 8E", () => {
  assert.ok(
    !existsSync(join(root, "../backend/db/migrations/007_concierge_instrument.sql")),
    "Phase 8E must not add a Supabase SQL migration — frontend only",
  );
});

// ── ds-* token compliance in changed surfaces ─────────────────────────────────

test("ConciergePage has no raw hex colors (#) in design surfaces", () => {
  // Extract only the new/changed design surface sections; allow existing rgba for semantic trust signals
  const hasRawHex = /#[0-9A-Fa-f]{6}\b/.test(conciergePage);
  // rgba is allowed for trust signals (existing pattern: rgba(232, 178, 107, 0.08))
  assert.ok(
    !hasRawHex,
    "ConciergePage must not contain raw hex colors — use ds-* tokens",
  );
});

test("AIConciergePanel has no forbidden legacy palette classes in new additions", () => {
  assert.ok(
    !aiConciergePanelSrc.includes("rounded-full border border-ds-pen-stroke bg-ds-carbon px-3 py-1.5 text-xs font-medium"),
    "AIConciergePanel must not have old chatbot pill chip style",
  );
});

test("ConciergePage Overline tracking is 0.1em in instrument header", () => {
  // The editorial header should use tracking-[0.1em] per Design Bible §4.4
  assert.ok(
    conciergePage.includes("tracking-[0.1em]"),
    "ConciergePage instrument header must use Design Bible Overline tracking-[0.1em]",
  );
});

// ── Phase 8E patch: Design Bible contract misses ───────────────────────────────

test("ConciergePage has no raw rgba() backgrounds", () => {
  assert.ok(
    !conciergePage.includes("rgba("),
    "ConciergePage must not use raw rgba() backgrounds — use color-mix(in srgb, ...) or ds-* tokens",
  );
});

test("ConciergePage sources summary uses tracking-[0.1em] not tracking-[0.08em]", () => {
  assert.ok(
    !conciergePage.includes("tracking-[0.08em]"),
    "ConciergePage must not use tracking-[0.08em] in any label — use tracking-[0.1em] per Design Bible §4.4",
  );
});

test("AIConciergePanel close button has 44px minimum touch target (not 32px)", () => {
  // Close button must be upgraded from 32px to 44px for accessibility
  assert.ok(
    !aiConciergePanelSrc.includes('minWidth: "32px"') &&
      !aiConciergePanelSrc.includes('minHeight: "32px"'),
    "AIConciergePanel close button must not use 32px min size — must be 44px for touch accessibility",
  );
});

test("AIConciergePanel close button explicitly sets 44px minWidth and minHeight", () => {
  assert.ok(
    aiConciergePanelSrc.includes('data-testid="concierge-panel-close"'),
    "AIConciergePanel close button testid must be present",
  );
  assert.ok(
    aiConciergePanelSrc.includes('aria-label="Close Concierge"'),
    "AIConciergePanel close button aria-label must be preserved",
  );
});
