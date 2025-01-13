"""Role-based access control implementation."""

from typing import Dict, List, Optional, Set, Type

from ..base.model import BaseModel
from ..metrics import MetricsManager
from .base import AccessDeniedError, AccessManager, User


class Role:
    """Role with permissions."""

    def __init__(self, name: str, permissions: Set[str]) -> None:
        """Initialize role.

        Args:
            name: Role name
            permissions: Set of permissions
        """
        self.name = name
        self.permissions = permissions


class RBACManager(AccessManager):
    """Role-based access control manager."""

    def __init__(
        self,
        metrics_manager: Optional[MetricsManager] = None,
    ) -> None:
        """Initialize RBAC manager.

        Args:
            metrics_manager: Optional metrics manager
        """
        self._metrics_manager = metrics_manager
        self._roles: Dict[str, Role] = {}
        self._model_permissions: Dict[Type[BaseModel], Dict[str, Set[str]]] = {}

    def add_role(self, role: Role) -> None:
        """Add role.

        Args:
            role: Role to add
        """
        self._roles[role.name] = role

    def remove_role(self, name: str) -> None:
        """Remove role.

        Args:
            name: Role name
        """
        if name in self._roles:
            del self._roles[name]

    def register_rule(
        self,
        model: Type[BaseModel],
        operation: str,
        permissions: Set[str],
    ) -> None:
        """Register access rule.

        Args:
            model: Model class
            operation: Operation name
            permissions: Required permissions
        """
        if model not in self._model_permissions:
            self._model_permissions[model] = {}
        self._model_permissions[model][operation] = permissions

    async def check_access(
        self,
        user: User,
        model: Type[BaseModel],
        operation: str,
        session: Optional[Any] = None,
    ) -> bool:
        """Check if user can access model in given operation.

        Args:
            user: User to check
            model: Model class
            operation: Operation name
            session: Optional database session (not used)

        Returns:
            bool: True if access is allowed

        Raises:
            AccessDeniedError: If access is denied
        """
        # Get required permissions
        if model not in self._model_permissions:
            return True
        if operation not in self._model_permissions[model]:
            return True
        required_permissions = self._model_permissions[model][operation]

        # Check permissions
        for permission in required_permissions:
            if permission not in user.permissions:
                await self._track_access_denied(
                    user.id,
                    model.__name__,
                    operation,
                    f"Missing permission: {permission}",
                )
                raise AccessDeniedError(f"Missing permission: {permission}")

        # Track access granted
        await self._track_access_granted(user.id, model.__name__, operation)
        return True

    async def _track_access_denied(
        self,
        user_id: str,
        model: str,
        operation: str,
        reason: str,
    ) -> None:
        """Track access denied.

        Args:
            user_id: User ID
            model: Model name
            operation: Operation name
            reason: Denial reason
        """
        if self._metrics_manager:
            await self._metrics_manager.track_access_denied(
                user_id=user_id,
                model=model,
                operation=operation,
                reason=reason,
            )

    async def _track_access_granted(
        self,
        user_id: str,
        model: str,
        operation: str,
    ) -> None:
        """Track access granted.

        Args:
            user_id: User ID
            model: Model name
            operation: Operation name
        """
        if self._metrics_manager:
            await self._metrics_manager.track_access_granted(
                user_id=user_id,
                model=model,
                operation=operation,
            )


# Global RBAC manager instance
rbac_manager = RBACManager()
