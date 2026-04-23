# `.clinerules/` — Showcase output, not source

This directory is **generated output** from running PRG against its own
codebase (self-dogfooding). It exists in the repo so first-time visitors can
see concrete examples of what `prg analyze` and `prg create-rules` produce —
not because it is hand-maintained.

## Do not edit these files by hand

Any direct edit will be overwritten the next time the maintainer runs:

```bash
prg analyze . --ide antigravity
prg create-rules .
```

If you want to change what PRG emits, modify the **generators** — not the
output:

| To change…                          | Edit…                                                        |
|-------------------------------------|--------------------------------------------------------------|
| Built-in skill content              | `generator/skills/builtin/<skill>/SKILL.md`                  |
| Skill YAML scaffolds                | `generator/templates/skills/<tech>.yaml`                     |
| Skill/rules rendering templates     | `generator/templates/SKILL.md.jinja2`, `RULES.md.jinja2`     |
| Quality checks (what passes a gate) | `generator/utils/quality_checker.py`                         |
| Tech detection                      | `generator/utils/tech_detector.py`                           |

## What lives here

```
.clinerules/
├── constitution.md            # Non-negotiable coding rules for AI agents
├── skills/
│   ├── builtin/               # Ships with PRG — shipped as the examples layer
│   ├── learned/               # Inferred from project signals (LLM-assisted)
│   └── project/               # Generated from the repo's actual README/structure
└── README.md                  # This file
```

Transient artifacts such as `rules.md`, `clinerules.yaml`, and
`auto-triggers.json` are **gitignored** — they are regenerated on every run.

## Philosophy

Keeping a curated example set in-tree is a deliberate choice: visitors can
inspect a realistic `.clinerules/` without having to install the tool first.
The trade-off is that regeneration occasionally produces noisy diffs — those
are expected and usually not reviewed line-by-line.

If you want a hand-curated reference set instead, see
[`docs/AUTHORING-SKILLS.md`](../docs/AUTHORING-SKILLS.md) for the canonical
skill shape and conventions.
