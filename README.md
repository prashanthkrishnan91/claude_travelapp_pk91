# claude_travelapp_pk91

## Supabase migration reminder

For AI Concierge chat persistence, apply these DB migrations in order on the deployed Supabase project:

1. `backend/db/migrations/002_concierge_messages.sql`
2. `backend/db/migrations/003_concierge_message_dedupe.sql`
3. `backend/db/migrations/004_*.sql` (only if a future PR explicitly adds one)

After applying migrations, reload Supabase/PostgREST schema cache (or restart the API) so `public.concierge_messages` and indexes are visible to PostgREST.
