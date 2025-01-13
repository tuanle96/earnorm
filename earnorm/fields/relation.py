"""Relation field types for EarnORM."""

from typing import (
    Any,
    Dict,
    ForwardRef,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
)

from bson import ObjectId
from typing_extensions import Self

from earnorm.base.registry import Registry
from earnorm.base.types import ModelProtocol
from earnorm.fields.base import Field

M = TypeVar("M", bound=ModelProtocol)
T = TypeVar("T")


class BaseRelationField(Field[M], Generic[M]):
    """Base class for relation fields."""

    def __init__(
        self,
        referenced_model: Union[str, Type[M], ForwardRef],
        required: bool = False,
        unique: bool = False,
        default: Optional[Union[M, List[M]]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize relation field.

        Args:
            referenced_model: The model class that this field references
            required: Whether this field is required
            unique: Whether this field should be unique
            default: Default value for this field
            **kwargs: Additional arguments passed to Field constructor
        """
        self._model_registry = Registry()
        self._referenced_model_name: str = ""
        self._referenced_model_class: Optional[Type[M]] = None

        if isinstance(referenced_model, str):
            self._referenced_model_name = referenced_model
        elif isinstance(referenced_model, ForwardRef):
            self._referenced_model_name = referenced_model.__forward_arg__
        else:
            self._referenced_model_name = referenced_model.__name__
            self._referenced_model_class = referenced_model

        super().__init__(required=required, unique=unique, default=default, **kwargs)

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model class."""
        if self._referenced_model_class is None:
            model_class = self._model_registry.get_model(self._referenced_model_name)
            if model_class is None:
                raise ValueError(
                    f"Model {self._referenced_model_name} not found in registry"
                )
            self._referenced_model_class = cast(Type[M], model_class)
        return self._referenced_model_class

    @property
    def collection(self) -> str:
        """Get collection name."""
        return getattr(self.referenced_model, "collection", "")

    def __get__(
        self, instance: Optional[ModelProtocol], owner: Type[ModelProtocol]
    ) -> Union[Self, M]:
        """Get field value."""
        if instance is None:
            return self
        value = instance.data.get(self.name)
        if value is None:
            # Create empty instance instead of returning None
            return self.referenced_model()
        return value

    def __set__(
        self,
        instance: Optional[ModelProtocol],
        value: Optional[Union[str, ObjectId, Dict[str, Any], M]],
    ) -> None:
        """Set field value."""
        if instance is None:
            return
        instance.data[self.name] = value

    def __delete__(self, instance: Optional[ModelProtocol]) -> None:
        """Delete field value."""
        if instance is None:
            return
        instance.data.pop(self.name, None)

    async def async_convert(
        self, value: Optional[Union[str, ObjectId, Dict[str, Any], M]]
    ) -> Optional[M]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted value as model instance or None
        """
        if value is None:
            return None
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, (str, ObjectId)):
            record = await self.referenced_model.find_one(
                [("_id", "=", ObjectId(str(value)))]
            )
            if record:
                return cast(M, record)
            return None
        if isinstance(value, dict):
            return self.referenced_model(**value)
        raise ValueError(f"Cannot convert {value} to {self.referenced_model}")


class ReferenceField(Field[M], Generic[M]):
    """Reference field for model relations."""

    def __init__(
        self,
        referenced_model: Union[str, Type[M], ForwardRef],
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        lazy: bool = False,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
        )
        self._referenced_model: Type[M] = cast(Type[M], referenced_model)
        self.lazy = lazy

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return self.referenced_model.get_collection_name()

    def convert(self, value: Any) -> M:
        """Convert value to model instance."""
        if value is None:
            # Create empty instance instead of returning None
            return self.referenced_model()
        if isinstance(value, ObjectId):
            if self.lazy:
                model = self.referenced_model()
                model.data["_id"] = value
                return model
            raise ValueError("Cannot convert ObjectId in sync mode")
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(**value)
        model = self.referenced_model()
        model.data["_id"] = ObjectId(str(value))
        return model

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB ObjectId to Python model instance."""
        if value is None:
            # Create empty instance instead of returning None
            return self.referenced_model()
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(**value)
        model = self.referenced_model()
        model.data["_id"] = ObjectId(str(value))
        return model

    async def async_convert(
        self, value: Optional[Union[str, ObjectId, Dict[str, Any], M]]
    ) -> Optional[M]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted value as model instance or None
        """
        if value is None:
            return None
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, (str, ObjectId)):
            record = await self.referenced_model.find_one(
                [("_id", "=", ObjectId(str(value)))]
            )
            if record:
                return cast(M, record)
            return None
        if isinstance(value, dict):
            return self.referenced_model(**value)
        raise ValueError(f"Cannot convert {value} to {self.referenced_model}")


class Many2oneField(ReferenceField[M], Generic[M]):
    """Many-to-one relation field."""

    def __init__(
        self,
        referenced_model: Union[str, Type[M], ForwardRef],
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        lazy: bool = False,
    ) -> None:
        """Initialize field."""
        super().__init__(
            referenced_model,
            required=required,
            default=default,
            index=index,
            unique=unique,
            lazy=lazy,
        )

    def convert(self, value: Any) -> M:
        """Convert value to model instance."""
        if value is None:
            # Create empty instance instead of returning None
            return self.referenced_model()
        if isinstance(value, ObjectId):
            if self.lazy:
                model = self.referenced_model()
                model.data["_id"] = value
                return model
            raise ValueError("Cannot convert ObjectId in sync mode")
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(**value)
        model = self.referenced_model()
        model.data["_id"] = ObjectId(str(value))
        return model

    def from_mongo(self, value: Any) -> M:
        """Convert MongoDB ObjectId to Python model instance."""
        if value is None:
            # Create empty instance instead of returning None
            return self.referenced_model()
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(**value)
        model = self.referenced_model()
        model.data["_id"] = ObjectId(str(value))
        return model

    async def async_convert(
        self, value: Optional[Union[str, ObjectId, Dict[str, Any], M]]
    ) -> Optional[M]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted value as model instance or None
        """
        if value is None:
            return None
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, (str, ObjectId)):
            record = await self.referenced_model.find_one(
                [("_id", "=", ObjectId(str(value)))]
            )
            if record:
                return cast(M, record)
            return None
        if isinstance(value, dict):
            return self.referenced_model(**value)
        raise ValueError(f"Cannot convert {value} to {self.referenced_model}")


class One2manyField(Field[List[M]], Generic[M]):
    """One-to-many relation field."""

    def __init__(
        self,
        referenced_model: Union[str, Type[M], ForwardRef],
        inverse_field: str,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
        )
        self._referenced_model: Type[M] = cast(Type[M], referenced_model)
        self.inverse_field = inverse_field

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return self.referenced_model.get_collection_name()

    def convert(self, value: Any) -> List[M]:
        """Convert value to model instance."""
        if value is None:
            return []
        if isinstance(value, list):
            result: List[M] = []
            for item in cast(List[Union[Dict[str, Any], M]], value):
                if isinstance(item, dict):
                    model = self.referenced_model(**item)
                    result.append(model)
                elif isinstance(item, self.referenced_model):
                    result.append(item)
            return result
        raise ValueError(f"Cannot convert {value} to list of {self.referenced_model}")

    def from_mongo(self, value: Any) -> List[M]:
        """Convert MongoDB ObjectId to Python model instance."""
        if value is None:
            return []
        if isinstance(value, list):
            result: List[M] = []
            for item in cast(List[Union[Dict[str, Any], M]], value):
                if isinstance(item, dict):
                    model = self.referenced_model(**item)
                    result.append(model)
                elif isinstance(item, self.referenced_model):
                    result.append(item)
            return result
        raise ValueError(f"Cannot convert {value} to list of {self.referenced_model}")

    async def async_convert(
        self, value: Optional[Union[List[Dict[str, Any]], List[M]]]
    ) -> Optional[List[M]]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted value as model instance or None
        """
        if value is None:
            return None
        result: List[M] = []
        for item in cast(List[Union[Dict[str, Any], M]], value):
            if isinstance(item, dict):
                model = self.referenced_model(**item)
                result.append(model)
            elif isinstance(item, self.referenced_model):
                result.append(item)
        return result


class Many2manyField(Field[List[M]], Generic[M]):
    """Many-to-many relation field."""

    def __init__(
        self,
        referenced_model: Union[str, Type[M], ForwardRef],
        inverse_field: str,
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
            index=index,
            unique=unique,
        )
        self._referenced_model: Type[M] = cast(Type[M], referenced_model)
        self.inverse_field = inverse_field

    @property
    def referenced_model(self) -> Type[M]:
        """Get referenced model."""
        if not self._referenced_model:
            raise ValueError("Referenced model not set")
        return self._referenced_model

    @property
    def collection(self) -> str:
        """Get collection name."""
        return self.referenced_model.get_collection_name()

    def convert(self, value: Any) -> List[M]:
        """Convert value to model instance."""
        if value is None:
            return []
        if isinstance(value, list):
            result: List[M] = []
            for item in cast(List[Union[Dict[str, Any], M]], value):
                if isinstance(item, dict):
                    model = self.referenced_model(**item)
                    result.append(model)
                elif isinstance(item, self.referenced_model):
                    result.append(item)
            return result
        raise ValueError(f"Cannot convert {value} to list of {self.referenced_model}")

    def from_mongo(self, value: Any) -> List[M]:
        """Convert MongoDB ObjectId to Python model instance."""
        if value is None:
            return []
        if isinstance(value, list):
            result: List[M] = []
            for item in cast(List[Union[Dict[str, Any], M]], value):
                if isinstance(item, dict):
                    model = self.referenced_model(**item)
                    result.append(model)
                elif isinstance(item, self.referenced_model):
                    result.append(item)
            return result
        raise ValueError(f"Cannot convert {value} to list of {self.referenced_model}")

    async def async_convert(
        self, value: Optional[Union[List[Dict[str, Any]], List[M]]]
    ) -> Optional[List[M]]:
        """Convert value to model instance asynchronously.

        Args:
            value: Value to convert

        Returns:
            Converted value as model instance or None
        """
        if value is None:
            return None
        result: List[M] = []
        for item in cast(List[Union[Dict[str, Any], M]], value):
            if isinstance(item, dict):
                model = self.referenced_model(**item)
                result.append(model)
            elif isinstance(item, self.referenced_model):
                result.append(item)
        return result
