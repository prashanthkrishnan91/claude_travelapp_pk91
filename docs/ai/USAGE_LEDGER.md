# AI Usage Ledger

Committed, sanitized audit trail of Claude token/cost usage by PR, prompt, and delta.

## Purpose

A future auditor can pull this file from GitHub and understand token/cost burn by PR, prompt phase, and per-prompt delta without needing local raw snapshots. Raw `.ai/usage/*.json` files stay local and gitignored.

## Privacy rule

Never commit to this ledger:
- Raw `.ai/usage/*.json` snapshots or baseline files
- Prompts or conversation content
- Secrets, env values, or API keys
- Local Claude DB data (`~/.claude/`)

This file contains only sanitized session-level and delta summaries.

## Two-layer model

| Layer | Location | Committed? | Purpose |
|---|---|---|---|
| Raw snapshots | `.ai/usage/*.json` | No (gitignored) | Local debugging, full token detail |
| Sanitized ledger | `docs/ai/USAGE_LEDGER.md` | Yes | Auditable PR/prompt-level history |

PR usage notes in the PR body are not sufficient for workflow audits — they are too lossy once the PR is merged. This ledger is the durable audit source.

## Ledger columns

| Column | Description |
|---|---|
| Date | ISO date of the session (YYYY-MM-DD) |
| PR | PR number or `unknown` |
| Prompt ID | Human-readable prompt/patch ID: `initial`, `patch-1`, `patch-2`, `same-chat-pr-2`, etc. |
| Phase | `initial` / `follow-up` / `audit` / `merge-gate` / `backfill` / `unknown` |
| Linked PR | Original PR number if this is a follow-up, or `n/a` |
| Repo area | e.g. `workflow/docs`, `backend/concierge`, `frontend/trip` |
| Claude session | Session URL or `unknown` |
| Model | e.g. `claude-sonnet-4-6`, `claude-opus-4-7` |
| Chat strategy | `same-chat`, `new-chat`, or `unknown` |
| Source | `ccusage`, `statusline`, `manual`, or `unavailable` |
| Input tok | Session-level input tokens (cumulative) |
| Output tok | Session-level output tokens (cumulative) |
| Cache read | Session-level cache read tokens (cumulative) |
| Cache creation | Session-level cache creation tokens (cumulative) |
| Total tok | Session-level total tokens (cumulative) |
| Est. cost | Session-level estimated cost (cumulative) |
| Δ input | Per-prompt delta input tokens vs saved baseline |
| Δ output | Per-prompt delta output tokens vs saved baseline |
| Δ cache read | Per-prompt delta cache read tokens vs saved baseline |
| Δ cache creation | Per-prompt delta cache creation tokens vs saved baseline |
| Δ total | Per-prompt delta total tokens vs saved baseline |
| Δ cost | Per-prompt delta estimated cost vs saved baseline |
| Waste | `none` / `preventable-follow-up` / `necessary-follow-up` / `exploration` / `unknown` |
| Main drivers | What consumed tokens (e.g. broad discovery, many iterations) |
| Follow-up patches | Number of follow-up PRs required |
| Efficiency lesson | One-line lesson for future sessions |

## Ledger table

| Date | PR | Prompt ID | Phase | Linked PR | Repo area | Session | Model | Chat | Source | Input tok | Output tok | Cache read | Cache creation | Total tok | Est. cost | Δ input | Δ output | Δ cache read | Δ cache creation | Δ total | Δ cost | Waste | Main drivers | Follow-up patches | Efficiency lesson |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD | #000 | initial | initial | n/a | workflow/docs | unknown | claude-sonnet-4-6 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unknown | template row — replace | 0 | n/a |
| 2026-05-13 | stage3-exit-canonical-flight-seeding | initial | initial | n/a | backend/routes,services,tests | web-claude | claude-opus-4-7 | same-chat | manual | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | unify /trips/create-with-search flight seeding with /explore/flights via canonical_flight_search helper; persist FlightItineraryOffer as Trip Ideas | 0 | one provider seam → fewer divergent flight pathways |
| 2026-05-14 | flight-offer-fingerprint-GbKID | initial | initial | n/a | backend/flights | web-claude | claude-opus-4-7 | same-chat | ccusage | 86 | 26669 | 4051596 | 141748 | 4220099 | $3.58 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | none | anchor reads, itinerary+trips edits, test additions | 0 | replace title-based dedupe for canonical Duffel offers with deterministic offer_fingerprint |

## Per-prompt delta workflow

```bash
# a) Initial PR prompt: save baseline before, capture after
bash scripts/ai/usage_snapshot.sh --save-baseline before-pr-123
# ... Claude does the work ...
bash scripts/ai/usage_snapshot.sh --pr 123 --prompt-id initial --phase initial \
  --delta-from-baseline .ai/usage/baseline-before-pr-123.json \
  --model claude-sonnet-4-6 --repo-area workflow/docs \
  --main-drivers "anchor reads, file writes" --follow-up-patches 0 \
  --waste-classification none --append-ledger

# b) Follow-up patch delta linked to original PR
bash scripts/ai/usage_snapshot.sh --save-baseline before-patch1
# ... Claude patches ...
bash scripts/ai/usage_snapshot.sh --pr 124 --prompt-id patch-1 --phase follow-up \
  --linked-pr 123 --delta-from-baseline .ai/usage/baseline-before-patch1.json \
  --waste-classification preventable-follow-up --append-ledger

# c) Same-chat second PR delta
bash scripts/ai/usage_snapshot.sh --save-baseline before-pr-125-same-chat
# ... more Claude work in same session ...
bash scripts/ai/usage_snapshot.sh --pr 125 --prompt-id initial --phase initial \
  --chat-strategy same-chat \
  --delta-from-baseline .ai/usage/baseline-before-pr-125-same-chat.json \
  --append-ledger
```

If ccusage is unavailable, delta fields show `unavailable` — that is acceptable.

## Backfilling prior sessions

```bash
bash scripts/ai/backfill_usage_ledger.sh --since YYYY-MM-DD
```

Prints 26-column candidate rows with `phase=backfill`, `prompt_id=unknown`, delta=`unavailable`.
Do not guess PR numbers or delta values — mark as `unknown`/`unavailable`.

## Audit guidance

Use this ledger plus GitHub PR history to diagnose token burn:
- High Δ total for `follow-up` phase → contract was unclear at initial PR time.
- `preventable-follow-up` waste → candidate for `docs/ai/MISS_LEDGER.md` promotion.
- High session input tokens, low output → over-broad discovery reads.
- Recurring efficiency lessons → consider OS-level rule change.
