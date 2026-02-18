"""
Skill Generation Strategies

This module provides a strategy pattern implementation for skill generation,
allowing different methods (AI, README parsing, Cowork analysis, stub templates)
to be used interchangeably.
"""

from generator.strategies.ai_strategy import AIStrategy
from generator.strategies.readme_strategy import READMEStrategy
from generator.strategies.cowork_strategy import CoworkStrategy
from generator.strategies.stub_strategy import StubStrategy

__all__ = [
    "AIStrategy",
    "READMEStrategy",
    "CoworkStrategy",
    "StubStrategy",
]
