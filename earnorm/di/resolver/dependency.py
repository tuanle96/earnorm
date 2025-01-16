"""Dependency resolution."""

import logging
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


class DependencyResolver:
    """Dependency resolver."""

    def __init__(self) -> None:
        """Initialize resolver."""
        self._dependencies: Dict[str, Set[str]] = {}

    def add_dependency(self, service: str, depends_on: str) -> None:
        """Add dependency."""
        if service not in self._dependencies:
            self._dependencies[service] = set()
        self._dependencies[service].add(depends_on)

    def get_dependencies(self, service: str) -> Set[str]:
        """Get service dependencies."""
        return self._dependencies.get(service, set())

    def resolve_order(self) -> List[str]:
        """Resolve dependency order."""
        resolved: List[str] = []
        visited: Set[str] = set()

        def visit(service: str) -> None:
            """Visit service in dependency graph."""
            if service in visited:
                return

            visited.add(service)

            # Visit dependencies first
            for dependency in self.get_dependencies(service):
                visit(dependency)

            resolved.append(service)

        # Visit all services
        for service in self._dependencies:
            visit(service)

        return resolved

    def check_circular(self) -> None:
        """Check for circular dependencies."""
        visited: Set[str] = set()
        path: Set[str] = set()

        def visit(service: str) -> None:
            """Visit service in dependency graph."""
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

    async def init(self, **config: Any) -> None:
        """Initialize resolver."""
        # No initialization needed for now
        pass


class CircularDependencyError(Exception):
    """Circular dependency error."""

    def __init__(self, message: str) -> None:
        """Initialize error."""
        self.message = message
        super().__init__(message)
