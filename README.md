# claude_travelapp_pk91

## Supabase migration reminder

For AI Concierge chat persistence, apply these DB migrations in order on the deployed Supabase project:

1. `backend/db/migrations/002_concierge_messages.sql`
2. `backend/db/migrations/003_concierge_message_dedupe.sql`
3. `backend/db/migrations/004_*.sql` (only if a future PR explicitly adds one)

After applying migrations, reload Supabase/PostgREST schema cache (or restart the API) so `public.concierge_messages` and indexes are visible to PostgREST.

## AI Concierge production trust mode

- `RESEARCH_ENGINE_REQUIRE_GOOGLE_VERIFICATION=true` enforces fail-closed behavior for live place cards.
- When enabled and Google verification is unavailable, concierge returns **research-only** sources (non-addable) and does not fall back to sample/database place cards for place intents.
- Yelp/Foursquare enrichment is optional and non-authoritative; it never creates new cards and never changes addability.
- “Why this pick” card copy is deterministic and Google-grounded; raw editorial snippets/listicle text are sanitized/rejected and never rendered directly on addable cards.
