# Concierge Salon — Production Implementation Blueprint (for Sonnet)

**Status:** Implementation blueprint · ready for one PR from `main`
**Source concept (approved):** `docs/ai/concepts/concierge-salon-concept-v1.html`
**Target file (primary):** `frontend/src/components/concierge/ConciergePage.tsx`
**Target file (CSS):** `frontend/src/app/globals.css` (ATELIER ROOM SYSTEM section, ~line 6976+)
**Route:** `/concierge` (outside-trip Concierge only). The in-trip `AIConciergePanel.tsx` is **out of scope**.

This blueprint exists because a prior Sonnet attempt (PR #455) copied the concept's *ingredients* but missed its *spatial composition*: it produced a heavy dark slab, pre-search vertical scrolling, a buried/muddy portal, and a form-like composer. Everything below is written to make those outcomes structurally impossible. Read it fully before writing code. Do not freelance the layout — the constraints in §3 and the forbidden outcomes in §8 are the contract.

---

## 1. Production target summary

**The intended experience.** The outside-trip Concierge is a *private travel salon* — one cinematic room inside the Atelier world, not a chat box on paper. Opening `/concierge` reveals, immediately and without scrolling, a **portal**: a layered destination "window" that suggests mood and possibility before the user types anything. A **concierge desk** (destination + query + submit) is fused to the base of the portal as a single integrated instrument. A small set of **invitations** (prompt starters) live *inside* the stage as editorial entry points. To the right, a **dossier rail** explains what the concierge can do as a tactile briefing object. When the user searches, the portal **tunes** toward the typed destination (using the existing world-DNA pipeline — real, not faked), and a **curated shortlist of verified result cards** reveals in place of the empty stage. Saving a card gives a quiet folio-style acknowledgement. The room is warm, dark-but-not-black, readable, and emotionally transportive.

**What must NOT happen.** This is not a light "paper page with widgets," and it is not a black void. It must not become a giant flat dark slab; the portal must never sit below the fold or behind a muddy unreadable wash; the desk must never overlay the portal or read as a detached form block; pre-search must never introduce an internal scrollbar or page scroll at a normal laptop height; the dossier rail must never dominate the stage; and there must be no excessive header/intro copy pushing the portal down. No fake places, counts, prices, images, or demo "mood logic." No regression to search, refinement, transcript, save, maps, or destination behavior.

---

## 2. Exact component / DOM hierarchy (target)

Restructure `ConciergePage.tsx`'s returned JSX to the hierarchy below. Names in `()` are the controlling CSS class; `[testid]` marks a `data-testid` that must exist. Keep the existing React state and handlers (see §5/§6) — this is a **layout restructure**, not a logic rewrite.

```
<div [concierge-page] class="atelier-salon-page atelier-salon-room atelier-salon-stage-room"   ← outer room shell
     style={worldStyleVars(salonWorld)} data-world-location data-scenery-tone>
  <WorldAtmosphere />                                         ← ambient drift layer (z-index:-1), reused as-is

  <div class="atelier-salon-workbench mx-auto">              ← 2-col grid on desktop: 1fr / dossier
    │
    ├── <div class="atelier-salon-main-panel atelier-salon-stage-panel">   ← the salon stage (flex column, 100svh-bounded)
    │     │
    │     ├── <section class="atelier-salon-portal"           ← THE PORTAL — emotional centerpiece
    │     │            data-portal-state={mode}>              ← mode: "open" (pre-search) | "tuned" (post-search)
    │     │      ├── <WorldScenery /> or .atelier-salon-portal-scene   ← painted destination scenery (tunes)
    │     │      ├── <span class="atelier-salon-portal-haze" aria-hidden> ← depth: soft atmospheric blur
    │     │      ├── <span class="atelier-salon-portal-bloom" aria-hidden>← depth: horizon light bloom
    │     │      ├── <span class="atelier-salon-portal-grain" aria-hidden>← depth: fine grain
    │     │      ├── <span class="atelier-salon-portal-vignette" aria-hidden>← depth: legibility vignette
    │     │      └── <div class="atelier-salon-portal-copy">  ← all readable content sits ABOVE the depth layers
    │     │            ├── <header [concierge-instrument-header]
    │     │            │            class="atelier-salon-room-header atelier-salon-panel-header">
    │     │            │       eyebrow ("Private Travel Concierge")
    │     │            │       <h1>  {lastQuery ? `"${lastQuery}"` : "What can I find for you?"}  </h1>
    │     │            │       (pre-search only) one short mood sub-line — max 2 lines
    │     │            └── (pre-search only) invitations block:
    │     │                  <div [concierge-empty-state] class="atelier-salon-invitation">
    │     │                    <div class="atelier-salon-chip-grid">
    │     │                      EDITORIAL_PROMPTS.map → <button [concierge-prompt-chip]
    │     │                              class="atelier-salon-starter-chip folio-concierge-chip"> …
    │     │
    │     ├── <main [concierge-results-canvas] class="atelier-salon-panel-body">  ← results reveal / transcript
    │     │      (renders ONLY transcript messages, loading, error, bottomRef;
    │     │       empty-state invitations now live in the portal, NOT here)
    │     │      • transcript: [concierge-user-query], [concierge-result-section] → ConciergeResultCard(s)
    │     │      • [concierge-loading-state]   • [concierge-error-state]   • <div ref={bottomRef}/>
    │     │
    │     └── <div [concierge-instrument-composer]              ← THE DESK — fused to portal/stage base
    │              class="atelier-salon-desk folio-cinema-composer atelier-salon-composer-surface">
    │            • (post-search) refinement/follow-up chips row
    │            • [concierge-destination-field]  → label "Where" + MapPin + destination <input>
    │            • input row: [concierge-clear-chat] (conditional) + <textarea [concierge-query-input]>
    │                          + submit <button [concierge-submit-button]>
    │
    └── <aside class="atelier-salon-briefing-rail">            ← THE DOSSIER — desktop-only tactile briefing
          • header "How I can help"  • capability list (no counts)  • footer verified badges
```

**Belonging rules (explicit):**
- The portal's depth layers (`scene/haze/bloom/grain/vignette`) are siblings *inside* `.atelier-salon-portal` and sit *below* `.atelier-salon-portal-copy` in z-order. All text is inside `.atelier-salon-portal-copy`.
- The header (`concierge-instrument-header`) and the pre-search invitations live **inside the portal copy**, not as separate stacked blocks above/below the portal. This is the single most important composition change vs. PR #455.
- The desk (`concierge-instrument-composer`) is a **flex-flow sibling directly after** the portal+canvas, pinned at the panel base. It is never `position: absolute` over the portal.
- The results canvas (`concierge-results-canvas`) is the **only** scrollable region, and only has content post-search.
- The dossier is a grid sibling of the panel, never inside it.

---

## 3. Layout rules with concrete constraints

These are hard numeric constraints. Implement them in CSS; do not approximate.

**Desktop (≥900px):**
- The room must fit the viewport. `.atelier-salon-main-panel` keeps `height: calc(100svh - var(--ds-space-10))` and `overflow: hidden` (already present). The panel is a flex column.
- **Pre-search must fit above the fold with zero scroll** (no internal scrollbar, no page scroll) at standard heights (test at 800px and 900px viewport height). Composition: portal `flex: 1 1 auto` (grows to fill), results canvas `flex: 0 0 auto` and **empty/zero-height pre-search**, desk `flex: 0 0 auto` pinned at base.
- Portal must be **visible immediately** on load — it is the first and largest element in the stage. Minimum portal height pre-search: `min-height: clamp(320px, 42vh, 460px)` but allow it to grow via `flex: 1` to consume leftover space so the desk lands at the panel base.
- **Post-search**: set portal to `data-portal-state="tuned"` → collapse to a banner via `flex: 0 0 auto; height: clamp(132px, 18vh, 200px)`. Results canvas becomes `flex: 1 1 auto; overflow-y: auto; min-height: 0` and is the only scroller. Desk stays pinned at base.
- The desk is **attached to the portal/stage**, not floating: the composer sits flush at the panel base with its existing top brass hairline (`.atelier-salon-composer-surface::before`) acting as the join. No large gap (`> var(--ds-space-4)`) between portal base (pre-search) / canvas (post-search) and the desk.
- Dossier rail aligns to stage height: it already uses `position: sticky; top: var(--ds-space-5)`. Constrain it so it reads as secondary — `width: 17rem` (existing grid `1fr 17rem`), and give it `max-height: calc(100svh - var(--ds-space-10))` with internal `overflow-y: auto` if its content would exceed the stage. It must visually balance, not dominate.
- The dark cinematic surface must read as a **room**: warm-dark (umber-tinted, e.g. `--ds-midnight-ink`/velvet range from the concept), framed with a soft brass hairline border and rounded corners (`border-radius: 16px`), with the layered portal providing depth. It must not be a single flat rectangle of one solid dark color edge-to-edge.

**Mobile (<900px):**
- Portal-first and compact. Single column. The portal is the top element and fills most of the first screen: `min-height: clamp(300px, 52vh, 420px)`.
- Pre-search: portal + 1–2 invitations + the desk, with the desk thumb-reachable near the bottom. Avoid pushing the desk off-screen; keep the pre-search column within ~100svh (a small amount of scroll on short phones is acceptable, but the portal and desk must both be reachable without hunting).
- Post-search: portal collapses to a short tuned banner (`height: clamp(120px, 22vh, 168px)`), results scroll beneath it, desk pinned/sticky at the bottom (`concierge-sticky-bottom` already does this — preserve it).
- Tap targets ≥44px (existing inputs/buttons already use `min-height: 44px` — preserve).

---

## 4. CSS architecture blueprint

**Reuse (do not reinvent):**
- `WorldAtmosphere`, `WorldScenery`, `WorldMist` from `components/ui/World.tsx`. The portal scene/atmosphere should be built from `WorldScenery` (painted destination scenery) + `WorldAtmosphere`, both already wired to `--world-*` vars.
- `worldStyleVars(salonWorld)`, `applyRoom`, `pickWorldFromDestination`, `roomSceneryFor` from `lib/worldData.ts`. These already inject `--world-ink`, `--world-ink-mist`, `--world-surface`, `--world-accent` and provide the salon archetype scenery. **This is the real mood-tuning engine.**
- Existing salon primitives that must remain (pinned by tests): `.atelier-salon-room`, `.atelier-salon-room-header` (+`::before`), `.atelier-salon-starter-chip` (+ reduced-motion guard), `.atelier-salon-invitation`, `.atelier-salon-composer-surface`, `.atelier-salon-user-turn`, `.atelier-salon-chip-grid`, `.atelier-salon-workbench`, `.atelier-salon-main-panel`, `.atelier-salon-panel-header`, `.atelier-salon-panel-body`, `.atelier-salon-briefing-rail` (+ header/item/footer), `folio-cinema-desk`, `folio-cinema-composer`, `folio-concierge-chip`.

**New classes to add (ATELIER ROOM SYSTEM section of `globals.css`):**
- `.atelier-salon-stage-panel` — variant of the main panel that hosts the portal+canvas+desk as a flex column (the portal-grow / canvas-scroll behavior from §3).
- `.atelier-salon-portal` — the portal frame: `position: relative; isolation: isolate; overflow: hidden; border-radius: 14px;` brass hairline border; the `flex` and `min-height`/`height` rules + `[data-portal-state]` open/tuned variants from §3; a `transition` on height/flex gated by reduced-motion.
- `.atelier-salon-portal-scene` — if not using `<WorldScenery>` directly, the painted scene layer reading `--world-scenery` / `roomSceneryFor(salonWorld)`.
- `.atelier-salon-portal-haze`, `-bloom`, `-grain`, `-vignette` — the four depth layers, `position:absolute; inset:0; pointer-events:none;` with ascending z-index below `.atelier-salon-portal-copy`.
- `.atelier-salon-portal-copy` — `position: relative; z-index: 2;` flex column, `justify-content: space-between`, padding `clamp` for cinematic margins; holds header + invitations.
- `.atelier-salon-desk` — desk treatment co-classed with `folio-cinema-composer`: fuses the composer to the stage base; warm-dark instrument surface; ensures fields read as one integrated desk row, not a stacked form.

**Translate from the prototype (adapt, don't copy literally):**
- The layered portal idea (scene → haze → bloom → grain → vignette → copy) — translate the *structure*, but build the scene from `WorldScenery`/world-DNA vars, NOT the prototype's hardcoded Kyoto/Amalfi gradients.
- The "desk fused to portal base" composition and the editorial invitation buttons.
- Reduced-motion gating pattern and the brass-hairline join.

**Do NOT copy from the prototype:**
- The prototype's inline `:root` hex palette — production uses `--ds-*` and `--world-*` tokens only (no raw hex in components; tokens or `color-mix`).
- The prototype's hardcoded `SCENES`/`RESULTS` objects, `pickScene()` regex, demo invitations with `data-scene`/`data-season`, phone mockup frames, masthead/notes/colophon, and the reset button.
- The prototype's `<input>`-driven demo desk wiring — production wires the existing React state/handlers.

**Spacing / sizing guardrails (prevent PR #455 tall-scroll):**
- Use `--ds-space-*` tokens for padding/gap. Gaps inside the panel: `var(--ds-space-4)`/`-5`.
- The panel is height-bounded (`calc(100svh - var(--ds-space-10))`) and `overflow: hidden` — never `height: auto` on the panel.
- Pre-search canvas must contribute **0 height** (render nothing in it pre-search). Do not put the invitations in the canvas — they go in the portal copy.
- No `min-height` on the canvas that would force the panel taller than the viewport.

**Reduced-motion:**
- Every new rule with `transition`/`transform`/`animation` (portal drift, bloom breathe, portal open↔tuned height transition, save microinteraction) must be disabled or reduced under `@media (prefers-reduced-motion: reduce)`. Ambient drift fully off; height transition → instant; bloom animation → static.

**Contrast (WCAG AA at rendered size):**
- Portal headline + sub: **light text** (`--ds-pearl-cream` / `--ds-text`), never `--world-ink` (dark). The vignette + a subtle text-shadow guarantee legibility over the scene. Verify ≥4.5:1 for the sub-line and ≥3:1 for the large `h1`.
- Desk fields: pearl/cream input text and visible labels on the warm-dark desk; placeholder ≥4.5:1; focus ring 2px `--ds-accent` with offset (existing pattern — preserve).
- Result cards keep their existing dark-tone tokens (already AA).

---

## 5. State / data mapping (portal behavior, no fake intelligence)

All state already exists in `ConciergePage.tsx`. Map it to portal modes:

| Production state | Portal / stage behavior |
|---|---|
| **Pre-search** (`messages.length === 0 && !lastQuery && !loading`) | `data-portal-state="open"`. Portal large (`flex:1`), shows eyebrow + `"What can I find for you?"` + 1 short mood sub-line + invitations inside the copy. Canvas empty (0 height). Scene = salon archetype default (warm "possibility" mood, no destination). |
| **User types destination** (`destination` changes) | `salonWorld = applyRoom(pickWorldFromDestination(destination), "salon")` re-computes (already memoized). `worldStyleVars` updates `--world-*`; the portal scene **tunes toward the typed destination** via the world-DNA pipeline. This is the real tuning — driven by the destination the user actually typed, not invented. If the destination is unknown to the library, it falls back to the salon archetype gracefully. |
| **User submits search** (`handleUserInput` → `sendQuery`) | On submit, `lastQuery` is set → portal switches to `data-portal-state="tuned"` and collapses to the banner; `h1` shows `"${lastQuery}"`; results canvas takes over. Destination still required (`destinationError`) — preserve. |
| **Loading** (`loading === true`) | Portal stays tuned (banner). Existing `[concierge-loading-state]` "Searching · Verifying · Composing" renders in the canvas. No fake progress bars. |
| **Results exist** (`hasResults`) | Curated shortlist reveals in the canvas as `ConciergeResultCard`s (unchanged renderer). Optional: a soft reveal animation on the section (reduced-motion gated). |
| **No results / refinement note** | Existing refinement text messages render in the canvas (`isRefinement` branch). No change. |
| **Error** (`error && !loading`) | Existing `[concierge-error-state]` named-constraint + retry renders in the canvas. No change. |

**Mood tuning rule (write this down in code comments):** the portal mood is a pure function of the typed `destination` via `pickWorldFromDestination` + `applyRoom(..., "salon")` + `roomSceneryFor`. There is **no** separate regex, no hardcoded destination list, no demo `SCENES` map. If `destination` is empty, the salon archetype default mood is shown.

---

## 6. Existing behavior preservation (must not regress)

Every item below must work exactly as on `main` after the PR:
- **Concierge search** — `callConciergeSearch(null, query, requestId, effectiveDest)` path, request IDs, destination required.
- **Refinement** — `handleUserInput`/`handleRefinement`/`parseRefinementAction`, `ACTION.*` branches, contextual search, dedupe, refinement & follow-up chips (`refinementChips`/`followUpChips`/`activeChips`).
- **Transcript** — `localStorage` persistence (`TRANSCRIPT_KEY`), lazy init, `clearTranscript`, user-turn markers, scroll-to-bottom.
- **Destination field** — `[concierge-destination-field]`, `destination`/`destinationError` validation copy.
- **Prompt/invitation click** — chips populate the **query input only** and focus it; they must **not** auto-set destination or auto-submit (this is a product-truth rule — the concierge must not pretend to know the city). Preserve `EDITORIAL_PROMPTS` exactly.
- **Verified cards** — `ConciergeResultCard`, `isRenderableVerifiedPlace`/`isAddableCanonicalCard`, TrustStrip, "Concierge note" verbatim reason, More/Less, collapsed sources, warnings.
- **Save** — `handleSaveCard` → `saveItem({ provider: "google_places", providerPlaceId, … })`, `cardSaveStates`, `[concierge-result-save-btn]`, saved/saving/error states.
- **Add to Trip** — preserve the existing standalone-page message for `ACTION.ADD_SELECTED_TO_DAY` (no trip context off-trip). Do not invent an add-to-trip control here.
- **Maps** — map link `<a>` to `googleMapsUri`/`mapsLink`; **Source** links.
- **All existing testids** (preserve unless explicitly justified in the PR body): `concierge-page`, `concierge-instrument-header`, `concierge-results-canvas`, `concierge-empty-state`, `concierge-prompt-chip`, `concierge-instrument-composer`, `concierge-destination-field`, `concierge-query-input`, `concierge-submit-button`, `concierge-clear-chat`, `concierge-result-save-btn`, `concierge-user-query`, `concierge-result-section`, `concierge-loading-state`, `concierge-error-state`.
- **Preserved classes** (pinned by `tests/atelier-salon-room-v1.test.mjs`): `atelier-salon-room`, `folio-cinema-desk`, `folio-cinema-composer`, `atelier-salon-room-header`, `atelier-salon-starter-chip`, `atelier-salon-invitation`, `atelier-salon-composer-surface`, `atelier-salon-chip-grid`, `atelier-salon-main-panel`, `atelier-salon-panel-body`, `atelier-salon-briefing-rail`. If a test must change because a class legitimately moved, update the test in the same PR and justify it.
- **Mobile nav / floating Atelier route shell** — `AppShell.tsx` keeps `isSalonRoute` immersive shell: sidebar suppressed, `AtelierNavArtifact` floating nav, `home-edge-bleed` wrapper, `data-atelier-shell="salon"`. **Do not edit `AppShell.tsx`** unless strictly necessary; if you must, preserve the 8J/F1/F2 regex patterns.

---

## 7. Prototype-only exclusions (must NOT ship)

Do not port any of these into production:
- Fake Kyoto / Amalfi / Lisbon / Hokkaido result data, or any hardcoded place list.
- Hardcoded demo regex mood logic (`pickScene`) as product truth.
- Phone mockup frames (`.phone`, notch, status bar) — those are presentation chrome for the concept doc only.
- The prototype masthead, intro section, `.notes`, `.colophon`, and any documentation/design-note copy.
- The reset/demo button and the demo `<input>` wiring.
- Fake result images / fake plate gradients standing in for photos. Production uses real `WorldScenery` painting or a real curated photo only if the world data supplies one.
- Any fake counts, fake saved totals, fake prices, fake "verified by" claims, or fabricated intelligence. Trust signals come only from `TrustStrip` + backend verification (existing).
- Design-note text rendered as user-facing copy (e.g. "A window, not a wishlist" is concept caption language — keep production copy honest and minimal).

---

## 8. Exact visual failures to block (forbidden outcomes — from PR #455)

The PR is rejected if any of these are present in screenshots:
1. **Paper page + widgets** — a light page with a bordered panel and a sidebar list, no cinematic portal centerpiece.
2. **Giant dark slab** — a single flat edge-to-edge dark rectangle with no depth, framing, or portal.
3. **Portal below the fold** — user must scroll to see the portal on a normal desktop height.
4. **Visible internal scrollbar before search** — any scrollbar in the salon/workbench/panel pre-search.
5. **Composer covering the portal** — desk absolutely positioned over or overlapping the portal.
6. **Muddy brown unreadable portal** — scene too dark/low-contrast; copy hard to read.
7. **Black text over dark portal** — using `--world-ink` (dark) for portal copy instead of pearl/cream.
8. **Separate form block instead of fused desk** — destination + query rendered as a detached stacked form with a gap from the stage.
9. **Right rail dominating** — dossier wider/taller/louder than the stage.
10. **Excessive header/intro copy above the portal** — more than the eyebrow + one h1 + one short sub-line; anything that pushes the portal down.

---

## 9. Implementation sequence for Sonnet

Do these in order; commit once at the end (one PR).

1. **Inspect** (read-only): `ConciergePage.tsx` (whole file), `globals.css` ATELIER ROOM SYSTEM section (~6976–7255) and `folio-cinema-desk`/`folio-cinema-composer` (~2141–2270), `World.tsx` (`WorldScenery`, `WorldAtmosphere`), `worldData.ts` (`applyRoom`, `pickWorldFromDestination`, `worldStyleVars`, `roomSceneryFor`, salon archetype scenery), `AppShell.tsx` (salon route — read only), `tests/atelier-salon-room-v1.test.mjs`, `docs/ai/concepts/concierge-salon-concept-v1.html`.
2. **Restructure JSX** in `ConciergePage.tsx` to the §2 hierarchy: introduce the portal section (move header + pre-search invitations into the portal copy), keep the canvas for transcript/loading/error only, keep the composer as the fused desk at base, keep the dossier aside. Drive `data-portal-state` from existing state (§5). Do not touch handlers/state logic.
3. **Add/refactor CSS** in the ATELIER ROOM SYSTEM section: add `.atelier-salon-stage-panel`, `.atelier-salon-portal` (+ `[data-portal-state]` variants), portal depth layers, `.atelier-salon-portal-copy`, `.atelier-salon-desk`. Apply the §3 flex/height constraints. Keep all existing salon classes intact.
4. **Wire existing state** to portal modes (no new fetching, no new state beyond a derived `portalMode` boolean/string computed from `messages`/`lastQuery`/`loading`).
5. **Preserve result renderers** — `ConciergeResultCard` and the transcript mapping unchanged.
6. **Update tests** — keep all preserved-contract assertions green; add new structure tests (§11). If a moved class breaks an assertion, update that assertion and justify in the PR body.
7. **Run validation** — `cd frontend && npm test` (or the targeted salon + concierge test files), plus typecheck/lint. Use the repo's default test routing; this is a UI slice (Tier 1–2), not the full backend suite.
8. **Screenshot check** — run the app and capture the four states in §10. Verify no pre-search scroll at 1440×900 and 1280×800, portal readable, desk fused, dossier balanced, real results preserved. If you cannot run a browser, say so explicitly in the PR body rather than claiming visual success.

---

## 10. Acceptance criteria (visually validatable)

The PR is acceptable only if all are true:
- **Desktop pre-search screenshot** (1440×900 and 1280×800): portal visible immediately as the centerpiece; eyebrow + one h1 + ≤1 sub-line only; invitations inside the stage; desk fused at base; dossier balanced on the right; **no internal scrollbar and no page scroll**.
- **Desktop post-search screenshot**: portal collapsed to a tuned banner reflecting the destination/query; curated shortlist of real verified cards revealed and scrolling inside the canvas only; desk pinned at base.
- **Mobile pre-search screenshot** (~390×844): portal-first and compact; 1–2 invitations; desk thumb-reachable; floating Atelier nav present.
- **Mobile post-search screenshot**: portal collapsed; results scroll beneath; sticky desk at bottom.
- Portal copy is light-on-dark and readable (passes AA); no muddy/unreadable wash.
- The desk is visually attached to the stage (no detached form, no overlay).
- Real results preserved: a live `/concierge` search returns and renders the same cards, save, maps, sources, refinement as `main`.
- `prefers-reduced-motion` disables portal/bloom animation and the open↔tuned transition.

---

## 11. Suggested tests (only useful ones)

Add to / extend `tests/atelier-salon-room-v1.test.mjs` (static, source-reading contract tests — the existing pattern in this repo):
- **Structure:** `globals.css` defines `.atelier-salon-portal`, `.atelier-salon-portal-copy`, and the four depth-layer classes; `.atelier-salon-portal` has `[data-portal-state]` open/tuned rules; `ConciergePage.tsx` renders `atelier-salon-portal` and sets `data-portal-state`.
- **Composition:** `ConciergePage.tsx` places `concierge-instrument-header` and `concierge-empty-state` inside the portal (assert the portal class appears before the canvas in source, and the empty-state is not inside `concierge-results-canvas`).
- **Preservation:** all testids in §6 still present; `folio-cinema-desk`, `folio-cinema-composer`, `atelier-salon-*` preserved classes still present; `EDITORIAL_PROMPTS` unchanged; chips populate input only (no `setDestination`/auto-submit in the chip `onClick`).
- **No fake data:** assert the production source contains none of the prototype strings (e.g. no `pickScene`, no `Nanzen-ji`, `Da Adolfo`, `Pontocho`, no `data-scene`, no `SCENES`/`RESULTS` demo objects).
- **Reduced-motion guard:** every new portal rule with `transition`/`animation`/`transform` is matched by a `@media (prefers-reduced-motion: reduce)` override (string-proximity check, same style as existing A7).
- **No pre-search internal scroll:** assert `.atelier-salon-panel-body` has no `min-height` forcing height, and the empty-state lives in the portal (so the canvas is empty pre-search). (Structural proxy — the real check is the screenshot.)

Do not add brittle pixel-snapshot tests or full e2e for this slice.

---

## 12. Final Sonnet prompt skeleton (paste into a fresh Sonnet chat)

```
Repo: prashanthkrishnan91/claude_travelapp_pk91
Branch: create a fresh branch from main.

Task: Rebuild the outside-trip Concierge page (/concierge) into the cinematic
"Private Travel Salon" composition. This is a UI layout restructure of
frontend/src/components/concierge/ConciergePage.tsx + globals.css ONLY.
No backend/API/provider/SQL/state-logic changes.

Read first (in this order):
- docs/ai/design/CONCIERGE_SALON_PRODUCTION_BLUEPRINT.md   ← the contract; follow it exactly
- docs/ai/concepts/concierge-salon-concept-v1.html         ← approved visual concept
- frontend/src/components/concierge/ConciergePage.tsx
- frontend/src/app/globals.css (ATELIER ROOM SYSTEM section, ~6976+)
- frontend/src/components/ui/World.tsx (WorldScenery, WorldAtmosphere)
- frontend/src/lib/worldData.ts (applyRoom, pickWorldFromDestination, worldStyleVars, roomSceneryFor)
- frontend/tests/atelier-salon-room-v1.test.mjs

Build to the blueprint's §2 DOM hierarchy and §3 layout constraints. The portal is
the centerpiece (header + invitations live INSIDE the portal copy); the desk is
fused to the stage base (never overlaying the portal); the canvas holds only
transcript/loading/error and is the only scroller (post-search only); the dossier
is a balanced right rail. Mood tuning is driven ONLY by the typed destination via
the existing world-DNA pipeline — no fake regex, no demo data.

Hard rules:
- Honor every forbidden outcome in blueprint §8 (no paper-page-widgets, no dark slab,
  portal must not sit below the fold, no pre-search scroll, no composer overlay, no
  muddy/unreadable portal, no dark-text-on-dark, no detached form, no dominating rail,
  no excess header copy).
- Preserve every behavior + testid + class in blueprint §6. Exclude everything in §7.
- Light-on-dark portal copy (pearl/cream, never --world-ink); AA contrast; reduced-motion
  guards on all new motion.
- Use --ds-*/--world-* tokens and color-mix; no raw hex in components.

Validate per §9–§11: run frontend tests + typecheck/lint, add the §11 contract tests,
and capture the four screenshots in §10 (desktop/mobile × pre/post search). If you
cannot run a browser, say so explicitly — do not claim visual success.

Open one PR from main, ready for review, filling the repo PR template honestly
(Level 1–2 UI slice; state test tier + why; AI usage note; Supabase SQL: No).
Stop after opening the PR.
```

---

*This blueprint is documentation only. It does not modify the production app. Implementation happens in a separate Sonnet PR per §12.*
