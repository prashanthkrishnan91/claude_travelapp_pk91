# hook session-end

Cleanup and persist session state before ending work.

## Usage

```bash
npx claude-flow hook session-end [options]
```

## Options

| Option | Description |
|--------|-------------|
| `--session-id, -s <id>` | Session identifier to end |
| `--save-state` | Save current session state (default: true) |
| `--export-metrics` | Export session metrics |
| `--generate-summary` | Create session summary |
| `--cleanup-temp` | Remove temporary files |

## Examples

### Basic session end
```bash
npx claude-flow hook session-end --session-id "dev-session-001"
```

### With full export
```bash
npx claude-flow hook session-end -s "feature-booking" --export-metrics --generate-summary
```

### Quick close
```bash
npx claude-flow hook session-end -s "hotfix" --save-state false --cleanup-temp
```

### Complete persistence
```bash
npx claude-flow hook session-end -s "major-refactor" --save-state --export-metrics --generate-summary
```

## Features

### State Persistence
- Saves current context and open tasks
- Stores task progress (completed, in-progress, pending)
- Preserves architectural decisions
- Maintains agent memory state

### Metric Export
- Session duration
- Commands executed
- Files modified
- Tokens consumed
- Performance data

### Summary Generation
- Work accomplished this session
- Key decisions made
- Problems solved
- Next steps identified

### Cleanup Operations
- Removes temp files and intermediate outputs
- Clears ephemeral caches
- Frees allocated resources
- Optimizes memory storage

## Integration

This hook is automatically called by Claude Code when:
- Ending a conversation
- Closing work session
- Before shutdown
- Switching contexts

## Output

Returns JSON with:

```json
{
  "sessionId": "dev-session-001",
  "duration": 7200000,
  "saved": true,
  "metrics": {
    "commandsRun": 145,
    "filesModified": 23,
    "tokensUsed": 85000,
    "tasksCompleted": 8
  },
  "summaryPath": "/sessions/dev-session-001-summary.md",
  "cleanedUp": true
}
```

## See Also

- `hook pre-task` — Pre-task preparation
- `hook post-task` — Post-task cleanup
- `hook setup` — Hook system configuration
