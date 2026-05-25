/**
 * Journey Desk v1B — Ideas Tray (placement-first, IA pivot).
 *
 * The Ideas Tray is a lightweight quick-placement overlay only:
 * mobile bottom sheet / desktop right drawer, one bold primary action per card,
 * note preview (read-only), contextual secondary actions — all wired to real
 * durable writes (day-level assignIdeaToDay, status/note updateIdeaMeta,
 * deleteItem). Note editing and status management belong in the Ideas tab, not
 * the tray.
 *
 * IA contract (post-pivot):
 *   - Brief "Review ideas" → switches to Ideas tab workspace (setActiveMobileWorkspace("ideas"))
 *   - ExpandedDayPanel "Add from Ideas" → opens IdeasTray for quick placement
 *   - IdeasTray has NO note editor and NO status chip row
 *
 * Source-scan contract tests (no DOM/browser in this environment).
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tray = readFileSync(
  new URL("../src/components/trips/IdeasTray.tsx", import.meta.url),
  "utf8",
);
const page = readFileSync(
  new URL("../src/app/trips/[id]/page.tsx", import.meta.url),
  "utf8",
);
const css = readFileSync(
  new URL("../src/app/globals.css", import.meta.url),
  "utf8",
);
const ideasPanel = readFileSync(
  new URL("../src/components/trips/TripIdeasPanel.tsx", import.meta.url),
  "utf8",
);

// ── Tray shell ────────────────────────────────────────────────────────────────

test("tray has a stable testid and is a modal dialog", () => {
  assert.match(tray, /data-testid="journey-desk-ideas-tray"/);
  assert.match(tray, /role="dialog"/);
  assert.match(tray, /aria-modal="true"/);
});

test("tray header communicates purpose — placement, not a duplicate Ideas page", () => {
  assert.match(tray, /Place one in\./);
  assert.match(tray, /Place saved ideas into your plan/);
  assert.match(tray, /from your Private Folio/i);
});

test("each card offers a quiet fallback to the legacy Ideas workspace", () => {
  assert.match(tray, /data-testid="ideas-tray-manage-link"/);
  assert.match(tray, /Manage in Ideas/);
  assert.match(tray, /onManage/);
  assert.doesNotMatch(tray, /Edit note in Ideas/);
});

test("tray shows the real candidate count from the ideas array", () => {
  assert.match(tray, /\{ideas\.length\}\s*\{ideas\.length === 1 \? "candidate" : "candidates"\}/);
});

test("tray is a bottom sheet on mobile and a right drawer on desktop", () => {
  assert.match(tray, /bottom-0/);
  assert.match(tray, /lg:right-0/);
});

test("tray filter chips cover All/Hotels/Flights/Dining/Places with real counts", () => {
  assert.match(tray, /label: "All"/);
  assert.match(tray, /label: "Hotels"/);
  assert.match(tray, /label: "Flights"/);
  assert.match(tray, /label: "Dining"/);
  assert.match(tray, /label: "Places"/);
  // counts derive from real itemType, never fabricated
  assert.match(tray, /ideas\.filter\(\(i\) => i\.itemType === key\)\.length/);
});

// ── Placement-first card, honest writes ───────────────────────────────────────

test("card primary action is placement-first and day-level (Add to Day… / Keep as Maybe)", () => {
  assert.match(tray, /Add to Day…/);
  assert.match(tray, /Keep as Maybe/);
  assert.match(tray, /Add to which day/);
});

test("placement is wired to the real day-level write via onAssign(day.id)", () => {
  assert.match(tray, /onAssign\(day\.id\)/);
  assert.match(tray, /const dayAssignable = days\.length > 0/);
});

test("no fabricated slot label — placement never claims a slot", () => {
  assert.doesNotMatch(tray, /·\s*(Morning|Afternoon|Evening)/i);
  assert.doesNotMatch(tray, /Add to Day \d+ ·/);
});

test("status fallback uses the durable updateIdeaMeta path (ideaStatus maybe)", () => {
  assert.match(tray, /ideaStatus: "maybe"/);
});

test("primary action uses marine ink; it is the one bold action per card", () => {
  assert.match(tray, /data-testid="ideas-tray-primary-action"[\s\S]{0,400}bg-ds-marine-ink/);
});

// ── Note preview (read-only) — no editor in tray ─────────────────────────────

test("private marginalia reads the saved user note (carryover preserved)", () => {
  assert.match(tray, /x\.userNote \?\? x\.user_note/);
  assert.match(tray, /data-testid="ideas-tray-note-private"/);
  assert.match(tray, /jd-note-private/);
});

test("private note is italic serif (distinct from concierge reason)", () => {
  assert.match(tray, /jd-note-private[\s\S]{0,80}font-serif italic/);
});

test("tray reads the SAME note key as the legacy Ideas tab and the carryover", () => {
  // The legacy TripIdeasPanel reads userNote ?? user_note; the Saved -> Trip
  // Ideas carryover writes details.userNote. The tray must read the same shape
  // so any note visible on the old tab is visible in the tray.
  assert.match(ideasPanel, /d\.userNote \?\? d\.user_note/);
  assert.match(tray, /x\.userNote \?\? x\.user_note/);
});

test("concierge reason is a distinct muted helper, shown only when real and not equal to the user note", () => {
  assert.match(tray, /data-testid="ideas-tray-note-concierge"/);
  assert.match(tray, /reason && reason !== note/);
});

test("provider facts (rating) render only from real data", () => {
  assert.match(tray, /const r = x\.rating as number/);
  assert.match(tray, /if \(!r \|\| typeof r !== "number"\) return null/);
});

test("tray fabricates no prices/weather", () => {
  assert.doesNotMatch(tray, /\$\d|weather|°|sunny|rain/i);
});

// ── Tray does NOT contain note editor or status chip row (IA pivot) ───────────

test("tray has no inline note editor — editing belongs in the Ideas tab", () => {
  assert.doesNotMatch(tray, /data-testid="ideas-tray-note-editor"/);
  assert.doesNotMatch(tray, /data-testid="ideas-tray-note-textarea"/);
  assert.doesNotMatch(tray, /data-testid="ideas-tray-note-save"/);
  assert.doesNotMatch(tray, /data-testid="ideas-tray-note-cancel"/);
  assert.doesNotMatch(tray, /data-testid="ideas-tray-note-edit-btn"/);
});

test("tray has no status chip row — Must-do/Maybe/Skip management belongs in the Ideas tab", () => {
  assert.doesNotMatch(tray, /data-testid="ideas-tray-status-chips"/);
  assert.doesNotMatch(tray, /IDEA_STATUS_OPTIONS/);
  assert.doesNotMatch(tray, /onUpdateStatus/);
});

test("note preview still renders in collapsed state (private marginalia)", () => {
  assert.match(tray, /data-testid="ideas-tray-note-private"/);
  assert.match(tray, /jd-note-private/);
});

// ── Contextual secondary actions (quiet links) ────────────────────────────────

test("secondary actions are contextual to real data (map link, flight booking)", () => {
  assert.match(tray, /mapsUrl &&/);
  assert.match(tray, /item\.itemType === "flight" && bookingUrl/);
  assert.match(tray, /Google Flights/);
});

test("tray closes on Escape and on scrim/close click", () => {
  assert.match(tray, /e\.key === "Escape"/);
  assert.match(tray, /aria-label="Close ideas tray"/);
});

// ── Page integration — corrected IA (Brief → Ideas tab; ExpandedDayPanel → Tray) ──

test("page imports and renders the Ideas Tray", () => {
  assert.match(page, /import \{ IdeasTray \} from "@\/components\/trips\/IdeasTray"/);
  assert.match(page, /<IdeasTray/);
});

test("the v1A Brief 'Review ideas' switches to the Ideas tab workspace (not open tray)", () => {
  // Brief's onReview routes to the Ideas tab, not the placement overlay.
  assert.match(page, /onReview=\{\(\) => setActiveMobileWorkspace\("ideas"\)\}/);
  // ideasTrayOpen state is still used by ExpandedDayPanel's Add from Ideas entry point.
  assert.match(page, /const \[ideasTrayOpen, setIdeasTrayOpen\] = useState\(false\)/);
});

test("Brief 'Review ideas' does NOT open IdeasTray directly", () => {
  // The Brief onReview must not call setIdeasTrayOpen(true).
  assert.doesNotMatch(page, /onReview=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

test("ExpandedDayPanel 'Add from Ideas' still opens IdeasTray for quick day-specific placement", () => {
  assert.match(page, /onAddFromIdeas=\{\(\) => setIdeasTrayOpen\(true\)\}/);
});

test("the Journey Desk has no duplicate launcher pill", () => {
  assert.doesNotMatch(page, /journey-desk-ideas-launcher/);
});

test("tray actions are wired to real durable writes only", () => {
  assert.match(page, /await assignIdeaToDay\(itemId, dayId\)/);
  assert.match(page, /await updateIdeaMeta\(itemId, currentDetails, patch\)/);
  assert.match(page, /await deleteItem\(itemId\)/);
  assert.match(page, /onAssign=\{handleIdeaAssign\}/);
  assert.match(page, /onUpdateMeta=\{handleIdeaMeta\}/);
  assert.match(page, /onRemove=\{handleIdeaRemove\}/);
});

test("the manage fallback opens the legacy Ideas workspace (no new route)", () => {
  assert.match(page, /onManage=\{\(\) => \{[\s\S]{0,120}setIdeasTrayOpen\(false\)[\s\S]{0,120}setActiveMobileWorkspace\("ideas"\)/);
});

test("v1A surfaces are not regressed (cover, Brief, Dayboard still present)", () => {
  assert.match(page, /data-testid="trip-chapter-cover"/);
  assert.match(page, /<TripBrief/);
  assert.match(page, /<Dayboard/);
});

// ── CSS primitives, reduced-motion guarded ────────────────────────────────────

test("tray paper surfaces and brass note hairline are defined with tokens", () => {
  assert.match(css, /\.journey-desk-tray \{/);
  assert.match(css, /\.jd-tray-card \{/);
  const idx = css.indexOf(".jd-note-private {");
  assert.ok(idx !== -1, ".jd-note-private must be defined");
  assert.match(css.slice(idx, idx + 200), /var\(--ds-ember-brass\)/);
});

test("tray entrance animation is reduced-motion guarded", () => {
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]{0,120}\.jd-tray-enter \{ animation: none/);
});
