# AI Handoff — Travel Concierge

## Last change
Merged differentiator-first whyPick reasoning pipeline with generic output rejection (PR #165).

## Files touched
- backend/app/concierge/evidence.py
- backend/app/concierge/whypick_prompt.py
- backend/app/concierge/reasoning.py
- backend/app/services/live_research.py
- backend/app/services/concierge.py
- backend/tests/* (whyPick, evidence, integration)

## Behavior change
- whyPick now prioritizes structured differentiators (editorial, Michelin, specialty tags) instead of generic rating/location templates
- LLM output is validated and rejected if it lacks venue-specific signals
- Deterministic fallback now uses specialty tags when LLM is unavailable or fails validation
- Alignment enforced across venue.why_pick, supportingDetails.whyPick, and display.displayWhy

## Known issues
- LLM path may not consistently trigger (fallback still dominates in some cases)
- Some venues lack safe differentiators → still produce simpler deterministic output
- Need further improvement in differentiator richness for sparse cities

## Next likely task
Improve evidence intake and differentiator selection so LLM path triggers more reliably and produces richer whyPick reasoning.

## Debug notes
- generation_method often shows "deterministic" due to missing/invalid API key or validation rejection
- foursquare tags sometimes marked safe_for_copy=False, limiting differentiator pool
- fallback path is working correctly but overused
