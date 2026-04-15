-- =============================================================
-- Travel Concierge — Supabase Schema
-- Postgres 15+ / Supabase
-- =============================================================

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- -------------------------------------------------------------
-- Helper: updated_at trigger
-- -------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =============================================================
-- USERS
-- Mirrors auth.users; holds profile + preferences.
-- =============================================================
create table if not exists public.users (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text not null unique,
  full_name       text,
  home_airport    text,
  home_currency   text default 'USD',
  preferences     jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists users_email_idx on public.users (email);

create trigger users_set_updated_at
before update on public.users
for each row execute function public.set_updated_at();

-- =============================================================
-- TRAVEL CARDS
-- Issuer cards owned by a user (AMEX Gold, Bilt, Venture X, ...).
-- =============================================================
create table if not exists public.travel_cards (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  card_key        text not null,            -- e.g. 'amex_gold', 'bilt', 'venture_x'
  display_name    text not null,            -- 'AMEX Gold'
  issuer          text not null,            -- 'American Express', 'Wells Fargo', 'Capital One'
  currency        text not null default 'USD',
  points_balance  bigint not null default 0,
  point_value_cpp numeric(6,4),             -- user-set cents-per-point valuation
  is_primary      boolean not null default false,
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (user_id, card_key)
);

create index if not exists travel_cards_user_idx on public.travel_cards (user_id);

create trigger travel_cards_set_updated_at
before update on public.travel_cards
for each row execute function public.set_updated_at();

-- =============================================================
-- TRANSFER PARTNERS
-- Global catalog of loyalty programs each card can transfer to.
-- =============================================================
create table if not exists public.transfer_partners (
  id              uuid primary key default gen_random_uuid(),
  card_key        text not null,            -- references travel_cards.card_key (logical)
  partner_key     text not null,            -- 'air_canada_aeroplan'
  partner_name    text not null,            -- 'Air Canada Aeroplan'
  partner_type    text not null check (partner_type in ('airline','hotel')),
  transfer_ratio  numeric(6,4) not null default 1.0,  -- 1.0 = 1:1
  min_transfer    integer not null default 1000,
  transfer_bonus  numeric(5,4),             -- e.g. 0.25 for +25%
  notes           text,
  is_active       boolean not null default true,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (card_key, partner_key)
);

create index if not exists transfer_partners_card_idx on public.transfer_partners (card_key);
create index if not exists transfer_partners_partner_idx on public.transfer_partners (partner_key);

create trigger transfer_partners_set_updated_at
before update on public.transfer_partners
for each row execute function public.set_updated_at();

-- =============================================================
-- TRIPS
-- Top-level research/planning container.
-- =============================================================
create table if not exists public.trips (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references public.users(id) on delete cascade,
  title           text not null,
  destination     text not null,
  origin          text,
  start_date      date,
  end_date        date,
  travelers       integer not null default 1,
  budget_cash     numeric(12,2),
  budget_currency text not null default 'USD',
  status          text not null default 'draft'
                  check (status in ('draft','researching','planned','booked','completed','archived')),
  notes           text,
  metadata        jsonb not null default '{}'::jsonb,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  constraint trips_date_order check (end_date is null or start_date is null or end_date >= start_date)
);

create index if not exists trips_user_idx on public.trips (user_id);
create index if not exists trips_status_idx on public.trips (status);
create index if not exists trips_dates_idx on public.trips (start_date, end_date);

create trigger trips_set_updated_at
before update on public.trips
for each row execute function public.set_updated_at();

-- =============================================================
-- ITINERARY DAYS
-- One row per day of a trip.
-- =============================================================
create table if not exists public.itinerary_days (
  id              uuid primary key default gen_random_uuid(),
  trip_id         uuid not null references public.trips(id) on delete cascade,
  day_number      integer not null,
  date            date,
  title           text,
  summary         text,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (trip_id, day_number)
);

create index if not exists itinerary_days_trip_idx on public.itinerary_days (trip_id);

create trigger itinerary_days_set_updated_at
before update on public.itinerary_days
for each row execute function public.set_updated_at();

-- =============================================================
-- ITINERARY ITEMS
-- Flights, hotels, activities, transit, meals — with dual pricing.
-- =============================================================
create table if not exists public.itinerary_items (
  id                 uuid primary key default gen_random_uuid(),
  day_id             uuid not null references public.itinerary_days(id) on delete cascade,
  trip_id            uuid not null references public.trips(id) on delete cascade,
  item_type          text not null
                     check (item_type in ('flight','hotel','activity','transit','meal','note')),
  title              text not null,
  description        text,
  location           text,
  start_time         timestamptz,
  end_time           timestamptz,
  -- Pricing
  cash_price         numeric(12,2),
  cash_currency      text default 'USD',
  points_price       bigint,
  points_card_key    text,                 -- which card's points are used
  points_partner_key text,                 -- transfer partner redemption, if any
  cpp_value          numeric(6,4),         -- realized cents-per-point for this redemption
  best_option        text check (best_option in ('cash','points')) ,
  -- Structured payload (flight segments, hotel details, etc.)
  details            jsonb not null default '{}'::jsonb,
  position           integer not null default 0,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

create index if not exists itinerary_items_day_idx on public.itinerary_items (day_id);
create index if not exists itinerary_items_trip_idx on public.itinerary_items (trip_id);
create index if not exists itinerary_items_type_idx on public.itinerary_items (item_type);

create trigger itinerary_items_set_updated_at
before update on public.itinerary_items
for each row execute function public.set_updated_at();

-- =============================================================
-- RESEARCH CACHE
-- Caches external lookups (flight searches, hotel rates, AI responses).
-- =============================================================
create table if not exists public.research_cache (
  id              uuid primary key default gen_random_uuid(),
  cache_key       text not null unique,    -- hash of query params
  source          text not null,           -- 'amadeus','google_flights','claude','manual'
  query           jsonb not null,
  payload         jsonb not null,
  expires_at      timestamptz,
  created_at      timestamptz not null default now()
);

create index if not exists research_cache_source_idx on public.research_cache (source);
create index if not exists research_cache_expires_idx on public.research_cache (expires_at);
