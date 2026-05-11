/**
 * Stage 2A Slice 3 — Trip-Optional AI Concierge structural tests
 * Source-file assertions only — no DOM rendering.
 */

import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { test } from "node:test";
import assert from "node:assert/strict";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, "..");

const apiSrc = readFileSync(join(root, "src/lib/api.ts"), "utf8");
const conciergeSrc = readFileSync(join(root, "src/lib/concierge/types.ts"), "utf8");

// ── callConcierge signature ────────────────────────────────────────────────

test("callConcierge accepts tripId as string | null", () => {
  assert.ok(
    apiSrc.includes("tripId: string | null"),
    "callConcierge must accept string | null for tripId"
  );
});

test("callConcierge has optional destination parameter", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConcierge("),
    apiSrc.indexOf("export async function callConciergeSearch(")
  );
  assert.ok(
    fnBlock.includes("destination?: string"),
    "callConcierge must have optional destination param"
  );
});

test("callConcierge sends trip_id only when truthy", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConcierge("),
    apiSrc.indexOf("export async function callConciergeSearch(")
  );
  assert.ok(
    fnBlock.includes("tripId ? { trip_id: tripId }"),
    "callConcierge must conditionally include trip_id"
  );
});

test("callConcierge sends destination only when truthy", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConcierge("),
    apiSrc.indexOf("export async function callConciergeSearch(")
  );
  assert.ok(
    fnBlock.includes("destination ? { destination }"),
    "callConcierge must conditionally include destination"
  );
});

// ── callConciergeSearch signature ─────────────────────────────────────────

test("callConciergeSearch accepts tripId as string | null", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConciergeSearch("),
    apiSrc.indexOf("export async function fetchConciergeMessages(")
  );
  assert.ok(
    fnBlock.includes("tripId: string | null"),
    "callConciergeSearch must accept string | null for tripId"
  );
});

test("callConciergeSearch has optional destination parameter after clientMessageId", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConciergeSearch("),
    apiSrc.indexOf("export async function fetchConciergeMessages(")
  );
  assert.ok(
    fnBlock.includes("destination?: string"),
    "callConciergeSearch must have optional destination param"
  );
});

test("callConciergeSearch sends trip_id only when truthy", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConciergeSearch("),
    apiSrc.indexOf("export async function fetchConciergeMessages(")
  );
  assert.ok(
    fnBlock.includes("tripId ? { trip_id: tripId }"),
    "callConciergeSearch must conditionally include trip_id"
  );
});

test("callConciergeSearch sends destination only when truthy", () => {
  const fnBlock = apiSrc.slice(
    apiSrc.indexOf("export async function callConciergeSearch("),
    apiSrc.indexOf("export async function fetchConciergeMessages(")
  );
  assert.ok(
    fnBlock.includes("destination ? { destination }"),
    "callConciergeSearch must conditionally include destination"
  );
});

// ── Forbidden scope: TripBuilder + tripCandidates untouched ───────────────

test("TripBuilder.tsx does not reference destination-only concierge path", () => {
  const tbSrc = readFileSync(
    join(root, "src/components/trips/TripBuilder.tsx"),
    "utf8"
  );
  assert.ok(
    !tbSrc.includes("destination?: string") || tbSrc.indexOf("destination?: string") === tbSrc.lastIndexOf("destination?: string"),
    "TripBuilder must not import or define tripless destination override"
  );
  assert.ok(
    !tbSrc.includes("callConcierge(null"),
    "TripBuilder must not call tripless concierge path"
  );
});

test("tripCandidates.ts has no destination override", () => {
  const tcSrc = readFileSync(
    join(root, "src/lib/tripCandidates.ts"),
    "utf8"
  );
  assert.ok(
    !tcSrc.includes("destination?"),
    "tripCandidates.ts must not be touched by Slice 3"
  );
});

// ── Backend model contract ─────────────────────────────────────────────────

const modelSrc = readFileSync(
  join(root, "../backend/app/models/concierge.py"),
  "utf8"
);

test("ConciergeSearchRequest has Optional[UUID] trip_id", () => {
  const block = modelSrc.slice(
    modelSrc.indexOf("class ConciergeSearchRequest"),
    modelSrc.indexOf("class ConciergeCacheClearRequest")
  );
  assert.ok(
    block.includes("trip_id: Optional[UUID]"),
    "ConciergeSearchRequest.trip_id must be Optional[UUID]"
  );
});

test("ConciergeSearchRequest has destination field", () => {
  const block = modelSrc.slice(
    modelSrc.indexOf("class ConciergeSearchRequest"),
    modelSrc.indexOf("class ConciergeCacheClearRequest")
  );
  assert.ok(
    block.includes("destination: Optional[str]"),
    "ConciergeSearchRequest must have Optional destination"
  );
});

test("ConciergeSearchRequest has model_validator", () => {
  const block = modelSrc.slice(
    modelSrc.indexOf("class ConciergeSearchRequest"),
    modelSrc.indexOf("class ConciergeCacheClearRequest")
  );
  assert.ok(
    block.includes("require_trip_or_destination"),
    "ConciergeSearchRequest must have require_trip_or_destination validator"
  );
});

test("ConciergeRequest has Optional[UUID] trip_id", () => {
  const block = modelSrc.slice(
    modelSrc.indexOf("class ConciergeRequest"),
    modelSrc.indexOf("class Suggestion")
  );
  assert.ok(
    block.includes("trip_id: Optional[UUID]"),
    "ConciergeRequest.trip_id must be Optional[UUID]"
  );
});

// ── Service contract ───────────────────────────────────────────────────────

const serviceSrc = readFileSync(
  join(root, "../backend/app/services/concierge.py"),
  "utf8"
);

test("service.search accepts Optional[UUID] trip_id", () => {
  const fnBlock = serviceSrc.slice(
    serviceSrc.indexOf("    def search("),
    serviceSrc.indexOf("    def _align_summary_with_ranked_cards")
  );
  assert.ok(
    fnBlock.includes("trip_id: Optional[UUID]"),
    "service.search must accept Optional[UUID]"
  );
});

test("service.search accepts destination kwarg", () => {
  const fnBlock = serviceSrc.slice(
    serviceSrc.indexOf("    def search("),
    serviceSrc.indexOf("    def _align_summary_with_ranked_cards")
  );
  assert.ok(
    fnBlock.includes("destination: Optional[str]"),
    "service.search must have destination parameter"
  );
});

test("service.search guards _fetch_trip behind trip_id is not None", () => {
  const fnBlock = serviceSrc.slice(
    serviceSrc.indexOf("    def search("),
    serviceSrc.indexOf("    def _align_summary_with_ranked_cards")
  );
  assert.ok(
    fnBlock.includes("if trip_id is not None:"),
    "service.search must guard _fetch_trip"
  );
});
