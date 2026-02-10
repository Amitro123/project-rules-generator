"""Custom exceptions for the project-rules-generator."""


class PRGError(Exception):
    """Base exception for all PRG errors."""
    pass


class AIClientError(PRGError):
    """Raised when AI client operations fail."""
    pass


class ValidationError(PRGError):
    """Raised when input validation fails."""
    pass


class FileOperationError(PRGError):
    """Raised when file operations fail."""
    pass


class SecurityError(PRGError):
    """Raised when security checks fail (e.g., path traversal)."""
    pass


class PlanParsingError(PRGError):
    """Raised when plan file parsing fails."""
    pass


class ConfigurationError(PRGError):
    """Raised when configuration is invalid."""
    pass
