/**
 * Saved Notes v1 — persisted user notes for saved items.
 *
 * Tests:
 * A. SavedItem type has note field
 * B. updateSavedItemNote API helper exported
 * C. Backend migration 007 adds note column
 * D. Backend model SavedItemNoteUpdate exported; routes PATCH /{id}/note
 * E. NoteEditor component in SavedShell (view / edit / clear)
 * F. Compare sheet: Your note vs Saved context separated
 * G. Existing SavedShell actions preserved (no regression)
 * H. Note CSS primitives in globals
 * I. No fake/invented note data
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");

function read(rel) {
  return readFileSync(path.join(root, rel), "utf8");
}

const typesIndex = read("src/types/index.ts");
const apiTs = read("src/lib/api.ts");
const savedShell = read("src/components/saved/SavedShell.tsx");
const globals = read("src/app/globals.css");
const migration007 = read("../backend/db/migrations/007_saved_items_note.sql");
const savedItemsModel = read("../backend/app/models/saved_items.py");
const savedItemsService = read("../backend/app/services/saved_items.py");
const savedItemsRoute = read("../backend/app/routes/saved_items.py");

// ── A. Type system ────────────────────────────────────────────────────────────

test("SavedItem interface has note field (nullable)", () => {
  const block = typesIndex.slice(typesIndex.indexOf("export interface SavedItem"));
  assert.ok(
    block.includes("note?") || block.includes("note:"),
    "SavedItem must have a note field"
  );
});

test("SavedItem note field allows null/undefined (optional or nullable)", () => {
  const block = typesIndex.slice(typesIndex.indexOf("export interface SavedItem"));
  const noteMatch =
    block.includes("note?: string | null") ||
    block.includes("note?: string") ||
    block.includes("note: string | null | undefined");
  assert.ok(noteMatch, "note must be optional or nullable");
});

// ── B. Frontend API helper ────────────────────────────────────────────────────

test("updateSavedItemNote is exported from api.ts", () => {
  assert.ok(
    apiTs.includes("export async function updateSavedItemNote"),
    "updateSavedItemNote must be exported"
  );
});

test("updateSavedItemNote PATCHes /saved-items/{itemId}/note", () => {
  assert.match(apiTs, /\/saved-items\/\$\{itemId\}\/note/);
  assert.match(apiTs, /method:\s*"PATCH"/);
});

test("updateSavedItemNote sends note in body", () => {
  const block = apiTs.slice(apiTs.indexOf("updateSavedItemNote"));
  assert.ok(block.includes("note"), "body must include note");
  assert.ok(block.includes("JSON.stringify"), "body must be JSON");
});

// ── C. Backend migration ──────────────────────────────────────────────────────

test("migration 007 adds note column to saved_items", () => {
  assert.ok(migration007.includes("note"), "migration must add note column");
  assert.ok(migration007.includes("saved_items"), "migration must target saved_items");
  // Non-destructive: no DROP or destructive ALTER
  assert.ok(!migration007.includes("DROP COLUMN"), "no DROP COLUMN in migration");
});

test("migration 007 uses IF NOT EXISTS (safe re-run)", () => {
  assert.ok(
    migration007.includes("if not exists") || migration007.includes("IF NOT EXISTS"),
    "migration must use IF NOT EXISTS for safety"
  );
});

// ── D. Backend model + service + route ───────────────────────────────────────

test("SavedItemNoteUpdate model exists in models/saved_items.py", () => {
  assert.ok(
    savedItemsModel.includes("SavedItemNoteUpdate"),
    "SavedItemNoteUpdate model must be defined"
  );
});

test("SavedItem model has note field (Optional[str])", () => {
  assert.match(savedItemsModel, /note:\s*Optional\[str\]/);
});

test("SavedItemNoteUpdate trims whitespace (validator)", () => {
  assert.ok(
    savedItemsModel.includes("trim_note") || savedItemsModel.includes("strip()"),
    "note must be trimmed"
  );
});

test("SavedItemsService has update_note method", () => {
  assert.ok(savedItemsService.includes("def update_note"), "update_note method must exist");
});

test("update_note calls _ensure_owned (ownership check)", () => {
  const block = savedItemsService.slice(savedItemsService.indexOf("def update_note"));
  assert.ok(block.includes("_ensure_owned"), "update_note must check ownership");
});

test("PATCH /{item_id}/note route is defined in routes", () => {
  assert.match(savedItemsRoute, /router\.patch\(.*\/note/);
});

test("note PATCH route uses SavedItemNoteUpdate payload", () => {
  assert.ok(savedItemsRoute.includes("SavedItemNoteUpdate"), "route must import/use SavedItemNoteUpdate");
});

test("note PATCH route returns SavedItem (response_model)", () => {
  const block = savedItemsRoute.slice(savedItemsRoute.indexOf("patch"));
  assert.ok(block.includes("SavedItem"), "PATCH route must return SavedItem");
});

// ── E. NoteEditor UI in SavedShell ───────────────────────────────────────────

test("NoteEditor component is defined in SavedShell", () => {
  assert.ok(savedShell.includes("function NoteEditor"), "NoteEditor component must exist");
});

test("NoteEditor shows Your note label when note exists", () => {
  assert.ok(savedShell.includes("Your note"), "must show 'Your note' label");
});

test("NoteEditor shows Add note affordance when no note", () => {
  assert.ok(
    savedShell.includes("Add note") || savedShell.includes("+ Add note"),
    "must show Add note link"
  );
});

test("NoteEditor has save and cancel buttons", () => {
  assert.ok(savedShell.includes('data-testid="note-save-btn"'), "must have save button");
  assert.ok(savedShell.includes('data-testid="note-cancel-btn"'), "must have cancel button");
});

test("NoteEditor has a textarea for editing", () => {
  assert.ok(savedShell.includes('data-testid="note-textarea"'), "must have textarea");
});

test("NoteEditor calls updateSavedItemNote on save", () => {
  assert.ok(savedShell.includes("updateSavedItemNote"), "must call updateSavedItemNote");
});

test("NoteEditor is imported/used in PlaceDossierCard", () => {
  const block = savedShell.slice(savedShell.indexOf("function PlaceDossierCard"));
  assert.ok(block.includes("NoteEditor"), "PlaceDossierCard must render NoteEditor");
});

test("NoteEditor is imported/used in FlightCard", () => {
  const block = savedShell.slice(savedShell.indexOf("function FlightCard"));
  assert.ok(block.includes("NoteEditor"), "FlightCard must render NoteEditor");
});

test("NoteEditor clears note when empty string saved (clear path)", () => {
  const noteEditorBlock = savedShell.slice(
    savedShell.indexOf("function NoteEditor"),
    savedShell.indexOf("function PlanningBridge")
  );
  assert.ok(
    noteEditorBlock.includes("null") || noteEditorBlock.includes("|| null"),
    "empty save should clear note to null"
  );
});

test("NoteEditor shows error state on save failure", () => {
  assert.ok(savedShell.includes('data-testid="note-save-error"'), "must show save error");
});

test("NoteEditor edit button testid present", () => {
  assert.ok(savedShell.includes('data-testid="note-edit-btn"'), "must have note-edit-btn");
});

test("NoteEditor add button testid present", () => {
  assert.ok(savedShell.includes('data-testid="note-add-btn"'), "must have note-add-btn");
});

test("NoteEditor view container testid present", () => {
  assert.ok(savedShell.includes('data-testid="note-view"'), "must have note-view testid");
});

test("NoteEditor editor container testid present", () => {
  assert.ok(savedShell.includes('data-testid="note-editor"'), "must have note-editor testid");
});

test("onNoteUpdate callback propagated through SavedItemCard", () => {
  const block = savedShell.slice(savedShell.indexOf("function SavedItemCard"));
  assert.ok(block.includes("onNoteUpdate"), "SavedItemCard must pass onNoteUpdate");
});

test("handleNoteUpdate updates items state in SavedShell", () => {
  const block = savedShell.slice(savedShell.indexOf("export function SavedShell"));
  assert.ok(block.includes("handleNoteUpdate"), "SavedShell must define handleNoteUpdate");
  assert.ok(block.includes("setItems"), "handleNoteUpdate must call setItems");
});

// ── F. Compare sheet: Your note vs Saved context ─────────────────────────────

test("compare sheet shows Your note row with testid compare-your-note", () => {
  assert.ok(
    savedShell.includes('data-testid="compare-your-note"'),
    "compare sheet must have compare-your-note row"
  );
});

test("compare sheet labels note row as Your note (not Saved context)", () => {
  const compareBlock = savedShell.slice(savedShell.indexOf("function CompareSheet"));
  assert.ok(
    compareBlock.includes("Your note"),
    "compare sheet Your note label must be present"
  );
});

test("compare sheet keeps Saved context as a separate row", () => {
  const compareBlock = savedShell.slice(savedShell.indexOf("function CompareSheet"));
  assert.ok(
    compareBlock.includes("Saved context"),
    "compare sheet must still show Saved context row"
  );
});

test("Your note and Saved context use different testids in compare", () => {
  assert.ok(
    savedShell.includes('data-testid="compare-your-note"'),
    "Your note must have its own testid"
  );
  assert.ok(
    savedShell.includes('data-testid="compare-note"'),
    "Saved context must keep its own testid"
  );
  // The two must be separate nodes (not conflated)
  assert.notEqual(
    savedShell.indexOf('data-testid="compare-your-note"'),
    savedShell.indexOf('data-testid="compare-note"'),
    "must be different elements"
  );
});

test("compare sheet Your note row is conditional (omitted when no note)", () => {
  const compareBlock = savedShell.slice(savedShell.indexOf("function CompareSheet"));
  // Must be inside a conditional — look for {userNote && ( or similar
  assert.match(compareBlock, /userNote && \(/);
});

test("compare sheet Saved context row is conditional (unchanged logic)", () => {
  const compareBlock = savedShell.slice(savedShell.indexOf("function CompareSheet"));
  assert.match(compareBlock, /savedQuery && \(/);
});

// ── G. Existing actions preserved (regression guard) ─────────────────────────

test("listSavedItems still imported", () => {
  assert.ok(savedShell.includes("listSavedItems"), "listSavedItems must remain imported");
});

test("deleteSavedItem still imported", () => {
  assert.ok(savedShell.includes("deleteSavedItem"), "deleteSavedItem must remain imported");
});

test("addSavedItemToTrip still imported", () => {
  assert.ok(savedShell.includes("addSavedItemToTrip"), "addSavedItemToTrip must remain imported");
});

test("compare tray still present and capped at COMPARE_MAX=4", () => {
  assert.ok(savedShell.includes("COMPARE_MAX = 4"), "compare cap must remain 4");
  assert.ok(savedShell.includes("folio-compare-tray"), "compare tray must remain");
});

test("compare sheet place-only invariant preserved", () => {
  assert.match(savedShell, /PLACE_VERTICALS[\s\S]*"restaurant", "attraction", "hotel"/);
});

test("remove saved btn testid preserved", () => {
  assert.ok(savedShell.includes('data-testid="remove-saved-btn"'), "remove button must remain");
});

test("add-to-trip testids preserved", () => {
  assert.ok(savedShell.includes('data-testid="add-to-trip-btn"'), "add-to-trip-btn preserved");
  assert.ok(savedShell.includes('data-testid="create-trip-btn"'), "create-trip-btn preserved");
});

test("flight route band testid preserved", () => {
  assert.ok(savedShell.includes('data-testid="flight-route-band"'), "flight-route-band preserved");
});

// ── H. CSS primitives ─────────────────────────────────────────────────────────

test("globals.css defines folio-note-view", () => {
  assert.ok(globals.includes(".folio-note-view"), ".folio-note-view must be defined");
});

test("globals.css defines folio-note-editor", () => {
  assert.ok(globals.includes(".folio-note-editor"), ".folio-note-editor must be defined");
});

test("globals.css defines folio-note-textarea", () => {
  assert.ok(globals.includes(".folio-note-textarea"), ".folio-note-textarea must be defined");
});

test("globals.css defines folio-note-label", () => {
  assert.ok(globals.includes(".folio-note-label"), ".folio-note-label must be defined");
});

test("globals.css defines folio-note-text", () => {
  assert.ok(globals.includes(".folio-note-text"), ".folio-note-text must be defined");
});

test("globals.css note primitives use design tokens (no raw hex)", () => {
  const start = globals.indexOf(".folio-note-view");
  const end = globals.indexOf(".folio-compare-your-note");
  const section = globals.slice(start, end);
  assert.doesNotMatch(
    section,
    /#[0-9a-fA-F]{3,6}\b/,
    "note CSS must use ds-* tokens, no raw hex"
  );
});

test("globals.css defines folio-compare-your-note for compare sheet", () => {
  assert.ok(
    globals.includes(".folio-compare-your-note"),
    "must define compare your-note variant"
  );
});

test("reduced-motion block covers note editor transitions", () => {
  const rmBlock = globals.slice(globals.lastIndexOf("prefers-reduced-motion"));
  assert.ok(
    rmBlock.includes("folio-note") || globals.includes("folio-note-add-link"),
    "reduced-motion must cover note editor or note links"
  );
});

// ── I. No fake/invented notes ─────────────────────────────────────────────────

test("NoteEditor does not pre-populate with fabricated note content", () => {
  const noteEditorBlock = savedShell.slice(
    savedShell.indexOf("function NoteEditor"),
    savedShell.indexOf("function PlanningBridge")
  );
  // The initial draft must come from the passed prop (initialNote / note), not a hardcoded string.
  // Placeholders are allowed; the draft state must use the prop.
  assert.match(
    noteEditorBlock,
    /useState\(note.*\)|useState\(initialNote/,
    "draft state must be initialized from the note prop"
  );
  // The draft textarea value must reference the state, not a literal.
  assert.ok(
    noteEditorBlock.includes("value={draft}"),
    "textarea value must be the draft state variable"
  );
});

test("compare sheet Your note renders item.note, not whyItMattered/searchContext.query", () => {
  const compareBlock = savedShell.slice(savedShell.indexOf("function CompareSheet"));
  // userNote must be assigned from it.note
  assert.match(
    compareBlock,
    /userNote\s*=\s*it\.note/,
    "userNote must come from it.note"
  );
  // The Your note row and the conditional block both reference userNote in the compare body
  assert.ok(
    compareBlock.includes("compare-your-note") && compareBlock.includes("userNote"),
    "Your note row must render userNote in compare sheet"
  );
  // savedQuery (whyItMattered result) must NOT be used for the Your note row
  // (it is a separate Saved context row)
  const yourNoteIdx = compareBlock.indexOf("compare-your-note");
  const savedCtxIdx = compareBlock.indexOf('"compare-note"');
  assert.ok(yourNoteIdx < savedCtxIdx, "Your note row must appear before Saved context row");
});
