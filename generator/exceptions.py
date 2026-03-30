"""Custom exceptions for the project-rules-generator."""


class PRGError(Exception):
    """Base exception for all PRG errors."""

    pass


class ValidationError(PRGError):
    """Raised when input validation fails."""

    pass


class FileOperationError(PRGError):
    """Raised when file operations fail."""

    pass


class SecurityError(PRGError):
    """Raised when a security constraint is violated (e.g. path traversal)."""

    pass
