# Contract Audit Skill

Use before PR summary whenever outputs, payloads, routes, UI data, provider evidence, persistence contracts, or shared functions change.

Return:
- changed outputs/contracts
- downstream consumers
- behavior changes
- files intentionally not changed
- tests or rationale proving safety

Travel-specific checks:
- addable card identity remains Google Places canonical
- enrichment sources cannot mint cards
- AI Concierge card fields remain aligned: `display.displayWhy`, `supportingDetails.whyPick`, top-level `whyPick`
- typed backend payloads normalize before frontend card mapping

Fail if downstream consumers are not checked.
