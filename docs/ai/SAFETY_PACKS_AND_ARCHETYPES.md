# Safety Packs and Build Archetypes — Travel

This document is the repo-native source for reusable **safety packs** and **build archetypes**. Prompts reference these by name; they do not paste the rules.

A safety pack is a named bundle of constraints / invariants / required evidence that a prompt would otherwise repeat. A build archetype is a named shape for the slice itself (capability slice, scaffold, plumbing fix, etc.).

When a slice fits a pack/archetype, the prompt names it and the pack's rules are in force automatically. Do not paste the contents below into prompts.

---

## Shared safety packs

### No Visible Behavior Change Pack

- **When to use:** refactors, internal cleanups, capability scaffolds, deduping helpers, moving code without changing visible output.
- **What it owns:** no change to user-visible UI text, layout, snapshot fields, addable-card contract, action surfaces, or external contracts.
- **Required evidence:** snapshot/contract diff is empty for visible fields; UI golden scenarios unchanged; targeted Tier 0–1 bundle from `TEST_ROUTING.md` green.
- **When not to use:** the slice is intentionally adding/changing visible behavior — use the relevant feature pack instead.

### Backend-only Scaffold Pack

- **When to use:** new module, adapter, provider, or pipeline seam shipped disabled behind a flag/contract.
- **What it owns:** no UI surface changes, no visible card change, scaffold gated off by default, contracts forward-compatible.
- **Required evidence:** Tier 1 contract bundle green per `TEST_ROUTING.md`; flag/gate verified off; visible snapshot/UI unchanged.
- **When not to use:** the slice flips visibility — use the shadow-to-visible-governance archetype instead.

### Runtime/API Contract Pack

- **When to use:** any change to API shape, snapshot endpoint, worker, db row shape, env, route, or provider behavior.
- **What it owns:** contract diff stated explicitly; downstream consumers identified; runtime evidence required (Railway / provider / cache); manual actions explicit if any.
- **Required evidence:** runtime check named (`/runtime-gate` or `/latency-gate`); contract bundle green; downstream consumers updated or explicitly out-of-scope with split proposal.
- **When not to use:** purely internal helper change with no contract impact.

### No Provider/LLM Expansion Pack

- **When to use:** any slice touching prompts, providers, LLM behavior, fanout, semantic Concierge, or research workers.
- **What it owns:** no new providers, no expanded LLM authority, no new prompt surface that owns visible card authority, no broadened tool use, no keyword patching as a substitute for semantic behavior.
- **Required evidence:** named contract showing what the LLM may and may not do; reviewer-agent check (`place-authority-reviewer`); claim-safety check.
- **When not to use:** the slice is intentionally introducing a new provider via a deliberate, gated provider-expansion slice.

### Plain-English UI Pack

- **When to use:** any visible UI / copy / card change.
- **What it owns:** no raw provider keys, no leaked diagnostics, no shadow labels, plain-English copy, no leaked thresholds.
- **Required evidence:** UI reviewer-agent clean (`accessibility-reviewer` / `premium-delight-reviewer` as applicable); UI golden scenario screenshot/diff.
- **When not to use:** backend-only slices that do not touch visible UI.

### Evidence/Claim Safety Pack

- **When to use:** any change to evidence atoms, sourced artifacts, research outputs, prose, or claim text.
- **What it owns:** every visible claim must trace to an evidence source; no fabricated claims; no leaked diagnostics; writer-safe evidence before it reaches prose.
- **Required evidence:** `claim-safety-gate` clean; reviewer-agent check (`evidence-prose-reviewer`).
- **When not to use:** structural changes that don't touch claim text or evidence.

### SQL/Persistence Manual Action Pack

- **When to use:** any Supabase SQL, schema, RLS, auth, persistence-contract change, or manual-action-required change.
- **What it owns:** explicit SQL listed; explicit manual actions in PR summary; runtime cert plan; rollback plan if applicable.
- **Required evidence:** SQL block; reviewer-agent check; manual actions checklist updated.
- **When not to use:** the slice has no schema / persistence change.

### Performance/Latency Pack

- **When to use:** any latency-sensitive surface, snapshot endpoint, route budget, cache, db, or worker change.
- **What it owns:** named latency budget; benchmark plan; before/after numbers required for visible performance claims.
- **Required evidence:** `performance-benchmarker` evidence; runtime trace.
- **When not to use:** non-latency-sensitive slice.

### Test Tier Pack

- **When to use:** every PR.
- **What it owns:** chosen test tier per `docs/ai/TEST_ROUTING.md`; reason it was sufficient; whether full suite was skipped or run with explicit reason.
- **Required evidence:** PR summary states tier and reason.
- **When not to use:** never — every PR uses this pack.

---

## Travel-specific safety packs

### Google Places Addable Authority Pack

- **When to use:** any slice touching addable cards, search-to-card flow, Discover/Saved/Trip add-to-trip flow, or candidate ingestion.
- **What it owns:** Google Places is the canonical source for addable cards. Other providers cannot mint addable cards. Addable card identity / shape is owned by Google Places.
- **Required evidence:** `place-authority-reviewer` clean; addable-card test bundle green per `TEST_ROUTING.md`.
- **When not to use:** slice does not add or change addable cards.

### Enrichment Evidence Only Pack

- **When to use:** any slice touching Yelp / Foursquare / editorial / web sources, or merging enrichment into cards.
- **What it owns:** Yelp / Foursquare / editorial / web sources are enrichment / evidence only. They cannot mint addable cards. They contribute fields/notes only inside the card contract.
- **Required evidence:** addable-card identity unchanged; enrichment fields traceable to source; `evidence-prose-reviewer` clean.
- **When not to use:** slice does not touch enrichment providers.

### Semantic Concierge Behavior Pack

- **When to use:** any slice touching the AI Concierge semantic layer, ranking, intent handling, or query understanding.
- **What it owns:** no keyword patching as a substitute for semantic behavior. Semantic behavior must be implemented at the semantic layer, not by ad-hoc keyword rules sprinkled over surface code.
- **Required evidence:** named semantic surface change; reviewer-agent check (`place-authority-reviewer` for source authority side-effects); regression coverage.
- **When not to use:** purely structural Concierge slice with no semantic behavior change.

### AI Concierge Card Contract Pack

- **When to use:** any slice touching AI Concierge cards, card shape, or whyPick / displayWhy fields.
- **What it owns:** AI Concierge card fields must stay aligned: `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick`. Card contract is preserved end-to-end.
- **Required evidence:** AI Concierge card contract bundle green per `TEST_ROUTING.md` (backend + frontend); snapshot diff shows aligned fields; renderer tests pass.
- **When not to use:** slice does not touch Concierge cards.

### No Mock/Sample Visible Data Pack

- **When to use:** any visible product surface (Concierge cards, Discover, Saved, Trip, OptimizeTripModal).
- **What it owns:** no mock / sample / prototype / unsupported visible claims. No visible deterministic-fallback notes. No `book.example.com`-style placeholder data in persistence/visible paths.
- **Required evidence:** mock/fail-closed safety bundle green per `TEST_ROUTING.md`; manual visible-surface check; `evidence-prose-reviewer` clean.
- **When not to use:** non-visible internal slices.

### Latency Budget Pack

- **When to use:** any AI Concierge / search / provider / cache / route / fanout slice.
- **What it owns:** total request-path latency matters more than local provider timeout. Latency budget for the surface is named explicitly. Provider timeouts must respect the request-path budget.
- **Required evidence:** `latency-reviewer` clean; before/after request-path latency for visible performance claims; `performance-benchmarker` evidence if claim is user-facing.
- **When not to use:** non-latency-sensitive slice.

---

## Shared build archetypes

A build archetype is a named shape for the slice. The prompt names exactly one.

### capability-slice

One coherent product or backend capability shipped end-to-end at the appropriate visibility level. Default. Includes related code, contract, tests, docs.

### disabled-promotion-scaffold

New module/adapter/provider shipped disabled behind a flag/contract. No visible change. Followed (later) by a shadow-to-visible-governance slice when ready to promote.

### shadow-to-visible-governance

Promotes a previously-scaffolded capability from shadow to visible. Owns the governance: feature flag flip, contract reveal, card-authority handoff, runtime cert.

### full-plumbing-root-cause-fix

Sev 1 or stuck-symptom fix that requires the durable end-to-end fix across the seam, not a tactical patch. Requires runtime evidence and contract audit.

### contract-consolidation

Unifies parallel/duplicate contracts (e.g., parallel adapters, duplicate snapshot fields, drift between Concierge card surfaces). Owns the migration plan and downstream consumer audit.

### runtime-validation

Deployment / Railway / provider / cache validation slice. Produces runtime evidence to certify a prior change.

### UI-surface-pass

Capped UI polish or visual consistency pass on one page/component. Requires `<ui_budget>`.

### merge-gate

Cheap PR review for merge readiness. Read-only. No fixes; report blockers.

### workflow-update

Documentation / workflow / OS update only. No product code changes. No new OS version labels (extend OS v4 in place).

---

## How a prompt uses this file

```
<safety_packs>
Google Places Addable Authority Pack, Enrichment Evidence Only Pack, AI Concierge Card Contract Pack, Test Tier Pack.
</safety_packs>

<build_archetype>
capability-slice
</build_archetype>
```

That is sufficient. Do not paste the pack contents.
