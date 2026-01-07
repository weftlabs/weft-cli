# Weft Self-Development Quick Reference

## One-Time Setup

```bash
cd weft/  # The Weft repository
weft init
export WEFT_ANTHROPIC_API_KEY=sk-ant-...
weft up
```

## Self-Development Workflow

```bash
# 1. Prepare enhancement request
vim enhancement-request.md

# 2. Start self-development feature
weft feature start self-<name> --file enhancement-request.md

# 3. Review AI-generated outputs
cat .weft/self-<name>/spec.md      # Meta's understanding
cat .weft/self-<name>/design.md    # Architect's design

# 4. Implement the design
vim src/weft/...                    # Code
vim tests/...                       # Tests

# 5. Test
pytest tests/ -v

# 6. Commit
git add .
git commit -m "feat: <description>

Self-development design in .weft/self-<name>/"
git push origin feature/self-<name>
```

## Enhancement Request Template

```markdown
# Enhancement Request: [Feature Name]

## Current Weft System Context
- Component 1: src/weft/path/to/file.py
- Component 2: src/weft/path/to/other.py

## Enhancement Goal
[What to add/improve]

## Requirements
- Requirement 1
- Requirement 2

## Constraints
- Must follow Weft patterns
- Backward compatible
- Tests >= 90%

## Success Criteria
- [ ] Works as expected
- [ ] Tests pass
- [ ] Docs updated
```

## Naming Convention

**System enhancements MUST use `self-*` prefix:**

✅ Good:
- `self-add-database-agent`
- `self-improve-error-messages`
- `self-add-retry-logic`

❌ Bad (ambiguous):
- `add-database-agent`
- `improve-errors`

## Validation Checklist

### Meta Output (spec.md)
- [ ] Clear prompt for Architect
- [ ] Includes Weft context
- [ ] Lists requirements
- [ ] References Weft patterns

### Architect Output (design.md)
- [ ] Complete architecture
- [ ] Weft file paths
- [ ] Integration with Weft CLI
- [ ] Testing approach
- [ ] Implementation guidance

### Quality Check
- [ ] Implementable?
- [ ] Follows Weft patterns?
- [ ] All requirements covered?
- [ ] Edge cases considered?

## Common Commands

```bash
# Check Weft status
weft status

# List self-development features
ls -la .weft/self-*

# View feature artifacts
cat .weft/self-<name>/spec.md
cat .weft/self-<name>/design.md
cat .weft/self-<name>/history/*.log

# Run tests
pytest tests/test_*.py -v

# Check coverage
pytest --cov=src/weft --cov-report=term-missing
```

## File Paths Quick Reference

### Weft Source
- Agents: `src/weft/agents/`
- CLI: `src/weft/cli/`
- Config: `src/weft/config.py`
- Queue: `src/weft/queue/`
- AI Backend: `src/weft/ai/`

### Tests
- Unit tests: `tests/test_*.py`
- Integration: `tests/integration/`

### Documentation
- Architecture: `docs/01-architecture-and-agents.md`
- CLI Reference: `docs/cli-reference.md`
- Self-dev: `docs/weft-self-development.md`
- Workflow: `docs/self-development.md`

### Configuration
- Weft config: `.weftrc.yaml`
- Prompt specs: `prompt-specs/v1.0.0/`

## Tips

### Write Better Enhancement Requests
1. Be specific about Weft components
2. Reference existing Weft files
3. Include Weft file paths
4. Define clear success criteria
5. Consider Weft CLI integration

### Validate AI Outputs
1. Check Weft file paths are correct
2. Verify Weft patterns are followed
3. Ensure CLI integration is covered
4. Confirm tests are comprehensive

### Iterate if Needed
1. Review enhancement request
2. Add more Weft context
3. Reference more examples
4. Re-run `weft feature start`

## Related Documentation

- **Conceptual:** `docs/weft-self-development.md`
- **Detailed Workflow:** `docs/self-development.md`
- **Template:** `templates/weft-enhancement.md`
- **Example:** `examples/self-development/weft-session.md`
- **Best Practices:** `docs/self-development-guide.md`

## Support

For issues or questions:
- Read the docs: `docs/weft-self-development.md`
- Check examples: `examples/self-development/`
- Review validation report: `examples/self-development/validation-report.md`
