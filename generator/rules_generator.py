"""
Rules Generator — Orchestrator
================================

Replaces the old function-based rules_generator.py with a class-based
orchestrator that selects the right strategy via a chain:

    CoworkStrategy  → rich priority-scored rules (prg create-rules .)
    LegacyStrategy  → context-aware DO/DON'T rules  (prg analyze .)
    StubStrategy    → minimal fallback

Backward compatibility:
    ``from generator.rules_generator import generate_rules`` still works —
    the module-level function at the bottom delegates to RulesGenerator.
    ``from generator.rules_generator import rules_to_json`` also preserved.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generator.rules_creator import append_mandatory_anti_patterns
from generator.utils.readme_bridge import bridge_missing_context, is_readme_sufficient

# ── Strategy Protocol ─────────────────────────────────────────────────────────


class _RulesStrategy:
    """Base class for inline rules generation strategies."""

    name: str = "base"

    def can_handle(self, **kwargs) -> bool:  # noqa: ANN003
        """Return True if this strategy should be tried."""
        return True

    def generate(self, **kwargs) -> Optional[str]:  # noqa: ANN003
        """Generate rules content. Return None to fall through to next strategy."""
        raise NotImplementedError


# ── CoworkStrategy ────────────────────────────────────────────────────────────


class _CoworkStrategy(_RulesStrategy):
    """
    Wraps CoworkRulesCreator to produce priority-scored rules.md.
    Used by: prg create-rules .
    """

    name = "cowork"

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def can_handle(self, **kwargs) -> bool:
        return True  # Always available

    def generate(
        self,
        readme_content: str = "",
        tech_stack: Optional[List[str]] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
        **_,
    ) -> Optional[str]:
        from generator.rules_creator import CoworkRulesCreator

        creator = CoworkRulesCreator(self.project_path)
        content, _metadata, _quality = creator.create_rules(
            readme_content=readme_content,
            tech_stack=tech_stack,
            enhanced_context=enhanced_context,
        )
        return content


# ── LegacyStrategy ────────────────────────────────────────────────────────────


class _LegacyStrategy(_RulesStrategy):
    """
    Context-aware rules generation from actual project analysis.
    Used by: prg analyze .
    Preserves all original _generate_enhanced_rules / _generate_basic_rules logic.
    """

    name = "legacy"

    def can_handle(self, **kwargs) -> bool:
        return True  # Always available as fallback

    def generate(
        self,
        project_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
        **_,
    ) -> Optional[str]:
        if project_data is None:
            return None
        cfg = config or {}
        if enhanced_context:
            return _generate_enhanced_rules(project_data, cfg, enhanced_context)
        return _generate_basic_rules(project_data, cfg)


# ── StubStrategy ──────────────────────────────────────────────────────────────


class _StubStrategy(_RulesStrategy):
    """Minimal fallback when no context is available."""

    name = "stub"

    def generate(self, **kwargs) -> str:
        return (
            "# Project Rules\n\n"
            "## DO\n\n"
            "- Follow existing project structure\n"
            "- Write tests for new features\n"
            "- Don't commit secrets or API keys\n"
        )


# ── RulesGenerator (Orchestrator) ─────────────────────────────────────────────


class RulesGenerator:
    """
    Orchestrates rules generation via a strategy chain.

    Strategy priority:
        1. CoworkStrategy  — for prg create-rules (priority-scored output)
        2. LegacyStrategy  — for prg analyze (DO/DON'T/TESTING/WORKFLOWS output)
        3. StubStrategy    — minimal fallback
    """

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self._cowork = _CoworkStrategy(self.project_path)
        self._legacy = _LegacyStrategy()
        self._stub = _StubStrategy()

    # ── Cowork path (prg create-rules .) ──────────────────────────────────────

    def create_rules(
        self,
        tech_stack: Optional[List[str]] = None,
        quality_threshold: float = 85.0,
        output_dir: Optional[Path] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, Any, Any]:
        """
        Generate Cowork-quality rules.md and write to output_dir.

        Returns:
            (output_path, metadata, quality_report)
        """
        from generator.rules_creator import CoworkRulesCreator

        out_dir = output_dir or (self.project_path / ".clinerules")
        readme_content = self._read_readme()

        # If README is missing or sparse, bridge the gap with project tree
        # (+ optional user description in interactive/CLI mode)
        if not is_readme_sufficient(readme_content):
            supplement = bridge_missing_context(self.project_path, "rules")
            if supplement:
                readme_content = supplement + "\n\n" + readme_content

        creator = CoworkRulesCreator(self.project_path)
        content, metadata, quality = creator.create_rules(
            readme_content=readme_content,
            tech_stack=tech_stack,
            enhanced_context=enhanced_context,
        )

        output_path = creator.export_to_file(content, metadata, out_dir)
        return output_path, metadata, quality

    # ── Legacy path (prg analyze .) ───────────────────────────────────────────

    def generate_legacy(
        self,
        project_data: Dict[str, Any],
        config: Dict[str, Any],
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate rules via the legacy enhanced-analysis path.
        Preserves full DO/DON'T/TESTING/WORKFLOWS/CONTEXT STRATEGY output.
        """
        result = self._legacy.generate(
            project_data=project_data,
            config=config,
            enhanced_context=enhanced_context,
        )
        return result or self._stub.generate()

    # ── Shared utilities ──────────────────────────────────────────────────────

    def rules_to_json(self, rules_md: str) -> str:
        """Convert rules markdown to structured JSON."""
        return rules_to_json(rules_md)

    def _read_readme(self) -> str:
        """Read README from project path."""
        from generator.utils.readme_bridge import find_readme

        p = find_readme(self.project_path)
        return p.read_text(encoding="utf-8", errors="ignore") if p else ""


# ═════════════════════════════════════════════════════════════════════════════
# LEGACY STRATEGY — section builders live in rules_sections.py
# Backward-compat re-exports so existing imports keep working.
# ═════════════════════════════════════════════════════════════════════════════

from generator.rules_sections import (  # noqa: F401, E402
    _build_context_strategy,
    _build_dep_section,
    _build_dont_rules,
    _build_do_rules,
    _build_file_structure,
    _build_test_section,
    _build_workflow_section,
    _generate_basic_rules,
    _generate_enhanced_rules,
    _sanitize_readme_section,
)


# ═════════════════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY — module-level functions
# analyze_cmd.py imports these directly; they now delegate to RulesGenerator.
# ═════════════════════════════════════════════════════════════════════════════


def generate_rules(
    project_data: Dict[str, Any],
    config: Dict[str, Any],
    enhanced_context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Backward-compatible entry point used by analyze_cmd.py.

    Delegates to RulesGenerator.generate_legacy() — zero behavior change.
    """
    generator = RulesGenerator()
    return generator.generate_legacy(project_data, config, enhanced_context)


def rules_to_json(rules_md: str) -> str:
    """
    Convert rules markdown to structured JSON.

    Backward-compatible module-level function.
    """
    data: Dict[str, Any] = {}

    fm_match = re.match(r"^---\n(.*?)\n---", rules_md, re.DOTALL)
    if fm_match:
        for line in fm_match.group(1).split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                data[key.strip()] = val.strip()

    sections: Dict[str, List[str]] = {}
    current_section = None
    for line in rules_md.split("\n"):
        header = re.match(r"^##\s+(.+)$", line)
        if header:
            current_section = header.group(1).strip()
            sections[current_section] = []
        elif current_section and line.strip().startswith("-"):
            item = line.strip().lstrip("-").strip()
            if item:
                sections[current_section].append(item)

    do_rules = sections.get("DO (must follow)", [])
    dont_rules = sections.get("DON'T", [])

    data["rules"] = {"do": do_rules, "dont": dont_rules}
    data["priorities"] = sections.get("PRIORITIES", [])
    data["rules_count"] = len(do_rules) + len(dont_rules)

    skip = {"DO (must follow)", "DON'T", "PRIORITIES"}
    for section_name, items in sections.items():
        if section_name not in skip and items:
            key = section_name.lower().replace(" ", "_")
            data[key] = items

    return json.dumps(data, indent=2, ensure_ascii=False)
