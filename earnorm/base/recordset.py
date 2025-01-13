"""RecordSet implementation for EarnORM."""

from typing import Any, Callable, Dict, Iterator, List, Optional, Type, TypeVar, cast

from earnorm.base.domain import DomainParser
from earnorm.base.env import env
from earnorm.base.types import ModelProtocol, RecordSetProtocol, RegistryProtocol

M = TypeVar("M", bound=ModelProtocol)


class RecordSet(RecordSetProtocol[M]):
    """RecordSet for batch operations.

    A RecordSet represents a collection of records from a specific model.
    It provides methods for CRUD operations and iterating over the records.
    RecordSet can only be created from Model classes.

    Example:
        ```python
        # Get users recordset
        users = await User.search([('is_active', '=', True)])

        # Access first record
        first_user = users[0]

        # Update all records
        await users.write({'status': 'active'})

        # Delete all records
        await users.unlink()
        ```
    """

    def __init__(self, model_cls: Type[M], records: List[M]) -> None:
        """Initialize RecordSet.

        Should only be called from Model classes.

        Args:
            model_cls: Model class
            records: List of records
        """
        from earnorm.base.model import BaseModel

        if not issubclass(model_cls, BaseModel):
            raise ValueError("RecordSet can only be created from Model classes")
        self._model_cls = model_cls
        self._records = records
        self._collection = model_cls.get_collection_name()

    def __getitem__(self, index: int) -> M:
        """Get record by index."""
        return self._records[index]

    def __len__(self) -> int:
        """Get number of records."""
        return len(self._records)

    def __iter__(self) -> Iterator[M]:
        """Iterate over records."""
        return iter(self._records)

    def __getattr__(self, name: str) -> Any:
        """Forward attribute access to first record.

        If recordset is empty, return empty value based on field type.
        """
        if not self._records:
            field = getattr(self._model_cls, name, None)
            if field is None:
                raise AttributeError(
                    f"'{self._model_cls.__name__}' has no attribute '{name}'"
                )
            return None  # Return None for empty recordset
        return getattr(self._records[0], name)

    @property
    def ids(self) -> List[str]:
        """Get list of record IDs."""
        return [str(record.id) for record in self._records]

    def ensure_one(self) -> M:
        """Ensure recordset contains exactly one record.

        Returns:
            Single record

        Raises:
            ValueError: If recordset doesn't contain exactly one record
        """
        if len(self._records) != 1:
            raise ValueError(
                f"Expected singleton recordset, got {len(self._records)} records"
            )
        return self._records[0]

    def exists(self) -> bool:
        """Check if recordset contains any records."""
        return bool(self._records)

    async def create(self, values: Dict[str, Any]) -> "RecordSetProtocol[M]":
        """Create new record."""
        record = self._model_cls(**values)
        await record.save()
        return RecordSet(self._model_cls, [record])

    async def write(self, values: Dict[str, Any]) -> bool:
        """Update records with values."""
        for record in self._records:
            for key, value in values.items():
                setattr(record, key, value)
            await record.save()
        return True

    async def unlink(self) -> bool:
        """Delete records."""
        for record in self._records:
            await record.delete()
        self._records.clear()
        return True

    def filtered(self, func: Callable[[M], bool]) -> "RecordSet[M]":
        """Filter records using predicate function."""
        filtered_records = [r for r in self._records if func(r)]
        return RecordSet(self._model_cls, filtered_records)

    def mapped(self, field: str) -> List[Any]:
        """Map field values from records.

        Args:
            field: Field name to map

        Returns:
            List of field values
        """
        return [getattr(r, field) for r in self._records]

    @property
    def env(self) -> RegistryProtocol:
        """Get environment registry."""
        return env

    def filtered_domain(self, domain: List[Any]) -> "RecordSet[M]":
        """Filter records using domain expression.

        Args:
            domain: Domain expression list

        Returns:
            New filtered recordset
        """
        query = DomainParser(domain).to_mongo_query()
        filtered_records: List[M] = []
        for record in self._records:
            match = True
            for field, value in query.items():
                if isinstance(value, dict):
                    # Handle operators
                    for op_name, op_value in cast(Dict[str, Any], value).items():
                        if op_name == "$gt" and not getattr(record, field) > op_value:
                            match = False
                        elif (
                            op_name == "$gte" and not getattr(record, field) >= op_value
                        ):
                            match = False
                        elif op_name == "$lt" and not getattr(record, field) < op_value:
                            match = False
                        elif (
                            op_name == "$lte" and not getattr(record, field) <= op_value
                        ):
                            match = False
                        elif op_name == "$ne" and getattr(record, field) == op_value:
                            match = False
                        elif (
                            op_name == "$in" and getattr(record, field) not in op_value
                        ):
                            match = False
                        elif op_name == "$nin" and getattr(record, field) in op_value:
                            match = False
                else:
                    # Direct value comparison
                    if getattr(record, field) != value:
                        match = False
            if match:
                filtered_records.append(record)
        return RecordSet(self._model_cls, filtered_records)

    def sorted(self, key: str, reverse: bool = False) -> "RecordSet[M]":
        """Sort records by field.

        Args:
            key: Field name to sort by
            reverse: Sort in descending order if True

        Returns:
            New sorted recordset
        """
        sorted_records = sorted(
            self._records, key=lambda r: getattr(r, key), reverse=reverse
        )
        return RecordSet(self._model_cls, sorted_records)

    def count(self) -> int:
        """Get number of records."""
        return len(self._records)

    def first(self) -> Optional[M]:
        """Get first record or None."""
        return self._records[0] if self._records else None

    def last(self) -> Optional[M]:
        """Get last record or None."""
        return self._records[-1] if self._records else None
