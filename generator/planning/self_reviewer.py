"""Self-review agent for critiquing generated artifacts."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from generator.ai.factory import create_ai_client

REVIEW_SYSTEM_PROMPT = (
    "You are a document reviewer. Evaluate the provided artifact for quality, "
    "accuracy, and hallucinations. Only reference information that appears in "
    "the provided README context. Flag any project names, tools, or services "
    "that appear in the artifact but NOT in the README."
)


@dataclass
class ReviewReport:
    """Result of a self-review critique."""

    verdict: str  # "Pass", "Needs Revision", "Major Issues"
    strengths: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    action_plan: List[str] = field(default_factory=list)
    hallucinations: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Render as CRITIQUE.md content."""
        lines = ["# Review Report", ""]
        lines.append(f"**Verdict:** {self.verdict}")
        lines.append("")

        if self.strengths:
            lines.append("## Strengths")
            for s in self.strengths:
                lines.append(f"- {s}")
            lines.append("")

        if self.issues:
            lines.append("## Issues")
            for i in self.issues:
                lines.append(f"- {i}")
            lines.append("")

        if self.hallucinations:
            lines.append("## Hallucinations Detected")
            for h in self.hallucinations:
                lines.append(f"- {h}")
            lines.append("")

        if self.action_plan:
            lines.append("## Action Plan")
            for a in self.action_plan:
                lines.append(f"- [ ] {a}")
            lines.append("")

        return "\n".join(lines)


class SelfReviewer:
    """Critique generated artifacts for quality and hallucinations."""

    def __init__(
        self, provider: str = "groq", api_key: Optional[str] = None, client=None
    ):
        self.client = client or create_ai_client(provider=provider, api_key=api_key)

    def review(
        self, filepath: Path, project_path: Optional[Path] = None
    ) -> ReviewReport:
        """Critique a generated artifact.

        Args:
            filepath: Path to the artifact to review
            project_path: Optional project root to read README for context

        Returns:
            ReviewReport with verdict, issues, and hallucination list
        """
        content = filepath.read_text(encoding="utf-8")

        # Gather README context
        readme_excerpt = ""
        if project_path:
            readme_path = Path(project_path) / "README.md"
            if readme_path.exists():
                readme_excerpt = readme_path.read_text(encoding="utf-8")[:2000]

        prompt = self._build_review_prompt(content, readme_excerpt)

        try:
            response = self.client.generate(
                prompt,
                temperature=0.3,
                max_tokens=2000,
                system_message=REVIEW_SYSTEM_PROMPT,
            )
            report = self._parse_review(response)
        except Exception:
            report = self._static_review(content, readme_excerpt)

        # Always run static hallucination check
        static_hallucinations = self._detect_hallucinations(content, readme_excerpt)
        for h in static_hallucinations:
            if h not in report.hallucinations:
                report.hallucinations.append(h)

        # Upgrade verdict if hallucinations found
        if report.hallucinations and report.verdict == "Pass":
            report.verdict = "Needs Revision"

        return report

    def _build_review_prompt(self, content: str, readme_excerpt: str) -> str:
        """Build prompt for AI-powered review."""
        readme_block = ""
        if readme_excerpt:
            readme_block = f"""
<readme>
{readme_excerpt}
</readme>
"""

        return f"""Review this generated artifact for quality and accuracy.
{readme_block}
<artifact>
{content[:3000]}
</artifact>

Check for:
1. Does the title match the actual content?
2. Are there references to projects, tools, or services NOT in the README?
3. Is testing integrated throughout or end-loaded into a final phase?
4. Are there missing sections or incomplete tasks?

Respond in this exact format:
VERDICT: [Pass / Needs Revision / Major Issues]
STRENGTHS:
- [strength 1]
- [strength 2]
ISSUES:
- [issue 1]
- [issue 2]
HALLUCINATIONS:
- [term not in README, or "None"]
ACTION_PLAN:
- [fix 1]
- [fix 2]
"""

    def _parse_review(self, response: str) -> ReviewReport:
        """Parse AI response into ReviewReport."""
        verdict = "Needs Revision"
        strengths = []
        issues = []
        hallucinations = []
        action_plan = []

        # Extract verdict
        verdict_match = re.search(r"VERDICT:\s*(.+)", response)
        if verdict_match:
            raw = verdict_match.group(1).strip()
            if "Pass" in raw:
                verdict = "Pass"
            elif "Major" in raw:
                verdict = "Major Issues"
            else:
                verdict = "Needs Revision"

        # Extract sections
        strengths = self._extract_section(response, "STRENGTHS")
        issues = self._extract_section(response, "ISSUES")
        hallucinations = self._extract_section(response, "HALLUCINATIONS")
        action_plan = self._extract_section(response, "ACTION_PLAN")

        # Clean up "None" entries
        hallucinations = [
            h
            for h in hallucinations
            if h.lower() not in ("none", "n/a", "none detected")
        ]

        return ReviewReport(
            verdict=verdict,
            strengths=strengths,
            issues=issues,
            action_plan=action_plan,
            hallucinations=hallucinations,
        )

    def _extract_section(self, text: str, header: str) -> List[str]:
        """Extract bullet items under a section header."""
        pattern = rf"{header}:\s*\n((?:\s*-\s+.+\n?)+)"
        match = re.search(pattern, text)
        if not match:
            return []

        items = []
        for line in match.group(1).split("\n"):
            line = line.strip()
            if line.startswith("-"):
                item = line.lstrip("-").strip()
                if item:
                    items.append(item)
        return items

    def _detect_hallucinations(self, content: str, readme_content: str) -> List[str]:
        """Static check for terms in artifact not present in README."""
        if not readme_content:
            return []

        hallucinated = []
        readme_lower = readme_content.lower()

        # Find capitalized compound names (DevLens-AI, GithubAgent, etc.)
        candidates = set(re.findall(r"\b[A-Z][a-zA-Z]+-[A-Z][a-zA-Z]+\b", content))
        candidates |= set(re.findall(r"\b[A-Z][a-z]+[A-Z][a-zA-Z]+\b", content))

        for term in candidates:
            if term.lower() not in readme_lower:
                hallucinated.append(term)

        return hallucinated

    def _static_review(self, content: str, readme_excerpt: str) -> ReviewReport:
        """Fallback review when AI is unavailable."""
        issues = []
        strengths = []

        # Check basic structure
        if content.startswith("#"):
            strengths.append("Has a title heading")
        else:
            issues.append("Missing title heading")

        phase_count = len(re.findall(r"^## ", content, re.MULTILINE))
        if phase_count >= 3:
            strengths.append(f"Has {phase_count} phases")
        elif phase_count > 0:
            issues.append(f"Only {phase_count} phase(s) - expected 3-5")
        else:
            issues.append("No phase sections found")

        task_count = len(re.findall(r"- \[ \]", content))
        if task_count >= 5:
            strengths.append(f"Contains {task_count} tasks")
        else:
            issues.append(f"Only {task_count} task(s) found")

        hallucinations = self._detect_hallucinations(content, readme_excerpt)

        verdict = "Pass"
        if hallucinations:
            verdict = "Major Issues"
        elif issues:
            verdict = "Needs Revision"

        return ReviewReport(
            verdict=verdict,
            strengths=strengths,
            issues=issues,
            hallucinations=hallucinations,
            action_plan=[f"Fix: {i}" for i in issues],
        )
