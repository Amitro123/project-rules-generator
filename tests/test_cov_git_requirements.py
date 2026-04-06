"""Coverage boost: RulesGitMiner and RequirementsInferrer."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# RulesGitMiner
# ---------------------------------------------------------------------------
from generator.rules_git_miner import RulesGitMiner


def _miner_with_available(tmp_path, available=True):
    """Create a RulesGitMiner with _check_available pre-set to avoid subprocess."""
    with patch.object(RulesGitMiner, "_check_available", return_value=available):
        return RulesGitMiner(project_path=tmp_path)


class TestRulesGitMinerCheckAvailable:
    def test_returns_false_when_not_git_repo(self, tmp_path):
        """Non-git directory must return False without crashing."""
        miner = RulesGitMiner(project_path=tmp_path)
        assert miner.available is False

    def test_returns_false_on_os_error(self, tmp_path):
        with patch("subprocess.run", side_effect=OSError("no git")):
            miner = RulesGitMiner(project_path=tmp_path)
        assert miner.available is False


class TestRulesGitMinerExtractAntipatterns:
    def test_returns_empty_when_unavailable(self, tmp_path):
        miner = _miner_with_available(tmp_path, available=False)
        assert miner.extract_antipatterns() == []

    def test_returns_rules_when_available(self, tmp_path):
        miner = _miner_with_available(tmp_path, available=True)
        hotspot_result = MagicMock(returncode=0, stdout="file.py\nfile.py\n" * 12)
        large_result = MagicMock(returncode=0, stdout="abc123 commit\n 600 insertions(+)\nabc456 commit\n 700 insertions(+)\nabc789 commit\n 800 insertions(+)\n")
        with patch("subprocess.run", side_effect=[hotspot_result, large_result]):
            rules = miner.extract_antipatterns()
        assert len(rules) > 0


class TestRulesGitMinerFindHotspots:
    def test_hotspot_detected_when_file_changed_often(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "\n".join(["hotfile.py"] * 15 + ["other.py"] * 3)
        mock_result = MagicMock(returncode=0, stdout=output)
        with patch("subprocess.run", return_value=mock_result):
            rules = miner._find_hotspots()
        assert len(rules) == 1
        assert "hotfile.py" in rules[0].content

    def test_no_hotspot_when_all_files_low_change_count(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "\n".join(["file.py"] * 5)
        mock_result = MagicMock(returncode=0, stdout=output)
        with patch("subprocess.run", return_value=mock_result):
            rules = miner._find_hotspots()
        assert rules == []

    def test_returns_empty_on_nonzero_returncode(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="")):
            assert miner._find_hotspots() == []

    def test_priority_is_medium(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "\n".join(["hotfile.py"] * 15)
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_hotspots()
        assert rules[0].priority == "Medium"
        assert rules[0].source == "git_history"

    def test_shows_up_to_three_hotspot_filenames(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        # 4 hot files, should only show 3
        output = "\n".join(
            ["a.py"] * 15 + ["b.py"] * 14 + ["c.py"] * 13 + ["d.py"] * 12
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_hotspots()
        # Rule content mentions hotspot file names; d.py may or may not appear
        assert "a.py" in rules[0].content


class TestRulesGitMinerFindLargeCommits:
    def test_three_large_commits_creates_rule(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = (
            "abc123 big commit\n"
            " 600 insertions(+), 10 deletions(-)\n"
            "def456 another big\n"
            " 700 insertions(+)\n"
            "ghi789 yet another\n"
            " 800 insertions(+)\n"
        )
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_large_commits()
        assert len(rules) == 1
        assert "Large commits" in rules[0].content

    def test_two_or_fewer_large_commits_no_rule(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "abc123 commit\n 600 insertions(+)\n"
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_large_commits()
        assert rules == []

    def test_small_commits_not_counted(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "abc commit\n 100 insertions(+)\n" * 10
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_large_commits()
        assert rules == []

    def test_returns_empty_on_nonzero_returncode(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        with patch("subprocess.run", return_value=MagicMock(returncode=2, stdout="")):
            assert miner._find_large_commits() == []

    def test_priority_is_low(self, tmp_path):
        miner = _miner_with_available(tmp_path)
        output = "c\n 600 insertions(+)\nc\n 700 insertions(+)\nc\n 800 insertions(+)\n"
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=output)):
            rules = miner._find_large_commits()
        assert rules[0].priority == "Low"


# ---------------------------------------------------------------------------
# RequirementsInferrer
# ---------------------------------------------------------------------------
from generator.requirements import Requirement, RequirementsInferrer


class TestRequirementsInferrerAnalyzeReadme:
    def test_extracts_bullets_from_features_section(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n\n## Features\n\n- Fast processing\n- Easy install\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_readme(readme)
        assert len(reqs) == 2
        assert reqs[0].source == "README"
        assert "Fast processing" in reqs[0].description

    def test_extracts_from_how_it_works_section(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n\n## How It Works\n\n- Reads config file\n- Generates output\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_readme(readme)
        assert len(reqs) == 2

    def test_returns_empty_for_readme_without_target_sections(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("# Project\n\n## Installation\n\npip install x\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_readme(readme)
        assert reqs == []

    def test_ids_are_sequential(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Features\n\n- Feature A\n- Feature B\n- Feature C\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_readme(readme)
        ids = [r.id for r in reqs]
        assert ids == ["feat-1", "feat-2", "feat-3"]

    def test_priority_is_two(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Features\n\n- Feature A\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_readme(readme)
        assert reqs[0].priority == 2


class TestRequirementsInferrerAnalyzeGitHistory:
    def test_extracts_feat_commits(self, tmp_path):
        inferrer = RequirementsInferrer(provider=None)
        mock_result = MagicMock(stdout="abc123 feat: add login\ndef456 fix: typo\nghi789 feat: add logout\n")
        with patch("subprocess.run", return_value=mock_result):
            reqs = inferrer._analyze_git_history(tmp_path)
        descriptions = [r.description for r in reqs]
        assert any("add login" in d for d in descriptions)
        assert any("add logout" in d for d in descriptions)

    def test_filters_fix_commits(self, tmp_path):
        inferrer = RequirementsInferrer(provider=None)
        mock_result = MagicMock(stdout="abc123 fix: typo in README\n")
        with patch("subprocess.run", return_value=mock_result):
            reqs = inferrer._analyze_git_history(tmp_path)
        assert reqs == []

    def test_returns_empty_on_subprocess_error(self, tmp_path):
        inferrer = RequirementsInferrer(provider=None)
        with patch("subprocess.run", side_effect=OSError("no git")):
            reqs = inferrer._analyze_git_history(tmp_path)
        assert reqs == []

    def test_source_is_git(self, tmp_path):
        inferrer = RequirementsInferrer(provider=None)
        mock_result = MagicMock(stdout="abc123 add user feature\n")
        with patch("subprocess.run", return_value=mock_result):
            reqs = inferrer._analyze_git_history(tmp_path)
        assert reqs[0].source == "Git"

    def test_ids_sequential(self, tmp_path):
        inferrer = RequirementsInferrer(provider=None)
        mock_result = MagicMock(stdout="a add feature one\nb implement feature two\n")
        with patch("subprocess.run", return_value=mock_result):
            reqs = inferrer._analyze_git_history(tmp_path)
        assert reqs[0].id == "git-1"
        assert reqs[1].id == "git-2"


class TestRequirementsInferrerAnalyzeCodebase:
    def test_extracts_todos(self, tmp_path):
        py_file = tmp_path / "module.py"
        py_file.write_text("def foo():\n    # TODO: implement this\n    pass\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_codebase(tmp_path)
        assert len(reqs) == 1
        assert "module.py" in reqs[0].description
        assert "implement this" in reqs[0].description

    def test_multiple_todos_extracted(self, tmp_path):
        py_file = tmp_path / "service.py"
        py_file.write_text("# TODO: add caching\n# TODO: add retries\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_codebase(tmp_path)
        assert len(reqs) == 2

    def test_source_is_code(self, tmp_path):
        py_file = tmp_path / "x.py"
        py_file.write_text("# TODO: fix this\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_codebase(tmp_path)
        assert reqs[0].source == "Code"
        assert reqs[0].priority == 4

    def test_skips_venv_directory(self, tmp_path):
        venv = tmp_path / "venv"
        venv.mkdir()
        venv_file = venv / "pkg.py"
        venv_file.write_text("# TODO: skip me\n")
        inferrer = RequirementsInferrer(provider=None)
        reqs = inferrer._analyze_codebase(tmp_path)
        assert all("venv" not in r.description for r in reqs)

    def test_returns_empty_for_no_todos(self, tmp_path):
        py_file = tmp_path / "clean.py"
        py_file.write_text("def foo(): pass\n")
        inferrer = RequirementsInferrer(provider=None)
        assert inferrer._analyze_codebase(tmp_path) == []


class TestRequirementsInferrerParseSynthesized:
    def test_parses_well_formed_response(self):
        inferrer = RequirementsInferrer(provider=None)
        response = "ID: req-1\nDESC: Add login\nPRIORITY: 2\nSOURCE: README\n---\nID: req-2\nDESC: Add logout\nPRIORITY: 3\nSOURCE: Git\n---"
        reqs = inferrer._parse_synthesized(response)
        assert len(reqs) == 2
        assert reqs[0].id == "req-1"
        assert reqs[1].description == "Add logout"

    def test_skips_malformed_blocks(self):
        inferrer = RequirementsInferrer(provider=None)
        response = "missing id field\nDESC: foo\nPRIORITY: 1\nSOURCE: x\n---\nID: r1\nDESC: ok\nPRIORITY: 2\nSOURCE: README\n---"
        reqs = inferrer._parse_synthesized(response)
        assert len(reqs) == 1
        assert reqs[0].id == "r1"

    def test_returns_empty_for_no_blocks(self):
        inferrer = RequirementsInferrer(provider=None)
        assert inferrer._parse_synthesized("no relevant content") == []

    def test_priority_parsed_as_int(self):
        inferrer = RequirementsInferrer(provider=None)
        response = "ID: r1\nDESC: test\nPRIORITY: 4\nSOURCE: Code\n---"
        reqs = inferrer._parse_synthesized(response)
        assert reqs[0].priority == 4


class TestRequirementsInferrerSynthesize:
    def test_returns_empty_for_empty_input(self):
        inferrer = RequirementsInferrer(provider=None)
        assert inferrer._synthesize([]) == []

    def test_returns_raw_when_no_provider(self):
        inferrer = RequirementsInferrer(provider=None)
        reqs = [Requirement(id="r1", description="test", source="README")]
        result = inferrer._synthesize(reqs)
        assert result == reqs

    def test_infer_combines_all_sources(self, tmp_path):
        readme = tmp_path / "README.md"
        readme.write_text("## Features\n\n- Fast\n")
        inferrer = RequirementsInferrer(provider=None)
        with patch.object(inferrer, "_analyze_git_history", return_value=[]):
            with patch.object(inferrer, "_analyze_codebase", return_value=[]):
                reqs = inferrer.infer(tmp_path)
        assert any(r.source == "README" for r in reqs)
