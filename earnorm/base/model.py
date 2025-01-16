"""Base model implementation."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor
from pymongo.client_session import ClientSession
from typing_extensions import Self

from earnorm.base.domain.expression import DomainExpression
from earnorm.base.domain.parser import DomainParser
from earnorm.base.fields.metadata import FieldMetadata
from earnorm.base.models.lifecycle import Lifecycle
from earnorm.base.models.persistence import Persistence
from earnorm.base.models.validation import Validator
from earnorm.base.recordset.recordset import RecordSet
from earnorm.base.types import (
    ContainerProtocol,
    DocumentType,
    FieldProtocol,
    ModelProtocol,
    RecordSetProtocol,
)
from earnorm.cache import cached
from earnorm.di import container

logger = logging.getLogger(__name__)

M = TypeVar("M", bound=ModelProtocol)
F = TypeVar("F")
DomainInput = Union[List[Any], DomainExpression]


class BaseModel(ModelProtocol):
    """Base model class.

    All models should inherit from this class. It provides:
    - CRUD operations (search, browse, find_one, save, delete)
    - Event handling via decorators
    - Validation
    - Serialization

    Attributes:
        _name: Model name
        _collection: MongoDB collection name
        _abstract: Whether model is abstract
        _data: Model data dictionary
        _event_handlers: Dictionary of event handlers
        _fields: Dictionary of field metadata
    """

    _name: str = ""
    _collection: str = ""
    _abstract: bool = False
    _data: DocumentType = {}
    _indexes: List[DocumentType] = []
    _fields: Dict[str, FieldMetadata] = {}
    __annotations__: Dict[str, Any] = {}

    def __new__(cls: Type[Self], **kwargs: Any) -> RecordSet[Self]:
        """Create new instance.

        This method is called before __init__ when creating a new instance.
        It returns a RecordSet containing a single record.

        Args:
            **kwargs: Model data

        Returns:
            RecordSet containing the new instance

        Examples:
            >>> user = User(name="admin")  # Returns RecordSet[User]
            >>> print(user.name)  # Can access fields directly
            >>> users = user.filter(active=True)  # Can use RecordSet methods
        """
        instance = super().__new__(cls)
        instance.__init__(**kwargs)  # type: ignore
        return RecordSet(cls, [cast(Self, instance)])

    def __init__(self, **kwargs: Any) -> None:
        """Initialize model.

        Args:
            **kwargs: Model data
        """
        self._data = kwargs
        self._validator = Validator()
        self._persistence = Persistence()
        self._lifecycle: Lifecycle[ModelProtocol] = Lifecycle()

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dict representation.

        Returns:
            Dict containing the model's data in Python format
        """
        return self._data.copy()

    def to_mongo(self) -> Dict[str, Any]:
        """Convert model to MongoDB representation.

        Returns:
            Dict containing the model's data in MongoDB format
        """
        data = self.to_dict()
        if "_id" in data and isinstance(data["_id"], str):
            data["_id"] = ObjectId(data["_id"])
        return data

    def from_mongo(self, data: Dict[str, Any]) -> None:
        """Convert MongoDB data to model.

        Args:
            data: Dict containing the model's data in MongoDB format
        """
        if "_id" in data and isinstance(data["_id"], ObjectId):
            data["_id"] = str(data["_id"])
        self._data = data

    @property
    def data(self) -> DocumentType:
        """Get model data."""
        return self._data

    @classmethod
    def get_collection_name(cls) -> str:
        """Get collection name."""
        return cls._collection

    @classmethod
    def get_name(cls) -> str:
        """Get model name."""
        return cls._name

    @classmethod
    def get_indexes(cls) -> List[DocumentType]:
        """Get model indexes."""
        return cls._indexes

    @classmethod
    async def search(
        cls: Type[M],
        domain: Optional[DomainInput] = None,
        **kwargs: Any,
    ) -> RecordSetProtocol[M]:
        """Search records and return RecordSet.

        Args:
            domain: Domain expression for filtering records. Can be:
                - List of conditions: [["field", "operator", value], ...]
                - DomainExpression instance
            **kwargs: Additional search parameters (sort, limit, skip)

        Returns:
            RecordSet containing matching records of type M

        Examples:
            >>> # Search by age
            >>> users = await User.search([["age", ">", 18]])
            >>> for user in users:
            ...     print(user.name)  # Can access User-specific fields
        """
        filter_dict = {}
        if domain is not None:
            parser = DomainParser()
            if isinstance(domain, list):
                domain_expr = DomainExpression(domain)
                filter_dict = parser.parse(domain_expr)
            else:
                filter_dict = parser.parse(domain)

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[cls.get_collection_name()]

        cursor: AsyncIOMotorCursor[DocumentType] = collection.find(
            filter_dict, **kwargs
        )
        records: List[M] = []
        async for doc in cursor:
            instance = cls()
            instance.from_mongo(doc)
            records.append(instance)

        result: RecordSetProtocol[M] = RecordSet[M](cls, records)
        return cast(RecordSetProtocol[M], result)

    @classmethod
    async def browse(cls: Type[M], ids: List[str]) -> RecordSetProtocol[M]:
        """Browse records by IDs.

        Args:
            ids: List of record IDs to browse

        Returns:
            RecordSet containing matching records of type M

        Examples:
            >>> user_ids = ["1", "2", "3"]
            >>> users = await User.browse(user_ids)
            >>> for user in users:
            ...     print(user.name)  # Can access User-specific fields
        """
        if not ids:
            result: RecordSetProtocol[M] = RecordSet[M](cls)
            return cast(RecordSetProtocol[M], result)

        object_ids = [ObjectId(id_) for id_ in ids]
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[cls.get_collection_name()]

        cursor: AsyncIOMotorCursor[DocumentType] = collection.find(
            {"_id": {"$in": object_ids}}
        )
        records: List[M] = []
        async for doc in cursor:
            instance = cls()
            instance.from_mongo(doc)
            records.append(instance)

        result: RecordSetProtocol[M] = RecordSet[M](cls, records)
        return cast(RecordSetProtocol[M], result)

    @classmethod
    async def find_one(
        cls: Type[M], domain: Optional[List[Any]] = None, **kwargs: Any
    ) -> RecordSetProtocol[M]:
        """Find single record.

        Args:
            domain: Domain expression for filtering records
            **kwargs: Additional search parameters

        Returns:
            RecordSet containing at most one record of type M

        Examples:
            >>> user = await User.find_one([["email", "=", "john@example.com"]])
            >>> if await user.exists():
            ...     record = (await user.all())[0]
            ...     print(record.name)  # Can access User-specific fields
        """
        filter_dict = {}
        if domain is not None:
            parser = DomainParser()
            domain_expr = DomainExpression(domain)
            filter_dict = parser.parse(domain_expr)

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection: AsyncIOMotorCollection[DocumentType] = db[cls.get_collection_name()]

        doc = await collection.find_one(filter_dict, **kwargs)
        if doc is None:
            result: RecordSetProtocol[M] = RecordSet[M](cls)
            return cast(RecordSetProtocol[M], result)

        instance = cls()
        instance.from_mongo(doc)
        result: RecordSetProtocol[M] = RecordSet[M](cls, [instance])
        return cast(RecordSetProtocol[M], result)

    @property
    def id(self) -> Optional[str]:
        """Get record ID."""
        return str(self._data["_id"]) if "_id" in self._data else None

    async def validate(self) -> None:
        """Validate record."""
        await self._validator.validate(cast(ModelProtocol, self))

    async def save(self) -> None:
        """Save record."""
        await self._lifecycle.before_save(self)
        await self.validate()
        await self._persistence.save(self)
        await self._lifecycle.after_save(self)

    async def delete(self) -> None:
        """Delete record."""
        await self._lifecycle.before_delete(self)
        await self._persistence.delete(self)
        await self._lifecycle.after_delete(self)

    def __getattr__(self, name: str) -> Any:
        """Get dynamic attribute.

        This method is called when an attribute is not found in the class.
        It first checks if the attribute is a field, and if so, returns its value with the correct type.
        Otherwise, it looks up the attribute in the model's data dictionary.

        Args:
            name: Name of the attribute

        Returns:
            Attribute value with the correct type based on field definition

        Raises:
            AttributeError: If attribute not found

        Examples:
            >>> class User(BaseModel):
            ...     name = fields.String()
            ...     age = fields.Integer()
            >>> user = User(name="admin", age=25)
            >>> user.name  # Returns str
            >>> user.age   # Returns int
        """
        # First check if it's a field
        if name in self._fields:
            metadata = self._fields[name]
            field = cast(FieldProtocol[Any], metadata.field)
            if name in self._data:
                return field.convert(self._data[name])  # Convert to correct type
            return field.convert(
                field.default
            )  # Return default value with correct type

        # Then check in data dictionary
        if name in self._data:
            return self._data[name]

        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute value.

        This method is called when setting an attribute value.
        It first checks if the attribute is a field, and if so, converts and validates the value.
        Otherwise, it sets the attribute directly.

        Args:
            name: Name of the attribute
            value: Value to set

        Raises:
            ValidationError: If field validation fails
            AttributeError: If attribute not found

        Examples:
            >>> class User(BaseModel):
            ...     name = fields.String()
            ...     age = fields.Integer()
            >>> user = User()
            >>> user.name = "admin"  # Sets str value
            >>> user.age = "25"      # Converts to int
        """
        # Handle special attributes
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        # Handle fields
        if name in self._fields:
            metadata = self._fields[name]
            field = cast(FieldProtocol[Any], metadata.field)
            converted_value = field.convert(value)  # Convert to correct type
            self._data[name] = converted_value
            return

        # Handle regular attributes
        super().__setattr__(name, value)

    @classmethod
    @cached(ttl=300)
    async def find(
        cls,
        filter: DocumentType,
        sort: Optional[List[Tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
        session: Optional[ClientSession] = None,
    ) -> List[ModelProtocol]:
        """Find models by filter.

        Args:
            filter: Query filter
            sort: Sort specification as list of (field, direction) tuples
            limit: Maximum number of records
            skip: Number of records to skip
            collection: Optional collection instance
            session: Optional session for transactions

        Returns:
            List of model instances

        Raises:
            ValueError: If filter is invalid
            TypeError: If sort specification is invalid
        """
        if collection is None:
            container_instance = cast(ContainerProtocol, container)
            registry = container_instance.registry
            db = registry.db
            collection = db[cls._collection]

        cursor: AsyncIOMotorCursor[DocumentType] = collection.find(
            filter, session=session
        )

        if sort:
            cursor.sort(sort)
        if limit:
            cursor.limit(limit)
        if skip:
            cursor.skip(skip)

        records: List[ModelProtocol] = []
        async for data in cursor:
            model = cls(**data)
            model.from_mongo(data)
            records.append(cast(ModelProtocol, model))

        return records

    @classmethod
    async def _domain_to_filter(cls, domain: List[Any]) -> DocumentType:
        """Convert domain to MongoDB filter.

        Args:
            domain: Domain expression as list of conditions

        Returns:
            MongoDB filter dict

        Raises:
            ValueError: If domain expression is invalid
            TypeError: If domain items are not in correct format

        Examples:
            >>> await Model._domain_to_filter([["age", ">", 18]])
            {'age': {'$gt': 18}}
            >>> await Model._domain_to_filter([
            ...     ["age", ">", 18],
            ...     "AND",
            ...     ["active", "=", True]
            ... ])
            {'$and': [{'age': {'$gt': 18}}, {'active': True}]}
        """
        if not domain:
            return {}

        # Convert legacy domain format to DomainExpression
        expr = DomainExpression(domain)
        parser = DomainParser()
        return parser.parse(expr)

    @classmethod
    @cached(ttl=300)
    async def get_by_id(cls: Type[M], id: str) -> Optional[M]:
        """Get model by ID.

        Args:
            id: Model ID

        Returns:
            Model instance if found, None otherwise

        Raises:
            ValueError: If ID is empty or invalid
        """
        if not id:
            raise ValueError("ID cannot be empty")

        try:
            object_id = ObjectId(id)
        except Exception as e:
            raise ValueError(f"Invalid ID format: {e}")

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        collection = db[cls._collection]

        data = await collection.find_one({"_id": object_id})
        if not data:
            return None

        model = cls(**data)
        model.from_mongo(data)
        return model

    @classmethod
    @cached(ttl=300)
    async def count(
        cls,
        filter: DocumentType,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
        session: Optional[ClientSession] = None,
    ) -> int:
        """Count models by filter.

        Args:
            filter: Filter conditions
            collection: Optional collection instance
            session: Optional client session

        Returns:
            int: Number of models
        """
        if collection is None:
            container_instance = cast(ContainerProtocol, container)
            registry = container_instance.registry
            db = registry.db
            collection = db[cls._collection]

        return await collection.count_documents(filter, session=session)  # type: ignore

    def __str__(self) -> str:
        """Get string representation."""
        return f"{self.__class__.__name__}({self.id})"

    def __repr__(self) -> str:
        """Get string representation."""
        return self.__str__()
