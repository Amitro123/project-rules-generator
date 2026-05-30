"""ProjectProfile exceptions."""

from __future__ import annotations


class InvariantViolation(Exception):
    """Raised when a ProjectProfile's invariants fail validation.

    Each violation message includes the failing invariant name (e.g.
    ``skill_set_disk_mismatch``) so callers can route the error or print
    a remediation hint without parsing the message body.
    """

    def __init__(self, invariant: str, message: str) -> None:
        super().__init__(f"[{invariant}] {message}")
        self.invariant = invariant
        self.message = message
