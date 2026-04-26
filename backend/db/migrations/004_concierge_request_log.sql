-- Migration 004: concierge request observability logs + 30-day retention

create table if not exists public.concierge_request_log (
  request_id uuid primary key,
  user_id uuid references auth.users(id),
  prompt text not null,
  response_type text not null,
  stage1_prior jsonb not null default '{}'::jsonb,
  intent_confidence numeric,
  intent_classifier_version text,
  sources_used text[] not null default '{}',
  llm_model text,
  llm_tokens_in int,
  llm_tokens_out int,
  latency_ms int,
  pipeline_version text,
  created_at timestamptz not null default now()
);

create index if not exists concierge_request_log_created_at_idx
  on public.concierge_request_log (created_at desc);
create index if not exists concierge_request_log_response_type_created_at_idx
  on public.concierge_request_log (response_type, created_at desc);

-- Retention procedure (run daily via Supabase pg_cron when available).
create or replace function public.prune_concierge_request_log()
returns void
language sql
security definer
as $$
  delete from public.concierge_request_log
  where created_at < now() - interval '30 days';
$$;

-- Requires pg_cron extension in Supabase project.
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    if not exists (
      select 1
      from cron.job
      where jobname = 'prune_concierge_request_log_daily'
    ) then
      perform cron.schedule(
        'prune_concierge_request_log_daily',
        '15 3 * * *',
        $$select public.prune_concierge_request_log();$$
      );
    end if;
  end if;
exception
  when undefined_table then
    -- cron.job metadata table may not be visible in some environments.
    null;
end $$;
