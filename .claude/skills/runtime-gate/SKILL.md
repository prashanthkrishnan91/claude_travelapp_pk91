# Runtime / Latency Gate Skill

Use when provider, fanout, LLM, DB, cache, route, or request-path behavior changes.

Return:
- new live calls, loops, fanout, LLM calls, DB calls, or cache changes
- local timeout behavior
- total route/runtime impact proof or explicit limitation
- fallback/skip behavior
- request-path executor lifecycle safety
- runtime evidence needed yes/no and why

Travel-specific rule: fail if only local provider timeout is tested but total route impact is not considered.
