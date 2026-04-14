# Stream-Chain Skill

Stream-Chain enables multi-agent pipeline orchestration through sequential data flow. Each step receives the complete output from the previous step, enabling sophisticated multi-agent coordination through streaming.

## Core Functionality

### Custom Chains
Execute user-defined prompt sequences with full control over each step.

### Predefined Pipelines
Battle-tested workflows for common development tasks.

## Available Pipelines

| Pipeline | Description |
|----------|-------------|
| `analysis` | Codebase examination and improvement identification |
| `refactor` | Systematic code refactoring with prioritization |
| `test` | Comprehensive test generation and coverage analysis |
| `optimize` | Performance bottleneck identification and optimization |

## Usage

### Run a Predefined Pipeline
```bash
npx claude-flow stream-chain --pipeline analysis --input "src/"
npx claude-flow stream-chain --pipeline refactor --input "src/services/"
npx claude-flow stream-chain --pipeline test --input "src/api/"
npx claude-flow stream-chain --pipeline optimize --input "src/"
```

### Custom Chain
```bash
npx claude-flow stream-chain \
  --steps "Analyze the code for issues" \
           "Suggest refactoring improvements" \
           "Generate unit tests for the improvements" \
  --input "path/to/code"
```

## Configuration

### Minimum Requirements
- At least 2 prompts per custom chain
- Valid input path or content

### Options
| Option | Default | Description |
|--------|---------|-------------|
| `--timeout` | 30s | Max time per step |
| `--debug` | false | Verbose step output |
| `--verbose` | false | Show intermediate results |
| `--memory` | true | Store outputs in cross-session memory |

### Custom Pipeline Definition (`.claude-flow/config.json`)
```json
{
  "streamChain": {
    "pipelines": {
      "my-pipeline": {
        "steps": [
          "Analyze the input for patterns",
          "Identify improvement opportunities",
          "Generate implementation plan"
        ],
        "timeout": 45,
        "memoryKey": "my-pipeline-output"
      }
    }
  }
}
```

## Performance

- Throughput: 2–5 steps per minute (varies by complexity)
- Context: up to 100K tokens per step
- Memory: ~50MB per active chain
- Cross-session persistence: enabled by default

## Integration with Agents

Stream-Chain can invoke agent roles at each step:

```json
{
  "steps": [
    { "agent": "researcher", "prompt": "Analyze the codebase" },
    { "agent": "planner", "prompt": "Plan refactoring based on analysis" },
    { "agent": "coder", "prompt": "Implement the refactoring plan" },
    { "agent": "tester", "prompt": "Generate tests for the implementation" }
  ]
}
```
