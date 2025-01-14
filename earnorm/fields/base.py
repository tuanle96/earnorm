"""Base field types for EarnORM."""

from abc import abstractmethod
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar, Union

from bson import ObjectId
from typing_extensions import Self

from earnorm.base.types import FieldProtocol, ModelProtocol
from earnorm.validators import ValidationError

T = TypeVar("T")
M = TypeVar("M", bound=ModelProtocol)
ValidatorFunc = Callable[[Any], None]


class Field(FieldProtocol, Generic[T]):
    """Base field class."""

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize field."""
        self.required = required
        self.unique = unique
        self.default = default
        self.validators = validators or []
        self.name: str = ""

    def validate(self, value: Any) -> None:
        """Validate field value.

        Args:
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        if self.required and value is None:
            raise ValidationError(f"Field {self.name} is required")

        if value is not None:
            for validator in self.validators:
                validator(value)

    def __get__(
        self, instance: Optional[ModelProtocol], owner: Type[ModelProtocol]
    ) -> Union[Self, T]:
        """Get field value."""
        if instance is None:
            return self
        value = instance.data.get(self.name)
        if value is None:
            return self.convert(self.default)
        return self.from_mongo(value)

    def __set__(self, instance: Optional[ModelProtocol], value: Any) -> None:
        """Set field value."""
        if instance is None:
            return

        # Validate before setting
        self.validate(value)

        if isinstance(value, Field):
            instance.data[self.name] = self.convert(value.default)
        else:
            instance.data[self.name] = self.convert(value)

    def __delete__(self, instance: Optional[ModelProtocol]) -> None:
        """Delete field value."""
        if instance is None:
            return
        instance.data.pop(self.name, None)

    @abstractmethod
    def convert(self, value: Any) -> T:
        """Convert value to field type."""
        pass

    def to_dict(self, value: Optional[T]) -> Any:
        """Convert value to dict representation."""
        return value

    def to_mongo(self, value: Optional[T]) -> Any:
        """Convert Python value to MongoDB value."""
        return value

    def from_mongo(self, value: Any) -> T:
        """Convert MongoDB value to Python value."""
        return self.convert(value)


class IntegerField(Field[int]):
    """Integer field."""

    def convert(self, value: Any) -> int:
        """Convert value to integer."""
        if value is None:
            return 0
        return int(value)

    def to_mongo(self, value: Optional[int]) -> int:
        """Convert Python integer to MongoDB integer."""
        if value is None:
            return 0
        return int(value)

    def from_mongo(self, value: Any) -> int:
        """Convert MongoDB integer to Python integer."""
        if value is None:
            return 0
        return int(value)


class FloatField(Field[float]):
    """Float field."""

    def convert(self, value: Any) -> float:
        """Convert value to float."""
        if value is None:
            return 0.0
        return float(value)

    def to_mongo(self, value: Optional[float]) -> float:
        """Convert Python float to MongoDB float."""
        if value is None:
            return 0.0
        return float(value)

    def from_mongo(self, value: Any) -> float:
        """Convert MongoDB float to Python float."""
        if value is None:
            return 0.0
        return float(value)


class BooleanField(Field[bool]):
    """Boolean field."""

    def convert(self, value: Any) -> bool:
        """Convert value to boolean."""
        if value is None:
            return False
        return bool(value)

    def to_mongo(self, value: Optional[bool]) -> bool:
        """Convert Python boolean to MongoDB boolean."""
        if value is None:
            return False
        return bool(value)

    def from_mongo(self, value: Any) -> bool:
        """Convert MongoDB boolean to Python boolean."""
        if value is None:
            return False
        return bool(value)


class ObjectIdField(Field[ObjectId]):
    """ObjectId field."""

    def convert(self, value: Any) -> ObjectId:
        """Convert value to ObjectId."""
        if value is None or value == "":
            return ObjectId()  # Generate new ObjectId instead of returning None
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    def to_dict(self, value: Optional[ObjectId]) -> Optional[str]:
        """Convert ObjectId to string."""
        if value is None:
            return None
        return str(value)

    def to_mongo(self, value: Optional[ObjectId]) -> Optional[ObjectId]:
        """Convert Python ObjectId to MongoDB ObjectId."""
        if value is None:
            return None
        if type(value) is ObjectId:  # type: ignore
            return value
        return ObjectId(str(value))

    def from_mongo(self, value: Any) -> ObjectId:
        """Convert MongoDB ObjectId to Python ObjectId."""
        if value is None:
            return ObjectId()  # Return new ObjectId instead of None
        if type(value) is ObjectId:  # type: ignore
            return value
        return ObjectId(str(value))


class ListField(Field[List[T]], Generic[T]):
    """List field."""

    def __init__(
        self,
        field: Field[T],
        *,
        required: bool = False,
        default: Any = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
        )
        self.field = field

    def convert(self, value: Any) -> List[T]:
        """Convert value to list."""
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.convert(item)
            result.append(converted)
        return result

    def to_dict(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert list to dict representation."""
        if value is None:
            return None
        return [self.field.to_dict(item) for item in value]

    def to_mongo(self, value: Optional[List[T]]) -> Optional[List[Any]]:
        """Convert Python list to MongoDB array."""
        if value is None:
            return None
        return [self.field.to_mongo(item) for item in value]

    def from_mongo(self, value: Any) -> List[T]:
        """Convert MongoDB array to Python list."""
        if value is None:
            return []  # Return empty list instead of None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.from_mongo(item)
            result.append(converted)
        return result


class DictField(Field[Dict[str, Any]]):
    """Dict field."""

    def convert(self, value: Any) -> Dict[str, Any]:
        """Convert value to dict."""
        if value is None:
            return {}
        return dict(value)

    def to_mongo(self, value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Python dict to MongoDB document."""
        if value is None:
            return {}
        return dict(value)

    def from_mongo(self, value: Any) -> Dict[str, Any]:
        """Convert MongoDB document to Python dict."""
        if value is None:
            return {}
        return dict(value)
