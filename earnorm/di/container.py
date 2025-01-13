"""Dependency injection container."""

from typing import Any, Protocol, Union, runtime_checkable

from ..metrics.base import MetricsManager
from ..pool.base import PoolManager
from ..rules.base import RuleManager
from ..security.base import AclManager


@runtime_checkable
class Container(Protocol):
    """Protocol for dependency injection container."""

    async def get(
        self, name: str
    ) -> Union[PoolManager, MetricsManager, AclManager, RuleManager]:
        """Get service by name.

        Args:
            name: Service name

        Returns:
            Service instance
        """
        ...
