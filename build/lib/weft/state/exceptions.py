"""Feature state-related exceptions."""


class StateError(Exception):
    """Base exception for feature state operations."""

    pass


class InvalidTransitionError(StateError):
    """Raised when attempting an invalid state transition."""

    pass


class StateFileError(StateError):
    """Raised when state file operations fail."""

    pass
