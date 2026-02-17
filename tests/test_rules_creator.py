
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from generator.rules_creator import CoworkRulesCreator, RulesMetadata, Rule

@pytest.fixture
def temp_project(tmp_path):
    """Create a temp project structure."""
    (tmp_path / "README.md").write_text("# Test Project\n\nUses FastAPI and React.")
    (tmp_path / "requirements.txt").write_text("fastapi\nreact")
    return tmp_path

class TestCoworkRulesCreator:
    
    def test_tech_stack_detection(self, temp_project):
        """Test that tech stack is detected from README."""
        creator = CoworkRulesCreator(temp_project)
        readme = (temp_project / "README.md").read_text()
        
        tech_stack = creator._detect_tech_stack(readme, None)
        
        assert "fastapi" in tech_stack
        assert "react" in tech_stack

    def test_rules_generation_priority(self, temp_project):
        """Test that high priority rules are generated for detected tech."""
        creator = CoworkRulesCreator(temp_project)
        metadata = RulesMetadata(
            project_name="Test",
            tech_stack=["fastapi"],
            project_type="python-api",
            priority_areas=["rest_api_patterns"]
        )
        
        rules = creator._generate_rules(metadata, None)
        
        # Check for FastAPI high priority rule
        fastapi_high = any(
            r.priority == "High" and "async/await" in r.content 
            for r in rules["Coding Standards"]
        )
        assert fastapi_high

    def test_quality_validation(self, temp_project):
        """Test quality report generation."""
        creator = CoworkRulesCreator(temp_project)
        metadata = RulesMetadata(project_name="Test")
        
        # Create minimal rules
        rules_by_category = {
            "General": [Rule("Test rule", priority="High")]
        }
        
        content = "# Test\n## Priority Areas" # Incomplete content
        
        report = creator._validate_quality(content, metadata, rules_by_category)
        
        assert not report.passed
        assert report.score < 100
        assert any("Missing sections" in i for i in report.issues)

    @patch("subprocess.run")
    def test_git_antipatterns(self, mock_run, temp_project):
        """Test extraction of git anti-patterns."""
        creator = CoworkRulesCreator(temp_project)
        creator._git_available = True
        
        # Mock git log output for hot spots
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "file.py\n" * 15 # 15 changes to file.py
        
        antipatterns = creator._extract_git_antipatterns()
        
        assert len(antipatterns) > 0
        assert "Hot spots detected" in antipatterns[0].content

    def test_end_to_end_generation(self, temp_project):
        """Test full generation flow."""
        creator = CoworkRulesCreator(temp_project)
        readme = (temp_project / "README.md").read_text()
        
        content, metadata, quality = creator.create_rules(readme)
        
        assert "FastAPI" in content or "fastapi" in content
        assert "## 🎯 Coding Standards" in content
        assert quality.score > 50 # Basic score check
