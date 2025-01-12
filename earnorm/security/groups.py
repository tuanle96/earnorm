"""Security groups management."""

from functools import wraps
from typing import Dict, List, Optional, Set, Type

from ..base.model import BaseModel


class GroupManager:
    """Manager for security groups."""

    def __init__(self):
        self._groups: Dict[str, Dict[str, Any]] = {}
        self._implied: Dict[str, Set[str]] = {}
        self._categories: Dict[str, List[str]] = {}
        self._cache: Dict[str, Set[str]] = {}

    def register_group(
        self,
        name: str,
        category: str = "Other",
        parent: Optional[str] = None,
        implied_groups: Optional[List[str]] = None,
        permissions: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        """Register a security group."""
        self._groups[name] = {
            "category": category,
            "parent": parent,
            "permissions": permissions or {},
        }

        # Add to category
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        # Process implied groups
        if implied_groups:
            self._implied[name] = set(implied_groups)

    def get_implied_groups(self, group: str) -> Set[str]:
        """Get all implied groups for a group."""
        # Check cache
        if group in self._cache:
            return self._cache[group]

        # Calculate implied groups
        result = {group}
        to_process = {group}

        while to_process:
            current = to_process.pop()
            if current in self._implied:
                for implied in self._implied[current]:
                    if implied not in result:
                        result.add(implied)
                        to_process.add(implied)

        # Cache result
        self._cache[group] = result
        return result

    def check_membership(self, user_groups: List[str], group: str) -> bool:
        """Check if user has group membership."""
        # Get all implied groups
        required = self.get_implied_groups(group)

        # Check if user has any of the required groups
        return any(g in required for g in user_groups)

    def get_permissions(self, groups: List[str]) -> Dict[str, List[str]]:
        """Get combined permissions for groups."""
        result = {}

        # Process each group
        for group in groups:
            if group in self._groups:
                perms = self._groups[group].get("permissions", {})
                for collection, operations in perms.items():
                    if collection not in result:
                        result[collection] = []
                    result[collection].extend(
                        op for op in operations if op not in result[collection]
                    )

        return result

    def get_categories(self) -> Dict[str, List[str]]:
        """Get groups by category."""
        return self._categories.copy()

    def clear_cache(self) -> None:
        """Clear group cache."""
        self._cache.clear()


# Global group manager instance
group_manager = GroupManager()


def group(cls):
    """Decorator to register a security group."""
    group_manager.register_group(
        name=cls.name,
        category=getattr(cls, "category", "Other"),
        parent=getattr(cls, "parent", None),
        implied_groups=getattr(cls, "implied_groups", []),
        permissions=getattr(cls, "permissions", {}),
    )
    return cls


def define(cls):
    """Decorator to define group constants."""
    for name, value in vars(cls).items():
        if not name.startswith("_"):
            group_manager.register_group(name=value)
    return cls
