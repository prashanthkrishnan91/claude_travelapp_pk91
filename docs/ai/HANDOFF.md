# HANDOFF — current state only

## Active work
- Cluster 2 context-tax reduction (SETUP_AUDIT.md) is the current workflow slice, branch
  `claude/context-tax-reduction-cluster-2-65e2xb`, PR #536.
- No product implementation PR is open.
- AI Route Planning v1 shipped in PR #533.
- Claude Code workflow Cluster 1 shipped in PR #535.
- Next step: review/merge of PR #536.

## Blocked / waiting on user
- AI Route Planning v1's user-facing flow requires all of `AI_ROUTE_REORDER_PROPOSAL_V1_ENABLED`,
  `ROUTE_REORDER_PROPOSAL_V1_ENABLED`, `ROUTE_ESTIMATE_V1_ENABLED`, `ANTHROPIC_API_KEY`,
  `GOOGLE_ROUTES_API_KEY`. Current runtime state of these flags/keys is not verified in this
  session — do not assume enabled or disabled without checking Railway/Vercel env directly.
- No other known open manual action.

## Landmines
- One PR at a time.
- No merge recommendation without semantic audit.
- No UI merge without visual proof.
- No runtime/provider claims without runtime evidence.
- Avoid duplicate route-planning diagnostics/buttons — `RouteQualityDiagnosticNote` and
  `DayFlowReview` were deliberately removed from the itinerary UI (PR #532) for reading as
  internal/debug tooling.
- Existing inline Google Routes connectors remain the canonical travel-time display.
- Check `SETUP_AUDIT.md` before changing workflow infrastructure.
- Use `ship-pr` when opening a PR.

## Recently merged
- #535 — Claude Code workflow Cluster 1: added `ship-pr` skill for single-pass PR packaging.
- #534 — Merged root-level `SETUP_AUDIT.md` workflow audit.
- #533 — AI Route Planning v1: LLM-proposed day reorder verified by Google Routes, with
  fixed-time-anchor and day-part-boundary enforcement.
