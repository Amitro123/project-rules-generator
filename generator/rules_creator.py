"""
Cowork-Powered Rules Creator — backward-compatibility shim.

All logic has moved to generator/rules/:
  generator/rules/models.py   — Rule, RulesMetadata, QualityReport dataclasses
  generator/rules/creator.py  — CoworkRulesCreator class

This file re-exports everything so existing imports continue to work unchanged.
"""

from generator.rules import (  # noqa: F401
    CoworkRulesCreator,
    QualityReport,
    Rule,
    RulesMetadata,
    append_mandatory_anti_patterns,
)
# Re-export internal collaborators so existing mock.patch('generator.rules_creator.X') targets work.
from generator.rules_git_miner import RulesGitMiner  # noqa: F401
from generator.rules_renderer import RulesContentRenderer  # noqa: F401

__all__ = [
    "Rule",
    "RulesMetadata",
    "QualityReport",
    "CoworkRulesCreator",
    "append_mandatory_anti_patterns",
]
