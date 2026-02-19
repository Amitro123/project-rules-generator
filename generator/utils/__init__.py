"""Utilities package."""

from .cli import flush_input
from .encoding import normalize_mojibake
from .quality_checker import QualityReport, is_stub, validate_quality
from .tech_detector import detect_from_dependencies, detect_tech_stack, extract_context

__all__ = [
    "normalize_mojibake",
    "flush_input",
    "detect_tech_stack",
    "detect_from_dependencies",
    "extract_context",
    "is_stub",
    "validate_quality",
    "QualityReport",
]
