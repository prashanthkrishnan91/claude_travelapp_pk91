/**
 * Global Controls, Forms, Action Sheets, and Modal Interaction Polish — Stage 3.5 Phase 8H
 *
 * Contract tests verifying:
 * 1.  globals.css .input uses ds-token border and background (no raw rgba/hex for color).
 * 2.  globals.css .input uses focus-visible:outline pattern (not :focus outline: none).
 * 3.  globals.css .input has min-height 44px touch target.
 * 4.  globals.css .select mirrors .input ds-token pattern.
 * 5.  globals.css .label uses Overline typography tokens (text-transform uppercase, ds-type-overline).
 * 6.  globals.css .btn-primary focus-visible uses var(--ds-accent) not raw hex.
 * 7.  globals.css .btn-primary has min-height 2.75rem (44px).
 * 8.  globals.css .btn-secondary is defined with ds-tokens.
 * 9.  globals.css .btn-secondary has focus-visible:outline pattern.
 * 10. globals.css .btn-secondary has min-height 2.75rem (44px).
 * 11. globals.css .btn-ghost focus-visible uses var(--ds-accent) not raw hex.
 * 12. globals.css .btn-ghost has min-height 2.75rem (44px).
 * 13. globals.css .btn-ghost uses color-mix or ds-token (no raw rgba for border/background).
 * 14. EmptyState.tsx uses ds-token text and background classes (no cream-* / white/[.]).
 * 15. StatCard.tsx uses ds-token text classes (no cream-* / brand-* / emerald-*).
 * 16. ResultActionSheet save-action-btn has min-h-[44px] touch target.
 * 17. ResultActionSheet more-actions-toggle has min-h-[44px] touch target.
 * 18. ResultActionSheet action handlers preserved (handleSave, handleUnsave).
 * 19. ResultActionSheet testids preserved (result-action-sheet, save-action-btn, more-actions-toggle, manage-in-saved-link, save-first-hint, trip-actions-guidance, action-error).
 * 20. ResultActionSheet has no backend/provider imports.
 * 21. ResultActionSheet focus-visible:outline on all interactive elements.
 * 22. TripIdeasPanel has no focus:ring-* legacy pattern.
 * 23. TripIdeasPanel uses focus-visible:outline pattern on replaced elements.
 * 24. No nested interactive controls in ResultActionSheet (no <button> inside <button>/<a>).
 * 25. Modal control type attributes: btn-primary buttons should be type-safe.
 * 26. globals.css no raw hex in .input/:focus-visible block (color properties).
 * 27. globals.css no raw hex in .select/:focus-visible block (color properties).
 * 28. globals.css no raw hex in .btn-ghost border/background (color properties).
 * 29. globals.css no raw hex in .label (color properties).
 * 30. globals.css no raw hex in .btn-secondary (color properties).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, '..');

function read(rel) {
  return readFileSync(path.join(root, rel), 'utf8');
}

const globals = read('src/app/globals.css');
const emptyState = read('src/components/ui/EmptyState.tsx');
const statCard = read('src/components/ui/StatCard.tsx');
const actionSheet = read('src/components/explore/ResultActionSheet.tsx');
const ideasPanel = read('src/components/trips/TripIdeasPanel.tsx');

// ── 1. .input ds-token border ────────────────────────────────────────────────

test('.input border uses var(--ds-pen-stroke)', () => {
  assert.ok(globals.includes('var(--ds-pen-stroke)'), '.input block must reference var(--ds-pen-stroke)');
});

test('.input background uses var(--ds-midnight-ink)', () => {
  assert.ok(globals.includes('var(--ds-midnight-ink)'), '.input block must reference var(--ds-midnight-ink)');
});

test('.input color uses var(--ds-text-primary)', () => {
  assert.ok(globals.includes('var(--ds-text-primary)'), '.input block must reference var(--ds-text-primary)');
});

// ── 2. .input focus-visible pattern ──────────────────────────────────────────

test('.input uses :focus-visible (not bare :focus for outline)', () => {
  assert.ok(globals.includes('.input:focus-visible'), '.input must use :focus-visible selector');
  assert.ok(!globals.includes('.input:focus\n'), '.input should not have bare :focus block (only :focus-visible)');
});

test('.input:focus-visible uses outline: 2px solid var(--ds-accent)', () => {
  const focusBlock = globals.slice(globals.indexOf('.input:focus-visible'));
  const blockEnd = focusBlock.indexOf('}');
  const block = focusBlock.slice(0, blockEnd);
  assert.ok(block.includes('var(--ds-accent)'), '.input:focus-visible must use var(--ds-accent) outline');
  assert.ok(block.includes('outline: 2px'), '.input:focus-visible must use 2px outline');
});

test('.input has no outline: none', () => {
  const inputSection = globals.slice(globals.indexOf('.input {'), globals.indexOf('.input::placeholder'));
  assert.ok(!inputSection.includes('outline: none'), '.input must not suppress focus with outline: none');
});

// ── 3. .input touch target ───────────────────────────────────────────────────

test('.input has min-height 2.75rem (44px touch target)', () => {
  const inputSection = globals.slice(globals.indexOf('.input {'), globals.indexOf('.input::placeholder'));
  assert.ok(inputSection.includes('min-height: 2.75rem'), '.input must have min-height: 2.75rem for 44px touch target');
});

// ── 4. .select ds-token pattern ──────────────────────────────────────────────

test('.select border uses var(--ds-pen-stroke)', () => {
  const selectSection = globals.slice(globals.indexOf('.select {'), globals.indexOf('.select:focus-visible'));
  assert.ok(selectSection.includes('var(--ds-pen-stroke)'), '.select must use var(--ds-pen-stroke) border');
});

test('.select uses :focus-visible (not bare :focus)', () => {
  assert.ok(globals.includes('.select:focus-visible'), '.select must use :focus-visible');
});

test('.select has min-height 2.75rem', () => {
  const selectSection = globals.slice(globals.indexOf('.select {'), globals.indexOf('.select:focus-visible'));
  assert.ok(selectSection.includes('min-height: 2.75rem'), '.select must have min-height: 2.75rem');
});

// ── 5. .label Overline grammar ────────────────────────────────────────────────

test('.label uses var(--ds-type-overline-size)', () => {
  const labelSection = globals.slice(globals.indexOf('.label {'), globals.indexOf('.badge {'));
  assert.ok(labelSection.includes('var(--ds-type-overline-size)'), '.label must use overline size token');
});

test('.label uses var(--ds-type-overline-tracking)', () => {
  const labelSection = globals.slice(globals.indexOf('.label {'), globals.indexOf('.badge {'));
  assert.ok(labelSection.includes('var(--ds-type-overline-tracking)'), '.label must use overline tracking token');
});

test('.label uses text-transform uppercase (Overline grammar)', () => {
  const labelSection = globals.slice(globals.indexOf('.label {'), globals.indexOf('.badge {'));
  assert.ok(labelSection.includes('text-transform: uppercase'), '.label must be uppercase (Overline)');
});

test('.label uses var(--ds-text-tertiary) (no raw hex)', () => {
  const labelSection = globals.slice(globals.indexOf('.label {'), globals.indexOf('.badge {'));
  assert.ok(labelSection.includes('var(--ds-text-tertiary)'), '.label must use ds-text-tertiary color token');
});

// ── 6. .btn-primary focus-visible ds-token ───────────────────────────────────

test('.btn-primary:focus-visible uses var(--ds-accent) not raw hex', () => {
  const focusBlock = globals.slice(globals.indexOf('.btn-primary:focus-visible'), globals.indexOf('.btn-primary:focus-visible') + 100);
  assert.ok(focusBlock.includes('var(--ds-accent)'), '.btn-primary:focus-visible must use var(--ds-accent)');
  assert.ok(!focusBlock.includes('#e8b854'), '.btn-primary:focus-visible must not use raw hex #e8b854');
});

// ── 7. .btn-primary touch target ─────────────────────────────────────────────

test('.btn-primary has min-height 2.75rem', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-primary {'), globals.indexOf('.btn-primary:hover'));
  assert.ok(btnSection.includes('min-height: 2.75rem'), '.btn-primary must have min-height: 2.75rem');
});

// ── 8. .btn-secondary exists with ds-tokens ───────────────────────────────────

test('.btn-secondary is defined in globals.css', () => {
  assert.ok(globals.includes('.btn-secondary {'), '.btn-secondary class must be defined');
});

test('.btn-secondary uses var(--ds-pen-stroke) border', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-secondary {'), globals.indexOf('.btn-secondary:hover'));
  assert.ok(btnSection.includes('var(--ds-pen-stroke)'), '.btn-secondary must use var(--ds-pen-stroke)');
});

test('.btn-secondary uses var(--ds-carbon-mist) background (defined token)', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-secondary {'), globals.indexOf('.btn-secondary:hover'));
  assert.ok(btnSection.includes('var(--ds-carbon-mist)'), '.btn-secondary must use var(--ds-carbon-mist) not undefined var(--ds-carbon)');
});

test('.btn-secondary uses var(--ds-text-secondary) color', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-secondary {'), globals.indexOf('.btn-secondary:hover'));
  assert.ok(btnSection.includes('var(--ds-text-secondary)'), '.btn-secondary must use var(--ds-text-secondary)');
});

// ── 9. .btn-secondary focus-visible ──────────────────────────────────────────

test('.btn-secondary:focus-visible uses var(--ds-accent)', () => {
  const idx = globals.indexOf('.btn-secondary:focus-visible');
  assert.ok(idx !== -1, '.btn-secondary:focus-visible must be defined');
  const block = globals.slice(idx, idx + 120);
  assert.ok(block.includes('var(--ds-accent)'), '.btn-secondary:focus-visible must use var(--ds-accent)');
});

// ── 10. .btn-secondary touch target ──────────────────────────────────────────

test('.btn-secondary has min-height 2.75rem', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-secondary {'), globals.indexOf('.btn-secondary:hover'));
  assert.ok(btnSection.includes('min-height: 2.75rem'), '.btn-secondary must have min-height: 2.75rem');
});

// ── 11. .btn-ghost focus-visible ds-token ────────────────────────────────────

test('.btn-ghost:focus-visible uses var(--ds-accent) not raw hex', () => {
  const idx = globals.indexOf('.btn-ghost:focus-visible');
  assert.ok(idx !== -1, '.btn-ghost:focus-visible must exist');
  const block = globals.slice(idx, idx + 120);
  assert.ok(block.includes('var(--ds-accent)'), '.btn-ghost:focus-visible must use var(--ds-accent)');
  assert.ok(!block.includes('#e8b854'), '.btn-ghost:focus-visible must not use raw hex');
});

// ── 12. .btn-ghost touch target ──────────────────────────────────────────────

test('.btn-ghost has min-height 2.75rem', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-ghost {'), globals.indexOf('.btn-ghost:hover'));
  assert.ok(btnSection.includes('min-height: 2.75rem'), '.btn-ghost must have min-height: 2.75rem');
});

// ── 13. .btn-ghost no raw rgba for color properties ──────────────────────────

test('.btn-ghost uses color-mix or ds-token for border/background (no raw rgba color)', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-ghost {'), globals.indexOf('.btn-ghost:hover'));
  assert.ok(
    btnSection.includes('color-mix(') || btnSection.includes('var(--ds-'),
    '.btn-ghost must use color-mix or ds-token for border/bg'
  );
  // The only rgba in .btn-ghost base should be for elevation shadows, not color
  const borderLine = btnSection.split('\n').find(l => l.trim().startsWith('border:') || l.trim().startsWith('border-color:'));
  if (borderLine) {
    assert.ok(!borderLine.includes('rgba(255'), '.btn-ghost border must not use rgba(255,... for color');
  }
});

// ── 14. EmptyState.tsx ds-tokens ─────────────────────────────────────────────

test('EmptyState has no cream-* legacy classes', () => {
  assert.ok(!emptyState.includes('cream-'), 'EmptyState must not use cream-* classes');
});

test('EmptyState has no bg-white/[ legacy classes', () => {
  assert.ok(!emptyState.includes('bg-white/['), 'EmptyState must not use bg-white/[ alpha classes');
});

test('EmptyState uses text-ds-text for heading', () => {
  assert.ok(emptyState.includes('text-ds-text'), 'EmptyState heading must use text-ds-text');
});

test('EmptyState uses text-ds-text-tertiary for description', () => {
  assert.ok(emptyState.includes('text-ds-text-tertiary'), 'EmptyState description must use text-ds-text-tertiary');
});

test('EmptyState uses bg-ds-carbon for icon container', () => {
  assert.ok(emptyState.includes('bg-ds-carbon'), 'EmptyState icon container must use bg-ds-carbon');
});

test('EmptyState uses border-ds-pen-stroke for icon container', () => {
  assert.ok(emptyState.includes('border-ds-pen-stroke'), 'EmptyState icon container must use border-ds-pen-stroke');
});

// ── 15. StatCard.tsx ds-tokens ────────────────────────────────────────────────

test('StatCard has no cream-* legacy classes', () => {
  assert.ok(!statCard.includes('text-cream-'), 'StatCard must not use text-cream-* classes');
});

test('StatCard has no brand-* hard-coded default colorClass', () => {
  assert.ok(!statCard.includes('bg-brand-'), 'StatCard must not use bg-brand-* as default colorClass');
});

test('StatCard has no emerald-* classes', () => {
  assert.ok(!statCard.includes('text-emerald-'), 'StatCard must not use text-emerald-* classes');
});

test('StatCard uses text-ds-text for value', () => {
  assert.ok(statCard.includes('text-ds-text'), 'StatCard value must use text-ds-text');
});

test('StatCard uses text-ds-text-tertiary for label', () => {
  assert.ok(statCard.includes('text-ds-text-tertiary'), 'StatCard label must use text-ds-text-tertiary');
});

test('StatCard uses text-ds-trust for positive trend', () => {
  assert.ok(statCard.includes('text-ds-trust'), 'StatCard positive trend must use text-ds-trust');
});

// ── 16–17. ResultActionSheet touch targets ────────────────────────────────────

test('ResultActionSheet save-action-btn has min-h-[44px]', () => {
  const saveBlock = actionSheet.slice(actionSheet.indexOf('save-action-btn'));
  // Walk back to find the button element
  const btnStart = actionSheet.lastIndexOf('<button', actionSheet.indexOf('save-action-btn'));
  const btnSrc = actionSheet.slice(btnStart, actionSheet.indexOf('</button>', btnStart) + 9);
  assert.ok(btnSrc.includes('min-h-[44px]'), 'save-action-btn button must have min-h-[44px]');
});

test('ResultActionSheet more-actions-toggle has min-h-[44px]', () => {
  const moreIdx = actionSheet.indexOf('more-actions-toggle');
  const btnStart = actionSheet.lastIndexOf('<button', moreIdx);
  const btnSrc = actionSheet.slice(btnStart, actionSheet.indexOf('</button>', btnStart) + 9);
  assert.ok(btnSrc.includes('min-h-[44px]'), 'more-actions-toggle button must have min-h-[44px]');
});

// ── 18. ResultActionSheet handlers preserved ──────────────────────────────────

test('ResultActionSheet handleSave function preserved', () => {
  assert.ok(actionSheet.includes('async function handleSave'), 'handleSave must be present');
});

test('ResultActionSheet handleUnsave function preserved', () => {
  assert.ok(actionSheet.includes('async function handleUnsave'), 'handleUnsave must be present');
});

test('ResultActionSheet saveItem api call preserved', () => {
  assert.ok(actionSheet.includes('saveItem('), 'saveItem call must be preserved');
});

test('ResultActionSheet deleteSavedItem api call preserved', () => {
  assert.ok(actionSheet.includes('deleteSavedItem('), 'deleteSavedItem call must be preserved');
});

// ── 19. ResultActionSheet testids preserved ───────────────────────────────────

test('ResultActionSheet has result-action-sheet testid', () => {
  assert.ok(actionSheet.includes('data-testid="result-action-sheet"'), 'result-action-sheet testid must exist');
});

test('ResultActionSheet has save-action-btn testid', () => {
  assert.ok(actionSheet.includes('data-testid="save-action-btn"'), 'save-action-btn testid must exist');
});

test('ResultActionSheet has more-actions-toggle testid', () => {
  assert.ok(actionSheet.includes('data-testid="more-actions-toggle"'), 'more-actions-toggle testid must exist');
});

test('ResultActionSheet has manage-in-saved-link testid', () => {
  assert.ok(actionSheet.includes('data-testid="manage-in-saved-link"'), 'manage-in-saved-link testid must exist');
});

test('ResultActionSheet has save-first-hint testid', () => {
  assert.ok(actionSheet.includes('data-testid="save-first-hint"'), 'save-first-hint testid must exist');
});

test('ResultActionSheet has trip-actions-guidance testid', () => {
  assert.ok(actionSheet.includes('data-testid="trip-actions-guidance"'), 'trip-actions-guidance testid must exist');
});

test('ResultActionSheet has action-error testid', () => {
  assert.ok(actionSheet.includes('data-testid="action-error"'), 'action-error testid must exist');
});

// ── 20. ResultActionSheet no backend imports ──────────────────────────────────

test('ResultActionSheet has no backend/provider imports', () => {
  assert.ok(!actionSheet.includes("from '@/app/api"), 'ResultActionSheet must not import from api routes');
  assert.ok(!actionSheet.includes("from '@/services/"), 'ResultActionSheet must not import from backend services');
  assert.ok(!actionSheet.includes('concierge'), 'ResultActionSheet must not import concierge modules');
});

// ── 21. ResultActionSheet focus-visible on interactive elements ───────────────

test('ResultActionSheet save-action-btn has focus-visible:outline', () => {
  assert.ok(actionSheet.includes('focus-visible:outline'), 'ResultActionSheet must use focus-visible:outline');
  assert.ok(!actionSheet.includes('focus:ring-'), 'ResultActionSheet must not use legacy focus:ring-*');
});

// ── 22–23. TripIdeasPanel focus pattern ──────────────────────────────────────

test('TripIdeasPanel has no focus:ring-* legacy pattern', () => {
  assert.ok(!ideasPanel.includes('focus:ring-'), 'TripIdeasPanel must not have focus:ring-* pattern');
});

test('TripIdeasPanel has no focus:outline-none (bare)', () => {
  assert.ok(!ideasPanel.includes('focus:outline-none'), 'TripIdeasPanel must not suppress focus with focus:outline-none');
});

test('TripIdeasPanel uses focus-visible:outline pattern on inputs', () => {
  assert.ok(
    ideasPanel.includes('focus-visible:outline focus-visible:outline-2 focus-visible:outline-ds-accent'),
    'TripIdeasPanel must use focus-visible:outline-ds-accent pattern'
  );
});

// ── 24. No nested interactive controls in ResultActionSheet ───────────────────

test('ResultActionSheet has no <button> inside another <button>', () => {
  // Static check: no button immediately inside another button element
  const buttonPositions = [];
  let idx = 0;
  while ((idx = actionSheet.indexOf('<button', idx)) !== -1) {
    buttonPositions.push(idx);
    idx++;
  }
  // Each button should have its closing </button> before the next <button> starts
  // (nested buttons are structurally invalid HTML)
  for (let i = 0; i < buttonPositions.length - 1; i++) {
    const closeIdx = actionSheet.indexOf('</button>', buttonPositions[i]);
    assert.ok(
      closeIdx !== -1 && closeIdx < buttonPositions[i + 1],
      `Button at position ${buttonPositions[i]} must close before next button opens`
    );
  }
});

// ── 25. Semantic elements — save and more-actions are buttons ─────────────────

test('ResultActionSheet save-action-btn is a <button> element', () => {
  const btnStart = actionSheet.lastIndexOf('<button', actionSheet.indexOf('save-action-btn'));
  assert.ok(btnStart !== -1, 'save-action-btn must be a <button> element');
});

test('ResultActionSheet more-actions-toggle is a <button> element', () => {
  const btnStart = actionSheet.lastIndexOf('<button', actionSheet.indexOf('more-actions-toggle'));
  assert.ok(btnStart !== -1, 'more-actions-toggle must be a <button> element');
});

test('ResultActionSheet manage-in-saved-link is a <Link> element', () => {
  const linkStart = actionSheet.lastIndexOf('<Link', actionSheet.indexOf('manage-in-saved-link'));
  assert.ok(linkStart !== -1, 'manage-in-saved-link must be a <Link> element');
});

// ── 26–30. No raw hex in specific color properties of touched classes ─────────

test('globals.css .input:focus-visible block has no raw hex color value', () => {
  const idx = globals.indexOf('.input:focus-visible');
  const block = globals.slice(idx, globals.indexOf('}', idx) + 1);
  // Should not contain a hex color like #xxxxxx for color properties
  assert.ok(!block.match(/border-color:\s*#[0-9a-fA-F]/), '.input:focus-visible border-color must not be raw hex');
  assert.ok(!block.match(/outline:\s*\d+px\s+solid\s+#[0-9a-fA-F]/), '.input:focus-visible outline must not be raw hex');
});

test('globals.css .btn-secondary block has no raw hex for color/background/border', () => {
  const idx = globals.indexOf('.btn-secondary {');
  const endIdx = globals.indexOf('.btn-secondary:hover');
  const block = globals.slice(idx, endIdx);
  // color, background, border should not be raw hex - they should be CSS vars
  const colorLines = block.split('\n').filter(l =>
    l.trim().startsWith('color:') || l.trim().startsWith('background:') || l.trim().startsWith('border:')
  );
  for (const line of colorLines) {
    assert.ok(!line.match(/#[0-9a-fA-F]{3,6}/), `.btn-secondary color properties must not use raw hex: ${line.trim()}`);
  }
});

test('globals.css .label has no raw hex color', () => {
  const idx = globals.indexOf('.label {');
  const block = globals.slice(idx, globals.indexOf('}', idx) + 1);
  assert.ok(!block.match(/color:\s*#[0-9a-fA-F]/), '.label color must not be raw hex');
});

test('globals.css .btn-ghost:focus-visible uses var(--ds-accent) not raw hex', () => {
  const idx = globals.indexOf('.btn-ghost:focus-visible');
  const block = globals.slice(idx, globals.indexOf('}', idx) + 1);
  assert.ok(block.includes('var(--ds-accent)'), '.btn-ghost:focus-visible must use var(--ds-accent)');
  assert.ok(!block.match(/#[0-9a-fA-F]{6}/), '.btn-ghost:focus-visible must not use raw hex');
});

test('globals.css .btn-primary:focus-visible uses var(--ds-accent) not raw hex #e8b854', () => {
  const idx = globals.indexOf('.btn-primary:focus-visible');
  const block = globals.slice(idx, globals.indexOf('}', idx) + 1);
  assert.ok(block.includes('var(--ds-accent)'), '.btn-primary:focus-visible must use var(--ds-accent)');
  assert.ok(!block.includes('#e8b854'), '.btn-primary:focus-visible must not use raw hex #e8b854');
});

// ── PATCH: Issue 1 — .btn-secondary undefined var(--ds-carbon) fix ───────────

test('.btn-secondary background is defined token (not undefined var(--ds-carbon))', () => {
  const btnSection = globals.slice(globals.indexOf('.btn-secondary {'), globals.indexOf('.btn-secondary:hover'));
  const bgLine = btnSection.split('\n').find(l => l.trim().startsWith('background:'));
  assert.ok(bgLine, '.btn-secondary must have a background: property');
  assert.ok(!bgLine.trim().endsWith('var(--ds-carbon);'), `.btn-secondary must not use undefined var(--ds-carbon): ${bgLine.trim()}`);
  assert.ok(bgLine.includes('var(--ds-carbon-mist)'), `.btn-secondary background must use var(--ds-carbon-mist): ${bgLine.trim()}`);
});

// ── PATCH: Issue 2 — .btn-primary raw hex removed ────────────────────────────

test('globals.css .btn-primary base block has no raw hex for gradient or color', () => {
  const idx = globals.indexOf('.btn-primary {');
  const endIdx = globals.indexOf('.btn-primary:hover');
  const block = globals.slice(idx, endIdx);
  const colorLines = block.split('\n').filter(l =>
    l.trim().startsWith('background:') || l.trim().startsWith('color:')
  );
  for (const line of colorLines) {
    assert.ok(!line.match(/#[0-9a-fA-F]{3,6}/), `.btn-primary color/background must not use raw hex: ${line.trim()}`);
  }
});

test('globals.css .btn-primary gradient uses var(--ds-accent)', () => {
  const idx = globals.indexOf('.btn-primary {');
  const endIdx = globals.indexOf('.btn-primary:hover');
  const block = globals.slice(idx, endIdx);
  assert.ok(block.includes('var(--ds-accent)'), '.btn-primary gradient must include var(--ds-accent)');
});

test('globals.css .btn-primary color uses var(--ds-text-inverse)', () => {
  const idx = globals.indexOf('.btn-primary {');
  const endIdx = globals.indexOf('.btn-primary:hover');
  const block = globals.slice(idx, endIdx);
  assert.ok(block.includes('var(--ds-text-inverse)'), '.btn-primary text color must use var(--ds-text-inverse)');
});

// ── PATCH: Issue 3 — ResultActionSheet type="button" and manage-in-saved-link ─

test('ResultActionSheet save-action-btn has type="button"', () => {
  const idx = actionSheet.indexOf('save-action-btn');
  const btnStart = actionSheet.lastIndexOf('<button', idx);
  const ctx = actionSheet.slice(btnStart, btnStart + 300);
  assert.ok(ctx.includes('type="button"'), 'save-action-btn must have type="button"');
});

test('ResultActionSheet more-actions-toggle has type="button"', () => {
  const idx = actionSheet.indexOf('more-actions-toggle');
  const btnStart = actionSheet.lastIndexOf('<button', idx);
  const ctx = actionSheet.slice(btnStart, btnStart + 300);
  assert.ok(ctx.includes('type="button"'), 'more-actions-toggle must have type="button"');
});

test('ResultActionSheet manage-in-saved-link has min-h-[44px]', () => {
  const idx = actionSheet.indexOf('manage-in-saved-link');
  const linkStart = actionSheet.lastIndexOf('<Link', idx);
  const ctx = actionSheet.slice(linkStart, linkStart + 400);
  assert.ok(ctx.includes('min-h-[44px]'), 'manage-in-saved-link must have min-h-[44px] touch target');
});

// ── PATCH: Issue 4 — TripIdeasPanel type="button" on non-submit buttons ──────

function buttonCtx(src, anchor) {
  const idx = src.indexOf(anchor);
  if (idx === -1) return '';
  const start = src.lastIndexOf('<button', idx);
  return start === -1 ? '' : src.slice(start, start + 350);
}

test('TripIdeasPanel panel-toggle button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'setOpen((v) => !v)');
  assert.ok(ctx.includes('type="button"'), 'panel open/close button must have type="button"');
});

test('TripIdeasPanel remove-idea button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'onClick={onRemove}');
  assert.ok(ctx.includes('type="button"'), 'remove idea button must have type="button"');
});

test('TripIdeasPanel status-option buttons have type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'handleStatusChange(opt.value)');
  assert.ok(ctx.includes('type="button"'), 'status option buttons must have type="button"');
});

test('TripIdeasPanel note-toggle button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'setNoteOpen((v) => !v)');
  assert.ok(ctx.includes('type="button"'), 'note toggle button must have type="button"');
});

test('TripIdeasPanel assign button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'onAssign(selectedDay)');
  assert.ok(ctx.includes('type="button"'), 'assign/add-to-day button must have type="button"');
});

test('TripIdeasPanel status-filter buttons have type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'setStatusFilter(opt.value)');
  assert.ok(ctx.includes('type="button"'), 'status filter buttons must have type="button"');
});

test('TripIdeasPanel reset-filters button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, 'onClick={handleReset}');
  assert.ok(ctx.includes('type="button"'), 'reset filters button must have type="button"');
});

test('TripIdeasPanel show-more button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, '[group.key]: true }))');
  assert.ok(ctx.includes('type="button"'), 'show more button must have type="button"');
});

test('TripIdeasPanel show-less button has type="button"', () => {
  const ctx = buttonCtx(ideasPanel, '[group.key]: false }))');
  assert.ok(ctx.includes('type="button"'), 'show less button must have type="button"');
});
