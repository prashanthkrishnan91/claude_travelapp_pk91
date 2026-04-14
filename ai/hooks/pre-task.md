# hook pre-task

Execute pre-task preparations and context loading.

## Usage

```bash
npx claude-flow hook pre-task [options]
```

## Options

| Option | Description |
|--------|-------------|
| `--description, -d <text>` | Task description for context |
| `--auto-spawn-agents` | Automatically spawn required agents (default: true) |
| `--load-memory` | Load relevant memory from previous sessions |
| `--optimize-topology` | Select optimal swarm topology |
| `--estimate-complexity` | Analyze task complexity |

## Examples

### Basic pre-task hook
```bash
npx claude-flow hook pre-task --description "Implement itinerary recommendation service"
```

### With memory loading
```bash
npx claude-flow hook pre-task -d "Continue booking API development" --load-memory
```

### Manual agent control
```bash
npx claude-flow hook pre-task -d "Debug issue #123" --auto-spawn-agents false
```

### Full optimization
```bash
npx claude-flow hook pre-task -d "Refactor travel search module" --optimize-topology --estimate-complexity
```

## Features

### Auto Agent Assignment
- Analyzes task requirements
- Determines needed agent types (coder, tester, researcher, etc.)
- Spawns agents automatically
- Configures agent parameters

### Memory Loading
- Retrieves relevant past decisions
- Loads previous task contexts
- Restores agent configurations
- Maintains continuity across sessions

### Topology Optimization
- Analyzes task structure
- Selects best swarm topology (hierarchical, mesh, etc.)
- Configures communication patterns
- Optimizes for performance

### Complexity Estimation
- Evaluates task difficulty
- Suggests agent count
- Identifies dependencies

## Integration

This hook is automatically called by Claude Code when:
- Starting a new task
- Resuming work after a break
- Switching between projects
- Beginning complex operations

## Output

Returns JSON with:

```json
{
  "continue": true,
  "topology": "hierarchical",
  "agentsSpawned": 5,
  "complexity": "medium",
  "estimatedMinutes": 30,
  "memoryLoaded": true
}
```

## See Also

- `hook post-task` — Post-task cleanup and learning storage
- `hook session-end` — Session state persistence
- `hook setup` — Initial hook configuration
