import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    import opik
    from opik import Opik

    OPIK_AVAILABLE = True
except ImportError:
    OPIK_AVAILABLE = False


class OpikEvaluator:
    """Integration with Comet Opik for LLM evaluation and tracking."""

    def __init__(self, api_key: Optional[str] = None, project_name: str = "project-rules-generator"):
        self.api_key = api_key or os.getenv("OPIK_API_KEY")
        self.project_name = project_name
        self.enabled = OPIK_AVAILABLE and bool(self.api_key)

        if not OPIK_AVAILABLE:
            logger.debug("Opik not installed. Skipping Opik initialization.")
        elif not self.enabled:
            logger.debug("OPIK_API_KEY not found. Opik integration disabled.")
        else:
            try:
                # Initialize Opik client
                self.client = Opik(api_key=self.api_key, project_name=self.project_name)
                logger.info(f"Opik integration initialized for project: {self.project_name}")
            except Exception as e:  # noqa: BLE001 — observability must never block main flow
                logger.warning(f"Failed to initialize Opik client: {e}")
                self.enabled = False

    def track_evaluation(
        self,
        content: str,
        task_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, float]] = None,
        output_props: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log content generation to Opik for observability and evaluation.
        """
        if not self.enabled:
            return

        try:
            # Log a trace for this generation
            # We use a naming convention: rules-<type> (e.g., rules-analysis, rules-patch)
            trace_name = f"rules-{task_type}"

            # Prepare input/output data
            # Since we are evaluating the *result*, the "input" to the evaluation is the generated content
            # But usually in a trace, input is the prompt and output is the generation.
            # Here we might be just logging the artifact itself.

            # Using basic trace logging
            # Prepare output dictionary
            output_data = {
                "content_snippet": content[:1000],  # Log first 1000 chars
                "content_length": len(content),
            }
            if output_props:
                output_data.update(output_props)

            # Since log_metric is not available on this Trace object, we include metrics in output
            # Removed: if metrics: output_data.update(metrics)

            # Using basic trace logging
            trace = self.client.trace(
                name=trace_name,
                input={"metadata": metadata or {}, "task": task_type},
                output=output_data,
            )

            # Log feedback scores (metrics)
            if metrics:
                for k, v in metrics.items():
                    # log_feedback_score(name, value, category_name=None, reason=None)
                    try:
                        trace.log_feedback_score(name=k, value=float(v))
                    except Exception:  # noqa: BLE001 — observability must never block main flow
                        pass  # Ignore individual metric failures

            # Log local check metrics as feedback scores too
            if metadata and "quick_check" in metadata:
                for k, v in metadata["quick_check"].items():
                    try:
                        trace.log_feedback_score(name=k, value=1.0 if v else 0.0)
                    except Exception:  # noqa: BLE001 — observability must never block main flow
                        pass

            trace.end()
            logger.debug(f"Logged Opik trace: {trace.id}")

        except Exception as e:  # noqa: BLE001 — observability must never block main flow
            logger.warning(f"Failed to log to Opik: {e}")

    def get_dashboard_url(self) -> str:
        """Return the URL to the Opik dashboard."""
        return "https://www.comet.com/opik/dashboard"
