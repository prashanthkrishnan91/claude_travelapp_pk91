-- Migration 005: Add saved_items — trip-optional user-scoped save backing
-- Stage 2A Slice 2 decision: docs/product/DECISION_LOG.md (2026-05-11)
--
-- Covers all four Explore verticals without another table redesign:
--   restaurant | attraction | hotel | flight
-- Hotels carry guests/rooms in search_context; flights carry passengers/cabin
-- in search_context — they are not collapsed into shared fields.

create table if not exists public.saved_items (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null references public.users(id) on delete cascade,

  -- Vertical discriminator — enforced via check constraint
  vertical          text not null
                    check (vertical in ('restaurant','attraction','hotel','flight')),

  -- Human-visible identity
  display_name      text not null,

  -- Provider / place identity
  -- For restaurants/attractions/hotels: provider='google_places', provider_place_id=Google Place ID
  -- For flights and non-place providers: provider_item_id holds the offer/itinerary/entity identity
  -- Exactly one of provider_place_id or provider_item_id is expected when provider is set.
  provider          text,
  provider_place_id text,   -- Google Place ID (restaurants, attractions, hotels)
  provider_item_id  text,   -- Generic offer / itinerary / entity identity (flights, non-place)

  -- Snapshot for card rendering without re-fetch
  display_snapshot  jsonb not null default '{}'::jsonb,

  -- Vertical-specific search context at save time
  -- restaurants/attractions: { destination, area }
  -- hotels: { destination, check_in, check_out, guests, rooms }
  -- flights: { origin, destination, departure_date, return_date, passengers, cabin_class }
  search_context    jsonb not null default '{}'::jsonb,

  -- Provenance: how/when/where the item was surfaced
  provenance        jsonb not null default '{}'::jsonb,

  -- Soft-delete: 'active' | 'deleted'
  status            text not null default 'active'
                    check (status in ('active','deleted')),

  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

-- Ownership index
create index if not exists saved_items_user_idx
  on public.saved_items (user_id, status, created_at desc);

-- Deduplication index for place-based providers (Google Places: restaurants, attractions, hotels)
create unique index if not exists saved_items_place_identity_uq
  on public.saved_items (user_id, vertical, provider, provider_place_id)
  where provider_place_id is not null and status = 'active';

-- Deduplication index for non-place providers (flights: offer/itinerary identity)
create unique index if not exists saved_items_item_identity_uq
  on public.saved_items (user_id, vertical, provider, provider_item_id)
  where provider_item_id is not null and status = 'active';

-- Vertical filter index
create index if not exists saved_items_vertical_idx
  on public.saved_items (user_id, vertical, status);

create trigger saved_items_set_updated_at
before update on public.saved_items
for each row execute function public.set_updated_at();

-- RLS
alter table public.saved_items enable row level security;

create policy "saved_items: select own"
  on public.saved_items for select
  using (auth.uid() = user_id);

create policy "saved_items: insert own"
  on public.saved_items for insert
  with check (auth.uid() = user_id);

create policy "saved_items: update own"
  on public.saved_items for update
  using (auth.uid() = user_id);

create policy "saved_items: delete own"
  on public.saved_items for delete
  using (auth.uid() = user_id);
