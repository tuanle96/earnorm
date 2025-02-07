"""EarnORM - Async-first ORM for MongoDB and more.

This module provides the main entry point for initializing EarnORM and guides for using models and fields.

Initialization
-------------
The initialization process includes:
1. Loading and validating configuration data from YAML or .env file
2. Creating temporary SystemConfig for DI container
3. Initializing DI container
4. Registering basic services
5. Initializing Environment
6. Creating final SystemConfig
7. Registering remaining services
8. Setting up cleanup handlers for graceful shutdown

Basic initialization examples:
    >>> # Initialize with YAML config
    >>> config = await earnorm.init("config.yaml")
    >>>
    >>> # Initialize with .env file
    >>> config = await earnorm.init(".env")
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

import logging
import signal
from pathlib import Path
from typing import Any, Optional

import yaml

from earnorm.base.env import Environment
from earnorm.base.model.base import BaseModel
from earnorm.config.data import SystemConfigData
from earnorm.config.model import SystemConfig
from earnorm.di import container
from earnorm.exceptions import ConfigError, ConfigValidationError
from earnorm.registry import register_all

logger = logging.getLogger(__name__)


async def init(
    config_path: str | Path,
    *,
    env_file: Optional[str | Path] = None,
    cleanup_handlers: bool = True,
    debug: bool = False,
) -> None:
    """Initialize EarnORM.

    This function initializes EarnORM with the given configuration.
    It performs the following steps:
    1. Load and validate configuration
    2. Initialize DI container
    3. Register basic services
    4. Initialize Environment
    5. Create SystemConfig
    6. Register remaining services
    7. Setup cleanup handlers

    Args:
        config_path: Path to config file (YAML or .env)
        env_file: Optional path to .env file
        cleanup_handlers: Whether to setup cleanup handlers
        debug: Whether to enable debug mode

    Raises:
        ConfigError: If config loading fails
        ConfigValidationError: If config validation fails
        DIError: If DI container initialization fails
        RegistrationError: If service registration fails
        ValueError: If config file path is invalid
        OSError: If file system operations fail
    """
    try:
        # 1. Load and validate config data
        logger.info("Loading config from %s", config_path)
        config_path = Path(config_path) if isinstance(config_path, str) else config_path

        if not config_path.exists():
            raise ValueError(f"Config file not found: {config_path}")

        # Load config data based on file type
        try:
            if config_path.suffix == ".yaml":
                config_data = await SystemConfigData.load_yaml(str(config_path))
            else:
                config_data = await SystemConfigData.load_env(str(config_path))

            # Validate config data
            config_data.validate()
            config_dict = config_data.to_dict()
            logger.debug("Loaded and validated config: %s", config_dict)

        except (ConfigError, yaml.YAMLError, ConfigValidationError) as e:
            raise ConfigError(f"Failed to load or validate config: {e}") from e

        try:
            # 2. Create temporary config for service registration
            config = await SystemConfig.from_data(None, config_data)
            container.register("config", config)

            # 3. Register all services in correct order
            await register_all(config)

            # 4. Initialize Environment with registered services
            env = Environment.get_instance()
            await env.init(config=config_data)

            # 5. Update config with initialized environment
            config = await SystemConfig.from_data(env, config_data)
            container.register("config", config)

        except Exception as e:
            raise ConfigError(
                f"Failed to initialize environment and config: {e}"
            ) from e

        # 6. Setup cleanup handlers
        if cleanup_handlers:
            logger.info("Setting up cleanup handlers")
            try:

                def cleanup(signum: int, frame: Any) -> None:
                    """Cleanup handler for graceful shutdown."""
                    logger.info("Received signal %d, cleaning up...", signum)
                    # To be implemented
                    logger.info("Cleanup complete")

                signal.signal(signal.SIGINT, cleanup)
                signal.signal(signal.SIGTERM, cleanup)
            except Exception as e:
                logger.warning("Failed to setup cleanup handlers: %s", e)

        logger.info("EarnORM initialized successfully")

    except Exception as e:
        logger.error("Failed to initialize EarnORM: %s", str(e))
        raise


__version__ = "0.1.0"
__all__ = ["init", "__version__", "BaseModel"]
