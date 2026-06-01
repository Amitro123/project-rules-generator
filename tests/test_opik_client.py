"""Tests for generator/integrations/opik_client.py.

The Opik integration was at 23% coverage (CR §4.4). It is an optional
observability shim: it must degrade gracefully when the ``opik`` package is
absent or no API key is set, and never let a tracing failure bubble into the
main generation flow. We patch the module-level ``OPIK_AVAILABLE`` flag and
inject a fake ``Opik`` class so every branch runs without the real dependency.
"""

from unittest.mock import MagicMock, patch

import generator.integrations.opik_client as opik_mod
from generator.integrations.opik_client import OpikEvaluator


class TestInit:
    def test_disabled_when_opik_not_installed(self, monkeypatch):
        """No opik package → integration disabled regardless of key."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", False)
        ev = OpikEvaluator(api_key="secret")
        assert ev.enabled is False

    def test_disabled_when_no_api_key(self, monkeypatch):
        """opik present but no key (and none in env) → disabled."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", True)
        monkeypatch.delenv("OPIK_API_KEY", raising=False)
        ev = OpikEvaluator(api_key=None)
        assert ev.enabled is False

    def test_api_key_read_from_env(self, monkeypatch):
        """A key in OPIK_API_KEY is picked up when none is passed explicitly."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", True)
        monkeypatch.setenv("OPIK_API_KEY", "env-key")
        fake_opik = MagicMock()
        monkeypatch.setattr(opik_mod, "Opik", fake_opik, raising=False)
        ev = OpikEvaluator(api_key=None)
        assert ev.enabled is True
        assert ev.api_key == "env-key"

    def test_enabled_initializes_client(self, monkeypatch):
        """opik present + key → client constructed and integration enabled."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", True)
        fake_opik = MagicMock()
        monkeypatch.setattr(opik_mod, "Opik", fake_opik, raising=False)
        ev = OpikEvaluator(api_key="secret", project_name="proj")
        assert ev.enabled is True
        fake_opik.assert_called_once_with(api_key="secret", project_name="proj")
        assert ev.client is fake_opik.return_value

    def test_client_init_exception_disables(self, monkeypatch):
        """If constructing the Opik client raises, enabled flips back to False."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", True)
        boom = MagicMock(side_effect=RuntimeError("network down"))
        monkeypatch.setattr(opik_mod, "Opik", boom, raising=False)
        ev = OpikEvaluator(api_key="secret")
        assert ev.enabled is False


class TestTrackEvaluation:
    def _enabled_evaluator(self, monkeypatch):
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", True)
        monkeypatch.setattr(opik_mod, "Opik", MagicMock(), raising=False)
        return OpikEvaluator(api_key="secret")

    def test_noop_when_disabled(self, monkeypatch):
        """A disabled evaluator does nothing (and never touches a client)."""
        monkeypatch.setattr(opik_mod, "OPIK_AVAILABLE", False)
        ev = OpikEvaluator(api_key=None)
        # Should simply return without raising even though there is no client.
        ev.track_evaluation("content", "analysis")

    def test_logs_trace_with_output_snippet(self, monkeypatch):
        """A trace is created with the content snippet/length in its output."""
        ev = self._enabled_evaluator(monkeypatch)
        trace = MagicMock(id="t1")
        ev.client.trace.return_value = trace

        ev.track_evaluation("x" * 2000, "analysis", output_props={"k": "v"})

        ev.client.trace.assert_called_once()
        output = ev.client.trace.call_args.kwargs["output"]
        assert output["content_length"] == 2000
        assert len(output["content_snippet"]) == 1000  # truncated to first 1000
        assert output["k"] == "v"
        trace.end.assert_called_once()

    def test_metrics_logged_as_feedback_scores(self, monkeypatch):
        """Each metric becomes a feedback score on the trace."""
        ev = self._enabled_evaluator(monkeypatch)
        trace = MagicMock(id="t2")
        ev.client.trace.return_value = trace

        ev.track_evaluation("c", "patch", metrics={"score": 0.9})

        trace.log_feedback_score.assert_any_call(name="score", value=0.9)

    def test_quick_check_metadata_logged(self, monkeypatch):
        """quick_check booleans in metadata are logged as 1.0/0.0 scores."""
        ev = self._enabled_evaluator(monkeypatch)
        trace = MagicMock(id="t3")
        ev.client.trace.return_value = trace

        ev.track_evaluation("c", "patch", metadata={"quick_check": {"has_tests": True, "lint": False}})

        trace.log_feedback_score.assert_any_call(name="has_tests", value=1.0)
        trace.log_feedback_score.assert_any_call(name="lint", value=0.0)

    def test_individual_metric_failure_swallowed(self, monkeypatch):
        """A failing log_feedback_score must not abort the whole trace."""
        ev = self._enabled_evaluator(monkeypatch)
        trace = MagicMock(id="t4")
        trace.log_feedback_score.side_effect = RuntimeError("score rejected")
        ev.client.trace.return_value = trace

        # Should not raise despite the per-metric failure.
        ev.track_evaluation("c", "patch", metrics={"score": 0.5})
        trace.end.assert_called_once()

    def test_quick_check_metric_failure_swallowed(self, monkeypatch):
        """A failing quick_check feedback score is ignored, trace still ends."""
        ev = self._enabled_evaluator(monkeypatch)
        trace = MagicMock(id="t5")
        trace.log_feedback_score.side_effect = RuntimeError("score rejected")
        ev.client.trace.return_value = trace

        ev.track_evaluation("c", "patch", metadata={"quick_check": {"lint": True}})
        trace.end.assert_called_once()

    def test_trace_failure_is_swallowed(self, monkeypatch):
        """An exception from client.trace() is caught (observability is best-effort)."""
        ev = self._enabled_evaluator(monkeypatch)
        ev.client.trace.side_effect = RuntimeError("opik exploded")
        # Must not propagate.
        ev.track_evaluation("c", "analysis")


class TestDashboardUrl:
    def test_returns_static_url(self):
        ev = OpikEvaluator(api_key=None)
        assert ev.get_dashboard_url() == "https://www.comet.com/opik/dashboard"
