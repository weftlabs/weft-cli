"""Configuration error classes for Weft."""


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


class SecurityError(Exception):
    """Raised when security violations are detected in configuration."""

    pass
