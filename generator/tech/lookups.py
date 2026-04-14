"""Derived lookup dicts built once at module load from _PROFILES.

All callers should import the named dicts directly:
    from generator.tech.lookups import TECH_RULES, PKG_MAP
"""

from typing import Dict, List

from generator.tech.profiles import _PROFILES

REGISTRY = {p.name: p for p in _PROFILES}

# tech name → preferred skill filename
TECH_SKILL_NAMES: Dict[str, str] = {p.name: p.skill_name for p in _PROFILES if p.skill_name}
# Legacy aliases pointing to the same skill
TECH_SKILL_NAMES["websockets"] = "websocket-handler"
TECH_SKILL_NAMES["chrome-extension"] = "chrome-extension"

# tech name → list of shell tools
TECH_TOOLS: Dict[str, List[str]] = {p.name: p.tools for p in _PROFILES if p.tools}

# tech name → coding rules {priority: [rules]}
TECH_RULES: Dict[str, Dict[str, List[str]]] = {p.name: p.rules for p in _PROFILES if p.rules}

# tech name → list of README keywords
TECH_README_KEYWORDS: Dict[str, List[str]] = {p.name: p.readme_keywords for p in _PROFILES if p.readme_keywords}

# package name → canonical tech name  (inverse of TechProfile.packages)
PKG_MAP: Dict[str, str] = {}
for _p in _PROFILES:
    for _pkg in _p.packages:
        PKG_MAP[_pkg] = _p.name

# skill_name → Python import keyword (for code-usage file search)
SKILL_IMPORT_NAMES: Dict[str, str] = {}
for _p in _PROFILES:
    if not _p.skill_name:
        continue
    if _p.import_name:
        SKILL_IMPORT_NAMES[_p.skill_name] = _p.import_name
    elif _p.packages:
        _kw = _p.packages[0].replace("-", "_").split(".")[0]
        SKILL_IMPORT_NAMES[_p.skill_name] = _kw

# tech name → output category (backend | frontend | database | infrastructure | ml | ai | testing | language)
TECH_CATEGORIES: Dict[str, str] = {p.name: p.category for p in _PROFILES}

# tech name → human-readable display label (e.g. "FastAPI", "Next.js")
TECH_DISPLAY_NAMES: Dict[str, str] = {p.name: (p.display_name if p.display_name else p.name.title()) for p in _PROFILES}

# filename → tech name  (for file-presence–based detection, e.g. "Dockerfile" → "docker")
FILE_DETECTION_MAP: Dict[str, str] = {}
for _p in _PROFILES:
    for _f in _p.detection_files:
        FILE_DETECTION_MAP[_f] = _p.name

# directory path → tech name  (e.g. ".github/workflows" → "github-actions")
DIR_DETECTION_MAP: Dict[str, str] = {}
for _p in _PROFILES:
    for _d in _p.detection_dirs:
        DIR_DETECTION_MAP[_d] = _p.name
