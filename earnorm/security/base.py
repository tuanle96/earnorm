"""Base interfaces for access control."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Set, Type, runtime_checkable

from motor.motor_asyncio import AsyncIOMotorClientSession

from ..base.model import BaseModel


@runtime_checkable
class User(Protocol):
    """User protocol."""

    id: str
    roles: List[str]
    groups: Set[str]
    permissions: Set[str]


class AccessDeniedError(Exception):
    """Raised when access is denied."""

    pass


class AccessManager(ABC):
    """Base access manager interface."""

    @abstractmethod
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
            operation: Operation name (read/write/create/delete)
            session: Optional database session

        Returns:
            bool: True if access is allowed

        Raises:
            AccessDeniedError: If access is denied
        """
        pass

    @abstractmethod
    def register_rule(
        self,
        model: Type[BaseModel],
        operation: str,
        rule: Any,
    ) -> None:
        """Register access rule.

        Args:
            model: Model class
            operation: Operation name
            rule: Access rule (implementation specific)
        """
        pass
