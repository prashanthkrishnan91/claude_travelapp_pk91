# DOSSIER — Travel Concierge: Interview Preparation Document

**Prepared for:** Prashanth Krishnan (PK) — Director of Analytics interview preparation
**Source of truth:** this repository only (`prashanthkrishnan91/claude_travelapp_pk91`). Every claim below cites the file, commit, or document that evidences it.
**Truth policy:** nothing here is embellished. Where the repo cannot prove something (production metrics, business outcomes, pre-May-2026 history), it is listed in §6 "ASK PRASHANTH" instead of being asserted.

**Known evidence limits (state these honestly if asked):**
- The analysis clone is **shallow**: visible git history is 178 commits, 2026-05-25 → 2026-07-19 (PRs #487–#536). Older work (PRs #1–#486) is evidenced only through docs — e.g., `docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md` (dated 2026-05-08, references PR #290) and `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md` (216 archived rows).
- Latency numbers in this repo are **engineered budgets enforced in code**, not measured production percentiles.
- Token/cost columns in the usage ledger are recorded as `unavailable` (browser-only environment has no usage metering — `docs/ai/AI_USAGE_TRACKING.md`, `.claude/skills/ship-pr/SKILL.md` step 2).

---

## Verified fact sheet (safe to quote)

| Fact | Value | Evidence |
|---|---|---|
| Product | Personal AI travel concierge, "Luxury for Less" | `README.md:3` |
| Stack | Next.js 15 / React 19 / TS strict / Tailwind v4; FastAPI / Python 3.11 / Pydantic v2; Supabase; Vercel + Railway | `frontend/package.json`, `backend/requirements.txt`, `README.md:30-44` |
| Repo size | 663 files; 223 Python files; 98 JS/TS files | file count at analysis time (2026-07-19) |
| API surface | 57 endpoints across 19 registered routers | `backend/app/routes/` (20 files), `backend/app/main.py:94-112` |
| Backend tests | 99 test files, ~3,635 test functions, ~64,780 lines of test code | `backend/tests/` |
| Frontend tests | 107 test files (source-contract style, `node --test`) | `frontend/tests/` |
| Full-suite scale | "~2,600 tests" per test-routing doc; "2510 total tests, 0 failures" recorded at PR #436 (2026-05-18) | `docs/ai/TEST_ROUTING.md`, `docs/product/BUILD_QUEUE.md` |
| Delivery rate (visible window) | ~51 PRs merged in ~8 weeks (PRs #487–#536, May 25 – Jul 19 2026), near-daily commits | git log; merge commits |
| Governance surface | 14 safety packs, 9 build archetypes, 16 reviewer agents, 22 skills, 15 command aliases, 3 hooks, 2 CI workflows, 15-check-group CI readiness gate (A–O, 711-line script) | `docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`, `.claude/agents/`, `.claude/skills/`, `scripts/workflow/ai_pr_readiness_check.py` |
| Self-learning artifacts | 18 miss-ledger entries; 216 archived usage-ledger rows; 12 product decisions with rejected alternatives | `docs/ai/MISS_LEDGER.md`, `docs/ai/USAGE_LEDGER_ARCHIVE_2026H1.md`, `docs/product/DECISION_LOG.md` |
| Self-audit | `SETUP_AUDIT.md` (PR #534) mined ~372 commits, ~365 ledger rows, 29 misses across two repos; found ~1 in 5 commits was post-push compliance repair; fixes shipped as PRs #535–#536 | `SETUP_AUDIT.md`, `docs/ai/HANDOFF.md` |
| Largest modules (honest debt) | `live_research.py` 4,642 ln; `TripBuilder.tsx` 3,026 ln; `api.ts` 2,954 ln; `globals.css` 10,383 ln | respective files |

---

# 1. SYSTEM NARRATIVE

Travel Concierge is a personal AI-powered travel planning product — "a discovery-first travel intelligence platform" (`docs/product/NORTH_STAR.md:7`) built as a Next.js 15 + FastAPI + Supabase system deployed on Vercel and Railway (`README.md:30-44`). But the honest one-line description of what was actually built is this: **a production-shaped system for making LLM-generated content trustworthy, and a governed operating system for directing AI agents as a software workforce — with the travel app as the proving ground.**

The problem the system solves is the central problem of consumer AI products: an LLM will happily recommend a restaurant that doesn't exist, invent a "waterfront view," or fabricate a drive time. The architectural answer is a strict **authority hierarchy for data**: Google Places is the sole canonical source for a place's existence, operational status, and addability — only it can "mint" an addable card (`backend/app/services/provider_registry.py:82-92`, `can_create_addable_cards`). Yelp/Foursquare are enrichment-only; editorial/web sources are evidence-only, used for reasoning but never shown as addable places (`README.md:49-65`, `backend/app/concierge/evidence.py:1-6`). Between the LLM and the user sits a deterministic **claim-safety gate** — a 752-line reviewer that rejects any visible sentence not backed by an evidence atom, with rules like "a business name is NEVER sufficient evidence for a temporal claim" ('2AM Izakaya' does not prove it's open late) — and a fail-closed contract: *hide the note, keep the card* (`backend/app/concierge/claim_safety_reviewer.py:16-27`). The same philosophy extends to routing: the AI route planner is "a read-only, explain-first advisor — never an editor"; the LLM proposes a day reorder, Google Routes verifies it with real measured legs, and any proposal crossing a day-part boundary is "rejected deterministically after generation, not silently repaired" (`docs/ai/AI_ROUTE_PLANNING_V1_ADR.md`, `backend/app/services/route_reorder_proposal_generate.py:1-55`).

The second architectural pillar is **fail-closed everywhere**. When an audit found the flights/hotels search was entirely mock-backed — persisting fake airlines with `book.example.com` booking URLs into real user itineraries — the chosen fix was not deletion and not a rushed provider integration, but honest degradation: HTTP 503 `provider_unavailable`, no trip persisted, and UI copy that says "provider integration pending" instead of the misleading "try adjusting your dates" (`docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md`, five options weighed). Providers live in a central registry where quarantined providers "will not activate in production even if API keys are present" (`docs/product/DECISION_LOG.md:83-91`); new features ship dark behind default-off flags with documented rollback env vars and activation runbooks (`backend/app/core/config.py:89-105`, `docs/ai/ROUTE_PLANNING_V1_ACTIVATION_RUNBOOK.md`).

The third pillar — and the strongest Director-level material — is that the **development process itself is an engineered, instrumented system**. All work was done through a browser/mobile Claude + Codex workflow with no local CLI (`CLAUDE.md:3`), which forced every quality control into the repo: a 15-check CI readiness gate on every PR (`scripts/workflow/ai_pr_readiness_check.py`), test-tier routing so routine PRs don't burn the ~2,600-test full suite (`docs/ai/TEST_ROUTING.md`), severity routing with a hard "stop patching after two failed patches" rule (`docs/ai/ISSUE_SEVERITY_ROUTING.md`), per-PR usage and miss ledgers, and a promotion ladder that turns repeated failures into checks — one miss gets logged, two similar misses update one precise document, three become a hook or CI rule (`docs/ai/OS_LEARNING_PROTOCOL.md`). This "AI Repo Operating System" is versioned like software (v2 → v3 → v4), and its final act in the visible history is auditing *itself*: `SETUP_AUDIT.md` (PR #534) mined the system's own ledgers, quantified that ~1 in 5 commits was post-push compliance repair, found that the 16-agent reviewer layer had zero recorded catches while CI gates and fresh-context audits caught everything, and shipped measured fixes in the next two PRs.

The philosophy, in one sentence a candidate can say out loud: *"I treated AI agents the way a director treats a team — clear contracts, evidence requirements, escalation rules, and instrumentation — and I treated AI-generated claims the way an analytics leader treats data: no claim reaches a user without a verifiable source, and when the source is missing, the system says 'unavailable' instead of guessing."*

---

# 2. DECISION LOG

The 12 most significant decisions evidenced in the repo. **⚖ = demonstrates judgment under constraint.**

### D1. Google Places is the sole authority that can mint an addable place ⚖
- **Context:** LLMs and enrichment APIs hallucinate or mismatch venues; an itinerary full of nonexistent places destroys trust.
- **Options visible:** treat all providers as peers vs. a single canonical authority with everything else demoted.
- **Decision:** only `google_places` carries `can_create_addable_cards=True`; promotion to an addable card requires `business_status == "OPERATIONAL"` plus name-match confidence (`backend/app/services/provider_registry.py:82-92, 354`; `backend/app/services/google_places.py:186-192`). Yelp/Foursquare = enrichment signals only; editorial = evidence only (`backend/app/concierge/evidence.py:1-6`).
- **Consequence:** zero hallucinated venues by construction, at the cost that every card requires a paid Google verification call. The frontend mirrors the contract fail-loud: cards missing the canonical fields are dropped, "so backend contract drift surfaces as missing cards (loud) instead of a silently degraded polished card (quiet)" (`frontend/src/components/trips/AIConciergePanel.tsx:498-512`).

### D2. Fail closed instead of mock data — keep the product concept, kill the fake data ⚖
- **Context:** audit found flights/hotels search fully mock-backed, and `/trips/create-with-search` persisting fake bookings into itineraries — "the highest-blast-radius mock-derived persistence path in the repo."
- **Options considered (all five written down):** A fail-closed UX, B provider scaffold, C Amadeus flights, D hotels provider, E delete the surfaces (`docs/ai/LEGACY_FLIGHTS_HOTELS_STRATEGY.md`, 2026-05-08).
- **Decision:** Option A — HTTP 503 `provider_unavailable`, no persistence, honest copy; Option E explicitly rejected ("prefer disable/fail closed over delete the product concept").
- **Consequence:** enforcement went into code: remaining fixtures must carry a `__legacy_product_mock__` marker, and persistence "fails closed on any mock-derived row" including `book.example.com` URLs (`backend/app/services/search.py:26-121`; regression tests `backend/tests/test_create_with_search_fail_closed.py`). A durable product invariant was born: "No Mock/Sample Visible Data Pack" (`docs/ai/SAFETY_PACKS_AND_ARCHETYPES.md`).

### D3. Central Provider Registry with quarantine semantics
- **Context:** provider sprawl (Duffel, Amadeus, Ignav, Skyscanner, Brave, Serper, Foursquare…) and the risk of an API key silently activating an untrusted source.
- **Decision:** one frozen registry entry per provider with role enum, `production_allowed`, and quarantine status; disabled providers "will not activate in production even if API keys are present" (`backend/app/services/provider_registry.py:155-279`; `docs/product/DECISION_LOG.md:83-91`, 2026-05-12).
- **Consequence:** when Ignav (the live flight provider chosen after Skyscanner API access was rejected — `docs/product/DECISION_LOG.md:211-224`) returned "externally incorrect schedule times" in a production smoke test, it was quarantined by editing one file (`provider_registry.py:264-279`). Duffel later required a *second* trust gate: it calls the API but returns UNAVAILABLE until `DUFFEL_SCHEDULE_TRUST_CERTIFIED=1` (`backend/app/services/flights_provider_duffel.py:10-18`).

### D4. Latency is a budget, quality degrades — never the reverse
- **Context:** the concierge pipeline fans out to Google, enrichment, and an LLM note-writer; unbounded, it would be slow exactly when it matters.
- **Decision:** a request-scoped deadline manager: 3,000ms p50 target, 4,000ms soft ceiling (skip LLM note generation), 6,000ms hard cutoff (return best available), card count clamped to 5–7, LLM set-writer capped at 1.5s and not even started under 1,200ms remaining (`backend/app/concierge/deadline_manager.py:33-45`). Critical path (Google search) separated from droppable enrichment (`backend/app/concierge/parallel_retrieval.py`).
- **Consequence:** cards always return; prose is what gets sacrificed. Enforced by adversarial tests "designed to FAIL a weak implementation" (`backend/tests/test_concierge_latency_architecture_v1.py`, `test_sla_card_cap.py`). *(Note: these are engineered budgets, not measured production percentiles.)*

### D5. Deterministic regex claim-safety gate instead of an LLM judge ⚖
- **Context:** every LLM-visible sentence is a hallucination risk, but adding a second LLM as judge adds cost, latency, and non-determinism.
- **Decision:** a 752-line deterministic reviewer (<1ms) with typed evidence atoms and a closed claim-type set; unsupported claim ⇒ "hide note, keep card" (`backend/app/concierge/claim_safety_reviewer.py`), backed by `reason_validator.py` (bans waterfront/view/Michelin/hours/price claims without evidence) and a deterministic safe-reason fallback.
- **Consequence:** cheap, fast, auditable — and honestly brittle to novel phrasing (a trade-off worth owning in interviews). Telemetry invariants are asserted in tests: `fallback_note_visible_count: 0` (`claim_safety_reviewer.py:30-36`).

### D6. "LLM proposes, deterministic systems verify" for AI route planning
- **Context:** after route foundations shipped, the tempting next step was auto-optimizing users' days — maximal blast radius on user data.
- **Decision:** two decision-only ADRs *before* implementation (`docs/ai/ROUTE_PLANNING_V1_CONTRACT.md` PR #509; `docs/ai/AI_ROUTE_PLANNING_V1_ADR.md` PR #525): AI is read-only and explain-first; any reorder requires explicit user approval with before/after preview; LLM output crossing day-part boundaries is rejected, not repaired; both orders are verified against real Google Routes legs; "No fabricated travel time, distance, or location" (`backend/app/services/route_reorder_proposal_generate.py:1-55`).
- **Consequence:** the feature shipped as 6+ lettered PRs (A–F, #526–#531) each independently gated, then activation (#533) — and the verification stance caught real bugs pre-merge (see stories 3, 4, 5 in §3).

### D7. Feature-flag-everything with production-inert activation runbooks
- **Decision:** ~10 default-off flags each annotated with rollback env var and preconditions; full reorder flow requires 4 flags + 2 keys, "Any missing piece fails closed… never a guess" (`backend/app/core/config.py:89-105`); a master kill switch `ALLOW_LIVE_RESEARCH_CALLS` overrides everything (`config.py:35-39`, tested in `backend/tests/test_live_research_killswitch.py`); route planning shipped feature-complete but production-inert with a pre-activation checklist and cost guardrails (`docs/ai/ROUTE_PLANNING_V1_ACTIVATION_RUNBOOK.md`).
- **Consequence:** code merges are decoupled from risk activation — the same separation-of-deployment-from-release discipline used in mature data platforms.

### D8. No atomic write primitive → best-effort rollback + honest error copy ⚖
- **Context:** applying an approved reorder means N sequential per-item position writes; Supabase usage here has "no atomic/batch position-write primitive" (`backend/app/services/route_reorder_proposal.py:23-31`).
- **Options:** build a SQL/RPC transactional surface (new migration, manual action) vs. application-level compensation.
- **Decision:** stale-order check at apply time, tracked writes with reverse rollback, fail-closed 502 — and, in a follow-up, the error message only claims "nothing changed" when every rollback write actually succeeded (`route_reorder_proposal.py:184-247`; commits `c9b5c20`, `c1cb929`).
- **Consequence:** a consciously-documented engineering trade-off (honest messaging over new infrastructure), plus tests for mid-apply failure and failing rollback.

### D9. Discovery-first pivot; Saved Item becomes the root object
- **Context:** the app originally forced trip creation before any value ("Trip-first gate forces users to commit before they explore").
- **Decision (2026-05-10):** product spine becomes Discover → Search → Save → Plan → Optimize → Watch; "Travel Idea / Saved Item is the future root object"; trip becomes one conversion path (`docs/product/DECISION_LOG.md:18-30`, `docs/product/NORTH_STAR.md:7-20`). The save foundation deliberately rejected sentinel-trip hacks: "Hidden or sentinel `trip_id` values to fake global persistence" is explicitly forbidden (`docs/product/STAGE_2A_CONTRACT.md:88`).
- **Consequence:** a staged roadmap with entry/exit gates per stage (`docs/product/ROADMAP.md`) and Stage 3 honestly marked "functionally exited" with two named accepted gaps rather than claimed complete.

### D10. A scope-creep firewall: DO_NOT_BUILD_YET as a first-class artifact ⚖
- **Decision:** consciously deferred items live in `docs/product/DO_NOT_BUILD_YET.md` ("the scope-creep firewall"): auto-booking, social features, noisy alerts, scraping-heavy deal infra, "trying to become an Expedia/Kayak replacement," and fake hotel rates before a named provider contract exists. New ideas route to `docs/product/IDEA_INBOX.md` with a triage decision, not to the build queue. Major design work is gated behind an explicit timing rule: no design transformation "until the product workflows are stable enough that visual work will not be repeatedly invalidated by feature churn" (`docs/ai/DESIGN_VISION.md:5-17`).
- **Consequence:** every decision log entry records rejected alternatives and "what would change our mind" — reversible, evidence-based scoping (`docs/product/DECISION_LOG.md:5-14`).

### D11. The AI Repo Operating System: prompts carry only the task delta ⚖
- **Context:** an earlier prompt standard implied every prompt should repeat every rule — causing "prompt bloat and tiny micro-PRs" (`docs/ai/PROMPT_ENGINEERING_STANDARD.md:7`).
- **Decision (OS v4):** prompts are 6-section work orders (task delta 2–6 lines, named safety packs, archetype, anchor files, acceptance evidence, stop condition) targeting <700–1,200 words; repeated process lives in the repo as 14 safety packs, 9 archetypes, 22 skills, and routing docs; a hard compression gate fails prompts that are mostly repeated workflow language (`docs/ai/AI_REPO_OPERATING_SYSTEM.md`, `CLAUDE.md`). Work ships as one coherent "capability slice" per PR, with explicit split criteria.
- **Consequence:** an explicitly versioned process (v2: skills+reviewers → v3: self-learning loop → v4: consolidation, "no v4.2 or v5 — extend in place", `AI_REPO_OPERATING_SYSTEM.md:112-122`).

### D12. Enforcement lives in CI, not in documentation ⚖
- **Context:** the same PR-body formatting miss recurred four times (PRs #381, #394, #397, #420) *after* being documented in KNOWN_FAILURE_MODES (`docs/ai/MISS_LEDGER.md`; `SETUP_AUDIT.md` finding #1).
- **Decision:** promote failure patterns into a 711-line, self-tested CI gate with 15 check groups — usage-ledger enforcement, exact body anchors, runtime-evidence requirement (failure seam before patching), design-claim vs. screenshot check, patch-exhaustion hard fail at 3 follow-ups, committed-`.env` hard fail, PR size limits (`scripts/workflow/ai_pr_readiness_check.py`; `docs/ai/AI_PR_READINESS_GATE.md`). Promotion follows a ladder: 1 miss → ledger; 2 similar → one precise doc; 3 → hook/CI (`docs/ai/OS_LEARNING_PROTOCOL.md`).
- **Consequence:** the browser-only constraint (no local shell, no local lint — `CLAUDE.md:3`) made this mandatory: quality had to be machine-checked server-side because nothing could be assumed about the operator's environment.

---

# 3. FAILURE & RECOVERY STORIES

These are real, evidenced, and told honestly — the strongest interview material in the repo.

### F1. The PR #499 patch loop: six attempts, production-DB forensics, and a surgical revert
Route-planning readiness depended on itinerary items carrying coordinates. PR #499 (branch `claude/gracious-fermat-FagWz`, May 28 – Jun 1 2026) tried to fix coordinate loss and looped: v1 (`48ed549`) → v1.1 (`0a60678`) → v1.2 (`6928848`) → v1.3 (`5beebf5`) → v1.4 (`d38ee69`) → revert (`8f5453e`). Two frontend patches were written before anyone looked at the actual data. The breakthrough (v1.2) came from **querying the persisted Supabase rows**: three Miami items created within 333ms with `details.lat=null` and no concierge source — the signature of the `/plan/day` ingress. Root cause: the `PlannedAttraction`/`PlannedRestaurant` Pydantic models in `backend/app/models/plan.py` simply had no lat/lng fields, so `backend/app/routes/plan.py` silently dropped coordinates that upstream results carried. When v1.4 caused a perceived preview regression, the response was a *surgical* revert preserving the production-proven v1.1–v1.3 (commit `8f5453e` documents exactly what was reverted vs. kept). The saga violated the repo's own written two-patch escalation rule (`docs/ai/FAILURE_RECOVERY.md`), and `SETUP_AUDIT.md` later named it the repo's largest token sink — driving a rewritten enforcement-backed `failure-recovery` skill and a planned DEAD_ENDS registry. **Interview frame:** evidence-first debugging ("query the persisted row before patching again"), and honest acknowledgment that a written rule without enforcement didn't hold.

### F2. One bug class, five separate fixes — until a canonical contract ended it
The lat/lng metadata gap recurred across five PRs because many ingress paths write itinerary items and each was patched alone: `ResultActionSheet.buildSavePayload` never wrote coordinates (#501, `81e181c`); `travelHints.ts` read only one key spelling (#504, `f579b53`); the backend requested `places.location` from Google **but never parsed it** (#508, `b05d4c7`, a 5-line fix shipped with 761 lines of tests); saved-items conversion dropped `category` and `gv.lat/lng` (#521, `a050bf9`); and finally PR #530 (`ab29d2a`) audited *every* add-to-itinerary path, finding `TripBuilder.handleAddResult` dropped metadata entirely and that frontend and backend disagreed on coordinate range validation. The durable fix was a canonical read/write contract (`frontend/src/lib/tripItemMetadata.ts`, `itineraryCoordinates.ts`) plus [-90,90]/[-180,180] parity — not a sixth handler patch. `SETUP_AUDIT.md`'s verdict: "Lossy intermediate card shapes silently drop place identity; every handler patched alone regresses another path." **Interview frame:** recognizing a bug *class* vs. a bug instance; schema/contract thinking over spot fixes.

### F3. Partial-write risk caught by a pre-merge audit (PR #528)
The reorder-apply endpoint sequentially PATCHed item positions; a mid-sequence failure could leave a user's day half-reordered while returning `status="applied"`. A fresh-context audit of the open PR flagged it as a merge blocker; the fix (`c9b5c20`) added tracked writes, reverse rollback, a fail-closed 502, tightened the response `status` from `str` to a closed `Literal`, and added tests for mid-apply and failing-rollback paths (`backend/app/services/route_reorder_proposal.py`). The audit also caught that visual proof was claimed but not committed — fixed in the same commit (`docs/visual-proof/pr528/`).

### F4. Fixing the honesty of the fix (PR #528 follow-up)
Story F3's own 502 message said "nothing changed" even when rollback writes themselves failed. Commit `c1cb929` ("Make rollback-failure error copy honest") made `_rollback_positions` report whether every rollback write succeeded, and the copy now only claims restoration when true. **Interview frame:** error messages are claims too, and claims require evidence — the claim-safety philosophy applied recursively to the system's own failure paths.

### F5. The app fabricating data from its own fallback (PR #531, "PR F blocker")
After clearing stale Google route legs, the route connector fell back to a local haversine estimate and rendered it **with the same "min drive · km" copy as a real provider leg** — locally-computed guesses dressed as measured route timing. An audit flagged it; the fix (`a15fd34`) restricts duration/distance rendering to matched Google Routes legs, with a neutral "Route time unavailable" state otherwise, six regression tests, and committed visual proof captured via a temporary harness that was itself reverted after capture. **Interview frame:** the hardest fabrication risks aren't the LLM's — they're your own fallback code paths.

### F6. Literally-false UI copy caught by audit (PR #529)
`DayFlowReview` displayed "Hotels and flights are excluded from route planning v1" whenever *any* non-routable item existed — literally false on a transit-only or note-only day. Fix `5f1e718` replaced the boolean with an `excludedStopTypes` array naming only the types actually present, and separately fixed a readiness gate that conflated "eligible" stops with "located" stops (+107 test lines, `frontend/src/components/trips/ItineraryDayColumn.tsx`).

### F7. "1715 tests, 0 failures" — while 63 new tests never ran (PR #420)
A new test file was committed but not wired into `package.json`'s explicit test list, so the PR truthfully-but-wrongly claimed a full pass; the real count was 1778 (`docs/ai/MISS_LEDGER.md`, 2026-05-17). Related: the readiness checker itself had a false-PASS mode — run without `--pr-body-file`, it silently skipped section checks — which is now a hard-coded warning in `CLAUDE.md` and `ship-pr` step 6. **Interview frame:** verification tooling needs verification; a green check is only as good as what the check actually executed.

### F8. The system audits itself — and the fix breaks its own CI (PRs #534–#536)
`SETUP_AUDIT.md` (2026-07-18/19) mined the workflow's own telemetry (~372 commits, ~365 ledger rows, 29 misses across two repos) and quantified the process's failure modes: ~1 in 5 commits was post-push compliance repair; `HANDOFF.md` had bloated to 1,007 lines (~10–15K tokens of per-session read tax; now 34 lines); the 287KB usage ledger had grown too large for the Read tool while every token column read `unavailable`; **the 16-file reviewer-agent layer had zero recorded catches in ~160 PRs** (`AGENT_EFFECTIVENESS_LEDGER.md` still "None yet") while CI gates, tests, and fresh-context audits caught everything; PR #533 was hand-polled hourly for 8+ days; 19 of 21 skills lacked the frontmatter needed to auto-fire. Fixes shipped immediately: the `ship-pr` single-pass packaging skill (PR #535) and ledger/HANDOFF slimming (PR #536) — and PR #536 itself broke CI because `certify_v4_1.py` hard-asserted the retired 26-column ledger schema, escalating from a spot patch (`ddceca9`) to a full downstream-consumer audit (`c270032`) within the same PR. Notably, finding #9 (fresh-chat rule vs. 46% same-chat reality) was deliberately closed with **"do nothing"** — not every finding deserves a rule. **Interview frame:** measuring your own process with its own exhaust data, killing your own darlings (the reviewer-agent fleet), and knowing when *not* to add process.

---

# 4. STAR CASE STUDIES

Calibrated for Director of Analytics: systems thinking, quality guardrails, directing AI as a workforce. All claims trace to §§1–3 citations.

### S1. Directing an AI workforce with an engineered operating system
- **Situation:** A solo builder using multiple AI agents (browser Claude for building, Codex for surgical fixes, ChatGPT for work-order writing and review — roles codified in `AGENTS.md`) on a growing codebase, with no local dev environment at all (`CLAUDE.md:3`).
- **Task:** Sustain high shipping velocity without the classic AI failure modes — hallucinated claims, silent scope creep, plausible-but-wrong fixes, unbounded patch loops.
- **Action:** Built a versioned "AI Repo Operating System": prompts reduced to task deltas referencing 14 named safety packs and 9 build archetypes; severity routing (Level 0–3) deciding patch vs. root-cause vs. split; test-tier routing (Tier 0–3 vs. a ~2,600-test suite); a 15-check CI readiness gate enforcing evidence (failure seams before runtime patches, screenshots before visual claims, ledger rows before merge); and per-PR usage + miss ledgers feeding a promotion ladder that converts repeated failures into automated checks.
- **Result (verifiable):** ~51 PRs merged in the 8 visible weeks with near-daily activity; pre-merge audits repeatedly caught real defects (partial-write risk, fabricated route timings, false UI copy — §3 F3–F6); and the process itself was measurable enough to be audited and improved with data (§3 F8). *Honest caveat: single-user project; the claim is about the governance system, not scale of team.*

### S2. A trust architecture for AI-generated content (the analytics-governance story)
- **Situation:** A consumer AI product where the model could invent venues, amenities, hours, and travel times.
- **Task:** Make every user-visible claim traceable to a verifiable source — the same provenance discipline analytics leaders demand of metrics.
- **Action:** Designed a data-authority hierarchy (Google Places canonical and solely able to mint addable cards; enrichment and editorial sources structurally demoted); typed evidence atoms with a closed claim-type vocabulary; a deterministic claim-safety reviewer with fail-closed behavior ("hide note, keep card"); a display-contract normalizer that "never invents data"; and a UI trust layer where "Verified by Google" can only render on explicit evidence and missing fields are omitted, never shown as "N/A" (`backend/app/concierge/*`, `frontend/src/lib/concierge/cardHelpers.ts`, `frontend/src/components/ui/TrustStrip.tsx`, `docs/product/DESIGN_IMPLEMENTATION_CONTRACT.md` §21–24).
- **Result:** Fabrication is prevented *by construction* rather than by review — including against the system's own fallback code (§3 F5). Telemetry invariants (`fallback_note_visible_count: 0`) are asserted in tests, and a per-request log table captures response type, intent confidence, model, token counts, and latency for offline analysis (`backend/db/migrations/004_concierge_request_log.sql`).

### S3. From patch loop to root cause: the coordinate-loss investigation
- **Situation:** Route planning readiness was blocked by itinerary items mysteriously missing coordinates; two frontend patches had already failed (§3 F1–F2).
- **Task:** Stop the loop and find the real cause.
- **Action:** Switched from patching symptoms to forensics on production data: traced specific persisted Supabase rows (three Miami items, `details.lat=null`, created within 333ms, no concierge source) to fingerprint the ingress path; found the backend Pydantic models silently dropping fields; later ran a systematic audit of *every* ingress path and unified them behind one canonical metadata contract with frontend/backend validation parity (PR #530).
- **Result:** The bug class — previously fixed five separate times — stopped recurring through contract consolidation; the episode was written into the failure-recovery doctrine ("query the actual persisted row before patching again") and honestly logged as the repo's most expensive lesson (`SETUP_AUDIT.md` finding #3).

### S4. Auditing my own operation with its own data
- **Situation:** After ~2 months and hundreds of PRs of AI-assisted development, process friction was noticeable but unquantified.
- **Task:** Measure the workflow objectively and fix the highest-cost problems first.
- **Action:** Ran a ranked self-audit (`SETUP_AUDIT.md`) over the system's own exhaust: 372 commits, ~365 usage-ledger rows, 29 miss entries. Quantified compliance-repair waste (~1 in 5 commits), context tax (1,007-line handoff ≈ 10–15K tokens per session), rule-violation rates (patch loops past the written limit), and — most uncomfortably — that the 16 reviewer agents had zero recorded value while CI gates caught everything. Converted findings into ranked clusters and shipped the top two within 24 hours (ship-pr skill, context-tax reduction); explicitly decided one finding warranted no action.
- **Result:** Measured before/after: handoff 1,007 → 34 lines; every pre-push check consolidated into a single-pass skill targeting the 26% waste figure; the audit and both fixes are the last three merged PRs in the repo. **This is the purest analytics-leadership story in the codebase: instrument, quantify, prioritize by cost, act, and retire what the data says isn't working — even your own ideas.**

### S5. Engineering latency as a first-class budget
- **Situation:** The concierge pipeline fans out across a paid search provider, enrichment sources, and an LLM writer — unbounded, the worst queries would be the slowest.
- **Task:** Guarantee responsiveness while spending as much of the budget as possible on quality.
- **Action:** Built a request-scoped deadline manager (3,000ms target / 4,000ms soft / 6,000ms hard) that sheds work in a designed order — enrichment first, LLM prose second, never the cards; capped LLM writing at 1.5s with a don't-even-start threshold; split critical from droppable retrieval; added per-stage timing telemetry and cost guardrails (per-user rate limits + duplicate-request cooldowns returning 429/Retry-After) on the expensive endpoints (`backend/app/concierge/deadline_manager.py`, `parallel_retrieval.py`, `backend/app/core/cost_guardrails.py`).
- **Result:** Degradation semantics are explicit and adversarially tested (tests "designed to FAIL a weak implementation"). *Honest caveat: budgets and enforcement are verified in code and tests; measured production percentiles are not in the repo.*

### S6. Shipping a risky AI feature as governed slices (Route Planning v1)
- **Situation:** The most-wanted feature — AI reordering of a user's day — was also the most dangerous: it writes to user itineraries based on LLM output.
- **Task:** Ship it without ever letting the AI silently edit user data.
- **Action:** Wrote two decision-only ADRs before any code (contract PR #509, AI-layer PR #525) establishing "read-only, explain-first advisor — never an editor." Delivered as lettered slices (#526 diagnostic → #527 read-only UI note → #528 approval contract → #529 review surface → #530 coordinate parity → #531 connector hardening → #533 activation), each independently gated with tests and committed visual proof, all behind default-off flags with an activation runbook. Fresh-context audits on open PRs caught partial-write, fabricated-timing, and false-copy defects before merge (§3 F3–F6). A UI experiment (#514's Check-route panel) was deleted three weeks later (#519) when inline connectors proved better — and later, diagnostic surfaces were removed from the product UI for "reading as internal/debug tooling" (#532).
- **Result:** The feature reached activation with the invariant intact: every user-visible travel time originates from Google Routes, every reorder requires explicit approval, and every failure path is fail-closed with honest copy.

---

# 5. LIKELY CHALLENGE QUESTIONS (with honest, repo-grounded answers)

**Q1. "This is a personal project with no users. Why does it matter for a Director role?"**
Honest answer: correct — the repo itself says "optimized for personal use and rapid iteration, not production-scale distribution" (`README.md:105`), and there are no user metrics anywhere. The claim isn't scale; it's that the *governance problems* are the same ones a Director owns: provenance of claims, quality gates that don't rely on heroics, measurable process, escalation rules, and directing non-deterministic workers (AI agents) toward reliable output. The artifacts — a 15-check CI gate, 18-entry miss ledger, ranked self-audit with quantified waste — are real management systems, exercised across ~536 PRs.

**Q2. "Your frontend 'tests' just read source files and grep for strings. Are those real tests?"**
Honest answer: they are contract/regression tests, not behavioral tests, and the repo says so itself: they "guard the user-visible copy strings, not the runtime behavior, since the repo does not yet wire React Testing Library" (`frontend/tests/fail-closed-flights-hotels.test.mjs`). That was a deliberate trade in a browser-only environment with no local runtime: 107 files of executable ADRs that lock invariants and PR-slice contracts. The backend is different — ~3,635 unit tests. The known gaps: no DOM rendering tests, no e2e, and backend tests stub FastAPI/Supabase so the real HTTP layer is untested — and PR #420 proved the meta-risk (63 tests silently not running). I'd stand up runtime testing before any multi-user deployment.

**Q3. "You built 16 reviewer agents that never caught anything. Isn't that over-engineering?"**
Honest answer: yes, and I'm the one who proved it. `SETUP_AUDIT.md` finding #7: after ~160 PRs, the agent-effectiveness ledger still read "None yet," while every real catch in the miss ledger credits CI gates, tests, PK review, or fresh-context audit sessions. The transferable lesson: track the effectiveness of your quality mechanisms as data, and be willing to retire your own ideas when the ledger says they don't pay. Fresh-context *audits* (same idea, different mechanism) demonstrably worked — they caught the partial-write and fabricated-timing blockers.

**Q4. "Your own ledger shows you violated your own two-patch escalation rule. Why should anyone believe your process works?"**
Honest answer: PR #499 ran six attempts and the same coordinate gap was re-fixed across five PRs — with the rule already written down (`docs/ai/FAILURE_RECOVERY.md`). The finding I stand behind: *written rules don't change behavior; enforcement does.* That's exactly why the readiness gate hard-fails at 3 follow-ups without an escalation note (check H), and why the promotion ladder ends in CI checks, not more prose. The four-times-repeated PR-template miss (#381/#394/#397/#420) is the cleanest proof: documented after occurrence one, kept recurring, stopped only when it became a machine check.

**Q5. "Where is the analytics in this? You're interviewing for Director of Analytics."**
Honest answer: there's no BI stack here, and I won't pretend otherwise. What the repo shows is analytics *thinking* applied to two domains: (1) data governance for AI content — authority hierarchies, typed evidence, closed vocabularies, provenance-gated claims, an instrumented request log with model/tokens/latency/intent-confidence per request and a 30-day retention policy (`backend/db/migrations/004_concierge_request_log.sql`), a deterministic weighted ranking model with documented invariants (`backend/app/concierge/ranker.py`), and a cents-per-point value-scoring engine (`backend/app/services/value_engine_v2.py`); (2) process telemetry — per-PR ledgers analyzed to quantify waste (26% compliance-repair commits) and drive ranked fixes. Business-analytics scale and stakeholder work come from my career, not this repo (see §6).

**Q6. "The security posture: CORS `*`, service-role key bypassing RLS, hardcoded Supabase URL, JWKS never refreshed. Production-quality?"**
Honest answer: those are real (`backend/app/main.py:37-44`, `backend/app/db/client.py:24-26`, `backend/app/core/auth.py:17-25`), and consistent with a single-user private deployment — the repo is explicit about that scope. There's also a genuinely risky default I'd fix first: Supabase client-creation failure silently falls back to an in-memory mock DB with only a log warning (`db/client.py:35-39`). Auth itself is real (Supabase JWT verification, ownership checks on every trip/day mutation, fail-closed API client). Multi-user would require: RLS with anon key, secrets hygiene, CORS allowlist, distributed rate limiting (current guardrails are per-process in-memory).

**Q7. "Why a regex claim-safety gate instead of an LLM judge? Isn't that brittle?"**
Honest answer: deliberately brittle-but-auditable. The reviewer is deterministic, <1ms, testable with 123 dedicated tests, and fails closed — a rejected note hides prose but never blocks the card. An LLM judge would add cost and latency on every request and make failures non-reproducible. The known weakness is novel phrasing slipping past patterns; the mitigation is layered defense (evidence-typed atoms upstream, banned-claim validator, deterministic fallback writer) plus captured-production-failure harnesses (`backend/tests/evidence_harness_v5.py`) that re-test exact bad phrasings from past incidents.

**Q8. "A 3,026-line component, a 2,954-line API client, a 10,383-line stylesheet. Is that quality?"**
Honest answer: that's real accumulated debt and I can name it precisely (`TripBuilder.tsx`, `api.ts`, `globals.css`, plus two near-duplicate ~1,550-line concierge surfaces and untyped JS islands in a strict-TS repo). The counterweight: zero TODO/HACK markers because debt is tracked in docs and audits rather than comments; the riskiest seams (card contract, coordinates, claim safety) were pulled into small canonical modules *because* audits showed monoliths dropping data; and contract tests pin the invariants refactors must preserve. Slice-based delivery under PR-size CI limits kept changes reviewable even when files stayed big.

**Q9. "How did you develop and validate anything with no local environment at all?"**
Honest answer: everything ran through browser/mobile Claude sessions against the repo, with CI as the only executor — which is why enforcement had to live in scripts and workflows. Costs of that constraint are documented: Vercel-only ESLint failures because lint couldn't run pre-push (recurred three times before promotion — `MISS_LEDGER` 2026-05-26), token columns permanently `unavailable`, and validation leaning on committed screenshot evidence (`docs/visual-proof/pr514…pr531`) plus production-DB inspection via Supabase MCP for runtime truth. The discipline that emerged — evidence files in the repo, machine-checked PR bodies, single-pass `ship-pr` packaging — is the interesting part: it's remote-team management logic applied to tools.

**Q10. "What breaks first if this had to scale to real users?"**
Honest answer, from the repo's own weaknesses: per-process in-memory rate limits and caches (no cross-replica coordination — `backend/app/core/cost_guardrails.py`, `provider_cache.py`); non-transactional multi-write itinerary operations relying on best-effort rollback (`route_reorder_proposal.py:23-37`); the silent mock-DB fallback; Google-per-card verification cost with no shared cache tier beyond 6–24h TTLs; no runtime/e2e test layer; and prop-drilled client state with no cache layer, already flagged as a scaling risk as surfaces multiply. I'd sequence: kill the silent fallback, move guardrails/caches to a shared store, add an RPC transactional write path, then runtime tests.

*(Bonus) Q11. "What did you deliberately not build?"* — Auto-booking, social features, scraping-heavy deal infra, an Expedia clone, and mock hotel rates — each with a written reason and a re-entry condition (`docs/product/DO_NOT_BUILD_YET.md`); plus a design-sprint timing gate that blocked "painting the walls before the foundation is set" (`docs/product/DECISION_LOG.md:32-37`).

---

# 6. ASK PRASHANTH

Gaps only you can fill. Do not assert any of these in an interview without your own confirmation.

**Business & motivation**
1. Why you built this — the real story (learning vehicle for AI-directed development? product ambition? both?), and how you frame it relative to your day job.
2. Who actually uses it today — is it deployed and in personal/family use? The "wife-wow" goal is documented (`NORTH_STAR.md:20`); the outcome is not.
3. Your professional analytics background — the repo shows governance instincts but nothing about your career scale (team size, data platforms, business impact). Interview answers must bridge the two.

**Timeline & history (shallow-clone gaps)**
4. Project start date and the story of PRs #1–#486 (only PR #290+ is indirectly evidenced from 2026-05-08 docs). Total calendar duration and hours/week invested.
5. The sibling repo (`SETUP_AUDIT.md` audits a "finance tracker" alongside this one) — is it part of your narrative? Its ~22-PR provider saga is referenced but not verifiable here.
6. The pre-OS era: what development looked like before OS v2, and what specifically prompted creating the operating system (the miss ledger's 2026-05-07 seed entries hint at a "deployment storm" and follow-up loops).

**Outcomes & metrics (not in repo)**
7. Actual spend: API costs (Google Places, Anthropic, Tavily), Railway/Vercel bills, and any Claude usage totals — all token columns read `unavailable`.
8. Production reality of Route Planning v1: `HANDOFF.md` says the activation flags/keys were unverified as of 2026-07-19. Did activation happen? Any measured latencies or usage?
9. Measured concierge latency in production vs. the 3s/4s/6s budgets — the repo only proves the budgets exist and are tested.
10. Before/after evidence that the ship-pr skill actually reduced the 26% compliance-repair rate (it shipped 2026-07-18; the repo history ends the next day).
11. Which model(s) did the building — the OS assigns roles (Sonnet builds, Opus plans, Codex patches per `AGENTS.md`), but per-PR model data is mostly archived/unavailable.
12. Supabase data volumes (trips, items, request-log rows) — nothing in the repo states them.

**Narrative choices**
13. How you want to attribute the work: the repo evidences a human-directed multi-agent workflow (PK + ChatGPT + Claude + Codex per `AGENTS.md`). Decide the honest phrasing you're comfortable with — e.g., "I architected, directed, audited, and quality-gated; AI agents wrote most of the code under contracts I enforced."
14. Any interview claims about Anthropic/OpenAI tooling preferences, costs, or comparative agent performance — the repo contains role assignments but no benchmark data.
15. What you'd build next and why — `BUILD_QUEUE.md` says Stage 3.5 design surfaces are "Now" and Stage 4 AI destination intelligence is "Next," but your current intent may differ.
