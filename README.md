# claude_travelapp_pk91

## Supabase migration reminder

For AI Concierge chat persistence, apply these DB migrations in order on the deployed Supabase project:

1. `backend/db/migrations/002_concierge_messages.sql`
2. `backend/db/migrations/003_concierge_message_dedupe.sql`

If `public.concierge_messages` is missing from PostgREST schema cache, reload schema cache after applying migrations.
