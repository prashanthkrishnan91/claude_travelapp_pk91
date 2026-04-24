-- Migration 002: Add persistent AI concierge message history per trip

create table if not exists public.concierge_messages (
  id                 uuid primary key default gen_random_uuid(),
  trip_id            uuid not null references public.trips(id) on delete cascade,
  role               text not null check (role in ('user','assistant','system','tool')),
  content            text not null,
  structured_results jsonb,
  created_at         timestamptz not null default now()
);

create index if not exists concierge_messages_trip_idx
  on public.concierge_messages (trip_id, created_at);
