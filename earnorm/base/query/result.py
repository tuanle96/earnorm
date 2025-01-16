"""Query result implementation."""

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

from earnorm.base.models.interfaces import ModelInterface

T = TypeVar("T", bound=ModelInterface)


@dataclass
class QueryResult(Generic[T]):
    """Query result container.

    This class holds:
    - Query result items
    - Pagination metadata
    - Total count

    Examples:
        >>> result = QueryResult(
        ...     items=[user1, user2],
        ...     total=10,
        ...     limit=2,
        ...     offset=0
        ... )
        >>> print(f"Found {result.total} users")
        >>> for user in result.items:
        ...     print(user.name)
    """

    items: List[T]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None

    @property
    def has_more(self) -> bool:
        """Check if there are more items.

        Returns:
            True if there are more items after the current page
        """
        if self.limit is None or self.offset is None:
            return False
        return self.offset + self.limit < self.total

    @property
    def next_offset(self) -> Optional[int]:
        """Get next page offset.

        Returns:
            Offset for next page, or None if no next page
        """
        if not self.has_more:
            return None
        assert self.offset is not None
        assert self.limit is not None
        return self.offset + self.limit
