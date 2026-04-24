-- =============================================================
-- Supabase Row Level Security Policies
-- Apply this to your Supabase project via the SQL editor.
-- =============================================================

-- -------------------------------------------------------------
-- Auto-create public.users row when a new auth user signs up
-- -------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- =============================================================
-- TRAVEL CARDS
-- =============================================================
alter table public.travel_cards enable row level security;

create policy "travel_cards: select own"
  on public.travel_cards for select
  using (auth.uid() = user_id);

create policy "travel_cards: insert own"
  on public.travel_cards for insert
  with check (auth.uid() = user_id);

create policy "travel_cards: update own"
  on public.travel_cards for update
  using (auth.uid() = user_id);

create policy "travel_cards: delete own"
  on public.travel_cards for delete
  using (auth.uid() = user_id);

-- =============================================================
-- TRIPS
-- =============================================================
alter table public.trips enable row level security;

create policy "trips: select own"
  on public.trips for select
  using (auth.uid() = user_id);

create policy "trips: insert own"
  on public.trips for insert
  with check (auth.uid() = user_id);

create policy "trips: update own"
  on public.trips for update
  using (auth.uid() = user_id);

create policy "trips: delete own"
  on public.trips for delete
  using (auth.uid() = user_id);

-- =============================================================
-- ITINERARY ITEMS
-- Access is scoped through trip ownership.
-- =============================================================
alter table public.itinerary_items enable row level security;

create policy "itinerary_items: select via trip"
  on public.itinerary_items for select
  using (
    exists (
      select 1 from public.trips
      where trips.id = itinerary_items.trip_id
        and trips.user_id = auth.uid()
    )
  );

create policy "itinerary_items: insert via trip"
  on public.itinerary_items for insert
  with check (
    exists (
      select 1 from public.trips
      where trips.id = itinerary_items.trip_id
        and trips.user_id = auth.uid()
    )
  );

create policy "itinerary_items: update via trip"
  on public.itinerary_items for update
  using (
    exists (
      select 1 from public.trips
      where trips.id = itinerary_items.trip_id
        and trips.user_id = auth.uid()
    )
  );

create policy "itinerary_items: delete via trip"
  on public.itinerary_items for delete
  using (
    exists (
      select 1 from public.trips
      where trips.id = itinerary_items.trip_id
        and trips.user_id = auth.uid()
    )
  );

-- =============================================================
-- CONCIERGE MESSAGES
-- Access is scoped through trip ownership.
-- =============================================================
alter table public.concierge_messages enable row level security;

create policy "concierge_messages: select via trip"
  on public.concierge_messages for select
  using (
    exists (
      select 1 from public.trips
      where trips.id = concierge_messages.trip_id
        and trips.user_id = auth.uid()
    )
  );

create policy "concierge_messages: insert via trip"
  on public.concierge_messages for insert
  with check (
    exists (
      select 1 from public.trips
      where trips.id = concierge_messages.trip_id
        and trips.user_id = auth.uid()
    )
  );
