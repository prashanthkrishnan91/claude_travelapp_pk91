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
- `docs/ai/AGENT_ROUTER.md`
- `docs/ai/AGENT_INTAKE_REGISTRY.md`
- `docs/ai/AGENT_EFFECTIVENESS_LEDGER.md`
- `docs/ai/PROMPT_ENGINEERING_STANDARD.md`
- `docs/ai/TOOL_FAILURE_TAXONOMY.md`

## Required Product OS docs (OS v4)

- `docs/product/NORTH_STAR.md`
- `docs/product/ROADMAP.md`
- `docs/product/BUILD_QUEUE.md`
- `docs/product/IDEA_INBOX.md`
- `docs/product/DECISION_LOG.md`
- `docs/product/RELEASE_GATES.md`
- `docs/product/PRODUCT_HEALTH.md`
- `docs/product/DO_NOT_BUILD_YET.md`
- `docs/product/PROGRESS_REPORT_TEMPLATE.md`
- `docs/product/FEATURE_SLICE_CONTRACT.md`
- `docs/product/GOLDEN_SCENARIOS.md`

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
- `prompt-intake`
- `roadmap-check`
- `idea-triage`
- `build-queue-update`
- `progress-report`
- `product-retrospective`
- `feature-contract`
- `golden-scenarios`
- `prompt-lint`
- `tool-failure-triage`

## Required agents

- `contract-auditor`
- `test-strategist`
- `pr-reviewer`
- `workflow-retrospective-reviewer`
- `roadmap-guardian`
- `prompt-intake-reviewer`
- `agent-curator`
- `prompt-quality-reviewer`
- `eval-scenario-reviewer`
- Certification pack: `reality-checker`, `evidence-collector`, `premium-delight-reviewer`, `accessibility-reviewer`, `performance-benchmarker`
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
- `/prompt-intake`
- `/roadmap-check`
- `/idea-triage`
- `/progress-report`
- `/build-queue-update`

## Optional / future

- advisory hooks
- evidence MCP integrations
- hard-blocking hooks only after explicit approval

## Audit rule

If a future repo lacks one required OS or Product OS component, add it before scaling AI-driven feature work.
