# ui-empty

## Overview

Directory-based community: frontend/src/components/ui

- **Size**: 4 nodes
- **Cohesion**: 0.0000
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| EmptyState | Function | /home/user/claude_travelapp_pk91/frontend/src/components/ui/EmptyState.tsx | 10-21 |
| Skeleton | Function | /home/user/claude_travelapp_pk91/frontend/src/components/ui/Skeleton.tsx | 7-9 |
| StatCard | Function | /home/user/claude_travelapp_pk91/frontend/src/components/ui/StatCard.tsx | 13-42 |
| TripStatusBadge | Function | /home/user/claude_travelapp_pk91/frontend/src/components/ui/TripStatusBadge.tsx | 13-16 |

## Execution Flows

- **DashboardPage** (criticality: 0.68, depth: 3)
- **TripsPage** (criticality: 0.67, depth: 2)
- **DashboardLoading** (criticality: 0.43, depth: 1)
- **CardsPage** (criticality: 0.43, depth: 1)
- **TripsLoading** (criticality: 0.35, depth: 1)

## Dependencies

### Outgoing

- `clsx` (4 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/app/loading.tsx::DashboardLoading` (26 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/loading.tsx::TripsLoading` (11 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/page.tsx::DashboardPage` (4 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx::TripsPage` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/cards/page.tsx::CardsPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/EmptyState.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/Skeleton.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/StatCard.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/dashboard/RecentTrips.tsx::RecentTrips` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/TripStatusBadge.tsx` (1 edge(s))
