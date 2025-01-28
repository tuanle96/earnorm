"""Config model module.

This module defines the SystemConfig model that represents system-wide configuration.
It follows the singleton pattern - only one instance exists in the database.

Examples:
    >>> from earnorm.di import container
    >>> config = container.get("config")
    >>> print(config.mongodb_uri)
    >>> config.redis_host = "localhost"
    >>> await config.write({"redis_host": "localhost"})
"""

import logging
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional, Self, TypeVar, Union

import yaml
from dotenv import load_dotenv

from earnorm.base import BaseModel
from earnorm.exceptions import ConfigError, ConfigValidationError
from earnorm.fields.primitive.boolean import BooleanField
from earnorm.fields.primitive.datetime import DateTimeField
from earnorm.fields.primitive.number import IntegerField
from earnorm.fields.primitive.string import StringField

logger = logging.getLogger(__name__)

# Config prefixes
CONFIG_PREFIXES = ("MONGO_", "REDIS_", "CACHE_", "EVENT_")

# Type for config data
ConfigData = Dict[str, Union[str, int, bool]]

# Type variable for SystemConfig
T = TypeVar("T", bound="SystemConfig")


def validate_pool_sizes(min_size: int, max_size: int) -> None:
    """Validate pool size configuration.

    Args:
        min_size: Minimum pool size
        max_size: Maximum pool size

    Raises:
        ConfigValidationError: If validation fails
    """
    if min_size > max_size:
        raise ConfigValidationError(
            f"Minimum pool size ({min_size}) cannot be greater than "
            f"maximum pool size ({max_size})"
        )


class SystemConfig(BaseModel):
    """System configuration model.

    This model represents system-wide configuration with validation rules.
    Config can be loaded from environment variables or YAML files.

    Examples:
        >>> # Load from .env file
        >>> config = await SystemConfig.load_env(".env")
        >>> print(config.database_uri)

        >>> # Load from YAML file
        >>> config = await SystemConfig.load_yaml("config.yaml")
        >>> print(config.redis_host)
    """

    # Collection configuration
    _name = "system_config"

    # Singleton instance
    _instance: ClassVar[Optional["SystemConfig"]] = None

    # Version and timestamps
    version = StringField(default="1.0.0")
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

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

    def __init__(self, **data: Any) -> None:
        """Initialize config instance."""
        super().__init__(**data)

    def validate(self) -> None:
        """Validate all configuration settings.

        This method runs all validation checks on the configuration:
        - Database configuration (URI, pool sizes, timeouts)
        - Redis configuration (host, port, pool sizes)
        - Cache configuration (backend type, TTL values)

        Raises:
            ConfigValidationError: If any validation check fails
        """
        self._validate_database_config()
        self._validate_redis_config()
        self._validate_cache_config()

    @property
    def database(self) -> Dict[str, Any]:
        """Get database configuration.

        Returns:
            Dictionary with database configuration
        """
        return {
            "backend_type": self.database_backend,
            "uri": self.database_uri,
            "database": self.database_name,
            "username": self.database_username,
            "password": self.database_password,
            "pool_size": self.database_max_pool_size,
            "pool_timeout": self.database_pool_timeout,
            "max_lifetime": self.database_max_lifetime,
            "idle_timeout": self.database_idle_timeout,
            "ssl": self.database_ssl,
            "ssl_ca": self.database_ssl_ca,
            "ssl_cert": self.database_ssl_cert,
            "ssl_key": self.database_ssl_key,
        }

    @property
    def redis(self) -> Dict[str, Any]:
        """Get Redis configuration.

        Returns:
            Dictionary with Redis configuration
        """
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "min_pool_size": self.redis_min_pool_size,
            "max_pool_size": self.redis_max_pool_size,
            "pool_timeout": self.redis_pool_timeout,
        }

    @property
    def cache(self) -> Dict[str, Any]:
        """Get cache configuration.

        Returns:
            Dictionary with cache configuration
        """
        return {
            "backend": self.cache_backend,
            "ttl": self.cache_ttl,
        }

    def _validate_database_config(self) -> None:
        """Validate database configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        if (
            self.database_min_pool_size is not None
            and self.database_max_pool_size is not None
        ):
            validate_pool_sizes(
                self.database_min_pool_size, self.database_max_pool_size
            )

    def _validate_redis_config(self) -> None:
        """Validate Redis configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        if (
            self.redis_min_pool_size is not None
            and self.redis_max_pool_size is not None
        ):
            validate_pool_sizes(self.redis_min_pool_size, self.redis_max_pool_size)

    def _validate_cache_config(self) -> None:
        """Validate cache configuration.

        Raises:
            ConfigValidationError: If validation fails
        """
        if self.cache_backend == "redis":
            if not self.redis_host:
                raise ConfigValidationError(
                    "Redis host is required for Redis cache backend"
                )

    @classmethod
    async def load_env(cls, env_file: Optional[Union[str, Path]] = None) -> Self:
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            SystemConfig instance

        Raises:
            ConfigError: If failed to load configuration
        """
        try:
            # Load environment variables from file
            if env_file:
                load_dotenv(env_file)

            # Get all environment variables with config prefixes
            config_data: ConfigData = {}
            for key, value in os.environ.items():
                if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                    config_data[key.lower()] = value

            # Create config instance
            return await cls.create(values=config_data)
        except Exception as e:
            raise ConfigError("Failed to load configuration from environment") from e

    @classmethod
    async def load_yaml(cls, yaml_file: Union[str, Path]) -> Self:
        """Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            SystemConfig instance

        Raises:
            ConfigError: If failed to load configuration
        """
        try:
            # Load YAML file
            with open(yaml_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)

            # Create config instance
            return await cls.create(**config_data)
        except Exception as e:
            raise ConfigError("Failed to load configuration from YAML file") from e
