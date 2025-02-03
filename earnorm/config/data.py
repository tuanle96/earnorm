"""Config data module.

This module defines the SystemConfigData class that represents system-wide configuration data.
It is used to load and validate configuration before initializing the Environment.

Examples:
    >>> # Load from .env file
    >>> config = await SystemConfigData.load_env(".env")
    >>> print(config.database_uri)

    >>> # Load from YAML file
    >>> config = await SystemConfigData.load_yaml("config.yaml")
    >>> print(config.redis_host)
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Self, TypeVar, Union, cast
from urllib.parse import parse_qs, urlparse

import yaml
from dotenv import load_dotenv

from earnorm.exceptions import ConfigError, ConfigValidationError
from earnorm.fields import BaseField
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.string import StringField

logger = logging.getLogger(__name__)

# Config prefixes
CONFIG_PREFIXES = ("MONGO_", "REDIS_", "CACHE_", "EVENT_")

# Type for config data
ConfigData = Dict[str, Union[str, int, bool]]

# Type variable for SystemConfigData
T = TypeVar("T", bound="SystemConfigData")


def validate_pool_sizes(min_size: Optional[int], max_size: Optional[int]) -> None:
    """Validate pool size configuration.

    Args:
        min_size: Minimum pool size
        max_size: Maximum pool size

    Raises:
        ConfigValidationError: If validation fails
    """
    if min_size is None or max_size is None:
        return

    if min_size > max_size:
        raise ConfigValidationError(
            f"Minimum pool size ({min_size}) cannot be greater than "
            f"maximum pool size ({max_size})"
        )


class SystemConfigData:
    """System configuration data.

    This class represents system-wide configuration with validation rules.
    Config can be loaded from environment variables or YAML files.

    Examples:
        >>> # Load from .env file
        >>> config = await SystemConfigData.load_env(".env")
        >>> print(config.database_uri)

        >>> # Load from YAML file
        >>> config = await SystemConfigData.load_yaml("config.yaml")
        >>> print(config.redis_host)
    """

    # Version and timestamps
    version = StringField(default="1.0.0")
    created_at = DateTimeField(auto_now_add=True, required=False)
    updated_at = DateTimeField(auto_now=True, required=False)

    # Database Configuration
    database_backend = StringField(
        default="mongodb",
        choices=["mongodb", "mysql", "postgres"],
        description="Database backend type",
    )
    database_uri = StringField(
        required=True,
        min_length=10,
        description="Database connection URI",
    )
    database_name = StringField(
        required=True,
        min_length=1,
        max_length=64,
        description="Database name",
    )
    database_username = StringField(
        required=False,
        description="Database username",
    )
    database_password = StringField(
        required=False,
        description="Database password",
    )
    database_min_pool_size = IntegerField(
        default=5,
        min_value=1,
        max_value=100,
        description="Minimum database connection pool size",
    )
    database_max_pool_size = IntegerField(
        default=20,
        min_value=5,
        max_value=1000,
        description="Maximum database connection pool size",
    )
    database_pool_timeout = IntegerField(
        default=30,
        min_value=1,
        max_value=300,
        description="Database connection timeout in seconds",
    )
    database_max_lifetime = IntegerField(
        default=3600,
        min_value=60,
        max_value=86400,  # 24 hours
        description="Maximum connection lifetime in seconds",
    )
    database_idle_timeout = IntegerField(
        default=300,
        min_value=10,
        max_value=3600,
        description="Connection idle timeout in seconds",
    )
    database_ssl = BooleanField(
        default=False,
        description="Whether to use SSL for database connection",
    )
    database_ssl_ca = StringField(
        required=False,
        description="SSL CA certificate path",
    )
    database_ssl_cert = StringField(
        required=False,
        description="SSL certificate path",
    )
    database_ssl_key = StringField(
        required=False,
        description="SSL key path",
    )

    # Redis Configuration
    redis_host = StringField(
        required=True, min_length=1, max_length=255, description="Redis server host"
    )
    redis_port = IntegerField(
        default=6379, min_value=1, max_value=65535, description="Redis server port"
    )
    redis_db = IntegerField(
        default=0, min_value=0, max_value=15, description="Redis database number"
    )
    redis_min_pool_size = IntegerField(
        default=5,
        min_value=1,
        max_value=100,
        description="Minimum Redis connection pool size",
    )
    redis_max_pool_size = IntegerField(
        default=20,
        min_value=5,
        max_value=1000,
        description="Maximum Redis connection pool size",
    )
    redis_pool_timeout = IntegerField(
        default=30,
        min_value=1,
        max_value=300,
        description="Redis connection timeout in seconds",
    )

    # Cache Configuration
    cache_backend = StringField(
        default="redis", choices=["redis", "memory"], description="Cache backend type"
    )
    cache_ttl = IntegerField(
        default=3600,
        min_value=1,
        max_value=86400,  # 24 hours
        description="Default cache TTL in seconds",
    )

    # Event Configuration
    event_enabled = BooleanField(
        default=True,
        description="Whether to enable event system",
    )
    event_queue = StringField(
        default="earnorm:events",
        min_length=1,
        max_length=255,
        description="Event queue name",
    )
    event_batch_size = IntegerField(
        default=100,
        min_value=1,
        max_value=10000,
        description="Event batch size",
    )

    def __init__(self, data: Optional[ConfigData] = None) -> None:
        """Initialize configuration data.

        Args:
            data: Initial configuration data
        """
        self._data = data or {}
        self._fields = self._get_fields()

    @classmethod
    def _get_fields(cls) -> Dict[str, BaseField[Any]]:
        """Get all field definitions.

        Returns:
            Dictionary mapping field names to field instances
        """
        return {
            name: field
            for name, field in cls.__dict__.items()
            if isinstance(field, BaseField)
        }

    def validate(self) -> None:
        """Validate all configuration settings.

        This method runs all validation checks on the configuration:
        - Database configuration (URI, pool sizes, timeouts)
        - Redis configuration (host, port, pool sizes)
        - Cache configuration (backend type, TTL values)

        Raises:
            ConfigValidationError: If any validation check fails
        """
        logger.debug("Starting config validation")

        try:
            self._validate_database_config()
            logger.debug("Database config validation passed")

            self._validate_redis_config()
            logger.debug("Redis config validation passed")

            self._validate_cache_config()
            logger.debug("Cache config validation passed")

        except ConfigValidationError as e:
            logger.error(f"Config validation failed: {str(e)}")
            raise

    def _validate_database_config(self) -> None:
        """Validate database configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        logger.debug("Validating database config")
        logger.debug(f"Database URI: {self._data.get('database_uri')}")
        logger.debug(f"Database name: {self._data.get('database_name')}")
        logger.debug(f"Database options: {self.database_options}")

        # Validate required fields
        if not self._data.get("database_uri"):
            raise ConfigValidationError("Database URI is required")

        if not self._data.get("database_name"):
            raise ConfigValidationError("Database name is required")

        # Validate pool sizes
        min_size = cast(Optional[int], self._data.get("database_min_pool_size"))
        max_size = cast(Optional[int], self._data.get("database_max_pool_size"))
        validate_pool_sizes(min_size, max_size)

        # Validate MongoDB URI format
        if not self.validate_mongodb_uri(str(self._data.get("database_uri"))):
            raise ConfigValidationError(
                f"Invalid MongoDB URI format: {self._data.get('database_uri')}"
            )

        # Validate database options
        self._validate_database_options()

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        logger.debug("Validating Redis config")

        min_size = cast(Optional[int], self._data.get("redis_min_pool_size"))
        max_size = cast(Optional[int], self._data.get("redis_max_pool_size"))
        validate_pool_sizes(min_size, max_size)

    def _validate_cache_config(self) -> None:
        """Validate cache configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        logger.debug("Validating cache config")

        backend = self._data.get("cache_backend")
        if backend == "redis":
            if not self._data.get("redis_host"):
                raise ConfigValidationError(
                    "Redis host is required when using Redis cache backend"
                )

    @staticmethod
    def validate_mongodb_uri(uri: str) -> bool:
        """Validate MongoDB URI format.

        Args:
            uri: MongoDB connection string

        Returns:
            bool: True if valid, False otherwise

        Example URI format:
            mongodb://hostname:port/database?option1=value1&option2=value2
        """
        try:
            result = urlparse(uri)

            # Validate basic URI components
            if not all(
                [
                    result.scheme == "mongodb",
                    result.hostname,
                    result.hostname != "none",
                    result.port,  # Port must be specified
                ]
            ):
                logger.error(
                    "Invalid MongoDB URI components: scheme=%s, hostname=%s, port=%s",
                    result.scheme,
                    result.hostname,
                    result.port,
                )
                return False

            # Parse and validate query params
            params = parse_qs(result.query)

            # Check for recommended params
            recommended_params = ["retryWrites", "retryReads"]
            missing_params = [
                param for param in recommended_params if param not in params
            ]

            if missing_params:
                logger.warning(
                    "Missing recommended MongoDB URI parameters: %s", missing_params
                )

            return True

        except Exception as e:
            logger.error("Failed to validate MongoDB URI: %s", str(e))
            return False

    @classmethod
    async def load_yaml(cls, yaml_file: Union[str, Path]) -> Self:
        """Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            SystemConfig instance

        Raises:
            ConfigError: If loading fails
        """
        try:
            logger.debug(f"Loading config from YAML file: {yaml_file}")

            # Read YAML file
            with open(yaml_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            logger.debug(f"Loaded raw config data: {config_data}")
            logger.debug(f"Database URI type: {type(config_data.get('database_uri'))}")
            logger.debug(f"Database URI value: '{config_data.get('database_uri')}'")
            logger.debug(
                f"Database URI length: {len(str(config_data.get('database_uri')))}"
            )

            # Create config instance
            instance = cls(config_data)
            logger.debug(f"Created config instance with data: {instance._data}")

            return instance

        except Exception as e:
            logger.error(f"Failed to load config from YAML: {str(e)}")
            raise ConfigError(f"Failed to load config from YAML: {e}") from e

    @classmethod
    async def load_env(cls, path: Optional[Union[str, Path]] = None) -> Self:
        """Load configuration from environment variables.

        Args:
            path: Path to .env file (optional)

        Returns:
            Configuration instance

        Raises:
            ConfigError: If .env file not found
        """
        if path:
            try:
                load_dotenv(path)
            except OSError as e:
                raise ConfigError(f"Failed to load .env file: {e}") from e

        data: ConfigData = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                data[key.lower()] = value

        return cls(data)

    def to_dict(self) -> ConfigData:
        """Convert configuration to dictionary.

        Returns:
            Dictionary with configuration values
        """
        return self._data.copy()

    def __getattr__(self, name: str) -> Any:
        """Get configuration value.

        Args:
            name: Configuration key

        Returns:
            Configuration value

        Raises:
            AttributeError: If key not found
        """
        if name in self._fields:
            return self._data.get(name)
        raise AttributeError(f"Configuration has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set configuration value.

        Args:
            name: Configuration key
            value: Configuration value
        """
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif name in self._fields:
            self._data[name] = value
        else:
            raise AttributeError(f"Configuration has no attribute '{name}'")

    @property
    def database_options(self) -> Dict[str, Any]:
        """Get database connection options.

        Returns:
            Dictionary of database connection options
        """
        options = self._data.get("database_options")
        if not isinstance(options, dict):
            return {
                "server_selection_timeout_ms": 5000,
                "connect_timeout_ms": 10000,
                "socket_timeout_ms": 20000,
                "retry_writes": True,
                "retry_reads": True,
                "w": 1,
                "j": True,
            }
        return options

    def _validate_database_options(self) -> None:
        """Validate database connection options.

        Raises:
            ConfigValidationError: If validation fails
        """
        options = self.database_options

        # Validate timeout values
        timeout_fields = [
            "server_selection_timeout_ms",
            "connect_timeout_ms",
            "socket_timeout_ms",
        ]

        for field in timeout_fields:
            value = options.get(field)
            if value is not None and not isinstance(value, int):
                raise ConfigValidationError(
                    f"Invalid {field} value: {value}. Must be an integer"
                )

        # Validate boolean flags
        bool_fields = ["retry_writes", "retry_reads", "j"]
        for field in bool_fields:
            value = options.get(field)
            if value is not None and not isinstance(value, bool):
                raise ConfigValidationError(
                    f"Invalid {field} value: {value}. Must be a boolean"
                )

        # Validate write concern
        w = options.get("w")
        if w is not None and not isinstance(w, (int, str)):
            raise ConfigValidationError(
                f"Invalid write concern (w) value: {w}. Must be an integer or string"
            )
