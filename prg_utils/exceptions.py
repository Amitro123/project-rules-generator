"""Custom exceptions for better error handling"""


class ProjectRulesGeneratorError(Exception):
    """Base exception for all generator errors."""

    pass


class READMENotFoundError(ProjectRulesGeneratorError):
    """README.md file not found."""

    pass


class InvalidREADMEError(ProjectRulesGeneratorError):
    """README.md is empty or malformed."""

    pass
