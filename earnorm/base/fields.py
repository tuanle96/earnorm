"""Field type definitions."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints

from bson import ObjectId
from pydantic import Field as PydanticField
from pydantic import validator
from pydantic.fields import FieldInfo


class FieldType(Enum):
    """Field types supported by EarnORM."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    OBJECTID = "objectid"
    LIST = "list"
    DICT = "dict"
    REFERENCE = "reference"
    EMBEDDED = "embedded"


class Field(PydanticField):
    """Base field class with extended functionality."""

    def __init__(
        self,
        default: Any = None,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        unique: bool = False,
        index: bool = False,
        required: bool = True,
        readonly: bool = False,
        computed: Optional[str] = None,
        depends: Optional[List[str]] = None,
        store: bool = True,
        **extra: Any,
    ) -> None:
        """Initialize field with extended options."""
        super().__init__(default=default, title=title, description=description, **extra)
        self.unique = unique
        self.index = index
        self.required = required
        self.readonly = readonly
        self.computed = computed
        self.depends = depends or []
        self.store = store
        self._validators = []

    def add_validator(self, validator_func: callable) -> None:
        """Add a validator function."""
        self._validators.append(validator_func)

    async def validate(self, value: Any) -> Any:
        """Run all validators on value."""
        for validator in self._validators:
            value = await validator(value)
        return value


class StringField(Field):
    """String field type."""

    def __init__(
        self,
        *,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        regex: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.regex = regex


class IntegerField(Field):
    """Integer field type."""

    def __init__(
        self,
        *,
        minimum: Optional[int] = None,
        maximum: Optional[int] = None,
        multiple_of: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.multiple_of = multiple_of


class FloatField(Field):
    """Float field type."""

    def __init__(
        self,
        *,
        minimum: Optional[float] = None,
        maximum: Optional[float] = None,
        multiple_of: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.minimum = minimum
        self.maximum = maximum
        self.multiple_of = multiple_of


class BooleanField(Field):
    """Boolean field type."""

    pass


class DateTimeField(Field):
    """DateTime field type."""

    def __init__(
        self, *, auto_now: bool = False, auto_now_add: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add


class ObjectIdField(Field):
    """ObjectId field type."""

    @validator("*")
    def validate_objectid(cls, v: Any) -> ObjectId:
        if isinstance(v, str):
            return ObjectId(v)
        return v


class ListField(Field):
    """List field type."""

    def __init__(
        self,
        item_type: Type[Field],
        *,
        min_items: Optional[int] = None,
        max_items: Optional[int] = None,
        unique_items: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.item_type = item_type
        self.min_items = min_items
        self.max_items = max_items
        self.unique_items = unique_items


class DictField(Field):
    """Dict field type."""

    def __init__(self, value_type: Optional[Type[Field]] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.value_type = value_type


class ReferenceField(Field):
    """Reference field type."""

    def __init__(
        self,
        to: Union[str, Type["BaseModel"]],
        *,
        on_delete: str = "CASCADE",
        lazy: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.to = to
        self.on_delete = on_delete
        self.lazy = lazy

    async def resolve(self, value: Any) -> Optional["BaseModel"]:
        """Resolve reference to actual model instance."""
        if isinstance(self.to, str):
            # Lazy import to avoid circular imports
            from ..registry import get_model

            model_cls = get_model(self.to)
        else:
            model_cls = self.to

        if isinstance(value, ObjectId):
            return await model_cls.find_one(id=value)
        return None


class EmbeddedField(Field):
    """Embedded document field type."""

    def __init__(self, model_type: Type["BaseModel"], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.model_type = model_type

    async def validate(self, value: Any) -> Any:
        """Validate embedded document."""
        if isinstance(value, dict):
            return await self.model_type(**value).validate()
        elif isinstance(value, self.model_type):
            return await value.validate()
        raise ValueError(f"Invalid value for embedded field: {value}")
