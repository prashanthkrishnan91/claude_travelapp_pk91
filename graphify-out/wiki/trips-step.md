# trips-step

## Overview

Directory-based community: frontend/src/components/trips

- **Size**: 17 nodes
- **Cohesion**: 0.0564
- **Dominant Language**: tsx

## Members

| Name | Kind | File | Lines |
|------|------|------|-------|
| CompareModal | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/CompareModal.tsx | 11-187 |
| formatDate | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/ItineraryDayColumn.tsx | 20-27 |
| ItineraryDayColumn | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/ItineraryDayColumn.tsx | 29-115 |
| ItineraryItemCard | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/ItineraryItemCard.tsx | 70-184 |
| SearchResultCard | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/SearchResultCard.tsx | 69-186 |
| TripBuilder | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilder.tsx | 74-619 |
| StepIndicator | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 52-91 |
| DestinationStep | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 95-143 |
| DatesStep | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 145-189 |
| TravelersStep | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 191-247 |
| BudgetStep | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 258-312 |
| NotesStep | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 314-339 |
| ReviewSummary | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 343-379 |
| TripBuilderForm | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 383-496 |
| patch | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 393-395 |
| canAdvance | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 397-400 |
| handleSave | Function | /home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx | 402-413 |

## Execution Flows

- **TripDetailPage** (criticality: 0.69, depth: 4)
- **NewTripPage** (criticality: 0.52, depth: 2)

## Dependencies

### Outgoing

- `map` (31 edge(s))
- `useState` (13 edge(s))
- `onChange` (11 edge(s))
- `useCallback` (10 edge(s))
- `setDays` (7 edge(s))
- `find` (6 edge(s))
- `String` (6 edge(s))
- `replace` (5 edge(s))
- `toLocaleString` (4 edge(s))
- `has` (4 edge(s))
- `delete` (4 edge(s))
- `startsWith` (4 edge(s))
- `clsx` (4 edge(s))
- `max` (3 edge(s))
- `DollarSign` (3 edge(s))

### Incoming

- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilderForm.tsx` (11 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/ItineraryDayColumn.tsx` (2 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/CompareModal.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/ItineraryItemCard.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/SearchResultCard.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/[id]/page.tsx::TripDetailPage` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/components/trips/TripBuilder.tsx` (1 edge(s))
- `/home/user/claude_travelapp_pk91/frontend/src/app/trips/new/page.tsx::NewTripPage` (1 edge(s))
