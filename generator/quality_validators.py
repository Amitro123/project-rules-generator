"""
Quality Validators
==================

Single module for all quality validation logic in PRG.

Classes:
    SkillQualityValidator  — validates skill content (hallucination detection, auto-fix)
    RulesQualityValidator  — validates rules sets (completeness, conflicts, priority)

Shared low-level checks live in generator.utils.quality_checker.
"""

import re
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List

from generator.utils.quality_checker import QualityReport, validate_quality

if TYPE_CHECKING:
    from generator.rules_creator import QualityReport as RulesQualityReport
    from generator.rules_creator import Rule, RulesMetadata
    from generator.skill_creator import SkillMetadata


# ---------------------------------------------------------------------------
# Skill quality
# ---------------------------------------------------------------------------


class SkillQualityValidator:
    """Validates and auto-fixes generated skill content."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def validate(self, content: str, metadata: "SkillMetadata") -> QualityReport:
        """Run quality gates on skill content.

        Delegates shared checks to quality_checker.validate_quality(), then adds
        the project-specific hallucination check that requires self.project_path.
        """
        report = validate_quality(content, metadata.auto_triggers, metadata.tools)

        hallucinated = self._detect_hallucinated_paths(content)
        if hallucinated:
            extra_issue = f"Hallucinated file paths: {', '.join(hallucinated[:3])}"
            score = max(0.0, report.score - 20)
            issues = report.issues + [extra_issue]
            return QualityReport(
                score=score,
                passed=score >= 70 and not issues,
                issues=issues,
                warnings=report.warnings,
                suggestions=report.suggestions,
            )

        return report

    def _detect_hallucinated_paths(self, content: str) -> List[str]:
        """Detect file paths referenced in content that don't exist in the project."""
        hallucinated = []

        patterns = [
            r"(?:File:|Path:|`)([\w/.-]+\.[\w]+)",
            r"`(src/[\w/]+\.py)`",
            r"(?:in|check|see) `([\w/.-]+\.[\w]+)`",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, content):
                if not (self.project_path / match).exists():
                    hallucinated.append(match)

        return hallucinated

    def auto_fix(self, content: str, quality: QualityReport) -> str:
        """Attempt to auto-fix common quality issues."""
        content = content.replace("cd project_name", f"cd {self.project_path.name}")
        content = content.replace("/path/to/project", str(self.project_path))

        content = re.sub(r"\[describe.*?\]", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\[example.*?\]", "", content, flags=re.IGNORECASE)

        if "## Anti-Patterns" not in content:
            content += (
                "\n\n## Anti-Patterns\n\n"
                "\u274c **Don't** use generic solutions without understanding project context\n"
                "\u2705 **Do** analyze project structure first\n\n"
                "\u274c **Don't** skip validation steps\n"
                "\u2705 **Do** always verify changes work\n"
            )

        return content


# ---------------------------------------------------------------------------
# Rules quality
# ---------------------------------------------------------------------------


class RulesQualityValidator:
    """Validates quality of a generated rules set."""

    def validate(
        self,
        content: str,
        metadata: "RulesMetadata",
        rules_by_category: Dict[str, List["Rule"]],
    ) -> "RulesQualityReport":
        """Validate rules quality with Cowork standards."""
        from generator.rules_creator import QualityReport as RulesQR

        issues: List[str] = []
        warnings: List[str] = []
        score = 100.0

        required_sections = ["Coding Standards", "Priority Areas", "Tech Stack"]
        completeness = sum(1 for sec in required_sections if sec in content) / len(required_sections)

        if completeness < 1.0:
            issues.append(f"Missing sections (completeness: {completeness * 100:.0f}%)")
            score -= 20

        total_rules = sum(len(rules) for rules in rules_by_category.values())
        if total_rules < 5:
            warnings.append(f"Only {total_rules} rules generated (recommend 10+)")
            score -= 10

        high_priority = sum(1 for rules in rules_by_category.values() for rule in rules if rule.priority == "High")
        if high_priority < 2:
            warnings.append("Few high-priority rules (recommend 3+)")
            score -= 5

        conflicts = self.detect_rule_conflicts(rules_by_category)
        if conflicts:
            issues.extend(conflicts)
            score -= len(conflicts) * 10

        if not any(rule.source.endswith("_patterns") for rules in rules_by_category.values() for rule in rules):
            warnings.append("No tech-specific rules (may be too generic)")
            score -= 5

        passed = score >= 85 and len(issues) == 0

        return RulesQR(
            score=max(0, score),
            passed=passed,
            issues=issues,
            warnings=warnings,
            completeness=completeness,
            conflicts=conflicts,
        )

    def detect_rule_conflicts(self, rules_by_category: Dict[str, List["Rule"]]) -> List[str]:
        """Detect genuinely contradictory rules (same topic, opposite direction)."""
        conflicts: List[str] = []
        all_rules = [rule.content.lower() for rules in rules_by_category.values() for rule in rules]

        conflict_pairs = [
            ("use async", "don't use async"),
            ("use class components", "don't use class components"),
            ("use sync", "don't use sync"),
        ]

        for positive, negative in conflict_pairs:
            if any(positive in r for r in all_rules) and any(negative in r for r in all_rules):
                conflicts.append(f"Conflicting rules about '{positive}'")

        return conflicts
