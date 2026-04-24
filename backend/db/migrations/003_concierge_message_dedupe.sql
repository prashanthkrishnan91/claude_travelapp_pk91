-- Migration 003: add idempotency key for concierge message persistence

alter table if exists public.concierge_messages
  add column if not exists client_message_id text;

create unique index if not exists concierge_messages_client_message_id_uidx
  on public.concierge_messages (client_message_id)
  where client_message_id is not null;
