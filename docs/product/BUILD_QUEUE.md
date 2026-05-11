# Build Queue

The active product queue. Every meaningful implementation PR should map to one item here.

Update via `.claude/skills/build-queue-update/SKILL.md` after meaningful roadmap decisions or merged PRs. Keep updates concise.

## Now

- **Stage 2A Slice 3 — Trip-Optional AI Concierge:** backend accepts optional `trip_id`; Concierge usable from Explore shell. Unblocks Attractions vertical.

## Next

- Saved lists foundation (Stage 3 entry).

## Completed

- Stage 2A Slice 2 — Unified Result Actions v1 + saved_items foundation: `saved_items` migration (005), `SavedItemsService`, `/saved-items` route (POST/GET/DELETE), `ResultActionSheet` (Save live; Add to Trip / Create Trip deferred), wired into `RestaurantExploreFlow`. (2026-05-11)
- Stage 2A Slice 1 — Global Explore Shell v1: `/explore` route, 4-vertical entry grid, Restaurants live (Google Places), Attractions/Hotels/Flights deferred with polished states, `ExploreResultContext` action-ready type, nav links in Sidebar + MobileNav. (2026-05-11)
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
