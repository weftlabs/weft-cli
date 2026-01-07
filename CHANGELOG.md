# Changelog

All notable changes to Weft will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-07

### Added
- Initial release of Weft CLI
- Structured, agent-based workflow for AI-assisted feature development
- Role-based AI agents for design, architecture, implementation, and validation
- Git-native feature workflow with isolated branches
- Human review gate before merge
- Docker-based isolated agent runtime
- Configuration via `.weftrc.yaml`
- CLI commands for creating, running, reviewing, and dropping features

### Documentation

- Installation and setup guide
- Agent workflow overview
- Configuration reference
- CLI command reference
- Architecture overview
- Troubleshooting guide
- Development and contribution guide

### Security

- No automatic code execution or merging
- Human-in-the-loop review by default
- API keys provided via environment variables
- AI interactions are auditable and inspectable

### Known limitations

As an initial release, Weft is under active development.
Some behaviors and interfaces may change before version 1.0.

[0.1.0]: https://github.com/weftlabs/weft-cli/releases/tag/v0.1.0
