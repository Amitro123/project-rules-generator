"""Assembles the full _PROFILES list from all category modules."""

from typing import List

from generator.tech._profiles.backend import BACKEND
from generator.tech._profiles.database import DATABASE
from generator.tech._profiles.frontend import FRONTEND
from generator.tech._profiles.infrastructure import INFRASTRUCTURE
from generator.tech._profiles.languages import LANGUAGES
from generator.tech._profiles.ml_ai import ML_AI
from generator.tech._profiles.testing import TESTING
from generator.tech.profile import TechProfile

_PROFILES: List[TechProfile] = BACKEND + FRONTEND + TESTING + INFRASTRUCTURE + DATABASE + ML_AI + LANGUAGES
