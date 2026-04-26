-- Distribution of concierge response types over the last N requests.
-- Usage: replace :limit with an integer (e.g., 500).

with recent as (
  select response_type
  from public.concierge_request_log
  order by created_at desc
  limit :limit
)
select
  response_type,
  count(*) as requests,
  round(100.0 * count(*) / nullif((select count(*) from recent), 0), 2) as pct_of_recent
from recent
group by response_type
order by requests desc, response_type asc;
