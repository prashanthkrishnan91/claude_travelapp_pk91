# utils-ask

## Overview

Directory-based community: ai/utils

- **Size**: 25 nodes
- **Cohesion**: 0.2083
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| AISettings | Class | /home/user/claude_travelapp_pk91/ai/utils/config.py | 24-51 |
| __init__ | Function | /home/user/claude_travelapp_pk91/ai/utils/config.py | 27-43 |
| validate | Function | /home/user/claude_travelapp_pk91/ai/utils/config.py | 45-51 |
| get_ai_settings | Function | /home/user/claude_travelapp_pk91/ai/utils/config.py | 55-57 |
| LLMClient | Class | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 23-109 |
| __init__ | Function | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 26-35 |
| ask | Function | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 37-58 |
| ask_json | Function | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 60-70 |
| _extract_json | Function | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 77-109 |
| clamp | Function | /home/user/claude_travelapp_pk91/ai/utils/llm.py | 112-117 |
| loadMemory | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 22-31 |
| saveMemory | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 33-36 |
| get | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 39-44 |
| set | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 46-56 |
| delete | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 58-67 |
| clear | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 69-72 |
| keys | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 74-79 |
| k | Function | /home/user/claude_travelapp_pk91/ai/utils/memory.js | 76-76 |
| routeTask | Function | /home/user/claude_travelapp_pk91/ai/utils/router.js | 62-106 |
| kw | Function | /home/user/claude_travelapp_pk91/ai/utils/router.js | 85-85 |
| AgentResult | Class | /home/user/claude_travelapp_pk91/ai/utils/state.py | 15-34 |
| PipelineState | Class | /home/user/claude_travelapp_pk91/ai/utils/state.py | 38-82 |
| add_result | Function | /home/user/claude_travelapp_pk91/ai/utils/state.py | 60-66 |
| is_successful | Function | /home/user/claude_travelapp_pk91/ai/utils/state.py | 69-70 |
| to_summary | Function | /home/user/claude_travelapp_pk91/ai/utils/state.py | 72-82 |

## Execution Flows

- **ask_json** (criticality: 0.36, depth: 1)
- **get** (criticality: 0.36, depth: 1)
- **set** (criticality: 0.36, depth: 1)
- **delete** (criticality: 0.36, depth: 1)
- **clear** (criticality: 0.32, depth: 1)
- **get_ai_settings** (criticality: 0.16, depth: 1)

## Dependencies

### Outgoing

- `getenv` (9 edge(s))
- `log` (5 edge(s))
- `loads` (3 edge(s))
- `int` (2 edge(s))
- `float` (2 edge(s))
- `strip` (2 edge(s))
- `search` (2 edge(s))
- `group` (2 edge(s))
- `min` (2 edge(s))
- `error` (2 edge(s))
- `exit` (2 edge(s))
- `stringify` (2 edge(s))
- `filter` (2 edge(s))
- `lower` (1 edge(s))
- `ValueError` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/ai/utils/memory.js` (8 edge(s))
- `/home/user/claude_travelapp_pk91/ai/utils/router.js` (3 edge(s))
- `/home/user/claude_travelapp_pk91/ai/utils/config.py` (2 edge(s))
- `/home/user/claude_travelapp_pk91/ai/utils/llm.py` (2 edge(s))
- `/home/user/claude_travelapp_pk91/ai/utils/state.py` (2 edge(s))
