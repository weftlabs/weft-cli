# Enhancement Request: [Feature Name]

## Current Weft System Context

[Describe the relevant parts of Weft with file paths]

Example:
```
Weft currently has:
- Agent 00 (Meta): src/weft/agents/meta.py
- Agent 01 (Architect): src/weft/agents/architect.py
- BaseAgent: src/weft/agents/base.py
- AIBackend: src/weft/ai/backend.py
- Queue operations: src/weft/queue/operations.py
- CLI commands: src/weft/cli/commands.py
- Config: .weftrc.yaml managed by src/weft/config.py
```

## Enhancement Goal

[What you want to add, improve, or change in Weft]

Example:
```
Add Agent 02 (Database Designer) that receives domain models from Agent 01
and generates database schemas including tables, relationships, indexes, and
migration strategies. Integrate with `weft feature start` orchestration.
```

## Requirements

List specific requirements:

- Functional requirement 1
- Functional requirement 2
- Non-functional requirement 1

Example:
```
- Extend BaseAgent class
- Load prompt spec from prompt-specs/v1.0.0/02_database.md
- Process domain models (input from Agent 01)
- Generate database schemas with:
  - Table definitions (columns, types, constraints)
  - Relationships (foreign keys, CASCADE rules)
  - Indexes (primary, unique, composite)
  - Migration strategy
- Integrate with `weft feature start` command
- Register in Weft agent registry
```

## Constraints

List constraints and limitations:

- Must follow pattern X
- Cannot change Y
- Must maintain compatibility with Z

Example:
```
- Must follow existing agent patterns (see meta.py, architect.py)
- Cannot modify BaseAgent interface
- Must maintain backward compatibility with Weft CLI
- Must achieve >= 90% test coverage
- Must include comprehensive documentation
- Must work with .weftrc.yaml configuration
```

## Success Criteria

Define what "done" looks like:

- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3

Example:
```
- [ ] Agent can process domain models from Architect
- [ ] Generates valid database schemas with all required sections
- [ ] Weft CLI integration works (`weft feature start` recognizes agent)
- [ ] Unit tests achieve >= 90% coverage
- [ ] Integration test demonstrates full workflow
- [ ] Documentation updated (CLI reference, agents guide)
- [ ] Prompt specification written and versioned
```

## Reference Implementation

Point to similar existing Weft code:

Example:
```
- Agent pattern: src/weft/agents/meta.py
- Agent pattern: src/weft/agents/architect.py
- BaseAgent: src/weft/agents/base.py
- Testing pattern: tests/test_meta_agent.py
- CLI integration: src/weft/cli/commands.py
```

## Additional Context

[Any other relevant information]

Example:
```
- Database schemas will be consumed by Agent 03 (UI) and Agent 04 (Integration)
- Output format should be markdown with SQL examples
- Consider both PostgreSQL and MySQL in design
- Should follow Weft's .weft/ directory structure conventions
```
