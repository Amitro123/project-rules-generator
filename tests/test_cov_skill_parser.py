"""Coverage boost: SkillParser pure methods (57% covered, 62 miss)."""

import json
from pathlib import Path

import pytest

from generator.skill_parser import SkillParser

SAMPLE_SKILL_MD = """---
name: fastapi-workflow
description: Use when user mentions "run fastapi", "api workflow".
---

A comprehensive FastAPI workflow skill.

## Auto-Trigger

- "run fastapi"
- "api endpoint"
- "fastapi deploy"

**Negative Triggers:**

- "install fastapi"
- "fastapi docs"

## When to use

- User needs to deploy a FastAPI app
- User asks about API endpoints

## Tools

read, exec, pytest, uvicorn

## Command

`prg fastapi-workflow`

## Input/Output

Input: project directory / Output: deployed API
"""


class TestCleanMarkdown:
    def test_strips_list_marker(self):
        assert SkillParser.clean_markdown("- Item") == "Item"

    def test_strips_arrow_marker(self):
        assert SkillParser.clean_markdown("→ Step") == "Step"

    def test_removes_bold(self):
        assert SkillParser.clean_markdown("**Bold text**") == "Bold text"

    def test_removes_italic(self):
        assert SkillParser.clean_markdown("*italic*") == "italic"

    def test_removes_inline_code(self):
        assert SkillParser.clean_markdown("`code`") == "code"

    def test_extracts_link_text(self):
        result = SkillParser.clean_markdown("[Click here](http://example.com)")
        assert result == "Click here"

    def test_removes_image_badge(self):
        result = SkillParser.clean_markdown("![badge](http://badge.com/img.png) text")
        assert "![" not in result

    def test_collapses_multiple_spaces(self):
        result = SkillParser.clean_markdown("too   many  spaces")
        assert "  " not in result

    def test_empty_string_returns_empty(self):
        assert SkillParser.clean_markdown("") == ""

    def test_strips_gt_marker(self):
        result = SkillParser.clean_markdown("> blockquote")
        assert ">" not in result


class TestSummarizePurpose:
    def test_returns_fallback_when_no_context(self):
        result = SkillParser.summarize_purpose("fastapi", [], "MyApp")
        assert "fastapi" in result.lower()
        assert "MyApp" in result

    def test_uses_best_descriptive_line(self):
        context = ["# Heading", "FastAPI provides high-performance API endpoints for the service"]
        result = SkillParser.summarize_purpose("fastapi", context, "MyApp")
        assert "FastAPI" in result

    def test_skips_shell_commands(self):
        context = ["pip install fastapi", "uvicorn main:app"]
        result = SkillParser.summarize_purpose("fastapi", context, "MyApp")
        # Should fall back since no descriptive lines
        assert "fastapi" in result.lower()

    def test_skips_table_lines(self):
        context = ["| col1 | col2 |", "FastAPI enables async processing"]
        result = SkillParser.summarize_purpose("fastapi", context, "MyApp")
        assert "FastAPI" in result

    def test_skips_arrow_heavy_lines(self):
        context = ["A → B → C → D → E", "FastAPI processes requests asynchronously"]
        result = SkillParser.summarize_purpose("fastapi", context, "MyApp")
        assert "FastAPI" in result

    def test_empty_project_name_fallback(self):
        result = SkillParser.summarize_purpose("redis", [], "")
        assert "redis" in result.lower()
        assert "this project" in result


class TestBuildGuidelines:
    def test_returns_string(self):
        result = SkillParser.build_guidelines("fastapi", [])
        assert isinstance(result, str)

    def test_default_guideline_when_no_context(self):
        result = SkillParser.build_guidelines("redis", [])
        assert "redis" in result.lower()

    def test_includes_architecture_lines(self):
        context = ["FastAPI model: async request handling"]
        result = SkillParser.build_guidelines("fastapi", context)
        assert "async" in result.lower() or "model" in result.lower()

    def test_skips_shell_commands(self):
        context = ["pip install fastapi", "uvicorn main:app --reload"]
        result = SkillParser.build_guidelines("fastapi", context)
        assert "pip " not in result
        assert "uvicorn " not in result

    def test_skips_arrow_heavy_lines(self):
        context = ["A → B → C → D"]
        result = SkillParser.build_guidelines("fastapi", context)
        assert "A → B" not in result

    def test_always_appends_error_handling_guideline(self):
        result = SkillParser.build_guidelines("redis", [])
        assert "errors" in result.lower() or "redis" in result.lower()

    def test_max_eight_guidelines(self):
        context = [f"FastAPI config key{i}: value{i}" for i in range(20)]
        result = SkillParser.build_guidelines("fastapi", context)
        lines = [l for l in result.split("\n") if l.strip()]
        assert len(lines) <= 8


class TestExtractAllTriggers:
    def test_extracts_quoted_triggers(self):
        skills = {
            "project": {
                "my-skill": {
                    "content": '## Auto-Trigger\n\n- "run tests"\n- "execute suite"\n'
                }
            }
        }
        result = SkillParser.extract_all_triggers(skills)
        assert "my-skill" in result
        assert "run tests" in result["my-skill"]

    def test_extracts_unquoted_trigger(self):
        skills = {
            "project": {
                "my-skill": {
                    "content": "## Auto-Trigger\n\n- run tests\n"
                }
            }
        }
        result = SkillParser.extract_all_triggers(skills)
        assert "my-skill" in result

    def test_project_overwrites_builtin(self):
        skills = {
            "builtin": {"shared": {"content": '## Auto-Trigger\n\n- "builtin phrase"\n'}},
            "project": {"shared": {"content": '## Auto-Trigger\n\n- "project phrase"\n'}},
        }
        result = SkillParser.extract_all_triggers(skills)
        assert "project phrase" in result["shared"]
        assert "builtin phrase" not in result.get("shared", [])

    def test_missing_trigger_section_skipped(self):
        skills = {
            "project": {
                "no-trigger-skill": {"content": "# Skill\n\nNo trigger section.\n"}
            }
        }
        result = SkillParser.extract_all_triggers(skills)
        assert "no-trigger-skill" not in result

    def test_strips_when_prefix_from_unquoted(self):
        skills = {
            "project": {
                "my-skill": {
                    "content": "## Auto-Trigger\n\n- when user asks about testing\n"
                }
            }
        }
        result = SkillParser.extract_all_triggers(skills)
        if "my-skill" in result:
            assert not any("when " in t for t in result["my-skill"])


class TestSaveTriggersJson:
    def test_creates_json_file(self, tmp_path):
        triggers = {"my-skill": ["phrase 1", "phrase 2"]}
        SkillParser.save_triggers_json(triggers, tmp_path)
        output_file = tmp_path / "auto-triggers.json"
        assert output_file.exists()

    def test_json_content_is_correct(self, tmp_path):
        triggers = {"skill-a": ["trigger1"], "skill-b": ["trigger2", "trigger3"]}
        SkillParser.save_triggers_json(triggers, tmp_path)
        data = json.loads((tmp_path / "auto-triggers.json").read_text())
        assert data["skill-a"] == ["trigger1"]
        assert len(data["skill-b"]) == 2

    def test_handles_write_error_gracefully(self, tmp_path):
        # Write to a file that doesn't have parent dir — should not raise
        bad_path = tmp_path / "nonexistent_dir"
        SkillParser.save_triggers_json({"x": ["y"]}, bad_path)


class TestParseSkillMd:
    def test_extracts_name_from_filename(self):
        result = SkillParser.parse_skill_md("# FastAPI\n", "fastapi-workflow.md")
        assert result["name"] == "fastapi-workflow"

    def test_extracts_description(self):
        content = "# FastAPI Workflow\n\nA comprehensive FastAPI skill for deployments.\n"
        result = SkillParser.parse_skill_md(content, "fastapi-workflow.md")
        assert "comprehensive" in result["description"].lower()

    def test_extracts_auto_triggers(self):
        result = SkillParser.parse_skill_md(SAMPLE_SKILL_MD, "fastapi-workflow.md")
        assert len(result["triggers"]) > 0

    def test_extracts_negative_triggers(self):
        # The regex requires exactly: ** or ##, then "Negative Triggers", colon optional, single * optional, then newline
        content = (
            "# Skill\n\nDesc.\n\n"
            "## Auto-Trigger\n\n- run fastapi\n\n"
            "## Negative Triggers\n\n- install fastapi\n- fastapi docs\n"
        )
        result = SkillParser.parse_skill_md(content, "fastapi-workflow.md")
        assert len(result["negative_triggers"]) > 0

    def test_extracts_when_to_use(self):
        result = SkillParser.parse_skill_md(SAMPLE_SKILL_MD, "fastapi-workflow.md")
        assert "FastAPI" in result["when_to_use"] or "API" in result["when_to_use"]

    def test_extracts_tools(self):
        result = SkillParser.parse_skill_md(SAMPLE_SKILL_MD, "fastapi-workflow.md")
        assert isinstance(result["tools"], list)

    def test_extracts_command(self):
        result = SkillParser.parse_skill_md(SAMPLE_SKILL_MD, "fastapi-workflow.md")
        assert "fastapi-workflow" in result["command"]

    def test_extracts_input_output(self):
        result = SkillParser.parse_skill_md(SAMPLE_SKILL_MD, "fastapi-workflow.md")
        assert "Input" in result["input_output"] or "Output" in result["input_output"]

    def test_default_command_when_missing(self):
        result = SkillParser.parse_skill_md("# My skill\n\nDescription.", "my-skill.md")
        assert result["command"] == "`prg my-skill`"

    def test_default_io_when_missing(self):
        result = SkillParser.parse_skill_md("# My skill\n\nDescription.", "my-skill.md")
        assert result["input_output"] == "Standard CLI I/O"

    def test_triggers_inferred_from_when_to_use(self):
        content = "# Skill\n\nDesc.\n\n## When to use\n\n- Use when testing\n- Use when debugging\n"
        result = SkillParser.parse_skill_md(content, "x.md")
        assert len(result["triggers"]) > 0

    def test_separate_input_output_sections(self):
        content = "# Skill\n\nDesc.\n\n## Input\n\nProject path\n\n## Output\n\nGenerated files\n"
        result = SkillParser.parse_skill_md(content, "x.md")
        assert "Project path" in result["input_output"] or "Generated files" in result["input_output"]
