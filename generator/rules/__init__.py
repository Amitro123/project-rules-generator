"""generator.rules — rules generation package.

Re-exports all public names so generator.rules_creator shim continues to work.
"""

from generator.rules.creator import CoworkRulesCreator
from generator.rules.models import QualityReport, Rule, RulesMetadata
from generator.rules_renderer import append_mandatory_anti_patterns  # noqa: F401 (re-export passthrough)

__all__ = [
    "Rule",
    "RulesMetadata",
    "QualityReport",
    "CoworkRulesCreator",
    "append_mandatory_anti_patterns",
]
