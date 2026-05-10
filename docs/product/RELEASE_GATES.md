# Release Gates

Milestone gates that decide when a stage is ready. Gates are not feature lists; they are go/no-go criteria.

## Product Spine Stability Gate

- No catastrophic failures in AI Concierge, add, save, or trip flows.
- No mock/sample/prototype leakage in user-visible surfaces.
- Basic add/save/trip card contracts intact.
- Acceptable runtime/latency for current scope.

## Discovery-First Gate

- App is useful with no trip created.
- Global Explore shell works for primary verticals.
- Unified result actions (save / add to trip / create trip) live and consistent.
- AI Concierge cards remain trustworthy outside trip context.

## Saved Lists Gate

- Saved item is a first-class root object.
- Saving works from Discover, search, AI Concierge, and trip surfaces.
- Saved lists / boards have stable view, edit, and reorganization.
- No regressions in trip add flows.

## Wife Wow Readiness Gate

- App useful without trip.
- Discover works.
- Saved lists work.
- Trip creation / add-to-day works.
- AI Concierge returns trusted cards.
- One or two verticals usable end-to-end.
- No mock/sample leakage.
- No embarrassing fallback text.
- No broken account/auth flows.
- Acceptable latency.
- Mobile experience usable.

## Design Sprint Exit Gate

- Visual system applied consistently to Discover, Saved, and Trip flows.
- Empty / loading / error states polished.
- Copy tone consistent and free of internal jargon.
- Mobile parity with desktop polish.
- No regressions in core flows.

## Deal/Points Readiness Gate

- Deal source model trustworthy and bounded.
- Deals link cleanly to saved items.
- Points / transfer partner data trustworthy.
- Plain-English answers for points-to-destination questions.
- No scraping fragility presented as production data.

## Watchtower Alert Readiness Gate

- Triggers fire only on meaningful changes.
- Suppression rules tested.
- Alert delivery surface low-noise.
- User can mute / scope without losing saved intent.
