"""Connection pooling protocols.

This module provides protocol definitions for connection pooling in EarnORM.
It includes protocols for connections and pools that define the interface
that must be implemented by specific database backend implementations.

Example:
    >>> from earnorm.pool.protocols import PoolProtocol, ConnectionProtocol
    >>> from typing import Any, Protocol
    >>>
    >>> class MyConnection(ConnectionProtocol, Protocol):
    ...     async def custom_method(self) -> None:
    ...         \"\"\"Custom connection method.\"\"\"
    ...         ...
    >>>
    >>> class MyPool(PoolProtocol[MyConnection], Protocol):
    ...     async def custom_method(self) -> None:
    ...         \"\"\"Custom pool method.\"\"\"
    ...         ...
"""

from earnorm.pool.protocols.connection import ConnectionProtocol
from earnorm.pool.protocols.pool import PoolProtocol

__all__ = [
    "PoolProtocol",
    "ConnectionProtocol",
]
