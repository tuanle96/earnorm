"""Record rules management."""

from functools import wraps
from typing import Any, Dict, List, Optional, Type

from ..base.model import BaseModel


class RecordRules:
    """Base class for record rules."""

    _collection: str
    _rules: Dict[str, List[str]] = {"read": [], "write": [], "create": [], "delete": []}

    @classmethod
    def register(cls, operation: str):
        """Decorator to register a rule method."""

        def decorator(func):
            cls._rules[operation].append(func.__name__)
            return func

        return decorator

    @classmethod
    def apply_rules(cls, user: "BaseModel", operation: str) -> Dict[str, Any]:
        """Apply all rules for an operation."""
        filters = {}

        # Get all rules for operation
        rule_methods = cls._rules.get(operation, [])

        # Apply each rule
        for method_name in rule_methods:
            method = getattr(cls, method_name)
            rule_filter = method(cls, user)
            filters.update(rule_filter or {})

        return filters


class RuleManager:
    """Manager for record rules."""

    def __init__(self):
        self._rules: Dict[str, Type[RecordRules]] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}

    def register_rules(self, collection: str, rules: Type[RecordRules]) -> None:
        """Register rules for a collection."""
        self._rules[collection] = rules

    def get_filters(
        self, user: "BaseModel", collection: str, operation: str
    ) -> Dict[str, Any]:
        """Get filters for user and operation."""
        # Check cache first
        cache_key = f"{user.id}:{collection}:{operation}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get rules for collection
        rules = self._rules.get(collection)
        if not rules:
            return {}  # No rules means no filters

        # Apply rules
        filters = rules.apply_rules(user, operation)

        # Cache result
        self._cache[cache_key] = filters
        return filters

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear rules cache for user or all users."""
        if user_id:
            self._cache = {
                k: v for k, v in self._cache.items() if not k.startswith(f"{user_id}:")
            }
        else:
            self._cache.clear()


# Global rule manager instance
rule_manager = RuleManager()


# Decorator shortcuts
def read(func):
    """Register a read rule."""
    return RecordRules.register("read")(func)


def write(func):
    """Register a write rule."""
    return RecordRules.register("write")(func)


def create(func):
    """Register a create rule."""
    return RecordRules.register("create")(func)


def delete(func):
    """Register a delete rule."""
    return RecordRules.register("delete")(func)


def apply_rules(operation: str):
    """Decorator to apply rules to model methods."""

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current user from environment
            user = self.env.user
            if not user:
                raise PermissionError("No user in context")

            # Get filters from rules
            filters = rule_manager.get_filters(user, self._collection, operation)

            # Apply filters to query
            if operation == "read":
                if hasattr(self, "find"):
                    # For find methods
                    kwargs.update(filters)
                else:
                    # For single record access
                    for field, value in filters.items():
                        if not self.matches_filter(field, value):
                            raise PermissionError(
                                f"Access denied: record does not match rules"
                            )
            else:
                # For write/create/delete operations
                for field, value in filters.items():
                    if not self.matches_filter(field, value):
                        raise PermissionError(
                            f"Access denied: operation not allowed by rules"
                        )

            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
