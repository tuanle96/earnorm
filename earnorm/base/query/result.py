"""Query result implementation."""

from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

from earnorm.base.types import ModelProtocol

M = TypeVar("M", bound=ModelProtocol)


@dataclass
class QueryResult(Generic[M]):
    """Query result container.

    This class holds:
    - Query result items
    - Pagination metadata
    - Total count

    Type Parameters:
        M: Type of model in the result items
    """

    items: List[M]
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
