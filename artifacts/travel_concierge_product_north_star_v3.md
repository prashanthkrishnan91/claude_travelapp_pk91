# Travel Concierge Product North Star v3

Date: 2026-05-09
Repo: `prashanthkrishnan91/claude_travelapp_pk91`
Status: Architecture / product spec / planning only. No runtime code, SQL, UI, or provider changes.
Severity classification: Level 3 — long-term product model, staged roadmap, feature layers, and Wife Wow Readiness Gate.

Companion to:
- `artifacts/ai_concierge_semantic_place_intelligence.md`
- `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md`

These two artifacts remain the binding north star for AI Concierge place search, verified addable cards, evidence, notes, latency, reviewer gates, and quality certification. This v3 artifact is broader and product-level. It does not replace them.

---

## 1. Executive summary

Travel Concierge is becoming a premium household travel discovery and intelligence platform. The product loop is:

```text
Discover -> Search -> Save -> Plan -> Optimize -> Watch
```

The app must be useful **before a trip exists**. Discovery, search, and saving are first-class. A Trip is one optional destination for ideas, not the entry point.

This v3 north star defines:

- the product layers (Layer 0 trust foundation through Layer 9 Watchtower),
- the discovery-first object model with Travel Idea / Saved Item as the new root,
- staged delivery from current product spine through deal/points/alert intelligence,
- a Wife Wow Readiness Gate that paces the design sprint,
- a single first implementation slice prompt for the discovery-first audit.

Everything inside AI Concierge place search continues to follow the v2 amendment: latency, verified cards, no visible fallback notes, reviewer gates, set-level writer, card roles, quality certification.

## 2. Why this update exists

Three signals forced this update:

1. **Wife feedback.** PK's wife used the app and reacted with "do we need to create a trip for everything?" That is a structural product signal, not a UI bug. The current trip-first flow makes users feel they must commit to a trip before they can search, save, or explore.
2. **Travel scope is infinite** unless layered. Flights, hotels, restaurants, attractions, neighborhoods, road-trip stops, deals, points, and alerts cannot all live inside an itinerary screen without overwhelming the user.
3. **Existing semantic-place artifacts are correct but narrower than the full product.** They define how AI Concierge place search must behave. They do not define what the product is when the user has no trip yet, wants to compare ideas, asks "where should we go?", or holds 20k Amex points and wants to know what they can do.

This v3 adds the broader product model and staged roadmap on top of the AI Concierge pillar.

## 3. Relationship to existing artifacts

`artifacts/ai_concierge_semantic_place_intelligence.md` and `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md` govern:

- open natural-language place understanding,
- verified Google-backed addable cards,
- semantic frame extraction, retrieval planner, verified entity layer, semantic ranker,
- evidence dossiers, set-level concierge writer, LLM reviewer gate,
- latency budgets (p50 <= 2.5s, p75 <= 3.0s, p95 <= 4.0s, hard 6.0s),
- 5-7 first-response cards, more-options pool, no visible fallback notes,
- card roles, reviewer-gated visible notes, quality certification.

This v3 artifact governs:

- the product layers above place search,
- discovery-first architecture (search and save before trip exists),
- saved lists / boards as a first-class object,
- AI destination intelligence and luxury-for-less scoring,
- road-trip mode as a first-class planning mode,
- deal intelligence (on-demand then alerted),
- points and transfer intelligence,
- Travel Watchtower / alerts,
- the Wife Wow Readiness Gate and design pause strategy.

Conflict rule:

> If anything in this v3 artifact appears to conflict with the AI Concierge semantic-place artifacts on place-search quality, trust, latency, visible notes, evidence, or addable-card authority, the **semantic-place artifacts win**. v3 only extends; it does not relax those invariants.

## 4. Product north-star statement

> Travel Concierge should feel like a fast, beautiful, opinionated, trustworthy personal travel intelligence app that helps PK and his wife casually discover, save, compare, optimize, and turn the best ideas into beautiful trips.

It should make Google Maps, Kayak, ChatGPT travel chat, and points blogs feel like fragmented support tools rather than the destination. The household opens Travel Concierge to *think about travel*, not only to plan a confirmed trip.

## 5. Core product shift

**From:** trip-first itinerary builder. Users must create a trip to do anything meaningful.

**To:** discovery-first travel intelligence platform. Users open the app, browse, search, and save without commitment. Trips are created when an idea is ready to become real.

Concrete shifts:

- **Travel Idea / Saved Item becomes the root object**, not Trip.
- **Search and save must work before trip creation.** Global Discover/Explore is a first-class surface.
- **Trip becomes a destination for ideas**, not a prerequisite. A Trip is one of several places a Saved Item can land (the others being a Saved List, a Road Trip Route, or simply staying as a loose idea).
- **Action vocabulary becomes uniform across verticals**: every result supports `Save`, `Add to trip`, `Start trip from this`, `Compare`.
- **The home screen is opinionated**, not an empty itinerary list.

## 6. Product layers

The product is defined as nine layers stacked on the trust foundation. Each layer can be shipped in slices and gated by feature flag. No layer compromises a lower layer.

### Layer 0 — Trust foundation
- Google-verified addable cards (semantic-place artifacts own this).
- No mock or sample data leakage.
- No unsupported claims in visible text.
- Latency discipline (p50/p75/p95 budgets from v2 amendment).
- No visible fallback notes.
- Stable auth, account, and trip state.

### Layer 1 — Discover without a trip
- Global Explore/Discover surface as default home for "no active trip" state.
- Search bar that works without a trip selected.
- Category entry points (flights, hotels, restaurants, attractions, neighborhoods, road trips, deals, points).
- Recent searches and recently viewed ideas.
- Destination idea cards seeded from preferences and editorial collections.

### Layer 2 — Saved lists / boards
- Save any result (place, flight, hotel, destination, road trip, deal).
- List/board organization with user-defined names ("warm winter ideas", "anniversary trip shortlist").
- Tags and freeform notes per item.
- States per item: `maybe`, `favorite`, `rejected`, `booked`.
- "Add saved item to trip" and "Create trip from saved list" actions.

### Layer 3 — Search verticals
- Flights (price-and-route exploration, not booking).
- Hotels (with verified card discipline).
- Restaurants (AI Concierge place search, governed by v2 amendment).
- Attractions and experiences.
- Neighborhoods and areas.
- Road-trip stops along a route.
- Shared actions across verticals: `save`, `compare`, `add to trip`, `start trip`.

### Layer 4 — Trip planning
- Committed itinerary view.
- Add saved ideas to trip days.
- Route and map planning across days.
- Flights and hotels attached to trip.
- Item state per day: `maybe`, `booked`, `confirmed`.

### Layer 5 — AI destination intelligence
- "Where should we go?" entry point.
- Filter dimensions: domestic vs international, warm vs cold, trip length, flight effort, hotel cost signal, vibe (lively, quiet, foodie, design, outdoors), luxury-for-less score.
- Destination cards have actions: `save`, `search flights/hotels`, `start trip`.
- Reasoning is grounded in available evidence and follows AI Concierge note rules (no name/category-decoding prose, no fabricated claims).

### Layer 6 — Road trip mode
- Route-based planning as a first-class mode (not a degraded itinerary).
- Start, end, and optional loop points.
- Drive-time constraints per leg (max hours per day, preferred stop cadence).
- Scenic stops, restaurants, hotels, and attractions along the route.
- Convert a route directly into a multi-day trip.

### Layer 7 — Deal intelligence
- On-demand cheap flight / deal search.
- Saved-destination deal scan.
- Hotel value signals (cash and points where data permits).
- Hidden opportunity cards (e.g. cheap warm Caribbean week, off-peak Europe).
- No noisy alerts in this layer; alerts arrive in Layer 9.

### Layer 8 — Points and transfer intelligence
- Points wallet with manual entry first (Amex MR, Chase UR, Capital One Miles, Citi TYP, others later).
- Transfer partner directory.
- Transfer ratios and current transfer bonuses.
- "What can 20k Amex points do?" advisor: realistic redemptions, both flights and hotels.
- Good-use vs weak-use labels with short evidence.
- Transfer caution rules (transfers are usually irreversible; only transfer with a target booking confirmed).

### Layer 9 — Travel Watchtower / alerts
- Flight fare alerts on saved routes / saved destinations.
- Hotel price alerts.
- Transfer bonus alerts.
- Saved-destination opportunity alerts (deal or points window opens).
- Alerts must be **rare, high-signal, explainable, and email-first** before they ever become push notifications.
- Each alert is a short claim plus a one-tap action: snooze, ignore, save, search, start trip.

## 7. Core object model

This is conceptual. Database schema is intentionally not designed here.

| Object | Purpose | Lifecycle | Key conversion actions |
|---|---|---|---|
| `Travel Idea` | Loose user-expressed travel intent ("Italy in fall", "warm in February"). | Created from Discover/search/AI; can be saved, refined, abandoned, converted. | Save, refine into Destination Idea, start trip. |
| `Destination Idea` | A specific destination concept with optional preferences. | Created from AI destination intelligence or user input. | Save, search flights/hotels, start trip. |
| `Search Result` | Provider-backed candidate (place, flight, hotel, attraction, route stop). | Ephemeral unless saved. | Save, add to trip, compare, start trip. |
| `Saved Item` | Persistent user-owned reference to any result or idea. | Long-lived; can be moved between lists, rejected, or converted. | Add to list, add to trip, archive, convert. |
| `Saved List / Board` | Named collection of Saved Items with optional notes/tags. | Long-lived; user-managed. | Create trip from list, share (later), archive. |
| `Trip` | Committed itinerary shell with dates, days, and attached items. | Created from a Saved Item, list, AI destination, or empty. | Add saved item, attach flight/hotel, mark booked. |
| `Itinerary Day` | One day inside a trip with ordered items. | Lives inside a Trip. | Add item, reorder, mark item booked. |
| `Flight Candidate` | Provider-sourced flight option with price/route signal. | Ephemeral unless saved or attached to trip. | Save, attach to trip, set fare alert (later). |
| `Hotel Candidate` | Provider-sourced hotel option with verified identity where possible. | Ephemeral unless saved or attached to trip. | Save, attach to trip, set price alert (later). |
| `Verified Place` | Google-verified place identity (governed by semantic-place artifacts). | Canonical and reusable across cards. | Save, add to trip, surface in concierge results. |
| `Road Trip Route` | Start/end/loop with constraints and stops. | Long-lived; can be saved or converted to trip. | Save, convert to trip, add stop. |
| `Road Trip Stop` | Candidate stop along a route. | Lives inside a Route. | Save, add to trip day, swap. |
| `Deal Signal` | An evidence-backed deal observation (cheap fare, hotel value, points window). | Time-bounded; expires. | Save destination, search, set alert (later). |
| `Points Wallet` | User's points balances per program. | Long-lived; manually entered first. | Query "what can these do?", set transfer-bonus alert (later). |
| `Transfer Opportunity` | A specific transfer path/bonus with evidence and caution. | Time-bounded. | Show realistic redemptions, save, alert (later). |
| `Alert / Watchtower Trigger` | A rule that watches a Saved Item, route, or wallet for a high-signal event. | User-managed; snoozable. | Snooze, ignore, action (search/save/start trip). |

Lifecycle principle: **anything ephemeral can become a Saved Item with one action, and any Saved Item can become a Trip.** That two-step ladder is the spine of the product.

## 8. User journeys

Concise, not exhaustive. Each is a target experience, not a current state.

**A. Casual discovery before a trip exists.**
Open app -> Discover surface -> browse categories or run a free-text search -> save 4-5 ideas to "warm winter" list -> close the app. No trip created.

**B. AI destination recommendation.**
Tap "Where should we go?" -> answer 3-4 quick prompts (length, warm/cold, flight effort, vibe) -> see 6 destination cards with role badges and luxury-for-less scoring -> save two, search flights for one, start a trip from another.

**C. Saved list to trip.**
Open "Anniversary shortlist" -> select 4 items -> tap "Create trip from these" -> dates picker -> trip is created with the items pre-assigned to days, ready for refinement.

**D. Road trip.**
Enter "Denver to Santa Fe over 3 days" -> system proposes route with scenic stops, restaurants, hotels along the corridor -> save route -> convert to a 3-day trip with daily anchors.

**E. Deal search.**
Ask "cheap warm Caribbean week in February" -> see 5 deal signals with evidence and price context -> save the most appealing destination -> later (Layer 9) get an email when the fare reopens.

**F. Points question.**
Type "I have 20k Amex points" -> get a small set of realistic redemptions split into "flights" and "hotels", with good-use vs weak-use labels and a transfer-caution note -> save one to revisit -> later set a transfer-bonus alert.

**G. Wife-wow first session.**
Open app -> beautiful Discover home with curated destination ideas, recent searches, saved lists, and a clear "Where should we go?" entry point -> run one search and save two results without creating a trip -> immediately feel that the app is useful, fast, and premium.

## 9. Good ideas, risky ideas, and do-not-build-yet

**Strong near and mid-term (build):**
- Global search without a trip.
- Saved lists / boards.
- AI destination cards with luxury-for-less scoring.
- Road-trip mode.
- Search verticals with shared action vocabulary.
- Create trip from saved list.

**Valuable but later (build after Wife Wow):**
- Deal notifications.
- Transfer bonus notifications.
- Hotel price alerts.
- Points wallet.
- Travel Watchtower with rule UI.
- Email/calendar import.
- Light social/import (e.g. import a friend's shared list) once trust and quality are proven.

**Avoid for now:**
- Auto-booking flights or hotels.
- Public social network or community feed.
- Scraping-heavy infrastructure as a primary data source.
- Adding many providers before core UX stabilizes.
- Push notifications before alert relevance is proven via email.
- Trying to become a full Expedia or Kayak replacement.
- Dashboards / admin tools for power-user subset before household value is proven.

## 10. Staged roadmap

Each stage has an explicit gate. A stage does not start until the gate of the previous stage is satisfied. Stages can be implemented as multiple coherent slices, but no stage is mixed with the next.

### Stage 1 — Stabilize current product spine
Gate to enter: nothing; this is the current state.
Exit gate: no catastrophic failures in core flows; no mock/sample leakage; trip shell stable; AI Concierge returns trusted cards; verified cards render, add, and save reliably; flights and hotels are not embarrassing.

### Stage 2 — Open app before trip exists
Exit gate: Global Discover/Explore is the default home when no trip is active; search works without trip; category entry points exist; `save`, `add to trip`, `create trip` actions present everywhere relevant.

### Stage 3 — Saved lists / boards
Exit gate: any result type can be saved; lists are named, tagged, annotated; "create trip from list" and "add saved item to trip" both work; saved-state survives session and device.

### Stage 4 — AI destination intelligence
Exit gate: destination recommendation cards exist with preference filters; luxury-for-less scoring is computed and explainable; destination -> search/trip conversion paths work; reasoning follows AI Concierge note rules.

### Stage 5 — Road trip mode
Exit gate: route-based search returns stop candidates with drive-time constraints; routes can be saved and converted to trips.

### Stage 6 — Wife Wow Design Sprint
Gate to enter: Stages 1-5 complete and the Wife Wow Readiness Gate (Section 11) is satisfied.
Exit gate: premium design system live across home, Discover, Saved, Trip, Concierge; no ugly state pass; mobile-first polish; motion and premium feel land; first-session "wow" reaction is achievable.

### Stage 7 — Deal intelligence
Exit gate: on-demand deal search works; saved-destination deal scan returns useful results; hotel value signals exist; opportunity cards are evidence-grounded.

### Stage 8 — Points intelligence
Exit gate: points wallet captures balances; transfer partner search works; transfer ratios and active bonuses surface; "what can these points do?" advisor gives realistic, labeled redemptions with caution.

### Stage 9 — Travel Watchtower
Exit gate: alerts are rare, explainable, email-first; rule creation and snooze/ignore/action work; alert quality logged and certified before push is enabled.

## 11. Wife Wow Readiness Gate

Before the design sprint (Stage 6), all of the following must be true:

- App is useful without a trip (Stage 2 done).
- Discover surface works and feels alive.
- Saved lists work end-to-end.
- Trip creation, add-to-day, and convert-from-list work.
- AI Concierge returns trusted cards under v2 amendment rules.
- At least one or two search verticals are usable end-to-end (recommended: restaurants and one of flights/hotels).
- No mock/sample data leakage anywhere visible.
- No embarrassing fallback text in visible notes (`fallback_note_visible_count == 0`).
- No broken account/auth flows.
- Latency is within v2 amendment budgets on key flows.
- Mobile experience is usable (not necessarily pretty yet).

Explicit pacing rule:

> Travel scope is endless. Do not wait for every possible feature (deals, points, alerts, road trips polished, social) before the design sprint. Pause when the **core habit loop** is stable enough that the wife reaches for the app voluntarily.

If three of the readiness items are still red after Stage 5, fix only those three. Do not start Stage 6 design with red items.

## 12. Architecture principles

These guide every product decision in v3. They sit on top of, and do not weaken, the AI Concierge architecture invariants.

1. **Discovery-first, not trip-first.** Default surfaces work without a trip.
2. **Everything saveable.** Any result, idea, route, or deal can become a Saved Item with one action.
3. **Trip as conversion, not prerequisite.** Trip creation is an outcome of saved interest, not the entry point.
4. **Google Places remains canonical for addable places.** Yelp, Foursquare, Tavily, Brave, Serper, and editorial sources are evidence only and never mint addable cards.
5. **Enrichment is evidence, not authority.** Deal/points/editorial claims need freshness and source-awareness; they cannot fabricate verified facts.
6. **Alerts must be rare and explainable.** No alert without a one-line claim and a one-tap action.
7. **UI must remain premium and intuitive.** No surface degrades trust, speed, or aesthetic clarity.
8. **No layer relaxes a lower layer.** Adding deal/points/alerts may not erode trust, latency, or addable-card discipline.
9. **Backend-first contracts.** Cards and actions are stable backend contracts; UI consumes additive optional fields.
10. **Hard separation between addability and reasoning.** Addable identity = Google. Reasoning = many sources within budget and gated by reviewer.

## 13. Implementation strategy

Use **Level 2 coherent product slices**. Avoid huge chaotic PRs that mix verticals, alerts, and design.

Suggested first implementation slices, in order:

1. **Product architecture audit against current app navigation and data model** (docs-only).
2. **Global Explore shell without trip** (default home + category entry points + free-text search routing).
3. **Unified result action model** (`save`, `add to trip`, `create trip`) across verticals.
4. **Saved Lists foundation** (object model, basic UI, persistence, item states).
5. **Create trip from saved list** (conversion path with day assignment).
6. **AI destination recommendation architecture** (object model, ranker inputs, reasoning rules).
7. **Road-trip planning architecture** (route object, stop candidates, drive-time constraints, conversion).
8. **Wife Wow Design Sprint planning artifact** (separate companion doc when the gate is met).

Likely reviewer agents per slice (read-only, before PR summary):

- Slice 1: `contract-auditor`, `pr-reviewer`, `workflow-retrospective-reviewer`.
- Slice 2: `contract-auditor`, `place-authority-reviewer`, `pr-reviewer`, `test-strategist`.
- Slice 3: `contract-auditor`, `place-authority-reviewer`, `pr-reviewer`, `test-strategist`.
- Slice 4: `contract-auditor`, `pr-reviewer`, `test-strategist`.
- Slice 5: `contract-auditor`, `pr-reviewer`, `test-strategist`, `latency-reviewer`.
- Slice 6: `contract-auditor`, `evidence-prose-reviewer`, `place-authority-reviewer`, `pr-reviewer`, `test-strategist`.
- Slice 7: `contract-auditor`, `place-authority-reviewer`, `pr-reviewer`, `test-strategist`, `latency-reviewer`.
- Slice 8: `pr-reviewer`, `workflow-retrospective-reviewer`.

Per-slice rules:

- One PR opens, one PR closes; do not stack two slices in a single PR.
- Every slice carries a feature flag if it changes user-visible behavior.
- Every slice is gated by the relevant readiness item from Section 11 when applicable.

## 14. Current roadmap alignment

How v3 coexists with the work already in flight:

- **AI Concierge semantic work continues** as Layer 0/1 trust foundation. v2 amendment PRs (#256-#264) remain in their declared sequence and own latency, evidence, reviewer, and certification.
- **Flights and hotels cleanup** continues as part of Stage 1 (search vertical stabilization).
- **Product-surface cleanup** (mock/sample leakage removal, account/auth stability) remains Stage 1.
- **Global Explore and Saved Lists** become the next product-model shift after Stage 1 exit conditions are met.
- **Design sprint waits** for the Wife Wow Readiness Gate. Small UI fixes are acceptable in the meantime; major redesign is not.
- **Deal/points/alert layers** are explicitly post-design. They depend on a stable, premium, low-friction product spine.

## 15. First implementation prompt

Use this prompt only after this v3 artifact is merged. Do not run prompts for later stages from this document; future stages get their own prompts at their own time.

Model: Claude Sonnet.
Chat strategy: new focused chat.
Usage estimate: Low to Medium (audit only).
UI budget: None; docs-only PR if any artifact is added.
Severity classification: Level 2 (product audit + plan).

```text
You are working in repo prashanthkrishnan91/claude_travelapp_pk91.

Task: Travel product architecture audit for the discovery-first shift.

Severity classification: Level 2 — product architecture audit and short implementation plan. No runtime changes in this task.

Read first (smallest needed subset):
- artifacts/travel_concierge_product_north_star_v3.md (this north star)
- artifacts/ai_concierge_semantic_place_intelligence.md
- artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md
- docs/ai/HANDOFF.md
- docs/ai/AI_REPO_OPERATING_SYSTEM.md
- docs/ai/EXECUTION_PRINCIPLES.md
- docs/ai/ISSUE_SEVERITY_ROUTING.md
- README.md only if needed for setup context

Use OS v3 with these focused skills:
- task-planner
- contract-audit
- workflow-retrospective if a workflow miss is detected

Delegate conceptually to read-only reviewer agents before PR summary:
- contract-auditor
- pr-reviewer
- workflow-retrospective-reviewer

Goal:
Audit the current app's navigation, trip-first assumptions, data contracts, search entry points, saved/favorites behavior, and itinerary add flows. Then produce a short, focused implementation plan for the Global Explore + Saved Lists foundation (Stage 2 + Stage 3 in the v3 north star).

Required audit outputs (in the audit doc or PR description):
1. Where the current app forces trip-first behavior (entry points, default home, missing-trip empty states).
2. Existing object model summary (Trip, Itinerary Day, place/card contracts, any saved/favorite primitive that already exists).
3. Existing search entry points and how they route when no trip is active.
4. Action vocabulary inconsistencies across verticals (save vs favorite vs add vs nothing).
5. Auth/account state assumptions that block discovery before a trip exists.
6. Latency and trust risks in the proposed shift (must respect AI Concierge v2 amendment budgets).
7. Place authority risk assessment (Google remains canonical for addable cards under all proposed changes).

Required plan outputs (separate section in the audit doc or PR description):
- Slice 2: Global Explore shell without trip — proposed scope, files likely touched, contract changes (additive only), feature-flag name, acceptance criteria.
- Slice 3: Unified result action model — same shape.
- Slice 4: Saved Lists foundation — same shape, including a conceptual object model for Saved Item / Saved List.
- Explicit non-goals for these three slices (no deals, no points, no alerts, no road trip, no AI destination, no design sprint).

Constraints:
- Do not write runtime code in this task. This is audit + plan only.
- Do not create SQL.
- Do not modify Vercel settings.
- Do not change provider/API code.
- Do not edit AI Concierge place-search artifacts; they remain the binding pillar.
- If any audit finding requires breaking the AI Concierge v2 amendment invariants, stop and report a split plan instead.
- Keep the audit doc concise; it is a planning artifact, not a code reference manual.

Output:
Open one focused PR titled: `product-audit: discovery-first shift — Global Explore + Saved Lists foundation plan`.
The PR adds a single new docs artifact (e.g. `artifacts/travel_product_audit_discovery_first.md`) with the audit and the slice plan.
Do not bundle implementation slices into this PR.

Stop after PR summary. Do not propose the next implementation prompt.

Final response format:
Severity classification: Level 2
Root cause/plan:
Files changed:
Tests: docs-only, no runtime tests required; explain why this tier is sufficient
Risks:
Supabase SQL: No
HANDOFF.md edited: Yes/No + reason
README.md edited: Yes/No + reason
```

---

## Appendix A — What v3 explicitly does not change

- AI Concierge place-search latency, evidence, note, reviewer, and certification rules from the v2 amendment.
- Google-canonical addability rule.
- The AI Concierge PR sequence (#256-#264 in the v2 amendment) and its certification gate.
- The repo's OS v2/v3 workflow, severity routing, test routing, claim-safety gate, and PR template.

## Appendix B — Glossary

- **Travel Idea**: a loose user-expressed travel intent before any concrete destination or dates.
- **Saved Item**: a persistent, user-owned reference to any result or idea; the new product root object.
- **Saved List / Board**: a named collection of Saved Items.
- **Trip**: a committed itinerary shell; one of several conversion targets for a Saved Item.
- **Verified Place**: a Google-verified place identity with `place_id`, OPERATIONAL status, and Maps URI.
- **Card role**: a curated label assigned to a result inside a final ranked set (e.g. `best_overall`, `best_atmosphere`, `caveat_pick`); defined in the AI Concierge v2 amendment.
- **Wife Wow Readiness Gate**: the explicit list of preconditions that must be true before the major design sprint begins.
- **Travel Watchtower**: the alert layer (Layer 9) that watches Saved Items, routes, and wallets for high-signal events.
