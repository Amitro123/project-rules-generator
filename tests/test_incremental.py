"""Tests for incremental analysis (Feature 3)."""
import json
import pytest
from pathlib import Path
from click.testing import CliRunner

from generator.incremental_analyzer import IncrementalAnalyzer
from main import main


class TestComputeProjectHash:
    """Test hash computation for project files."""

    def test_hash_returns_all_sections(self, tmp_path):
        (tmp_path / 'README.md').write_text('# Test')
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')

        hashes = analyzer.compute_project_hash()

        assert set(hashes.keys()) == {'deps', 'readme', 'source', 'tests', 'structure'}
        assert all(isinstance(v, str) for v in hashes.values())

    def test_hash_changes_when_readme_changes(self, tmp_path):
        (tmp_path / 'README.md').write_text('# Version 1')
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')
        h1 = analyzer.compute_project_hash()

        (tmp_path / 'README.md').write_text('# Version 2 — updated')
        h2 = analyzer.compute_project_hash()

        assert h1['readme'] != h2['readme']
        # Other sections unchanged
        assert h1['deps'] == h2['deps']

    def test_hash_changes_when_deps_change(self, tmp_path):
        (tmp_path / 'requirements.txt').write_text('click>=8.0')
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')
        h1 = analyzer.compute_project_hash()

        (tmp_path / 'requirements.txt').write_text('click>=8.0\nfastapi>=0.100')
        h2 = analyzer.compute_project_hash()

        assert h1['deps'] != h2['deps']

    def test_hash_changes_when_source_added(self, tmp_path):
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')
        h1 = analyzer.compute_project_hash()

        (tmp_path / 'app.py').write_text('print("hello")')
        h2 = analyzer.compute_project_hash()

        assert h1['source'] != h2['source']

    def test_hash_changes_when_tests_added(self, tmp_path):
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')
        h1 = analyzer.compute_project_hash()

        tests_dir = tmp_path / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_app.py').write_text('def test_pass(): pass')
        h2 = analyzer.compute_project_hash()

        assert h1['tests'] != h2['tests']

    def test_hash_ignores_venv(self, tmp_path):
        (tmp_path / '.venv').mkdir()
        (tmp_path / '.venv' / 'lib.py').write_text('x = 1')
        analyzer = IncrementalAnalyzer(tmp_path, tmp_path / '.clinerules')
        h1 = analyzer.compute_project_hash()

        # Adding a file inside .venv should not change source hash
        (tmp_path / '.venv' / 'more.py').write_text('y = 2')
        h2 = analyzer.compute_project_hash()

        assert h1['source'] == h2['source']


class TestCacheIO:
    """Test saving and loading hash cache."""

    def test_save_and_load(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        hashes = {'deps': 'abc', 'readme': 'def', 'source': 'ghi', 'tests': 'jkl', 'structure': 'mno'}
        analyzer.save_hash(hashes)

        loaded = analyzer.load_previous_hash()
        assert loaded == hashes

    def test_load_returns_none_when_no_cache(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        assert analyzer.load_previous_hash() is None

    def test_load_returns_none_on_corrupt_cache(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        (output_dir / '.prg-cache.json').write_text('not json!', encoding='utf-8')
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        assert analyzer.load_previous_hash() is None

    def test_cache_file_location(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        analyzer.save_hash({'deps': 'a', 'readme': 'b', 'source': 'c', 'tests': 'd', 'structure': 'e'})

        assert (output_dir / '.prg-cache.json').exists()
        data = json.loads((output_dir / '.prg-cache.json').read_text(encoding='utf-8'))
        assert data['version'] == 1
        assert 'timestamp' in data


class TestDetectChanges:
    """Test change detection logic."""

    def test_no_cache_returns_all_sections(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        changes = analyzer.detect_changes()
        assert changes == {'deps', 'readme', 'source', 'tests', 'structure'}

    def test_no_changes_returns_empty(self, tmp_path):
        (tmp_path / 'README.md').write_text('# Stable')
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        # Save current state
        analyzer.save_hash(analyzer.compute_project_hash())

        # No changes made
        changes = analyzer.detect_changes()
        assert changes == set()

    def test_detects_readme_change(self, tmp_path):
        (tmp_path / 'README.md').write_text('# V1')
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)
        analyzer.save_hash(analyzer.compute_project_hash())

        (tmp_path / 'README.md').write_text('# V2 — big update')
        changes = analyzer.detect_changes()
        assert 'readme' in changes

    def test_needs_regeneration(self, tmp_path):
        output_dir = tmp_path / '.clinerules'
        output_dir.mkdir()
        analyzer = IncrementalAnalyzer(tmp_path, output_dir)

        # No cache → needs regen
        assert analyzer.needs_regeneration() is True

        # Save hash → no changes
        analyzer.save_hash(analyzer.compute_project_hash())
        assert analyzer.needs_regeneration() is False


class TestMergeRules:
    """Test incremental merge of rules content."""

    def test_full_replace_on_major_changes(self):
        old = "# Old Rules\nold content"
        new = "# New Rules\nnew content"
        result = IncrementalAnalyzer.merge_rules(old, new, {'readme', 'deps'})
        assert result == new

    def test_skills_section_merge(self):
        old = "# Rules\nOld header\n\n# 🧠 Agent Skills\n\nOld skills"
        new = "# Rules\nNew header\n\n# 🧠 Agent Skills\n\nNew skills"
        result = IncrementalAnalyzer.merge_rules(old, new, {'source'})
        assert 'Old header' in result
        assert 'New skills' in result
        assert 'Old skills' not in result

    def test_fallback_to_full_replace(self):
        old = "no markers here"
        new = "completely new content"
        result = IncrementalAnalyzer.merge_rules(old, new, {'source'})
        assert result == new


class TestIncrementalCLI:
    """Test --incremental flag via CLI."""

    def test_incremental_flag_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        assert '--incremental' in result.output

    def test_incremental_skip_when_no_changes(self, tmp_path):
        """After first run, second run with --incremental should skip."""
        (tmp_path / 'README.md').write_text('# Test\n\nDescription.')

        runner = CliRunner()
        # First run: generates files and saves cache
        result1 = runner.invoke(main, [str(tmp_path), '--no-commit', '--verbose', '--incremental'])
        assert result1.exit_code == 0, f"Exit {result1.exit_code}: {result1.output}\n{result1.exception}"

        # Second run: no changes → skip
        result2 = runner.invoke(main, [str(tmp_path), '--no-commit', '--verbose', '--incremental'])
        assert result2.exit_code == 0
        assert 'No changes detected' in result2.output
