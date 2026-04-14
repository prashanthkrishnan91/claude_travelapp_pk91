# Hook Setup Guide

Configure the Claude Flow hook system for the Travel Concierge App.

## Quick Start

### 1. Initialize with Hooks
```bash
npx claude-flow init --hooks
```

This automatically creates:
- `.claude/settings.json` with hook configurations
- Hook command documentation
- Default hook handlers

### 2. Test Hook Functionality
```bash
# Test pre-edit hook
npx claude-flow hook pre-edit --file src/api/routes.py

# Test session summary
npx claude-flow hook session-end --summary
```

### 3. Customize Hooks

Edit `.claude/settings.json` to customize:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^Write$",
        "hooks": [{
          "type": "command",
          "command": "npx claude-flow hook pre-write --file '${tool.params.file_path}'"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "^(Write|Edit)$",
        "hooks": [{
          "type": "command",
          "command": "npx claude-flow hook post-edit --file '${tool.params.file_path}'"
        }]
      }
    ]
  }
}
```

## Hook Response Format

Hooks return JSON with:
- `continue`: Whether to proceed (true/false)
- `reason`: Explanation for decision
- `metadata`: Additional context

### Example — Blocking Response
```json
{
  "continue": false,
  "reason": "Protected file — manual review required",
  "metadata": {
    "file": ".env.production",
    "protection_level": "high"
  }
}
```

### Example — Allow Response
```json
{
  "continue": true,
  "metadata": {
    "file": "src/services/booking.py"
  }
}
```

## Common Patterns

### Protected File Detection
```json
{
  "matcher": "^(Write|Edit)$",
  "hooks": [{
    "type": "command",
    "command": "npx claude-flow hook check-protected --file '${tool.params.file_path}'"
  }]
}
```

### Automatic Testing on Save
```json
{
  "matcher": "^Write$",
  "hooks": [{
    "type": "command",
    "command": "test -f '${tool.params.file_path%.py}_test.py' && pytest '${tool.params.file_path%.py}_test.py'"
  }]
}
```

### Pre-task Memory Loading
```json
{
  "event": "UserPromptSubmit",
  "hooks": [{
    "type": "command",
    "command": "node ai/utils/memory.js get recent_context"
  }]
}
```

## Performance Tips

- Keep hook execution under 100ms
- Use caching for repeated read operations
- Batch related operations into a single hook
- Run non-critical hooks asynchronously with `&`

## Debugging Hooks

```bash
# Enable debug output
export CLAUDE_FLOW_DEBUG=true

# Test specific hook
npx claude-flow hook pre-edit --file src/api/routes.py --debug

# View hook execution log
cat .claude-flow/logs/hooks.log
```

## Environment Variables

```bash
CLAUDE_FLOW_DEBUG=false         # Enable debug logging
CLAUDE_FLOW_HOOK_TIMEOUT=100    # Max hook execution time (ms)
CLAUDE_FLOW_MEMORY_DIR=.claude-flow/data  # Memory storage path
```
