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

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPIK_API_KEY")
        self.enabled = OPIK_AVAILABLE and bool(self.api_key)

        if not OPIK_AVAILABLE:
            logger.debug("Opik not installed. Skipping Opik initialization.")
        elif not self.enabled:
            logger.debug("OPIK_API_KEY not found. Opik integration disabled.")
        else:
            try:
                # Initialize Opik client
                self.client = Opik(api_key=self.api_key)
                logger.info("Opik integration initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize Opik client: {e}")
                self.enabled = False

    def track_evaluation(
        self, content: str, task_type: str, metadata: Dict[str, Any] = None
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
            trace = self.client.trace(
                name=trace_name,
                input={"metadata": metadata or {}, "task": task_type},
                output={
                    "content_snippet": content[:1000],  # Log first 1000 chars
                    "content_length": len(content),
                },
            )

            # Log any metrics we have locally (e.g. from quick check)
            if metadata and "quick_check" in metadata:
                for k, v in metadata["quick_check"].items():
                    trace.log_metric(k, 1 if v else 0)

            trace.end()
            logger.debug(f"Logged Opik trace: {trace.id}")

        except Exception as e:
            logger.warning(f"Failed to log to Opik: {e}")

    def get_dashboard_url(self) -> str:
        """Return the URL to the Opik dashboard."""
        return "https://www.comet.com/opik/dashboard"
