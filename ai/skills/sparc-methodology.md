# SPARC Methodology Skill

SPARC (**S**pecification, **P**seudocode, **A**rchitecture, **R**efinement, **C**ompletion) is a systematic development methodology integrated with Claude Flow's multi-agent orchestration capabilities.

## Overview

SPARC provides 17 specialized operational modes for structured software development. It emphasizes:

- **Structured Phases**: Clear handoffs between development stages
- **Test-Driven Development**: Tests written before implementation
- **Concurrent Agent Work**: Multiple agents work in parallel where possible
- **Persistent Knowledge Sharing**: ReasoningBank stores learnings across cycles
- **Quality Assurance Throughout**: Gates at every phase transition

## Available Modes

| Mode | Description |
|------|-------------|
| `orchestrator` | Coordinates full SPARC cycle |
| `specification` | Requirements and acceptance criteria |
| `pseudocode` | Algorithmic logic before coding |
| `architect` | System design and component boundaries |
| `tdd` | Test-driven development cycle |
| `coder` | Implementation specialist |
| `reviewer` | Code quality and security review |
| `tester` | Comprehensive test generation |
| `researcher` | Deep analysis and synthesis |
| `documenter` | Technical documentation |
| `designer` | API and UX design |
| `debugger` | Root cause analysis |
| `optimizer` | Performance profiling |
| `refactorer` | Structural improvement |
| `security` | Security audit |
| `devops` | Deployment and infrastructure |
| `integrator` | System integration |

## Activation

### Via MCP Tools (in Claude Code)
```bash
npx claude-flow sparc run <mode> --task "Your task description"
```

### Examples
```bash
# Full SPARC cycle
npx claude-flow sparc run orchestrator --task "Build itinerary recommendation service"

# Specification phase only
npx claude-flow sparc run specification --task "Define booking API"

# TDD implementation
npx claude-flow sparc run tdd --task "Implement hotel search with filters"

# Architecture design
npx claude-flow sparc run architect --task "Design caching layer for travel data"
```

## Integration with Claude Flow

SPARC works seamlessly with:
- **Agent swarms**: Distribute phase work across specialized agents
- **ReasoningBank**: Store and retrieve phase outputs
- **Memory coordination**: Persist decisions across sessions
- **Hook system**: Trigger phase transitions automatically

## Phase Quality Gates

```
Specification → must have: requirements doc, acceptance criteria
Pseudocode   → must have: algorithm outline, edge cases documented
Architecture → must have: component diagram, interface definitions
Refinement   → must have: >80% test coverage, review approved
Completion   → must have: integration tests pass, docs complete
```

## Configuration (`.claude-flow/config.json`)

```json
{
  "sparc": {
    "enabledModes": ["orchestrator", "coder", "tester", "reviewer"],
    "qualityGates": {
      "minCoverage": 80,
      "requireReview": true
    },
    "memory": {
      "namespace": "sparc",
      "ttlDays": 30
    }
  }
}
```
