"""Coverage boost: pure-logic tests for tasks, rules_renderer, quality_validators, self_reviewer."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from generator.planning.task_creator import TaskEntry
from generator.requirements import Requirement

# ---------------------------------------------------------------------------
# TraceabilityMatrix (tasks.py)
# ---------------------------------------------------------------------------
from generator.tasks import TraceabilityMatrix


def _req(id_, desc, source="README"):
    return Requirement(id=id_, description=desc, source=source)


def _task(id_, title):
    return TaskEntry(id=id_, title=title, file="", goal=title)


class TestTraceabilityMatrix:
    def test_build_maps_overlapping_keywords(self):
        reqs = [_req("r1", "implement user authentication login")]
        tasks = [_task(1, "implement authentication module")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        assert 1 in m.mapping["r1"]

    def test_build_no_overlap_leaves_gap(self):
        reqs = [_req("r1", "implement user authentication")]
        tasks = [_task(1, "fix typo in docs")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        assert m.mapping["r1"] == []

    def test_get_gaps_returns_unmapped(self):
        reqs = [_req("r1", "implement feature"), _req("r2", "write tests for feature")]
        tasks = [_task(1, "implement feature set")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        gaps = m.get_gaps()
        gap_ids = {g.id for g in gaps}
        assert "r1" not in gap_ids  # overlaps: "implement", "feature"
        assert "r2" in gap_ids  # "write", "tests" don't match "implement", "feature", "set"

    def test_get_gaps_all_covered(self):
        reqs = [_req("r1", "add user login feature")]
        tasks = [_task(1, "add login feature support")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        assert m.get_gaps() == []

    def test_get_gaps_all_missing(self):
        reqs = [_req("r1", "deploy kubernetes cluster")]
        tasks = [_task(1, "fix typo in README")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        assert len(m.get_gaps()) == 1

    def test_format_table_header_present(self):
        reqs = [_req("r1", "add user login")]
        tasks = []
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        table = m.format_table()
        assert "| Req ID |" in table
        assert "r1" in table

    def test_format_table_shows_covered(self):
        reqs = [_req("r1", "implement user login system")]
        tasks = [_task(42, "implement login user system")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        table = m.format_table()
        assert "#42" in table
        assert "COV" in table

    def test_format_table_shows_missing(self):
        reqs = [_req("r1", "deploy kubernetes cluster")]
        tasks = [_task(1, "fix typo")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        table = m.format_table()
        assert "MISSING" in table
        assert "pending" in table

    def test_build_single_word_overlap_not_enough(self):
        reqs = [_req("r1", "authentication")]
        tasks = [_task(1, "authentication module")]
        m = TraceabilityMatrix(requirements=reqs, tasks=tasks)
        m.build()
        # Only 1 word overlap ("authentication"), need >= 2
        assert m.mapping["r1"] == []

    def test_empty_requirements(self):
        m = TraceabilityMatrix(requirements=[], tasks=[_task(1, "some task")])
        m.build()
        assert m.get_gaps() == []
        assert "Req ID" in m.format_table()


from generator.rules_creator import Rule, RulesMetadata

# ---------------------------------------------------------------------------
# rules_renderer.py
# ---------------------------------------------------------------------------
from generator.rules_renderer import RulesContentRenderer, append_mandatory_anti_patterns


def _metadata(name="MyProject", tech=None, ptype="python-cli", areas=None, signals=None):
    return RulesMetadata(
        project_name=name,
        tech_stack=tech or ["python"],
        project_type=ptype,
        priority_areas=areas or ["testing"],
        detected_signals=signals or [],
    )


class TestAppendMandatoryAntiPatterns:
    def test_appends_section(self):
        result = append_mandatory_anti_patterns("existing content\n")
        assert "Critical Anti-Patterns" in result
        assert "NEVER run destructive" in result

    def test_react_anti_pattern_added_for_react_framework(self):
        result = append_mandatory_anti_patterns("content", framework="react")
        assert "mutate React state" in result

    def test_react_anti_pattern_not_added_without_react(self):
        result = append_mandatory_anti_patterns("content", framework="django")
        assert "mutate React state" not in result

    def test_react_case_insensitive(self):
        result = append_mandatory_anti_patterns("content", framework="React")
        assert "mutate React state" in result


class TestFormatPriorityAreas:
    def test_empty_areas_returns_fallback(self):
        renderer = RulesContentRenderer()
        result = renderer.format_priority_areas([])
        assert "No specific priority" in result

    def test_areas_formatted_as_bold_list(self):
        renderer = RulesContentRenderer()
        result = renderer.format_priority_areas(["async_patterns", "rest_api"])
        assert "**Async Patterns**" in result
        assert "**Rest Api**" in result

    def test_underscores_converted_to_spaces(self):
        renderer = RulesContentRenderer()
        result = renderer.format_priority_areas(["test_driven_development"])
        assert "Test Driven Development" in result


class TestRulesContentRenderer:
    def _make_rules(self):
        return {
            "Testing": [Rule("Use pytest", priority="High", category="Testing", source="pytest_patterns")],
            "Code Style": [Rule("Follow PEP 8", priority="Medium", category="Code Style", source="analysis")],
        }

    def test_render_contains_project_name(self):
        renderer = RulesContentRenderer()
        meta = _metadata(name="AwesomeProject")
        content = renderer.render(meta, self._make_rules())
        assert "AwesomeProject" in content

    def test_render_contains_high_priority_section(self):
        renderer = RulesContentRenderer()
        meta = _metadata()
        content = renderer.render(meta, self._make_rules())
        assert "High Priority" in content
        assert "Use pytest" in content

    def test_render_contains_tech_stack(self):
        renderer = RulesContentRenderer()
        meta = _metadata(tech=["python", "fastapi"])
        content = renderer.render(meta, self._make_rules())
        assert "fastapi" in content

    def test_render_includes_signals(self):
        renderer = RulesContentRenderer()
        meta = _metadata(signals=["has_docker", "has_tests"])
        content = renderer.render(meta, self._make_rules())
        assert "has_docker" in content

    def test_render_appends_anti_patterns(self):
        renderer = RulesContentRenderer()
        meta = _metadata()
        content = renderer.render(meta, self._make_rules())
        assert "Critical Anti-Patterns" in content

    def test_render_react_anti_pattern_for_react_tech(self):
        renderer = RulesContentRenderer()
        meta = _metadata(tech=["react", "typescript"])
        content = renderer.render(meta, self._make_rules())
        assert "mutate React state" in content

    def test_render_no_duplicate_high_priority_in_categories(self):
        renderer = RulesContentRenderer()
        meta = _metadata()
        rules = {"Testing": [Rule("Use pytest", priority="High", category="Testing", source="pytest_patterns")]}
        content = renderer.render(meta, rules)
        # "Use pytest" appears in High Priority section; Categories section should skip it
        assert content.count("Use pytest") == 1

    def test_render_yaml_frontmatter(self):
        renderer = RulesContentRenderer()
        meta = _metadata(name="Proj", tech=["python"])
        content = renderer.render(meta, {})
        assert content.startswith("---")
        assert "project: Proj" in content


# ---------------------------------------------------------------------------
# quality_validators.py
# ---------------------------------------------------------------------------
from generator.quality_validators import RulesQualityValidator, SkillQualityValidator


class TestSkillQualityValidatorAutoFix:
    def test_fixes_cd_project_name(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v.auto_fix("cd project_name\n", MagicMock())
        assert f"cd {tmp_path.name}" in result

    def test_fixes_path_to_project(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v.auto_fix("see /path/to/project here", MagicMock())
        assert str(tmp_path) in result

    def test_removes_describe_placeholder(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v.auto_fix("do [describe the thing] now", MagicMock())
        assert "[describe" not in result

    def test_removes_example_placeholder(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v.auto_fix("run [example command here]", MagicMock())
        assert "[example" not in result

    def test_adds_anti_patterns_if_missing(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v.auto_fix("# My Skill\n", MagicMock())
        assert "## Anti-Patterns" in result

    def test_does_not_duplicate_anti_patterns(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        content = "# Skill\n\n## Anti-Patterns\n\n❌ bad\n"
        result = v.auto_fix(content, MagicMock())
        assert result.count("## Anti-Patterns") == 1


class TestSkillQualityValidatorDetectHallucinations:
    def test_nonexistent_path_flagged(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v._detect_hallucinated_paths("File:src/fake/module.py")
        assert any("src/fake/module.py" in r for r in result)

    def test_existing_file_not_flagged(self, tmp_path):
        real_file = tmp_path / "main.py"
        real_file.write_text("# real")
        v = SkillQualityValidator(project_path=tmp_path)
        result = v._detect_hallucinated_paths("File:main.py")
        assert not any("main.py" in r for r in result)

    def test_backtick_src_pattern(self, tmp_path):
        v = SkillQualityValidator(project_path=tmp_path)
        result = v._detect_hallucinated_paths("check `src/utils/helper.py`")
        assert any("src/utils/helper.py" in r for r in result)


class TestRulesQualityValidator:
    def _rules(self, *contents, priority="High", source="pytest_patterns"):
        return {"Cat": [Rule(c, priority=priority, category="Cat", source=source) for c in contents]}

    def test_passes_with_complete_valid_rules(self):
        content = "## Coding Standards\n## Priority Areas\n## Tech Stack\n"
        rules = self._rules(*["Rule " + str(i) for i in range(10)])
        v = RulesQualityValidator()
        meta = _metadata()
        report = v.validate(content, meta, rules)
        assert report.passed
        assert report.score >= 85

    def test_fails_missing_sections(self):
        content = "# Just a heading\n"
        rules = self._rules(*["Rule " + str(i) for i in range(10)])
        v = RulesQualityValidator()
        report = v.validate(content, _metadata(), rules)
        assert not report.passed
        assert any("Missing sections" in i for i in report.issues)

    def test_warns_on_few_rules(self):
        content = "## Coding Standards\n## Priority Areas\n## Tech Stack\n"
        rules = self._rules("Rule 1", "Rule 2")
        v = RulesQualityValidator()
        report = v.validate(content, _metadata(), rules)
        assert any("Only" in w for w in report.warnings)

    def test_detect_conflict_async(self):
        v = RulesQualityValidator()
        rules = {
            "A": [Rule("use async", priority="High", category="A", source="x")],
            "B": [Rule("don't use async", priority="High", category="B", source="x")],
        }
        conflicts = v.detect_rule_conflicts(rules)
        assert any("async" in c for c in conflicts)

    def test_no_conflict_with_no_contradictions(self):
        v = RulesQualityValidator()
        rules = {"A": [Rule("use async patterns", priority="High", category="A", source="x")]}
        assert v.detect_rule_conflicts(rules) == []


# ---------------------------------------------------------------------------
# self_reviewer.py — pure methods only (no LLM)
# ---------------------------------------------------------------------------
from generator.planning.self_reviewer import ReviewReport, SelfReviewer


class TestReviewReportToMarkdown:
    def test_verdict_present(self):
        r = ReviewReport(verdict="Pass")
        md = r.to_markdown()
        assert "**Verdict:** Pass" in md

    def test_strengths_section(self):
        r = ReviewReport(verdict="Pass", strengths=["Good structure"])
        md = r.to_markdown()
        assert "## Strengths" in md
        assert "- Good structure" in md

    def test_issues_section(self):
        r = ReviewReport(verdict="Needs Revision", issues=["Missing tests"])
        md = r.to_markdown()
        assert "## Issues" in md
        assert "- Missing tests" in md

    def test_action_plan_uses_checkbox(self):
        r = ReviewReport(verdict="Pass", action_plan=["Add unit tests"])
        md = r.to_markdown()
        assert "- [ ] Add unit tests" in md

    def test_suspicious_terms_section(self):
        r = ReviewReport(verdict="Major Issues", suspicious_terms=["FakeService"])
        md = r.to_markdown()
        assert "## Suspicious Terms" in md
        assert "- FakeService" in md

    def test_empty_sections_not_rendered(self):
        r = ReviewReport(verdict="Pass")
        md = r.to_markdown()
        assert "## Strengths" not in md
        assert "## Issues" not in md
        assert "## Action Plan" not in md


class TestSelfReviewerParseReview:
    def _reviewer(self):
        return SelfReviewer(client=MagicMock())

    def test_parses_pass_verdict(self):
        r = self._reviewer()
        response = "VERDICT: Pass\nSTRENGTHS:\n- Good\nISSUES:\nHALLUCINATIONS:\nACTION_PLAN:\n"
        report = r._parse_review(response)
        assert report.verdict == "Pass"

    def test_parses_major_issues_verdict(self):
        r = self._reviewer()
        response = "VERDICT: Major Issues Found\nSTRENGTHS:\nISSUES:\nHALLUCINATIONS:\nACTION_PLAN:\n"
        report = r._parse_review(response)
        assert report.verdict == "Major Issues"

    def test_defaults_to_needs_revision(self):
        r = self._reviewer()
        report = r._parse_review("no verdict line here")
        assert report.verdict == "Needs Revision"

    def test_parses_strengths(self):
        r = self._reviewer()
        response = (
            "VERDICT: Pass\nSTRENGTHS:\n- Great tests\n- Clear structure\nISSUES:\nHALLUCINATIONS:\nACTION_PLAN:\n"
        )
        report = r._parse_review(response)
        assert "Great tests" in report.strengths
        assert "Clear structure" in report.strengths

    def test_none_hallucinations_filtered(self):
        r = self._reviewer()
        response = "VERDICT: Pass\nSTRENGTHS:\nISSUES:\nHALLUCINATIONS:\n- None\n- N/A\nACTION_PLAN:\n"
        report = r._parse_review(response)
        assert report.suspicious_terms == []

    def test_real_hallucination_kept(self):
        r = self._reviewer()
        response = "VERDICT: Pass\nSTRENGTHS:\nISSUES:\nHALLUCINATIONS:\n- FakeService-Pro\nACTION_PLAN:\n"
        report = r._parse_review(response)
        assert "FakeService-Pro" in report.suspicious_terms


class TestSelfReviewerExtractSection:
    def _reviewer(self):
        return SelfReviewer(client=MagicMock())

    def test_extracts_bullets(self):
        r = self._reviewer()
        text = "ISSUES:\n- Missing tests\n- Bad imports\n"
        items = r._extract_section(text, "ISSUES")
        assert items == ["Missing tests", "Bad imports"]

    def test_returns_empty_when_section_missing(self):
        r = self._reviewer()
        assert r._extract_section("no section here", "ISSUES") == []

    def test_strips_leading_dashes_and_spaces(self):
        r = self._reviewer()
        text = "STRENGTHS:\n-  Good structure  \n"
        items = r._extract_section(text, "STRENGTHS")
        assert items == ["Good structure"]


class TestSelfReviewerFlagSuspiciousTerms:
    def _reviewer(self):
        return SelfReviewer(client=MagicMock())

    def test_camel_case_not_in_readme_flagged(self):
        r = self._reviewer()
        result = r._flag_suspicious_terms("Use DevLens-AI for analysis", "readme has nothing about that")
        assert "DevLens-AI" in result

    def test_term_in_readme_not_flagged(self):
        r = self._reviewer()
        result = r._flag_suspicious_terms("Use DevLens-AI for analysis", "devlens-ai is great")
        assert "DevLens-AI" not in result

    def test_empty_readme_returns_empty(self):
        r = self._reviewer()
        result = r._flag_suspicious_terms("Use FakeTool-Pro", "")
        assert result == []


class TestSelfReviewerStaticReview:
    def _reviewer(self):
        return SelfReviewer(client=MagicMock())

    def test_pass_with_good_plan(self):
        r = self._reviewer()
        content = "# My Plan\n\n## Phase 1\n\n- [ ] Task 1\n- [ ] Task 2\n- [ ] Task 3\n## Phase 2\n\n- [ ] Task 4\n- [ ] Task 5\n## Phase 3\n\n- [ ] Task 6\n"
        report = r._static_review(content, "")
        assert report.verdict == "Pass"
        assert any("title" in s.lower() for s in report.strengths)

    def test_needs_revision_missing_phases(self):
        r = self._reviewer()
        content = "# Plan\n\n- [ ] Task 1\n- [ ] Task 2\n- [ ] Task 3\n- [ ] Task 4\n- [ ] Task 5\n"
        report = r._static_review(content, "")
        assert report.verdict == "Needs Revision"

    def test_missing_title_is_issue(self):
        r = self._reviewer()
        content = (
            "no title here\n\n## Phase 1\n\n- [ ] Task 1\n- [ ] Task 2\n- [ ] Task 3\n- [ ] Task 4\n- [ ] Task 5\n"
        )
        report = r._static_review(content, "")
        assert any("title" in i.lower() for i in report.issues)

    def test_action_plan_derived_from_issues(self):
        r = self._reviewer()
        content = "no title\n"
        report = r._static_review(content, "")
        assert len(report.action_plan) > 0
        assert all("Fix:" in a for a in report.action_plan)
