"""RecordSet implementation for EarnORM."""

from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
)

from earnorm.base.model import BaseModel
from earnorm.base.registry import registry

T = TypeVar("T", bound=BaseModel)


class RecordSet(Generic[T]):
    """RecordSet for batch operations.

    A RecordSet represents a collection of records from a specific model.
    It provides methods for CRUD operations and iterating over the records.

    Example:
        ```python
        # Get users recordset
        users = env['users'].search([('is_active', '=', True)])

        # Access first record
        first_user = users[0]

        # Update all records
        users.write({'status': 'active'})

        # Delete all records
        users.unlink()
        ```
    """

    def __init__(self, model: T, records: Optional[Sequence[T]] = None) -> None:
        """Initialize RecordSet.

        Args:
            model: Model class
            records: Optional sequence of records
        """
        self._model = model
        self._records: List[T] = list(records) if records else []
        self._collection = model.get_collection()

    def __getitem__(self, index: Union[int, slice]) -> Union[T, "RecordSet[T]"]:
        """Get record or slice of records.

        Args:
            index: Integer index or slice

        Returns:
            Single record or new RecordSet with sliced records
        """
        if isinstance(index, slice):
            return RecordSet(self._model, self._records[index])
        return self._records[index]

    def __len__(self) -> int:
        """Get number of records."""
        return len(self._records)

    def __iter__(self) -> Iterator[T]:
        """Iterate over records."""
        return iter(self._records)

    @property
    def ids(self) -> List[str]:
        """Get list of record IDs."""
        return [str(record.id) for record in self._records]

    async def create(self, values: Dict[str, Any]) -> "RecordSet[T]":
        """Create new record.

        Args:
            values: Field values

        Returns:
            New RecordSet with created record
        """
        record = self._model(**values)
        await record.save()
        return RecordSet(self._model, [record])

    async def write(self, values: Dict[str, Any]) -> bool:
        """Update records with values.

        Args:
            values: Field values to update

        Returns:
            True if successful
        """
        for record in self._records:
            for key, value in values.items():
                setattr(record, key, value)
            await record.save()
        return True

    async def unlink(self) -> bool:
        """Delete records.

        Returns:
            True if successful
        """
        for record in self._records:
            await record.delete()
        self._records.clear()
        return True

    async def search(self, domain: List[tuple], **kwargs) -> "RecordSet[T]":
        """Search records matching domain.

        Args:
            domain: Search domain
            **kwargs: Additional search options

        Returns:
            RecordSet with matching records
        """
        # Convert domain to MongoDB query
        query = self._domain_to_query(domain)

        # Get records from database
        records = await self._model.find(query, **kwargs)
        return RecordSet(self._model, records)

    def filtered(self, func: Callable[[T], bool]) -> "RecordSet[T]":
        """Filter records using predicate function.

        Args:
            func: Filter function returning bool

        Returns:
            New RecordSet with filtered records
        """
        filtered_records = [r for r in self._records if func(r)]
        return RecordSet(self._model, filtered_records)

    def mapped(self, func: Callable[[T], Any]) -> List[Any]:
        """Map function over records.

        Args:
            func: Mapping function

        Returns:
            List of mapped values
        """
        return [func(record) for record in self._records]

    def _domain_to_query(self, domain: List[tuple]) -> Dict:
        """Convert domain to MongoDB query.

        Args:
            domain: List of (field, operator, value) tuples

        Returns:
            MongoDB query dict
        """
        query = {}
        operators = {
            "=": "$eq",
            "!=": "$ne",
            ">": "$gt",
            ">=": "$gte",
            "<": "$lt",
            "<=": "$lte",
            "in": "$in",
            "not in": "$nin",
            "like": "$regex",
        }

        for field, op, value in domain:
            if op in operators:
                mongo_op = operators[op]
                query[field] = {mongo_op: value}
            else:
                query[field] = value

        return query

    def exists(self) -> bool:
        """Check if recordset contains any records.

        Returns:
            True if recordset is not empty
        """
        return bool(self._records)

    @property
    def env(self):
        """Get environment registry."""
        return registry
