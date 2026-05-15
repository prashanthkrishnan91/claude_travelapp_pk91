-- Migration 006: Durable Concierge Evidence/Note Cache
-- Turns the PR #384 in-memory evidence/note cache into a Supabase-backed
-- durable layer. Repeat/similar AI Concierge searches reuse evidence atoms
-- and approved notes across worker restarts, deploys, and next-day usage
-- until TTL expires, preventing re-spending Tavily/editorial credits.
--
-- Manual application required: see PR body for instructions.
-- No RLS user policies — service-role only (backend bypasses RLS).

-- ── Evidence cache ────────────────────────────────────────────────────────────
-- Stores accepted editorial evidence atoms per semantic fingerprint.
-- TTL: 14 days (configurable via _DURABLE_EVIDENCE_TTL_DAYS).
-- Atoms are JSON-serialized EnrichmentAtom dicts keyed by Google place_id.

create table if not exists public.concierge_evidence_cache (
  id                    uuid primary key default gen_random_uuid(),
  evidence_fingerprint  text not null,
  destination           text,
  normalized_context    jsonb not null default '{}'::jsonb,
  atoms_by_place_id     jsonb not null,
  accepted_count        integer not null default 0,
  version_salt          text not null,
  expires_at            timestamptz not null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique(evidence_fingerprint, version_salt)
);

create index if not exists concierge_evidence_cache_fingerprint_idx
  on public.concierge_evidence_cache (evidence_fingerprint, version_salt);

create index if not exists concierge_evidence_cache_expires_idx
  on public.concierge_evidence_cache (expires_at);

-- updated_at trigger (reuses set_updated_at function from prior migrations)
create trigger concierge_evidence_cache_set_updated_at
before update on public.concierge_evidence_cache
for each row execute function public.set_updated_at();

-- RLS: enabled but no user policies — service role bypasses RLS.
-- Anon/authenticated users cannot read or write this table.
alter table public.concierge_evidence_cache enable row level security;


-- ── Note cache ────────────────────────────────────────────────────────────────
-- Stores approved, quality-gated concierge notes per (place_id, fingerprint).
-- TTL: 30 days (configurable via _DURABLE_NOTE_TTL_DAYS).
-- Only notes that passed the quality gate (validated=True in SetWriterResult)
-- are stored. Generic, rating-only, rejected, or template notes are never stored.

create table if not exists public.concierge_note_cache (
  id                    uuid primary key default gen_random_uuid(),
  evidence_fingerprint  text not null,
  provider_place_id     text not null,
  note                  text not null,
  source                text not null,
  version_salt          text not null,
  expires_at            timestamptz not null,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique(provider_place_id, evidence_fingerprint, version_salt)
);

create index if not exists concierge_note_cache_lookup_idx
  on public.concierge_note_cache (provider_place_id, evidence_fingerprint, version_salt);

create index if not exists concierge_note_cache_fingerprint_idx
  on public.concierge_note_cache (evidence_fingerprint, version_salt);

create index if not exists concierge_note_cache_expires_idx
  on public.concierge_note_cache (expires_at);

create trigger concierge_note_cache_set_updated_at
before update on public.concierge_note_cache
for each row execute function public.set_updated_at();

-- RLS: enabled but no user policies — service role bypasses RLS.
alter table public.concierge_note_cache enable row level security;
