"""
Rules Manager — Facade
======================

Public API for all rules generation. Mirrors SkillsManager pattern:

    RulesManager (Facade)
        └── RulesGenerator (Orchestrator + inline strategies)
                ├── CoworkStrategy  → rules_creator.CoworkRulesCreator
                └── LegacyStrategy  → _generate_enhanced_rules / _generate_basic_rules

Usage:
    manager = RulesManager(project_path)
    output_path = manager.create_rules()                   # prg create-rules .
    content     = manager.analyze_rules(project_data, cfg) # prg analyze .
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from generator.rules_generator import RulesGenerator


class RulesManager:
    """
    Facade for all rules generation operations.

    Delegates to RulesGenerator (orchestrator) which selects the
    appropriate strategy (Cowork or Legacy) based on context.
    """

    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.generator = RulesGenerator(self.project_path)

    # ── Public API ────────────────────────────────────────────────────────────

    def create_rules(
        self,
        tech_stack: Optional[List[str]] = None,
        quality_threshold: float = 85.0,
        output_dir: Optional[Path] = None,
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Path, Any, Any]:
        """
        Create Cowork-quality rules.md for the project.

        Used by: ``prg create-rules .``

        Args:
            tech_stack: Override auto-detected tech stack.
            quality_threshold: Minimum quality score to pass (0-100).
            output_dir: Where to write rules.md (default: .clinerules/).
            enhanced_context: Optional rich project context.

        Returns:
            Tuple of (output_path, metadata, quality_report)
        """
        out_dir = output_dir or (self.project_path / ".clinerules")
        return self.generator.create_rules(
            tech_stack=tech_stack,
            quality_threshold=quality_threshold,
            output_dir=out_dir,
            enhanced_context=enhanced_context,
        )

    def analyze_rules(
        self,
        project_data: Dict[str, Any],
        config: Dict[str, Any],
        enhanced_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate rules content via the legacy enhanced-analysis path.

        Used by: ``prg analyze .``

        Args:
            project_data: Parsed project data from README.
            config: Generation configuration dict.
            enhanced_context: Full context from EnhancedProjectParser.

        Returns:
            Markdown string for rules file.
        """
        return self.generator.generate_legacy(project_data, config, enhanced_context)

    def rules_to_json(self, rules_md: str) -> str:
        """Convert rules markdown to structured JSON (machine-readable)."""
        return self.generator.rules_to_json(rules_md)
