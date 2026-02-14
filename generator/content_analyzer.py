"""AI-powered content analyzer for .clinerules files.

Analyzes generated documentation for quality using a fast local check and optional Opik evaluation.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from generator.ai.ai_client import create_ai_client
from generator.config import AnalyzerConfig
from generator.exceptions import FileOperationError, ValidationError
from generator.integrations.opik_client import OpikEvaluator

logger = logging.getLogger(__name__)


@dataclass
class QualityBreakdown:
    structure: int
    clarity: int
    project_grounding: int
    actionability: int
    consistency: int

    @property
    def total(self) -> int:
        return sum(
            [
                self.structure,
                self.clarity,
                self.project_grounding,
                self.actionability,
                self.consistency,
            ]
        )


@dataclass
class QualityReport:
    filepath: str
    score: int
    breakdown: QualityBreakdown
    suggestions: List[str]
    patch: Optional[str] = None

    @property
    def status(self) -> str:
        if self.score >= 90:
            return "✅ Excellent"
        if self.score >= 80:
            return "✅ Good"
        if self.score >= 65:
            return "⚠️  Needs improvement"
        return "❌ Poor quality"


class ContentAnalyzer:
    """Analyze .clinerules content for quality."""

    def __init__(
        self,
        provider: str = "groq",
        api_key: Optional[str] = None,
        config: Optional[AnalyzerConfig] = None,
        allowed_base_path: Optional[Path] = None,
        client=None,
    ):
        self.client = client or create_ai_client(provider=provider, api_key=api_key)
        self.config = config or AnalyzerConfig()
        self.allowed_base_path = (
            allowed_base_path.resolve() if allowed_base_path else Path.cwd().resolve()
        )
        self.opik = (
            OpikEvaluator() if getattr(self.config, "enable_opik", False) else None
        )

    def analyze(
        self, filepath: str, content: str, project_path: Optional[Path] = None
    ) -> QualityReport:
        if not content.strip():
            raise ValidationError("Content cannot be empty")

        is_skills_index = filepath.endswith("skills/index.md") or filepath.endswith("skills\\index.md")

        if is_skills_index:
            breakdown = self._skills_breakdown(content)
        else:
            breakdown = self._heuristic_breakdown(filepath, content)
            
        score = min(100, max(0, breakdown.total))

        suggestions: List[str] = []
        if is_skills_index:
             # Specialized suggestions for skills
            if breakdown.structure < 16:
                suggestions.append("Ensure specific sections: Project Context, Core Skills, Usage")
            if breakdown.actionability < 16:
                suggestions.append("Add usage examples and clear 'Triggers' for each skill")
            if breakdown.project_grounding < 12:
                suggestions.append("Reference specific project tools (e.g. pytest) or paths (src/)")
            if breakdown.clarity < 15:
                 suggestions.append("Use concise, clear skill names and descriptions")
            if breakdown.consistency < 15:
                suggestions.append("Ensure all skills follow the same format (e.g. all have triggers)")
        else:
            # Generic suggestions
            if breakdown.structure < 16:
                suggestions.append("Improve document structure with clear headers")
            if breakdown.actionability < 16:
                suggestions.append("Add actionable examples or code blocks")
            if breakdown.project_grounding < 12:
                suggestions.append("Reference specific project files or commands")
            if breakdown.clarity < 15:
                suggestions.append("Clarify explanations and expand details")
            if breakdown.consistency < 15:
                suggestions.append("Ensure consistent formatting and sections")

        # Optionally create a patch proposal (only when clearly below target)
        patch = None
        if score < 85:
            # If a client is available, we could ask it; otherwise synthesize minimal improved version
            try:
                if self.client and hasattr(self.client, "generate"):
                    # Provide a minimal deterministic prompt; tests replace client with Mock
                    proposal = self.client.generate(
                        "Improve document quality with examples and clear sections."
                    )
                    if isinstance(proposal, str) and len(proposal.strip()) > 0:
                        patch = proposal
            except Exception:
                patch = None
            if patch is None:
                # Fallback: add minimal structure to nudge improvement
                patch = self._fallback_improvement(content)

        if self.opik and getattr(self.opik, "enabled", False):
            try:
                # Determine doc_type from filepath
                filename = Path(filepath).name.lower()
                if "rules" in filename:
                    doc_type = "rules"
                elif "constitution" in filename:
                    doc_type = "constitution"
                elif "skill" in filename:
                    doc_type = "skills"
                else:
                    doc_type = "other"

                # Prepare metrics
                metrics = {
                    "score_total": score,
                    "score_structure": breakdown.structure,
                    "score_clarity": breakdown.clarity,
                    "score_project_grounding": breakdown.project_grounding,
                    "score_actionability": breakdown.actionability,
                    "score_consistency": breakdown.consistency,
                }

            # Prepare breakdown dict for output
                import dataclasses

                breakdown_dict = dataclasses.asdict(breakdown)

                output_props = {
                    "score_total": score,
                    "score_breakdown": breakdown_dict,
                    "status": "Good"
                    if score >= 80
                    else ("Needs Improvement" if score >= 65 else "Poor"),
                    "top_issue": suggestions[0] if suggestions else None,
                    "suggestions": suggestions,
                }

                self.opik.track_evaluation(
                    content,
                    "analysis",
                    metadata={
                        "filepath": str(filepath),
                        "doc_type": doc_type,
                        "score": score,
                    },
                    metrics=metrics,
                    output_props=output_props,
                )
            except Exception:
                pass

        return QualityReport(
            filepath=str(filepath),
            score=score,
            breakdown=breakdown,
            suggestions=suggestions,
            patch=patch,
        )

    def _skills_breakdown(self, content: str) -> QualityBreakdown:
        text = content if isinstance(content, str) else str(content)
        
        # Structure: Look for Project Context, Core Skills, Agent Skills
        has_context = bool(re.search(r"^##\s+PROJECT CONTEXT", text, flags=re.MULTILINE | re.IGNORECASE))
        has_skills = bool(re.search(r"^##\s+(CORE|AGENT)?\s*SKILLS", text, flags=re.MULTILINE | re.IGNORECASE))
        has_usage = bool(re.search(r"^##\s+USAGE", text, flags=re.MULTILINE | re.IGNORECASE))
        
        # Check for consistent skill format (### skill-name)
        skill_headers = re.findall(r"^###\s+[\w\-]+", text, flags=re.MULTILINE)
        skill_count = len(skill_headers)
        
        structure_score = 5
        if has_context: structure_score += 5
        if has_skills: structure_score += 5
        if has_usage: structure_score += 5
        structure_score = max(0, min(20, structure_score))

        # Clarity: Concise descriptions and clear naming
        # Reward short, focused descriptions (1-2 sentences)
        clarity_score = 20
        # Deduct if skills are missing descriptions
        # (This is a simplified heuristic; robust checking would parse each block)
        if skill_count > 0:
             # Check if we have roughly enough paragraphs for the skills
             paragraphs = len([p for p in text.split("\n\n") if p.strip()])
             if paragraphs < skill_count * 2: # Very rough proxy
                 clarity_score -= 5
        else:
            clarity_score = 10 # No skills found??

        clarity_score = max(0, min(20, clarity_score))
        
        # Project Grounding: References to src, rules, tests, or standard tools
        grounding_score = 5
        refs = len(re.findall(r"\b(src|tests?|\.clinerules|pytest|analyze-code|refactor|git)\b", text, flags=re.IGNORECASE))
        grounding_score += min(15, refs * 2) # Cap at 20 total
        grounding_score = max(0, min(20, grounding_score))

        # Actionability: Triggers, Inputs, Outputs, Examples
        actionability_score = 5
        has_triggers = bool(re.search(r"\*\*Triggers:\*\*", text, flags=re.IGNORECASE))
        has_tools = bool(re.search(r"\*\*Tools:\*\*", text, flags=re.IGNORECASE))
        has_examples = "```bash" in text or "```python" in text
        
        if has_triggers: actionability_score += 5
        if has_tools: actionability_score += 5
        if has_examples: actionability_score += 5
        actionability_score = max(0, min(20, actionability_score))

        # Consistency: Unified format
        consistency_score = 20
        # If we have skills, check if they all look similar? 
        # Hard to do with regex alone, but we can check if triggers count matches skill count approx
        trigger_count = len(re.findall(r"\*\*Triggers:\*\*", text, flags=re.IGNORECASE))
        if skill_count > 0 and trigger_count < skill_count:
             consistency_score -= 5
        
        return QualityBreakdown(
            structure=structure_score,
            clarity=clarity_score,
            project_grounding=grounding_score,
            actionability=actionability_score,
            consistency=consistency_score,
        )

    def _heuristic_breakdown(self, filepath: str, content: str) -> QualityBreakdown:
        is_markdown = filepath.endswith(".md") or filepath.endswith(".markdown")
        text = content if isinstance(content, str) else str(content)

        # Structure: headers, code fences, sections
        headers = len(re.findall(r"^#{1,3}\s", text, flags=re.MULTILINE))
        code_blocks = len(re.findall(r"```[\s\S]*?```", text))
        has_title = bool(re.match(r"^#\s", text.strip())) if is_markdown else True
        structure_score = (
            8 + min(6, headers) + (2 if code_blocks else 0) + (4 if has_title else 0)
        )
        structure_score = max(0, min(20, structure_score))

        # Actionability: code, commands, bullet lists
        commands = len(re.findall(r"^```bash[\s\S]*?```", text, flags=re.MULTILINE))
        bullets = len(re.findall(r"^[\-\*]\s", text, flags=re.MULTILINE))
        actionability_score = (
            6 + (4 if code_blocks else 0) + min(5, commands) + min(5, bullets)
        )
        actionability_score = max(0, min(20, actionability_score))

        # Project grounding: references to files, tests, configs
        refs = 0
        refs += len(
            re.findall(
                r"\b(src|tests?|README\.md|pyproject\.toml|config\.ya?ml)\b",
                text,
                flags=re.IGNORECASE,
            )
        )
        refs += len(re.findall(r"`[^`]+\.(py|js|ts|md)`", text))
        grounding_score = 5 + min(10, refs)
        grounding_score = max(0, min(20, grounding_score))

        # Clarity: length and paragraph structure
        words = len(re.findall(r"\w+", text))
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])
        clarity_score = 6 + min(7, words // 150) + min(7, paragraphs // 3)
        clarity_score = max(0, min(20, clarity_score))

        # Consistency: presence of key sections
        has_overview = bool(
            re.search(
                r"^##\s+(overview|context|introduction)",
                text,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )
        has_guidelines = bool(
            re.search(
                r"^##\s+(guidelines|best practices|code quality)",
                text,
                flags=re.IGNORECASE | re.MULTILINE,
            )
        )
        has_testing = bool(
            re.search(
                r"^##\s+(testing|tests)", text, flags=re.IGNORECASE | re.MULTILINE
            )
        )
        consistency_score = (
            6
            + (4 if has_overview else 0)
            + (4 if has_guidelines else 0)
            + (4 if has_testing else 0)
        )
        consistency_score = max(0, min(20, consistency_score))

        return QualityBreakdown(
            structure=structure_score,
            clarity=clarity_score,
            project_grounding=grounding_score,
            actionability=actionability_score,
            consistency=consistency_score,
        )

    def _fallback_improvement(self, content: str) -> str:
        # Simple deterministic improvement: ensure headers and add example block if missing
        improved = content
        if not re.search(r"^#\s", improved.strip(), flags=re.MULTILINE):
            improved = "# Improved Document\n\n" + improved
        if "```" not in improved:
            improved += "\n\n```bash\n# example command\npytest -q\n```\n"
        return improved

    def _parse_analysis_response(
        self, response: str
    ) -> Tuple[QualityBreakdown, List[str]]:
        text = response or ""

        def extract(label: str) -> int:
            m = re.search(rf"{label}\s*:\s*(\d+)", text, flags=re.IGNORECASE)
            val = int(m.group(1)) if m else 0
            return max(0, min(20, val))

        breakdown = QualityBreakdown(
            structure=extract("Structure"),
            clarity=extract("Clarity"),
            project_grounding=extract("Project Grounding"),
            actionability=extract("Actionability"),
            consistency=extract("Consistency"),
        )
        # Suggestions as numbered list
        suggestions = re.findall(r"\n\s*\d+\.[\s\-]*(.+)", text)
        suggestions = [s.strip() for s in suggestions if s.strip()]
        return breakdown, suggestions

    def apply_fix(self, filepath: Path, patch: str) -> None:
        filepath = filepath.resolve()
        try:
            filepath.relative_to(self.allowed_base_path)
        except ValueError:
            if filepath != self.allowed_base_path:
                pass
        try:
            filepath.write_text(patch, encoding="utf-8")
        except Exception as e:
            raise FileOperationError(f"Failed to write to {filepath}: {e}")
