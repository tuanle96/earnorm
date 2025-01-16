"""Model interface definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.types import DocumentType

T = TypeVar("T", bound="ModelInterface")


class ModelInterface(ABC):
    """Base model interface.

    This interface defines the core functionality that all models must implement:
    - CRUD operations (find, save, delete)
    - Data access (id, data)
    - Validation

    Attributes:
        _name: Model name
        _collection: MongoDB collection name
        _abstract: Whether model is abstract
        _data: Model data dictionary
    """

    _name: str = ""
    _collection: str = ""
    _abstract: bool = False
    _data: DocumentType = {}

    @property
    @abstractmethod
    def id(self) -> Optional[str]:
        """Get model ID.

        Returns:
            Optional[str]: Model ID if exists
        """
        pass

    @property
    @abstractmethod
    def data(self) -> DocumentType:
        """Get model data.

        Returns:
            DocumentType: Model data dictionary
        """
        pass

    @classmethod
    @abstractmethod
    async def find_one(
        cls,
        filter: DocumentType,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
    ) -> Optional[ModelInterface]:
        """Find single record.

        Args:
            filter: Query filter
            collection: Optional collection instance

        Returns:
            Optional[ModelInterface]: Found record or None
        """
        pass

    @classmethod
    @abstractmethod
    async def find(
        cls,
        filter: DocumentType,
        sort: Optional[List[tuple[str, int]]] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        collection: Optional[AsyncIOMotorCollection[DocumentType]] = None,
    ) -> List[ModelInterface]:
        """Find multiple records.

        Args:
            filter: Query filter
            sort: Sort specification
            limit: Maximum number of records
            skip: Number of records to skip
            collection: Optional collection instance

        Returns:
            List[ModelInterface]: List of found records
        """
        pass

    @abstractmethod
    async def validate(self) -> None:
        """Validate model data.

        Raises:
            ValidationError: If validation fails
        """
        pass

    @abstractmethod
    async def save(self) -> None:
        """Save model to database.

        Raises:
            ValidationError: If validation fails
            PersistenceError: If save fails
        """
        pass

    @abstractmethod
    async def delete(self) -> None:
        """Delete model from database.

        Raises:
            PersistenceError: If delete fails
        """
        pass
