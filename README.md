# Project Rules Generator

> **Stop re-explaining your project to every AI agent.** PRG scans your repo once and emits `.clinerules/` — structured rules, skills, and conventions as portable Markdown. Cline reads `.clinerules/` natively, `--ide antigravity` auto-registers them for Antigravity, and any agent (Claude, Cursor, Windsurf, Copilot) can load them as context. Works offline; LLM-augmented with a free API key.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/Amitro123/project-rules-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/Amitro123/project-rules-generator/actions/workflows/ci.yml)

```bash
pip install project-rules-generator && cd your-project && prg init .
```

![Screenshot: `prg analyze` running on a Python project, detecting the tech stack and writing rules.md, clinerules.yaml, and skills/ into .clinerules/](docs/assets/prg-analyze-demo.png)

<!-- TODO(demo): replace the static PNG above with a ~10s asciinema cast of `prg init . && prg analyze .` on a fresh repo. Embed via <a href="https://asciinema.org/a/XXXXX"><img src="https://asciinema.org/a/XXXXX.svg" /></a>. -->

---

## The Problem

Every AI agent you use — Claude, Cursor, Windsurf, Copilot — starts every conversation knowing **nothing** about your project.

You explain your stack. Again. You correct the same bad patterns. Again. You watch it generate code that ignores your architecture. Again.

The AI isn't dumb. It's **context-blind.**

---

## The Solution

**Project Rules Generator (PRG)** generates structured memory artifacts for AI coding agents — rules, skills, plans, and specs that any agent (Claude, Cursor, Windsurf, Copilot) can consume.

Run it once. Every future AI session starts with project context: your stack, your conventions, your architecture, your do's and don'ts.

```bash
cd your-project
prg init .
```

Your `.clinerules/` is now the memory your AI agents never had. Generate the artifacts, then let any agent consume them — or optionally run Ralph to execute autonomously on top of them.

---

## Quick Start

**No API key needed** — `prg init` and `prg analyze` work fully offline from your README and file structure:

```bash
pip install project-rules-generator
prg init .
prg analyze .
```

**With a free API key** — LLM-generated skills, richer analysis, and the planning commands:

```bash
export GROQ_API_KEY=gsk_...   # free at console.groq.com
prg analyze . --ai
prg design "Add OAuth2 login"   # requires API key
prg plan "Add OAuth2 login"     # requires API key
```

| Command | Offline | Requires API key |
|---------|:-------:|:----------------:|
| `prg init` / `prg analyze` | ✓ | — |
| `prg watch` | ✓ | — |
| `prg design` / `prg plan` | — | ✓ |
| `prg review` | — | ✓ |
| `prg analyze --ai` | — | ✓ |

**Optionally, run Ralph** — an autonomous execution loop that reads your generated artifacts and iterates until the feature is done:

```bash
prg feature "Add OAuth2 login"         # Set up feature branch + state
prg ralph run FEATURE-001              # Autonomous loop (no per-task prompts)
prg ralph approve FEATURE-001          # Human approval → merge to main
```

See [`docs/quick-start.md`](docs/quick-start.md) for the full guide.

---

## See It In Action

```
$ cd my-fastapi-project
$ prg init .
✓ Detected stack: Python · FastAPI · pytest · Docker
✓ Generated .clinerules/rules.md          (21 rules)
✓ Generated .clinerules/clinerules.yaml
→ Next: run `prg analyze . --ai` to add skills (free Groq key)

$ export GROQ_API_KEY=gsk_...
$ prg analyze . --ai
Analyzing project context...
✓ Rules updated                            (24 rules)
✓ Skills matched: test-driven-development, code-review, systematic-debugging
✓ Skill generated: fastapi-endpoints       (.clinerules/skills/learned/)
✓ Skill generated: pydantic-validation     (.clinerules/skills/learned/)
✓ Wrote .clinerules/clinerules.yaml        (project: 2 · learned: 2 · builtin: 3)

Cline & Antigravity load these automatically; point any agent at .clinerules/.
Ask it to "add a login endpoint" — it will use async SQLAlchemy,
Pydantic response models, and place the route in the right module.
```

**PRG analyzing itself** — real terminal output, no staging:

![PRG Analyze Demo](docs/assets/prg-analyze-demo.png)

---

## What Gets Generated

PRG writes `.clinerules/` (works with any agent) and optionally `.agents/rules/<project-name>.md` (for Antigravity IDE integration).

```text
.clinerules/
├── rules.json      ← Machine-readable rules
├── constitution.md  ← Non-negotiable principles (--constitution)
├── clinerules.yaml  ← Skill index for agents
└── skills/
    ├── project/     ← AI-generated, tailored to YOUR project
    ├── learned/     ← Reusable patterns, shared across projects
    └── builtin/     ← Battle-tested best practices, bundled
```

See [`docs/structure.md`](docs/structure.md) for a full breakdown of every file and location.

---

## AI Providers

PRG auto-detects the best available provider from your environment. Set one key, or set several — it routes intelligently.

| Provider | Model | Best For | Key |
|:---------|:------|:---------|:----|
| **Anthropic** | Claude Sonnet 4.6 | Highest quality rules & skills | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4o-mini | Solid all-rounder | `OPENAI_API_KEY` |
| **Gemini** | Gemini 2.0 Flash | Fast + high quality | `GEMINI_API_KEY` |
| **Groq** | Llama 3.1 8b | Free tier, fastest | `GROQ_API_KEY` |

No provider? `prg init` and `prg analyze` still work offline. `prg design`, `prg plan`, and `prg review` require a key.

```bash
prg providers list       # See what's configured
prg providers test       # Live latency check
prg providers benchmark  # Side-by-side quality ranking
```

---

## Key Concepts

- **3-Layer Skill System** — project > learned > builtin priority. See [`docs/skills.md`](docs/skills.md).
- **All Commands** — full CLI reference with examples. See [`docs/cli.md`](docs/cli.md).
- **How Analysis Works** — strategy chain and quality gate. See [`docs/architecture.md`](docs/architecture.md).
- **Ralph** — autonomous feature loop. See [`docs/ralph.md`](docs/ralph.md).
- **Two-Stage Planning** — `prg design` + `prg plan`. See [`docs/plan-and-design.md`](docs/plan-and-design.md).

---

## Installation

**From PyPI (recommended):**

```bash
pip install project-rules-generator
prg --version
```

**From source (contributors):**

```bash
git clone https://github.com/Amitro123/project-rules-generator
cd project-rules-generator
pip install -e .
prg --version
```

**Requirements:** Python 3.10+, Git

---

## Project Status

**Alpha** — core analysis, rules generation, and skill management are stable. The planning pipeline (`prg plan`, `prg design`) and autonomous loop (`prg ralph`) are in active development.

| Area | Status |
|------|--------|
| `prg init` / `prg analyze` / `prg create-rules` | ✅ Stable |
| `prg skills *` / `prg agent` | ✅ Stable |
| `prg plan` / `prg design` / `prg review` | 🚧 Beta |
| `prg ralph` / `prg feature` | 🚧 Experimental |
| IDE registration (`--ide antigravity`) | ✅ Implemented |
| IDE registration (cursor / windsurf / vscode) | 📋 Planned — PRs welcome |

**Known limitations:** See [`docs/KNOWN-ISSUES.md`](docs/KNOWN-ISSUES.md).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide: dev setup, how to add a command, how the skill system works, and testing rules.

```bash
pytest                              # run tests
black . && ruff check . && isort .  # format (required before commit)
```

See [`docs/index.md`](docs/index.md) for all documentation.

---

## License

MIT — see [`LICENSE`](LICENSE).

---

> Full version history: [`CHANGELOG.md`](CHANGELOG.md) · Architecture: [`docs/architecture.md`](docs/architecture.md) · Feature deep-dives: [`docs/features.md`](docs/features.md)
