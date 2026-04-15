# dashboard-points

## Overview

Directory-based community: frontend/src/components/dashboard

- **Size**: 5 nodes
- **Cohesion**: 0.0513
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| PointsSummary | Function | /home/user/claude_travelapp_pk91/frontend/src/components/dashboard/PointsSummary.tsx | 17-101 |
| QuickActions | Function | /home/user/claude_travelapp_pk91/frontend/src/components/dashboard/QuickActions.tsx | 35-61 |
| formatDateRange | Function | /home/user/claude_travelapp_pk91/frontend/src/components/dashboard/RecentTrips.tsx | 6-15 |
| fmt | Function | /home/user/claude_travelapp_pk91/frontend/src/components/dashboard/RecentTrips.tsx | 8-13 |
| RecentTrips | Function | /home/user/claude_travelapp_pk91/frontend/src/components/dashboard/RecentTrips.tsx | 21-107 |

## Execution Flows

- **DashboardPage** (criticality: 0.68, depth: 3)

## Dependencies

### Outgoing

- `Link` (5 edge(s))
- `format` (3 edge(s))
- `map` (3 edge(s))
- `reduce` (2 edge(s))
- `CreditCard` (2 edge(s))
- `toLocaleString` (2 edge(s))
- `Number` (2 edge(s))
- `TrendingUp` (1 edge(s))
- `toFixed` (1 edge(s))
- `Icon` (1 edge(s))
- `slice` (1 edge(s))
- `ArrowRight` (1 edge(s))
- `MapPin` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/TripStatusBadge.tsx::TripStatusBadge` (1 edge(s))
- `Calendar` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/app/page.tsx::DashboardPage` (3 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/dashboard/RecentTrips.tsx` (3 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/dashboard/PointsSummary.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/dashboard/QuickActions.tsx` (1 edge(s))
