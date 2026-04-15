# core-settings

## Overview

Directory-based community: backend/app/core

- **Size**: 4 nodes
- **Cohesion**: 0.2000
- **Dominant Language**: python

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| Settings | Class | /home/user/claude_travelapp_pk91/backend/app/core/config.py | 6-26 |
| supabase_key | Function | /home/user/claude_travelapp_pk91/backend/app/core/config.py | 24-26 |
| get_settings | Function | /home/user/claude_travelapp_pk91/backend/app/core/config.py | 30-31 |
| get_current_user_id | Function | /home/user/claude_travelapp_pk91/backend/app/core/deps.py | 12-25 |

## Execution Flows

- **get_supabase** (criticality: 0.28, depth: 2)

## Dependencies

### Outgoing

- `BaseSettings` (1 edge(s))
- `Header` (1 edge(s))
- `UUID` (1 edge(s))
- `HTTPException` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/backend/app/core/config.py` (2 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/db/client.py::get_supabase` (1 edge(s))
- `/home/user/claude_travelapp_pk91/backend/app/core/deps.py` (1 edge(s))
