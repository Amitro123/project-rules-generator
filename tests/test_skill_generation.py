"""Tests for skill generation prompt utilities."""

from pathlib import Path
from typing import Dict

import pytest

from generator.prompts.skill_generation import detect_project_tools


def test_detect_tools_defaults():
    """Test with no project path and no tech stack."""
    tools = detect_project_tools()
    assert tools == {}


def test_detect_tools_from_tech_stack():
    """Test detection based on tech stack list."""
    # Python defaults
    tools = detect_project_tools(tech_stack=["python"])
    assert tools.get("check") == "ruff check ."
    assert tools.get("lint") == "mypy ."

    # Pytest
    tools = detect_project_tools(tech_stack=["python", "pytest"])
    assert tools.get("test") == "pytest"

    # TypeScript/React defaults
    tools = detect_project_tools(tech_stack=["typescript", "react"])
    assert tools.get("check") == "npx tsc --noEmit"
    assert tools.get("lint") == "npx eslint ."

    # Jest
    tools = detect_project_tools(tech_stack=["typescript", "jest"])
    assert tools.get("test") == "npx jest"


def test_detect_tools_from_ruff_config(tmp_path: Path):
    """Test detection from ruff configuration files."""
    # ruff.toml
    (tmp_path / "ruff.toml").touch()
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "ruff check ."
    assert tools.get("format") == "ruff format ."

    # .ruff.toml (should be same)
    (tmp_path / "ruff.toml").unlink()
    (tmp_path / ".ruff.toml").touch()
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "ruff check ."
    assert tools.get("format") == "ruff format ."


def test_detect_tools_from_pyproject(tmp_path: Path):
    """Test detection from pyproject.toml content."""
    pyproject = tmp_path / "pyproject.toml"

    # Case 1: Ruff
    pyproject.write_text('[tool.ruff]\nline-length = 88', encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "ruff check ."
    assert tools.get("format") == "ruff format ."

    # Case 2: Flake8 and Black
    pyproject.write_text('[tool.flake8]\nmax-line-length = 88\n[tool.black]', encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "flake8 ."
    assert tools.get("format") == "black ."

    # Case 3: Mypy
    pyproject.write_text('[tool.mypy]\nstrict = true', encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("lint") == "mypy ."


def test_detect_tools_from_requirements(tmp_path: Path):
    """Test detection from requirements files."""
    req_file = tmp_path / "requirements.txt"

    # Case 1: Ruff
    req_file.write_text("ruff==0.1.0", encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "ruff check ."

    # Case 2: Mypy and Black
    req_file.write_text("mypy\nblack", encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("lint") == "mypy ."
    assert tools.get("format") == "black ."

    # Check requirements-dev.txt as well
    req_file.unlink()
    dev_req = tmp_path / "requirements-dev.txt"
    dev_req.write_text("ruff", encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path)
    assert tools.get("check") == "ruff check ."


def test_detect_tools_priority(tmp_path: Path):
    """Test priority of detection methods."""
    # Config file should take precedence over tech stack defaults if they conflict
    # Example: If ruff is in config, it should be detected even if tech stack says nothing about python
    # But current implementation adds defaults if tech stack has python and tool is missing.

    # Let's test mixed scenario:
    # project has python tech stack (adds ruff check/mypy lint defaults)
    # but requirements has flake8 (doesn't trigger ruff check override unless ruff is missing)

    # Actually, current implementation:
    # 1. Checks ruff config files -> sets check/format
    # 2. Checks pyproject.toml -> sets check/format/lint
    # 3. Checks requirements -> sets check/lint/format IF NOT present
    # 4. Checks tech stack -> sets test/check/lint IF NOT present

    # So explicit config (1 & 2) overrides requirements (3) which overrides defaults (4).

    # Test: pyproject has flake8, tech stack has python. Result should be flake8.
    (tmp_path / "pyproject.toml").write_text("[tool.flake8]", encoding="utf-8")
    tools = detect_project_tools(project_path=tmp_path, tech_stack=["python"])

    # logic:
    # 1. ruff config: no
    # 2. pyproject: flake8 -> tools['check'] = 'flake8 .'
    # 3. requirements: no
    # 4. tech stack: python -> if 'check' not in tools -> ruff.
    # Since 'check' is already 'flake8 .', it should NOT be overwritten by ruff default.

    assert tools.get("check") == "flake8 ."
    # 'lint' was not set by pyproject, so python default (mypy) should be added
    assert tools.get("lint") == "mypy ."
