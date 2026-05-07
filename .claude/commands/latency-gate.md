Use `.claude/skills/ai-repo-os/SKILL.md` latency gate.

Run when provider, fanout, LLM, DB, cache, or request-path behavior changes.

Return:
- new live calls/loops/fanout/cache behavior
- local timeout proof
- total route/runtime impact proof or limitation
- fallback/skip behavior
- executor lifecycle safety

Fail if only local timeout is tested.
