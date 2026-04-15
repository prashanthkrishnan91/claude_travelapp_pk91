# trips-page

## Overview

Directory-based community: frontend/src/app/trips

- **Size**: 6 nodes
- **Cohesion**: 0.0317
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| TripDetailPage | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/[id]/page.tsx | 15-84 |
| TripsLoading | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/loading.tsx | 3-42 |
| NewTripPage | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/new/page.tsx | 7-17 |
| formatDateRange | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx | 18-27 |
| fmt | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx | 20-25 |
| TripsPage | Function | /home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx | 34-148 |

## Execution Flows

- **TripDetailPage** (criticality: 0.69, depth: 4)
- **TripsPage** (criticality: 0.67, depth: 2)
- **NewTripPage** (criticality: 0.52, depth: 2)
- **TripsLoading** (criticality: 0.35, depth: 1)

## Dependencies

### Outgoing

- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/Skeleton.tsx::Skeleton` (11 edge(s))
- `Link` (4 edge(s))
- `map` (4 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/PageHeader.tsx::PageHeader` (3 edge(s))
- `all` (2 edge(s))
- `slice` (2 edge(s))
- `toISOString` (2 edge(s))
- `PlusCircle` (2 edge(s))
- `format` (2 edge(s))
- `Number` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::fetchTrip` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::fetchItinerary` (1 edge(s))
- `now` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::searchHotels` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::searchAttractions` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx` (3 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/[id]/page.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/loading.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/new/page.tsx` (1 edge(s))
