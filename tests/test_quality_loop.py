"""Tests for quality feedback loop."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from generator.content_analyzer import ContentAnalyzer, QualityBreakdown, QualityReport
from generator.quality_loop import batch_improve_with_feedback, improve_with_feedback


class TestImproveWithFeedback:
    """Test iterative improvement with feedback loop."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock analyzer for testing."""
        analyzer = Mock(spec=ContentAnalyzer)
        return analyzer

    @pytest.fixture
    def sample_file(self, tmp_path):
        """Create sample file for testing."""
        filepath = tmp_path / "test.md"
        filepath.write_text("# Test\n\nSome content", encoding="utf-8")
        return filepath

    def test_improve_until_target_reached(self, mock_analyzer, sample_file):
        """Test that improvement stops when target score is reached."""
        # Simulate progressive improvement: 70 -> 85 -> 92
        reports = [
            QualityReport(
                filepath="test.md",
                score=70,
                breakdown=QualityBreakdown(14, 14, 14, 14, 14),
                suggestions=["Improve structure"],
                patch="# Improved Test\n\nBetter content",
            ),
            QualityReport(
                filepath="test.md",
                score=85,
                breakdown=QualityBreakdown(17, 17, 17, 17, 17),
                suggestions=["Add examples"],
                patch="# Improved Test\n\nEven better content",
            ),
            QualityReport(
                filepath="test.md",
                score=92,
                breakdown=QualityBreakdown(18, 19, 18, 19, 18),
                suggestions=[],
                patch=None,
            ),
        ]

        mock_analyzer.analyze.side_effect = reports
        mock_analyzer.apply_fix.side_effect = lambda fp, patch: fp.write_text(
            patch, encoding="utf-8"
        )

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=5, verbose=False
        )

        # Should stop after reaching 92 (target is 90)
        assert result.score >= 90
        assert mock_analyzer.analyze.call_count == 3  # 70, 85, 92
        assert mock_analyzer.apply_fix.call_count == 2  # Applied 2 patches

    def test_respects_max_iterations(self, mock_analyzer, sample_file):
        """Test that improvement respects max_iterations limit."""
        # Simulate slow improvement that doesn't reach target
        low_report = QualityReport(
            filepath="test.md",
            score=75,
            breakdown=QualityBreakdown(15, 15, 15, 15, 15),
            suggestions=["Improve"],
            patch="Improved content",
        )

        mock_analyzer.analyze.return_value = low_report
        mock_analyzer.apply_fix.side_effect = lambda fp, patch: fp.write_text(
            patch, encoding="utf-8"
        )

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=3, verbose=False
        )

        # 3 loop iterations + 1 final re-score = 4 analyze calls
        assert mock_analyzer.analyze.call_count == 4
        assert result.score == 75  # Best attempt

    def test_early_exit_on_high_initial_score(self, mock_analyzer, sample_file):
        """Test that no iterations occur if initial score meets target."""
        high_report = QualityReport(
            filepath="test.md",
            score=95,
            breakdown=QualityBreakdown(19, 19, 19, 19, 19),
            suggestions=[],
            patch=None,
        )

        mock_analyzer.analyze.return_value = high_report

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=5, verbose=False
        )

        # Should return immediately without applying fixes
        assert result.score == 95
        assert mock_analyzer.analyze.call_count == 1
        assert mock_analyzer.apply_fix.call_count == 0

    def test_handles_missing_patch(self, mock_analyzer, sample_file):
        """Test handling when analyzer doesn't generate patch."""
        report_no_patch = QualityReport(
            filepath="test.md",
            score=70,
            breakdown=QualityBreakdown(14, 14, 14, 14, 14),
            suggestions=["Improve"],
            patch=None,  # No patch generated
        )

        mock_analyzer.analyze.return_value = report_no_patch

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=5, verbose=False
        )

        # 1 loop iteration + 1 final re-score = 2 analyze calls
        assert mock_analyzer.analyze.call_count == 2
        assert mock_analyzer.apply_fix.call_count == 0
        assert result.score == 70

    def test_handles_apply_fix_failure(self, mock_analyzer, sample_file):
        """Test handling when apply_fix raises exception."""
        report = QualityReport(
            filepath="test.md",
            score=70,
            breakdown=QualityBreakdown(14, 14, 14, 14, 14),
            suggestions=["Improve"],
            patch="Improved content",
        )

        mock_analyzer.analyze.return_value = report
        mock_analyzer.apply_fix.side_effect = IOError("Write failed")

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=5, verbose=False
        )

        # Should handle error gracefully and return best report
        # 1 loop iteration + 1 final re-score = 2 analyze calls
        assert result.score == 70
        assert mock_analyzer.analyze.call_count == 2

    def test_validates_input_parameters(self, mock_analyzer, sample_file):
        """Test input validation."""
        # Invalid target_score
        with pytest.raises(ValueError, match="target_score must be 0-100"):
            improve_with_feedback(
                sample_file, mock_analyzer, target_score=150, max_iterations=5
            )

        # Invalid max_iterations
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            improve_with_feedback(
                sample_file, mock_analyzer, target_score=90, max_iterations=0
            )

        # Non-existent file
        with pytest.raises(FileNotFoundError):
            improve_with_feedback(
                Path("nonexistent.md"), mock_analyzer, target_score=90, max_iterations=5
            )

    def test_tracks_best_attempt(self, mock_analyzer, sample_file):
        """Test that best score is tracked even if later iterations regress."""
        # Simulate improvement then regression: 70 -> 85 -> 80
        reports = [
            QualityReport(
                filepath="test.md",
                score=70,
                breakdown=QualityBreakdown(14, 14, 14, 14, 14),
                suggestions=["Improve"],
                patch="Better content",
            ),
            QualityReport(
                filepath="test.md",
                score=85,
                breakdown=QualityBreakdown(17, 17, 17, 17, 17),
                suggestions=["Improve more"],
                patch="Even better",
            ),
            QualityReport(
                filepath="test.md",
                score=80,  # Regression
                breakdown=QualityBreakdown(16, 16, 16, 16, 16),
                suggestions=["Fix regression"],
                patch="Fixed",
            ),
        ]

        mock_analyzer.analyze.side_effect = reports
        mock_analyzer.apply_fix.side_effect = lambda fp, patch: fp.write_text(
            patch, encoding="utf-8"
        )

        result = improve_with_feedback(
            sample_file, mock_analyzer, target_score=90, max_iterations=3, verbose=False
        )

        # Should return best score (85), not final score (80)
        assert result.score == 85


class TestBatchImproveWithFeedback:
    """Test batch improvement functionality."""

    @pytest.fixture
    def mock_analyzer(self):
        """Create mock analyzer for testing."""
        analyzer = Mock(spec=ContentAnalyzer)
        return analyzer

    @pytest.fixture
    def sample_files(self, tmp_path):
        """Create multiple sample files."""
        files = []
        for i in range(3):
            filepath = tmp_path / f"test{i}.md"
            filepath.write_text(f"# Test {i}\n\nContent", encoding="utf-8")
            files.append(filepath)
        return files

    def test_batch_improve_multiple_files(self, mock_analyzer, sample_files):
        """Test improving multiple files in batch."""

        # Mock different scores for different files
        def mock_analyze(filepath, content, project_path=None):
            if "test0" in filepath:
                score = 95  # Already good
            elif "test1" in filepath:
                score = 85  # Needs improvement
            else:
                score = 70  # Needs more improvement

            return QualityReport(
                filepath=filepath,
                score=score,
                breakdown=QualityBreakdown(
                    score // 5, score // 5, score // 5, score // 5, score // 5
                ),
                suggestions=[],
                patch=None if score >= 90 else "Improved",
            )

        mock_analyzer.analyze.side_effect = mock_analyze
        mock_analyzer.apply_fix.side_effect = lambda fp, patch: fp.write_text(
            patch, encoding="utf-8"
        )

        results = batch_improve_with_feedback(
            sample_files,
            mock_analyzer,
            target_score=90,
            max_iterations=3,
            verbose=False,
        )

        # Should return results for all files
        assert len(results) == 3
        assert all(filepath in results for filepath in sample_files)

    def test_batch_continues_on_individual_failure(self, mock_analyzer, sample_files):
        """Test that batch processing continues even if one file fails."""

        def mock_analyze(filepath, content, project_path=None):
            if "test1" in filepath:
                raise ValueError("Analysis failed")
            return QualityReport(
                filepath=filepath,
                score=95,
                breakdown=QualityBreakdown(19, 19, 19, 19, 19),
                suggestions=[],
                patch=None,
            )

        mock_analyzer.analyze.side_effect = mock_analyze

        results = batch_improve_with_feedback(
            sample_files,
            mock_analyzer,
            target_score=90,
            max_iterations=3,
            verbose=False,
        )

        # Should have results for 2 files (test1 failed)
        assert len(results) == 2
        assert sample_files[1] not in results  # test1 failed


class TestIntegration:
    """Integration tests with real ContentAnalyzer (heuristic mode)."""

    def test_full_workflow_with_real_analyzer(self, tmp_path):
        """Test full improvement workflow with real analyzer."""
        # Create a low-quality file
        filepath = tmp_path / "rules.md"
        low_quality_content = """# Rules
        
Some text.
"""
        filepath.write_text(low_quality_content, encoding="utf-8")

        # Use real analyzer (will use heuristic scoring)
        # Pass tmp_path as allowed_base_path to avoid security check
        analyzer = ContentAnalyzer(
            provider="groq", client=Mock(), allowed_base_path=tmp_path
        )

        # Mock the AI client to avoid actual API calls
        mock_client = Mock()
        mock_client.generate.return_value = """# Project Rules

## Overview
This document defines coding standards and best practices.

## Code Quality
- Use type hints for all functions
- Write comprehensive docstrings
- Follow PEP 8 style guide

## Testing
Run tests with: `pytest tests/ -v`

## Examples
```python
def example_function(param: str) -> int:
    \"\"\"Example with type hints.\"\"\"
    return len(param)
```
"""
        analyzer.client = mock_client

        # Run improvement
        # Run improvement
        improve_with_feedback(
            filepath, analyzer, target_score=90, max_iterations=3, verbose=False
        )

        # Verify file was updated
        updated_content = filepath.read_text(encoding="utf-8")
        assert len(updated_content) > len(low_quality_content)
        assert (
            "type hints" in updated_content.lower()
            or "examples" in updated_content.lower()
        )
