# Aspirational Design Vision — Luxury for Less Travel Concierge

This document captures the long-term design ambition. It is not an instruction to start broad UI work now.

## Timing rule

Do not start a major design transformation until the product workflows are stable enough that visual work will not be repeatedly invalidated by feature churn.

Design-session timing is appropriate when:

- Core trip creation, AI Concierge, Trip Ideas, itinerary movement, and day/timeline workflows are stable.
- No active blocking data, auth, persistence, or routing bugs are being triaged.
- Recent UI work has stayed stable for at least a few feature passes.
- The user explicitly asks for a design session or agrees that it is time.

Until then, apply only small UI fixes when they block usability or confidence.

## Product emotion

The app should feel cutting-edge, luxury, boutique, and personal. It should not feel like a generic SaaS dashboard. The user should want to log in every day.

For Travel Concierge, the target mood is:

- Boutique hotel lobby, private travel designer, editorial magazine, luxury-for-less insider.
- Warm, tactile, layered, atmospheric, and trustworthy.
- Beautiful login experience, not just a form.
- Premium without looking corporate or sterile.

## Future design-session agenda

When the timing rule says design is ready, run a dedicated design session before implementation:

1. Establish 3-5 visual directions.
2. Compare palettes, typography, image treatment, animation style, card systems, and empty/loading states.
3. Review inspiration sources such as Pinterest boards, boutique hotel sites, luxury travel/editorial sites, Google Stitch outputs if available, and user-provided screenshots.
4. Let the user pick and mix: palette, font personality, motion level, layout density, image/texture approach, and login/dashboard tone.
5. Convert the chosen direction into a design brief before coding.
6. Implement in capped phases with UI budget gates.

Do not use live inspiration claims unless current web research or user-provided screenshots are available in the session.

## Candidate inspiration/integration sources

These are optional inputs for the future design session, not automatic dependencies:

- Pinterest mood boards supplied by the user.
- Google Stitch outputs supplied by the user.
- Boutique hotel and luxury travel editorial screenshots supplied by the user.
- Existing Claude personal skills: `frontend-design`, `ui-ux-pro-max`, `brainstorming` for design ideation only.
- Existing frontend capabilities: Tailwind, CSS variables, GSAP animations, responsive component primitives.

## Candidate design capabilities to explore later

- Cinematic login page with animated ambient background.
- Destination-aware imagery or editorial hero treatments.
- Boutique card system with layered glass, texture, shadows, and warm accents.
- Motion language: subtle GSAP entrance, hover, drawer, and itinerary movement transitions.
- Premium empty/loading states instead of plain skeletons.
- Typography pairing with distinct travel personality.
- Optional textured backgrounds, grain, gradients, maps, or soft illustrated motifs.
- Mobile-first polish so the app feels intentional on phone browser.

## Guardrails

- Do not run broad UI redesigns while feature workflows are still changing.
- Do not let visual work touch backend, API, Supabase, ranking, or business logic unless explicitly scoped.
- Do not add heavy animation libraries beyond what is already available without budget approval.
- Preserve accessibility, readability, and performance.
- Avoid generic dark-mode SaaS styling.

## Implementation strategy when ready

Use this order:

1. Design discovery session — no code.
2. Design brief / style direction — no code.
3. Token and primitive pass — CSS variables, typography, shared primitives.
4. Login/auth page showcase.
5. One core page pass.
6. Component family pass.
7. Motion/animation pass.
8. Codex visual merge gate after each PR.

Each implementation phase must use `docs/ai/skills/ui_fix.md`, `docs/ai/UI_BASELINE.md`, and the UI budget gate in `docs/ai/PROMPT_LIBRARY.md`.
