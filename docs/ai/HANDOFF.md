# HANDOFF — current state only

## Active work
- Workflow-only slice: SETUP_AUDIT Cluster 3 — replaced `.claude/skills/failure-recovery/SKILL.md`
  with a frontmatter'd skill that operationalizes the two-failure stop rule, added
  `docs/ai/DEAD_ENDS.md` (durable Travel dead-end registry), a CLAUDE.md Core rule tying the
  two into the existing patch-exhaustion rule, and a `certify_v4_1.py` structural contract
  check. Branch `claude/setup-audit-cluster-3-travel-90k08o`.
- #539 merged (open-PR sweep semantic fix: concurrent blockers must all be reported, not one
  state). The 12-hour Travel PR Sweep Routine is now active and permanently reporting-only —
  it never makes GitHub mutations without an explicit later user request.
- No other product implementation PR is open.
- Next step: review/merge of this PR, then SETUP_AUDIT Clusters 4, 6, 7 remain available.

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
- At the second related failure, run `failure-recovery` before any third patch; check
  `docs/ai/DEAD_ENDS.md` before investigating a provider, data source, or previously tried
  approach.
- Avoid duplicate route-planning diagnostics/buttons — `RouteQualityDiagnosticNote` and
  `DayFlowReview` were deliberately removed from the itinerary UI (PR #532) for reading as
  internal/debug tooling.
- Existing inline Google Routes connectors remain the canonical travel-time display.
- Check `SETUP_AUDIT.md` before changing workflow infrastructure.
- Use `ship-pr` when opening a PR.

## Recently merged
- #539 — open-PR sweep semantic fix: report every concurrent blocker, not a single state.
- #535 — Claude Code workflow Cluster 1: added `ship-pr` skill for single-pass PR packaging.
- #534 — Merged root-level `SETUP_AUDIT.md` workflow audit.
