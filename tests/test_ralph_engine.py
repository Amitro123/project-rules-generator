"""Tests for generator/ralph_engine.py — RalphEngine core."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from generator.ralph_engine import (
    FeatureState,
    RalphEngine,
    _load_tasks,
    _pending_tasks,
    _save_tasks,
    next_feature_id,
    slugify,
)

# ---------------------------------------------------------------------------
# Helpers & fixtures
# ---------------------------------------------------------------------------


def _make_state(feature_dir: Path, **overrides: object) -> FeatureState:
    """Write a STATE.json and return the FeatureState."""
    defaults: dict = dict(
        feature_id="FEATURE-001",
        task="Add loading states",
        branch_name="ralph/FEATURE-001-add-loading-states",
        status="planning_complete",
        iteration=0,
        tasks_total=3,
        tasks_complete=0,
        max_iterations=20,
        last_review_score=None,
        test_pass_rate=None,
        exit_condition=None,
        human_feedback=None,
        consecutive_test_failures=0,
    )
    defaults.update(overrides)
    state = FeatureState(**defaults)
    state.save(feature_dir / "STATE.json")
    return state


def _make_tasks(tasks_yaml: Path, tasks: list[dict]) -> None:
    _save_tasks(tasks_yaml, tasks)


def _make_engine(tmp_path: Path, **state_overrides) -> RalphEngine:
    feature_dir = tmp_path / "features" / "FEATURE-001"
    feature_dir.mkdir(parents=True)
    _make_state(feature_dir, **state_overrides)
    return RalphEngine(
        feature_id="FEATURE-001",
        project_path=tmp_path,
        provider="groq",
        verbose=False,
    )


# ---------------------------------------------------------------------------
# FeatureState tests
# ---------------------------------------------------------------------------


def test_feature_state_load_save(tmp_path):
    """FeatureState saves and loads correctly from STATE.json."""
    state_path = tmp_path / "STATE.json"
    state = FeatureState(
        feature_id="FEATURE-001",
        task="Add loading states",
        branch_name="ralph/FEATURE-001-add-loading-states",
        iteration=3,
        tasks_total=5,
        tasks_complete=2,
        last_review_score=82,
    )
    state.save(state_path)
    loaded = FeatureState.load(state_path)
    assert loaded.feature_id == "FEATURE-001"
    assert loaded.iteration == 3
    assert loaded.tasks_complete == 2
    assert loaded.last_review_score == 82


def test_feature_state_load_ignores_unknown_keys(tmp_path):
    """FeatureState.load silently ignores extra JSON keys (forward compat)."""
    state_path = tmp_path / "STATE.json"
    data = {
        "feature_id": "FEATURE-002",
        "task": "x",
        "branch_name": "ralph/FEATURE-002-x",
        "future_field": "ignored",
    }
    state_path.write_text(json.dumps(data), encoding="utf-8")
    loaded = FeatureState.load(state_path)
    assert loaded.feature_id == "FEATURE-002"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


def test_next_feature_id_empty_dir(tmp_path):
    """Returns FEATURE-001 when no features exist."""
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    assert next_feature_id(features_dir) == "FEATURE-001"


def test_next_feature_id_increments(tmp_path):
    """Returns next available ID."""
    features_dir = tmp_path / "features"
    (features_dir / "FEATURE-001").mkdir(parents=True)
    (features_dir / "FEATURE-002").mkdir(parents=True)
    assert next_feature_id(features_dir) == "FEATURE-003"


def test_next_feature_id_no_dir(tmp_path):
    """Returns FEATURE-001 when features/ doesn't exist yet."""
    assert next_feature_id(tmp_path / "features") == "FEATURE-001"


def test_slugify_basic():
    assert slugify("Add loading states to forms") == "add-loading-states-to-forms"


def test_slugify_truncates():
    long = "a" * 100
    assert len(slugify(long)) <= 40


def test_slugify_special_chars():
    assert slugify("Fix UI: add 'spinner' & loader?") == "fix-ui-add-spinner-loader"


# ---------------------------------------------------------------------------
# RalphEngine init & state tests
# ---------------------------------------------------------------------------


def test_ralph_engine_init_loads_state(tmp_path):
    """RalphEngine loads STATE.json on init."""
    engine = _make_engine(tmp_path, iteration=5)
    assert engine.state.iteration == 5
    assert engine.state.feature_id == "FEATURE-001"


def test_ralph_engine_init_missing_state(tmp_path):
    """RalphEngine returns default state when STATE.json is absent."""
    feature_dir = tmp_path / "features" / "FEATURE-001"
    feature_dir.mkdir(parents=True)
    engine = RalphEngine(feature_id="FEATURE-001", project_path=tmp_path, verbose=False)
    assert engine.state.task == "(unknown)"
    assert engine.state.status == "planning_complete"


def test_save_state_creates_file(tmp_path):
    """save_state writes STATE.json."""
    engine = _make_engine(tmp_path)
    engine.state.iteration = 7
    engine.save_state()
    loaded = FeatureState.load(engine.state_path)
    assert loaded.iteration == 7


# ---------------------------------------------------------------------------
# review_score_from_verdict tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "verdict, expected",
    [
        ("Pass", 100),
        ("pass", 100),
        ("Pass — quality is great", 100),
        ("Needs Revision", 65),
        ("needs revision", 65),
        ("Major Issues", 40),
        ("major issues found", 40),
        ("Something Else", 65),
    ],
)
def test_review_score_from_verdict(verdict, expected):
    assert RalphEngine.review_score_from_verdict(verdict) == expected


# ---------------------------------------------------------------------------
# should_exit tests
# ---------------------------------------------------------------------------


def test_should_exit_max_iterations(tmp_path):
    engine = _make_engine(tmp_path, iteration=20, max_iterations=20)
    assert engine.should_exit() is True


def test_should_exit_not_yet(tmp_path):
    engine = _make_engine(tmp_path, iteration=3, max_iterations=20, tasks_total=5)
    tasks_yaml = engine.feature_dir / "TASKS.yaml"
    _make_tasks(tasks_yaml, [{"title": "T1", "status": "pending"}])
    assert engine.should_exit() is False


def test_should_exit_status_success(tmp_path):
    engine = _make_engine(tmp_path, status="success")
    assert engine.should_exit() is True


def test_should_exit_all_tasks_done(tmp_path):
    engine = _make_engine(tmp_path, iteration=1, max_iterations=20)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "done"}])
    assert engine.should_exit() is True


def test_should_exit_no_tasks_file(tmp_path):
    """With no TASKS.yaml (0 tasks), tasks check is skipped — exit only on max_iter or status."""
    engine = _make_engine(tmp_path, iteration=1, max_iterations=20)
    assert engine.should_exit() is False  # 0 total tasks → don't exit early via task check


# ---------------------------------------------------------------------------
# verify_success tests
# ---------------------------------------------------------------------------


def test_verify_success_all_pass(tmp_path):
    engine = _make_engine(tmp_path, last_review_score=90)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "done"}])
    engine._run_tests = MagicMock(return_value=(True, "all passed"))

    assert engine.verify_success() is True


def test_verify_success_low_review(tmp_path):
    engine = _make_engine(tmp_path, last_review_score=70)
    assert engine.verify_success() is False


def test_verify_success_pending_tasks(tmp_path):
    engine = _make_engine(tmp_path, last_review_score=90)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])
    engine._run_tests = MagicMock(return_value=(True, ""))
    assert engine.verify_success() is False


def test_verify_success_tests_fail(tmp_path):
    engine = _make_engine(tmp_path, last_review_score=90)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "done"}])
    engine._run_tests = MagicMock(return_value=(False, "FAIL"))
    assert engine.verify_success() is False


# ---------------------------------------------------------------------------
# Emergency stop behaviour
# ---------------------------------------------------------------------------


def test_emergency_stop_on_low_review_score(tmp_path):
    """execute_iteration should set status=stopped when score < 60."""
    engine = _make_engine(tmp_path, iteration=0)
    _make_tasks(engine.tasks_yaml, [{"title": "Add button", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=40)  # below threshold
    engine._run_tests = MagicMock(return_value=(True, ""))

    engine.state.iteration = 1
    engine.execute_iteration()

    assert engine.state.status == "stopped"
    assert "40" in (engine.state.exit_condition or "")


def test_test_fail_3x_triggers_stop(tmp_path):
    """Three consecutive test failures should set status=stopped."""
    engine = _make_engine(tmp_path, iteration=0, consecutive_test_failures=2)
    _make_tasks(engine.tasks_yaml, [{"title": "Task X", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=80)
    engine._run_tests = MagicMock(return_value=(False, "test output"))

    engine.state.iteration = 3
    engine.execute_iteration()

    assert engine.state.status == "stopped"
    assert engine.state.exit_condition == "test_fail_3x"


# ---------------------------------------------------------------------------
# Task tracking helpers
# ---------------------------------------------------------------------------


def test_mark_task_complete(tmp_path):
    engine = _make_engine(tmp_path)
    _make_tasks(
        engine.tasks_yaml,
        [
            {"title": "Task A", "status": "pending"},
            {"title": "Task B", "status": "pending"},
        ],
    )
    engine._mark_task_complete("Task A")
    tasks = _load_tasks(engine.tasks_yaml)
    statuses = {t["title"]: t["status"] for t in tasks}
    assert statuses["Task A"] == "done"
    assert statuses["Task B"] == "pending"


def test_next_task_title_returns_first_pending(tmp_path):
    engine = _make_engine(tmp_path)
    _make_tasks(
        engine.tasks_yaml,
        [
            {"title": "Done Task", "status": "done"},
            {"title": "Next Task", "status": "pending"},
        ],
    )
    assert engine._next_task_title() == "Next Task"


def test_next_task_title_none_when_all_done(tmp_path):
    engine = _make_engine(tmp_path)
    _make_tasks(engine.tasks_yaml, [{"title": "T", "status": "done"}])
    assert engine._next_task_title() is None


# ---------------------------------------------------------------------------
# build_context smoke test
# ---------------------------------------------------------------------------


def test_build_context_returns_string(tmp_path):
    engine = _make_engine(tmp_path)
    # Minimal setup
    (tmp_path / ".clinerules").mkdir()
    (tmp_path / ".clinerules" / "rules.md").write_text("# Rules\n- Do good.", encoding="utf-8")
    engine.plan_md.write_text("# Plan\n", encoding="utf-8")
    ctx = engine.build_context()
    assert "PROJECT RULES" in ctx
    assert "FEATURE PLAN" in ctx
    assert "CURRENT TASK" in ctx


# ---------------------------------------------------------------------------
# run_loop integration (mocked)
# ---------------------------------------------------------------------------


def test_run_loop_exits_on_max_iterations(tmp_path):
    engine = _make_engine(tmp_path, max_iterations=2)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    engine.execute_iteration = MagicMock()
    engine.verify_success = MagicMock(return_value=False)
    engine._create_pr = MagicMock()

    engine.run_loop(max_iterations=2)

    assert engine.execute_iteration.call_count <= 2
    assert engine.state.status in ("max_iterations", "stopped", "running")


def test_run_loop_exits_on_verify_success(tmp_path):
    engine = _make_engine(tmp_path, max_iterations=20, last_review_score=90)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    call_count = 0

    def fake_execute():
        nonlocal call_count
        call_count += 1
        # Mark task done on first iteration so verify_success can pass
        _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "done"}])
        engine.state.last_review_score = 90

    engine.execute_iteration = fake_execute
    engine._run_tests = MagicMock(return_value=(True, ""))
    engine._create_pr = MagicMock()

    engine.run_loop()

    assert engine.state.status == "success"
    engine._create_pr.assert_called_once()


# ---------------------------------------------------------------------------
# Characterization tests — execute_iteration() step coverage
# (These lock down each step's contract so refactoring stays safe.)
# ---------------------------------------------------------------------------


def test_step1_no_pending_tasks_marks_complete_and_returns(tmp_path):
    """Step 1: when no pending tasks exist, tasks_complete is updated and
    execute_iteration returns without calling agent or commit."""
    engine = _make_engine(tmp_path, tasks_total=1, tasks_complete=0)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "done"}])

    engine._agent_execute = MagicMock()
    engine._git_commit = MagicMock()
    engine.state.iteration = 1

    engine.execute_iteration()

    engine._agent_execute.assert_not_called()
    engine._git_commit.assert_not_called()
    assert engine.state.tasks_complete == 1


def test_step3_security_error_stops_loop(tmp_path):
    """Step 3: SecurityError from _agent_execute sets status=stopped with
    security_violation exit_condition and returns without committing."""
    from generator.exceptions import SecurityError

    engine = _make_engine(tmp_path)
    _make_tasks(engine.tasks_yaml, [{"title": "Malicious task", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(side_effect=SecurityError("path traversal"))
    engine._git_commit = MagicMock()
    engine.state.iteration = 1

    engine.execute_iteration()

    assert engine.state.status == "stopped"
    assert "security_violation" in (engine.state.exit_condition or "")
    engine._git_commit.assert_not_called()


def test_step4_agent_fail_1x_increments_counter(tmp_path):
    """Step 4: one empty agent response increments consecutive_agent_failures
    but does NOT stop the loop."""
    engine = _make_engine(tmp_path, consecutive_agent_failures=0)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=80)
    engine._run_tests = MagicMock(return_value=(True, ""))
    engine.state.iteration = 1

    engine.execute_iteration()

    assert engine.state.consecutive_agent_failures == 1
    assert engine.state.status != "stopped"


def test_step4_agent_fail_3x_stops_loop(tmp_path):
    """Step 4: three consecutive empty agent responses sets status=stopped
    with agent_fail_3x exit_condition."""
    engine = _make_engine(tmp_path, consecutive_agent_failures=2)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={})
    engine._git_commit = MagicMock()
    engine.state.iteration = 3

    engine.execute_iteration()

    assert engine.state.status == "stopped"
    assert engine.state.exit_condition == "agent_fail_3x"
    engine._git_commit.assert_not_called()


def test_step4_successful_changes_resets_failure_counter(tmp_path):
    """Step 4: a non-empty changes dict resets consecutive_agent_failures to 0."""
    engine = _make_engine(tmp_path, consecutive_agent_failures=2)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={"app.py": "content"})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=80)
    engine._run_tests = MagicMock(return_value=(True, ""))
    engine.state.iteration = 1

    engine.execute_iteration()

    assert engine.state.consecutive_agent_failures == 0


def test_step5_review_score_below_60_emergency_stop(tmp_path):
    """Step 5 (existing): review score < 60 → emergency stop. Characterization
    copy to confirm behavior survives the refactor."""
    engine = _make_engine(tmp_path)
    _make_tasks(engine.tasks_yaml, [{"title": "T1", "status": "pending"}])

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={"f.py": "x"})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=55)
    engine._run_tests = MagicMock(return_value=(True, ""))
    engine.state.iteration = 1

    engine.execute_iteration()

    assert engine.state.status == "stopped"
    assert "55" in (engine.state.exit_condition or "")


def test_step6_task_marked_complete_when_tests_pass_and_score_ok(tmp_path):
    """Step 6: when tests pass and review score >= 70, current task is marked done."""
    engine = _make_engine(tmp_path, tasks_total=2, tasks_complete=0)
    _make_tasks(
        engine.tasks_yaml,
        [{"title": "T1", "status": "pending"}, {"title": "T2", "status": "pending"}],
    )

    engine._match_skill = MagicMock(return_value=None)
    engine._agent_execute = MagicMock(return_value={"f.py": "x"})
    engine._git_commit = MagicMock()
    engine._run_self_review = MagicMock(return_value=80)
    engine._run_tests = MagicMock(return_value=(True, ""))
    engine.state.iteration = 1

    engine.execute_iteration()

    from generator.ralph_engine import _load_tasks

    tasks = _load_tasks(engine.tasks_yaml)
    statuses = {t["title"]: t["status"] for t in tasks}
    assert statuses["T1"] == "done"
    assert statuses["T2"] == "pending"
