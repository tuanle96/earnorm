"""Type definitions for DI container."""

from typing import Any, Dict, Protocol, runtime_checkable

__all__ = [
    "BaseManager",
    "MongoPoolManager",
    "CacheManager",
    "MetricsManager",
    "AclManager",
    "RbacManager",
    "RuleManager",
    "AuditManager",
    "EncryptionManager",
]


@runtime_checkable
class BaseManager(Protocol):
    """Base protocol for all managers."""

    async def init(self) -> None:
        """Initialize manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up manager."""
        ...


@runtime_checkable
class MongoPoolManager(Protocol):
    """Protocol for MongoDB pool manager."""

    async def init(self) -> None:
        """Initialize pool manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up pool manager."""
        ...

    def get_database(self, database: str) -> Any:
        """Get database instance."""
        ...

    def get_collection(self, collection: str) -> Any:
        """Get collection instance."""
        ...


@runtime_checkable
class CacheManager(Protocol):
    """Protocol for cache manager."""

    async def init(self) -> None:
        """Initialize cache manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up cache manager."""
        ...

    def get_cache(self, name: str) -> Any:
        """Get cache instance."""
        ...


@runtime_checkable
class MetricsManager(Protocol):
    """Protocol for metrics manager."""

    async def init(self) -> None:
        """Initialize metrics manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up metrics manager."""
        ...

    def track_operation(self, operation: str, duration: float) -> None:
        """Track operation metrics."""
        ...


@runtime_checkable
class AclManager(Protocol):
    """Protocol for ACL manager."""

    async def init(self) -> None:
        """Initialize ACL manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up ACL manager."""
        ...

    def check_access(self, user: Any, resource: str, action: str) -> bool:
        """Check if user has access to resource."""
        ...


@runtime_checkable
class RbacManager(Protocol):
    """Protocol for RBAC manager."""

    async def init(self) -> None:
        """Initialize RBAC manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up RBAC manager."""
        ...

    def check_role(self, user: Any, role: str) -> bool:
        """Check if user has role."""
        ...


@runtime_checkable
class RuleManager(Protocol):
    """Protocol for rule manager."""

    async def init(self) -> None:
        """Initialize rule manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up rule manager."""
        ...

    def check_rule(self, rule: str, context: Dict[str, Any]) -> bool:
        """Check if rule passes."""
        ...


@runtime_checkable
class AuditManager(Protocol):
    """Protocol for audit manager."""

    async def init(self) -> None:
        """Initialize audit manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up audit manager."""
        ...

    def log_action(self, user: Any, action: str, resource: str) -> None:
        """Log audit action."""
        ...


@runtime_checkable
class EncryptionManager(Protocol):
    """Protocol for encryption manager."""

    async def init(self) -> None:
        """Initialize encryption manager."""
        ...

    async def cleanup(self) -> None:
        """Clean up encryption manager."""
        ...

    def encrypt(self, data: str) -> str:
        """Encrypt data."""
        ...

    def decrypt(self, data: str) -> str:
        """Decrypt data."""
        ...
