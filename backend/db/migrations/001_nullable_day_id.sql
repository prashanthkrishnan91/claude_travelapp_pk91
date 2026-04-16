-- Migration 001: Make day_id nullable on itinerary_items
-- Allows trip-level items (e.g. saved flights) without a specific day assignment.
alter table public.itinerary_items
  alter column day_id drop not null;
