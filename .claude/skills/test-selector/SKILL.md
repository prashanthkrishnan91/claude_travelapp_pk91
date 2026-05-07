# Test Selector Skill

Use before coding and before PR summary.

Read `docs/ai/TEST_SELECTOR.md`, then return:
- changed areas
- smallest sufficient tests
- downstream consumer tests needed
- one adversarial test for the riskiest invariant, or rationale for no new test
- skipped tests and why

Travel rule: if a change touches provider evidence, semantic retrieval, card contracts, or visible prose, include downstream consumer tests instead of proving only the local function.
