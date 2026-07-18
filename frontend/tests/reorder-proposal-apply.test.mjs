/**
 * Reorder-proposal apply contract — explicit user-approved reorder
 * (AI Route Planning v1 PR C / apply, docs/ai/AI_ROUTE_PLANNING_V1_ADR.md
 * Section 9). ReorderProposalPreview now lives in its own shared component
 * file and is reused by the AI route-planning suggestion surfaced from
 * "Plan My Day" (DayPlanModal) — the apply contract itself is unchanged.
 *
 * Verifies:
 * 1.  applyRouteReorderProposal is exported from api.ts and only POSTs to
 *     the reorder-proposal apply endpoint.
 * 2.  ReorderProposalPreview is defined and exported from its own file.
 * 3.  The preview renders both current order and proposed order.
 * 4.  Cancel/dismiss sets dismissed state and never calls the apply helper.
 * 5.  Confirm is required before any write: applyRouteReorderProposal is
 *     only reachable from the confirm handler, never on render/mount.
 * 6.  Confirm calls the apply helper exactly once per click (guarded by the
 *     `applying` in-flight flag before any state update).
 * 7.  Confirm/cancel buttons are disabled while `applying` is true
 *     (prevents double-submit).
 * 8.  No auto-call: applyRouteReorderProposal is never called inside a
 *     useEffect, and the component renders nothing when proposal is null.
 * 9.  No LLM/AI suggestion call exists anywhere in the preview component.
 * 10. No route-estimate helper is imported/called from the preview.
 * 11. CheckRoutePanel is not resurrected in ItineraryDayColumn.
 * 12. Copy never implies automatic optimization — "Nothing changes until
 *     you confirm" and "This only reorders the stops shown" render, and no
 *     "Optimize Day"/auto-reorder language exists.
 * 13. Types are exported from types/index.ts.
 * 14. DayPlanModal (the Plan My Day result surface) wires the preview with
 *     a real, AI-generated proposal — not a hardcoded null.
 */

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const apiSrc = readFileSync(new URL("../src/lib/api.ts", import.meta.url), "utf8");
const previewSrc = readFileSync(
  new URL("../src/components/trips/ReorderProposalPreview.tsx", import.meta.url),
  "utf8",
);
const dayColumnSrc = readFileSync(
  new URL("../src/components/trips/ItineraryDayColumn.tsx", import.meta.url),
  "utf8",
);
const dayPlanModalSrc = readFileSync(
  new URL("../src/components/trips/DayPlanModal.tsx", import.meta.url),
  "utf8",
);
const typesSrc = readFileSync(new URL("../src/types/index.ts", import.meta.url), "utf8");

function extractComponent(src, name) {
  const match = src.match(new RegExp(`function ${name}\\([\\s\\S]*?\\n\\}\\n`));
  assert.ok(match, `${name} must be defined`);
  return match[0];
}

// ---------------------------------------------------------------------------
// 1. applyRouteReorderProposal — POST only, correct endpoint
// ---------------------------------------------------------------------------

test("applyRouteReorderProposal is exported from api.ts", () => {
  assert.match(
    apiSrc,
    /export async function applyRouteReorderProposal/,
    "applyRouteReorderProposal must be exported from api.ts",
  );
});

test("applyRouteReorderProposal targets the reorder-proposal apply endpoint and POSTs", () => {
  const fnMatch = apiSrc.match(/export async function applyRouteReorderProposal[\s\S]{0,600}/);
  assert.ok(fnMatch, "function must exist");
  assert.match(fnMatch[0], /route-reorder-proposal\/apply/, "must target the apply endpoint");
  assert.match(fnMatch[0], /method:\s*["']POST["']/, "must use POST");
});

// ---------------------------------------------------------------------------
// 2. Component defined and exported from its own shared file
// ---------------------------------------------------------------------------

test("ReorderProposalPreview component is defined and exported", () => {
  assert.match(previewSrc, /export function ReorderProposalPreview/, "ReorderProposalPreview must be defined and exported");
});

test("ReorderProposalPreview is imported and rendered in DayPlanModal", () => {
  assert.match(
    dayPlanModalSrc,
    /import\s*\{\s*ReorderProposalPreview\s*\}\s*from\s*["']\.\/ReorderProposalPreview["']/,
    "DayPlanModal must import the shared preview component",
  );
  assert.match(dayPlanModalSrc, /<ReorderProposalPreview\s/, "ReorderProposalPreview must be used in JSX");
});

// ---------------------------------------------------------------------------
// 3. Before/after preview
// ---------------------------------------------------------------------------

test("preview shows both current order and proposed order", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /data-testid="reorder-proposal-current"/, "current order block must render");
  assert.match(src, /data-testid="reorder-proposal-proposed"/, "proposed order block must render");
  assert.match(src, /displayedCurrentOrder\.map/, "must map over the (display-order-aware) current order");
  assert.match(src, /displayedProposedOrder\.map/, "must map over the (display-order-aware) proposed order");
});

test("preview prefers currentDisplayOrder/proposedDisplayOrder over raw currentOrder/proposedOrder when supplied", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(
    src,
    /const displayedCurrentOrder = proposal\.currentDisplayOrder \?\? proposal\.currentOrder;/,
    "display order must fall back to the raw order when absent",
  );
  assert.match(
    src,
    /const displayedProposedOrder = proposal\.proposedDisplayOrder \?\? proposal\.proposedOrder;/,
  );
});

test("apply always uses the raw currentOrder/proposedOrder, never the display order", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  const confirmMatch = src.match(/const handleConfirm = async \(\) => \{[\s\S]*?\n  \};/);
  assert.ok(confirmMatch, "handleConfirm must exist");
  assert.match(confirmMatch[0], /proposal\.currentOrder,\s*\n\s*proposal\.proposedOrder/);
  assert.doesNotMatch(confirmMatch[0], /displayedCurrentOrder|displayedProposedOrder|DisplayOrder/, "apply must never send display-only ordering");
});

// ---------------------------------------------------------------------------
// 4. Cancel/dismiss performs no write
// ---------------------------------------------------------------------------

test("cancel/dismiss handler never calls the apply helper", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  const cancelMatch = src.match(/const handleCancel = \(\) => \{[\s\S]*?\n  \};/);
  assert.ok(cancelMatch, "handleCancel must exist");
  assert.doesNotMatch(cancelMatch[0], /applyRouteReorderProposal/, "cancel must not call the apply helper");
  assert.match(cancelMatch[0], /setDismissed\(true\)/, "cancel must only set local dismissed state");
});

test("cancel button is wired to handleCancel", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /data-testid="reorder-proposal-cancel"[\s\S]{0,200}onClick=\{handleCancel\}|onClick=\{handleCancel\}[\s\S]{0,200}data-testid="reorder-proposal-cancel"/);
});

// ---------------------------------------------------------------------------
// 5-6. Confirm required before write; apply helper called exactly once
// ---------------------------------------------------------------------------

test("applyRouteReorderProposal is only reachable from the confirm handler", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  const confirmMatch = src.match(/const handleConfirm = async \(\) => \{[\s\S]*?\n  \};/);
  assert.ok(confirmMatch, "handleConfirm must exist");
  assert.match(confirmMatch[0], /applyRouteReorderProposal/, "confirm must call the apply helper");
  // Outside handleConfirm, the component body must not call it again.
  const withoutConfirm = src.replace(confirmMatch[0], "");
  assert.doesNotMatch(withoutConfirm, /applyRouteReorderProposal\(/, "apply helper must only be called from handleConfirm");
});

test("handleConfirm guards against double-submit with the applying flag before calling the helper", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  const confirmMatch = src.match(/const handleConfirm = async \(\) => \{[\s\S]*?\n  \};/);
  const body = confirmMatch[0];
  const guardIndex = body.indexOf("if (applying) return;");
  const callIndex = body.indexOf("applyRouteReorderProposal(");
  assert.ok(guardIndex >= 0, "must guard on the applying flag");
  assert.ok(callIndex > guardIndex, "guard must run before the apply call");
});

test("confirm button is wired to handleConfirm", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /data-testid="reorder-proposal-confirm"[\s\S]{0,200}onClick=\{handleConfirm\}|onClick=\{handleConfirm\}[\s\S]{0,200}data-testid="reorder-proposal-confirm"/);
});

// ---------------------------------------------------------------------------
// 7. Disabled/loading state prevents double-submit
// ---------------------------------------------------------------------------

test("cancel and confirm buttons are disabled while applying", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /disabled=\{applying\}/g);
});

// ---------------------------------------------------------------------------
// 8. No auto-call on render/mount
// ---------------------------------------------------------------------------

test("applyRouteReorderProposal is never called inside a useEffect", () => {
  const useEffectBodies = [...previewSrc.matchAll(/useEffect\s*\(\s*\(\)\s*=>\s*\{([\s\S]{0,1200}?)\}\s*,/g)]
    .map((m) => m[1] ?? "");
  const calledInEffect = useEffectBodies.some((body) => /applyRouteReorderProposal/.test(body));
  assert.equal(calledInEffect, false, "applyRouteReorderProposal must not be called from a useEffect");
});

test("preview renders nothing when proposal is null or dismissed", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /if \(!proposal \|\| dismissed\) return null;/, "must early-return null when no proposal");
});

test("DayPlanModal only supplies a real proposal, never a hardcoded null", () => {
  assert.doesNotMatch(
    dayPlanModalSrc,
    /<ReorderProposalPreview[\s\S]{0,200}proposal=\{null\}/,
    "the Plan My Day result surface must wire the preview with the generated proposal, not null",
  );
});

// ---------------------------------------------------------------------------
// 9. No LLM/AI suggestion call inside the preview itself
// ---------------------------------------------------------------------------

test("ReorderProposalPreview contains no LLM/AI suggestion call", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.doesNotMatch(src, /suggestDayTimeline|anthropic|openai|generateSuggestion|generateRouteReorderProposal/i);
});

// ---------------------------------------------------------------------------
// 10. No route-estimate helper imported/called from the preview
// ---------------------------------------------------------------------------

test("ReorderProposalPreview does not call callRouteEstimate", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.doesNotMatch(src, /callRouteEstimate/, "preview must not call the route-estimate helper");
});

// ---------------------------------------------------------------------------
// 11. CheckRoutePanel not resurrected
// ---------------------------------------------------------------------------

test("CheckRoutePanel is not resurrected", () => {
  assert.doesNotMatch(dayColumnSrc, /function CheckRoutePanel/, "CheckRoutePanel must not return");
  assert.doesNotMatch(dayColumnSrc, /<CheckRoutePanel\b/, "CheckRoutePanel must not be rendered");
});

// ---------------------------------------------------------------------------
// 12. Copy does not imply automatic optimization
// ---------------------------------------------------------------------------

test("copy states nothing changes until confirm and only reorders shown stops", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.match(src, /Nothing changes until you confirm\./);
  assert.match(src, /This only reorders the stops shown below\./);
});

test("no auto-optimization or Optimize Day language anywhere in the preview", () => {
  const src = extractComponent(previewSrc, "ReorderProposalPreview");
  assert.doesNotMatch(src, /Optimize Day/i);
  assert.doesNotMatch(src, /auto-optimi[sz]e/i);
  assert.doesNotMatch(src, /automatically reorder/i);
});

// ---------------------------------------------------------------------------
// 13. Types exported
// ---------------------------------------------------------------------------

test("ReorderProposal and RouteReorderApplyResponse are exported from types/index.ts", () => {
  assert.match(typesSrc, /export interface ReorderProposal/, "ReorderProposal must be exported");
  assert.match(typesSrc, /export interface RouteReorderApplyResponse/, "RouteReorderApplyResponse must be exported");
});

// ---------------------------------------------------------------------------
// 14. DayPlanModal wires a real, AI-generated proposal
// ---------------------------------------------------------------------------

test("DayPlanModal builds the proposal from a RouteReorderProposalGenerateResponse", () => {
  assert.match(
    dayPlanModalSrc,
    /RouteReorderProposalGenerateResponse/,
    "DayPlanModal must accept the generated proposal response type",
  );
  assert.match(
    dayPlanModalSrc,
    /proposedOrder:\s*routeProposal\.proposedOrder/,
    "the ReorderProposal passed to the preview must come from the generated response",
  );
});
