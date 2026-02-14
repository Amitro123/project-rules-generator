"""Tests for content analyzer quality scoring."""

from unittest.mock import Mock

import pytest

from generator.content_analyzer import ContentAnalyzer, QualityBreakdown, QualityReport


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
        report = QualityReport(
            filepath="test.md", score=92, breakdown=breakdown, suggestions=[]
        )
        assert report.status == "✅ Excellent"

    def test_good_status(self):
        """Test status for good score."""
        breakdown = QualityBreakdown(17, 17, 17, 17, 17)
        report = QualityReport(
            filepath="test.md", score=85, breakdown=breakdown, suggestions=[]
        )
        assert report.status == "✅ Good"

    def test_needs_improvement_status(self):
        """Test status for needs improvement score."""
        breakdown = QualityBreakdown(15, 14, 15, 14, 14)
        report = QualityReport(
            filepath="test.md", score=72, breakdown=breakdown, suggestions=[]
        )
        assert report.status == "⚠️  Needs improvement"

    def test_poor_status(self):
        """Test status for poor score."""
        breakdown = QualityBreakdown(10, 12, 8, 11, 9)
        report = QualityReport(
            filepath="test.md", score=50, breakdown=breakdown, suggestions=[]
        )
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
        assert (
            "header" in " ".join(report.suggestions).lower()
            or "structure" in " ".join(report.suggestions).lower()
        )

    def test_analyze_minimal_content(self, analyzer):
        """Test analysis of minimal content."""
        content = "# Title\n\nVery brief content."
        report = analyzer.analyze("rules.md", content)

        # Should identify lack of detail
        assert report.score < 80
        assert any(
            "detail" in s.lower() or "brief" in s.lower() for s in report.suggestions
        )

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
        assert any(
            "code" in s.lower() or "example" in s.lower() for s in report.suggestions
        )

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

        improved_content = (
            "# Improved\n\nBetter content with examples\n\n```bash\ncommand\n```"
        )
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


class TestScoreExtraction:
    """Test score extraction from AI responses."""

    def test_extract_score_from_response(self):
        """Test extracting scores from formatted response."""
        analyzer = ContentAnalyzer(client=Mock())
        response = """
**SCORES:**
Structure: 18
Clarity: 16
Project Grounding: 14
Actionability: 17
Consistency: 15

**SUGGESTIONS:**
1. Add more code examples
2. Reference specific files
"""
        breakdown, suggestions = analyzer._parse_analysis_response(response)

        assert breakdown.structure == 18
        assert breakdown.clarity == 16
        assert breakdown.project_grounding == 14
        assert breakdown.actionability == 17
        assert breakdown.consistency == 15
        assert len(suggestions) == 2
        assert "Add more code examples" in suggestions

    def test_extract_score_clamping(self):
        """Test that scores are clamped to 0-20 range."""
        analyzer = ContentAnalyzer(client=Mock())

        # Test upper bound
        response = "Structure: 25\nClarity: 30"
        breakdown, _ = analyzer._parse_analysis_response(response)
        assert breakdown.structure == 20

        # Test lower bound (negative)
        response = "Structure: -5"
        breakdown, _ = analyzer._parse_analysis_response(response)
        assert breakdown.structure == 0
