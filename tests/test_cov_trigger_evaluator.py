"""Coverage boost: TriggerEvaluator (0% covered, 52 stmts)."""

from generator.utils.trigger_evaluator import TriggerEvaluator, TriggerReport, TriggerTestCase

SAMPLE_SKILL_MD = """---
name: fastapi-workflow
description: >-
  Use when user mentions "fastapi workflow", "run fastapi", "api endpoint".
  Do NOT activate for "install fastapi", "fastapi docs".
---

# FastAPI Workflow
"""


class TestExtractTriggers:
    def test_extracts_trigger_phrases(self):
        triggers = TriggerEvaluator.extract_triggers(SAMPLE_SKILL_MD)
        assert "fastapi workflow" in triggers
        assert "run fastapi" in triggers
        assert "api endpoint" in triggers

    def test_empty_frontmatter_returns_empty(self):
        assert TriggerEvaluator.extract_triggers("# No frontmatter here") == []

    def test_no_mentions_clause_returns_empty(self):
        md = """---
name: test
description: Just a plain description.
---
"""
        assert TriggerEvaluator.extract_triggers(md) == []

    def test_malformed_yaml_returns_empty(self):
        md = """---
name: [unclosed bracket
---
"""
        assert TriggerEvaluator.extract_triggers(md) == []

    def test_incomplete_frontmatter_returns_empty(self):
        assert TriggerEvaluator.extract_triggers("---only one separator") == []


class TestExtractNegativeTriggers:
    def test_extracts_negative_phrases(self):
        negs = TriggerEvaluator._extract_negative_triggers(SAMPLE_SKILL_MD)
        assert "install fastapi" in negs
        assert "fastapi docs" in negs

    def test_no_do_not_clause_returns_empty(self):
        md = """---
name: x
description: Use when user mentions "test".
---
"""
        assert TriggerEvaluator._extract_negative_triggers(md) == []

    def test_empty_skill_returns_empty(self):
        assert TriggerEvaluator._extract_negative_triggers("") == []


class TestGetDescription:
    def test_returns_description_string(self):
        desc = TriggerEvaluator._get_description(SAMPLE_SKILL_MD)
        assert "fastapi workflow" in desc

    def test_no_description_key_returns_empty(self):
        md = """---
name: test
---
"""
        assert TriggerEvaluator._get_description(md) == ""

    def test_non_frontmatter_returns_empty(self):
        assert TriggerEvaluator._get_description("# Just markdown") == ""

    def test_invalid_yaml_returns_empty(self):
        md = """---
bad: [yaml
---
"""
        assert TriggerEvaluator._get_description(md) == ""


class TestMatchesAny:
    def test_matches_trigger_in_query(self):
        assert TriggerEvaluator._matches_any("run fastapi server", ["fastapi server", "deploy"])

    def test_case_insensitive_match(self):
        assert TriggerEvaluator._matches_any("Run FastAPI Server", ["fastapi server"])

    def test_no_match_returns_false(self):
        assert not TriggerEvaluator._matches_any("install packages", ["deploy", "run tests"])

    def test_empty_triggers_returns_false(self):
        assert not TriggerEvaluator._matches_any("run fastapi", [])


class TestDataclasses:
    def test_trigger_test_case_fields(self):
        tc = TriggerTestCase(query="run fastapi", should_fire=True, label="basic test")
        assert tc.query == "run fastapi"
        assert tc.should_fire is True
        assert tc.label == "basic test"

    def test_trigger_report_fields(self):
        report = TriggerReport(precision=0.95, passed=True, total=20, hits=19, misses=["bad query"])
        assert report.precision == 0.95
        assert report.passed is True
        assert report.total == 20
        assert len(report.misses) == 1

    def test_trigger_report_default_misses(self):
        report = TriggerReport(precision=1.0, passed=True, total=10, hits=10)
        assert report.misses == []
