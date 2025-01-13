"""Service providers for EarnORM."""

from typing import Any, Dict

from dependency_injector import providers

from ..base.pool import MongoPoolManager
from ..base.schema import SchemaManager
from ..cache.manager import CacheManager
from ..metrics.manager import MetricsManager
from ..security.acl import ACLManager
from ..security.audit import AuditManager
from ..security.encryption import EncryptionManager
from ..security.rbac import RBACManager
from ..security.rules import RuleManager
from .lifecycle import lifecycle_manager


class ServiceProvider:
    """Service provider for EarnORM.

    Manages service registration and resolution.
    """

    def __init__(self) -> None:
        """Initialize service provider."""
        self._services: Dict[str, Any] = {
            # Core services
            "pool_manager": MongoPoolManager,
            "schema_manager": SchemaManager,
            "cache_manager": CacheManager,
            "metrics_manager": MetricsManager,
            # Security services
            "acl_manager": ACLManager,
            "rbac_manager": RBACManager,
            "rule_manager": RuleManager,
            "audit_manager": AuditManager,
            "encryption_manager": EncryptionManager,
        }
        self._instances: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register service.

        Args:
            name: Service name
            service: Service class or instance
        """
        self._services[name] = service

    async def get(self, name: str) -> Any:
        """Get service instance.

        Args:
            name: Service name

        Returns:
            Service instance

        Raises:
            KeyError: If service not found
        """
        # Return cached instance if exists
        if name in self._instances:
            return self._instances[name]

        # Get service class
        service_class = self._services[name]

        # Create instance
        instance = providers.Singleton(service_class)

        # Initialize service
        await lifecycle_manager.init_service(instance)

        # Cache instance
        self._instances[name] = instance

        return instance

    def has(self, name: str) -> bool:
        """Check if service exists.

        Args:
            name: Service name

        Returns:
            True if service exists
        """
        return name in self._services

    async def start_all(self) -> None:
        """Start all services."""
        for instance in self._instances.values():
            await lifecycle_manager.start_service(instance)

    async def stop_all(self) -> None:
        """Stop all services."""
        for instance in self._instances.values():
            await lifecycle_manager.stop_service(instance)

    async def cleanup_all(self) -> None:
        """Clean up all services."""
        for instance in self._instances.values():
            await lifecycle_manager.cleanup_service(instance)
        self._instances.clear()


# Global provider instance
provider = ServiceProvider()
