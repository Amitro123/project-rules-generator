"""All TechProfile entries — the full technology registry data.

Data is split by category in generator/tech/_profiles/:
  backend.py        — web frameworks, async, CLI, HTTP clients, networking, specialised
  frontend.py       — frontend frameworks and tools
  testing.py        — testing frameworks
  infrastructure.py — Docker, CI, Kubernetes, etc.
  database.py       — databases and caches
  ml_ai.py          — ML and AI providers
  languages.py      — language detection entries (no skill generated)

Add a new technology to the appropriate category file.
All derived lookups (REGISTRY, TECH_SKILL_NAMES, …) in lookups.py are built
automatically from _PROFILES.
"""

from generator.tech._profiles._registry import _PROFILES

__all__ = ["_PROFILES"]
