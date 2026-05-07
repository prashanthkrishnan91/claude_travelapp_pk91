# Test Selector — Travel Concierge

Run the smallest sufficient suite, but if a change touches a shared contract or provider evidence, include downstream consumer tests.

## Required mapping

| Changed area | Required checks |
|---|---|
| `backend/app/concierge/semantic_retrieval.py` | semantic retrieval tests, verified card contract tests, open-language/venue-head cases |
| `backend/app/concierge/evidence_dossier.py` | evidence dossier tests, writer/AllowedClaimsPacket downstream tests |
| `backend/app/concierge/set_level_writer.py` | writer tests, claim-safety tests, visible-copy quality contracts |
| provider fanout/enrichment files | provider unit tests, route-level latency/deadline tests, cancellation/fallback behavior |
| frontend concierge card/UI files | card rendering tests, save/add-to-day/maps button checks, no duplicate address/diagnostic leakage |
| API response shape/mappers | producer + consumer contract tests, snake_case/camelCase normalization tests |
| docs-only changes | markdown/readability check; no runtime tests required unless docs changed generated behavior |

## Adversarial test rule
For non-trivial PRs, add or identify one adversarial test for the riskiest invariant: wrong source authority, unsupported claim, dropped card contract, timeout leak, or UI leakage.

## Skipping tests
If skipping a likely test, explain why it is not needed and what evidence covers the invariant instead.
