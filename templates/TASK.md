---
created: <% tp.date.now("YYYY-MM-DD") %>
status: draft
type: task
project: <% tp.file.folder() %>
title: <% tp.file.title %>
---

# Task: <% tp.file.title %>

<!--
TEMPLATE: TASK.md (full)
PURPOSE: A single, executable unit of implementation work. Lives below a SPEC.
WHEN TO USE: Anything taking >2 hours, anything touching >1 file in non-obvious ways,
or anything with non-trivial dependencies. For tiny one-shot work, use TASK.short.md.
VALIDATION: PRG checks that Steps contains >=1 checkbox, Definition of Done contains
>=1 checkbox, and no `<!-- GUIDE -->` comments remain.
-->

## Summary [REQUIRED]

<!--
GUIDE: One sentence. What gets built/changed and where. Read this in isolation —
does someone unfamiliar know what this task is about?
RULES:
  - Start with a verb (Add, Refactor, Wire up, Fix, Migrate).
  - Name the concrete artifact (file, module, endpoint).
  - No "why" — that goes in Context.
EXAMPLE:
  Add a `LogTailer` class in `security_monitor/io/tailer.py` that streams new
  lines from a rotating log file using inode-aware reopen.
STATUS: [REQUIRED]
-->

## Context [REQUIRED]

<!--
GUIDE: 2-4 sentences. Why this task exists, what spec or upstream work it
serves, and what someone would need to know to start.
RULES:
  - Link to the parent SPEC if there is one (use a wikilink: [[security_monitor-SPEC]]).
  - Mention the existing code that's relevant.
  - Skip restating things already in the spec.
EXAMPLE:
  Implements the log-ingestion piece of [[security_monitor-SPEC]]. The detector
  module is being written in parallel and consumes lines via an async iterator,
  so the tailer should expose `async def stream_lines() -> AsyncIterator[LogLine]`.
  Existing pattern to mirror: `prg_utils/file_watcher.py`.
STATUS: [REQUIRED]
-->

## Steps [REQUIRED]

<!--
GUIDE: Ordered, checkable steps. Each step is a concrete action a human or
agent could complete in one sitting (15min-2h). Number them so they can be
referenced in PR discussions.
RULES:
  - One verb per step ("Create", "Add", "Refactor", "Test", "Document").
  - End with verification step ("Run tests", "Manual smoke test").
  - Sub-bullets are fine for detail; don't nest deeper than 2 levels.
  - 4-12 steps is the sweet spot. More than 15 = task is too big, split it.
FORMAT:
  - [ ] 1. Step one
    - Sub-detail
  - [ ] 2. Step two
EXAMPLE:
  - [ ] 1. Create `security_monitor/io/tailer.py` with the `LogTailer` class skeleton.
  - [ ] 2. Implement `async def stream_lines()` using `aiofiles` and the polling pattern from `prg_utils/file_watcher.py`.
  - [ ] 3. Handle inode-aware reopen — when `os.stat(path).st_ino` changes, reopen at offset 0.
  - [ ] 4. Add structured logging via the existing `loguru` setup; one log line per reopen.
  - [ ] 5. Write unit tests in `tests/io/test_tailer.py` covering: normal append, rotation, missing file, permission denied.
  - [ ] 6. Run `pytest tests/io/` — must pass with no warnings.
  - [ ] 7. Run `black .`, `ruff check .`, `isort .` — must pass clean.
  - [ ] 8. Add a one-line entry to `CHANGELOG.md` under Unreleased > Added.
STATUS: [REQUIRED] — must contain at least 1 checkbox.
-->

## Dependencies [REQUIRED]

<!--
GUIDE: What must exist before this task can start, and what this task blocks.
Use wikilinks for tasks/specs in the same vault.
RULES:
  - "Blocked by:" — must be done first.
  - "Blocks:" — these can't start until this is done.
  - Note "(in parallel)" for tasks that share interface decisions.
  - Use "None" if there are truly no dependencies.
EXAMPLE:
  Blocked by:
  - [[security_monitor-SPEC]] approved
  - Decision on log-rotation strategy (logrotate vs. journalctl) — see [[2026-04-26 — Rotation strategy]]

  Blocks:
  - [[task-detector-implementation]] — needs the LogLine dataclass shape.

  In parallel with:
  - [[task-alert-dispatcher]] — independent module; share only the LogLine import.
STATUS: [REQUIRED]
-->

## Definition of Done [REQUIRED]

<!--
GUIDE: A binary checklist. When every box is checked, the task is mergeable.
This is stricter than Steps — Steps is the recipe, DoD is the contract.
RULES:
  - Each item is verifiable from the outside (CI pass, file exists, demo works).
  - Include: tests pass, lint clean, docs updated, peer-reviewed (if applicable).
  - Match acceptance criteria from the parent SPEC where relevant.
EXAMPLE:
  - [ ] All unit tests pass: `pytest tests/io/test_tailer.py`
  - [ ] Coverage on `security_monitor/io/tailer.py` >= 90%
  - [ ] `black`, `ruff check`, `isort` all clean
  - [ ] CHANGELOG.md updated with one-line entry
  - [ ] Manual smoke test: tail a real log, rotate it with `logrotate -f`, verify reopen.
  - [ ] PR reviewed and approved by one teammate.
STATUS: [REQUIRED] — must contain at least 1 checkbox.
-->

## Notes [OPTIONAL]

<!--
GUIDE: Anything that didn't fit above — alternate approaches considered,
links to relevant prior art, surprises encountered while implementing.
This is a free-form scratchpad. Keep it useful or delete it.
RULES:
  - Date entries you add post-hoc: "(2026-04-28) Tried X, didn't work because Y; switched to Z."
  - It's OK if this section is empty when the task starts.
EXAMPLE:
  - Considered using `watchdog` instead of polling, but it doesn't work cleanly across NFS — sticking with polling.
  - (2026-04-27) Found that `aiofiles` doesn't support seeking on opened files reliably; using `open()` in a thread executor instead.
STATUS: [OPTIONAL]
-->
