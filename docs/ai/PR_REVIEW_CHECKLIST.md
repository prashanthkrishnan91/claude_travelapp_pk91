# PR Review Checklist — Travel Concierge

Use this checklist before merge and inside `/pre-pr-self-audit`.

## Required checks

- Severity classification: Level 0/1/2/3 with reason.
- Root cause vs symptom: explain why the fix addresses the cause.
- Downstream contract audit: changed outputs, consumers, behavior changes, files intentionally not changed.
- Test coverage audit: smallest sufficient suite plus one adversarial invariant test or rationale.
- Latency/runtime audit: required for providers, fanout, LLM calls, DB calls, caches, or route behavior.
- Data trust / claim safety audit: source authority, evidence sufficiency, unsupported-claim prevention.
- UI leakage audit: no diagnostics, raw evidence, source-name-only facts, or internal labels in visible UI/prose.
- SQL/migration audit: Supabase SQL yes/no and manual action yes/no.
- Env var audit: new/changed env vars yes/no; default and rollback behavior.
- Feature flag/rollback audit: flag or safe rollback path for risky changes.
- PR summary accuracy: do not overclaim; list tests actually run and known limitations.

## OS v3 self-learning checks

- Did the prompt/task use OS v2/v3 work-order format?
- Did Claude use required focused skills?
- Did Claude delegate to applicable read-only reviewer agents?
- Did the PR include a workflow retrospective when required?
- If there was a miss, was it recorded in `docs/ai/MISS_LEDGER.md`?
- Is the proposed workflow update precise or bloated? Reject broad rule changes from a single isolated miss.
- Did the PR classify deployment/build impact when relevant?
- Did the PR avoid file-by-file commit churn for bulk workflow/docs edits?

## Do not merge if

- Google verification can be bypassed for addable cards.
- Enrichment sources can mint cards.
- Internal diagnostics or raw evidence can leak to UI/prose.
- Route latency claim is supported only by local timeout tests.
- A shared contract changed without consumer tests or explicit rationale.
- PR summary hides SQL/env/provider/LLM/runtime impact.
- The implementation is a symptom patch after repeated related failures.
- The PR proposes broad OS rule changes from a single isolated miss without ledger evidence.
