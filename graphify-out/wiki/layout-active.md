# layout-active

## Overview

Directory-based community: frontend/src/components/layout

- **Size**: 5 nodes
- **Cohesion**: 0.0784
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| MobileNav | Function | /home/user/claude_travelapp_pk91/frontend/src/components/layout/MobileNav.tsx | 29-129 |
| isActive | Function | /home/user/claude_travelapp_pk91/frontend/src/components/layout/MobileNav.tsx | 33-36 |
| PageHeader | Function | /home/user/claude_travelapp_pk91/frontend/src/components/layout/PageHeader.tsx | 9-21 |
| Sidebar | Function | /home/user/claude_travelapp_pk91/frontend/src/components/layout/Sidebar.tsx | 32-100 |
| isActive | Function | /home/user/claude_travelapp_pk91/frontend/src/components/layout/Sidebar.tsx | 35-38 |

## Execution Flows

- **TripDetailPage** (criticality: 0.69, depth: 4)
- **DashboardPage** (criticality: 0.68, depth: 3)
- **TripsPage** (criticality: 0.67, depth: 2)
- **RootLayout** (criticality: 0.52, depth: 2)
- **NewTripPage** (criticality: 0.52, depth: 2)
- **CardsPage** (criticality: 0.43, depth: 1)
- **ConciergePage** (criticality: 0.28, depth: 1)
- **SearchPage** (criticality: 0.28, depth: 1)
- **SettingsPage** (criticality: 0.28, depth: 1)

## Dependencies

### Outgoing

- `clsx` (7 edge(s))
- `map` (4 edge(s))
- `Link` (4 edge(s))
- `Icon` (4 edge(s))
- `Plane` (3 edge(s))
- `setOpen` (3 edge(s))
- `usePathname` (2 edge(s))
- `startsWith` (2 edge(s))
- `useState` (1 edge(s))
- `X` (1 edge(s))
- `Menu` (1 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/app/layout.tsx::RootLayout` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/MobileNav.tsx` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/Sidebar.tsx` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/cards/page.tsx::CardsPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/concierge/page.tsx::ConciergePage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/page.tsx::DashboardPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/search/page.tsx::SearchPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/settings/page.tsx::SettingsPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/[id]/page.tsx::TripDetailPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/new/page.tsx::NewTripPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/page.tsx::TripsPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/layout/PageHeader.tsx` (1 edge(s))
