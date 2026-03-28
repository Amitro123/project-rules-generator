"""
End-to-End: README → Skill generation + Quality validation
===========================================================
Simulates the full flow that a user triggers via:
    prg analyze . --create-skill jinja2-template-workflow --from-readme README.md

Pipeline:
  SkillGenerator.create_skill(name, from_readme=<path>)
      → normalise path → read content
      → READMEStrategy.generate()
          → extract_purpose / extract_tech_stack / extract_auto_triggers
          → extract_process_steps / extract_anti_patterns
          → assemble markdown skill
      → write SKILL.md
      → quality_checker.validate_quality()  ← assert thresholds

The tests use a realistic, well-formed README for a Jinja2 code-generation tool
(similar to this project's own architecture).
"""

import textwrap
from pathlib import Path

import pytest

from generator.skill_discovery import SkillDiscovery
from generator.skill_generator import SkillGenerator
from generator.strategies.readme_strategy import READMEStrategy
from generator.utils.quality_checker import QualityReport, validate_quality

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

JINJA2_README = textwrap.dedent("""
    # Jinja2 Template Engine — Code Generator

    > Build dynamic code and configuration files from structured templates.

    A Python tool that uses **Jinja2** to render typed templates into source code,
    configuration files, and documentation. Works with Click for CLI and Pydantic
    for schema validation.

    ## Installation

    1. Clone the repository:
       ```bash
       git clone https://github.com/example/jinja2-codegen.git
       cd jinja2-codegen
       ```
    2. Install dependencies:
       ```bash
       pip install -e .
       ```
    3. Verify:
       ```bash
       python -m jinja2_codegen --version
       ```

    ## Quick Start

    1. Create a template file (`templates/model.py.j2`):
       ```jinja2
       class {{ class_name }}(BaseModel):
           {% for field in fields %}
           {{ field.name }}: {{ field.type }}
           {% endfor %}
       ```
    2. Render from CLI:
       ```bash
       codegen render templates/model.py.j2 --var class_name=User --var fields='[...]'
       ```
    3. Or from Python:
       ```python
       from jinja2_codegen import render_template
       result = render_template("model.py.j2", class_name="User", fields=[...])
       ```

    ## Tech Stack

    - **Python 3.11+** — runtime
    - **Jinja2** — template engine (with `StrictUndefined` by default)
    - **Click** — CLI interface
    - **Pydantic v2** — schema validation for template variables
    - **pytest** — test suite

    ## Anti-Patterns

    ❌ Never use `Undefined` (default) — always use `StrictUndefined` so missing
       variables raise errors instead of silently rendering empty strings.

    ❌ Don't put business logic in templates — keep templates declarative.

    ❌ Don't use `render_template_string` on untrusted input — always load from
       trusted file paths via `Environment(loader=FileSystemLoader(...))`.

    ## Configuration

    Templates are loaded from `./templates/` by default.
    Override with `CODEGEN_TEMPLATE_DIR` env variable or `--template-dir` flag.
""")


@pytest.fixture
def readme_file(tmp_path) -> Path:
    """Write the Jinja2 README to a temp file and return its path."""
    readme = tmp_path / "README.md"
    readme.write_text(JINJA2_README, encoding="utf-8")
    return readme


@pytest.fixture
def project_with_readme(tmp_path) -> Path:
    """Minimal project structure with README + pyproject.toml (for tech validation)."""
    readme = tmp_path / "README.md"
    readme.write_text(JINJA2_README, encoding="utf-8")

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "jinja2-codegen"\n' 'dependencies = ["jinja2", "click", "pydantic>=2.0", "pytest"]\n',
        encoding="utf-8",
    )

    # Minimal source file so tech_detector finds Python
    src = tmp_path / "main.py"
    src.write_text("# entry point\n", encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# 1. READMEStrategy: unit-level — content in, skill content out
# ---------------------------------------------------------------------------


class TestREADMEStrategyUnit:
    """Test READMEStrategy in isolation, passing README content directly."""

    def test_returns_content_not_none(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate(
            skill_name="jinja2-template-workflow",
            project_path=project_with_readme,
            from_readme=JINJA2_README,
            provider="groq",
        )
        assert result is not None, "READMEStrategy returned None for valid README content"

    def test_purpose_extracted(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Purpose" in result

    def test_auto_trigger_section_present(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Auto-Trigger" in result

    def test_process_section_present(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Process" in result

    def test_context_appended(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Context (from README)" in result

    def test_tech_stack_detected(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Tech Stack" in result
        # click and pydantic should be detected — both appear in README and pyproject
        assert any(t in result.lower() for t in ["click", "pydantic", "python"])

    def test_output_section_present(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        assert "## Output" in result

    def test_triggers_mention_skill_name_words(self, project_with_readme):
        strategy = READMEStrategy()
        result = strategy.generate("jinja2-template-workflow", project_with_readme, JINJA2_README, "groq")
        # extract_auto_triggers always generates at least one trigger from skill name words
        assert '"jinja2"' in result or '"template"' in result or '"workflow"' in result


# ---------------------------------------------------------------------------
# 2. Full pipeline: SkillGenerator.create_skill() via file path
# ---------------------------------------------------------------------------


class TestFullPipelineFromPath:
    """Test the full pipeline: CLI-style path in → SKILL.md written out."""

    def _make_generator(self, tmp_path: Path) -> SkillGenerator:
        discovery = SkillDiscovery(project_path=tmp_path)
        return SkillGenerator(discovery)

    def test_skill_file_created(self, project_with_readme):
        generator = self._make_generator(project_with_readme)
        readme_path = project_with_readme / "README.md"

        skill_dir = generator.create_skill(
            "jinja2-template-workflow",
            from_readme=str(readme_path),
            project_path=str(project_with_readme),
        )

        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists(), f"SKILL.md not created at {skill_file}"

    def test_skill_content_not_empty(self, project_with_readme):
        generator = self._make_generator(project_with_readme)
        readme_path = project_with_readme / "README.md"

        skill_dir = generator.create_skill(
            "jinja2-template-workflow",
            from_readme=str(readme_path),
            project_path=str(project_with_readme),
        )

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert len(content) > 200, "Generated SKILL.md is too short"

    def test_skill_contains_readme_context(self, project_with_readme):
        generator = self._make_generator(project_with_readme)
        readme_path = project_with_readme / "README.md"

        skill_dir = generator.create_skill(
            "jinja2-template-workflow",
            from_readme=str(readme_path),
            project_path=str(project_with_readme),
        )

        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert "## Context (from README)" in content

    def test_path_normalised_to_hyphens(self, project_with_readme):
        """Skill name with spaces or underscores should be normalised."""
        generator = self._make_generator(project_with_readme)
        readme_path = project_with_readme / "README.md"

        skill_dir = generator.create_skill(
            "jinja2 template workflow",
            from_readme=str(readme_path),
        )
        # Normalised: spaces → hyphens
        assert skill_dir.name == "jinja2-template-workflow"


# ---------------------------------------------------------------------------
# 3. Quality validation of the generated skill
# ---------------------------------------------------------------------------


class TestGeneratedSkillQuality:
    """Generate a skill and assert it meets quality thresholds."""

    @pytest.fixture
    def generated_content(self, project_with_readme) -> str:
        strategy = READMEStrategy()
        content = strategy.generate(
            "jinja2-template-workflow",
            project_with_readme,
            JINJA2_README,
            "groq",
        )
        assert content is not None
        return content

    def test_quality_score_above_threshold(self, generated_content):
        """Quality score must reach 70 (the validate_quality pass threshold)."""
        # Extract triggers from the generated content for quality check
        trigger_lines = []
        in_trigger = False
        for line in generated_content.splitlines():
            if "## Auto-Trigger" in line:
                in_trigger = True
                continue
            if in_trigger:
                if line.startswith("##"):
                    break
                if line.strip().startswith("- "):
                    trigger_lines.append(line.strip()[2:])

        report = validate_quality(generated_content, trigger_lines, metadata_tools=["python"])
        assert report.score >= 70, (
            f"Quality score {report.score} < 70.\n" f"Issues: {report.issues}\n" f"Warnings: {report.warnings}"
        )

    def test_no_critical_issues(self, generated_content):
        """Generated skill must have zero critical issues."""
        report = validate_quality(generated_content, metadata_tools=["python"])
        critical = [i for i in report.issues if "hallucinated" in i.lower() or "generic path" in i.lower()]
        assert not critical, f"Critical issues found: {critical}"

    def test_required_sections_present(self, generated_content):
        for section in ["## Purpose", "## Auto-Trigger", "## Process", "## Output"]:
            assert section in generated_content, f"Required section missing: {section}"

    def test_content_length_reasonable(self, generated_content):
        assert len(generated_content) >= 500, f"Generated skill is too short ({len(generated_content)} chars)"

    def test_no_generic_stub_markers(self, generated_content):
        from generator.utils.quality_checker import is_stub_content

        assert not is_stub_content(generated_content), "Generated skill still contains generic stub markers"

    def test_quality_report_is_qualityreport_instance(self, generated_content):
        report = validate_quality(generated_content)
        assert isinstance(report, QualityReport)
        assert isinstance(report.score, float)
        assert isinstance(report.passed, bool)
        assert isinstance(report.issues, list)

    def test_anti_patterns_extracted_from_readme(self, generated_content):
        """❌ markers the author wrote in the README must appear in the skill.

        The Jinja2 README has three explicit anti-patterns.  At least one must
        be extracted — not just the generic structural checks.
        """
        assert "## Anti-Patterns" in generated_content, "Anti-Patterns section missing"
        # At least one of the explicit README anti-patterns must be present
        explicit_patterns = [
            "StrictUndefined",  # "Never use Undefined — always use StrictUndefined"
            "business logic",  # "Don't put business logic in templates"
            "render_template_string",  # "Don't use render_template_string on untrusted input"
        ]
        found = [p for p in explicit_patterns if p.lower() in generated_content.lower()]
        assert found, (
            f"None of the README's explicit ❌ anti-patterns were extracted.\n"
            f"Expected at least one of: {explicit_patterns}\n"
            f"Anti-Patterns section:\n" + generated_content.split("## Anti-Patterns")[1].split("##")[0]
        )

    def test_domain_specific_triggers_extracted(self, generated_content):
        """File extension triggers from the README (*.j2, *.jinja2) must appear
        in Auto-Trigger — not just the generic '*.py' backend trigger."""
        trigger_section = generated_content.split("## Auto-Trigger")[1].split("##")[0]
        # The Jinja2 README mentions *.j2 files
        assert (
            ".j2" in trigger_section
        ), f"Domain-specific .j2 trigger missing from Auto-Trigger section:\n{trigger_section}"


# ---------------------------------------------------------------------------
# 4. Regression: poor README produces lower quality than rich README
# ---------------------------------------------------------------------------


class TestQualityComparison:
    """Quality should be measurably better for a rich README vs a bare one."""

    BARE_README = "# My Project\n\nA project.\n"

    RICH_README = JINJA2_README

    def _generate_via_strategy(self, content: str, skill_name: str, tmp_path: Path) -> str:
        strategy = READMEStrategy()
        result = strategy.generate(skill_name, tmp_path, content, "groq")
        return result or ""

    def test_rich_readme_scores_higher(self, tmp_path):
        # Use skill names whose significant words appear in each README's purpose.
        # BARE_README purpose: "A project." → use "project-tool"
        # RICH_README purpose: "Build dynamic code and configuration files from structured templates."
        #   → "jinja2-template-workflow": "jinja2", "template", "workflow" — "template" matches
        bare_content = self._generate_via_strategy(self.BARE_README, "project-tool", tmp_path)
        rich_content = self._generate_via_strategy(self.RICH_README, "jinja2-template-workflow", tmp_path)

        bare_report = validate_quality(bare_content)
        rich_report = validate_quality(rich_content)

        assert (
            rich_report.score >= bare_report.score
        ), f"Rich README score ({rich_report.score}) should be >= bare ({bare_report.score})"

    def test_rich_readme_generates_more_content(self, tmp_path):
        # Use skill names whose significant words appear in each README's purpose.
        # BARE_README purpose: "A project." → use "project-tool"
        # RICH_README purpose: mentions "template" → "jinja2-template-workflow" passes relevance check
        bare_content = self._generate_via_strategy(self.BARE_README, "project-tool", tmp_path)
        rich_content = self._generate_via_strategy(self.RICH_README, "jinja2-template-workflow", tmp_path)

        assert len(rich_content) > len(bare_content), "Rich README should produce more content than a bare one"
