"""Access Control List management."""

from typing import Any, Dict, List, Optional, Protocol, Set, Type, runtime_checkable

from motor.motor_asyncio import AsyncIOMotorClientSession

from ..base.model import BaseModel
from ..cache.cache import cached


@runtime_checkable
class User(Protocol):
    """User protocol."""

    id: str
    roles: List[str]
    groups: Set[str]


class ACLManager:
    """Access Control List manager."""

    def __init__(self) -> None:
        """Initialize ACL manager."""
        self._acls: Dict[str, Dict[str, bool]] = {}

    async def can_access(
        self,
        user: User,
        collection: str,
        mode: str,
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if user can access collection in given mode.

        Args:
            user: User to check
            collection: Collection name
            mode: Access mode (read/write/create/unlink)
            session: Optional database session

        Returns:
            bool: True if access is allowed
        """
        # Get ACL for collection
        acl = self._acls.get(collection, {})

        # Check user groups
        for group in user.groups:
            if acl.get(f"{group}:{mode}", False):
                return True

        return False

    def register_acl(
        self,
        collection: str,
        group: str,
        mode: str,
        allow: bool = True,
    ) -> None:
        """Register ACL rule.

        Args:
            collection: Collection name
            group: Group name
            mode: Access mode (read/write/create/unlink)
            allow: Whether to allow access
        """
        if collection not in self._acls:
            self._acls[collection] = {}

        self._acls[collection][f"{group}:{mode}"] = allow

    @cached(ttl=300, key_pattern="acl_access:{0.__name__}:{1}:{2}")
    async def check_access(
        self,
        model_cls: Type[BaseModel],
        mode: str,
        groups: Set[str],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if model can be accessed in given mode."""
        # Get collection name from model class
        collection = model_cls.get_collection()

        # Get ACL for collection
        acl = self._acls.get(collection, {})

        # Check each group's access
        for group in groups:
            if acl.get(f"{group}:{mode}", False):
                return True

        return False


# Global ACL manager instance
acl_manager = ACLManager()
