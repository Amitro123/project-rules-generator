# Project Rules Generator 🚀

> **The First AI That Learns Your Coding Style**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-512%20Passing-green.svg)](tests/)

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
- **Context Awareness**: Reads your README & structure instead of using generic templates.
- **Memory**: Learns across ALL projects, not just one.
- **Expert Skills**: Generates advanced rules like "Optimize FFmpeg for ML" instead of just "Use React".
- **Smart Router**: Auto-selects the best available AI provider with graceful fallback.
- **Git Integration**: Auto-commits changes with smart `.gitignore` handling.
- **Constitution**: Automatically generates project `constitution.md` principles.
- **Incremental**: Fast! Updates only changed files or skills.
- **Context Optimization**: Smart `.clinerules.yaml` exclusions.

---

## Quick Start
Generate rules for your current project — no API key required:

```bash
prg analyze . --no-commit
```
*This generates `.clinerules/rules.md` and `.clinerules/skills/index.md` from your project structure and README.*

With an API key, add `--ai` for deeper analysis:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
prg analyze . --ai
```

---

## Installation

### Prerequisites
- Python 3.8 or higher
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

| Provider | Quality | Speed | Key Variable |
|:---|:---:|:---:|:---|
| **Anthropic** (Claude 3.5 Sonnet) | ⭐95 | 65 | `ANTHROPIC_API_KEY` |
| **OpenAI** (GPT-4o-mini) | ⭐90 | 70 | `OPENAI_API_KEY` |
| **Gemini** (2.0 Flash) | ⭐85 | 85 | `GEMINI_API_KEY` |
| **Groq** (Llama 3.1-8b) | ⭐75 | 95 | `GROQ_API_KEY` |

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
# Generate a plan from a description
prg plan "Add OAuth2 authentication"

# Check progress on the current plan
prg status

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

PRG operates on a 3-layer architecture for skill resolution:
1. **Project** (`.clinerules/skills/project/`): High priority overrides.
2. **Global Learned** (`~/.project-rules-generator/learned/`): Your personal library.
3. **Builtin** (`~/.project-rules-generator/builtin/`): Default best practices.

```mermaid
graph TB
    A[prg analyze . --ai] --> B[AIStrategyRouter]
    B --> C{Best provider?}
    C -->|ANTHROPIC_API_KEY set| D[Claude 3.5 Sonnet]
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
    ├── project/          # Project-specific overrides (Highest Priority)
    ├── learned/          # Global learned skills (Medium Priority)
    └── builtin/          # Core PRG skills (Lowest Priority)
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