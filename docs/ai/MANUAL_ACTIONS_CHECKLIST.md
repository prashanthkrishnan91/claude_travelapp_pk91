# Manual Actions Checklist — Travel Concierge

Every PR summary must answer these explicitly.

## Required yes/no fields

- Supabase SQL required: Yes/No
- Railway env vars required: Yes/No
- Vercel env vars required: Yes/No
- Railway redeploy required: Yes/No
- Vercel redeploy required: Yes/No
- New provider/API key required: Yes/No
- Runtime validation required: Yes/No and why
- UI validation required: Yes/No and why
- Rollback path: feature flag / revert / env off / not applicable

## When manual action is required

- SQL migration, schema, RLS, auth, or persistence contract changed.
- Env var or feature flag changed.
- Provider routing, enrichment, or LLM calls require production keys.
- Frontend public env variables changed and require Vercel redeploy.
- Runtime certification endpoint or production log evidence is part of success criteria.

## When manual action is not required

- Docs-only changes.
- Tests-only changes.
- Internal refactor with unchanged runtime contract.
- Backend-only code where existing deployment pipeline handles rollout and no env/SQL changes exist.
