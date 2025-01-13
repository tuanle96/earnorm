"""RecordSet implementation for EarnORM."""

from typing import (
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from earnorm.base.env import env
from earnorm.base.types import ModelProtocol, RecordSetProtocol, RegistryProtocol

M = TypeVar("M", bound=ModelProtocol)


class RecordSet(RecordSetProtocol[M]):
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

    def __init__(self, model_cls: Type[M], records: Optional[List[M]] = None) -> None:
        """Initialize RecordSet.

        Args:
            model_cls: Model class
            records: Optional sequence of records
        """
        self._model_cls = model_cls
        self._records: List[M] = list(records) if records else []
        self._collection = model_cls.get_collection_name()

    def __getitem__(self, index: int) -> M:
        """Get record by index.

        Args:
            index: Integer index

        Returns:
            Single record
        """
        return self._records[index]

    def __len__(self) -> int:
        """Get number of records."""
        return len(self._records)

    def __iter__(self) -> Iterator[M]:
        """Iterate over records."""
        return iter(self._records)

    @property
    def ids(self) -> List[str]:
        """Get list of record IDs."""
        return [str(record.id) for record in self._records]

    async def create(self, values: Dict[str, Any]) -> "RecordSetProtocol[M]":
        """Create new record.

        Args:
            values: Field values

        Returns:
            New RecordSet with created record
        """
        record = self._model_cls(**values)
        await record.save()
        return RecordSet(self._model_cls, [record])

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

    async def search(
        self,
        domain: List[Tuple[str, str, Any]],
        *,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> "RecordSet[M]":
        """Search records matching domain.

        Args:
            domain: Search domain
            offset: Number of records to skip
            limit: Maximum number of records to return
            order: Sort order

        Returns:
            RecordSet with matching records
        """
        # Convert domain to MongoDB query
        query = self._domain_to_query(domain)

        # Build find options
        options: Dict[str, Any] = {}
        if offset:
            options["skip"] = offset
        if limit:
            options["limit"] = limit
        if order:
            options["sort"] = self._parse_order(order)

        # Get records from database
        records = await self._model_cls.find(query)
        return cast("RecordSet[M]", RecordSet(self._model_cls, records))

    def filtered(self, func: Callable[[M], bool]) -> "RecordSet[M]":
        """Filter records using predicate function.

        Args:
            func: Filter function returning bool

        Returns:
            New RecordSet with filtered records
        """
        filtered_records = [r for r in self._records if func(r)]
        return RecordSet(self._model_cls, filtered_records)

    def mapped(self, func: Callable[[M], Any]) -> List[Any]:
        """Map function over records.

        Args:
            func: Mapping function

        Returns:
            List of mapped values
        """
        return [func(record) for record in self._records]

    def _domain_to_query(self, domain: List[Tuple[str, str, Any]]) -> Dict[str, Any]:
        """Convert domain to MongoDB query.

        Args:
            domain: List of (field, operator, value) tuples

        Returns:
            MongoDB query dict
        """
        query: Dict[str, Any] = {}
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
    def env(self) -> RegistryProtocol:
        """Get environment registry."""
        return env

    def _parse_order(self, order: str) -> List[Tuple[str, int]]:
        """Parse order string to MongoDB sort specification.

        Args:
            order: Order string (e.g. "name asc, date desc")

        Returns:
            List of (field, direction) tuples
        """
        sort: List[Tuple[str, int]] = []
        for item in order.split(","):
            field, direction = item.strip().split(" ")
            sort.append((field, 1 if direction.lower() == "asc" else -1))
        return sort
