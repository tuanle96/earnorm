"""RecordSet implementation."""

from typing import Any, Callable, Generic, Iterator, List, Sequence, TypeVar

from .model import BaseModel

T = TypeVar("T", bound=BaseModel)


class RecordSet(Generic[T]):
    """RecordSet for batch operations."""

    def __init__(self, records: Sequence[T]) -> None:
        """Initialize RecordSet."""
        self._records: List[T] = list(records)

    def __getitem__(self, index: int) -> T:
        """Get record by index."""
        return self._records[index]

    def __len__(self) -> int:
        """Get number of records."""
        return len(self._records)

    def __iter__(self) -> Iterator[T]:
        """Iterate over records."""
        return iter(self._records)

    def append(self, record: T) -> None:
        """Append record to recordset."""
        self._records.append(record)

    def extend(self, records: Sequence[T]) -> None:
        """Extend recordset with records."""
        self._records.extend(records)

    def filtered(self, predicate: Callable[[T], bool]) -> "RecordSet[T]":
        """Filter records by predicate."""
        return RecordSet([record for record in self._records if predicate(record)])

    def map(self, func: Callable[[T], Any]) -> List[Any]:
        """Map function over records."""
        return [func(record) for record in self._records]

    def to_list(self) -> List[T]:
        """Convert to list."""
        return self._records.copy()
