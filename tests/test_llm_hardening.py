"""Regression tests for LLM-output hardening.

These tests pin down the specific failure modes documented in
``bugs_docs/KNOWN-ISSUES.md`` so they can never silently return:

- Issue 1 — design fallback leaves success criteria empty
- Issue 2 — plan --from-design under-decomposes (1 task instead of many)
- Issue 3 — plan hallucinates `src/` for projects that use different layouts
- Issue 4 — plan truncates task content mid-sentence
"""

from __future__ import annotations

from pathlib import Path
from typing import List
from unittest.mock import patch

from generator.ai.hardening import (
    contains_unfilled_placeholders,
    discover_source_dirs,
    generate_with_validator,
    ground_paths,
    looks_truncated,
    reject_unfilled_placeholders,
    require_min_count,
    require_sections,
)

# ---------------------------------------------------------------------------
# looks_truncated
# ---------------------------------------------------------------------------


class TestLooksTruncated:
    def test_empty_string_is_truncated(self):
        assert looks_truncated("") is True

    def test_too_short_is_truncated(self):
        assert looks_truncated("Hello") is True

    def test_complete_response_is_not_truncated(self):
        text = "## Success Criteria\n\n- Response time < 100ms.\n- Cache hit rate > 80%.\n" + ("x" * 100)
        assert looks_truncated(text) is False

    def test_trailing_conjunction_is_truncated(self):
        text = "Step one is to validate all inputs and" + ("x" * 200)
        # Pad the content but still end in a conjunction
        text = text + " and"
        assert looks_truncated(text) is True

    def test_unclosed_fence_is_truncated(self):
        text = "## Data Models\n\n```python\nclass Foo:\n    pass\n" + "# padding " * 20
        # Single unclosed fence
        assert looks_truncated(text) is True

    def test_closed_fence_is_ok(self):
        text = "## Data Models\n\n```python\nclass Foo:\n    pass\n```\n" + "# padding " * 20
        assert looks_truncated(text) is False

    def test_trailing_colon_is_truncated(self):
        text = "Here are the next steps: " + ("context " * 50) + "files:"
        assert looks_truncated(text) is True

    def test_incomplete_python_identifier_is_truncated(self):
        # Simulates: "- Import `get_" cut off mid-identifier
        body = "## Changes\n\n- Create `database.py`.\n- Import `get_"
        text = body + ("x" * 200)  # pad past min_length, then replace tail
        text = ("x" * 200) + body
        assert looks_truncated(text) is True

    def test_complete_identifier_not_truncated(self):
        # A line ending in a complete identifier (no trailing _) is fine
        text = ("x" * 200) + "\n- Import `get_settings` from config."
        assert looks_truncated(text) is False

    def test_unclosed_single_backtick_in_tail_is_truncated(self):
        # Tail has one open backtick (odd count) — inline code cut off
        text = ("x" * 200) + "\n- Import `get_"
        assert looks_truncated(text) is True

    def test_balanced_single_backticks_in_tail_not_truncated(self):
        # Two backticks in tail → balanced → not truncated
        text = ("x" * 200) + "\n- Use `my_func` here."
        assert looks_truncated(text) is False


# ---------------------------------------------------------------------------
# generate_with_validator
# ---------------------------------------------------------------------------


class _FakeClient:
    """Minimal stand-in for an AIClient. Returns a scripted list of responses."""

    def __init__(self, responses: List[str]):
        self._responses = list(responses)
        self.calls: List[dict] = []

    def generate(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        return self._responses.pop(0) if self._responses else ""


class TestGenerateWithValidator:
    def test_returns_first_response_when_valid(self):
        client = _FakeClient(["## Success Criteria\n- Done\n" + "x" * 150])
        result = generate_with_validator(
            client,
            "prompt",
            validator=require_sections("Success Criteria"),
            max_retries=1,
        )
        assert "Success Criteria" in result
        assert len(client.calls) == 1  # no retry needed

    def test_retries_when_validator_rejects(self):
        client = _FakeClient(
            [
                "x" * 150,  # first response has no Success Criteria
                "## Success Criteria\n- Done\n" + "x" * 150,
            ]
        )
        result = generate_with_validator(
            client,
            "prompt",
            validator=require_sections("Success Criteria"),
            max_retries=1,
        )
        assert "Success Criteria" in result
        assert len(client.calls) == 2

    def test_retry_includes_repair_hint(self):
        client = _FakeClient(["x" * 150, "## Success Criteria\n- Done\n" + "x" * 150])
        generate_with_validator(
            client,
            "ORIGINAL",
            validator=require_sections("Success Criteria"),
            max_retries=1,
        )
        # Second attempt must include the repair hint
        assert "rejected" in client.calls[1]["prompt"].lower()
        # Second attempt lowers temperature
        assert client.calls[1]["temperature"] < client.calls[0]["temperature"]

    def test_exhausts_retries_and_returns_last(self):
        client = _FakeClient(["fail1" * 40, "fail2" * 40])
        result = generate_with_validator(
            client,
            "prompt",
            validator=require_sections("Missing"),
            max_retries=1,
        )
        assert "fail2" in result

    def test_sdk_exception_treated_as_invalid(self):
        class _Boom:
            def __init__(self):
                self.count = 0

            def generate(self, prompt, **kwargs):
                self.count += 1
                if self.count == 1:
                    raise RuntimeError("rate limit")
                return "## Success Criteria\n- Done\n" + "x" * 150

        client = _Boom()
        result = generate_with_validator(
            client,
            "prompt",
            validator=require_sections("Success Criteria"),
            max_retries=1,
        )
        assert "Success Criteria" in result

    def test_truncation_triggers_retry_without_validator(self):
        client = _FakeClient(["Ends in a conjunction and", "Complete response " * 20])
        result = generate_with_validator(client, "prompt", max_retries=1)
        assert "Complete" in result
        assert len(client.calls) == 2


# ---------------------------------------------------------------------------
# require_min_count
# ---------------------------------------------------------------------------


class TestRequireMinCount:
    def test_counts_matches(self):
        validator = require_min_count(r"^###?\s*\d+\.", 3)
        good = "### 1. Foo\n\n### 2. Bar\n\n### 3. Baz"
        assert validator(good) is True

    def test_rejects_fewer_matches(self):
        validator = require_min_count(r"^###?\s*\d+\.", 3)
        bad = "### 1. Only one"
        assert validator(bad) is False


# ---------------------------------------------------------------------------
# discover_source_dirs / ground_paths
# ---------------------------------------------------------------------------


class TestDiscoverSourceDirs:
    def test_prefers_conventional_src(self, tmp_path: Path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "mod.py").write_text("x = 1")
        (tmp_path / "mypkg").mkdir()
        (tmp_path / "mypkg" / "mod.py").write_text("x = 1")
        assert discover_source_dirs(tmp_path) == ["src"]

    def test_finds_python_package_when_no_convention(self, tmp_path: Path):
        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "mod.py").write_text("x = 1")
        (tmp_path / "cli").mkdir()
        (tmp_path / "cli" / "mod.py").write_text("x = 1")
        assert sorted(discover_source_dirs(tmp_path)) == ["cli", "generator"]

    def test_skips_tests_and_docs(self, tmp_path: Path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "t.py").write_text("x = 1")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "foo.md").write_text("x")
        (tmp_path / "lib").mkdir()
        (tmp_path / "lib" / "m.py").write_text("x = 1")
        assert discover_source_dirs(tmp_path) == ["lib"]

    def test_returns_empty_for_missing_path(self, tmp_path: Path):
        assert discover_source_dirs(tmp_path / "nope") == []


class TestGroundPaths:
    def test_rewrites_hallucinated_src_to_real_package(self, tmp_path: Path):
        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "__init__.py").write_text("")
        result = ground_paths(["src/api.py", "src/models.py"], tmp_path)
        assert result == ["generator/api.py", "generator/models.py"]

    def test_keeps_path_when_top_segment_exists(self, tmp_path: Path):
        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "m.py").write_text("x = 1")
        result = ground_paths(["generator/api.py"], tmp_path)
        assert result == ["generator/api.py"]

    def test_keeps_bare_filenames_untouched(self, tmp_path: Path):
        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "m.py").write_text("x = 1")
        result = ground_paths(["README.md", "pyproject.toml"], tmp_path)
        assert result == ["README.md", "pyproject.toml"]

    def test_passes_through_when_no_project_path(self):
        assert ground_paths(["src/api.py"], None) == ["src/api.py"]

    def test_passes_through_when_no_source_dirs_discoverable(self, tmp_path: Path):
        # Empty project — nothing to ground against
        assert ground_paths(["src/api.py"], tmp_path) == ["src/api.py"]

    def test_normalises_backslash_paths(self, tmp_path: Path):
        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "m.py").write_text("x = 1")
        result = ground_paths(["src\\api.py"], tmp_path)
        # Must be rewritten AND normalised
        assert result == ["generator/api.py"]


# ---------------------------------------------------------------------------
# DesignGenerator salvage path (Issue #1)
# ---------------------------------------------------------------------------


class TestDesignSalvage:
    def test_salvage_extracts_success_criteria_when_full_parse_fails(self):
        from generator.design_generator import DesignGenerator

        # Malformed body: no 'Design:' title → from_markdown() raises → salvage runs.
        # Pydantic requires problem_statement, so include one (and ensure it's
        # picked up by the salvage parser).
        raw = (
            "# Totally Wrong Heading Style\n\n"
            "## Problem Statement\n"
            "We need a better cache.\n\n"
            "## Success Criteria\n\n"
            "- **Performance**: Response time < 100ms\n"
            "- **Quality**: Test coverage > 85%\n"
            "- **Reliability**: Cache hit rate > 80%\n"
        )
        gen = DesignGenerator.__new__(DesignGenerator)  # skip __init__
        design = gen._parse_response(raw, "cache")
        assert len(design.success_criteria) == 3
        assert any("Response time" in c for c in design.success_criteria)

    def test_salvage_returns_none_for_completely_empty_body(self):
        from generator.design_generator import DesignGenerator

        result = DesignGenerator._salvage_partial_design("", "cache")
        assert result is None


# ---------------------------------------------------------------------------
# TaskDecomposer under-decomposition fallback (Issue #2)
# ---------------------------------------------------------------------------


class TestFromDesignFallback:
    def test_fallback_fires_when_llm_returns_one_task_with_paraphrased_title(self, tmp_path: Path):
        """The OLD behaviour: fallback only fired when title matched exactly.
        An LLM returning one paraphrased task used to silently produce a
        1-subtask plan. Now we fall back whenever fewer than 3 tasks are
        returned.
        """
        from generator.design_generator import ArchitectureDecision, Design
        from generator.tasks.decomposer import TaskDecomposer

        design = Design(
            title="Refactor analyze command",
            problem_statement="analyze() is a god function.",
            architecture_decisions=[
                ArchitectureDecision(title="Split by concern", choice="extract helpers"),
                ArchitectureDecision(title="Parameter surface", choice="subcommand extraction"),
                ArchitectureDecision(title="Testability", choice="dependency injection"),
            ],
            api_contracts=["extract_helpers(cmd) -> None"],
        )
        design_path = tmp_path / "DESIGN.md"
        design_path.write_text(design.to_markdown(), encoding="utf-8")

        decomposer = TaskDecomposer(api_key="fake-key")
        # LLM returns one task with a DIFFERENT title — the old trigger missed this.
        paraphrased = "### 1. Start by analyzing the command\nGoal: investigate\nEstimated: 5\n"
        with patch.object(TaskDecomposer, "_call_llm", return_value=paraphrased):
            tasks = decomposer.from_design(design_path)
        # Structural fallback produces one task per decision + contracts → ≥ 3
        assert len(tasks) >= 3

    def test_fallback_not_used_when_llm_returns_enough_tasks(self, tmp_path: Path):
        from generator.design_generator import Design
        from generator.tasks.decomposer import TaskDecomposer

        design = Design(title="Build X", problem_statement="Need X")
        design_path = tmp_path / "DESIGN.md"
        design_path.write_text(design.to_markdown(), encoding="utf-8")

        decomposer = TaskDecomposer(api_key="fake-key")
        good = (
            "### 1. First\nGoal: do A\nEstimated: 3\n"
            "### 2. Second\nGoal: do B\nEstimated: 3\n"
            "### 3. Third\nGoal: do C\nEstimated: 3\n"
            "### 4. Fourth\nGoal: do D\nEstimated: 3\n"
        )
        with patch.object(TaskDecomposer, "_call_llm", return_value=good):
            tasks = decomposer.from_design(design_path)
        assert len(tasks) == 4
        assert tasks[0].title == "First"


# ---------------------------------------------------------------------------
# TaskDecomposer path grounding (Issue #3)
# ---------------------------------------------------------------------------


class TestPathGrounding:
    def test_decompose_rewrites_hallucinated_src_paths(self, tmp_path: Path):
        """An LLM emitting ``src/api.py`` in a project with ``generator/``
        should have its paths rewritten, not silently shipped into PLAN.md.
        """
        from generator.tasks.decomposer import TaskDecomposer

        (tmp_path / "generator").mkdir()
        (tmp_path / "generator" / "__init__.py").write_text("")

        decomposer = TaskDecomposer(api_key="fake-key")
        response = (
            "### 1. Implement API\n"
            "Goal: create endpoint\n"
            "Files: src/api.py, src/models.py\n"
            "Estimated: 4\n"
            "### 2. Tests\n"
            "Goal: add tests\n"
            "Files: tests/test_api.py\n"
            "Estimated: 3\n"
            "### 3. Docs\n"
            "Goal: update docs\n"
            "Files: README.md\n"
            "Estimated: 2\n"
        )
        with patch.object(TaskDecomposer, "_call_llm", return_value=response):
            tasks = decomposer.decompose("Add API", project_path=tmp_path)

        # src/* must be rewritten to generator/*
        all_files = [f for t in tasks for f in t.files]
        assert "generator/api.py" in all_files
        assert "generator/models.py" in all_files
        assert "src/api.py" not in all_files
        # README.md (bare filename) and tests/ (real dir) untouched
        assert "README.md" in all_files


# ---------------------------------------------------------------------------
# TaskDecomposer field extraction (Issue #4 — truncation)
# ---------------------------------------------------------------------------


class TestMultilineFieldExtraction:
    def test_goal_spanning_two_lines_is_joined(self):
        from generator.tasks.decomposer import TaskDecomposer

        content = (
            "### 1. Build thing\n"
            "Goal: Define a Pydantic BaseModel named LLMConfig with fields:\n"
            "provider: str, model: str, api_key: str\n"
            "Files: config.py\n"
            "Estimated: 4\n"
        )
        tasks = TaskDecomposer.parse_response(content, "build")
        assert len(tasks) == 1
        # Previously the Goal would have been just the first line; the continuation
        # after the newline would have been dropped silently (Issue #4).
        assert "api_key: str" in tasks[0].goal
        assert "LLMConfig" in tasks[0].goal

    def test_goal_stops_at_next_field(self):
        from generator.tasks.decomposer import TaskDecomposer

        content = "### 1. Build thing\n" "Goal: do the thing\n" "Files: foo.py\n" "Estimated: 3\n"
        tasks = TaskDecomposer.parse_response(content, "build")
        assert tasks[0].goal == "do the thing"
        # files field must not have leaked into goal
        assert "foo.py" not in tasks[0].goal


# ---------------------------------------------------------------------------
# Unfilled placeholder detection (Bug 8 — Batch C)
# ---------------------------------------------------------------------------


class TestPlaceholderDetection:
    """LLMs sometimes echo back the prompt template's bracketed guidance
    instead of filling it in. These tests ensure we detect the common
    offenders so generate_skill can retry with a repair prompt."""

    def test_clean_text_has_no_placeholders(self):
        clean = "# Skill: Pytest Workflow\n\n" "## Purpose\n\nWithout this skill, tests fail silently in CI.\n"
        assert contains_unfilled_placeholders(clean) is False
        assert reject_unfilled_placeholders(clean) is True

    def test_detects_one_sentence_placeholder(self):
        bad = "## Purpose\n\n[One sentence: what problem does this solve]\n"
        assert contains_unfilled_placeholders(bad) is True
        assert reject_unfilled_placeholders(bad) is False

    def test_detects_first_step_placeholder(self):
        bad = "### 1. [First step name]\n\nDo something.\n"
        assert contains_unfilled_placeholders(bad) is True

    def test_detects_trigger_phrase_placeholder(self):
        bad = '- **"[trigger phrase 1]"**\n'
        assert contains_unfilled_placeholders(bad) is True

    def test_detects_unfilled_jinja_variable(self):
        bad = "# Skill: {{Skill Name Title Case}}\n"
        assert contains_unfilled_placeholders(bad) is True

    def test_detects_negative_triggers_placeholder(self):
        bad = "Do NOT activate for: [comma-separated negative triggers]\n"
        assert contains_unfilled_placeholders(bad) is True

    def test_legitimate_markdown_links_not_flagged(self):
        """Normal markdown `[link text](url)` must not trigger a false positive."""
        ok = "See the [docs](https://example.com/pytest) for details.\n"
        assert contains_unfilled_placeholders(ok) is False

    def test_empty_string_is_not_placeholder(self):
        assert contains_unfilled_placeholders("") is False


class TestSkillGeneratorRetry:
    """The skill generator should retry once when the LLM returns
    placeholder-laden output, feeding back a repair prompt."""

    # Fixtures must include ## Process so the truncation guard doesn't
    # fire before the placeholder check.  A valid SKILL.md always has
    # ## Process; anything missing it is treated as truncated output.
    _COMPLETE_PREFIX = "## Process\n\nStep 1: do the thing.\n\n"

    def test_retries_when_placeholders_detected(self, monkeypatch):
        from generator import llm_skill_generator

        bad = self._COMPLETE_PREFIX + "## Purpose\n\n[One sentence: what problem does this solve]\n"
        good = self._COMPLETE_PREFIX + "## Purpose\n\nWithout this skill, CI runs fail.\n" + ("x" * 200)

        # Simulate: client init succeeds, first generate returns bad, second returns good.
        calls: List[str] = []

        def fake_generate_content(self, prompt, max_tokens=2000):  # noqa: ARG001
            calls.append(prompt)
            return bad if len(calls) == 1 else good

        monkeypatch.setattr(
            llm_skill_generator.LLMSkillGenerator,
            "generate_content",
            fake_generate_content,
            raising=True,
        )
        monkeypatch.setattr(
            llm_skill_generator,
            "create_ai_client",
            lambda *a, **kw: object(),
        )

        gen = llm_skill_generator.LLMSkillGenerator(provider="groq", api_key="fake")
        result = gen.generate_skill(
            "my-skill",
            {
                "readme": "# project\n",
                "project_name": "proj",
                "tech_stack": {"backend": ["python"]},
                "structure": {},
                "key_files": {},
            },
        )

        assert len(calls) == 2, "placeholder-laden output should trigger a retry"
        assert "NOTE: Your previous response contained literal placeholders" in calls[1]
        assert result == good

    def test_no_retry_when_output_is_clean(self, monkeypatch):
        from generator import llm_skill_generator

        good = self._COMPLETE_PREFIX + "## Purpose\n\nWithout this skill, CI runs fail.\n" + ("x" * 200)
        calls: List[str] = []

        def fake_generate_content(self, prompt, max_tokens=2000):  # noqa: ARG001
            calls.append(prompt)
            return good

        monkeypatch.setattr(
            llm_skill_generator.LLMSkillGenerator,
            "generate_content",
            fake_generate_content,
            raising=True,
        )
        monkeypatch.setattr(
            llm_skill_generator,
            "create_ai_client",
            lambda *a, **kw: object(),
        )

        gen = llm_skill_generator.LLMSkillGenerator(provider="groq", api_key="fake")
        gen.generate_skill(
            "my-skill",
            {
                "readme": "# project\n",
                "project_name": "proj",
                "tech_stack": {"backend": ["python"]},
                "structure": {},
                "key_files": {},
            },
        )

        assert len(calls) == 1, "clean output should NOT trigger a retry"

    def test_truncated_output_retried_then_empty_on_second_truncation(self, monkeypatch):
        """When both LLM attempts return truncated output (missing ## Process),
        generate_skill returns '' so the strategy chain falls back to READMEStrategy
        or StubStrategy instead of writing a broken SKILL.md to disk."""
        from generator import llm_skill_generator

        truncated = "## Purpose\n\nWithout a clear understanding of"

        calls: List[str] = []

        def fake_generate_content(self, prompt, max_tokens=2000):  # noqa: ARG001
            calls.append(prompt)
            return truncated

        monkeypatch.setattr(llm_skill_generator.LLMSkillGenerator, "generate_content", fake_generate_content)
        monkeypatch.setattr(llm_skill_generator, "create_ai_client", lambda *a, **kw: object())

        gen = llm_skill_generator.LLMSkillGenerator(provider="groq", api_key="fake")
        result = gen.generate_skill(
            "reportlab-pdf",
            {"readme": "# project\n", "project_name": "proj", "tech_stack": {}, "structure": {}, "key_files": {}},
        )

        assert len(calls) == 2, "truncated output should trigger exactly one retry"
        assert result == "", "double-truncation must return '' so next strategy is tried"

    def test_truncated_first_attempt_ok_second_succeeds(self, monkeypatch):
        """When the first attempt is truncated but the retry produces a complete
        SKILL.md, generate_skill returns the good content."""
        from generator import llm_skill_generator

        truncated = "## Purpose\n\nWithout a clear understanding of"
        good = "## Process\n\nStep 1: run tests.\n\n## Purpose\n\nWithout this skill things break.\n"

        calls: List[str] = []

        def fake_generate_content(self, prompt, max_tokens=2000):  # noqa: ARG001
            calls.append(prompt)
            return truncated if len(calls) == 1 else good

        monkeypatch.setattr(llm_skill_generator.LLMSkillGenerator, "generate_content", fake_generate_content)
        monkeypatch.setattr(llm_skill_generator, "create_ai_client", lambda *a, **kw: object())

        gen = llm_skill_generator.LLMSkillGenerator(provider="groq", api_key="fake")
        result = gen.generate_skill(
            "reportlab-pdf",
            {"readme": "# project\n", "project_name": "proj", "tech_stack": {}, "structure": {}, "key_files": {}},
        )

        assert len(calls) == 2
        assert result == good
