# Claude Subagents Roadmap — Travel Concierge

Wave 1 does not add reviewer subagents. Add them only after skills/commands prove useful and repeated review work is clearly separable.

## Principles

- Prefer skills/commands first.
- Reviewer subagents should be mostly read-only.
- Subagents should return concise evidence, not rewrite code by default.
- Use subagents to protect main chat context during exploration/review.

## Candidate subagents

| Subagent | Purpose | Default tools |
|---|---|---|
| contract-auditor | Find changed contracts, consumers, and missed connected files. | read/search/test only |
| latency-reviewer | Review provider/fanout/LLM/cache/db route budget risks. | read/search/test only |
| claim-safety-reviewer | Check unsupported claims, writer-visible evidence, diagnostics leakage. | read/search/test only |
| test-strategist | Map changed areas to smallest sufficient tests and adversarial cases. | read/search/test only |
| pr-reviewer | Compare PR diff against OS checklist before merge. | read/search/test only |

## Add subagents when

- The same audit appears in three or more PRs.
- Main Claude context becomes bloated with exploration.
- A review task is separable from implementation.
- ChatGPT repeatedly catches the same class of miss after self-audit.
