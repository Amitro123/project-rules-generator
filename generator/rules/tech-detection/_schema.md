# Tech-Detection Rule Schema

This file documents the YAML rule shape. `generator/rules/loader.py`
validates every file against these requirements at import time —
malformed rules are skipped and a warning is logged, but never crash
the import.

## Common fields

Every rule file is a single YAML mapping with:

| Field | Required | Description |
|---|---|---|
| `name` | yes | Unique identifier; surfaces in shadow logs. Use kebab-case. |
| `predicate` | yes | Mapping `{type: <predicate_name>, ...params}` describing when the rule fires. See predicate table below. |
| `reason` | yes | Prose explanation. Surfaced in `ReconciliationResult.reason` / `CleanupTrace.reason` so users can see *why* a rule applied without reading code. |

## Precedence-rule extra fields (in `project-type-precedence/`)

| Field | Required | Description |
|---|---|---|
| `match_newer` | yes | Either a string (one newer_type to match), a list of strings (any of), or `"*"` to match any non-empty newer_type. |

## Cleanup-rule extra fields (in `tech-cleanup/`)

| Field | Required | Description |
|---|---|---|
| `strip` | yes | List of tech names to remove from `tech_stack` when this rule fires. |

## Predicate types

Each predicate has a `type` plus type-specific parameters. The loader rejects unknown predicate types.

### Precedence predicates

| `type` | Params | When it fires |
|---|---|---|
| `always` | — | Always (use sparingly — typically only the very first rule like python-api). |
| `newer_min_confidence` | `threshold: float` | `newer_confidence >= threshold` |
| `newer_confident_structure_uncertain` | `newer_min: float`, `structure_max: float` | `newer_confidence >= newer_min AND structure_confidence < structure_max` |
| `structure_unreliable_and_newer_confident` | `fallback_structure_types: [str]`, `newer_min: float` | `structure_type in fallback_structure_types AND newer_confidence >= newer_min` |

### Cleanup predicates

| `type` | Params | When it fires |
|---|---|---|
| `always` | — | Every run (e.g. always strip a noise token). |
| `stack_contains` | `token: str` | `token` is currently in `tech_stack` |
| `context_key_not_equal` | `key: str`, `value: any` | `context.get(key) != value` |

## Example: a precedence rule

```yaml
name: python-api-always-wins
match_newer: python-api
predicate:
  type: always
reason: |
  StructureAnalyzer misclassifies main.py+fastapi as python-cli;
  the newer detector is strictly more accurate for API projects.
```

## Example: a cleanup rule

```yaml
name: strip-reflex-js-build-artifacts
predicate:
  type: stack_contains
  token: reflex
strip:
  - react
  - node
  - javascript
  - typescript
  - nextjs
reason: |
  Reflex compiles Python to React/Next.js in a generated .web/
  directory. Those JS deps are build artifacts, not project tech.
```
