"""Access Control List management."""

from functools import wraps
from typing import Dict, List, Optional, Set, Type, Union

from ..base.model import BaseModel


class ACLManager:
    """Manager for Access Control Lists."""

    def __init__(self):
        self._acls: Dict[str, Dict[str, Set[str]]] = {}
        self._cache: Dict[str, Dict[str, bool]] = {}

    def register_model(self, model: Type[BaseModel]) -> None:
        """Register ACL for a model."""
        if hasattr(model, "_acl"):
            collection = model._collection
            self._acls[collection] = {
                op: set(groups) for op, groups in model._acl.items()
            }

    def can_access(self, user: "BaseModel", collection: str, operation: str) -> bool:
        """Check if user can perform operation on collection."""
        # Check cache first
        cache_key = f"{user.id}:{collection}:{operation}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get required groups for operation
        required_groups = self._acls.get(collection, {}).get(operation, set())
        if not required_groups:
            result = False  # No groups defined means no access
        else:
            # Check if user has any of the required groups
            result = any(group in user.groups for group in required_groups)

        # Cache result
        self._cache[cache_key] = result
        return result

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear ACL cache for user or all users."""
        if user_id:
            self._cache = {
                k: v for k, v in self._cache.items() if not k.startswith(f"{user_id}:")
            }
        else:
            self._cache.clear()


# Global ACL manager instance
acl_manager = ACLManager()


def requires(*groups: str):
    """Decorator to require group membership for method access."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = self.env.user
            if not user:
                raise PermissionError("No user in context")

            # Check if user has any of the required groups
            if not any(group in user.groups for group in groups):
                raise PermissionError(f"Access denied: requires one of {groups}")

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def check_operation(operation: str):
    """Decorator to check operation permission on model."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = self.env.user
            if not user:
                raise PermissionError("No user in context")

            # Check if user can perform operation
            if not acl_manager.can_access(user, self._collection, operation):
                raise PermissionError(
                    f"Access denied: cannot {operation} on {self._collection}"
                )

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
