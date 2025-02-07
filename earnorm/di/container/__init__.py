"""Container module for dependency injection.

This module provides the core dependency injection container functionality for EarnORM.
It includes:

1. Container System:
   - Service registration and retrieval
   - Factory registration and management
   - Lifecycle management
   - Dependency resolution

2. Service Management:
   - Service registration with lifecycles
   - Singleton and transient services
   - Service initialization
   - Instance caching
   - Resource cleanup

3. Factory Support:
   - Factory function registration
   - Factory-based instance creation
   - Async factory support
   - Factory configuration
   - Factory validation

4. Dependency Resolution:
   - Service dependency tracking
   - Circular dependency detection
   - Dependency order resolution
   - Dependency validation

Examples:
    >>> from earnorm.di.container import Container
    >>> from earnorm.config import SystemConfig

    >>> # Create and initialize container
    >>> container = Container()
    >>> config = SystemConfig()
    >>> await container.init(config)

    >>> # Register services
    >>> container.register("service", MyService())
    >>> container.register_factory("factory", create_service)

    >>> # Get services
    >>> service = await container.get("service")
    >>> factory = await container.get("factory")

See Also:
    - earnorm.di.lifecycle: Lifecycle management
    - earnorm.di.resolver: Dependency resolution
    - earnorm.config: Configuration management
"""

from earnorm.di.container.base import Container
from earnorm.di.container.factory import FactoryManager
from earnorm.di.container.interfaces import ContainerInterface
from earnorm.di.container.service import ServiceManager

__all__ = [
    # Container
    "Container",
    "ContainerInterface",
    # Managers
    "ServiceManager",
    "FactoryManager",
]
