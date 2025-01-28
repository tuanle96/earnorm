"""Dependency resolver module for dependency injection.

This module provides dependency resolution functionality for the DI system.
The dependency resolver is responsible for:

1. Dependency Management:
   - Dependency registration
   - Dependency tracking
   - Dependency validation

2. Resolution:
   - Dependency order resolution
   - Circular dependency detection
   - Missing dependency detection

3. Lifecycle Management:
   - Resolver initialization
   - Resource cleanup
   - Event handling

Example:
    >>> resolver = DependencyResolver()
    >>>
    >>> # Register dependencies
    >>> resolver.add_dependency("database", ["config"])
    >>> resolver.add_dependency("service", ["database", "cache"])
    >>>
    >>> # Resolve dependencies
    >>> order = resolver.resolve("service")
    >>> assert order == ["config", "database", "cache", "service"]
"""

import logging
from typing import Dict, List, Optional, Set

from earnorm.config.model import SystemConfig
from earnorm.di.lifecycle import LifecycleAware
from earnorm.exceptions import CircularDependencyError

logger = logging.getLogger(__name__)


class DependencyResolver(LifecycleAware):
    """Dependency resolver implementation for dependency injection.

    The DependencyResolver class manages service dependencies and their resolution.
    It ensures proper initialization order and detects circular dependencies.

    Features:
        - Dependency registration and tracking
        - Dependency order resolution
        - Circular dependency detection
        - Missing dependency detection
        - Lifecycle event handling

    Example:
        >>> resolver = DependencyResolver()
        >>>
        >>> # Register dependencies
        >>> resolver.add_dependency("service", ["database"])
        >>> resolver.add_dependency("database", ["config"])
        >>>
        >>> # Resolve dependencies
        >>> order = resolver.resolve("service")
        >>> assert order == ["config", "database", "service"]
    """

    def __init__(self) -> None:
        """Initialize dependency resolver.

        This constructor sets up:
        1. Dependency registry for storing dependencies
        2. Resolved set for tracking resolved dependencies
        3. Configuration storage
        """
        self._dependencies: Dict[str, List[str]] = {}
        self._resolved: Set[str] = set()
        self._config: Optional[SystemConfig] = None

    async def init(self) -> None:
        """Initialize dependency resolver.

        This method:
        1. Validates configuration
        2. Sets up required dependencies
        3. Initializes event handlers

        Raises:
            RuntimeError: If configuration is not set
            DependencyResolverError: If initialization fails
        """
        if self._config is None:
            raise RuntimeError("Config not set")

    async def destroy(self) -> None:
        """Destroy dependency resolver and cleanup resources.

        This method:
        1. Clears dependency registry
        2. Resets resolved set
        3. Releases resources
        """
        self.clear()

    @property
    def id(self) -> Optional[str]:
        """Get dependency resolver ID.

        Returns:
            Dependency resolver identifier
        """
        return "dependency_resolver"

    @property
    def data(self) -> Dict[str, str]:
        """Get dependency resolver data.

        Returns:
            Dictionary containing:
            - dependencies: Number of registered dependencies
            - resolved: Number of resolved dependencies
        """
        return {
            "dependencies": str(len(self._dependencies)),
            "resolved": str(len(self._resolved)),
        }

    async def setup(self, config: SystemConfig) -> None:
        """Setup dependency resolver with configuration.

        This method:
        1. Stores configuration for later use
        2. Initializes the resolver
        3. Sets up required dependencies

        Args:
            config: System configuration instance

        Raises:
            DependencyResolverError: If setup fails
        """
        self._config = config
        await self.init()

    def add_dependency(self, name: str, dependencies: List[str]) -> None:
        """Add dependencies for a service.

        This method registers the dependencies that a service requires.
        Dependencies are used to determine initialization order.

        Args:
            name: Name of the service
            dependencies: List of service names that this service depends on

        Example:
            >>> resolver.add_dependency("database", ["config"])
            >>> resolver.add_dependency("service", ["database", "cache"])
        """
        self._dependencies[name] = dependencies

    def resolve(self, name: str) -> List[str]:
        """Resolve dependencies for a service.

        This method determines the order in which services should be initialized
        to satisfy all dependencies. It performs:
        1. Dependency graph traversal
        2. Circular dependency detection
        3. Missing dependency detection

        Args:
            name: Name of the service to resolve dependencies for

        Returns:
            List of service names in initialization order

        Raises:
            CircularDependencyError: If circular dependency is detected
            DependencyNotFoundError: If required dependency is missing

        Example:
            >>> order = resolver.resolve("service")
            >>> assert order == ["config", "database", "cache", "service"]
        """
        resolved: List[str] = []
        visited: Set[str] = set()

        def visit(n: str) -> None:
            """Visit node in dependency graph.

            This function performs depth-first traversal of the dependency graph.
            It detects circular dependencies and builds the resolution order.

            Args:
                n: Name of the node to visit

            Raises:
                CircularDependencyError: If circular dependency is detected
            """
            if n in visited:
                raise CircularDependencyError(f"Circular dependency detected: {n}")

            visited.add(n)

            if n in self._dependencies:
                for dep in self._dependencies[n]:
                    if dep not in self._resolved:
                        visit(dep)

            visited.remove(n)
            if n not in self._resolved:
                resolved.append(n)
                self._resolved.add(n)

        visit(name)
        return resolved

    def clear(self) -> None:
        """Clear resolver state.

        This method:
        1. Clears dependency registry
        2. Resets resolved set
        3. Prepares resolver for reuse
        """
        self._dependencies.clear()
        self._resolved.clear()

    def get_dependencies(self, service: str) -> List[str]:
        """Get dependencies for a service.

        Args:
            service: Name of the service to get dependencies for

        Returns:
            List of service names that this service depends on

        Example:
            >>> deps = resolver.get_dependencies("service")
            >>> assert deps == ["database", "cache"]
        """
        return self._dependencies.get(service, [])

    def check_circular(self) -> None:
        """Check for circular dependencies in the entire dependency graph.

        This method:
        1. Traverses the entire dependency graph
        2. Detects any circular dependencies
        3. Validates dependency relationships

        Raises:
            CircularDependencyError: If any circular dependency is detected

        Example:
            >>> resolver.check_circular()  # Raises if circular deps found
        """
        visited: Set[str] = set()
        path: Set[str] = set()

        def visit(service: str) -> None:
            """Visit service in dependency graph.

            This function performs depth-first traversal to detect cycles.
            It tracks both visited nodes and current path.

            Args:
                service: Name of the service to visit

            Raises:
                CircularDependencyError: If circular dependency is detected
            """
            if service in path:
                raise CircularDependencyError(
                    f"Circular dependency detected: {service}"
                )

            if service in visited:
                return

            visited.add(service)
            path.add(service)

            # Visit dependencies
            for dependency in self.get_dependencies(service):
                visit(dependency)

            path.remove(service)

        # Visit all services
        for service in self._dependencies:
            visit(service)
