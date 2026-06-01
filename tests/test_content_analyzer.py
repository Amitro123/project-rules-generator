"""Tests for content analyzer quality scoring."""

from unittest.mock import Mock

import pytest

from generator.analyzers.content_analyzer import ContentAnalyzer, QualityBreakdown, QualityReport


class TestQualityBreakdown:
    """Test quality breakdown calculations."""

    def test_total_score_calculation(self):
        """Test that total score is sum of all criteria."""
        breakdown = QualityBreakdown(
            structure=18,
            clarity=16,
            project_grounding=14,
            actionability=17,
            consistency=15,
        )
        assert breakdown.total == 80


class TestQualityReport:
    """Test quality report status."""

    def test_excellent_status(self):
        """Test status for excellent score."""
        breakdown = QualityBreakdown(18, 19, 18, 19, 18)
        report = QualityReport(filepath="test.md", score=92, breakdown=breakdown, suggestions=[])
        assert report.status == "✅ Excellent"

    def test_good_status(self):
        """Test status for good score."""
        breakdown = QualityBreakdown(17, 17, 17, 17, 17)
        report = QualityReport(filepath="test.md", score=85, breakdown=breakdown, suggestions=[])
        assert report.status == "✅ Good"

    def test_needs_improvement_status(self):
        """Test status for needs improvement score."""
        breakdown = QualityBreakdown(15, 14, 15, 14, 14)
        report = QualityReport(filepath="test.md", score=72, breakdown=breakdown, suggestions=[])
        assert report.status == "⚠️  Needs improvement"

    def test_poor_status(self):
        """Test status for poor score."""
        breakdown = QualityBreakdown(10, 12, 8, 11, 9)
        report = QualityReport(filepath="test.md", score=50, breakdown=breakdown, suggestions=[])
        assert report.status == "❌ Poor quality"


class TestContentAnalyzer:
    """Test content analyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance with mock client (uses heuristic fallback)."""
        mock_client = Mock()
        mock_client.generate.return_value = None
        return ContentAnalyzer(client=mock_client)

    def test_analyze_well_structured_content(self, analyzer):
        """Test analysis of well-structured content."""
        content = """# Project Rules

## Context
This is a Python FastAPI project for building REST APIs.

## Guidelines

### Code Style
- Use `black` for formatting
- Run `pytest` for testing
- Follow PEP 8 conventions

### File Structure
```
src/
  api/
    routes.py
    models.py
  tests/
    test_api.py
```

## Commands

```bash
# Run tests
pytest tests/

# Start server
uvicorn main:app --reload
```
"""
        report = analyzer.analyze("rules.md", content)

        # Should score reasonably well
        assert report.score >= 60
        assert report.breakdown.structure >= 12
        assert report.breakdown.actionability >= 10
        assert isinstance(report.suggestions, list)

    def test_analyze_poor_content(self, analyzer):
        """Test analysis of poor quality content."""
        content = """TODO: Add content here

Some random text without structure or examples.
"""
        report = analyzer.analyze("rules.md", content)

        # Should score poorly
        assert report.score < 70
        assert len(report.suggestions) > 0
        assert "header" in " ".join(report.suggestions).lower() or "structure" in " ".join(report.suggestions).lower()

    def test_analyze_minimal_content(self, analyzer):
        """Test analysis of minimal content."""
        content = "# Title\n\nVery brief content."
        report = analyzer.analyze("rules.md", content)

        # Should identify lack of detail
        assert report.score < 80
        assert any("detail" in s.lower() or "brief" in s.lower() for s in report.suggestions)

    def test_analyze_missing_code_examples(self, analyzer):
        """Test detection of missing code examples."""
        content = """# Project Guide

## Overview
This project does things.

## Usage
You should use it properly.
"""
        report = analyzer.analyze("rules.md", content)

        # Should identify lack of actionability
        assert report.breakdown.actionability < 18
        assert any("code" in s.lower() or "example" in s.lower() for s in report.suggestions)

    def test_patch_generation_for_low_score(self, analyzer):
        """Test that patch is generated for scores < 85."""
        content = "# Bad\n\nTODO: write this"
        report = analyzer.analyze("rules.md", content)

        if report.score < 85:
            # Patch should be generated (may be None if AI unavailable)
            # In heuristic mode, patch generation requires AI, so it returns original
            assert report.patch is not None

    def test_no_patch_for_high_score(self, analyzer):
        """Test that no patch is generated for good scores."""
        content = """# Excellent Documentation

## Context
This Python project uses FastAPI for `src/api/main.py`.

## Commands

```bash
pytest tests/
uvicorn main:app
```

## Guidelines
- Run `black .` for formatting
- Execute `pytest` before commits
- Update `README.md` when adding features
"""
        report = analyzer.analyze("rules.md", content)

        # If score is high enough, no patch needed
        if report.score >= 85:
            assert report.patch is None

    def test_apply_fix(self, tmp_path):
        """Test applying fix to file."""
        test_file = tmp_path / "test.md"
        original_content = "# Original\n\nContent"
        test_file.write_text(original_content, encoding="utf-8")

        # Create analyzer with tmp_path as allowed base for security validation
        analyzer = ContentAnalyzer(client=Mock(), allowed_base_path=tmp_path)

        improved_content = "# Improved\n\nBetter content with examples\n\n```bash\ncommand\n```"
        analyzer.apply_fix(test_file, improved_content)

        result = test_file.read_text(encoding="utf-8")
        assert result == improved_content

    def test_heuristic_structure_scoring(self, analyzer):
        """Test heuristic structure scoring."""
        # Good structure
        good_content = """# Main Title

## Section 1
Content here.

## Section 2
More content.

## Section 3
Even more.
"""
        report = analyzer.analyze("test.md", good_content)
        assert report.breakdown.structure >= 13

        # Poor structure (no headers)
        poor_content = "Just text without any structure or headers."
        report = analyzer.analyze("test.md", poor_content)
        assert report.breakdown.structure < 13

    def test_heuristic_grounding_scoring(self, analyzer):
        """Test heuristic project grounding scoring."""
        # Well-grounded content
        grounded = """# Guide

Use `src/main.py` to start the app.
Edit `config.yaml` for settings.
Run tests with `pytest tests/test_api.py`.
"""
        report = analyzer.analyze("test.md", grounded)
        assert report.breakdown.project_grounding >= 10

        # Generic content
        generic = """# Guide

Do things properly.
Follow best practices.
Write good code.
"""
        report = analyzer.analyze("test.md", generic)
        assert report.breakdown.project_grounding < 12


class TestScorerReconciliation:
    """Lock in the create-rules vs prg-quality scorer reconciliation.

    Regression guard for the two defects that made `prg quality` score a
    well-formed Cowork-format rules.md ~40 points below what `prg create-rules`
    reported on the same file:

      1. A leading YAML frontmatter block hid the H1 title (lost structure bonus).
      2. The consistency dimension only recognized generic
         "Overview/Guidelines/Testing" headers, never PRG's own emoji-prefixed
         section names — so it was stuck at the 6/20 base.

    Both helpers (`_strip_frontmatter`, `_header_has_theme`) existed but were
    never wired into `_heuristic_breakdown`; these tests fail if that wiring is
    removed again.
    """

    # A trimmed Cowork-format document: frontmatter + emoji-prefixed PRG headers.
    COWORK_DOC = (
        "---\n"
        "project: demo\n"
        "version: 2.0\n"
        "---\n"
        "# 🤖 demo - Coding Rules\n\n"
        "## 📋 Priority Areas\n- rest_api_patterns\n- test_coverage\n\n"
        "## 💻 Coding Standards\n- Use type hints on all public signatures\n"
        "- Validate request bodies with Pydantic models\n\n"
        "## 🚫 Critical Anti-Patterns (NEVER DO THIS)\n- Don't hardcode API keys\n"
    )

    def test_score_text_needs_no_ai_client(self):
        """score_text is a pure classmethod — callable without constructing a client.

        create-rules relies on this to surface the shared document score without
        spinning up an AI provider.
        """
        report = ContentAnalyzer.score_text("rules.md", self.COWORK_DOC)
        assert isinstance(report, QualityReport)
        assert 0 <= report.score <= 100

    def test_frontmatter_does_not_cost_the_title_bonus(self):
        """An H1 hidden behind frontmatter must still earn the structure title bonus."""
        with_fm = ContentAnalyzer.score_text("rules.md", self.COWORK_DOC)
        without_fm = ContentAnalyzer.score_text("rules.md", self.COWORK_DOC.split("---\n", 2)[-1])
        # Stripping frontmatter ourselves should not change the structure score —
        # the analyzer already strips it internally.
        assert with_fm.breakdown.structure == without_fm.breakdown.structure
        assert with_fm.breakdown.structure >= 16

    def test_prg_section_vocabulary_credits_consistency(self):
        """Emoji-prefixed PRG headers must satisfy all three consistency themes."""
        report = ContentAnalyzer.score_text("rules.md", self.COWORK_DOC)
        # Priority Areas (overview) + Coding Standards (guideline) + Anti-Patterns
        # (testing) → full 6 + 4 + 4 + 4.
        assert report.breakdown.consistency == 18

    def test_analyze_delegates_to_shared_scorer(self):
        """`prg quality` (analyze) and the shared score_text agree on score/breakdown.

        analyze() only adds patch/Opik on top of score_text(); the headline number
        must be identical so create-rules and prg quality can never contradict.
        """
        analyzer = ContentAnalyzer(client=Mock())
        shared = ContentAnalyzer.score_text("rules.md", self.COWORK_DOC)
        via_analyze = analyzer.analyze("rules.md", self.COWORK_DOC)
        assert via_analyze.score == shared.score
        assert via_analyze.breakdown.total == shared.breakdown.total


class TestScoreExtraction:
    """Test score extraction from AI responses."""
