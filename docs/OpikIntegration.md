🚀 v1.2.0: Comet Opik Integration (Replace Subjective Scores)

**Remove hardcoded 5-dimension scoring → Opik LLM eval**

1. **content_analyzer.py → Simplified:**
```python
def quick_check(content):
    return {
        'length_ok': len(content) > 1000,
        'has_headers': '##' in content,
        'project_specific': any(t in content.lower() for t in tech_stack),
        'needs_review': True  # Send to Opik
    }
opik_client.py (NEW):

python
import opik
def eval_with_opik(content, task_type):
    opik.log_evaluation(
        name=f"rules-{task_type}",
        input={"content": content[:4000]},
        output="user_feedback",  # Thumbs up/down
        metrics=['completeness', 'relevance']
    )
CLI:

prg analyze . --eval-opik  # Logs to dashboard
prg leaderboard            # Compare projects

Migration:

rm content_analyzer.py complex scoring
Add quick_check() + opik_client.py
Test: prg analyze . --eval-opik → Comet dashboard entry!

Commit: "feat: Comet Opik eval (production metrics)"


***

## 🎯 **Benefits:**

Before: 78/100 subjective nonsense
After: Opik leaderboard + real metrics
✅ A/B test prompts
✅ Model comparison (Groq vs Claude)
✅ User thumbs up/down
✅ Production-grade eval!
