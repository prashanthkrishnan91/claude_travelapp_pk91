# app-page

## Overview

Directory-based community: frontend/src/app

- **Size**: 6 nodes
- **Cohesion**: 0.0270
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| ErrorPage | Function | /home/user/claude_travelapp_pk91/frontend/src/app/error.tsx | 11-31 |
| RootLayout | Function | /home/user/claude_travelapp_pk91/frontend/src/app/layout.tsx | 15-40 |
| DashboardLoading | Function | /home/user/claude_travelapp_pk91/frontend/src/app/loading.tsx | 3-98 |
| isUpcoming | Function | /home/user/claude_travelapp_pk91/frontend/src/app/page.tsx | 16-19 |
| nextTripLabel | Function | /home/user/claude_travelapp_pk91/frontend/src/app/page.tsx | 21-28 |
| DashboardPage | Function | /home/user/claude_travelapp_pk91/frontend/src/app/page.tsx | 30-112 |

## Execution Flows

- **DashboardPage** (criticality: 0.68, depth: 3)
- **RootLayout** (criticality: 0.52, depth: 2)
- **DashboardLoading** (criticality: 0.43, depth: 1)

## Dependencies

### Outgoing

- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/Skeleton.tsx::Skeleton` (26 edge(s))
- `map` (4 edge(s))
- `from` (4 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/ui/StatCard.tsx::StatCard` (4 edge(s))
- `filter` (2 edge(s))
- `reduce` (2 edge(s))
- `useEffect` (1 edge(s))
- `error` (1 edge(s))
- `AlertCircle` (1 edge(s))
- `RefreshCw` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/MobileNav.tsx::MobileNav` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/Sidebar.tsx::Sidebar` (1 edge(s))
- `all` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::fetchTrips` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/lib/api.ts::fetchCards` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/app/page.tsx` (3 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/error.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/layout.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/loading.tsx` (1 edge(s))
