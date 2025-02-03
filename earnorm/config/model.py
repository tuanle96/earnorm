"""System configuration model.

This module provides the SystemConfig model for storing system-wide configuration.

Examples:
    >>> from earnorm.di import container
    >>> config = container.get("config")
    >>> print(config.mongodb_uri)
    >>> config.redis_host = "localhost"
    >>> config.save_yaml("config.yaml")
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationInfo, field_validator

logger = logging.getLogger(__name__)

# Config prefixes
CONFIG_PREFIXES = ("MONGO_", "REDIS_", "CACHE_", "EVENT_")

# Type for config data
ConfigData = Dict[str, Union[str, int, bool]]


class SystemConfig(BaseModel):
    """System configuration model.

    This model represents system-wide configuration with validation rules.
    Config can be loaded from environment variables or YAML files.

    Examples:
        >>> # Load from .env file
        >>> config = SystemConfig.load_env(".env")
        >>> print(config.database_uri)

        >>> # Load from YAML file
        >>> config = SystemConfig.load_yaml("config.yaml")
        >>> print(config.redis_host)
    """

    # Version and timestamps
    version: str = Field(default="1.0.0")
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)

    # Database Configuration
    database_backend: str = Field(default="mongodb")
    database_uri: str = Field(...)  # Required field
    database_name: str = Field(...)  # Required field
    database_username: Optional[str] = Field(default=None)
    database_password: Optional[str] = Field(default=None)
    database_options: Dict[str, Any] = Field(
        default_factory=lambda: {
            "server_selection_timeout_ms": 5000,
            "connect_timeout_ms": 10000,
            "socket_timeout_ms": 20000,
            "retry_writes": True,
            "retry_reads": True,
            "w": 1,
            "j": True,
        }
    )

    # Pool Configuration
    min_pool_size: Optional[int] = Field(default=None)
    max_pool_size: Optional[int] = Field(default=None)

    # Redis Configuration
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)
    redis_min_pool_size: int = Field(default=1)
    redis_max_pool_size: int = Field(default=10)
    redis_pool_timeout: int = Field(default=10)

    # Cache Configuration
    cache_backend: str = Field(default="redis")
    cache_prefix: str = Field(default="earnorm")
    cache_ttl: int = Field(default=3600)

    # Event Configuration
    event_backend: str = Field(default="redis")
    event_prefix: str = Field(default="earnorm")

    @field_validator("database_uri")
    @classmethod
    def validate_database_uri(cls, v: str) -> str:
        """Validate database URI format.

        Args:
            v: Database URI

        Returns:
            Validated URI

        Raises:
            ValueError: If URI format is invalid
        """
        import re

        if not re.match(r"^(mongodb|mysql|postgres)://[^/\s]+(/[^/\s]*)?$", v):
            raise ValueError("Invalid database URI format")
        return v

    @field_validator("min_pool_size", "max_pool_size")
    @classmethod
    def validate_pool_sizes(
        cls, v: Optional[int], info: ValidationInfo
    ) -> Optional[int]:
        """Validate pool size configuration.

        Args:
            v: Pool size value
            info: Validation info

        Returns:
            Validated pool size

        Raises:
            ValueError: If validation fails
        """
        if v is None:
            return v

        min_size = info.data.get("min_pool_size")
        max_size = info.data.get("max_pool_size")

        if min_size is not None and max_size is not None and min_size > max_size:
            raise ValueError(
                f"Minimum pool size ({min_size}) cannot be greater than "
                f"maximum pool size ({max_size})"
            )

        return v

    @classmethod
    def load_env(cls, env_file: Optional[Union[str, Path]] = None) -> "SystemConfig":
        """Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file

        Returns:
            SystemConfig instance

        Examples:
            >>> config = SystemConfig.load_env(".env")
            >>> print(config.database_uri)
        """
        # Load .env file if provided
        if env_file:
            load_dotenv(env_file)

        # Get all environment variables with config prefixes
        config_data: Dict[str, Any] = {}
        for key, value in os.environ.items():
            if any(key.startswith(prefix) for prefix in CONFIG_PREFIXES):
                config_key = key.lower()
                config_data[config_key] = value

        # Create config instance
        return cls(**config_data)

    @classmethod
    def load_yaml(cls, yaml_file: Union[str, Path]) -> "SystemConfig":
        """Load configuration from YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            SystemConfig instance

        Examples:
            >>> config = SystemConfig.load_yaml("config.yaml")
            >>> print(config.redis_host)
        """
        # Read YAML file
        with open(yaml_file) as f:
            config_data = yaml.safe_load(f)

        # Create config instance
        return cls(**config_data)

    def save_yaml(self, yaml_file: Union[str, Path]) -> None:
        """Save configuration to YAML file.

        Args:
            yaml_file: Path to YAML file

        Examples:
            >>> config = SystemConfig.load_env()
            >>> config.save_yaml("config.yaml")
        """
        # Convert to dictionary
        config_data = self.model_dump()

        # Write YAML file
        with open(yaml_file, "w") as f:
            yaml.safe_dump(config_data, f)

    @classmethod
    async def from_data(cls, env: Any, config_data: Any) -> "SystemConfig":
        """Create SystemConfig instance from environment and config data.

        Args:
            env: Environment instance
            config_data: Configuration data object or dictionary

        Returns:
            SystemConfig instance

        Examples:
            >>> env = Environment()
            >>> config_data = {"database_uri": "mongodb://localhost:27017"}
            >>> config = await SystemConfig.from_data(env, config_data)
        """
        logger.debug("Creating SystemConfig from data: %s", config_data)

        # Convert config_data to dictionary if it's not already
        if hasattr(config_data, "_data"):
            config_dict = config_data._data
        elif hasattr(config_data, "model_dump"):
            config_dict = config_data.model_dump()
        else:
            config_dict = dict(config_data)

        # Convert database options if needed
        if "database_options" in config_dict and isinstance(
            config_dict["database_options"], str
        ):
            try:
                config_dict["database_options"] = yaml.safe_load(
                    config_dict["database_options"]
                )
            except Exception as e:
                logger.error("Failed to parse database options: %s", e)
                config_dict["database_options"] = {}

        # Create instance
        instance = cls(**config_dict)

        # Additional validation can be added here
        logger.debug("Created SystemConfig instance: %s", instance)

        return instance
