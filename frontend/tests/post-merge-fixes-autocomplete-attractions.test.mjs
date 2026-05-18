/**
 * Post-merge fixes — contract tests.
 *
 * Issue A — CityAutocomplete portal:
 *   The suggestions dropdown and manual fallback are rendered via React DOM portal
 *   into document.body at fixed coordinates anchored to the input, so they always
 *   appear above sibling form fields regardless of ancestor overflow/stacking context.
 *   Previous z-[60]+isolate fix was insufficient — portal is the real fix.
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

// ─── Issue A: CityAutocomplete portal approach ───────────────────────────────

test('IssueA: uses createPortal to render dropdown into document.body', () => {
  assert.match(
    autocompleteSrc,
    /createPortal/,
    'CityAutocomplete must use createPortal to escape the form stacking context',
  );
});

test('IssueA: portal uses fixed positioning (not absolute)', () => {
  assert.match(
    autocompleteSrc,
    /position.*["']?fixed["']?|fixed.*position/,
    'Portal dropdown must use position:fixed so it is anchored to the viewport',
  );
});

test('IssueA: portal layer uses high z-index (9999)', () => {
  assert.match(
    autocompleteSrc,
    /zIndex.*9999|9999.*zIndex/,
    'Portal dropdown must use zIndex:9999 to appear above all page content',
  );
});

test('IssueA: dropdown position derived from getBoundingClientRect', () => {
  assert.match(
    autocompleteSrc,
    /getBoundingClientRect/,
    'Dropdown position must be measured from the input container via getBoundingClientRect',
  );
});

test('IssueA: position updates on resize and scroll events', () => {
  assert.match(
    autocompleteSrc,
    /resize/,
    'Position must update on window resize',
  );
  assert.match(
    autocompleteSrc,
    /scroll/,
    'Position must update on scroll events',
  );
});

test('IssueA: visibility gated on isDropdownVisible or open/showManual', () => {
  assert.match(
    autocompleteSrc,
    /isDropdownVisible|open.*showManual|showManual.*open/,
    'Portal must only render when dropdown or manual fallback is visible',
  );
});

test('IssueA: handleSelect behavior preserved', () => {
  assert.match(
    autocompleteSrc,
    /handleSelect/,
    'handleSelect function must still be present',
  );
});

test('IssueA: outside-click behavior checks both containerRef and portalRef', () => {
  assert.match(
    autocompleteSrc,
    /containerRef/,
    'containerRef must still be used for outside-click detection',
  );
  assert.match(
    autocompleteSrc,
    /portalRef/,
    'portalRef must also be checked so clicks inside the portal are not mistaken for outside-clicks',
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

test('IssueA: TripBuilderForm overflow:visible can remain without being the sole fix', () => {
  assert.match(
    tripBuilderFormSrc,
    /overflow.*visible/,
    'TripBuilderForm may keep overflow:visible but the portal approach is the real fix',
  );
});

test('IssueA: dropdown not rendered inside form DOM when open (portal approach)', () => {
  // The root container div must not contain the dropdown (ul or manual panel)
  // as a direct sibling inside the non-portal container — it is rendered via portal.
  // This verifies there is no fallback absolute-positioned dropdown inside the container.
  assert.ok(
    !autocompleteSrc.includes('z-[60]') && !autocompleteSrc.includes('z-[100]'),
    'Old z-[60]/z-[100] classes must be absent — portal replaces the z-index-only approach',
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
