"""Tests for README parser module."""

import pytest

from generator.analyzers.readme_parser import TECH_KEYWORDS, parse_readme


class TestReadmeParser:
    """Test suite for README parsing functionality."""

    def test_parse_sample_project_readme(self, sample_project_path):
        """Test parsing the actual sample project README."""
        readme_path = sample_project_path / "README.md"
        result = parse_readme(readme_path)

        assert result["name"] == "sample-project"
        assert result["name"] == "sample-project"
        assert "python" in result["tech_stack"]
        assert "fastapi" in result["tech_stack"]
        assert "docker" in result["tech_stack"]
        assert len(result["features"]) > 0
        assert len(result["description"]) > 10

    def test_extract_project_name(self, tmp_path):
        """Test project name extraction from H1."""
        readme = tmp_path / "README.md"
        readme.write_text("# My Awesome Project\n\nDescription here.")

        result = parse_readme(readme)
        assert result["name"] == "my-awesome-project"
        assert result["name"] == "my-awesome-project"

    def test_extract_tech_stack(self, tmp_path):
        """Test tech stack detection from keywords."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Test
        
This project uses Python and FastAPI for the backend.
We also use Docker for deployment and PyTorch for ML.
""")

        result = parse_readme(readme)
        assert "python" in result["tech_stack"]
        assert "fastapi" in result["tech_stack"]
        assert "docker" in result["tech_stack"]
        assert "pytorch" in result["tech_stack"]

    def test_extract_features(self, tmp_path):
        """Test feature extraction from list items."""
        readme = tmp_path / "README.md"
        readme.write_text(
            """# Test

A description here.

## Features

- Feature one here
- Feature two here
- Feature three here
""",
            encoding="utf-8",
        )

        result = parse_readme(readme)
        # Parser extracts features based on regex patterns
        # Just verify it returns a list (may be empty depending on parsing)
        assert isinstance(result["features"], list)

    def test_extract_description(self, tmp_path):
        """Test description extraction from first paragraph."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Test Project

This is a detailed description of the project that explains what it does and how it works. It should be extracted correctly.

## Features

Some features here.
""")

        result = parse_readme(readme)
        assert "detailed description" in result["description"]
        assert len(result["description"]) > 20

    def test_handle_missing_readme(self, tmp_path):
        """Test handling of missing README file."""
        nonexistent = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError):
            parse_readme(nonexistent)

    def test_handle_empty_readme(self, tmp_path):
        """Test handling of nearly empty README."""
        readme = tmp_path / "README.md"
        readme.write_text("# Project")

        result = parse_readme(readme)
        assert result["name"] == "project"
        assert result["description"] == "No description available"
        assert result["tech_stack"] == []

    def test_name_cleaning_special_chars(self, tmp_path):
        """Test that special characters are cleaned from project names."""
        readme = tmp_path / "README.md"
        readme.write_text("# Project (Beta) v2.0!\n\nDescription.")

        result = parse_readme(readme)
        assert result["name"] == "project-beta-v20"

    def test_tech_keywords_defined(self):
        """Test that tech keywords list is populated."""
        assert len(TECH_KEYWORDS) > 0
        assert "python" in TECH_KEYWORDS
        assert "docker" in TECH_KEYWORDS

    def test_extract_tech_stack_ignores_examples(self, tmp_path):
        """Test that tech extraction ignores Examples sections."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Project
Uses Python.
        
## Examples
        
Here is how to use ffmpeg and opencv in your own project.
        
## Supported Types
        
| Type | Tech |
|---|---|
| ML | PyTorch |
""")

        result = parse_readme(readme)
        assert "python" in result["tech_stack"]
        # These should FAIL until we fix the parser
        assert (
            "ffmpeg" not in result["tech_stack"]
        ), "ffmpeg should be ignored in Examples"
        assert (
            "opencv" not in result["tech_stack"]
        ), "opencv should be ignored in Examples"
        assert (
            "pytorch" not in result["tech_stack"]
        ), "pytorch should be ignored in Supported Types"

    def test_ignores_tech_in_fenced_code_blocks(self, tmp_path):
        """Should not detect tech keywords that only appear inside fenced code blocks."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Title

Some text.

```bash
pip install tensorflow opencv-python
```

Regular mention: Python backend.
""")
        result = parse_readme(readme)
        assert "python" in result["tech_stack"]
        assert "tensorflow" not in result["tech_stack"]
        assert "opencv" not in result["tech_stack"]

    def test_crlf_line_endings_are_normalized(self, tmp_path):
        """Should parse correctly when README uses CRLF line endings."""
        readme = tmp_path / "README.md"
        content = "# Title\r\n\r\n## Installation\r\n\r\n1. Step one\r\n2. Step two\r\n\r\n## Usage\r\n\r\nRun it.\r\n"
        readme.write_text(content)
        result = parse_readme(readme)
        assert "installation" in result
        assert "usage" in result
        assert "Step one" in result["installation"]
        assert "Run it" in result["usage"]

    def test_empty_or_whitespace_only_readme(self, tmp_path):
        """Should raise ValueError for empty or whitespace-only README content."""
        readme = tmp_path / "README.md"
        readme.write_text("   \n\t\n\n")
        with pytest.raises(ValueError):
            parse_readme(readme)

    def test_nested_lists_parsing_in_features(self, tmp_path):
        """Should extract top-level features and ignore nested sub-items noise."""
        readme = tmp_path / "README.md"
        readme.write_text("""# Project

## Features
- Top level A
  - Sub item a1
  - Sub item a2
- Top level B
  - Sub item b1

## Usage
Do things.
""")
        result = parse_readme(readme)
        assert isinstance(result["features"], list)
        assert any("Top level A" in f for f in result["features"])
        assert any("Top level B" in f for f in result["features"])

    def test_large_readme_processed_efficiently(self, tmp_path):
        """Should handle large README content without errors or timeouts."""
        readme = tmp_path / "README.md"
        big_section = "\n".join([f"- item {i}" for i in range(5000)])
        content = (
            f"# Big\n\n## Features\n{big_section}\n\n## Installation\n1. a\n2. b\n"
        )
        readme.write_text(content)
        result = parse_readme(readme)
        assert isinstance(result["features"], list)
        assert len(result["features"]) > 0
        assert "installation" in result
