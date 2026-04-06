"""Coverage boost: SkillContentRenderer (54% covered, 37 miss)."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from generator.skill_content_renderer import SkillContentRenderer


def _make_metadata(name="fastapi-workflow", description="A FastAPI skill"):
    return SimpleNamespace(
        name=name,
        description=description,
        auto_triggers=["run fastapi", "api workflow", "fastapi deploy"],
        project_signals=["has_docker", "has_tests"],
        tools=["pytest", "uvicorn"],
        negative_triggers=["install fastapi"],
        tags=["python", "api"],
        category="backend",
        priority="High",
    )


def _make_renderer(tmp_path):
    scanner = MagicMock()
    scanner.detect_tech_stack.return_value = ["fastapi", "python"]
    meta_builder = MagicMock()
    meta_builder.generate_critical_rules.return_value = ["Never skip tests"]
    meta_builder.render_frontmatter.return_value = "---\nname: fastapi-workflow\n---\n\n"
    doc_loader = MagicMock()
    doc_loader.load_key_files.return_value = {}
    return SkillContentRenderer(
        project_path=tmp_path,
        scanner=scanner,
        meta_builder=meta_builder,
        doc_loader=doc_loader,
    )


class TestGenerateContentInline:
    def test_returns_string(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer.generate_content("fastapi-workflow", "# FastAPI readme", metadata)
        assert isinstance(content, str)

    def test_contains_skill_title(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer.generate_content("fastapi-workflow", "# FastAPI readme", metadata)
        assert "Fastapi Workflow" in content or "fastapi-workflow" in content.lower()

    def test_contains_description(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata(description="Deploy FastAPI apps")
        content = renderer.generate_content("fastapi-workflow", "", metadata)
        assert "Deploy FastAPI apps" in content

    def test_contains_triggers(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer.generate_content("fastapi-workflow", "", metadata)
        assert "run fastapi" in content

    def test_contains_critical_rules(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer.generate_content("fastapi-workflow", "", metadata)
        assert "Never skip tests" in content

    def test_contains_anti_patterns_section(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer.generate_content("fastapi-workflow", "", metadata)
        assert "Anti-Patterns" in content


class TestGenerateContentWithJinja2:
    def test_falls_back_to_inline_when_template_missing(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        # No Jinja2 template exists — should fall back to inline
        content = renderer.generate_content("fastapi-workflow", "# FastAPI", metadata)
        assert isinstance(content, str)
        assert len(content) > 50

    def test_jinja2_failure_falls_back_to_inline(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        with patch("generator.skill_content_renderer.HAS_JINJA2", True):
            with patch.object(renderer, "_generate_with_jinja2", side_effect=RuntimeError("template error")):
                content = renderer.generate_content("fastapi-workflow", "", metadata)
        # Falls back to inline, must still produce content
        assert isinstance(content, str)


class TestGenerateWithJinja2:
    def test_renders_when_template_exists(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        # Real template exists at templates/SKILL.md.jinja2 in the project
        try:
            content = renderer._generate_with_jinja2("test-skill", "# Readme", metadata)
            assert isinstance(content, str)
        except FileNotFoundError:
            pytest.skip("Jinja2 template not found in expected location")


class TestGenerateInline:
    def test_contains_project_name(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer._generate_inline("fastapi-workflow", "", metadata)
        # Project name should appear in content
        assert tmp_path.name in content

    def test_critical_block_included_when_rules_exist(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()
        content = renderer._generate_inline("fastapi-workflow", "", metadata)
        assert "CRITICAL" in content

    def test_empty_critical_rules_omits_block(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        renderer._meta_builder.generate_critical_rules.return_value = []
        metadata = _make_metadata()
        content = renderer._generate_inline("fastapi-workflow", "", metadata)
        assert "CRITICAL" not in content


class TestFormatTriggers:
    def test_each_trigger_on_its_own_line(self):
        result = SkillContentRenderer._format_triggers(["run fastapi", "api workflow"])
        assert "- run fastapi" in result
        assert "- api workflow" in result

    def test_empty_list_returns_empty_string(self):
        result = SkillContentRenderer._format_triggers([])
        assert result == ""


class TestFormatSignals:
    def test_each_signal_formatted_with_backticks(self):
        result = SkillContentRenderer._format_signals(["has_docker", "has_tests"])
        assert "`has_docker`" in result
        assert "`has_tests`" in result

    def test_empty_signals_returns_none_detected(self):
        result = SkillContentRenderer._format_signals([])
        assert "None detected" in result


class TestGenerateContentAI:
    def test_ai_fallback_on_exception(self, tmp_path):
        renderer = _make_renderer(tmp_path)
        metadata = _make_metadata()

        with patch("generator.llm_skill_generator.LLMSkillGenerator", side_effect=ImportError("no llm")):
            content = renderer.generate_content("fastapi-workflow", "", metadata, use_ai=True)

        assert isinstance(content, str)
        assert len(content) > 0
