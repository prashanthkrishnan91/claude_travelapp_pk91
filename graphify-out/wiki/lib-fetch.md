# lib-fetch

## Overview

Directory-based community: frontend/src/lib

- **Size**: 22 nodes
- **Cohesion**: 0.2414
- **Dominant Language**: typescript

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| snakeToCamel | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 31-33 |
| camelToSnake | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 35-37 |
| transformKeys | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 39-52 |
| toCamel | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 54-55 |
| toSnake | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 57-58 |
| apiFetch | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 62-94 |
| fetchTrips | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 98-104 |
| fetchTrip | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 106-112 |
| createTrip | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 114-133 |
| updateTrip | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 135-144 |
| fetchItinerary | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 149-171 |
| createDay | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 173-183 |
| deleteDay | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 185-189 |
| createItem | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 191-210 |
| updateItem | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 212-221 |
| deleteItem | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 223-225 |
| mapAttractionToResult | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 251-265 |
| mapHotelToResult | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 267-278 |
| searchHotels | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 281-297 |
| searchAttractions | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 300-317 |
| compareItems | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 321-328 |
| fetchCards | Function | /home/user/claude_travelapp_pk91/frontend/src/lib/api.ts | 332-338 |

## Execution Flows

- **TripDetailPage** (criticality: 0.69, depth: 4)
- **DashboardPage** (criticality: 0.68, depth: 3)
- **TripsPage** (criticality: 0.67, depth: 2)
- **createTrip** (criticality: 0.37, depth: 2)
- **updateTrip** (criticality: 0.37, depth: 2)

## Dependencies

### Outgoing

- `stringify` (8 edge(s))
- `map` (5 edge(s))
- `json` (2 edge(s))
- `replace` (2 edge(s))
- `fetch` (1 edge(s))
- `toLowerCase` (1 edge(s))
- `Number` (1 edge(s))
- `all` (1 edge(s))
- `round` (1 edge(s))
- `filter` (1 edge(s))
- `slice` (1 edge(s))
- `toUpperCase` (1 edge(s))
- `isArray` (1 edge(s))
- `fromEntries` (1 edge(s))
- `entries` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts` (22 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilder.tsx::TripBuilder` (8 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/[id]/page.tsx::TripDetailPage` (4 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/page.tsx::DashboardPage` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx::TripsPage` (1 edge(s))
