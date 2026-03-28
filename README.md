# Project Rules Generator 🚀

> **The First AI That Learns Your Coding Style**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-500%20Passing-green.svg)](tests/)

Most rule generators give you static templates. **Project Rules Generator (PRG)** reads your code, understands your architecture, and **learns from your patterns** to create smarter, context-aware `.clinerules` for any AI agent (Claude, Cursor, Windsurf, Gemini).

---

## Table of Contents
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [AI Providers](#ai-providers)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Contributing](#contributing)

---

## Features

| Feature | Description | AI Required |
|:--------|:------------|:-----------:|
| **Basic Analysis** | Scans code structure & README, generates `rules.md` | No |
| **AI Skills** | LLM-generated workflow skills tailored to your project | Yes |
| **Incremental** | Re-generates only changed sections — 3–5x faster | No |
| **Constitution** | Generates `constitution.md` coding principles | No |
| **Planning** | `prg plan` breaks a task into subtasks with `PLAN.md` | Yes |
| **Two-Stage Design** | `prg design` → `prg plan` for complex features | Yes |
| **Autopilot** | End-to-end discovery → plan → execute loop | Yes |
| **Project Manager** | Full lifecycle orchestration (Setup → Verify → Exec → Report) | Yes |
| **Smart Router** | Auto-selects best available provider; falls back gracefully | — |

---

## Quick Start
The fastest way to get started — no API key required:

```bash
cd /path/to/your-project
prg init .
```
*Detects your stack, generates `.clinerules/rules.md` from your README and file structure, and prints next steps.*

With an API key, add `--ai` for deeper analysis:
```bash
export GROQ_API_KEY=gsk_...   # free — get one at console.groq.com
prg analyze . --ai
```

---

## Installation

### Prerequisites
- Python 3.11 or higher
- Git

### From Source (Current)
```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
```

Verify the installation:
```bash
prg --version
```

---

## AI Providers

PRG automatically routes to the best available provider based on your environment variables.

| Provider | Model | Quality | Speed | Key Variable |
|:---|:---|:---:|:---:|:---|
| **Anthropic** | Claude Sonnet 4.6 | ⭐95 | 65 | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4o-mini | ⭐90 | 70 | `OPENAI_API_KEY` |
| **Gemini** | Gemini 2.0 Flash | ⭐85 | 85 | `GEMINI_API_KEY` |
| **Groq** | Llama 3.1 8b | ⭐75 | 95 | `GROQ_API_KEY` |

**Auto-detection**: PRG reads your env vars and picks the best available provider automatically.

```bash
# Set one or more keys — PRG handles the rest
export ANTHROPIC_API_KEY=sk-ant-...
export GROQ_API_KEY=gsk_...
```

```bash
# Check which providers are ready
prg providers list

# Run a live connectivity test
prg providers test
```

> See [docs/llm-router.md](docs/llm-router.md) for full routing configuration.

---

## Usage

### 1. AI-Powered Analysis & Skills
Uses the best available AI provider to deeply understand your project or generate specific skills.

```bash
# Analyze project (auto-selects best provider)
prg analyze . --ai

# Create a named skill using AI
prg analyze . --create-skill "design-token-parser" --ai

# Force a specific provider or control strategy
prg analyze . --ai --strategy speed
prg analyze . --ai --provider anthropic
```

*Note: No API key required for basic README-only generation:*
`prg analyze . --create-skill "ui-tokens" --from-readme README.md`

### 2. Incremental Update ⚡
Updates only what has changed since the last run. Perfect for CI/CD.

```bash
prg analyze . --incremental
```

### 3. Constitution Mode 📜
Generates a `constitution.md` with your project's core coding principles.

```bash
prg analyze . --constitution
```

### 4. Planning & Task Tracking
Break a task into subtasks, track progress, and execute step-by-step.

```bash
# Optional: generate an architectural design first (Stage 1)
prg design "Add OAuth2 authentication"

# Generate an implementation plan (Stage 2, or standalone)
prg plan "Add OAuth2 authentication"

# Execute the next pending task
prg next
```

### 5. Autopilot 🤖
Full autonomous mode: discover, plan, execute — all with git safety.

```bash
prg autopilot .
```

### 6. Provider Management
```bash
prg providers list                 # Rich table of all providers
prg providers test                 # Live connectivity + latency
prg providers test --provider groq # Test a specific provider
prg providers benchmark            # Rank by quality/speed composite
```

---

## How It Works

PRG operates on a 3-layer architecture for skill resolution (highest → lowest priority):
1. **Project** (`.clinerules/skills/project/`): Skills created with `--create-skill` — AI-generated with your project's context, project-specific.
2. **Learned** (`.clinerules/skills/learned/`): Reusable tech-pattern skills from the README auto-flow, shared across projects.
3. **Builtin** (`~/.project-rules-generator/builtin/`): Default best practices bundled with PRG.

```mermaid
graph TB
    A[prg analyze . --ai] --> B[AIStrategyRouter]
    B --> C{Best provider?}
    C -->|ANTHROPIC_API_KEY set| D[Claude Sonnet 4.6]
    C -->|GROQ_API_KEY set| E[Llama 3.1-8b]
    C -->|no keys| F[README-only mode]
    D --> G[.clinerules/rules.md + skills/]
    E --> G
    F --> G
```

### Output Structure
All generated files are consolidated into a single `.clinerules/` directory:
```text
.clinerules/
├── rules.md              # Main rules (from any mode)
├── constitution.md       # Code principles (when --constitution)
├── clinerules.yaml       # Lightweight YAML skill references
├── auto-triggers.json    # Skill activation trigger phrases
└── skills/
    ├── project/          # --create-skill output, project-specific (Highest Priority)
    ├── learned/          # README-flow tech-pattern skills, reusable (Medium Priority)
    └── builtin/          # Bundled best-practice skills (Lowest Priority)
```

---

## Contributing
We welcome contributions!
1. Fork the repo
2. Create your feature branch (`git checkout -b feat/amazing-feature`)
3. Run the test suite before committing: `pytest`
4. Ensure formatting passes: `black . && ruff check . && isort .`
5. Commit using conventional commits: `git commit -m "feat: add amazing feature"`
6. Push to the branch and open a PR.

See [`CLAUDE.md`](CLAUDE.md) for architecture notes and coding conventions.

---

**Project Rules Generator** — Because generic "analyze code" skills aren't enough anymore.

> Full version history: [`CHANGELOG.md`](CHANGELOG.md)