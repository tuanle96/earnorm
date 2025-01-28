"""Dependency Injection module for EarnORM.

This module provides a comprehensive dependency injection system for EarnORM.
It includes:

1. Container System:
   - Service registration and retrieval
   - Factory registration and management
   - Lifecycle management
   - Dependency resolution

2. Lifecycle Management:
   - Object initialization
   - Resource cleanup
   - Event handling

3. Service Management:
   - Singleton and transient lifecycles
   - Async initialization support
   - Caching mechanism

4. Factory Management:
   - Factory function registration
   - Instance creation
   - Async factory support

5. Dependency Resolution:
   - Circular dependency detection
   - Dependency order resolution
   - Dependency validation

Example:
    >>> from earnorm.di import container, init_container
    >>> from earnorm.config import SystemConfig

    >>> # Initialize container with config
    >>> config = SystemConfig()
    >>> await init_container(config)

    >>> # Register services
    >>> container.register("my_service", MyService())
    >>> container.register_factory("my_factory", create_service)

    >>> # Get services
    >>> service = await container.get("my_service")
    >>> factory_service = await container.get("my_factory")
"""

from earnorm.config.model import SystemConfig
from earnorm.di.container.base import Container, ContainerInterface
from earnorm.di.container.factory import FactoryManager
from earnorm.di.container.service import ServiceManager
from earnorm.di.lifecycle import LifecycleAware, LifecycleEvents, LifecycleManager
from earnorm.di.resolver.dependency import DependencyResolver
from earnorm.pool.registry import PoolRegistry

# Global container instance
container: ContainerInterface = Container()

# Initialize managers
container.register("service_manager", ServiceManager())
container.register("factory_manager", FactoryManager())
container.register("lifecycle_manager", LifecycleManager())
container.register("dependency_resolver", DependencyResolver())
container.register("pool_registry", PoolRegistry())

# Global lifecycle manager instance
lifecycle: LifecycleManager | None = None


async def init_container(config: SystemConfig) -> None:
    """Initialize the dependency injection container and all managers.

    This function performs the following steps:
    1. Initializes the global container with the provided configuration
    2. Sets up all registered managers (service, factory, lifecycle)
    3. Configures the dependency resolver
    4. Prepares the connection pool registry

    Args:
        config: System configuration instance containing all necessary settings

    Raises:
        DIError: If container initialization fails
        ServiceInitializationError: If service initialization fails
        FactoryError: If factory initialization fails
        EventError: If event system initialization fails
        CircularDependencyError: If circular dependencies are detected

    Example:
        >>> config = SystemConfig()
        >>> await init_container(config)
        >>> assert container.has("service_manager")
    """
    global lifecycle  # pylint: disable=global-statement

    # Initialize container
    await container.init(config=config)

    # Get lifecycle manager
    lifecycle = await container.get("lifecycle_manager")


__all__ = [
    # Container
    "Container",
    "ServiceManager",
    "FactoryManager",
    # Lifecycle
    "LifecycleAware",
    "LifecycleEvents",
    "LifecycleManager",
    # Resolver
    "DependencyResolver",
    # Global instances
    "container",
    "lifecycle",
    # Functions
    "init_container",
]
