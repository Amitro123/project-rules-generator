"""
Tests for the three readme_parser extractor fixes.

FIX-1: extract_purpose  — skip blockquotes, badges, full-bold lines, short lines
FIX-2: extract_auto_triggers — no hard-coded tech template triggers
FIX-3: extract_process_steps — stop condition checked before section-entry check
"""

import pytest

from generator.analyzers.readme_parser import extract_auto_triggers, extract_process_steps, extract_purpose

# ──────────────────────────────────────────────────────────────────────────────
# FIX-1: extract_purpose
# ──────────────────────────────────────────────────────────────────────────────


class TestExtractPurposeFix:
    def test_skips_blockquote_tagline(self):
        readme = "# My Tool\n\n> The world's greatest CLI.\n\nThis tool analyzes Python projects and generates rules.\n"
        result = extract_purpose(readme)
        assert "greatest" not in result
        assert "analyzes Python projects" in result

    def test_skips_badge_line(self):
        readme = "# My Tool\n\n[![Build](https://example.com/badge.svg)](https://ci.example.com)\n\nThis tool automates CI workflows for large repos.\n"
        result = extract_purpose(readme)
        assert "Build" not in result
        assert "automates CI" in result

    def test_skips_full_bold_marketing_line(self):
        readme = "# Awesome Project\n\n**The best project management tool ever.**\n\nManages tasks across multiple projects with AI assistance.\n"
        result = extract_purpose(readme)
        assert "best project management" not in result
        assert "Manages tasks" in result

    def test_skips_horizontal_rule(self):
        readme = "# Tool\n\n---\n\nBuilds and packages Python CLI applications automatically.\n"
        result = extract_purpose(readme)
        assert "---" not in result
        assert "Builds and packages" in result

    def test_skips_short_line(self):
        readme = "# Tool\n\nv1.2\n\nConverts Markdown documents to PDF using Pandoc.\n"
        result = extract_purpose(readme)
        assert result != "v1.2"
        assert "Converts Markdown" in result

    def test_returns_real_first_sentence(self):
        readme = "# Project Rules Generator\n\nA Python CLI tool that analyzes a project and generates .clinerules.\n"
        result = extract_purpose(readme)
        assert "CLI tool" in result

    def test_fallback_when_no_good_line(self):
        readme = "# Tool\n\n> Short.\n\n[![x](y)](z)\n"
        result = extract_purpose(readme)
        assert result == "Solve project-specific workflow challenges"


# ──────────────────────────────────────────────────────────────────────────────
# FIX-2: extract_auto_triggers
# ──────────────────────────────────────────────────────────────────────────────


class TestExtractAutoTriggersFix:
    def _readme_with_tech(self, *techs: str) -> str:
        tech_str = ", ".join(techs)
        return f"# My Skill\n\nThis project uses {tech_str}.\n\n## Quick Start\n\n1. Run it\n"

    def test_no_ffmpeg_trigger_for_ffmpeg_readme(self):
        readme = self._readme_with_tech("ffmpeg", "python")
        triggers = extract_auto_triggers(readme, "my-video-skill")
        assert not any(
            "FFmpeg operations" in t for t in triggers
        ), "Hard-coded 'FFmpeg operations needed' trigger should no longer be emitted"

    def test_no_frontend_trigger_for_react_readme(self):
        readme = self._readme_with_tech("react", "typescript")
        triggers = extract_auto_triggers(readme, "my-ui-skill")
        assert not any(
            "frontend code" in t for t in triggers
        ), "Hard-coded 'Working in frontend code: *.tsx' trigger should not appear"

    def test_no_backend_trigger_for_python_readme(self):
        readme = self._readme_with_tech("python")
        triggers = extract_auto_triggers(readme, "my-backend-skill")
        assert not any(
            "backend code" in t for t in triggers
        ), "Hard-coded 'Working in backend code: *.py' trigger should not appear"

    def test_skill_name_trigger_always_present(self):
        triggers = extract_auto_triggers("# Anything\n\nSome readme text.\n", "pytest-testing-workflow")
        assert any("pytest" in t and "testing" in t and "workflow" in t for t in triggers)

    def test_video_glob_trigger_when_explicit_glob_present(self):
        readme = "# Video Tool\n\nProcess *.mp4 files.\n"
        triggers = extract_auto_triggers(readme, "video-tool")
        assert any("video files" in t for t in triggers)

    def test_no_video_trigger_without_explicit_glob(self):
        readme = "# Video Tool\n\nThis uses ffmpeg for video processing.\n"
        triggers = extract_auto_triggers(readme, "video-tool")
        assert not any(
            "video files" in t for t in triggers
        ), "Video trigger should only fire when README contains explicit *.mp4/avi/mov glob"

    def test_domain_specific_extension_trigger(self):
        readme = "# Jinja Tool\n\nRender `templates/model.py.j2` files.\n"
        triggers = extract_auto_triggers(readme, "jinja-tool")
        assert any("*.j2" in t for t in triggers)


# ──────────────────────────────────────────────────────────────────────────────
# FIX-3: extract_process_steps (ordering bug)
# ──────────────────────────────────────────────────────────────────────────────


class TestExtractProcessStepsFix:
    def test_installation_does_not_re_enter_quick_start(self):
        """
        The ordering bug: when inside ## Quick Start, hitting ## Installation
        used to re-enter the section instead of stopping, because the entry
        check ran before the stop check.
        """
        readme = """\
# My Project

## Quick Start

1. Clone the repo
2. Install dependencies
3. Run the app

## Installation

This section should NOT be collected.

- Extra step from installation
"""
        steps = extract_process_steps(readme)
        # Should get exactly the Quick Start steps
        assert any("Clone" in s for s in steps)
        assert any("Install" in s for s in steps)
        assert any("Run" in s for s in steps)
        # Must NOT include anything from the Installation section
        assert not any(
            "Extra step from installation" in s for s in steps
        ), "Steps from ## Installation must not appear when already inside ## Quick Start"

    def test_stops_at_same_level_unrelated_header(self):
        readme = """\
# Project

## Quick Start

1. Step one
2. Step two

## AI Providers

Content from AI Providers should not appear.
"""
        steps = extract_process_steps(readme)
        assert any("Step one" in s for s in steps)
        assert not any("AI Providers" in s for s in steps)

    def test_collects_numbered_steps(self):
        readme = """\
# Project

## Quick Start

1. Install via pip
2. Configure your API key
3. Run prg analyze
"""
        steps = extract_process_steps(readme)
        assert len(steps) == 3
        assert any("Install" in s for s in steps)

    def test_skips_prerequisites_subsection(self):
        readme = """\
# Project

## Quick Start

### Prerequisites

- Python 3.10+
- Git

### Steps

1. Clone the repo
2. Install deps
"""
        steps = extract_process_steps(readme)
        # Prerequisites items should not appear; Steps items should
        assert not any("Python 3.10" in s for s in steps), "Prerequisites sub-section items should be skipped"
        assert any("Clone" in s for s in steps)
