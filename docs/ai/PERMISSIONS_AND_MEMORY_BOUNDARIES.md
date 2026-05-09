# Permissions and Memory Boundaries

Define safe, portable boundaries for Claude memory, settings, permissions, MCP, and secrets.

## Source of truth

- Repo OS docs are the source of shared workflow truth.
- User memory is personal preference only and must not override repo invariants.
- Project settings may contain safe shared settings only.
- Local settings are for personal machine-specific preferences and must not be required for repo correctness.

## Secrets and sensitive files

- Do not store secrets, keys, tokens, or private env values in memory files.
- Deny reading `.env`, `.env.*`, secrets, credential files, and private keys.
- If a hook or tool needs sensitive data, raise the concern instead of bypassing it.

## MCP rules

- MCP servers must be explicitly trusted and reviewed before use.
- Do not add MCP servers in workflow PRs unless the task explicitly requests it.
- Use `/mcp` only to inspect configured state.

## Permission troubleshooting

- If tool permissions block necessary work, state the exact permission issue and the safest next step.
- Do not silently broaden permissions. Document the change and require review.
- Use `/permissions` only to inspect or resolve a real access issue.
