# Templates

Strict markdown templates used by humans (in Obsidian via Templater) and by PRG (`prg analyze --ai`, `prg create-rules`) to produce structured artifacts with the same shape every time.

For when-to-use guidance, Templater setup, and PRG integration details, see [`TEMPLATE-GUIDE.md`](./TEMPLATE-GUIDE.md).

## Templates

| File | Purpose |
| --- | --- |
| [`SPEC.md`](./SPEC.md) | Full feature/project specification (7 sections). |
| [`SPEC.short.md`](./SPEC.short.md) | 3-section quick spec for small, well-understood changes. |
| [`TASK.md`](./TASK.md) | Full implementation task (Summary, Context, Steps, Dependencies, DoD, Notes). |
| [`TASK.short.md`](./TASK.short.md) | 3-section quick task for typo fixes, dep bumps, one-file changes. |
| [`PLAN.md`](./PLAN.md) | Multi-phase delivery plan (Overview, Phases, Risks, Assumptions, Open Questions). |
| [`SKILL.md`](./SKILL.md) | Strict agent-skill template with inline validation rules. |
| [`RULES.md`](./RULES.md) | Project rules template — output target is `.clinerules/rules.md`. |
| [`TEMPLATE-GUIDE.md`](./TEMPLATE-GUIDE.md) | How to use these templates in Obsidian, in PRG, and how to add new ones. |

## Examples

| File | What it shows |
| --- | --- |
| [`examples/security_monitor-SPEC.md`](./examples/security_monitor-SPEC.md) | A fully filled-in SPEC.md for an illustrative `security_monitor` project. |
| [`examples/security_monitor-TASK.md`](./examples/security_monitor-TASK.md) | A TASK.md derived from that spec. |

## Conventions enforced across all templates

- YAML frontmatter with `created`, `status`, `type`, `project`, `title`.
- Sections marked `[REQUIRED]` or `[OPTIONAL]` in the H2 line.
- Inline HTML comments per section containing `GUIDE`, `RULES`, `EXAMPLE`, `STATUS`. These are removed when the section is filled.
- Templater syntax for dynamic values: `<% tp.date.now("YYYY-MM-DD") %>`, `<% tp.file.title %>`, `<% tp.file.folder() %>`.

## Validation

Every template documents its validation rules in its own leading HTML comment block. PRG enforces them via `generator/utils/quality_checker.py`. The shared rules:

1. All `[REQUIRED]` sections must be non-empty.
2. No `<!-- GUIDE -->` HTML comments may remain in the filled file.
3. Per-template rules (e.g., "Acceptance Criteria must have ≥1 checkbox") are listed in the leading comment of each template.
