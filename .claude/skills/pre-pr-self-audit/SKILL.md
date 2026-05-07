# Pre-PR Self-Audit Skill

Use before opening or updating a PR.

Return:
- assumptions and success criteria
- every success criterion mapped to file/function/test/evidence
- contract/runtime/claim gates run or rationale
- limitations and out-of-scope
- manual actions checklist
- HANDOFF/README update decision

Fail the self-audit if:
- downstream consumers are not checked for changed contracts
- runtime/latency gate is skipped for provider/request-path changes
- claim-safety gate is skipped for visible text/data/evidence changes
- PR summary would overclaim evidence not actually proven
