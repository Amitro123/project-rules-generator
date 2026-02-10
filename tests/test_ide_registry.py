"""Tests for IDE Registry."""

import json
from pathlib import Path
from src.integrations.ide_registry import IDERegistry
import pytest

@pytest.fixture
def project_path(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / '.clinerules').mkdir()
    (project / '.clinerules' / 'rules.md').write_text("# Rules")
    return project

def test_detect_ide(project_path):
    registry = IDERegistry()

    # Default
    assert registry.detect_ide(project_path) == 'cline'

    # .vscode
    (project_path / '.vscode').mkdir()
    assert registry.detect_ide(project_path) == 'vscode'

    # .cursorrules
    (project_path / '.cursorrules').touch()
    assert registry.detect_ide(project_path) == 'cursor'

def test_register_antigravity(project_path):
    registry = IDERegistry()
    rules_path = project_path / '.clinerules' / 'rules.md'

    registry.register('antigravity', project_path, rules_path)

    settings_path = project_path / '.vscode' / 'settings.json'
    assert settings_path.exists()
    settings = json.loads(settings_path.read_text())
    assert settings['antigravity.rulesPath'] == '.clinerules/rules.md'

def test_register_cursor(project_path):
    registry = IDERegistry()
    rules_path = project_path / '.clinerules' / 'rules.md'

    registry.register('cursor', project_path, rules_path)

    target = project_path / '.cursorrules'
    assert target.exists()
    if target.is_symlink():
        assert target.readlink() == Path('.clinerules/rules.md')
    else:
        # Fallback to copy if symlink failed (e.g. windows without privs)
        assert target.read_text() == "# Rules"

def test_register_vscode(project_path):
    registry = IDERegistry()
    rules_path = project_path / '.clinerules' / 'rules.md'

    registry.register('vscode', project_path, rules_path)

    target = project_path / 'AGENTS.md'
    assert target.exists()
