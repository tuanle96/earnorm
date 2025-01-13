"""Field types for EarnORM models."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from bson import ObjectId

from ..validation.decorators import validates_fields
from ..validation.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinLengthValidator,
    MinValueValidator,
    RegexValidator,
    RequiredValidator,
    Validator,
)
from .model import BaseModel
from .recordset import RecordSet

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


class Field(Generic[T], ABC):
    """Base field class."""

    def __init__(
        self,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        validators: Optional[List[Validator]] = None,
    ) -> None:
        """Initialize field."""
        self.required = required
        self.default = default
        self.index = index
        self.unique = unique
        self.validators = validators or []
        if required:
            self.validators.append(RequiredValidator())

        # Set by Model metaclass
        self.name: str = ""
        self._model_cls: Optional[Type[BaseModel]] = None

    @property
    def model_cls(self) -> Optional[Type[BaseModel]]:
        """Get model class."""
        return self._model_cls

    @model_cls.setter
    def model_cls(self, value: Optional[Type[BaseModel]]) -> None:
        """Set model class."""
        self._model_cls = value

    @abstractmethod
    def convert(self, value: Any) -> Optional[T]:
        """Convert value to field type."""
        pass

    def to_dict(self, value: Optional[T]) -> Any:
        """Convert value to dict representation.

        Args:
            value: Value to convert

        Returns:
            Dict representation
        """
        return value

    @validates_fields("value")
    def validate(self, value: Optional[T]) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValueError: If validation fails
        """
        # Run field validators
        for validator in self.validators:
            validator(value)


class StringField(Field[str]):
    """String field."""

    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize string field.

        Args:
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regex pattern
            **kwargs: Additional field arguments
        """
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

        # Add string validators
        if min_length:
            self.validators.append(MinLengthValidator(min_length))
        if max_length:
            self.validators.append(MaxLengthValidator(max_length))
        if pattern:
            self.validators.append(RegexValidator(pattern))

    def convert(self, value: Any) -> str:
        """Convert value to string."""
        if value is None:
            return ""
        return str(value)

    def validate(self, value: Optional[str]) -> None:
        """Validate string value."""
        super().validate(value)
        if value is None:
            return

        if self.min_length and len(value) < self.min_length:
            raise ValueError(
                f"Field {self.name} must be at least {self.min_length} characters"
            )

        if self.max_length and len(value) > self.max_length:
            raise ValueError(
                f"Field {self.name} must be at most {self.max_length} characters"
            )


class IntegerField(Field[int]):
    """Integer field."""

    def __init__(
        self,
        *,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize integer field.

        Args:
            min_value: Minimum value
            max_value: Maximum value
            **kwargs: Additional field arguments
        """
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

        # Add numeric validators
        if min_value is not None:
            self.validators.append(MinValueValidator(min_value))
        if max_value is not None:
            self.validators.append(MaxValueValidator(max_value))

    def convert(self, value: Any) -> int:
        """Convert value to integer."""
        if value is None:
            return 0
        return int(value)

    def validate(self, value: Optional[int]) -> None:
        """Validate integer value."""
        super().validate(value)
        if value is None:
            return

        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Field {self.name} must be at least {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Field {self.name} must be at most {self.max_value}")


class FloatField(Field[float]):
    """Float field."""

    def __init__(
        self,
        *,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        precision: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize float field.

        Args:
            min_value: Minimum value
            max_value: Maximum value
            precision: Decimal precision
            **kwargs: Additional field arguments
        """
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision

    def convert(self, value: Any) -> float:
        """Convert value to float."""
        if value is None:
            return 0.0
        return float(value)

    def validate(self, value: Optional[float]) -> None:
        """Validate float value."""
        super().validate(value)
        if value is None:
            return

        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Field {self.name} must be at least {self.min_value}")

        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Field {self.name} must be at most {self.max_value}")


class BooleanField(Field[bool]):
    """Boolean field."""

    def convert(self, value: Any) -> bool:
        """Convert value to boolean."""
        if value is None:
            return False
        return bool(value)


class DateTimeField(Field[datetime]):
    """DateTime field."""

    def convert(self, value: Any) -> datetime:
        """Convert value to datetime."""
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))

    def to_dict(self, value: Optional[datetime]) -> Optional[str]:
        """Convert datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()


class ObjectIdField(Field[ObjectId]):
    """ObjectId field."""

    def convert(self, value: Any) -> Optional[ObjectId]:
        """Convert value to ObjectId."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    def to_dict(self, value: Optional[ObjectId]) -> Optional[str]:
        """Convert ObjectId to string."""
        if value is None:
            return None
        return str(value)


class ListField(Field[List[T]], Generic[T]):
    """List field."""

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        default: Any = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        validators: Optional[List[Validator]] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            validators=validators,
        )
        self.field = field
        self._min_length = min_length
        self._max_length = max_length

        if min_length is not None:
            self.validators.append(MinLengthValidator(min_length))
        if max_length is not None:
            self.validators.append(MaxLengthValidator(max_length))

    def convert(self, value: Any) -> Optional[List[T]]:
        """Convert value to list."""
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        for item in value:
            converted = self.field.convert(item)
            if converted is not None:
                result.append(converted)
        return result

    def validate(self, value: Optional[List[T]]) -> None:
        """Validate list value."""
        super().validate(value)
        if value is None:
            return

        if self._min_length and len(value) < self._min_length:
            raise ValueError(
                f"Field {self.name} must have at least {self._min_length} items"
            )

        if self._max_length and len(value) > self._max_length:
            raise ValueError(
                f"Field {self.name} must have at most {self._max_length} items"
            )

        for item in value:
            self.field.validate(item)

    def to_dict(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert list to dict representation."""
        if value is None:
            return None
        return [self.field.to_dict(item) for item in value]


class DictField(Field[Dict[str, Any]]):
    """Dict field."""

    def convert(self, value: Any) -> Dict[str, Any]:
        """Convert value to dict."""
        if value is None:
            return {}
        return dict(value)


class ReferenceField(Field[M]):
    """Reference field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        validators: Optional[List[Validator]] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            validators=validators,
        )
        self._referenced_model: Type[M] = referenced_model

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return getattr(self.referenced_model, "collection", "")

    def convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return self.referenced_model(
                _collection="", _abstract=False, _indexes=[], id=value
            )
        if isinstance(value, dict):
            return self.referenced_model(
                _collection="", _abstract=False, _indexes=[], **value
            )
        if isinstance(value, self.referenced_model):
            return value
        raise ValueError(
            f"Cannot convert {type(value)} to {self.referenced_model.__name__}"
        )

    def to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert reference to dict representation."""
        if value is None:
            return None
        return str(value.id)


class Many2oneField(Field[Optional[M]]):
    """Many2one field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        validators: Optional[List[Validator]] = None,
        ondelete: str = "set null",
        lazy: bool = False,
        relation: Optional[str] = None,
        column1: Optional[str] = None,
        column2: Optional[str] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
            validators=validators,
        )
        self._referenced_model: Type[M] = referenced_model
        self.ondelete = ondelete
        self.lazy = lazy
        self.relation = relation
        self.column1 = column1
        self.column2 = column2

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return getattr(self.referenced_model, "collection", "")

    def convert(self, value: Any) -> Optional[M]:
        """Convert value to referenced record."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            if self.lazy:
                return self.referenced_model(
                    _collection=self.collection, id=value, _abstract=False, _indexes=[]
                )
            return None  # Async operation not supported in sync convert
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(
                _collection=self.collection, _abstract=False, _indexes=[], **value
            )
        return self.referenced_model(
            _collection=self.collection,
            id=ObjectId(str(value)),
            _abstract=False,
            _indexes=[],
        )

    async def async_convert(self, value: Any) -> Optional[M]:
        """Convert value to referenced record asynchronously."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            if self.lazy:
                return self.referenced_model(
                    _collection=self.collection, id=value, _abstract=False, _indexes=[]
                )
            record: Optional[RecordSet[M]] = await self.referenced_model.find_one(
                {"_id": value}
            )
            if record and len(record) > 0:
                return record[0]
            return None
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(
                _collection=self.collection, _abstract=False, _indexes=[], **value
            )
        return self.referenced_model(
            _collection=self.collection,
            id=ObjectId(str(value)),
            _abstract=False,
            _indexes=[],
        )

    def to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert reference to dict representation."""
        if value is None:
            return None
        return str(value.id)


class One2manyField(Field[List[M]]):
    """One2many field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        inverse_field: str,
        *,
        required: bool = False,
        default: Any = None,
        validators: Optional[List[Validator]] = None,
        lazy: bool = False,
        relation: Optional[str] = None,
        column1: Optional[str] = None,
        column2: Optional[str] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            validators=validators,
        )
        self._referenced_model: Type[M] = referenced_model
        self.inverse_field = inverse_field
        self.lazy = lazy
        self.relation = relation
        self.column1 = column1
        self.column2 = column2

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return getattr(self.referenced_model, "collection", "")

    def convert(self, value: Any) -> List[M]:
        """Convert value to list of referenced records."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in value:
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,  # type: ignore
                            _abstract=False,
                            _indexes=[],
                        )
                    )
            elif isinstance(item, self.referenced_model):
                records.append(item)
            elif isinstance(item, dict):
                records.append(
                    self.referenced_model(
                        _collection=self.collection,
                        _abstract=False,
                        _indexes=[],
                        **item,
                    )
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        records.append(
                            self.referenced_model(
                                _collection=self.collection,
                                id=item_id,
                                _abstract=False,
                                _indexes=[],
                            )
                        )
                except (TypeError, ValueError):
                    continue
        return records

    async def async_convert(self, value: Any) -> List[M]:
        """Convert value to list of referenced records asynchronously."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in value:
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,  # type: ignore
                            _abstract=False,
                            _indexes=[],
                        )
                    )
                else:
                    record: Optional[RecordSet[M]] = (
                        await self.referenced_model.find_one({"_id": item})
                    )
                    if record and len(record) > 0:
                        records.append(record[0])
            elif isinstance(item, self.referenced_model):
                records.append(item)
            elif isinstance(item, dict):
                records.append(
                    self.referenced_model(
                        _collection=self.collection,
                        _abstract=False,
                        _indexes=[],
                        **item,
                    )
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        records.append(
                            self.referenced_model(
                                _collection=self.collection,
                                id=item_id,
                                _abstract=False,
                                _indexes=[],
                            )
                        )
                    else:
                        record: Optional[RecordSet[M]] = (
                            await self.referenced_model.find_one({"_id": item_id})
                        )
                        if record and len(record) > 0:
                            records.append(record[0])
                except (TypeError, ValueError):
                    continue
        return records

    def to_dict(self, value: Optional[List[M]]) -> Optional[List[str]]:
        """Convert references to dict representation."""
        if value is None:
            return None
        return [str(record.id) for record in value]


class Many2manyField(Field[List[M]]):
    """Many2many field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        *,
        required: bool = False,
        default: Any = None,
        validators: Optional[List[Validator]] = None,
        lazy: bool = False,
        relation: Optional[str] = None,
        column1: Optional[str] = None,
        column2: Optional[str] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            validators=validators,
        )
        self._referenced_model: Type[M] = referenced_model
        self.lazy = lazy
        self.relation = relation
        self.column1 = column1
        self.column2 = column2

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return getattr(self.referenced_model, "collection", "")

    def get_relation_name(self) -> str:
        """Get name of relation collection."""
        if self.relation:
            return self.relation
        if not self.model_cls or not self.referenced_model:
            raise ValueError("Model class or referenced model not set")
        model_collection = getattr(self.model_cls, "collection", "")
        ref_collection = self.collection
        return f"{model_collection}_{self.name}_{ref_collection}"

    def get_columns(self) -> tuple[str, str]:
        """Get names of relation columns."""
        if self.column1 and self.column2:
            return self.column1, self.column2
        if not self.model_cls or not self.referenced_model:
            raise ValueError("Model class or referenced model not set")
        model_collection = getattr(self.model_cls, "collection", "")
        ref_collection = self.collection
        return (
            f"{model_collection}_id",
            f"{ref_collection}_id",
        )

    def convert(self, value: Any) -> List[M]:
        """Convert value to list of referenced records."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in value:
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,  # type: ignore
                            _abstract=False,
                            _indexes=[],
                        )
                    )
            elif isinstance(item, self.referenced_model):
                records.append(item)
            elif isinstance(item, dict):
                records.append(
                    self.referenced_model(
                        _collection=self.collection,
                        _abstract=False,
                        _indexes=[],
                        **item,
                    )
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        records.append(
                            self.referenced_model(
                                _collection=self.collection,
                                id=item_id,
                                _abstract=False,
                                _indexes=[],
                            )
                        )
                except (TypeError, ValueError):
                    continue
        return records

    async def async_convert(self, value: Any) -> List[M]:
        """Convert value to list of referenced records asynchronously."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in value:
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,  # type: ignore
                            _abstract=False,
                            _indexes=[],
                        )
                    )
                else:
                    record: Optional[RecordSet[M]] = (
                        await self.referenced_model.find_one({"_id": item})
                    )
                    if record and len(record) > 0:
                        records.append(record[0])
            elif isinstance(item, self.referenced_model):
                records.append(item)
            elif isinstance(item, dict):
                records.append(
                    self.referenced_model(
                        _collection=self.collection,
                        _abstract=False,
                        _indexes=[],
                        **item,
                    )
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        records.append(
                            self.referenced_model(
                                _collection=self.collection,
                                id=item_id,
                                _abstract=False,
                                _indexes=[],
                            )
                        )
                    else:
                        record: Optional[RecordSet[M]] = (
                            await self.referenced_model.find_one({"_id": item_id})
                        )
                        if record and len(record) > 0:
                            records.append(record[0])
                except (TypeError, ValueError):
                    continue
        return records

    def to_dict(self, value: Optional[List[M]]) -> Optional[List[str]]:
        """Convert references to dict representation."""
        if value is None:
            return None
        return [str(record.id) for record in value]
