# hook post-task

Execute cleanup, analysis, and learning storage after task completion.

## Usage

```bash
npx claude-flow hook post-task [options]
```

## Options

| Option | Description |
|--------|-------------|
| `--task-id <id>` | Task identifier for tracking |
| `--analyze-performance` | Measure execution metrics |
| `--store-decisions` | Persist key decisions to memory |
| `--export-learnings` | Extract successful patterns for reuse |
| `--generate-report` | Create completion documentation |
| `--success <bool>` | Whether the task succeeded (default: true) |

## Examples

### Basic post-task hook
```bash
npx claude-flow hook post-task --task-id "task-123" --success true
```

### With full analysis
```bash
npx claude-flow hook post-task \
  --task-id "itinerary-builder" \
  --analyze-performance \
  --store-decisions \
  --export-learnings \
  --generate-report
```

### On failure
```bash
npx claude-flow hook post-task --task-id "booking-api" --success false
```

## Features

### Performance Metrics
- Measures execution time
- Tracks token usage
- Identifies bottlenecks
- Generates optimization suggestions

### Knowledge Preservation
Records key decisions made during the task:
- Implementation choices
- Error resolutions
- Architecture decisions
- Trade-off rationale

### Pattern Export
Extracts successful patterns for future use:
- Code patterns that worked well
- Agent routing decisions
- Effective prompt strategies

## Automatic Invocation

Claude Code triggers this hook automatically when:
- Tasks complete (success or failure)
- Switching between tasks
- Session completion
- After significant milestones

## Output

Returns JSON with:

```json
{
  "taskId": "itinerary-builder",
  "durationMs": 45000,
  "tokensUsed": 12500,
  "filesModified": 4,
  "performanceScore": 0.87,
  "learningsExported": true,
  "reportPath": "/sessions/task-report.md"
}
```

## See Also

- `hook pre-task` — Pre-task context loading
- `hook session-end` — Session state persistence
- `memory usage` — Memory management
