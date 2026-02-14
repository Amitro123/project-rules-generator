"""Utilities package."""

from .cli import flush_input
from .encoding import normalize_mojibake

__all__ = ["normalize_mojibake", "flush_input"]
