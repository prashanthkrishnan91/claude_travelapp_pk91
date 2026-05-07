Use `.claude/skills/ai-repo-os/SKILL.md` claim-safety gate.

Travel checks:
- Google Places remains canonical for addable cards.
- Enrichment cannot mint cards.
- Unsupported place claims are blocked or hidden.
- Source-name-only evidence cannot become visible filler.
- Internal diagnostics/raw evidence cannot reach UI/prose.

Fail if internal-only data can reach user-visible UI or LLM-visible prose without policy.
