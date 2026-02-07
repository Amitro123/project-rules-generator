
import pytest
import sys
from pathlib import Path

# Add project root to sys.path so we can import analyzer
sys.path.append(str(Path(__file__).parent.parent))


from analyzer.readme_parser import (
    extract_purpose, extract_tech_stack, 
    extract_auto_triggers, extract_process_steps, 
    extract_anti_patterns
)

SAMPLE_README = """
# My Project

This is a description of the project.

## Installation

1. Install dependencies:
   ```bash
   pip install my-project
   ```
2. Run setup.

## Usage

### Quick Start
1. Start server:
   `python run.py`

## Features
- Fast
- Secure

## Troubleshooting

- Problem: It crashes.
- Solution: Restart it.
"""

def test_extract_purpose():
    purpose = extract_purpose(SAMPLE_README)
    assert "This is a description of the project" in purpose

def test_extract_tech_stack():
    # SAMPLE_README doesn't have keywords from TECH_KEYWORDS except maybe 'python' in code block if we didn't strip it? 
    # But extract_tech_stack strips code blocks!
    # Let's add a tech keyword in text
    readme = SAMPLE_README + "\nBuilt with Python and FastAPI."
    tech = extract_tech_stack(readme)
    assert "python" in tech
    assert "fastapi" in tech

def test_extract_auto_triggers():
    readme = "Built with Python."
    triggers = extract_auto_triggers(readme, "my-skill")
    assert any("my" in t and "skill" in t for t in triggers) # User mentions
    assert "Working in backend code: *.py" in triggers

def test_extract_process_steps():
    # Should extract from Installation or Quick Start
    steps = extract_process_steps(SAMPLE_README)
    # Expect "Install dependencies" and code block, "Run setup"
    # Actually logic collects lines starting with digit or code blocks
    assert any("Install dependencies" in s for s in steps)
    assert any("pip install my-project" in s for s in steps)
    assert any("Run setup" in s for s in steps)

def test_extract_anti_patterns():
    tech = ['ffmpeg', 'redis']
    patterns = extract_anti_patterns("dummy", tech)
    assert any("FFmpeg" in p for p in patterns)
    assert any("Redis" in p for p in patterns)
    assert any("Not testing" in p for p in patterns)
