# Claude Hooks Roadmap — Travel Concierge

Wave 1 does not enable hooks. This roadmap documents future advisory hooks so automation can increase without creating brittle blockers.

## Principles

- Start advisory, not blocking.
- Hook messages should remind Claude which skill/command to run.
- Do not add paid CI, secrets, or expensive runtime calls.
- Keep judgment-heavy decisions in Claude/ChatGPT review, not shell scripts.

## Candidate advisory hooks

| Trigger | Advisory message |
|---|---|
| Provider/fanout/enrichment files changed | Run `/latency-gate`; prove local timeout and total route impact. |
| Evidence dossier/writer/claim files changed | Run `/claim-safety-gate`; audit writer-visible facts and UI leakage. |
| API response/mapping files changed | Run `/contract-audit`; list producer/consumer contract changes. |
| Frontend concierge card files changed | Run `/contract-audit`; verify visible fields/actions and no diagnostics leakage. |
| Migration/Supabase files changed | Fill SQL/manual action fields in PR template. |
| Docs-only task edits runtime files | Warn and require explicit rationale. |
| Stop event without PR template summary | Remind to run `/pre-pr-self-audit` and `/pr-summary`. |

## Future implementation note

Implement hooks only after this OS is used in real PRs and the highest-value reminders are clear.
