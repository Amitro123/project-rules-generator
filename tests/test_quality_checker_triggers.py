"""Tests for validate_quality's auto_triggers parsing.

Regression tests for the dict-shape crash (Batch D / Fix 1): validate_quality()
used to throw `TypeError: unsupported operand type(s) for +: 'dict' and 'list'`
when a skill's frontmatter used the shape

    auto_triggers:
      keywords: [foo]
      project_signals: [has_tests]

which is how most generator-created skills serialize triggers. Before the fix
9 real skills in the repo were silently unscoreable.
"""

from __future__ import annotations

from generator.utils.quality_checker import _flatten_trigger_spec, validate_quality


class TestFlattenTriggerSpec:
    """Unit tests for the normaliser."""

    def test_plain_list_of_strings_returned_as_strings(self):
        assert _flatten_trigger_spec(["fix deadcode", "remove unused"]) == [
            "fix deadcode",
            "remove unused",
        ]

    def test_list_of_dicts_keywords_flattened(self):
        spec = [{"keywords": ["foo", "bar"]}, {"keywords": ["baz"]}]
        assert _flatten_trigger_spec(spec) == ["foo", "bar", "baz"]

    def test_dict_shape_keywords_and_signals_flattened(self):
        """The crash-causing shape found in .clinerules/skills/learned/deadcode."""
        spec = {
            "keywords": ["deadcode"],
            "project_signals": ["has_tests", "has_ci"],
        }
        assert _flatten_trigger_spec(spec) == ["deadcode", "has_tests", "has_ci"]

    def test_dict_shape_only_keywords(self):
        spec = {"keywords": ["just-one"]}
        assert _flatten_trigger_spec(spec) == ["just-one"]

    def test_phrases_key_also_flattened(self):
        spec = {"phrases": ["fix bug", "audit code"]}
        assert _flatten_trigger_spec(spec) == ["fix bug", "audit code"]

    def test_empty_inputs(self):
        assert _flatten_trigger_spec([]) == []
        assert _flatten_trigger_spec({}) == []
        assert _flatten_trigger_spec(None) == []

    def test_unknown_shape_returns_empty_without_crash(self):
        # string at the top level — shouldn't happen but must not crash
        assert _flatten_trigger_spec("deadcode") == []
        assert _flatten_trigger_spec(42) == []

    def test_non_list_values_inside_dict_ignored(self):
        spec = {"keywords": "oops-string", "project_signals": ["ok"]}
        assert _flatten_trigger_spec(spec) == ["ok"]


class TestValidateQualityDoesNotCrashOnDictTriggers:
    """The regression that kicked this fix off."""

    SKILL_WITH_DICT_TRIGGERS = """---
name: deadcode
description: cleanup workflow for this project
auto_triggers:
  keywords:
    - deadcode
  project_signals:
    - has_tests
    - has_ci
tools: Bash Read Write
category: project
priority: 50
---

# Skill: Deadcode

## Purpose

Without this skill, developers leave unused imports and functions that clutter
the codebase. Dead code accumulates silently and hides real defects.

## Auto-Trigger

The agent should activate this skill when the user requests:

- **"deadcode"**

## Process

### 1. Scan for unused imports

Why: unused imports bloat the module and confuse readers.

```bash
ruff check --select F401 .
```

### 2. Remove them

```bash
ruff check --select F401 --fix .
```

## Output

A cleaner module with only live imports.

## Anti-Patterns

- Leaving commented-out code behind
"""

    def test_dict_triggers_do_not_raise(self):
        """Must not raise TypeError on the dict shape."""
        report = validate_quality(self.SKILL_WITH_DICT_TRIGGERS)
        # We only care that it didn't crash; the exact score is not the point.
        assert report.score >= 0
        assert report.score <= 100

    def test_dict_triggers_counted_as_triggers(self):
        """Triggers extracted from the dict should actually be counted."""
        report = validate_quality(self.SKILL_WITH_DICT_TRIGGERS)
        # The trigger-count warning only fires when < 2 triggers are found.
        # With `deadcode` keyword + 2 project_signals = 3 triggers, so the
        # "Only N auto-triggers" warning must NOT fire.
        assert not any(
            "auto-triggers" in w for w in report.warnings
        ), f"dict-shape triggers should be flattened and counted; warnings={report.warnings}"
