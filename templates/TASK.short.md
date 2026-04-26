---
created: <% tp.date.now("YYYY-MM-DD") %>
status: draft
type: task
project: <% tp.file.folder() %>
title: <% tp.file.title %>
variant: short
---

# Task: <% tp.file.title %>

<!--
TEMPLATE: TASK.short.md (3-section quick variant)
WHEN TO USE: A small change with no real ambiguity — a typo fix, a dependency
bump, a small refactor, a one-file addition. For anything bigger, use TASK.md.
VALIDATION: All three sections [REQUIRED]. Steps must contain >=1 checkbox.
No `<!-- GUIDE -->` comments may remain.
-->

## What [REQUIRED]

<!--
GUIDE: 1-2 sentences. What gets done, where, and (if not obvious) why.
RULES:
  - Start with a verb.
  - Name the concrete file/module/endpoint.
EXAMPLE:
  Bump `httpx` from 0.27 to 0.28 in `requirements.txt` and pin the lockfile,
  to pick up the fix for the connection-pool leak we hit last week.
STATUS: [REQUIRED]
-->

## Steps [REQUIRED]

<!--
GUIDE: 2-6 numbered, checkable actions.
RULES:
  - One verb per step.
  - End with a verification step.
FORMAT:
  - [ ] 1. ...
  - [ ] 2. ...
EXAMPLE:
  - [ ] 1. Update `httpx==0.28.*` in `requirements.txt`.
  - [ ] 2. Run `pip-compile` to regenerate `requirements.lock`.
  - [ ] 3. `pytest` — full suite, must pass.
  - [ ] 4. `black`, `ruff check`, `isort` — must be clean.
  - [ ] 5. Commit with message `chore(deps): bump httpx to 0.28`.
STATUS: [REQUIRED] — must contain at least 1 checkbox.
-->

## Done When [REQUIRED]

<!--
GUIDE: 1-3 binary checks. Don't conflate with Steps — these are outcome checks.
EXAMPLE:
  - [ ] CI is green on the PR.
  - [ ] No new deprecation warnings introduced.
  - [ ] CHANGELOG entry added under Unreleased > Changed.
STATUS: [REQUIRED] — must contain at least 1 checkbox.
-->
