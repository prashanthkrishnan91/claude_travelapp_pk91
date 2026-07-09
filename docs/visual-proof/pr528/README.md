# PR #528 visual proof — AI Route Planning v1 PR C (reorder-proposal apply contract)

**The component shown here is currently inert in the shipped app.** `ReorderProposalPreview` is
wired into `ItineraryDayColumn.tsx` with a hardcoded `proposal={null}` — no proposal generator
exists in this PR (per the ADR, the apply contract must exist and be proven safe *before* any
suggestion source is added). These screenshots are **not** from the live app; they come from a
temporary, uncommitted local harness that mounted the real `ReorderProposalPreview` component with
a fixture proposal (`{currentOrder: [a,b,c], proposedOrder: [c,a,b]}`, three sample stop titles) at
an `/auth/*`-prefixed route to bypass the app's auth-redirect shell — real component code, real
Tailwind design tokens, not a synthetic mockup. The harness itself was not committed (deleted after
capture); only the resulting screenshots are checked in here as evidence.

No live Supabase-backed backend was available in this sandbox, so the "confirm" click in these
captures hits an unreachable `localhost:8000` apply endpoint and resolves to the fail-closed error
state shown in `3-confirm-error-no-write.png` — this still proves the fail-closed contract (no
silent success, honest error copy, no partial state implied). The actual write-path correctness
(ownership, item-set equality, stale-order rejection, atomic-via-rollback partial-write handling)
is proven by the 18 backend contract tests in `backend/tests/test_route_reorder_proposal.py`, not
by this harness.

## Screenshots

1. `1-preview-before-after.png` — before/after preview: "Current order" and "Proposed order" shown
   side by side, with "Nothing changes until you confirm. This only reorders the stops shown
   below." copy, and Cancel / "Apply this order" actions.
2. `3-confirm-error-no-write.png` — after clicking "Apply this order" against an unreachable
   backend: fail-closed error copy ("This order couldn't be applied. Nothing changed."), preview
   still shown, no silent success.
3. `4-cancel-dismissed-no-change.png` — after clicking "Cancel": the preview is dismissed locally,
   no network call was made (cancel never calls the apply helper — see
   `frontend/tests/reorder-proposal-apply.test.mjs`).
4. `5-mobile-narrow.png` — same before/after preview at a 375px mobile viewport.
