// Dashboard past-trip computed display status — source-content contract tests.
//
// Guards that:
//   1. RecentTrips.tsx defines a getDisplayStatus function.
//   2. getDisplayStatus returns "completed" for past trips with planning statuses.
//   3. getDisplayStatus does NOT mutate stored status for future/active trips.
//   4. TripStatusBadge is called with getDisplayStatus(trip) not raw trip.status.
//   5. DashboardClient.tsx isUpcoming guard correctly excludes past trips from count.

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const recentTrips = readFileSync(
  new URL('../src/components/dashboard/RecentTrips.tsx', import.meta.url),
  'utf8',
);
const dashboardClient = readFileSync(
  new URL('../src/components/dashboard/DashboardClient.tsx', import.meta.url),
  'utf8',
);

// ── RecentTrips contract ──────────────────────────────────────────────────────

test('RecentTrips: defines getDisplayStatus function', () => {
  assert.match(
    recentTrips,
    /function getDisplayStatus\b/,
    'Expected getDisplayStatus to be defined in RecentTrips.tsx',
  );
});

test('RecentTrips: getDisplayStatus returns "completed" for past trips', () => {
  assert.match(
    recentTrips,
    /return "completed"/,
    'getDisplayStatus must return "completed" for trips whose endDate is in the past',
  );
});

test('RecentTrips: checks endDate < TODAY to determine past trips', () => {
  assert.match(
    recentTrips,
    /endDate.*<.*_TODAY|_TODAY.*endDate/,
    'getDisplayStatus must compare trip.endDate against TODAY',
  );
});

test('RecentTrips: only overrides planning-state statuses (not completed/archived)', () => {
  // The set of statuses that get overridden must not include "completed" or "archived"
  assert.match(
    recentTrips,
    /_PLANNING_STATUSES/,
    'Expected a _PLANNING_STATUSES guard to avoid overriding already-terminal statuses',
  );
  assert.doesNotMatch(
    recentTrips,
    /_PLANNING_STATUSES.*completed|completed.*_PLANNING_STATUSES/,
    '"completed" must not be in _PLANNING_STATUSES (it should stay as-is)',
  );
});

test('RecentTrips: TripStatusBadge receives getDisplayStatus(trip) not raw trip.status', () => {
  assert.match(
    recentTrips,
    /TripStatusBadge[^/]*status=\{getDisplayStatus\(trip\)\}/,
    'TripStatusBadge must be passed getDisplayStatus(trip) not trip.status',
  );
});

test('RecentTrips: does not mutate stored trip.status', () => {
  // Should not contain trip.status = or similar mutation patterns
  assert.doesNotMatch(
    recentTrips,
    /trip\.status\s*=/,
    'getDisplayStatus must compute display status without mutating stored trip.status',
  );
});

// ── DashboardClient contract ──────────────────────────────────────────────────

test('DashboardClient: isUpcoming filters out past trips by startDate', () => {
  assert.match(
    dashboardClient,
    /startDate.*>=.*TODAY|TODAY.*startDate/,
    'isUpcoming must exclude trips whose startDate is before today',
  );
});

test('DashboardClient: isUpcoming uses a date comparison not mutation', () => {
  assert.doesNotMatch(
    dashboardClient,
    /trip\.status\s*=.*completed/,
    'Dashboard must not mutate trip.status to "completed"',
  );
});
