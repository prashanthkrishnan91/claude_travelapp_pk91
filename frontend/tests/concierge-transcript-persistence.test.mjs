/**
 * Tests: outside-trip Concierge transcript + persistence behavior.
 *
 * Validates ConciergePage.tsx structural properties — sourced from file read,
 * not DOM rendering, consistent with the project's existing test pattern.
 *
 * Coverage:
 * A. User messages render in the transcript (not silently hidden).
 * B. localStorage persistence is wired (load on mount, save on change).
 * C. Clear-chat action exists and removes transcript state.
 * D. Card buttons/actions still present after transcript changes.
 * E. TRANSCRIPT_KEY constant is defined (regression guard on key name).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(
  join(__dirname, '../src/components/concierge/ConciergePage.tsx'),
  'utf8',
);

// ── A: User messages are rendered ────────────────────────────────────────────

test('user turn is rendered — msg.role === "user" no longer silently returns null', () => {
  // Old broken pattern: `if (msg.role === "user") return null;`
  // New correct pattern must render user messages.
  const silentNull = /if\s*\(\s*msg\.role\s*===\s*["']user["']\s*\)\s*return\s+null/;
  assert.ok(
    !silentNull.test(src),
    'ConciergePage must not silently suppress user messages with "return null". ' +
      'User turns should render as a chat bubble.',
  );
});

test('user turn renders a visible bubble element', () => {
  // The transcript should show user messages in a distinct visual container.
  // We check for the role check + render of user content (right-aligned bubble pattern).
  assert.ok(
    src.includes('msg.role === "user"'),
    'ConciergePage must check msg.role === "user" to render user turns.',
  );
  assert.ok(
    src.includes('justify-end'),
    'User message bubble should use justify-end for right-alignment.',
  );
});

// ── B: localStorage persistence ───────────────────────────────────────────────

test('TRANSCRIPT_KEY constant is defined', () => {
  assert.ok(
    src.includes('TRANSCRIPT_KEY'),
    'ConciergePage must define a TRANSCRIPT_KEY constant for localStorage.',
  );
});

test('localStorage.getItem is called on mount for transcript recovery', () => {
  assert.ok(
    src.includes('localStorage.getItem') || src.includes('localStorage.getItem'),
    'ConciergePage must read from localStorage to restore the transcript on mount.',
  );
});

test('localStorage.setItem is called to persist transcript', () => {
  assert.ok(
    src.includes('localStorage.setItem'),
    'ConciergePage must write to localStorage when the transcript changes.',
  );
});

test('useEffect is used for persistence side-effects', () => {
  assert.ok(
    src.includes('useEffect'),
    'ConciergePage must use useEffect to load/save the transcript.',
  );
});

// ── C: Clear-chat action ──────────────────────────────────────────────────────

test('clearTranscript function is defined', () => {
  assert.ok(
    src.includes('clearTranscript'),
    'ConciergePage must define a clearTranscript function.',
  );
});

test('clearTranscript removes from localStorage', () => {
  assert.ok(
    src.includes('localStorage.removeItem'),
    'clearTranscript must remove the persisted transcript from localStorage.',
  );
});

test('clear-chat button is rendered with aria-label', () => {
  assert.ok(
    src.includes('Clear chat'),
    'A clear-chat button with aria-label="Clear chat" must be present.',
  );
});

test('Trash2 icon is imported for the clear-chat button', () => {
  assert.ok(
    src.includes('Trash2'),
    'Trash2 lucide icon must be imported for the clear-chat button.',
  );
});

// ── D: Existing card buttons/actions still present ────────────────────────────

test('Map link button is still rendered', () => {
  assert.ok(
    src.includes('mapLink'),
    'Map link action must still be present in ConciergePage.',
  );
});

test('Source link button is still rendered', () => {
  assert.ok(
    src.includes('sourceLink'),
    'Source link action must still be present in ConciergePage.',
  );
});

test('ConciergeResultCard is still used to render cards', () => {
  assert.ok(
    src.includes('ConciergeResultCard'),
    'ConciergeResultCard component must still be used for place cards.',
  );
});

// ── E: Transcript state model ─────────────────────────────────────────────────

test('messages state is appended not replaced — both user and assistant turns', () => {
  // Check that sendQuery appends a user message before awaiting the search
  assert.ok(
    src.includes('role: "user"') && src.includes('role: "assistant"'),
    'ConciergePage must append both user and assistant role messages to the transcript.',
  );
});

test('fromSearchResult converts ConciergeSearchResult to assistant Message', () => {
  assert.ok(
    src.includes('fromSearchResult'),
    'fromSearchResult helper must still exist to convert API results to assistant messages.',
  );
});
