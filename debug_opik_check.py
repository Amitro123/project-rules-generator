import logging

from generator.integrations.opik_client import OpikEvaluator

# Configure logging to see output
logging.basicConfig(level=logging.DEBUG)

print("Initializing Opik Evaluator...")
# Pass a dummy key if env var not set, just to test initialization path
# But OpikEvaluator checks env var if key not passed.
# We'll try to rely on env var or just print status.
evaluator = OpikEvaluator(api_key="dummy_key_for_test")

print(f"Enabled: {evaluator.enabled}")

if evaluator.enabled:
    print("Tracking test evaluation...")
    evaluator.track_evaluation(
        content="This is a test content for Opik integration.",
        task_type="debug_test",
        metadata={"test": True},
    )
    print("Tracked.")
else:
    print("Opik not enabled (check OPIK_API_KEY or install opik).")
