# Travel Concierge V4 — Travel OS Addendum

Date: 2026-05-10
Repo: `prashanthkrishnan91/claude_travelapp_pk91`
Status: Architecture / product / roadmap source of truth. Docs-only. No runtime code, SQL, providers, or UI behavior changes.
Severity classification: Level 3 — comprehensive product architecture, source-of-truth roadmap, and execution sequencing.

Companion to (binding):
- `artifacts/ai_concierge_semantic_place_intelligence.md`
- `artifacts/ai_concierge_semantic_place_intelligence_v2_amendment.md`
- `artifacts/travel_concierge_product_north_star_v3.md`

V4 extends V3 and supersedes V3 only where V3 is too shallow for the full Travel OS goal. V4 never relaxes the semantic-place invariants. If anything in this artifact appears to conflict with the AI Concierge semantic-place artifacts on place-search trust, latency, evidence, addable-card authority, visible notes, reviewer gates, first-response card count, or more-options pool behavior, the semantic-place artifacts win.

---

## 1. Executive Summary

Travel Concierge is a premium personal household Travel OS that owns the full travel lifecycle:

```text
Dream -> Capture -> Verify -> Compare -> Decide -> Plan -> Book externally -> Track -> Execute day-of -> Remember -> Learn
```

The app owns research, verification, comparison, decisioning, trip planning, tracking, and memory. External sites remain source, checkout, reservation, navigation, or final-detail-verification endpoints — not research destinations. PK's wife should research and plan inside Travel Concierge, then leave the app only when she is ready to book, reserve, navigate, or verify final details.

The product moat is not generic AI itinerary generation. The moat is **verified decision intelligence across the full travel lifecycle** — fast verified place identity, evidence-grounded judgment, source-classified reasoning, persona fit, itinerary feasibility, and operational certainty — delivered as a coherent household product, not a chat box.

V4 transforms the product framing from "AI itinerary/search tool" into "personal household Travel OS with verified decision intelligence." It is execution-ready, not a wishlist. Every roadmap item attaches to the lifecycle and the object model.

## 2. Relationship to Existing Artifacts

- **AI Concierge semantic-place artifacts (binding for the place-search core).** They govern open natural-language place understanding, the verified Google-backed addable card spine, evidence dossiers, set-level concierge writer, the LLM reviewer gate, latency budgets (p50 ≤ 2.5s, p75 ≤ 3.0s, p95 ≤ 4.0s, hard cutoff ≤ 6.0s), 5–7 first-response cards, more-options pool, no visible fallback notes, role badges, and quality certification. V4 does not reinterpret any of this.
- **V3 product north star (still valid).** V3 introduced discovery-first product direction, the Travel Idea / Saved Item root, saved lists/boards, the discovery-first object model, the staged Layer 0–9 model, and the Wife Wow Readiness Gate. V4 keeps all of this and extends it.
- **V4 supersedes V3 where V3 is shallow:** universal capture from social/web/screenshots/email, decision intelligence as a first-class product surface, source credibility and anti-hype reasoning, dynamic itinerary modification, hotel/dining deep intelligence, dedicated travel-ops (day-of) layer, household collaboration, controlled external-link launchers, watchtower discipline, personalization brain, certifications, and an ordered execution sequence.
- **Conflict rule.** V3 governed the broad product direction; V4 is the broader Travel OS source of truth from this PR onward. **Semantic-place invariants always win.** V4 must never weaken them.

## 3. Market / Research Lessons Incorporated

A concise synthesis of competitive-product signals that shape the architecture. These are inputs, not blueprints.

- **Expedia Trip Matching.** Inspiration → AI itinerary → booking handoff is a real flow. Inspiration cannot be the only entry; verification and comparison must happen inside the app.
- **Triply / Roamy / ReelTrip-style import.** Users actively want to push Instagram/TikTok/YouTube/Maps lists/screenshots into a single planning surface that maps and routes them. Capture is a first-class pillar, not a side feature.
- **Booking.com AI (Smart Filters, Property Q&A, review summaries).** AI can dramatically reduce hotel/restaurant search friction by answering specific questions over reviews and inventory data. We do not need to own inventory to own the question-answering layer.
- **Wanderlog.** Itinerary + map + collaboration + route optimization + reservations + offline access is a sticky combination. Multi-modal stickiness comes from end-to-end ownership of planning, not from any single feature.
- **TripIt.** Operational certainty (confirmation parsing, calendar, offline details, terminal/gate, reservation organization) is a real moat. Day-of execution should not require a second app.
- **Roadtrippers.** Route-first discovery is a distinct planning mode. Stops along a corridor with drive-time constraints are not a degraded itinerary.
- **Points/deal tools (AwardWallet, ExpertFlyer, Going, MaxRewards, etc.).** Transfer bonuses, award availability, hotel rebook alerts, cashback portal awareness, and fee/term scrutiny are part of comprehensive travel planning — but they are noisy and easy to spam users with. Async, snapshot, watchlist-first.
- **Travel-planning research.** Itinerary quality requires temporal feasibility, spatial feasibility, ordering, persona fit, and modification capability. Generated itineraries that ignore opening hours, drive times, or spouse preferences feel toy-like.

Lesson: own the reasoning and decision layer. Use providers for inventory/availability/identity. Use external sites only for checkout/navigation/final verification.

## 4. Non-Negotiable Product Invariants

These hold across every phase, every PR, and every layer.

1. No fake cards anywhere visible.
2. No social/editorial/blog/LLM/reddit/screenshot source can mint addable place cards.
3. Google Places remains canonical for addable place identity (governed by semantic-place artifacts).
4. Experience/product/tour cards have a separate product-card contract from place cards. Product availability never mixes into Google place identity.
5. Flights, hotels, deals, points, alerts, award availability, and other slow/volatile data are async/snapshot/watchlist-first when they cannot meet the synchronous Concierge search budget.
6. Slow providers must not degrade AI Concierge search latency. Critical path stays Google + cache + verified entity layer + reviewer.
7. User-visible recommendations are plain-English, evidence-grounded, comparative, and decision-useful — never literal name/category/address decoding and never raw provider mess.
8. External links are controlled exits with a stated reason and what to verify there. They are not research rabbit holes.
9. No auto-booking, auto-payment, auto-transfer, refund handling, or charge handling until an explicit, gated later phase. V4 does not authorize any of these.
10. Alerts must be rare, high-signal, explainable, snoozable, and email-first before push.
11. No internal diagnostics, raw provider payloads, or debug strings in user-facing UI.
12. No orphan features. Every feature attaches to (a) the lifecycle in §5 and (b) at least one core object in §7.
13. Reviewer-gated visible notes (semantic-place rule) apply to every place-card surface.
14. No visible fallback prose anywhere in the place-search surface (`fallback_note_visible_count == 0`).
15. The synchronous Concierge search path is sacred. Async work cannot encroach on its budget.

## 5. Travel OS Lifecycle

Eleven steps. Every product surface, object, and PR must trace to at least one step.

### A. Dream
- **User job:** "Where could we go?", "What sounds appealing?", "What if we had a long weekend in February?"
- **System responsibility:** Surface destination ideas, vibes, and seeds without requiring a trip; respect persona signals when available.
- **Primary objects:** `Travel Idea`, `Destination Idea`, `Saved List`.
- **Example UX:** Discover home with curated destination cards, "Where should we go?" entry, recently saved ideas.
- **Should NOT happen:** force trip creation; show fake/generic dream copy; auto-add to a trip; mix dream prompts into the synchronous Concierge place-search surface.

### B. Capture
- **User job:** "Save this reel/screenshot/article/maps list/forwarded email so I do not lose it."
- **System responsibility:** Accept any inbound, extract candidates, verify identity before addability, dedupe, and route to Saved/Trip/Inbox.
- **Primary objects:** `Inspiration Item`, `Source`, `Claim`, `Saved Item` (after verification), `Verified Place`.
- **Example UX:** Inspiration Inbox with paste/share-extension flow, status chips (`candidate`, `verified`, `needs_review`, `rejected`, `duplicate`, `stale`).
- **Should NOT happen:** mint addable cards from social/blog content; treat source claims as facts; show influencer hype as endorsement; dedupe across users.

### C. Verify
- **User job:** "Is this real, current, open, and the place the source meant?"
- **System responsibility:** Resolve to Google place id with OPERATIONAL status and Maps URI for places; resolve to provider inventory for products/hotels/flights; classify source credibility; set `verification_state`.
- **Primary objects:** `Verified Place`, `Hotel Candidate`, `Flight Candidate`, `Experience/Product Candidate`, `Source`, `Claim`, `Evidence`.
- **Example UX:** Candidate card with verification badge, "Matched on Google", links to Maps for sanity check, "Needs review" state when ambiguous.
- **Should NOT happen:** auto-verify ambiguous candidates without user confirmation; carry social/editorial claims as verified facts.

### D. Compare
- **User job:** "Which of these should we choose?"
- **System responsibility:** Side-by-side comparison across places, hotels, flights, and experiences with shared decision dimensions and honest tradeoffs.
- **Primary objects:** `Saved Item`, `Verified Place`, `Hotel Candidate`, `Flight Candidate`, `Decision`.
- **Example UX:** Compare drawer over a Saved List or shortlist; pairwise tradeoffs; persona-fit notes.
- **Should NOT happen:** invent dimensions; compare unverified candidates as if they were peers; bury caveats.

### E. Decide
- **User job:** "Pick this. Skip that. Watch the third."
- **System responsibility:** Decision Cockpit that produces a recommendation, confidence, evidence summary, alternatives, and an external action link.
- **Primary objects:** `Decision`, `Saved Item`, `Trip`, `Watch Rule`.
- **Example UX:** Decision Cockpit page per object with `choose / shortlist / monitor / skip / verify manually`.
- **Should NOT happen:** make the decision for the user; spam confidence scores without evidence; obscure the catch.

### F. Plan
- **User job:** "Build a feasible plan we will actually use."
- **System responsibility:** Day-by-day itinerary that respects opening hours, meal timing, drive/walk times, ordering, ordering caveats, and locked items.
- **Primary objects:** `Trip`, `Itinerary Day`, `Saved Item`, `Verified Place`, `Reservation`.
- **Example UX:** Trip view with map + day stack; feasibility certification; modification commands.
- **Should NOT happen:** regenerate the whole trip on minor edits; ignore locks; produce backtracking schedules without warning.

### G. Book externally
- **User job:** "Now I will pay/reserve."
- **System responsibility:** Send the user to the right external endpoint with one-tap context and what to verify there. Track booked state on return.
- **Primary objects:** `Booking Link`, `Reservation`, `Saved Item`, `Trip`.
- **Example UX:** External-Link Launcher (§15) with reason, target, and "Mark as booked" return.
- **Should NOT happen:** capture payment in-app; auto-book; mask which site the user is going to; hide affiliate context.

### H. Track
- **User job:** "Watch for better fares, awards, weather, deadlines."
- **System responsibility:** Watchtower (§16) maintains rare, explainable, snoozable, email-first alerts.
- **Primary objects:** `Watch Rule`, `Alert`, `Reservation`, `Saved Item`.
- **Example UX:** Watchtower list with one-line claims and one-tap actions; quiet by default.
- **Should NOT happen:** noisy push notifications; alerts without evidence; alerts after the cancellation deadline.

### I. Execute day-of
- **User job:** "What now? What next? Where do I go? What do I have?"
- **System responsibility:** Travel Ops layer (§13): today timeline, leave-by reminders, terminal/gate, weather impact, reservation confirmations, offline snapshot.
- **Primary objects:** `Reservation`, `Itinerary Day`, `Trip`, `Alert`.
- **Example UX:** Today screen with the next anchor and a clean "go to" action.
- **Should NOT happen:** require Wi-Fi to view today's plan; show stale data; force a search to find a confirmation.

### J. Remember
- **User job:** "What did we love? Where did we eat? Save this for next time."
- **System responsibility:** Capture trip memories and feedback without creating a public feed.
- **Primary objects:** `Memory`, `Feedback`, `Saved Item`.
- **Example UX:** Trip recap with starred items, notes, photo references (no upload requirement v1).
- **Should NOT happen:** publish memories anywhere; lose the link from memory back to original Saved Item.

### K. Learn
- **User job:** none directly; the system improves persona fit silently.
- **System responsibility:** Personalization brain (§17) ingests selection/rejection/booking/loved/skipped signals to bias future recommendations.
- **Primary objects:** `Preference`, `Feedback`, `Memory`.
- **Example UX:** "Why this fits her" reason on future recommendations.
- **Should NOT happen:** silently retrain on noisy signals; use signals across users; surface internal preference scores.

## 6. Universal Capture / Inspiration Inbox

Capture is a top-tier pillar. The wife should be able to throw anything at the app and have it land safely.

### Inputs
- Instagram, TikTok, YouTube, Reels links (URL paste or share-sheet).
- Blog/article links and editorial roundups.
- Reddit threads.
- Google Maps links and Maps lists.
- Screenshots (photo upload).
- Notes / free-text.
- Hotel, flight, activity URLs.
- Deal-alert emails or copied text.
- Confirmation PDFs / screenshots / emails (later phases).

### Processing
- Extract entities and place candidates, hotels, flights, experiences, deals, claims, dates, prices, source context, vibes.
- Generate candidate objects.
- Verify candidate identity before addability (places → Google; products → product inventory; hotels/flights → provider).
- Dedupe against existing Saved Items and trip items.
- Persist `Source` and `Claim` records linked to each candidate.
- Mark `verification_state`: `candidate`, `verified`, `needs_review`, `rejected`, `duplicate`, `stale`.

### Rules
- Social/blog/reddit/screenshot content can create candidates only — never addable cards.
- Google verification is required to mint an addable place card.
- Product/experience cards need separate inventory/product verification.
- Source claims are stored as `Claim` records with credibility class, not promoted to facts.
- The Inbox does not auto-add anything to a trip.

## 7. Travel Knowledge Graph

The conceptual graph that all surfaces share. Schema design is intentionally not done here.

```text
User / Household
  -> Preferences
  -> Travel Ideas
  -> Saved Lists
  -> Saved Items
  -> Trips
       -> Itinerary Days
            -> Areas / Neighborhoods
                 -> Places (Verified Place)
                 -> Experiences / Products
                 -> Hotels (Hotel Candidate / Reservation)
                 -> Flights (Flight Candidate / Reservation)
                 -> Reservations
  -> Sources
  -> Claims
  -> Evidence
  -> Booking Links
  -> Watch Rules
  -> Memories / Feedback
```

### Object responsibilities

| Object | Purpose | Source of truth | Lifecycle | Key actions | Verification |
|---|---|---|---|---|---|
| `User / Household` | Identity unit. Two travelers + future kids; shared planning. | Auth provider | Long-lived | invite, share, leave | n/a |
| `Preference` | Persona signals (cuisine, vibe, walking tolerance, hotel style, points/cash). | Implicit + explicit user input | Long-lived | learn, edit, reset | n/a |
| `Travel Idea` | Loose intent ("Italy in fall"). | User | Created → refined → converted/abandoned | save, refine, start trip | n/a |
| `Saved List / Board` | Named collection of Saved Items. | User | Long-lived | create, rename, archive, share (later) | n/a |
| `Saved Item` | Persistent reference to any verified candidate or idea. | User | Long-lived | move, tag, state-change, convert to trip item | inherits from underlying object |
| `Inspiration Item` | Raw inbound inbox entity (URL, screenshot, note). | User | Inbox-lived → resolved | classify, extract, route, dismiss | none until candidates verify |
| `Source` | Originating reference (URL, screenshot, app, email). | System | Long-lived | view, classify, expire | classified credibility |
| `Claim` | Source-attributed assertion ("amazing tapas", "free breakfast"). | System | Lives with candidate | display contextually, never as fact | source credibility |
| `Evidence` | Structured/computed fact backing a recommendation. | System | Lives with candidate | feed reasoner / reviewer | typed and bounded |
| `Verified Place` | Google-canonical addable place identity. | Google | Long-lived (TTL refresh) | save, add to trip, surface in Concierge | governed by semantic-place artifacts |
| `Experience / Product` | Tour/ticket/class/food-tour candidate. | Product provider (later) | Time-bounded inventory | save, add to trip, book externally | provider-backed only |
| `Hotel Candidate` | Provider-sourced lodging option. | Hotel provider | Snapshot-lived | save, attach to trip, watch | provider + identity |
| `Flight Candidate` | Provider-sourced flight option. | Flight provider | Snapshot-lived | save, attach to trip, watch | provider |
| `Trip` | Committed itinerary shell. | User | Long-lived (post-trip stays for memory) | create, extend, archive | n/a |
| `Itinerary Day` | One day with ordered items. | User + system | Lives in Trip | reorder, lock, modify | feasibility-certified |
| `Area / Neighborhood` | Geographic anchor for clustering. | Computed | Stable | filter, route, "near here" queries | computed only |
| `Reservation` | Confirmation-backed booking record. | User-supplied confirmation | Bound to Trip | import, edit, share | confirmation parsing later |
| `Booking Link` | Controlled external action endpoint. | System | Stateless | open, return-mark | none |
| `Watch Rule` | User-configured monitor (price, fare, award, weather, deadline). | User | Long-lived | snooze, edit, delete | rule-bound |
| `Alert` | One emitted Watch event with claim + action. | System | Short-lived | act, snooze, dismiss | evidence-bounded |
| `Memory / Feedback` | Post-event note about an item ("loved", "too touristy"). | User | Long-lived | view, edit, feed personalization | n/a |
| `Decision` | Recorded choice on an object (choose/shortlist/monitor/skip). | User + system reason | Long-lived per object | revisit, change | none |

### The graph must support
- "Where did this recommendation come from?" → `Saved Item → Source / Claim`.
- "Why did we reject this?" → `Decision (skip) + reason_code`.
- "What is near our hotel?" → `Trip → Area → Verified Place` proximity.
- "Which saved reel had this place?" → `Inspiration Item → Saved Item → Verified Place`.
- "Which items are unverified?" → `Saved Item.verification_state ∈ {candidate, needs_review}`.
- "What can we swap if it rains?" → Day-level `RAINY_DAY_SWAP` over Saved Items tagged `weather_dependent`.
- "What did my wife like last time?" → `Memory + Feedback` joined to `Preference`.

## 8. Decision Cockpit

The single surface that answers "should we do/book this?" for every travel object. This is the moat.

For every place / hotel / flight / experience / deal / destination, the cockpit must answer:

- Should we do/book this?
- Why this over alternatives?
- What is the catch?
- Is it verified, current, open, nearby, bookable, worth it?
- Does it fit PK and wife preferences?
- What should we do next?
- Which external link should we use, and why?

### Decision outputs

```text
recommendation     ∈ {choose, shortlist, monitor, skip, verify_manually}
best_for           one-line persona/use fit
tradeoffs          short list of honest caveats
confidence         strong | mixed | weak
evidence_summary   brief, sourced
source_credibility classified (see §9)
alternatives       2–3 named options with reason for swap
external_action    one controlled link with reason and what to verify
```

Rules:
- Decisions show only after verification gates pass.
- Reasoning follows semantic-place evidence rules; no literal name/category decoding; no unsupported claims.
- The cockpit can refuse a decision and emit `verify_manually` with a clear next step. That is correct behavior.
- Decisions are persisted (`Decision` object) so future surfaces can reference and learn from them.

The app owns the decision layer even when external sites own checkout.

## 9. Source Credibility and Anti-Hype Engine

Credibility is a first-class signal. Every visible reason ties back to one or more sources whose class is known.

### Source classes

```text
verified_operational_fact      Google place id / OPERATIONAL / hours / status
provider_inventory_fact        provider availability, price, terms
expert_editorial               curated editorial / known expert / official guide
crowd_consensus                aggregated reviews (Google/Yelp/Foursquare themes)
social_hype                    Instagram/TikTok/Reels with high view count, low signal
personal_saved                 the user's own past saved/loved item
paid_affiliate_risk            marketing copy, affiliate listicle, sponsored post
stale_source                   data older than freshness threshold for class
conflicting_evidence           multiple sources disagree
unverified_claim               claim without supporting evidence
```

### Influence

| Class | Ranking | Visible copy | Decision confidence | Addable / bookable? |
|---|---|---|---|---|
| verified_operational_fact | strong | yes | strong | required for addable place |
| provider_inventory_fact | strong | yes | strong | required for hotel/flight/product |
| expert_editorial | medium | yes (cited) | strong if corroborated | no minting |
| crowd_consensus | medium | yes (theme summary, not counts) | medium | no minting |
| social_hype | small / negative if unsupported | warn | weak | no minting |
| personal_saved | medium boost | yes | medium | reuses underlying object |
| paid_affiliate_risk | small / suppress | warn | weak | no minting |
| stale_source | suppress unless flagged | warn or hide | weak | no |
| conflicting_evidence | reduce | "evidence is mixed" | mixed | depends |
| unverified_claim | suppress | hide | n/a | no |

### Example visible warnings
- "Viral, but reviews suggest long waits and inconsistent food."
- "Strong local/editorial support, not just influencer hype."
- "Photogenic, but weak evidence that it fits a quiet date-night ask."
- "Good cash deal; poor points redemption."
- "Sources disagree on whether breakfast is included; verify on hotel direct site before booking."

The anti-hype engine never invents skepticism. It states evidence honestly.

## 10. Domain Intelligence Layers

These are distinct intelligence modules sharing the object model. Each has a different verification spine and a different freshness profile. None of them weakens the synchronous Concierge place-search path.

### A. Place Intelligence
- Governed by `ai_concierge_semantic_place_intelligence.md` and the v2 amendment. V4 does not modify it.
- Verified Google-backed addable cards, semantic frame extraction, retrieval planner, evidence dossiers, set-level writer, reviewer gate, role badges, latency budgets, more-options pool.
- All other intelligence layers must respect Place Intelligence as the canonical place spine.

### B. Dining Intelligence
- Signature dishes (claim-classed, never invented).
- Reservation availability and deep links (Resy/OpenTable/Yelp Reservations).
- Vibe / noise / crowd theme extraction from review evidence.
- Date-night fit, dress code, dietary fit, lunch vs dinner use.
- Tourist-trap risk flag (chain/popularity/affiliate/social-hype-only).
- "Worth crossing town for?" comparative answer.
- Backup nearby suggestions if unavailable.

### C. Hotel Intelligence
- Location fit to itinerary anchors and saved items.
- Fees: resort, parking, destination, mandatory.
- Cancellation window and policy clarity.
- Room quality themes, quietness, bed/bathroom concerns.
- Pool/breakfast/lounge/amenities reality (theme summary, not provider marketing copy).
- Cash vs points vs portal vs direct rate honesty.
- Family vs couple fit.
- Should-we-book-now / monitor / skip recommendation tied to a Watch Rule.

### D. Flight Intelligence
- Route quality, airline reputation, connection risk.
- Price quality vs route history.
- Luggage/seat/ancillary caveats; basic-economy traps.
- Direct vs connection tradeoff with a clear recommendation.
- Booking timing and monitoring guidance.
- "Attach to trip", "watch for better fare", or "skip" outputs.

### E. Experience / Product Intelligence
- Separate product-card contract from place cards.
- Viator / GetYourGuide / Klook-class products in later phases.
- Tickets, tours, classes, food tours, day trips.
- Availability, cancellation, meeting point, duration, language, accessibility.
- Product availability never mixes into Google place identity.

### F. Destination Intelligence
- "Where should we go?" entry with persona-aware filters: domestic/international, warm/cold, trip length, flight effort, lodging cost signal, vibe, luxury-for-less, safety, season fit.
- Destination cards have actions: save, search flights/hotels, start trip.
- Reasoning grounded in available evidence, no fabricated facts (semantic-place note rules apply).

### G. Points / Deals / Coupons Intelligence
- Transfer bonuses (current + historical pattern).
- Award availability surfaces (read-only, snapshot).
- Hotel award alerts.
- Cash vs points comparative analysis.
- Coupon / cashback portal awareness (Rakuten / TopCashback / etc.).
- Amex/Chase/Citi/Capital One offer awareness — manual entry first, no scraping or login automation.
- Hidden-deal signals (price-vs-history, off-peak windows).
- Hotel rebook opportunities before free-cancellation deadline.
- All async / snapshot / watchlist; never on the Concierge synchronous path.

## 11. Spatial Trip Brain

Map-first reasoning, not just pins.

### Capabilities
- Neighborhood clustering of Saved Items and Day items.
- Route feasibility per day and across days.
- Backtracking detection and warning.
- "Near hotel", "between two anchors", "one perfect afternoon".
- Route-by-day optimization with locked items respected.
- "Where should we stay based on saved places?"
- "What saved items are too far out?"
- "What belongs on the same day?"
- Drive/walk-time warnings tied to opening hours.

### Rules
- Use Google Routes / provider routing first. Do not self-host routing infrastructure until provider limits or pricing justify it.
- Cache route snapshots per day; refresh on item changes.
- Spatial intelligence is async and snapshot-based when possible. It must not block synchronous Concierge search.

## 12. Itinerary Feasibility and Modification Engine

A trip is not feasible just because it has items. It must be certifiable and modifiable without full regeneration.

### Certification metrics
- Meal timing feasibility (breakfast/lunch/dinner spacing and venue type fit).
- Attraction opening-hours feasibility per item.
- Route / travel-time feasibility per leg.
- Ordering score (logical sequence by neighborhood, energy, meal anchors).
- Backtracking score.
- Overpacked-day score.
- Buffer score (cushion between items).
- Weather risk for outdoor items.
- Persona / preference fit per day.
- Booking / reservation dependency checks (do reservations align with the day order?).

### Modification commands

```text
ADD            insert an item with feasibility check
DELETE         remove an item; repair downstream
REPLACE        swap one item for another with similar role
MOVE           change day/time; repair routing and ordering
COMPARE        side-by-side feasibility of two candidates
LOCK           pin an item; future ops must respect it
UNLOCK         release a pin
RELAX_DAY      reduce density, redistribute
OPTIMIZE_ROUTE re-order today by route while respecting locks/anchors
ADD_BACKUP    attach a backup item to handle weather/closure
RAINY_DAY_SWAP swap weather-dependent items for indoor alternates
```

### Required behavior
- Preserve locked items.
- Produce a diff of changes.
- Explain the impact of each change in plain English.
- Avoid full regeneration unless the user explicitly asks.
- Repair downstream route/time issues automatically.

### Example
"Moved Musée d'Orsay to Day 3 because it is closer to dinner and reduces backtracking by 22 minutes. Coffee stop at Café X stays locked. Day 2 now has 35 minutes of buffer."

## 13. Travel Ops / Day-Of Layer

Replaces the need for TripIt-style apps for execution.

### Capabilities
- Confirmation import / upload (PDF, screenshot, copy/paste).
- Email forwarding (later: dedicated forwarding address).
- Flight / hotel / tour / restaurant confirmation parser.
- Calendar export (per trip and per day).
- Offline snapshot of today's plan, reservations, and key links.
- Today timeline: next anchor, time-to-leave, weather impact.
- Outfit/packing hints based on weather + venue dress code.
- Reservation confirmations surfaced where they are needed.
- Maps / ride / transit deep links.
- Opening-hour warnings ("closes in 25 minutes").
- "Leave by" reminders with route lookup.
- Backup if closed/raining.
- Cancellation-deadline reminders.
- Check-in / check-out details.
- Terminal / gate where available.

### Rules
- Day-of must work offline once cached.
- No noisy push notifications. Quiet by default.
- Never invent terminal/gate or address; show "unknown" rather than guess.

## 14. Collaboration / Wife Planning Layer

Two people first, not a public network.

### Capabilities
- Shared household trip board.
- Spouse invite (and later, kids/family).
- Item votes (like, neutral, no, must-do).
- Comments per item.
- States per item: `maybe`, `favorite`, `rejected`, `shortlisted`, `booked`, `executed`.
- "PK likes / wife likes" indicators.
- Decision conflict notes when votes disagree.
- Activity log (who added/edited/voted).
- Permission model (view / suggest / edit) — later phases.

### Rules
- Collaboration is private to the household.
- No public profiles, no follower graph, no activity feed beyond the household.
- Inviting requires explicit confirmation; no email scraping.

## 15. External-Link Launcher

Controlled exits with stated purpose.

### Endpoint classes
- Google Maps navigation.
- Restaurant reservation (Resy / OpenTable / Yelp Reservations / venue direct).
- Hotel direct.
- OTA hotel (Booking / Expedia / etc.).
- Airline checkout.
- Activity booking (Viator / GetYourGuide / venue direct).
- Award search (airline / hotel program).
- Transfer partner (issuer transfer page).
- Cashback / coupon portal.
- Original source (article / reel / map list / blog).
- Verification link (Maps URI for sanity check).

### For every external link, the app shows
- **Why this link** — one sentence.
- **What to do there** — two or three specific steps.
- **What to verify before booking** — fees, dates, room type, fare class, cancellation, etc.
- **Whether to return and mark booked / confirmed** — "Mark as booked when done" CTA on return.

External sites become action endpoints, not research destinations.

## 16. Watchtower / Alerts

Disciplined alerting. Quiet by default.

### Alert types
- Hotel price drop before cancellation deadline.
- Flight fare drop on a saved/booked route.
- Award availability opens.
- Transfer bonus makes a saved redemption better.
- Restaurant reservation window opens.
- Attraction ticket window opens.
- Weather impacts an outdoor plan.
- Booked place appears closed (status change, news signal).
- Cancellation deadline tomorrow.
- Itinerary overpacked or infeasible after edits.
- Check-in opens.

### Alert rules
- Rare. High signal. Explainable.
- Snoozable per rule and globally per trip.
- Email-first. Push only after email-quality is proven and explicitly enabled.
- Each alert includes one recommended action (search, switch, rebook, watch, dismiss).
- No alert fires without backing evidence and a stated source class.
- Alerts after the actionable window (e.g., past the cancellation deadline) must be suppressed.

## 17. Personalization / Wife Preference Brain

Quiet, evidence-based personalization. No public scoring, no opaque ML magic.

### Signals (per user, per household)
- Saved, rejected, booked, skipped.
- Loved, too touristy, too crowded, too expensive, too far.
- Liked vibe, would return.
- Hotel style preference.
- Cuisine preferences and aversions.
- Walking tolerance.
- Pace preference (relaxed / packed).
- Points vs cash preference.

### Rules
- Signals stay within the household.
- The brain biases ranking and reasoning; it never silently drops candidates a user might still want.
- Every personalized recommendation should eventually be able to answer "Why this fits her" with explicit signals.
- Personalization comes after the core habit loop is stable; do not start before Phase 5+.

## 18. Product Surfaces / Navigation Model

Eventual app surfaces. Each has a specific job.

| Surface | Purpose | Primary objects | Key actions | Do NOT include |
|---|---|---|---|---|
| Home / Command Center | One-tap entry to whatever matters now | Trip, Today, Saved Lists, Watchtower | resume trip, today, search, save, "where should we go?" | empty itinerary list as default; mocked data |
| Discover | Browse, search, dream | Travel Idea, Destination Idea, Saved List | search, save, start trip | non-verified addable cards |
| Inspiration Inbox | Capture and triage | Inspiration Item, Source, Claim | classify, verify, route | auto-add to trip |
| Saved | Long-term library | Saved Item, Saved List | tag, organize, compare, convert to trip | mixing trip-only items |
| Trips | Plan, modify, execute | Trip, Itinerary Day, Reservation | add, lock, modify, optimize, view today | live provider mess in UI |
| Map | Spatial reasoning | Trip, Area, Verified Place | cluster, route, "near hotel" | self-routed paths before provider justified |
| Concierge | Conversational place search | Verified Place, Evidence Dossier | search, follow up, more options | slow async layers on critical path |
| Deals / Watchtower | Async opportunities | Watch Rule, Alert, Hotel/Flight Candidate | snooze, act, dismiss | noisy push; non-actionable alerts |
| Points Wallet | Manual balances + advisor | Preference, Watch Rule | edit balance, "what can these do?" | scraping, login automation, auto-transfer |
| Today / Day-Of | Execution surface | Itinerary Day, Reservation, Alert | next anchor, leave-by, offline view | requiring connectivity |
| Memories | Post-trip recall and feedback | Memory, Feedback, Saved Item | review, star, note | public feed |

## 19. Execution Roadmap

Staged, dependency-aware roadmap. Each phase has a purpose, dependencies, what to build, what not to build, success gate, likely PR slices, and model routing.

Model routing convention:
- **Opus** — architecture, spec, deep design, large refactors with system-level reasoning.
- **Sonnet** — coherent multi-file implementation slices.
- **Codex** — audits, merge gates, surgical fixes, focused tests.

### Phase 0 — Stabilization / cleanup
- **Purpose:** finish current product spine work; no broken or embarrassing surfaces.
- **Dependencies:** none.
- **Build:** finish AI Concierge v2-amendment sequence (PRs through #264 if not yet shipped); ensure no mock leakage; ensure latency budgets pass certification queries.
- **Do NOT build:** new product surfaces; provider expansions; design overhauls.
- **Success gate:** AI Concierge passes certification §14 of the v2 amendment; `fallback_note_visible_count == 0` in production; flights/hotels are not embarrassing.
- **PR slices:** small focused PRs only.
- **Model:** Codex / Sonnet for surgical fixes.

### Phase 1 — V4 source-of-truth and current-code audit
- **Purpose:** publish V4 (this artifact) and audit the current code/data model against V4's object graph.
- **Dependencies:** Phase 0 complete enough that audit is meaningful.
- **Build:** this artifact (already), then a docs-only audit identifying gaps in object model, surfaces, and contracts.
- **Do NOT build:** any runtime code in this phase.
- **Success gate:** audit artifact landed with concrete gap list and slice plan for Phase 2.
- **PR slices:** 2 docs PRs.
- **Model:** Opus for V4 + audit; Codex for cross-checking references.

### Phase 2 — Universal object/action model
- **Purpose:** establish backend-first contracts for the V4 object graph (Saved Item, Source, Claim, Evidence, Verification State, Decision) without changing user-visible behavior.
- **Dependencies:** Phase 1 audit.
- **Build:** typed contracts and additive optional fields; no UI shift; feature flags off by default.
- **Do NOT build:** Inspiration Inbox UI; decision cockpit UI; collaboration; alerts.
- **Success gate:** contracts merged; existing surfaces unaffected; tests prove backward compatibility.
- **PR slices:** 2–3 backend PRs.
- **Model:** Sonnet implementation; Codex contract audit.

### Phase 3 — Global Discover + Saved foundation
- **Purpose:** V3 Stage 2/3 implementation; app is useful before a trip exists.
- **Dependencies:** Phase 2 contracts.
- **Build:** Discover home, free-text search without trip, unified `save / add to trip / start trip` action vocabulary, Saved Lists with item states.
- **Do NOT build:** Inspiration Inbox; alerts; deals; major redesign.
- **Success gate:** wife can save items without creating a trip; Saved Lists round-trip; discover home does not require a trip.
- **PR slices:** 3–4 PRs (Discover shell, action model, Saved Lists, "create trip from list").
- **Model:** Sonnet; Codex merge gate.

### Phase 4 — Inspiration Inbox v1
- **Purpose:** universal capture from links/text/screenshots into candidates.
- **Dependencies:** Phase 2 (Source/Claim/Verification model) + Phase 3 (Saved foundation).
- **Build:** paste/share a link; extract candidate places; Google verify; route to Saved Items or Trip.
- **Do NOT build:** confirmation parsing; product/experience extraction; alerts; auto-add.
- **Success gate:** wife pastes a Reels link, sees candidates, picks one, it lands as a verified Saved Item with source attribution.
- **PR slices:** 3 PRs (extractor + verify + UI).
- **Model:** Sonnet; Opus for extractor design only if it gets gnarly.

### Phase 5 — Decision Cockpit v1
- **Purpose:** unified decision surface per object.
- **Dependencies:** Phase 2 (Decision/Evidence) + Phase 4 (Source/Claim).
- **Build:** Decision Cockpit page for places first; recommendation, tradeoffs, alternatives, external action link.
- **Do NOT build:** decisions for hotels/flights yet; collaboration; alerts.
- **Success gate:** every Saved Place has a Decision Cockpit answering the §8 questions with reviewer-gated copy.
- **PR slices:** 2 PRs.
- **Model:** Sonnet; Opus for prompt/reviewer design.

### Phase 6 — Itinerary Feasibility Certification
- **Purpose:** make trips feasibility-aware.
- **Dependencies:** Phase 3 (Trips usable end-to-end).
- **Build:** certification metrics §12 surfaced as day-level signals.
- **Do NOT build:** modification engine yet (Phase 7); auto-fixes.
- **Success gate:** every Trip Day shows feasibility signals; tests cover meal timing, opening hours, route, ordering.
- **PR slices:** 2 PRs.
- **Model:** Sonnet.

### Phase 7 — Itinerary Modification Engine v1
- **Purpose:** ADD/DELETE/REPLACE/MOVE/LOCK/COMPARE/OPTIMIZE_ROUTE/ADD_BACKUP/RAINY_DAY_SWAP/RELAX_DAY operations.
- **Dependencies:** Phase 6 (feasibility) + Phase 3 (Trips).
- **Build:** modification commands with diffs and explanations; locks respected; downstream repair.
- **Do NOT build:** full regenerate; multi-trip optimization; automatic alerts.
- **Success gate:** modifying one item produces a diff and feasibility-corrected day without nuking the rest.
- **PR slices:** 3 PRs.
- **Model:** Opus design + Sonnet implementation; Codex merge gate.

### Phase 8 — Spatial Trip Brain v1
- **Purpose:** map-first reasoning over Trips and Saved Items.
- **Dependencies:** Phase 3 + Phase 7.
- **Build:** clustering, route snapshots per day, "near hotel" filters, backtracking warnings; Google Routes only.
- **Do NOT build:** self-hosted routing; live re-routing; off-Google routing.
- **Success gate:** map view shows clusters, drive/walk times, and warnings.
- **PR slices:** 2 PRs.
- **Model:** Sonnet.

### Phase 9 — Hotel/Dining deep intelligence
- **Purpose:** layer-specific intelligence beyond identity.
- **Dependencies:** Phase 5 (Decision Cockpit), Phase 4 (Sources/Claims).
- **Build:** review-theme extraction for restaurants and hotels; date-night/dress-code/quietness signals; cash vs points/portal honesty.
- **Do NOT build:** auto-booking; rate scraping; provider sprawl.
- **Success gate:** Decision Cockpit answers hotel/dining-specific questions with cited evidence.
- **PR slices:** 3 PRs (dining, hotels, prompt review).
- **Model:** Sonnet; Opus for prompt/reviewer design.

### Phase 10 — Travel Ops / confirmation import
- **Purpose:** day-of execution layer.
- **Dependencies:** Phase 3 + Phase 7.
- **Build:** confirmation upload/parse; calendar export; offline snapshot; today timeline; leave-by; reservation surfacing.
- **Do NOT build:** email forwarding (later sub-phase); push notifications; auto-rebook.
- **Success gate:** wife can upload a hotel confirmation PDF and see it inside the trip; today screen works offline.
- **PR slices:** 3 PRs.
- **Model:** Sonnet.

### Phase 11 — Collaboration
- **Purpose:** household planning.
- **Dependencies:** Phase 3 + Phase 5 + Phase 10.
- **Build:** spouse invite, votes, comments, item states, activity log.
- **Do NOT build:** public network; sharing outside household; permissions for non-household.
- **Success gate:** PK + wife can both vote on items and see the activity log.
- **PR slices:** 2 PRs.
- **Model:** Sonnet.

### Phase 12 — Points / deals / coupons intelligence
- **Purpose:** async value layer.
- **Dependencies:** Phase 5 (Decision Cockpit), Phase 10 (Reservations).
- **Build:** manual points wallet, transfer partner directory, cash vs points comparator, hidden-deal detection.
- **Do NOT build:** scraping issuer offers; auto-transfer; auto-rebook; login automation.
- **Success gate:** "what can 20k Amex do?" returns realistic, labeled, evidence-backed redemptions.
- **PR slices:** 3 PRs.
- **Model:** Sonnet; Opus for ranker/comparator spec.

### Phase 13 — Watchtower alerts
- **Purpose:** rare, high-signal alerts.
- **Dependencies:** Phase 12 (deals/points), Phase 10 (Reservations).
- **Build:** Watch Rules, alert rendering, snooze, email-first delivery.
- **Do NOT build:** push; SMS; high-frequency alerts.
- **Success gate:** alert quality certification passes (§21); zero noisy alerts in pilot.
- **PR slices:** 2 PRs.
- **Model:** Sonnet.

### Phase 14 — Memory and personalization
- **Purpose:** learn quietly.
- **Dependencies:** Phase 5 + Phase 10 + Phase 11.
- **Build:** Memory/Feedback objects, preference brain biasing rankings and reasons, "why this fits her" copy.
- **Do NOT build:** cross-household learning; opaque ML scores; public profile.
- **Success gate:** persona-fit reasons appear on at least one intelligence layer with cited signals.
- **PR slices:** 2 PRs.
- **Model:** Sonnet; Opus for signal-model spec.

### Phase 15 — Premium redesign / wife-wow sprint
- **Purpose:** premium polish across the surfaces.
- **Dependencies:** core habit loop stable (Wife Wow Readiness Gate, V3 §11).
- **Build:** design system, motion, premium feel across Home, Discover, Saved, Trip, Concierge, Today, Map.
- **Do NOT build:** new functional surfaces in this phase.
- **Success gate:** first-session "wow" reaction; no regression in any prior phase.
- **PR slices:** design-system PR, then surface-by-surface polish PRs.
- **Model:** Sonnet; Opus for design-system architecture only.

### Sequencing guidance
- Do not jump straight to deals/points/Watchtower before the core Travel OS object model exists (Phase 2).
- Do not build Inspiration Inbox before the candidate/verification/Saved-Item model is clear (Phases 2–3).
- Do not start a major visual redesign until the core habit loop is stable enough to pass the Wife Wow Readiness Gate.
- Do not turn every product idea into an implementation PR. V4 exists to prevent scattered feature drift.
- One PR opens, one PR closes; do not stack two phases in one PR.

## 20. Build Guardrails

Hard rules for every implementation PR.

- No orphan features. Every feature attaches to a lifecycle step (§5) and an object (§7).
- No provider sprawl before contracts and the object model exist.
- No slow live calls on the synchronous Concierge path.
- No UI masking backend weakness. Fix the backend or hide the surface.
- No broad redesign before the core habit loop is stable.
- No scraping-first strategy. Provider-backed first; manual entry second; scraping only with explicit, gated approval.
- No auto-booking, payment, refund, or charge handling in any phase here.
- No public social network or community feed in any phase here.
- No points/deals recommendation without freshness and source-class caution.
- No external content treated as fact without source classification (§9).
- Every implementation PR updates HANDOFF and progress_log lightly.
- Every non-trivial implementation PR must include severity, assumptions, success criteria, tests, risks, and a self-audit (per OS v2/v3).
- The synchronous Concierge place-search path is sacred (semantic-place artifacts).

## 21. Certification Framework

Each suite is a small, focused set of pass/fail scenarios. These are concepts, not test code.

### Place Search Certification (governed by v2 amendment §14)
- Latency budgets: p50 ≤ 2.5s, p75 ≤ 3.0s, p95 ≤ 4.0s, hard cutoff ≤ 6.0s.
- Verified-only addable cards.
- 5–7 first-response cards.
- `fallback_note_visible_count == 0`.
- Reviewer-approved or hidden notes only.

### Inspiration Extraction Certification
- Reels link → at least one extracted candidate.
- Maps list link → all entries become candidates with Google verification gate.
- Screenshot OCR → at least one entity extracted when text is legible; honest "unable to extract" when not.
- No social/blog content mints addable cards.
- Source/Claim records persisted.

### Source Credibility Certification
- Each visible reason cites at least one source with a known class.
- `unverified_claim` and `social_hype` never produce strong-confidence recommendations.
- Stale sources warn or hide per class freshness threshold.
- Conflicting evidence renders honestly ("evidence is mixed").

### Decision Cockpit Certification
- Every saved verified place has a cockpit answering §8 questions.
- `recommendation` ∈ {choose, shortlist, monitor, skip, verify_manually}.
- External action link present with reason and what-to-verify text.
- Reviewer gate applied to visible reasoning copy.

### Itinerary Feasibility Certification
- Meal timing, opening hours, route, ordering, overpacked, buffer, weather risk surfaced per day.
- Locked items respected.
- Booking dependency checks run before showing "feasible".

### Modification Engine Certification
- Every command (§12) preserves locks and produces a diff.
- No full-regenerate side effects.
- Downstream repair is automatic and explained.

### Hotel Intelligence Certification
- Fees, cancellation, room theme, quietness, breakfast/lounge/pool reality surfaced when evidence exists.
- Cash vs points vs portal vs direct comparison honest.
- "Book now / monitor / skip" recommendation tied to a Watch Rule.

### Dining Intelligence Certification
- Vibe / noise / crowd themes surfaced when evidence exists.
- Date-night / dress-code / dietary fit answered when asked.
- Tourist-trap risk flagged when evidence exists.
- Backup nearby suggestion present when reservation is unavailable.

### Travel Ops Certification
- Confirmation upload parses key fields (vendor, dates, confirmation number) when supported.
- Today screen works offline once cached.
- Calendar export round-trips correctly.
- Leave-by reminder uses real route times.

### Watchtower Alert Quality Certification
- Each alert has a one-line claim and one recommended action.
- No alert fires after the actionable window.
- Snooze works at rule and trip levels.
- Email-first; no push without quality cert pass.

### Wife Wow Readiness Gate (V3 §11, extended)
- App is useful before a trip exists.
- Discover home feels alive; no empty itinerary as default.
- Saved Lists work end-to-end.
- AI Concierge passes Place Search Certification.
- At least one or two search verticals usable end-to-end.
- No mock/sample leakage.
- Latency budgets met in production.
- Mobile is usable (premium not required yet).

## 22. Do-Not-Build-Yet List

Explicitly out of scope for now.

- Full direct booking, payment, refund, or charge handling in any flow.
- Public social feed or community network.
- Scraping-heavy infrastructure as a primary data source.
- Self-hosted routing before Google/provider routing limits or cost justify it.
- Push notifications before email alert quality is certified.
- Provider sprawl before contracts and the object model are stable.
- Visual redesign before the core habit loop is stable.
- Auto-transfer or auto-booking of points.
- Login automation or credential storage for issuer offers.
- Anything that weakens verification or slows AI Concierge synchronous search.

## 23. V4 Final North-Star Statement

> Travel Concierge should be the only app PK's wife needs to research, decide, plan, track, and execute travel. External sites are used only as source, checkout, reservation, verification, or navigation endpoints. The app's moat is verified decision intelligence across the full travel lifecycle.

V4 exists so that every future implementation PR — across capture, decision, planning, ops, alerts, points, personalization, and design — attaches to one coherent product and one coherent object model. Build the staged roadmap. Do not chase shiny features. Keep the synchronous Concierge path sacred. Make the wife reach for this app first, every time.
