# Claim Safety Gate Skill

Use when user-visible text, cards, actions, evidence, or LLM-visible prose changes.

Return:
- visible/user-facing claims affected
- evidence source for each risky claim
- unsupported claims blocked or hidden
- internal diagnostics/raw evidence leakage check
- source-name-only filler check

Travel-specific checks:
- Google Places remains canonical for addable cards.
- Enrichment sources cannot mint cards.
- Visible notes are evidence-grounded, LLM-written under claim safety, or hidden.
- No deterministic fallback visible notes.
- Source names alone cannot become visible prose.

Fail if internal-only data can reach UI or LLM-visible prose without policy.
