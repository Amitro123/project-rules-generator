---
created: <% tp.date.now("YYYY-MM-DD") %>
status: draft
type: rules
project: <% tp.file.folder() %>
title: <% tp.file.title %>
---

# Project Rules: <% tp.file.title %>

<!--
TEMPLATE: RULES.md
PURPOSE: The single document an AI agent reads to understand how to work in
this project. Written for Claude / Cline / Cursor / Windsurf / Gemini consumption.
The output of this template is what `prg create-rules` produces and what lives
at `.clinerules/rules.md`.

WHEN TO USE: Once per project. Re-run `prg create-rules` to regenerate when
the codebase shifts substantially.

VALIDATION: PRG checks that every [REQUIRED] section is non-empty, Tech Stack
contains >=1 detected technology, DO and DON'T each contain >=1 rule, and no
`<!-- GUIDE -->` comments remain. Quality threshold default: 85 (configurable
via `--quality-threshold`).
-->

## Project Overview [REQUIRED]

<!--
GUIDE: 3-6 sentences. What this project IS (one sentence), what it DOES
(one sentence), and what an agent needs to know to start contributing.
RULES:
  - Open with the artifact type ("a Python CLI", "a React SPA", "a microservice").
  - Mention the primary user and the primary value.
  - Mention any non-obvious architectural choice (monorepo, plugin system, multi-tenant).
EXAMPLE:
  security_monitor is a Python 3.10+ daemon that runs on Linux hosts and detects
  suspicious authentication patterns in system logs. It tails /var/log/auth.log,
  applies a small set of detector rules, and dispatches alerts to webhooks. The
  primary users are platform engineers responding to security incidents. Architecture
  is a single-binary process with pluggable detectors and dispatchers loaded at
  startup. There is no UI, no database beyond local SQLite, and no horizontal scaling.
STATUS: [REQUIRED]
-->

## Tech Stack [REQUIRED]

<!--
GUIDE: The actual technologies in use, with versions when they matter for
correctness or compatibility.
RULES:
  - Group by layer: Language, Framework, Storage, Tooling, Deployment.
  - Pin versions for anything where major-version differences matter.
  - PRG fills this from package files when run automatically.
FORMAT:
  - **Language**: Python 3.10+
  - **Framework**: ...
  - **Storage**: ...
  - **Tooling**: ...
  - **Deployment**: ...
EXAMPLE:
  - **Language**: Python 3.10+
  - **Async**: asyncio (stdlib), aiofiles for file IO
  - **Storage**: SQLite via stdlib `sqlite3`
  - **Tooling**: pytest, black, ruff, isort, mypy
  - **Build/Package**: setuptools, pyproject.toml
  - **Deployment**: systemd unit on Ubuntu 22.04 hosts
STATUS: [REQUIRED] — must contain at least 1 technology.
-->

## Tools [REQUIRED]

<!--
GUIDE: The CLI commands an agent should expect to run during normal work.
This is what "make this change" actually executes against.
RULES:
  - Group by purpose: Build, Test, Lint, Run.
  - Include the exact command, not a paraphrase.
EXAMPLE:
  ### Install
  ```bash
  pip install -e .
  ```

  ### Run
  ```bash
  python -m security_monitor --config /etc/security-monitor.yaml
  ```

  ### Test
  ```bash
  pytest                          # full suite
  pytest tests/io/                # one module
  pytest --cov=security_monitor   # with coverage
  ```

  ### Lint / format
  ```bash
  black .
  ruff check .
  isort .
  ```
STATUS: [REQUIRED]
-->

## DO Rules [REQUIRED]

<!--
GUIDE: Things an agent SHOULD do when working in this project. Each rule
is a positive directive — phrase as an instruction.
RULES:
  - Format: "**DO** [action]. [Optional: rationale.]"
  - Group thematically (Code style, Testing, Architecture, Process).
  - 6-15 rules total. Quality > quantity.
  - Each rule must be specific to THIS project — no platitudes ("write good code").
EXAMPLE:
  ### Code Style
  - **DO** keep line length to 120 chars (black + ruff configured for this).
  - **DO** use type hints on all public functions; mypy runs in CI.
  - **DO** prefer dataclasses over dicts for structured payloads.

  ### Testing
  - **DO** add a test for every new detector; coverage gate is 85% on `detectors/`.
  - **DO** mock filesystem and network in unit tests; integration tests live in `tests/integration/`.

  ### Architecture
  - **DO** add new detectors as classes in `security_monitor/detectors/` implementing `BaseDetector`.
  - **DO** keep dispatchers stateless; persistence belongs in `security_monitor/storage/`.

  ### Process
  - **DO** add a CHANGELOG.md entry under Unreleased for every user-visible change.
  - **DO** run `pytest && black . && ruff check .` before committing.
STATUS: [REQUIRED] — must contain at least 1 rule.
-->

## DON'T Rules [REQUIRED]

<!--
GUIDE: Things an agent must NOT do. Each rule is a prohibition with
the failure mode it prevents.
RULES:
  - Format: "**DON'T** [action]. [Why this is harmful.]"
  - Caught from real mistakes the project has hit before.
  - 4-10 rules. More than 12 = the rules are too vague.
EXAMPLE:
  - **DON'T** add new top-level dependencies without justification in the PR description. Each dep is a supply-chain risk and must be deliberate.
  - **DON'T** swallow exceptions in detectors. A failing detector should log and re-raise — silent failures hid two incidents in Q1.
  - **DON'T** write blocking IO in async code paths. Use `aiofiles` or run in an executor.
  - **DON'T** introduce a second config file. All config goes in the single YAML loaded at startup.
  - **DON'T** rename frontmatter fields in templates without updating both the parser AND the validation rules.
  - **DON'T** lower the coverage gate or quality threshold without an explicit instruction in CHANGELOG.md.
STATUS: [REQUIRED] — must contain at least 1 rule.
-->

## Agent Skills [OPTIONAL]

<!--
GUIDE: Project-specific skills the agent should reach for. Lists the skill
name and when it applies. Only include skills that exist (or are planned).
RULES:
  - Format: "- `skill-name` — Use when [trigger].
  - Cross-reference the skill files in .claude/skills/ or wherever they live.
EXAMPLE:
  - `add-detector` — Use when the user wants to add a new detection pattern.
  - `wire-up-dispatcher` — Use when adding support for a new alert destination.
  - `audit-config` — Use when validating the YAML config against the schema.
STATUS: [OPTIONAL] — leave this section out entirely if there are no project skills yet.
-->

## Workflow [REQUIRED]

<!--
GUIDE: The expected sequence for any non-trivial change. Walks an agent
from "I have a task" to "PR is mergeable".
RULES:
  - Numbered steps. Concrete commands or actions, not philosophy.
  - 5-10 steps. End at a green PR / merged commit.
EXAMPLE:
  1. Read or create the relevant SPEC in `specs/`.
  2. Break the SPEC into TASKs in `tasks/` (one TASK per ~half-day of work).
  3. Branch from `main`: `git checkout -b feat/<short-name>`.
  4. Implement following the DO/DON'T rules above.
  5. Add or update tests. Run `pytest` — must pass.
  6. Run `black .`, `ruff check .`, `isort .` — must be clean.
  7. Update CHANGELOG.md under Unreleased.
  8. Commit with conventional-commits style: `feat(detectors): add brute-force-ssh`.
  9. Open PR. Request review. Address comments.
  10. Merge after approval and green CI.
STATUS: [REQUIRED]
-->
