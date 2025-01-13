"""Base field types for EarnORM."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from bson import ObjectId

from earnorm.base.model import BaseModel

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
    ) -> None:
        """Initialize field."""
        self.required = required
        self.default = default
        self.index = index
        self.unique = unique

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
        """Convert value to dict representation."""
        return value

    def to_mongo(self, value: Optional[T]) -> Any:
        """Convert Python value to MongoDB value."""
        return value

    def from_mongo(self, value: Any) -> Optional[T]:
        """Convert MongoDB value to Python value."""
        return self.convert(value)


class StringField(Field[str]):
    """String field."""

    def convert(self, value: Any) -> str:
        """Convert value to string."""
        if value is None:
            return ""
        return str(value)

    def to_mongo(self, value: Optional[str]) -> str:
        """Convert Python string to MongoDB string."""
        if value is None:
            return ""
        return str(value)

    def from_mongo(self, value: Any) -> str:
        """Convert MongoDB string to Python string."""
        if value is None:
            return ""
        return str(value)


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

    def convert(self, value: Any) -> Optional[ObjectId]:
        """Convert value to ObjectId."""
        if value is None:
            return None
        if type(value) is ObjectId:  # type: ignore
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

    def from_mongo(self, value: Any) -> Optional[ObjectId]:
        """Convert MongoDB ObjectId to Python ObjectId."""
        if value is None:
            return None
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

    def convert(self, value: Any) -> Optional[List[T]]:
        """Convert value to list."""
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.convert(item)
            if converted is not None:
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

    def from_mongo(self, value: Any) -> Optional[List[T]]:
        """Convert MongoDB array to Python list."""
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(f"Expected list, got {type(value)}")
        result: List[T] = []
        items: List[Any] = value
        for item in items:
            converted = self.field.from_mongo(item)
            if converted is not None:
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
