"""generator.tech — tech registry package.

Re-exports everything from the sub-modules so callers that previously imported
from generator.tech_registry continue to work via the backward-compat shim.
"""

from generator.tech.lookups import (
    PKG_MAP,
    REGISTRY,
    SKILL_IMPORT_NAMES,
    TECH_README_KEYWORDS,
    TECH_RULES,
    TECH_SKILL_NAMES,
    TECH_TOOLS,
)
from generator.tech.profile import TechProfile
from generator.tech.profiles import _PROFILES

__all__ = [
    "TechProfile",
    "_PROFILES",
    "REGISTRY",
    "TECH_SKILL_NAMES",
    "TECH_TOOLS",
    "TECH_RULES",
    "TECH_README_KEYWORDS",
    "PKG_MAP",
    "SKILL_IMPORT_NAMES",
]
