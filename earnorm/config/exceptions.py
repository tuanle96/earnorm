"""Config module exceptions.

This module contains custom exceptions used by the config module.
"""


class ConfigError(Exception):
    """Base class for config module exceptions."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when config validation fails."""

    pass


class ConfigEncryptionError(ConfigError):
    """Raised when encryption/decryption fails."""

    pass


class ConfigMigrationError(ConfigError):
    """Raised when config migration fails."""

    pass


class ConfigBackupError(ConfigError):
    """Raised when config backup/restore fails."""

    pass
