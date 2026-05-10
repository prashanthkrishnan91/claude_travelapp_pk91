import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const recentTrips = readFileSync(new URL('../src/components/dashboard/RecentTrips.tsx', import.meta.url), 'utf8');
const tripsPage = readFileSync(new URL('../src/app/trips/page.tsx', import.meta.url), 'utf8');
const tripStatus = readFileSync(new URL('../src/lib/tripStatus.ts', import.meta.url), 'utf8');

test('tripStatus helper exports display and group helpers', () => {
  assert.match(tripStatus, /export function getDisplayTripStatus/);
  assert.match(tripStatus, /export function getTripStatusGroup/);
});

test('RecentTrips uses shared getDisplayTripStatus helper', () => {
  assert.match(recentTrips, /getDisplayTripStatus/);
  assert.match(recentTrips, /TripStatusBadge[^\n]*status=\{getDisplayTripStatus\(trip\)\}/);
});

test('/trips page groups by getTripStatusGroup and displays computed badge status', () => {
  assert.match(tripsPage, /getTripStatusGroup\(t\)/);
  assert.match(tripsPage, /TripStatusBadge status=\{getDisplayTripStatus\(trip\)\}/);
});
