# AI OS Manifest — Travel Concierge

A portable checklist for future repos and for auditing whether the OS is fully installed.

## Required entrypoints

- `AGENTS.md`
- `CLAUDE.md`
- `docs/ai/AI_REPO_OPERATING_SYSTEM.md`

## Required workflow docs

- `docs/ai/KNOWN_FAILURE_MODES.md`
- `docs/ai/TEST_SELECTOR.md`
- `docs/ai/PR_REVIEW_CHECKLIST.md`
- `docs/ai/DEFINITION_OF_DONE.md`
- `docs/ai/CONTEXT_MANAGEMENT.md`
- `docs/ai/FAILURE_RECOVERY.md`
- `docs/ai/RUNTIME_EVIDENCE.md`
- `docs/ai/MANUAL_ACTIONS_CHECKLIST.md`
- `docs/ai/PROMPT_BRIEF_TEMPLATE.md`
- `docs/ai/OS_LEARNING_PROTOCOL.md`
- `docs/ai/MISS_LEDGER.md`
- `docs/ai/WORKFLOW_RETROSPECTIVE.md`
- `docs/ai/HOOK_SAFETY.md`
- `docs/ai/PERMISSIONS_AND_MEMORY_BOUNDARIES.md`

## Required skills

- `ai-repo-os`
- `task-planner`
- `contract-audit`
- `test-selector`
- `runtime-gate`
- `claim-safety-gate`
- `pre-pr-self-audit`
- `pr-summary`
- `failure-recovery`
- `workflow-retrospective`
- `miss-ledger-update`

## Required agents

- `contract-auditor`
- `test-strategist`
- `pr-reviewer`
- `workflow-retrospective-reviewer`
- Travel-specific reviewers: `place-authority-reviewer`, `latency-reviewer`, `evidence-prose-reviewer`

## Required command aliases

- `/test-selector`
- `/contract-audit`
- `/latency-gate`
- `/claim-safety-gate`
- `/pre-pr-self-audit`
- `/pr-summary`
- `/update-handoff`
- `/workflow-retrospective`
- `/miss-ledger-update`

## Optional / future

- advisory hooks
- evidence MCP integrations
- hard-blocking hooks only after explicit approval

## Audit rule

If a future repo lacks one required OS component, add it before scaling AI-driven feature work.
