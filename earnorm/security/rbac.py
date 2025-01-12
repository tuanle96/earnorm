"""Role-based access control management."""

from functools import wraps
from typing import Any, Dict, List, Optional, Set, Type

from ..base.model import BaseModel


class RBACManager:
    """Manager for role-based access control."""

    def __init__(self):
        self._roles: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, Dict[str, bool]] = {}

    def register_role(
        self,
        name: str,
        permissions: Dict[str, List[str]],
        custom_rules: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a role with permissions."""
        self._roles[name] = {
            "permissions": permissions,
            "custom_rules": custom_rules or {},
        }

    def check_permission(
        self, roles: List[str], collection: str, operation: str
    ) -> bool:
        """Check if roles have permission for operation."""
        # Check cache
        cache_key = f"{','.join(roles)}:{collection}:{operation}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check each role
        result = False
        for role in roles:
            if role in self._roles:
                perms = self._roles[role]["permissions"]
                if collection in perms and operation in perms[collection]:
                    result = True
                    break

        # Cache result
        self._cache[cache_key] = result
        return result

    async def check_custom_rule(
        self, roles: List[str], rule_name: str, *args, **kwargs
    ) -> bool:
        """Check custom rule for roles."""
        # Check each role
        for role in roles:
            if role in self._roles:
                rules = self._roles[role]["custom_rules"]
                if rule_name in rules:
                    rule = rules[rule_name]
                    if await rule(*args, **kwargs):
                        return True
        return False

    def clear_cache(self) -> None:
        """Clear RBAC cache."""
        self._cache.clear()


# Global RBAC manager instance
rbac_manager = RBACManager()


def role(name: str):
    """Decorator to register a role."""

    def decorator(cls):
        # Get permissions
        permissions = getattr(cls, "permissions", {})

        # Get custom rules
        custom_rules = {}
        for attr_name, attr_value in vars(cls).items():
            if not attr_name.startswith("_") and callable(attr_value):
                custom_rules[attr_name] = attr_value

        # Register role
        rbac_manager.register_role(
            name=name, permissions=permissions, custom_rules=custom_rules
        )
        return cls

    return decorator


def requires_permission(collection: str, operation: str):
    """Decorator to require permission for method."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = self.env.user
            if not user:
                raise PermissionError("No user in context")

            # Check permission
            if not rbac_manager.check_permission(user.roles, collection, operation):
                raise PermissionError(
                    f"Access denied: requires {operation} on {collection}"
                )

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def requires_rule(rule_name: str):
    """Decorator to require custom rule for method."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = self.env.user
            if not user:
                raise PermissionError("No user in context")

            # Check custom rule
            if not await rbac_manager.check_custom_rule(
                user.roles, rule_name, *args, **kwargs
            ):
                raise PermissionError(f"Access denied: fails rule {rule_name}")

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
