"""Group-based access control implementation."""

from typing import Any, Dict, Optional, Set, Type

from motor.motor_asyncio import AsyncIOMotorClientSession

from ..base.model import BaseModel
from ..cache.cache import cached
from .base import AccessDeniedError, AccessManager, User


class ACLManager(AccessManager):
    """Group-based access control manager."""

    def __init__(self) -> None:
        """Initialize ACL manager."""
        self._acls: Dict[str, Dict[str, bool]] = {}

    def register_rule(
        self,
        model: Type[BaseModel],
        operation: str,
        rule: Dict[str, bool],
    ) -> None:
        """Register access rule.

        Args:
            model: Model class
            operation: Operation name
            rule: Access rules mapping group to allow/deny
        """
        collection = model.get_collection()
        if collection not in self._acls:
            self._acls[collection] = {}

        for group, allow in rule.items():
            self._acls[collection][f"{group}:{operation}"] = allow

    @cached(ttl=300, key_pattern="acl_access:{0.__name__}:{1}:{2.id}")
    async def check_access(
        self,
        user: User,
        model: Type[BaseModel],
        operation: str,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if user can access model in given operation.

        Args:
            user: User to check
            model: Model class
            operation: Operation name
            session: Optional database session

        Returns:
            bool: True if access is allowed

        Raises:
            AccessDeniedError: If access is denied
        """
        # Get collection name from model class
        collection = model.get_collection()

        # Get ACL for collection
        acl = self._acls.get(collection, {})

        # Check user groups
        for group in user.groups:
            if acl.get(f"{group}:{operation}", False):
                return True

        raise AccessDeniedError(
            f"Access denied for {user.id} to {collection} in mode {operation}"
        )


# Global ACL manager instance
acl_manager = ACLManager()
