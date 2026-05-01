/**
 * Cards edit + Account identity/sign-out — renderer contract tests.
 *
 * Verifies:
 * 1. updateCard is exported from api.ts and targets PATCH /cards/{id}
 * 2. Cards page imports updateCard and Pencil (edit trigger)
 * 3. EditCardModal exists with points balance field
 * 4. Cards page does not hardcode sample email or user id
 * 5. Sidebar loads user identity from supabase.auth (not hardcoded)
 * 6. Sidebar contains sign-out action
 * 7. MobileNav drawer has sign-out action
 * 8. getUserDisplay prefers full_name → name → email prefix over raw id
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const apiTs = readFileSync(
  new URL('../src/lib/api.ts', import.meta.url),
  'utf8',
);

const cardsPage = readFileSync(
  new URL('../src/app/cards/page.tsx', import.meta.url),
  'utf8',
);

const sidebarTs = readFileSync(
  new URL('../src/components/layout/Sidebar.tsx', import.meta.url),
  'utf8',
);

const mobileNavTs = readFileSync(
  new URL('../src/components/layout/MobileNav.tsx', import.meta.url),
  'utf8',
);

// ── api.ts: updateCard ───────────────────────────────────────────────────────

test('api.ts exports updateCard function', () => {
  assert.match(apiTs, /export async function updateCard/);
});

test('updateCard uses PATCH method', () => {
  const after = apiTs.slice(apiTs.indexOf('export async function updateCard'));
  const chunk = after.slice(0, 300);
  assert.match(chunk, /method.*PATCH/);
});

test('updateCard targets /cards/{cardId} path', () => {
  const after = apiTs.slice(apiTs.indexOf('export async function updateCard'));
  const chunk = after.slice(0, 300);
  assert.match(chunk, /\/cards\/\$\{cardId\}/);
});

test('UpdateCardData interface has pointsBalance field', () => {
  assert.match(apiTs, /UpdateCardData/);
  const after = apiTs.slice(apiTs.indexOf('UpdateCardData'));
  const chunk = after.slice(0, 200);
  assert.match(chunk, /pointsBalance/);
});

// ── Cards page: edit UI ─────────────────────────────────────────────────────

test('cards page imports updateCard from api', () => {
  assert.match(cardsPage, /updateCard/);
});

test('cards page has EditCardModal component', () => {
  assert.match(cardsPage, /EditCardModal/);
});

test('EditCardModal has points balance field', () => {
  const after = cardsPage.slice(cardsPage.indexOf('EditCardModal'));
  const chunk = after.slice(0, 2000);
  assert.match(chunk, /pointsBalance|points-balance|Points balance/i);
});

test('cards page has edit trigger (Pencil icon or edit button)', () => {
  assert.match(cardsPage, /Pencil|edit.*card|Edit Card/i);
});

test('cards page does not show hardcoded sample email', () => {
  assert.doesNotMatch(cardsPage, /traveler@example\.com/);
});

// ── Sidebar: real user identity ─────────────────────────────────────────────

test('Sidebar does not hardcode traveler@example.com', () => {
  assert.doesNotMatch(sidebarTs, /traveler@example\.com/);
});

test('Sidebar does not hardcode "Traveler" as static display name', () => {
  // The literal "Traveler" should not appear as a static JSX string
  assert.doesNotMatch(sidebarTs, />\s*Traveler\s*</);
});

test('Sidebar calls supabase.auth.getUser or onAuthStateChange', () => {
  assert.match(sidebarTs, /supabase\.auth\.(getUser|onAuthStateChange)/);
});

test('Sidebar has getUserDisplay or equivalent user identity helper', () => {
  assert.match(sidebarTs, /getUserDisplay|user_metadata|user\.email/);
});

// ── Sidebar: sign out ────────────────────────────────────────────────────────

test('Sidebar has sign out action', () => {
  assert.match(sidebarTs, /[Ss]ign\s*[Oo]ut|signOut/);
});

test('Sidebar sign out calls supabase.auth.signOut', () => {
  assert.match(sidebarTs, /supabase\.auth\.signOut/);
});

test('Sidebar sign out routes to login after sign out', () => {
  assert.match(sidebarTs, /auth\/login/);
});

// ── MobileNav: sign out ──────────────────────────────────────────────────────

test('MobileNav drawer has sign out button', () => {
  assert.match(mobileNavTs, /[Ss]ign\s*[Oo]ut|signOut/);
});

test('MobileNav sign out calls supabase.auth.signOut', () => {
  assert.match(mobileNavTs, /supabase\.auth\.signOut/);
});

test('MobileNav shows user identity (not hardcoded sample id)', () => {
  assert.doesNotMatch(mobileNavTs, /traveler@example\.com/);
  assert.match(mobileNavTs, /user_metadata|getUserDisplay|user\.email/);
});

// ── getUserDisplay priority logic (Sidebar) ──────────────────────────────────

test('getUserDisplay prefers full_name from metadata', () => {
  assert.match(sidebarTs, /full_name/);
});

test('getUserDisplay falls back to email prefix when no name', () => {
  assert.match(sidebarTs, /split\(["']@["']\)|email\.split/);
});


// ── EditCardModal submit-time points validation ─────────────────────────────

test('edit submit rejects non-numeric/NaN points before updateCard', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  assert.match(chunk, /Number\.isFinite\(parsedPointsBalance\)/);
  assert.match(chunk, /setError\("Points balance must be a non-negative number\."\)/);
});

test('edit submit rejects negative points before updateCard', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  assert.match(chunk, /parsedPointsBalance\s*<\s*0/);
});

test('edit submit rejects blank points before updateCard', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  assert.match(chunk, /!rawPointsBalance/);
});

test('edit submit allows zero points balance', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  assert.match(chunk, /pointsBalance:\s*parsedPointsBalance/);
  assert.doesNotMatch(chunk, /parsedPointsBalance\s*\?\s*Number/);
});

test('edit submit allows positive points balance via parsed numeric payload', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  assert.match(chunk, /const parsedPointsBalance = Number\(rawPointsBalance\)/);
  assert.match(chunk, /updateCard\(card\.id,\s*\{/);
});

test('edit validation is submit-time logic, not only input attributes', () => {
  const after = cardsPage.slice(cardsPage.indexOf('function EditCardModal'));
  const chunk = after.slice(0, 4500);
  const submitGuardIndex = chunk.indexOf('Number.isFinite(parsedPointsBalance)');
  const updateCallIndex = chunk.indexOf('updateCard(card.id');
  assert.ok(submitGuardIndex >= 0 && updateCallIndex >= 0 && submitGuardIndex < updateCallIndex);
});
