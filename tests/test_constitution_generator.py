"""Tests for constitution generator."""
import pytest
from pathlib import Path
from click.testing import CliRunner

from generator.constitution_generator import generate_constitution
from main import main


def _make_enhanced_context(project_type='cli-tool', tech_stack=None, python_deps=None,
                           node_deps=None, entry_points=None, patterns=None,
                           test_framework='pytest', test_files=5, has_conftest=True,
                           has_fixtures=False):
    """Helper to build a realistic enhanced_context dict."""
    tech_stack = tech_stack or ['python']
    python_deps = python_deps or []
    node_deps = node_deps or []
    entry_points = entry_points or ['main.py']
    patterns = patterns or [project_type]

    return {
        'metadata': {
            'project_type': project_type,
            'tech_stack': tech_stack,
            'languages': ['python'],
            'has_tests': True,
        },
        'dependencies': {
            'python': [{'name': d, 'version': '*'} for d in python_deps],
            'node': [{'name': d, 'version': '*'} for d in node_deps],
        },
        'structure': {
            'type': project_type,
            'entry_points': entry_points,
            'patterns': patterns,
        },
        'test_patterns': {
            'framework': test_framework,
            'test_files': test_files,
            'has_conftest': has_conftest,
            'has_fixtures': has_fixtures,
            'patterns': ['unit'],
        },
        'readme': {},
    }


class TestConstitutionGeneratorCLI:
    """Test constitution for a Python CLI project."""

    def test_cli_project_references_click(self):
        ctx = _make_enhanced_context(
            project_type='cli-tool',
            python_deps=['click', 'pydantic', 'pytest'],
            tech_stack=['python', 'pytest'],
        )
        result = generate_constitution('my-cli', ctx)

        assert 'Click' in result or 'click' in result.lower()
        assert 'constitution' in result.lower() or 'Constitution' in result

    def test_cli_project_references_pytest(self):
        ctx = _make_enhanced_context(
            python_deps=['click', 'pytest'],
            tech_stack=['python', 'pytest'],
        )
        result = generate_constitution('my-cli', ctx)

        assert 'pytest' in result

    def test_cli_project_references_pydantic(self):
        ctx = _make_enhanced_context(
            python_deps=['click', 'pydantic', 'pytest'],
            tech_stack=['python'],
        )
        result = generate_constitution('my-cli', ctx)

        assert 'Pydantic' in result or 'pydantic' in result.lower()

    def test_constitution_has_all_sections(self):
        ctx = _make_enhanced_context(
            python_deps=['click', 'pydantic', 'pytest'],
            tech_stack=['python', 'pytest'],
        )
        result = generate_constitution('my-cli', ctx)

        assert '## Code Quality Principles' in result
        assert '## Testing Standards' in result
        assert '## Architecture Decisions' in result
        assert '## Development Guidelines' in result


class TestConstitutionGeneratorFastAPI:
    """Test constitution for a FastAPI project."""

    def test_fastapi_references_depends(self):
        ctx = _make_enhanced_context(
            project_type='fastapi-api',
            python_deps=['fastapi', 'uvicorn', 'pydantic', 'pytest'],
            tech_stack=['python', 'pytest'],
            entry_points=['app/main.py'],
        )
        result = generate_constitution('my-api', ctx)

        assert 'Depends()' in result

    def test_fastapi_references_async(self):
        ctx = _make_enhanced_context(
            project_type='fastapi-api',
            python_deps=['fastapi', 'uvicorn'],
            tech_stack=['python'],
            entry_points=['app/main.py'],
        )
        result = generate_constitution('my-api', ctx)

        assert 'async' in result

    def test_fastapi_references_uvicorn(self):
        ctx = _make_enhanced_context(
            project_type='fastapi-api',
            python_deps=['fastapi', 'uvicorn'],
            tech_stack=['python'],
        )
        result = generate_constitution('my-api', ctx)

        # uvicorn implies async handlers
        assert 'async' in result


class TestConstitutionGeneratorSelfProject:
    """Test constitution for the project-rules-generator itself."""

    def test_self_project_constitution(self):
        ctx = _make_enhanced_context(
            project_type='cli-tool',
            python_deps=['click', 'pydantic', 'pytest', 'pyyaml', 'tqdm'],
            tech_stack=['python', 'pytest'],
            entry_points=['main.py', 'project_rules_generator.py'],
            has_conftest=True,
        )
        result = generate_constitution('project-rules-generator', ctx)

        assert 'project-rules-generator' in result
        assert 'pytest' in result
        assert 'Click' in result or 'click' in result.lower()
        assert 'Pydantic' in result or 'pydantic' in result.lower()
        assert '## Code Quality Principles' in result


class TestConstitutionCLIFlag:
    """Test --constitution flag via CliRunner."""

    def test_constitution_flag_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])

        assert '--constitution' in result.output

    def test_constitution_flag_generates_file(self, sample_project_path):
        runner = CliRunner()
        result = runner.invoke(main, [
            str(sample_project_path),
            '--constitution',
            '--no-commit',
            '--verbose',
        ])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}\n{result.exception}"
        # Check the file was generated (path mentioned in output)
        assert 'constitution' in result.output.lower() or 'Generated files' in result.output

    def test_constitution_flag_creates_file(self, tmp_path):
        """Test that constitution.md is actually created on disk."""
        # Create a minimal project
        (tmp_path / 'README.md').write_text('# Test Project\n\nA test.')
        (tmp_path / 'main.py').write_text('import click\n')
        (tmp_path / 'requirements.txt').write_text('click\npydantic\n')

        runner = CliRunner()
        result = runner.invoke(main, [
            str(tmp_path),
            '--constitution',
            '--no-commit',
            '--verbose',
        ])

        assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}\n{result.exception}"
        constitution_path = tmp_path / '.clinerules' / 'constitution.md'
        assert constitution_path.exists(), f"constitution.md not created. Output:\n{result.output}"
        content = constitution_path.read_text(encoding='utf-8')
        assert '## Code Quality Principles' in content
