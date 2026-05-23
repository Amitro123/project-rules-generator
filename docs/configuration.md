# Configuration

PRG reads configuration from three layers, in order of precedence
(latest wins for any given key):

1. **CLI flags** — `prg analyze --flag value` (highest priority)
2. **Project-level `config.yaml`** — at the project root, optional
3. **User-level `~/.prg/ai_strategy.yaml`** — LLM routing preferences,
   optional
4. **Environment variables** — for API keys and provider selection
5. **Built-in defaults** — declared in `prg_utils/config_schema.py`

If a key isn't set anywhere, the built-in default applies. CLI flags
override every other source for that single run; persistent settings
go in `config.yaml`.

This document covers every persistent setting. For one-shot flags, run
`prg analyze --help`.

---

## Project-level `config.yaml`

PRG looks for `config.yaml` at the project root when `prg analyze` runs.
The schema is enforced by Pydantic in `prg_utils/config_schema.py`; an
invalid file raises a clear `ValidationError` rather than silently
falling back.

### Full example

```yaml
llm:
  enabled: false                    # whether to call an LLM at all
  provider: anthropic               # anthropic | gemini | groq | openai
  model: claude-3-5-sonnet-20241022
  api_key: null                     # prefer env var (see below)

git:
  auto_commit: true                 # auto-commit generated files
  commit_message: "Auto-generated rules and skills"
  commit_user_name: "Project Rules Generator"
  commit_user_email: "rules@generator.local"

generation:
  output_format: markdown           # markdown | json | yaml
  include_examples: true
  verbose: true
  max_feature_count: 5              # int 1-20
  max_description_length: 200       # int 50-1000

packs:
  enabled: true                     # load external skill packs
  sources:                          # list of pack names/paths
    - team-defaults
    - ./packs/internal-skills

skill_sources:
  builtin:
    enabled: true
    path: templates/skills          # relative to project root or absolute
  learned:
    enabled: true
    path: ~/.project-rules-generator/learned_skills
    auto_save: true                 # save newly-generated skills here
  awesome:
    enabled: false
    path: ""
  preference_order:                 # higher = more specific wins
    - learned
    - awesome
    - builtin
```

### Section reference

#### `llm`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | bool | `false` | Master switch. `false` means PRG never calls an LLM, even with `--ai`. |
| `provider` | enum | `anthropic` | One of `anthropic`, `gemini`, `groq`, `openai`. Overridden by `--provider` on the CLI. |
| `model` | str | `claude-3-5-sonnet-20241022` | Model identifier for the chosen provider. |
| `api_key` | str \| null | `null` | Prefer the env var (see below). Hardcoding here works but the value is read by anyone with repo access. |

#### `git`

| Field | Type | Default | Notes |
|---|---|---|---|
| `auto_commit` | bool | `true` | When true, `prg analyze` commits generated files via `git`. `--no-commit` overrides per-run. |
| `commit_message` | str | `"Auto-generated rules and skills"` | First line of the commit. The body is auto-generated. |
| `commit_user_name` | str | `"Project Rules Generator"` | Used for the commit `author`/`committer` fields. |
| `commit_user_email` | str | `"rules@generator.local"` | Used for the commit `author`/`committer` fields. |

If your project has a [conventional-commits](https://www.conventionalcommits.org/) hook,
edit `commit_message` to a `feat:` / `chore:` form so the hook doesn't reject the
auto-commit (a real-world bug — see `ListOfBugs/Bug4.md`).

#### `generation`

| Field | Type | Default | Range |
|---|---|---|---|
| `output_format` | enum | `markdown` | `markdown` \| `json` \| `yaml` |
| `include_examples` | bool | `true` | Include code snippets in generated skills. |
| `verbose` | bool | `true` | Default verbose level for generation; CLI `--quiet` overrides. |
| `max_feature_count` | int | `5` | 1-20 |
| `max_description_length` | int | `200` | 50-1000 chars |

#### `packs`

External skill packs are reusable bundles of skills + rules that other
teams have shipped. PRG can load them at runtime to extend the
detection vocabulary.

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | bool | `true` | Master switch for pack loading. |
| `sources` | list[str] | `[]` | Each item is a pack name (resolved via `pack_manager.find_pack`) or an absolute / relative directory path. |

CLI `--include-pack <name>` adds packs ad-hoc without editing config.

#### `skill_sources`

PRG looks for skills in three layered sources. `preference_order` decides
which wins when the same skill name exists in multiple sources.

| Source | Default `enabled` | Default `path` | Purpose |
|---|---|---|---|
| `builtin` | `true` | `templates/skills` | Ships with PRG. Universal. |
| `learned` | `true` | `~/.project-rules-generator/learned_skills` | Per-user; populated by `--save-learned` and `prg skills save`. |
| `awesome` | `false` | `""` | Optional integration with external "awesome" skill lists. |

`preference_order` defaults to `["learned", "awesome", "builtin"]` —
your own learned skills override anything else with the same name.

---

## Environment variables

API keys and provider selection should live in the environment, not in
`config.yaml`, so they don't leak into git history.

| Variable | Used for | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic Claude calls | Required when `provider: anthropic` and `enabled: true`. |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini calls | PRG also reads `GOOGLE_API_KEY`; if both are set, `GOOGLE_API_KEY` wins (with a warning). Set only one to avoid the warning. |
| `GROQ_API_KEY` | Groq calls | Required when `provider: groq`. |
| `OPENAI_API_KEY` | OpenAI calls | Required when `provider: openai`. |
| `PRG_TEST_PROJECT_PATHS` | Test harness (developers only) | Semicolon-separated list of project paths to run the generic property tests against. See `tests/test_project_profile_property.py`. |

The CLI flag `--api-key <key>` overrides whatever's in the environment
for one run only.

---

## `~/.prg/ai_strategy.yaml` — LLM routing

When you have multiple LLM providers configured, PRG can route different
task kinds to different providers (e.g. `groq` for fast skill matching,
`anthropic` for high-quality plan generation). This config is per-user,
not per-project.

### Example

```yaml
# ~/.prg/ai_strategy.yaml

default_strategy: auto              # auto | speed | quality

# Per-strategy provider preference (first available wins)
strategies:
  speed:
    - groq
    - gemini
  quality:
    - anthropic
    - openai
  auto:
    # 'auto' picks the first provider with credentials present
    - anthropic
    - gemini
    - groq
    - openai

# Per-task overrides (optional). Task names match generator pipeline phases.
task_overrides:
  plan_decomposition: quality       # always use the 'quality' strategy here
  skill_matching: speed             # but speed for matching
```

CLI `--strategy <name>` overrides `default_strategy` for one run.

### When you need this

Most users don't. The defaults route to whichever provider has
credentials in the environment. Edit `ai_strategy.yaml` only if:

- You have multiple providers configured and want explicit routing
- You want to force a specific provider for a specific task kind
- You want to opt out of `auto` and pin to one provider

---

## Built-in defaults reference

Every setting above has a built-in default declared in
[`prg_utils/config_schema.py`](../prg_utils/config_schema.py). Reading
that file is the source of truth — if anything in this document
disagrees with the Pydantic models, the models win.

A handful of pipeline-internal thresholds (LLM truncation retries, Ralph
emergency-stop scores, subprocess timeouts) are declared as named module
constants — see `generator/ralph/engine.py:27-40` and
`generator/ai/hardening.py`. These aren't typically user-tunable; they're
documented in their source files for maintainers.

---

## See also

- [`README.md`](../README.md) — quick start
- [`docs/cli.md`](cli.md) — every CLI command and flag
- [`docs/structure.md`](structure.md) — what PRG writes and where
- [`docs/llm-router.md`](llm-router.md) — deeper dive on the AI strategy
  router
- [`prg_utils/config_schema.py`](../prg_utils/config_schema.py) — the
  Pydantic source of truth
