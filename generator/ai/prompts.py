"""AI prompts for content analysis and improvement."""

from typing import List, Optional
from generator.content_analyzer import QualityBreakdown


def get_improvement_prompt(
    filepath: str,
    content: str,
    breakdown: QualityBreakdown,
    suggestions: List[str],
    project_context: Optional[str] = None,
) -> str:
    """Generate compact improvement prompt that resists leakage.

    Uses delimited document block and short issue list to minimize
    the chance of small models echoing prompt instructions into output.

    Args:
        filepath: Path to file being improved
        content: Original content
        breakdown: Quality score breakdown
        suggestions: List of specific suggestions
        project_context: Optional short project context string

    Returns:
        Compact prompt for AI to generate improvements
    """
    # Build concise issue list from low-scoring dimensions
    issues = []
    if breakdown.structure < 16:
        issues.append(f"- Structure ({breakdown.structure}/20): add proper H1 title, fix header hierarchy, close all code fences")
    if breakdown.clarity < 16:
        issues.append(f"- Clarity ({breakdown.clarity}/20): replace generic descriptions with project-specific ones, remove fluff")
    if breakdown.project_grounding < 16:
        issues.append(f"- Project grounding ({breakdown.project_grounding}/20): reference actual project files and real CLI commands")
    if breakdown.actionability < 16:
        issues.append(f"- Actionability ({breakdown.actionability}/20): add working code examples with proper fenced blocks")
    if breakdown.consistency < 16:
        issues.append(f"- Consistency ({breakdown.consistency}/20): use same header style and bullet format throughout")

    issues_text = '\n'.join(issues) if issues else "- General quality improvements needed"

    # Build short suggestions list (max 5, one line each)
    suggestions_text = '\n'.join(f"- {s}" for s in suggestions[:5]) if suggestions else "- Improve overall quality"

    # Add project context if available so the AI can reference real files/commands
    context_block = ""
    if project_context:
        context_block = f"\nProject info (use these real references):\n{project_context}\n"

    prompt = f"""<document>
{content}
</document>
{context_block}
Fix these issues (current score: {breakdown.total}/100):
{issues_text}

Suggestions:
{suggestions_text}

Output the complete improved document. Start directly with the first heading."""

    return prompt
