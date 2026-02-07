import pytest
from pathlib import Path

# Define the expected builtin skills and their locations
EXPECTED_SKILLS = [
    "brainstorming",
    "writing-plans",
    "subagent-driven-development",
    "systematic-debugging",
    "requesting-code-review",
    "test-driven-development",
    "meta/writing-skills"
]

@pytest.fixture
def skills_root():
    """Returns the root path of the skills directory."""
    # Assuming code is running from project root or tests/
    # Adjust this based on actual project structure
    root = Path(__file__).parent.parent / "generator" / "skills"
    if not root.exists():
         root = Path("generator/skills") # try relative to CWD
    return root

def test_skills_directory_structure(skills_root):
    """Verify the 3-layer directory structure exists."""
    assert skills_root.exists(), "skills/ directory missing"
    assert (skills_root / "builtin").is_dir(), "skills/builtin/ directory missing"
    assert (skills_root / "awesome").is_dir(), "skills/awesome/ directory missing"
    assert (skills_root / "learned").is_dir(), "skills/learned/ directory missing"

@pytest.mark.parametrize("skill_path", EXPECTED_SKILLS)
def test_builtin_skill_exists(skills_root, skill_path):
    """Verify each expected builtin skill has a SKILL.md file."""
    skill_file = skills_root / "builtin" / skill_path / "SKILL.md"
    assert skill_file.exists(), f"Missing SKILL.md for {skill_path}"

@pytest.mark.parametrize("skill_path", EXPECTED_SKILLS)
def test_builtin_skill_content_structure(skills_root, skill_path):
    """Verify SKILL.md files contain required sections."""
    skill_file = skills_root / "builtin" / skill_path / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    
    # Required headers based on our template/meta-skill
    assert "# Skill:" in content, f"{skill_path} missing '# Skill:' header"
    assert "## Purpose" in content, f"{skill_path} missing '## Purpose' section"
    assert "## Auto-Trigger" in content, f"{skill_path} missing '## Auto-Trigger' section"
    # Some skills might name "Process" differently (e.g. "4-Phase Process"), so let's check broadly
    assert "## " in content, f"{skill_path} seems to have no H2 headers" 

def test_skills_readme_exists(skills_root):
    """Verify skills/README.md exists."""
    readme = skills_root / "README.md"
    assert readme.exists(), "skills/README.md missing"
