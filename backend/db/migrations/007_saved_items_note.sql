-- Migration 007: Add persisted user note to saved_items
-- Saved Notes v1: user can write/edit a freeform note on any saved item
-- ("great rooftop", "near hotel", "anniversary dinner", etc.)
--
-- Non-destructive: existing rows get note=NULL and continue to work unchanged.
-- The note is nullable text with no size enforcement in the DB;
-- the API layer trims and accepts empty-string as clear-to-null.

alter table public.saved_items
  add column if not exists note text;
