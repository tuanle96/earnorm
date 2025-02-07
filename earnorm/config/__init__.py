"""Config module for EarnORM.

This module provides configuration management functionality for the EarnORM framework.
It handles loading, validating and storing system-wide configuration settings.

Key Features:
    1. Configuration Management
       - Load from environment variables (.env)
       - Load from YAML files
       - Validation rules and type checking
       - Default values and required fields
       - Configuration versioning

    2. Database Configuration
       - Multiple database backends (MongoDB, MySQL, PostgreSQL)
       - Connection pooling and timeouts
       - SSL/TLS support
       - Authentication
       - Connection options

    3. Redis Configuration
       - Connection settings
       - Pool management
       - Database selection
       - Authentication

    4. Event System Configuration
       - Event queue settings
       - Batch processing
       - Event handlers
       - Error handling

Examples:
    >>> from earnorm.config import SystemConfig
    >>> from earnorm.di import container

    >>> # Load from .env file
    >>> config = SystemConfig.load_env(".env")
    >>> print(config.database_uri)

    >>> # Load from YAML
    >>> config = SystemConfig.load_yaml("config.yaml")
    >>> print(config.redis_host)

    >>> # Register in DI container
    >>> container.register("config", config)

Classes:
    SystemConfig:
        Main configuration class with validation rules.
        Supports loading from environment variables and YAML files.

Implementation Notes:
    1. Configuration Loading
       - Environment variables take precedence
       - Supports multiple config formats
       - Handles missing values
       - Provides defaults

    2. Validation Rules
       - Type checking
       - Value constraints
       - Required fields
       - Cross-field validation

    3. Security
       - Sensitive data handling
       - SSL/TLS configuration
       - Authentication credentials
       - Access control

See Also:
    - earnorm.di: Dependency injection system
    - earnorm.database: Database adapters
    - earnorm.env: Environment management
"""

from earnorm.config.model import SystemConfig

__all__ = [
    # Main config class
    "SystemConfig",
]
