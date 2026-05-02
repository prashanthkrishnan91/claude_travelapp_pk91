# UI Baseline — Travel Concierge

Purpose: prevent future UI prompts from rediscovering the visual foundation.

## Current baseline

Latest foundation PR: #168 — Travel UI Foundation: premium boutique design system pass.

Observed cost: ~43% of Claude session before merge, ~51% lifecycle. Treat broad UI foundation work as High usage.

## Visual direction

- Dark mode-first boutique travel concierge
- Deep navy / charcoal base
- Warm gold / amber accents
- Cream text scale
- Premium card surfaces
- Subtle borders, shadows, glassy depth
- Calm, editorial, concierge-style

## Known foundation files

Use these as baseline references before any future UI work:

- `frontend/src/app/globals.css`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/MobileNav.tsx`
- `frontend/src/components/layout/PageHeader.tsx`
- `frontend/src/components/ui/StatCard.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- Dashboard components updated in PR #168
- `frontend/src/app/trips/page.tsx`

## Known limitations after foundation pass

- Deep trip detail pages may still have light-era Tailwind classes.
- AI Concierge panel and search result cards may need page-specific polish.
- Cards/settings pages may need separate pass.

## Future UI prompt rules

- Do not rediscover the foundation.
- Reference PR #168 and this file as baseline.
- Use one page/component pass at a time unless UI budget explicitly approves more.
- Max 6 files for Sonnet UI implementation unless Code Committee approves.
- Use Codex cheap visual merge gate after UI PRs.
- Stop Sonnet chat after PR.
