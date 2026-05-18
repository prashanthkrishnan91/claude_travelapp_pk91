/**
 * Post-merge fixes — contract tests.
 *
 * Issue A — CityAutocomplete stacking:
 *   The root wrapper raises z-index and creates an isolate stacking context
 *   when the suggestions dropdown or manual fallback panel is visible, so it
 *   renders above sibling form fields on mobile and desktop.
 *
 * Issue B — Plan My Day canonical attractions:
 *   The no-cluster backend path now calls canonical Google Places attraction
 *   search (search_attraction_results / AttractionSearchRequest).  Attractions
 *   rotate by day_number.  Fails closed to [] on provider error/empty — no AI
 *   Concierge, no Tavily, no mock data.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const autocompleteSrc = readFileSync(
  new URL('../src/components/ui/CityAutocomplete.tsx', import.meta.url),
  'utf8',
);

const tripBuilderFormSrc = readFileSync(
  new URL('../src/components/trips/TripBuilderForm.tsx', import.meta.url),
  'utf8',
);

const planRouterSrc = readFileSync(
  new URL('../../backend/app/routes/plan.py', import.meta.url),
  'utf8',
);

const dayPlanModalSrc = readFileSync(
  new URL('../src/components/trips/DayPlanModal.tsx', import.meta.url),
  'utf8',
);

// ─── Issue A: CityAutocomplete stacking context ───────────────────────────────

test('IssueA: root wrapper applies z-[60] when dropdown is open', () => {
  assert.match(
    autocompleteSrc,
    /z-\[60\]/,
    'Container must apply z-[60] to raise above sibling fields when open',
  );
});

test('IssueA: root wrapper uses isolate class when dropdown is open', () => {
  assert.match(
    autocompleteSrc,
    /isolate/,
    'Container must use isolate to create a stacking context when open',
  );
});

test('IssueA: z-[60] and isolate are conditional on dropdown or manual visibility', () => {
  // Both classes should be gated on a visibility flag, not always applied.
  assert.match(
    autocompleteSrc,
    /isDropdownVisible|open.*showManual|showManual.*open/,
    'z-[60] and isolate must be conditional on open/showManual state',
  );
});

test('IssueA: suggestions dropdown uses z-[100] (higher than previous z-50)', () => {
  assert.match(
    autocompleteSrc,
    /z-\[100\]/,
    'Suggestion dropdown must use z-[100] to render above all siblings',
  );
  assert.ok(
    !autocompleteSrc.includes('z-50'),
    'Legacy z-50 must be replaced with z-[100] on the dropdown',
  );
});

test('IssueA: handleSelect behavior preserved', () => {
  assert.match(
    autocompleteSrc,
    /handleSelect/,
    'handleSelect function must still be present',
  );
});

test('IssueA: outside-click behavior preserved via containerRef', () => {
  assert.match(
    autocompleteSrc,
    /containerRef/,
    'containerRef must still be used for outside-click detection',
  );
  assert.match(
    autocompleteSrc,
    /document\.addEventListener.*mousedown|mousedown.*document\.addEventListener/s,
    'Outside-click listener must still be wired up',
  );
});

test('IssueA: airport resolution API call preserved', () => {
  assert.match(
    autocompleteSrc,
    /resolveAirports/,
    'resolveAirports API call must remain in CityAutocomplete',
  );
});

test('IssueA: TripBuilderForm still has overflow:visible to allow dropdown escape', () => {
  assert.match(
    tripBuilderFormSrc,
    /overflow.*visible/,
    'TripBuilderForm form element must keep overflow:visible',
  );
});

test('IssueA: no layout jump — z-index change is scoped to the open state only', () => {
  // Container gets z-[60] only when isDropdownVisible, not always.
  // If always applied, it would create a permanent stacking context change.
  const alwaysZ60 = /className=.*z-\[60\](?!.*isDropdownVisible|.*open|.*show)/;
  assert.ok(
    !alwaysZ60.test(autocompleteSrc.replace(/\s+/g, ' ')),
    'z-[60] must not be unconditionally applied — only when the dropdown is visible',
  );
});

// ─── Issue B: Plan My Day canonical attractions ───────────────────────────────

test('IssueB: plan.py imports AttractionSearchRequest', () => {
  assert.match(
    planRouterSrc,
    /AttractionSearchRequest/,
    'plan.py must import AttractionSearchRequest for canonical attraction search',
  );
});

test('IssueB: no-cluster path calls search_attraction_results', () => {
  assert.match(
    planRouterSrc,
    /search_attraction_results/,
    'No-cluster plan path must call search_attraction_results',
  );
});

test('IssueB: no-cluster path no longer hardcodes only attractions=[]', () => {
  // The return statement must use the planned_attractions variable, not []
  assert.match(
    planRouterSrc,
    /attractions=planned_attractions/,
    'DayPlanResponse must set attractions=planned_attractions (not a hardcoded [])',
  );
  // The DayPlanResponse constructor must not pass attractions=[] directly
  assert.ok(
    !planRouterSrc.match(/return DayPlanResponse\([^)]*attractions=\[\]/s),
    'DayPlanResponse constructor must not pass attractions=[] directly',
  );
});

test('IssueB: day_number influences attraction selection (rotation offset)', () => {
  assert.match(
    planRouterSrc,
    /day_number.*att_offset|att_offset.*day_number/s,
    'Attraction selection must rotate by day_number via att_offset',
  );
});

test('IssueB: provider-empty/error path still returns attractions=[] (fail closed)', () => {
  assert.match(
    planRouterSrc,
    /planned_attractions\s*=\s*\[\]/,
    'Fail-closed path must assign planned_attractions = [] when provider is empty/errors',
  );
});

test('IssueB: fail-closed path is guarded by except/error handler', () => {
  assert.match(
    planRouterSrc,
    /except\s+Exception/,
    'Canonical attraction search must be wrapped in except Exception for fail-closed safety',
  );
});

test('IssueB: no AI Concierge call introduced', () => {
  assert.ok(
    !planRouterSrc.includes('concierge') && !planRouterSrc.includes('callConcierge'),
    'plan.py must not call AI Concierge for attractions',
  );
});

test('IssueB: no Tavily/live research call introduced', () => {
  assert.ok(
    !planRouterSrc.includes('tavily') && !planRouterSrc.includes('live_research'),
    'plan.py must not call Tavily or live research for attractions',
  );
});

test('IssueB: no mock attraction call introduced', () => {
  assert.ok(
    !planRouterSrc.match(/mock_attraction|_mock_attractions\s*\(/),
    'plan.py must not call any mock attraction source',
  );
});

test('IssueB: restaurant diversity (day_number offset) still present', () => {
  assert.match(
    planRouterSrc,
    /offset\s*=\s*\(payload\.day_number\s*-\s*1\)\s*%\s*pool/,
    'Restaurant day_number offset must still be present',
  );
});

test('IssueB: up to 3 attractions selected per day', () => {
  assert.match(
    planRouterSrc,
    /min\(3,\s*n\)/,
    'Plan should select up to 3 attractions per day',
  );
});

test('IssueB: DayPlanModal handleAcceptAll still present', () => {
  assert.match(
    dayPlanModalSrc,
    /handleAcceptAll/,
    'DayPlanModal handleAcceptAll must still be present',
  );
});

test('IssueB: DayPlanModal handleAdd still present', () => {
  assert.match(
    dayPlanModalSrc,
    /handleAdd/,
    'DayPlanModal handleAdd must still be present',
  );
});

test('IssueB: cluster path behavior unchanged', () => {
  assert.match(
    planRouterSrc,
    /_plan_from_cluster/,
    'Cluster path function must still be present and unchanged',
  );
});
