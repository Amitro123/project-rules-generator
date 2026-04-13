# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 0.3.x   | ✅ Yes    |
| < 0.3   | ❌ No     |

## Scope

This project executes subprocess commands (git, editors), reads and writes files, and optionally calls external LLM APIs. Relevant security areas include:

- **Path traversal** — file read/write operations use `Path.resolve()` and base-path validation
- **Command injection** — all subprocess calls use list arguments, never `shell=True`
- **API key exposure** — keys are read from environment variables only, never hardcoded
- **Dependency vulnerabilities** — report outdated or vulnerable dependencies

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report privately via one of:
- **GitHub private vulnerability reporting** (preferred): [Security Advisories](../../security/advisories/new)
- **Email**: open a GitHub issue asking for a private contact channel

Include:
1. A description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. (Optional) suggested fix

You can expect an acknowledgement within **72 hours** and a fix or mitigation plan within **14 days** for confirmed vulnerabilities.
