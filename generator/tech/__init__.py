"""generator.tech — tech registry package.

Re-exports everything from the sub-modules for convenient imports.
"""

from generator.tech.lookups import (
    NPM_PKG_ALIASES,
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
    "NPM_PKG_ALIASES",
    "SKILL_IMPORT_NAMES",
]
