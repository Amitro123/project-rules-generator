"""Tests for CLI integration."""
import pytest
from pathlib import Path
from click.testing import CliRunner
from main import main, load_config


class TestCLI:
    """Test suite for command line interface."""

    def test_load_config_default(self):
        """Test loading default config when file exists."""
        config = load_config()
        
        assert 'llm' in config
        assert 'git' in config
        assert 'generation' in config
    
    def test_cli_basic_run(self, sample_project_path, tmp_path):
        """Test basic CLI execution."""
        runner = CliRunner()
        
        # Run on sample project
        result = runner.invoke(main, [
            str(sample_project_path),
            '--verbose',
            '--no-commit'
        ])
        
        assert result.exit_code == 0
        assert 'Generated files' in result.output
        assert 'sample-project-rules.md' in result.output
        assert 'sample-project-skills.md' in result.output
    
    def test_cli_missing_readme(self, tmp_path):
        """Test CLI error when no README exists."""
        runner = CliRunner()
        empty_dir = tmp_path / 'empty'
        empty_dir.mkdir()
        
        result = runner.invoke(main, [str(empty_dir)])
        
        assert result.exit_code == 1
        assert 'Error: No README.md found' in result.output
        assert 'No README.md' in result.output
    
    def test_cli_default_path(self, tmp_path):
        """Test CLI with default path (current directory).."""
        runner = CliRunner()
        
        # Create a README in temp directory
        (tmp_path / 'README.md').write_text('# Test\n\nDescription.')
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ['--no-commit', '--verbose'])
            # Should use current directory
            assert result.exit_code == 0 or 'Target' in result.output
    
    def test_cli_interactive_cancel(self, sample_project_path):
        """Test interactive mode with 'no' response."""
        runner = CliRunner()
        
        result = runner.invoke(main, [
            str(sample_project_path),
            '--interactive',
            '--no-commit'
        ], input='n\n')  # Respond 'no' to continue prompt
        
        assert result.exit_code == 0
        assert 'Aborted' in result.output
    
    def test_cli_version_flag(self):
        """Test --version flag."""
        runner = CliRunner()
        
        result = runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert '0.1.0' in result.output
    
    def test_cli_help(self):
        """Test --help output."""
        runner = CliRunner()
        
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'Generate rules.md and skills.md' in result.output
        assert '--commit' in result.output
        assert '--interactive' in result.output
