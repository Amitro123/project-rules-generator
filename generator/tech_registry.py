"""
Tech Registry — backward-compatibility shim.

All logic has moved to generator/tech/:
  generator/tech/profile.py   — TechProfile dataclass
  generator/tech/profiles.py  — _PROFILES list (add new techs here)
  generator/tech/lookups.py   — derived dicts (REGISTRY, PKG_MAP, …)

This file re-exports everything so existing imports continue to work unchanged.
"""

from generator.tech import (  # noqa: F401
    _PROFILES,
    PKG_MAP,
    REGISTRY,
    SKILL_IMPORT_NAMES,
    TECH_README_KEYWORDS,
    TECH_RULES,
    TECH_SKILL_NAMES,
    TECH_TOOLS,
    TechProfile,
)

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
