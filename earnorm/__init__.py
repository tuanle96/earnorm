"""EarnORM - Async-first ORM for MongoDB and more.

This module provides the main entry point for initializing EarnORM and guides for using models and fields.

Initialization
-------------
The initialization process includes:
1. Loading and validating configuration from YAML or .env file
2. Initializing the Dependency Injection container
3. Registering core services (database, cache, etc.)
4. Setting up cleanup handlers for graceful shutdown

Basic initialization examples:
    >>> # Initialize with YAML config
    >>> config = await earnorm.init("config.yaml")
    >>>
    >>> # Initialize with .env file and custom prefix
    >>> config = await earnorm.init(".env", env_prefix="APP_")
    >>>
    >>> # Initialize without auto cleanup
    >>> config = await earnorm.init("config.yaml", auto_cleanup=False)

Model Definition
--------------
Models are defined by inheriting from BaseModel and declaring fields:

    >>> from earnorm.base import BaseModel
    >>> from earnorm.fields.primitive import StringField, IntegerField, DateTimeField
    >>>
    >>> class User(BaseModel):
    ...     # Collection configuration
    ...     _collection = "users"  # MongoDB collection name
    ...     _name = "user"        # Model name for registry
    ...
    ...     # Collection indexes
    ...     indexes = [
    ...         {"keys": [("email", 1)], "unique": True},
    ...         {"keys": [("created_at", -1)]},
    ...     ]
    ...
    ...     # Fields
    ...     email = StringField(required=True, min_length=5, max_length=255)
    ...     name = StringField(required=True, min_length=2, max_length=100)
    ...     age = IntegerField(min_value=0, max_value=150)
    ...     created_at = DateTimeField(auto_now_add=True)
    ...     updated_at = DateTimeField(auto_now=True)

Field Types
----------
EarnORM provides various field types for different data types:

Primitive Fields:
    - StringField: For text data
    - IntegerField: For integer numbers
    - FloatField: For floating point numbers
    - BooleanField: For boolean values
    - DateTimeField: For datetime values
    - DecimalField: For precise decimal numbers
    - ObjectIdField: For MongoDB ObjectId values

Relationship Fields:
    - ReferenceField: For references to other models
    - ListField: For arrays/lists of values
    - DictField: For nested dictionary objects
    - EmbeddedField: For embedded documents

Field Options:
    - required: Whether field is required (default: False)
    - default: Default value if not provided
    - choices: List of valid choices
    - min_length/max_length: For string length validation
    - min_value/max_value: For number range validation
    - regex: Regular expression pattern for string validation
    - auto_now_add: Auto set current time on creation
    - auto_now: Auto update time on modification

Model Operations
--------------
Basic CRUD operations:

    >>> # Create
    >>> user = User(email="user@example.com", name="John Doe", age=30)
    >>> await user.save()
    >>>
    >>> # Read
    >>> user = await User.get_by_id("user_id")
    >>> users = await User.search({"age": {"$gte": 18}})
    >>>
    >>> # Update
    >>> user.name = "Jane Doe"
    >>> await user.save()
    >>>
    >>> # Delete
    >>> await user.delete()

Validation
---------
Models and fields are automatically validated:

    >>> # Validation on creation
    >>> try:
    ...     user = User(email="invalid", name="")  # Will raise ValidationError
    ... except ValidationError as e:
    ...     print(e)
    >>>
    >>> # Validation before save
    >>> user = User(email="user@example.com", name="John")
    >>> user.age = -1  # Will raise ValidationError on save
    >>> await user.save()

Configuration
-----------
Example YAML configuration:

    ```yaml
    # Database Configuration
    database_backend: "mongodb"
    database_uri: "mongodb://localhost:27017"
    database_name: "myapp"
    database_min_pool_size: 5
    database_max_pool_size: 20

    # Redis Configuration (for caching)
    redis_host: "localhost"
    redis_port: 6379
    redis_db: 0

    # Cache Configuration
    cache_backend: "redis"
    cache_ttl: 3600
    ```

For more details, refer to the documentation at https://earnorm.readthedocs.io
"""

import atexit
import logging
from pathlib import Path

import yaml

from earnorm.config import SystemConfig
from earnorm.di import container, init_container
from earnorm.exceptions import (
    CleanupError,
    ConfigError,
    ConfigValidationError,
    DIError,
    RegistrationError,
)
from earnorm.registry import register_all

logger = logging.getLogger(__name__)


async def init(
    config_path: str | Path,
    *,
    env_prefix: str = "EARNORM_",
    validate_config: bool = True,
    auto_cleanup: bool = True,
) -> SystemConfig:
    """Initialize EarnORM with the provided configuration.

    This function serves as the main entry point for initializing EarnORM. It performs
    the following steps in order:
    1. Loads configuration from the specified file (YAML or .env)
    2. Initializes the Dependency Injection container
    3. Registers all required services
    4. Sets up cleanup handlers for graceful shutdown

    Args:
        config_path: Path to config file, can be either a YAML or .env file.
                    Both string paths and Path objects are supported.
        env_prefix: Prefix for environment variables when using .env file.
                   Only used when loading from .env file.
                   Defaults to "EARNORM_".
        validate_config: Whether to validate the loaded configuration.
                        This is passed to load_yaml/load_env.
                        Defaults to True.
        auto_cleanup: Whether to register cleanup handlers for graceful shutdown.
                     Set to False if you want to handle cleanup manually.
                     Defaults to True.

    Returns:
        SystemConfig: The loaded and validated configuration object.
                     This can be used to access configuration values
                     throughout your application.

    Raises:
        ConfigError: If configuration loading fails (file not found, invalid format)
        ConfigValidationError: If configuration validation fails
        DIError: If dependency injection container initialization fails
        RegistrationError: If service registration fails
        CleanupError: If cleanup process fails
        ValueError: If config file path is invalid
        OSError: If file system operations fail
    """
    try:
        # 1. Load config
        logger.info("Loading config from %s", config_path)
        config_path = Path(config_path) if isinstance(config_path, str) else config_path

        try:
            if not config_path.exists():
                raise ValueError(f"Config file not found: {config_path}")
        except OSError as e:
            raise ValueError(f"Invalid config path: {config_path}") from e

        try:
            # Load and create config based on file type
            if config_path.suffix == ".yaml":
                config = await SystemConfig.load_yaml(
                    str(config_path), validate=validate_config
                )
            else:
                config = await SystemConfig.load_env(
                    str(config_path), prefix=env_prefix, validate=validate_config
                )
        except (ConfigError, yaml.YAMLError) as e:
            raise ConfigError(f"Failed to load config from {config_path}: {e}") from e

        # 2. Initialize DI container
        logger.info("Initializing DI container")
        try:
            await init_container(config=config)
        except DIError as e:
            raise DIError(f"Failed to initialize DI container: {e}") from e

        # 3. Register all services
        logger.info("Registering services")
        try:
            await register_all(config)
        except RegistrationError as e:
            raise RegistrationError(f"Failed to register services: {e}") from e

        # 4. Setup cleanup if requested
        if auto_cleanup:
            logger.debug("Setting up cleanup handlers")

            async def cleanup():
                """Cleanup all resources on shutdown."""
                try:
                    logger.info("Cleaning up resources")
                    lifecycle = await container.get("lifecycle_manager")
                    await lifecycle.destroy_all()
                except Exception as e:
                    logger.error("Error during cleanup: %s", e)
                    raise CleanupError(f"Failed to cleanup resources: {e}") from e

            atexit.register(cleanup)

        logger.info("EarnORM initialized successfully")
        return config

    except (
        ConfigError,
        ConfigValidationError,
        DIError,
        RegistrationError,
        ValueError,
        OSError,
    ) as e:
        logger.error("Failed to initialize EarnORM: %s", e)

        # Try to cleanup any partially initialized resources
        try:
            lifecycle = await container.get("lifecycle_manager")
            await lifecycle.destroy_all()
        except Exception as cleanup_error:  # pylint: disable=broad-except
            logger.error(
                "Error during cleanup after failed initialization: %s", cleanup_error
            )
            if not isinstance(e, CleanupError):
                raise CleanupError(
                    f"Failed to cleanup after initialization error: {cleanup_error}"
                ) from cleanup_error

        # Re-raise the original error
        raise


__version__ = "0.1.0"
__all__ = ["init", "__version__"]
