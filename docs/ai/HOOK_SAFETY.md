# Hook Safety

Hooks execute shell commands and must be treated as powerful and risky.

## OS v3 rules

- OS v3 allows advisory hooks only.
- Hard-blocking hooks are not permitted without explicit future approval.
- Hooks are reminders, not proof.

## Implementation rules

- Validate and sanitize hook input.
- Quote shell variables.
- Avoid `.env`, secrets, keys, `.git`, and credential files.
- Prefer `$CLAUDE_PROJECT_DIR` or project-root-safe paths.
- No network calls from hooks unless explicitly approved.
- No destructive commands.
- Hook scripts must be small, readable, deterministic, and safe to review.
- Hook scripts must not exfiltrate data or inspect sensitive files.

## Maintenance rules

- If a hook produces noise twice, revise or remove it.
- If a hook is silently ignored, remove it.
- If a hook needs repeated explanation, the rule belongs in a doc/skill instead.
- If a hook is promoted from advisory to required-evidence reminder, document the rationale in the PR that promotes it.
