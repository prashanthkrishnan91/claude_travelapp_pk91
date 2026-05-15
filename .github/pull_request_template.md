<!-- FORMAT COMPLIANCE: Keep all `## SectionName` headers exactly as written below.
     The CI readiness gate checks for exact substrings (`## Severity`, `## Validation`, etc.).
     Using `**SectionName:**` bold inline instead of `## SectionName` headers will fail the gate. -->

## Summary

## Severity
- Level: 0 / 1 / 2 / 3
- Reason:

## Root cause / task reason

## Files changed
- 

## Validation
- Commands/checks run:
- Test tier used + why sufficient:

### Runtime validation (only when relevant)
- 

## Product behavior changed
- Yes/No:
- User-visible impact:

## SQL / env / providers / UI
- Supabase SQL required (Yes/No + manual action):
- Env vars required (Yes/No + manual action):
- New providers or new LLM calls (Yes/No + details):
- UI changed (Yes/No + details):

### Screenshots / UI validation (only when relevant)
- 

## Risks / limitations

### Follow-up required (only when relevant)
- 

## AI usage note
Run `bash scripts/ai/usage_snapshot.sh --pr <number> --prompt-id <id> --phase <phase> --model <model>` before opening a PR.

**Usage note:** Low/Medium/High; source: ccusage/statusline/manual/unavailable; main drivers: [fill]; justified: yes/partially/no; next efficiency improvement: [fill]

## AI PR readiness
- [ ] Ran `python3 scripts/workflow/ai_pr_readiness_check.py --pr-body-file /tmp/body.txt --base-ref origin/main` locally before pushing
- Readiness check: pass / pass-with-known-gaps / not run
- Usage ledger row: committed / not required — [Level 0 docs-only reason] / blocked — [why tooling failed, do not merge Level 1+]
- Prompt ID / phase:
- Model:
- Chat strategy: new-chat / same-chat
- Main token drivers:
- Waste classification: none / preventable-follow-up / necessary-follow-up / exploration / unknown
- Follow-up count:
- Scope drift: none / explained
- Runtime/design validation note if relevant:

## Self-audit
- Repository PR template used exactly: Yes/No
- Scope stayed within requested files/behavior: Yes/No
- Downstream consumers reviewed (if relevant): Yes/No
