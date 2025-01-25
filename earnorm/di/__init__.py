"""Dependency injection module for EarnORM."""

from typing import Any, Optional

from earnorm.di.container.base import Container
from earnorm.di.container.factory import FactoryManager
from earnorm.di.container.service import ServiceManager
from earnorm.di.lifecycle import LifecycleAware, LifecycleEvents, LifecycleManager
from earnorm.di.resolver.dependency import CircularDependencyError, DependencyResolver
from earnorm.pool.registry import PoolRegistry

# Create global container instance
container = Container()

# Initialize managers
container.register("service_manager", ServiceManager())
container.register("factory_manager", FactoryManager())
container.register("lifecycle_manager", LifecycleManager())
container.register("dependency_resolver", DependencyResolver())
container.register("pool_registry", PoolRegistry())

# Export commonly used instances
lifecycle: Optional[LifecycleManager] = None


async def init_container(**config: Any) -> None:
    """Initialize container and managers.

    Args:
        **config: Configuration options
            - cache: Cache configuration
                - enabled: Whether cache is enabled
                - ttl: Default TTL in seconds
                - backend: Cache backend type (redis)
                - host: Cache host
                - port: Cache port
                - db: Cache database
                - min_size: Minimum pool size
                - max_size: Maximum pool size
                - timeout: Connection timeout
                - max_lifetime: Maximum connection lifetime
                - idle_timeout: Connection idle timeout
                - validate_on_borrow: Whether to validate connections on borrow
                - test_on_return: Whether to test connections on return
    """
    global lifecycle

    # Initialize container
    await container.init(**config)

    # Get lifecycle manager
    lifecycle = await container.get("lifecycle_manager")


__all__ = [
    "container",
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
    "CircularDependencyError",
    # Global instances
    "container",
    "lifecycle",
    # Functions
    "init_container",
]
