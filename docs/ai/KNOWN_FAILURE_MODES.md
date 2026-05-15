# Known AI Failure Modes — Travel Concierge

Use this file before non-trivial implementation, review, or follow-up prompts. Add to it after repeated failures.

## Canonical authority failures

- Google Places is the only canonical source for addable cards, place identity, operational status, address, maps URL, and place_id.
- Yelp, Foursquare, Tavily, Serper, editorial articles, blogs, and web/social sources are enrichment only. They cannot mint addable cards.
- Enrichment evidence can help ranking/reasoning only after Google verification.

## Semantic behavior failures

- Do not patch individual venue categories with keywords. Preserve open-language semantic behavior.
- Do not let modifiers like waterfront, view, cheap, romantic, or trendy override the venue head.
- More-options follow-ups should reuse verified pools when possible.

## Evidence/prose failures

- Do not expose internal diagnostics, raw evidence structures, source names, or provider keys to UI or LLM-visible prose.
- Source-name-only facts such as `editorial_mention:eater.com` must not become visible filler unless explicitly approved.
- Visible notes must be evidence-grounded, LLM-written under claim safety, or hidden.
- Do not add deterministic fallback visible notes.
- If evidence is thin, hide the note instead of inventing one.

## Contract failures

- If changing evidence atoms/provider facts, audit downstream consumers including evidence dossier, AllowedClaimsPacket, set-level writer, visible card mappers, save/add-to-day payloads, and frontend card rendering.
- Keep AI Concierge card fields aligned: `display.displayWhy`, `supportingDetails.whyPick`, and top-level `whyPick`.
- Backend typed responses must normalize snake_case/camelCase contracts before card mapping.

## Runtime failures

- Any new live provider, enrichment layer, LLM call, fanout, or cache behavior must prove total route budget impact, not only local timeout.
- Do not use `with ThreadPoolExecutor(...)` in request-path fanout where timeout must return quickly. Use explicit lifecycle, cancel pending futures, and `shutdown(wait=False, cancel_futures=True)`.
- Non-blocking enrichment is preferred when user-visible cards can render safely without enrichment.

## CI workflow failures

- Any diff-based CI check (`git diff base...HEAD`) must use `ref: ${{ github.event.pull_request.head.sha }}` + `git fetch origin <base>` in `actions/checkout@v4`. The default checkout for `pull_request` events is `refs/pull/{n}/merge` (a synthetic merge commit). GitHub may not update this ref before CI starts, causing the diff to see a stale file list.
- PR body section headers must use `## SectionName` markdown headers exactly. Using `**SectionName:**` bold inline fails the substring gate even when the content is correct.
- PR body updates via the GitHub API after a push do NOT affect already-queued CI runs. The body in `GITHUB_EVENT_PATH` is snapshot at trigger time. Body must be correct before the triggering push, or a new commit is required to re-trigger CI with the updated body.

## Validation failures

- UI validation is not required after every backend sub-PR. Use tests/telemetry until visible product behavior meaningfully changes.
- If route latency or production providers are the claim, runtime logs or production evidence may be required.
