"""Tests for SkillTracker — score math, JSON persistence, low-scoring detection."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.skill_tracker import MIN_FEEDBACK_FOR_FLAG, SkillTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_tracker(tmp_path) -> SkillTracker:
    return SkillTracker(data_path=tmp_path / "skill-usage.json")


# ---------------------------------------------------------------------------
# record_match
# ---------------------------------------------------------------------------


class TestRecordMatch:
    def test_increments_match_count(self, tmp_path):
        t = make_tracker(tmp_path)
        t.record_match("my-skill")
        t.record_match("my-skill")
        assert t.get_stats("my-skill")["match_count"] == 2

    def test_updates_last_used(self, tmp_path):
        t = make_tracker(tmp_path)
        t.record_match("my-skill")
        assert t.get_stats("my-skill")["last_used"] is not None

    def test_unknown_skill_starts_at_zero(self, tmp_path):
        t = make_tracker(tmp_path)
        assert t.get_stats("nonexistent") == {}


# ---------------------------------------------------------------------------
# record_feedback + score
# ---------------------------------------------------------------------------


class TestRecordFeedback:
    def test_useful_vote_increases_score(self, tmp_path):
        t = make_tracker(tmp_path)
        score = t.record_feedback("skill-a", useful=True)
        assert score == 1.0

    def test_not_useful_vote_decreases_score(self, tmp_path):
        t = make_tracker(tmp_path)
        t.record_feedback("skill-a", useful=False)
        score = t.record_feedback("skill-a", useful=False)
        assert score == 0.0

    def test_mixed_votes_average_correctly(self, tmp_path):
        t = make_tracker(tmp_path)
        t.record_feedback("skill-a", useful=True)
        t.record_feedback("skill-a", useful=True)
        score = t.record_feedback("skill-a", useful=False)
        assert abs(score - 2 / 3) < 1e-9

    def test_default_score_before_any_feedback(self, tmp_path):
        t = make_tracker(tmp_path)
        assert t.get_score("new-skill") == 0.5

    def test_get_score_reflects_latest_feedback(self, tmp_path):
        t = make_tracker(tmp_path)
        t.record_feedback("skill-b", useful=True)
        t.record_feedback("skill-b", useful=False)
        assert t.get_score("skill-b") == 0.5


# ---------------------------------------------------------------------------
# get_low_scoring
# ---------------------------------------------------------------------------


class TestGetLowScoring:
    def test_skill_below_threshold_with_enough_votes_is_flagged(self, tmp_path):
        t = make_tracker(tmp_path)
        for _ in range(MIN_FEEDBACK_FOR_FLAG):
            t.record_feedback("bad-skill", useful=False)
        low = t.get_low_scoring(threshold=0.3)
        assert "bad-skill" in low

    def test_skill_below_threshold_with_too_few_votes_not_flagged(self, tmp_path):
        t = make_tracker(tmp_path)
        # Only 1 vote — below MIN_FEEDBACK_FOR_FLAG
        t.record_feedback("maybe-bad", useful=False)
        low = t.get_low_scoring(threshold=0.3)
        assert "maybe-bad" not in low

    def test_high_scoring_skill_not_flagged(self, tmp_path):
        t = make_tracker(tmp_path)
        for _ in range(MIN_FEEDBACK_FOR_FLAG):
            t.record_feedback("good-skill", useful=True)
        low = t.get_low_scoring(threshold=0.3)
        assert "good-skill" not in low

    def test_returns_sorted_list(self, tmp_path):
        t = make_tracker(tmp_path)
        for name in ["z-skill", "a-skill", "m-skill"]:
            for _ in range(MIN_FEEDBACK_FOR_FLAG):
                t.record_feedback(name, useful=False)
        low = t.get_low_scoring()
        assert low == sorted(low)

    def test_empty_when_no_data(self, tmp_path):
        t = make_tracker(tmp_path)
        assert t.get_low_scoring() == []


# ---------------------------------------------------------------------------
# JSON persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_data_survives_reload(self, tmp_path):
        path = tmp_path / "skill-usage.json"
        t1 = SkillTracker(data_path=path)
        t1.record_match("skill-x")
        t1.record_feedback("skill-x", useful=True)

        t2 = SkillTracker(data_path=path)
        stats = t2.get_stats("skill-x")
        assert stats["match_count"] == 1
        assert stats["useful_count"] == 1
        assert stats["score"] == 1.0

    def test_creates_parent_dir_if_missing(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "usage.json"
        t = SkillTracker(data_path=path)
        t.record_match("x")
        assert path.exists()

    def test_corrupt_json_does_not_crash(self, tmp_path):
        path = tmp_path / "skill-usage.json"
        path.write_text("not valid json", encoding="utf-8")
        t = SkillTracker(data_path=path)  # should not raise
        assert t.get_score("anything") == 0.5

    def test_written_file_is_valid_json(self, tmp_path):
        path = tmp_path / "skill-usage.json"
        t = SkillTracker(data_path=path)
        t.record_match("skill-y")
        data = json.loads(path.read_text())
        assert "skill-y" in data


# ---------------------------------------------------------------------------
# CLI — prg skills feedback and prg skills stale
# ---------------------------------------------------------------------------


class TestFeedbackCommand:
    def test_feedback_useful(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from cli.skills_cmd import skills_feedback

        data_path = tmp_path / "usage.json"
        monkeypatch.setattr("generator.skill_tracker._DEFAULT_PATH", data_path)

        runner = CliRunner()
        result = runner.invoke(skills_feedback, ["my-skill", "--useful"])
        assert result.exit_code == 0
        assert "useful" in result.output
        assert "100%" in result.output

    def test_feedback_not_useful(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from cli.skills_cmd import skills_feedback

        data_path = tmp_path / "usage.json"
        monkeypatch.setattr("generator.skill_tracker._DEFAULT_PATH", data_path)

        runner = CliRunner()
        result = runner.invoke(skills_feedback, ["my-skill", "--not-useful"])
        assert result.exit_code == 0
        assert "not useful" in result.output

    def test_feedback_requires_flag(self):
        from click.testing import CliRunner

        from cli.skills_cmd import skills_feedback

        runner = CliRunner()
        result = runner.invoke(skills_feedback, ["my-skill"])
        assert result.exit_code != 0


class TestStaleCommand:
    def test_stale_shows_low_scoring_skills(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from cli.skills_cmd import skills_stale
        from generator.skill_tracker import SkillTracker

        data_path = tmp_path / "usage.json"
        monkeypatch.setattr("generator.skill_tracker._DEFAULT_PATH", data_path)

        # Seed a low-scoring skill with enough votes
        t = SkillTracker(data_path=data_path)
        for _ in range(MIN_FEEDBACK_FOR_FLAG):
            t.record_feedback("bad-skill", useful=False)

        runner = CliRunner()
        result = runner.invoke(skills_stale, [])
        assert result.exit_code == 0
        assert "bad-skill" in result.output
        assert "prg analyze" in result.output

    def test_stale_empty_message_when_no_low_skills(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from cli.skills_cmd import skills_stale

        data_path = tmp_path / "usage.json"
        monkeypatch.setattr("generator.skill_tracker._DEFAULT_PATH", data_path)

        runner = CliRunner()
        result = runner.invoke(skills_stale, [])
        assert result.exit_code == 0
        assert "No skills" in result.output
