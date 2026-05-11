# Build Queue

The active product queue. Every meaningful implementation PR should map to one item here.

Update via `.claude/skills/build-queue-update/SKILL.md` after meaningful roadmap decisions or merged PRs. Keep updates concise.

## Now

- **Stage 2A Slice 1 — Global Explore Shell v1:** Add `/explore` route + nav link. Destination search + vertical filters. Real Google Places results. No trip required. See `docs/product/STAGE_2A_CONTRACT.md`.
- **Stage 2A Slice 2 — Unified Result Actions v1:** `ResultActionSheet` component with Save / Add to Trip / Create Trip. Trip-optional save path. Wire into Explore shell and `SearchResultCard`.

## Next

- Stage 2A Slice 3 — Trip-Optional AI Concierge: backend accepts optional `trip_id`; Concierge usable from Explore shell.
- Saved lists foundation (Stage 3 entry).

## Completed

- Stage 1 → Stage 2 transition: discovery-first architecture audit + Stage 2A contract. See `docs/product/STAGE_2A_CONTRACT.md`. (2026-05-11)

## Later

- AI destination intelligence.
- Road-trip mode.
- Deal intelligence.
- Points intelligence.
- Travel Watchtower.

## Blocked

- _none recorded_

## Validation Needed

- _none recorded_

## Design Pause Candidates

- Wife Wow Design Sprint after Discover + Saved + core trip flows are stable.

## Do Not Build Yet

See `docs/product/DO_NOT_BUILD_YET.md`. Highlights:

- auto-booking
- noisy alerts
- scraping-heavy deal infrastructure
- public social/community features
- full design sprint before Wife Wow Readiness Gate
