"""Relation field types for EarnORM."""

from typing import Any, Dict, Generic, List, Optional, Self, Type, TypeVar, Union, cast

from bson import ObjectId

from earnorm.base.model import BaseModel
from earnorm.fields.base import Field

M = TypeVar("M", bound="BaseModel")
T = TypeVar("T")


class BaseRelationField(Field[M], Generic[M]):
    """Base class for relation fields."""

    def __init__(
        self,
        referenced_model: Type[M],
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
        self.referenced_model = referenced_model
        super().__init__(required=required, unique=unique, default=default, **kwargs)

    def __get__(
        self, instance: Optional[BaseModel], owner: Type[BaseModel]
    ) -> Union[Self, Optional[M]]:
        """Get field value."""
        if instance is None:
            return self
        return instance.data.get(self.name)

    def __set__(
        self,
        instance: Optional[BaseModel],
        value: Optional[Union[str, ObjectId, Dict[str, Any], M]],
    ) -> None:
        """Set field value."""
        if instance is None:
            return
        instance.data[self.name] = value

    def __delete__(self, instance: Optional[BaseModel]) -> None:
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
            record = await self.referenced_model.find_one({"_id": ObjectId(str(value))})
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
        referenced_model: Type[M],
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
        self._referenced_model: Type[M] = referenced_model
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
        return getattr(self.referenced_model, "collection", "")

    def convert(self, value: Any) -> Optional[M]:
        """Convert value to model instance."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            if self.lazy:
                return self.referenced_model(
                    _collection=self.collection,
                    id=value,
                    _abstract=False,
                    _indexes=[],
                )
            return None  # Async operation not supported in sync convert
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(
                _collection=self.collection,
                _abstract=False,
                _indexes=[],
                **value,
            )
        return self.referenced_model(
            _collection=self.collection,
            id=ObjectId(str(value)),
            _abstract=False,
            _indexes=[],
        )

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
            record = await self.referenced_model.find_one({"_id": ObjectId(str(value))})
            if record:
                return cast(M, record)
            return None
        if isinstance(value, dict):
            return self.referenced_model(**value)
        raise ValueError(f"Cannot convert {value} to {self.referenced_model}")

    def to_dict(self, value: Optional[M]) -> Optional[str]:
        """Convert reference to dict representation."""
        if value is None:
            return None
        return str(value.id)

    def to_mongo(self, value: Optional[M]) -> Optional[ObjectId]:
        """Convert Python model instance to MongoDB ObjectId."""
        if value is None:
            return None
        if isinstance(value, ObjectId):
            return value
        if isinstance(value, self.referenced_model):
            return ObjectId(str(value.id)) if value.id else None
        if isinstance(value, dict) and "_id" in value:
            id_value: Any = value["_id"]
            if isinstance(id_value, ObjectId):
                return id_value
            return ObjectId(str(id_value))
        return ObjectId(str(value))

    def from_mongo(self, value: Any) -> Optional[M]:
        """Convert MongoDB ObjectId to Python model instance."""
        if value is None:
            return None
        if isinstance(value, self.referenced_model):
            return value
        if isinstance(value, dict):
            return self.referenced_model(
                _collection=self.collection,
                _abstract=False,
                _indexes=[],
                **value,
            )
        if isinstance(value, ObjectId):
            if self.lazy:
                return self.referenced_model(
                    _collection=self.collection,
                    id=value,
                    _abstract=False,
                    _indexes=[],
                )
            return None  # Async operation not supported in sync convert
        return self.referenced_model(
            _collection=self.collection,
            id=ObjectId(str(value)),
            _abstract=False,
            _indexes=[],
        )


class Many2oneField(ReferenceField[M], Generic[M]):
    """Many2one field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        *,
        required: bool = False,
        default: Any = None,
        index: bool = False,
        unique: bool = False,
        ondelete: str = "set null",
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
        self.ondelete = ondelete


class One2manyField(Field[List[M]], Generic[M]):
    """One2many field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        inverse_field: str,
        *,
        required: bool = False,
        default: Any = None,
        lazy: bool = False,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
        )
        self._referenced_model: Type[M] = referenced_model
        self.inverse_field = inverse_field
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
        return getattr(self.referenced_model, "collection", "")

    def convert(
        self, value: Optional[Union[List[Union[str, ObjectId, Dict[str, Any], M]], M]]
    ) -> List[M]:
        """Convert value to list of referenced records."""
        if value is None:
            return []
        values: List[Union[str, ObjectId, Dict[str, Any], M]] = (
            [value] if not isinstance(value, (list, tuple)) else list(value)
        )

        records: List[M] = []
        for item in values:
            record: Optional[M] = None
            if isinstance(item, ObjectId):
                if self.lazy:
                    record = self.referenced_model(
                        _collection=self.collection,
                        id=item,
                        _abstract=False,
                        _indexes=[],
                    )
            elif isinstance(item, self.referenced_model):
                record = item
            elif isinstance(item, dict):
                record = self.referenced_model(
                    _collection=self.collection,
                    _abstract=False,
                    _indexes=[],
                    **item,
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        record = self.referenced_model(
                            _collection=self.collection,
                            id=item_id,
                            _abstract=False,
                            _indexes=[],
                        )
                except (TypeError, ValueError):
                    continue
            if record is not None:
                records.append(record)
        return records

    async def async_convert(self, value: Any) -> List[M]:
        """Convert value to list of referenced records asynchronously."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in cast(List[Any], value):
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,
                            _abstract=False,
                            _indexes=[],
                        )
                    )
                else:
                    record = await self.referenced_model.find_one({"_id": item})
                    if record:
                        records.append(cast(M, record))
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
                        record = await self.referenced_model.find_one({"_id": item_id})
                        if record:
                            records.append(record)  # type: ignore
                except (TypeError, ValueError):
                    continue
        return records

    def to_dict(self, value: Optional[List[M]]) -> Optional[List[str]]:
        """Convert references to dict representation."""
        if value is None:
            return None
        return [str(record.id) for record in value]

    def to_mongo(self, value: Optional[List[M]]) -> Optional[List[ObjectId]]:
        """Convert Python model instances to MongoDB ObjectIds."""
        if value is None:
            return None
        result: List[ObjectId] = []
        for item in value:
            if isinstance(item, ObjectId):
                result.append(item)
            elif isinstance(item, self.referenced_model):
                if item.id:  # Check if id exists
                    result.append(ObjectId(str(item.id)))
            elif isinstance(item, dict) and "_id" in item:
                id_value: Any = item["_id"]
                if isinstance(id_value, ObjectId):
                    result.append(id_value)
                else:
                    result.append(ObjectId(str(id_value)))
            else:
                result.append(ObjectId(str(item)))
        return result

    def from_mongo(self, value: Any) -> List[M]:
        """Convert MongoDB ObjectIds to Python model instances."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in cast(List[Any], value):
            if isinstance(item, self.referenced_model):
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
            elif isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,
                            _abstract=False,
                            _indexes=[],
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


class Many2manyField(Field[List[M]], Generic[M]):
    """Many2many field for model relations."""

    def __init__(
        self,
        referenced_model: Type[M],
        *,
        required: bool = False,
        default: Any = None,
        lazy: bool = False,
        relation: Optional[str] = None,
        column1: Optional[str] = None,
        column2: Optional[str] = None,
    ) -> None:
        """Initialize field."""
        super().__init__(
            required=required,
            default=default,
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

    def convert(
        self, value: Optional[Union[List[Union[str, ObjectId, Dict[str, Any], M]], M]]
    ) -> List[M]:
        """Convert value to list of referenced records."""
        if value is None:
            return []
        values: List[Union[str, ObjectId, Dict[str, Any], M]] = (
            [value] if not isinstance(value, (list, tuple)) else list(value)
        )

        records: List[M] = []
        for item in values:
            record: Optional[M] = None
            if isinstance(item, ObjectId):
                if self.lazy:
                    record = self.referenced_model(
                        _collection=self.collection,
                        id=item,
                        _abstract=False,
                        _indexes=[],
                    )
            elif isinstance(item, self.referenced_model):
                record = item
            elif isinstance(item, dict):
                record = self.referenced_model(
                    _collection=self.collection,
                    _abstract=False,
                    _indexes=[],
                    **item,
                )
            else:
                try:
                    item_id = ObjectId(str(item))
                    if self.lazy:
                        record = self.referenced_model(
                            _collection=self.collection,
                            id=item_id,
                            _abstract=False,
                            _indexes=[],
                        )
                except (TypeError, ValueError):
                    continue
            if record is not None:
                records.append(record)
        return records

    async def async_convert(
        self, value: Optional[Union[List[Union[str, ObjectId, Dict[str, Any], M]], M]]
    ) -> List[M]:
        """Convert value to list of referenced records asynchronously."""
        if value is None:
            return []
        values: List[Union[str, ObjectId, Dict[str, Any], M]] = (
            [value] if not isinstance(value, (list, tuple)) else list(value)
        )

        records: List[M] = []
        for item in values:
            if isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,
                            _abstract=False,
                            _indexes=[],
                        )
                    )
                else:
                    record = await self.referenced_model.find_one({"_id": item})
                    if record:
                        records.append(cast(M, record))
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
                        record = await self.referenced_model.find_one({"_id": item_id})
                        if record:
                            records.append(cast(M, record))
                except (TypeError, ValueError):
                    continue
        return records

    def to_dict(self, value: Optional[List[M]]) -> Optional[List[str]]:
        """Convert references to dict representation."""
        if value is None:
            return None
        return [str(record.id) for record in value]

    def to_mongo(self, value: Optional[List[M]]) -> Optional[List[ObjectId]]:
        """Convert Python model instances to MongoDB ObjectIds."""
        if value is None:
            return None
        result: List[ObjectId] = []
        for item in value:
            if isinstance(item, ObjectId):
                result.append(item)
            elif isinstance(item, self.referenced_model):
                if item.id:  # Check if id exists
                    result.append(ObjectId(str(item.id)))
            elif isinstance(item, dict) and "_id" in item:
                id_value: Any = item["_id"]
                if isinstance(id_value, ObjectId):
                    result.append(id_value)
                else:
                    result.append(ObjectId(str(id_value)))
            else:
                result.append(ObjectId(str(item)))
        return result

    def from_mongo(self, value: Any) -> List[M]:
        """Convert MongoDB ObjectIds to Python model instances."""
        if value is None:
            return []
        if not isinstance(value, (list, tuple)):
            value = [value]

        records: List[M] = []
        for item in cast(List[Any], value):
            if isinstance(item, self.referenced_model):
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
            elif isinstance(item, ObjectId):
                if self.lazy:
                    records.append(
                        self.referenced_model(
                            _collection=self.collection,
                            id=item,
                            _abstract=False,
                            _indexes=[],
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
