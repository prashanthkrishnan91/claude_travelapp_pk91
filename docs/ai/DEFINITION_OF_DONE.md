# Definition of Done — Travel Concierge

Passing tests is necessary but not sufficient. Done means the relevant product invariant is proven.

| Task type | Done means |
|---|---|
| Backend contract change | Producer and consumer audited; contract tests pass; changed fields are documented in PR summary. |
| Provider/enrichment change | Source authority remains Google-first; local timeout and total route impact are considered; fallback/skip behavior is safe. |
| Evidence/prose change | Claims are evidence-bound or hidden; no source-name filler; claim-safety tests pass. |
| Semantic retrieval change | Open-language behavior preserved; no keyword-only patch; verified cards still map to UI. |
| Frontend card/UI change | No duplicate fields, no diagnostic leakage, add/save/maps actions still work. |
| Runtime/logging/telemetry change | Logs are useful but not user-visible; env defaults are safe. |
| Docs/workflow change | No runtime code changed; instructions are concise and do not conflict with existing docs. |

## Required PR proof

Every PR must state:

- what changed
- why it is done
- tests actually run
- known limitations
- UI validation needed yes/no and why
- Supabase SQL yes/no
- runtime/product impact
