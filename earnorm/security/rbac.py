"""Role-based Access Control management."""

from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClientSession


class RBACManager:
    """Role-based Access Control manager."""

    def __init__(self) -> None:
        """Initialize RBAC manager."""
        self._permissions: Dict[str, Dict[str, bool]] = {}

    async def check_permission(
        self,
        roles: List[str],
        collection: str,
        mode: str,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if roles have permission for collection in given mode.

        Args:
            roles: List of role names
            collection: Collection name
            mode: Access mode (read/write/create/unlink)
            session: Optional database session

        Returns:
            bool: True if permission is granted
        """
        # Get permissions for collection
        perms = self._permissions.get(collection, {})

        # Check roles
        for role in roles:
            if perms.get(f"{role}:{mode}", False):
                return True

        return False

    def register_permission(
        self,
        collection: str,
        role: str,
        mode: str,
        allow: bool = True,
    ) -> None:
        """Register permission rule.

        Args:
            collection: Collection name
            role: Role name
            mode: Access mode (read/write/create/unlink)
            allow: Whether to allow access
        """
        if collection not in self._permissions:
            self._permissions[collection] = {}

        self._permissions[collection][f"{role}:{mode}"] = allow


# Global RBAC manager instance
rbac_manager = RBACManager()
