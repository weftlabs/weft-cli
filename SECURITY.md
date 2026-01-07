# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Currently supported versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue in Weft, please report it responsibly:

### Reporting Process

1. **Do NOT open a public GitHub issue** for security vulnerabilities
2. **Use GitHub's Security Advisory feature**:
    - Go to the [Security tab](https://github.com/weftlabs/weft-cli/security)
    - Click "Report a vulnerability"
    - Fill out the private security advisory form
3. **Or email directly** (if you prefer): [security@weftlabs.com](mailto:security@weftlabs.com)

### What to Include in Your Report

To help us triage and fix the issue quickly, please include:

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Affected versions** of Weft
- **Potential impact** (e.g., data exposure, code execution)
- **Suggested fix** (if you have one)
- **Your contact information** (for follow-up questions)

### Response Timeline

- **Initial response**: Within 48 hours
- **Status update**: Within 7 days
- **Fix timeline**: Depends on severity
  - **Critical**: Patch within 7 days
  - **High**: Patch within 30 days
  - **Medium/Low**: Addressed in next planned release

### Disclosure Policy

- Please give us reasonable time to fix the issue before public disclosure
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- Coordinated disclosure: We'll work with you on timing of public announcements

## Security Best Practices for Users

When using Weft, follow these security guidelines:

### API Keys and Secrets

- **Never commit API keys** to version control
- **Use environment variables**: Store `ANTHROPIC_API_KEY` in `.env` file (add to `.gitignore`)
- **Use dotenv files**: Keep `.env` outside of Git repositories
- **Rotate keys regularly**: Change API keys every 90 days as a best practice

### AI-Generated Code Review

- **Always review AI outputs** before accepting (human-in-the-loop is mandatory)
- **Check for security vulnerabilities**: SQL injection, XSS, command injection, etc.
- **Validate input handling**: Ensure generated code sanitizes user input
- **Review dependencies**: Check if AI suggests insecure or outdated packages

### Data Privacy

- **Avoid passing secrets** to AI agents in prompts
- **Don't include PII**: Keep user data and personally identifiable information out of prompts
- **Review logs**: AI history contains all prompts - ensure no sensitive data leaked
- **Use read-only mounts**: Docker configurations mount code repositories as read-only

### Docker and Container Security

- **Use read-only mounts** for code repositories (default configuration)
- **Run as non-root**: Container users should not have root privileges
- **Keep images updated**: Regularly pull latest base images
- **Limit network access**: Watchers only need API access, not full internet

### Git and Version Control

- **Validate AI-generated commits**: Review all code before merging to main branch
- **Use feature branches**: Worktrees isolate experimental code
- **Sign commits** (optional): Consider GPG signing for added verification
- **Audit AI history repo**: Regularly review AI history for unexpected changes

### Dependencies

- **Use lockfile**: Install from `requirements-lock.txt` for reproducible builds
- **Run security scans**: Use tools like `pip-audit` or `safety` to check for CVEs
- **Keep dependencies updated**: Update regularly but test thoroughly
- **Review transitive deps**: AI agents may suggest packages with vulnerable dependencies

## Known Security Considerations

### AI-Generated Code Risks

- **No sandbox execution**: AI-generated code is not run in a sandbox during review
- **Code quality varies**: AI may generate insecure patterns (SQL injection, XSS, etc.)
- **Dependency suggestions**: AI may suggest outdated or vulnerable packages
- **Mitigation**: Mandatory human review before accepting any AI outputs

### Data Sent to AI

- **Full feature specification**: Agent 00 receives your entire feature description
- **Previous outputs**: Subsequent agents receive outputs from earlier agents
- **Code context**: Integration agent may receive existing code patterns
- **Mitigation**: Avoid including secrets, PII, or proprietary algorithms in prompts

### Git Operations

- **Trust assumption**: Git operations assume trusted repository (no signature verification)
- **Merge conflicts**: Manual resolution required - potential for mistakes
- **Worktree isolation**: Features are isolated but share git object database
- **Mitigation**: Review all merges carefully, use protected branches

### Network and API

- **Claude API calls**: All AI processing goes through Anthropic's API
- **Retry logic**: Failed requests are retried automatically (may expose patterns)
- **Rate limiting**: Excessive requests may trigger rate limits
- **Mitigation**: API keys are never logged, use environment variables only

### Docker and File System

- **Shared volumes**: AI history repo is mounted read-write for watchers
- **File permissions**: Watchers write to filesystem (but only in designated directories)
- **Container escape**: Docker misconfigurations could allow container escape
- **Mitigation**: Use provided Docker Compose files, don't modify security settings

## Security Roadmap

### v0.2 (Planned)
- Add bandit SAST scanning to CI/CD
- Implement dependency vulnerability scanning (Snyk or Dependabot)
- Add security policy enforcement in pre-commit hooks

### v0.3 (Planned)
- Sandboxed code execution for AI-generated code review
- Static analysis of AI outputs before application
- Signature verification for AI history commits

### Future Enhancements
- Local LLM support (removes API dependency)
- End-to-end encryption for AI history
- Fine-grained access controls for multi-user deployments
- Audit logging with tamper-proof trail

## Security Contact

For urgent security issues, contact:

- **Email**: security@weftlabs.com
- **GPG Key**: [TBD]

For general security questions, open a discussion in GitHub Discussions.

---

**Last Updated**: 2025-12-31
**Security Policy Version**: 1.0
