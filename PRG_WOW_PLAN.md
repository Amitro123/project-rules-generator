# PRG "Wow" Improvement Plan

## Goal
Make PRG the go-to CLI for bootstrapping AI-assisted development on **any** project —
beautiful output, relevant rules, multi-provider support, instant first-run value.

---

## Phase 1 — Core Quality (output that's actually right)

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 1.1 | **DESIGN-7**: Remove PRG-specific hardcoded rules (`refactor/`, `generator/cli.py`) from non-PRG projects | `generator/rules_creator.py` | ⬜ |
| 1.2 | **DESIGN-5**: Expand README context limit 1000 → 4000 chars | `generator/config.py`, `project_planner.py` | ⬜ |
| 1.3 | **DESIGN-2**: Unified provider resolver — `generator/ai/provider_resolver.py` | new file + factory.py | ⬜ |

**Why first:** Every first-run experience depends on output quality. A user who gets PRG's own architecture rules injected into their FastAPI project never comes back.

---

## Phase 2 — Beautiful CLI (first impression = everything)

`rich` is already in `requirements.txt` but not used. Wire it up.

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 2.1 | `prg analyze .` — rich progress panel, spinner per step, colored summary table | `cli/analyze_cmd.py` | ⬜ |
| 2.2 | `prg create-rules .` — live rule generation progress with category labels | `cli/create_rules_cmd.py` | ⬜ |
| 2.3 | `prg status` — rich progress bar + task table | `cli/jobs.py` | ⬜ |
| 2.4 | Error messages — provider-specific help text when API key missing | `generator/ai/provider_resolver.py` | ⬜ |

**Why second:** `rich` is already a declared dependency with zero new cost — we're leaving money on the table not using it.

---

## Phase 3 — Skills Discovery Commands

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 3.1 | `prg skills list` — rich table: name / layer / trigger count / quality score | new sub-command | ⬜ |
| 3.2 | `prg skills validate <name>` — show TriggerEvaluator precision score | new sub-command | ⬜ |
| 3.3 | `prg skills import <url>` — fetch a SKILL.md from GitHub/URL into learned/ | new sub-command | ⬜ |

**Why third:** `TriggerEvaluator` is a unique PRG feature no other tool has. Surfacing it as a command turns an invisible quality gate into a visible differentiator.

---

## Phase 4 — First-Run Story

| # | Item | File(s) | Status |
|---|------|---------|--------|
| 4.1 | `prg init` — interactive wizard: detect provider, set API key, run analyze | new command | ⬜ |
| 4.2 | Zero-API-key mode — `prg analyze .` falls back gracefully, tells user exactly what to do | `analyze_cmd.py` | ⬜ |
| 4.3 | Built-in demo fixture — `prg demo` runs against a bundled sample project, shows expected output | new command | ⬜ |

---

## Phase 5 — Ecosystem (future)

- OpenAI / Anthropic provider support
- `prg skills publish` — push to a community registry
- VS Code extension that runs `prg analyze` on open workspace
- GitHub Action: auto-refresh rules on README change

---

## Implementation Order

```
Phase 1.1 → 1.2 → 1.3  (quality foundation)
Phase 2.1 → 2.2 → 2.3  (visual polish — biggest wow per hour)
Phase 3.1 → 3.2         (surface hidden power)
Phase 4.1 → 4.2         (lower barrier to entry)
```

Each step is independently releasable and independently testable.
