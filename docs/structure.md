# Output Structure

Project Rules Generator writes generated artifacts into two locations inside your project, depending on which AI agent you use.

## Full Output Tree

```
.agents/
└── rules/
    └── <project-name>.md     # Auto-loaded agent rules (Always On)

.clinerules/
├── rules.json                # Machine-readable rules (used by planning commands)
├── auto-triggers.json        # Skill activation phrases (used by prg agent)
├── constitution.md           # Non-negotiable principles (--constitution flag)
├── clinerules.yaml           # Skill index for agents (written when skills present)
└── skills/
    ├── index.md              # Skills manifest (always generated)
    ├── project/              # Project-specific skills (High Priority)
    ├── learned/              # Global learned skills (Medium Priority)
    └── builtin/              # Core PRG skills (Low Priority)
```

## Two Output Paths Explained

### `.agents/rules/<project-name>.md` — Agent Auto-Load

This file is written so that Claude Code, Windsurf, and compatible agents pick it up **automatically** without any manual configuration. The agent marks it as "Always On" and injects the project context — stack, architecture, file structure, DOs/DON'Ts — at the start of every session.

This is the primary delivery mechanism for rules: you run `prg analyze` once and every future agent session starts context-aware.

See [`docs/agent_integration_guide.md`](agent_integration_guide.md) for details on how this injection works.

### `.clinerules/` — Cline / Skill System

This directory is consumed by Cline and any agent that reads `.clinerules/`. It contains the full skill system (builtin, learned, project layers) plus machine-readable rule files used by planning commands (`prg design`, `prg plan`, `prg agent`).

## File Descriptions

- **`rules.md`**: The core human-readable rules file. Contains critical "DOs" and "DON'T's", testing instructions, dependency information, and architectural overview. Always generated in `.clinerules/`.
- **`.agents/rules/<project-name>.md`**: Auto-loaded project rules for Claude Code / Windsurf. A copy of `rules.md` used for automatic context injection. Generated when `--ide antigravity` is passed to `prg analyze`.
- **`rules.json`**: Machine-readable version of rules, used by `prg plan` and `prg design` for task decomposition.
- **`auto-triggers.json`**: Lookup table mapping phrases to skill names. Used by `prg agent` for smart skill routing.
- **`constitution.md`**: High-level coding philosophy and non-negotiable principles. Generated with the `--constitution` flag.
- **`clinerules.yaml`**: Skill index written when skills are discovered. Used by agents to locate and load skills.
- **`skills/index.md`**: Skills manifest — always generated, lists all available skills across all layers.
- **`skills/project/`**: Auto-generated project-specific skills (highest priority). Written by `prg analyze`.
- **`skills/learned/`**: Your global reusable skills library (medium priority). Created with `--create-skill`.
- **`skills/builtin/`**: Battle-tested universal skills shipped with PRG (lowest priority).
- **`.prg-cache.json`**: Internal incremental cache. Add to `.gitignore` — not meant to be committed.

> **Note:** While `--ide` help text shows other values (`cline`, `cursor`, `vscode`), only `antigravity` has a custom registration implementation today. Other agents can still consume `.clinerules/` directly.

See [`CONTRIBUTING.md`](../CONTRIBUTING.md) § *Where `prg analyze` writes* for details on adding support for other IDE paths.
