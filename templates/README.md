# Weft Templates

This directory contains templates for self-development and other Weft workflows.

## Available Templates

### weft-enhancement.md
**Purpose:** Template for creating Weft system enhancement requests

**Use when:** You want to add a feature, agent, or improvement to Weft itself

**How to use:**
```bash
# Copy template
cp templates/weft-enhancement.md my-enhancement.md

# Fill in the template
vim my-enhancement.md

# Use with weft feature start
weft feature start self-my-enhancement --file my-enhancement.md
```

**Sections:**
- Current Weft System Context (with file paths)
- Enhancement Goal
- Requirements (functional and non-functional)
- Constraints (patterns, compatibility)
- Success Criteria (checkboxes)
- Reference Implementation (similar Weft code)
- Additional Context

### weft-self-development-cheatsheet.md
**Purpose:** Quick reference for self-development workflow

**Use when:** You need a quick reminder of commands and patterns

**Contents:**
- One-time setup commands
- Complete workflow steps
- Enhancement request template (inline)
- Naming conventions
- Validation checklist
- Common commands
- File path reference
- Tips and best practices

## Template Categories

### Self-Development Templates
Templates for enhancing Weft itself:
- `weft-enhancement.md` - Enhancement request template
- `weft-self-development-cheatsheet.md` - Quick reference

### Future Templates (Planned)
- Application feature request template (for user apps)
- Agent prompt specification template
- Test specification template
- Documentation template

## Usage Patterns

### Creating a New Enhancement Request

1. **Copy the template:**
   ```bash
   cp templates/weft-enhancement.md enhancements/add-retry-logic.md
   ```

2. **Fill in Weft-specific details:**
   - Reference actual Weft files (src/weft/...)
   - Use Weft terminology
   - Consider CLI integration
   - Include test requirements

3. **Start self-development:**
   ```bash
   weft feature start self-add-retry-logic --file enhancements/add-retry-logic.md
   ```

### Using the Cheat Sheet

Keep it open while working:
```bash
# Split terminal or separate window
cat templates/weft-self-development-cheatsheet.md
```

Or print for reference:
```bash
# Generate PDF (requires pandoc)
pandoc templates/weft-self-development-cheatsheet.md -o cheatsheet.pdf
```

## Best Practices

### When Creating Templates
1. **Be Specific:** Include Weft file paths and examples
2. **Be Complete:** Cover all necessary sections
3. **Be Clear:** Use examples to illustrate each section
4. **Be Consistent:** Follow Weft terminology and conventions

### When Using Templates
1. **Don't Skip Sections:** Fill out all required fields
2. **Be Detailed:** More context = better AI-generated designs
3. **Reference Code:** Point to existing Weft implementations
4. **Define Success:** Clear criteria prevent ambiguity

## Template Maintenance

### Updating Templates
When Weft's structure changes, update templates to reflect:
- New file paths
- New conventions
- New agents or features
- New configuration options

### Version History
Templates should be versioned with Weft:
- Update when Weft's architecture changes
- Document changes in git commits
- Reference template version in enhancement requests

## Related Documentation

- **Self-Development Guide:** `docs/weft-self-development.md`
- **Workflow Details:** `docs/self-development.md`
- **Examples:** `examples/self-development/`
- **Architecture:** `docs/01-architecture-and-agents.md`
