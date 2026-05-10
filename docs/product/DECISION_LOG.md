# Decision Log

Product decisions are recorded here so we do not re-litigate direction.

## Template

```
## YYYY-MM-DD — Decision title
- Decision:
- Why:
- Alternatives rejected:
- What would change our mind:
- Roadmap impact:
```

## Seed decisions

## 2026-05-10 — Shift from trip-first to discovery-first
- Decision: The app must be useful before a trip exists. Travel Idea / Saved Item is the future root object; Trip is one conversion path.
- Why: Trip-first gate forces users to commit before they explore; Discover-first matches real user intent and unlocks Saved, AI, and Watchtower stages.
- Alternatives rejected: Keep trip-first and treat Discover as a sub-feature.
- What would change our mind: Strong evidence that users will not engage without a trip context.
- Roadmap impact: Defines Stage 2 as the discovery-first shift; reorders saved/AI work behind it.

## 2026-05-10 — Travel Idea / Saved Item becomes future root object
- Decision: Saved items, not trips, are the long-lived primary object the rest of the product hangs off.
- Why: Saved-first lets Discover, AI, deals, points, and Watchtower all share one substrate.
- Alternatives rejected: Trip-as-root with saved-items as a child container.
- What would change our mind: A demonstrated cost in trip clarity that cannot be repaired.
- Roadmap impact: Stage 3 builds the saved-item foundation as a first-class root object.

## 2026-05-10 — Design sprint waits for Wife Wow Readiness Gate
- Decision: Major design transformation only after Discover + Saved + core trip flows are stable, AI Concierge is trustworthy, and no embarrassing leakage remains.
- Why: Painting the walls before the foundation is set wastes design work and rots fast.
- Alternatives rejected: Do design sprint earlier alongside feature work.
- What would change our mind: A specific high-impact surface where design is the blocker, not features.
- Roadmap impact: Stage 6 is gated by `Wife Wow Readiness Gate`; design polish beyond that gate is deferred.
