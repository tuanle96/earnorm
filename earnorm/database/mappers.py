"""Database type mappers.

This module provides type mapping between field types and database types.
It supports multiple database backends and custom type mapping.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, TypeVar

from earnorm.database.type_mapping import get_field_options, get_field_type
from earnorm.fields.base import BaseField

T = TypeVar("T")


class DatabaseTypeMapper(ABC):
    """Abstract base class for database type mapping.

    This class defines the interface for mapping field types to database types.
    Each database backend should implement its own mapper.
    """

    @abstractmethod
    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get database field type.

        Args:
            field: Field instance to map

        Returns:
            Database type name
        """
        pass

    @abstractmethod
    def get_field_options(self, field: BaseField[Any]) -> Dict[str, Any]:
        """Get database field options.

        Args:
            field: Field instance to map

        Returns:
            Dictionary of field options
        """
        pass


class MongoDBTypeMapper(DatabaseTypeMapper):
    """MongoDB type mapper implementation."""

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get MongoDB field type.

        Args:
            field: Field instance to map

        Returns:
            MongoDB type name
        """
        field_type = field.__class__.__name__.lower().replace("field", "")
        return get_field_type(field_type, "mongodb")

    def get_field_options(self, field: BaseField[Any]) -> Dict[str, Any]:
        """Get MongoDB field options.

        Args:
            field: Field instance to map

        Returns:
            Dictionary of field options
        """
        options = get_field_options("mongodb")

        # Add index options
        if getattr(field, "index", False):
            options["index"] = True

        # Add unique constraint
        if getattr(field, "unique", False):
            options["unique"] = True

        # Add sparse index for nullable fields
        if not getattr(field, "required", False):
            options["sparse"] = True

        # Add text index for string fields
        if field_type := getattr(field, "field_type", ""):
            if field_type == "string" and getattr(field, "text_index", False):
                options["text"] = True

        return options


class PostgresTypeMapper(DatabaseTypeMapper):
    """PostgreSQL type mapper implementation."""

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get PostgreSQL field type.

        Args:
            field: Field instance to map

        Returns:
            PostgreSQL type name
        """
        field_type = field.__class__.__name__.lower().replace("field", "")
        db_type = get_field_type(field_type, "postgres")

        # Handle special cases
        if field_type == "string":
            max_length = getattr(field, "max_length", None)
            if max_length:
                return f"VARCHAR({max_length})"
        elif field_type == "decimal":
            max_digits = getattr(field, "max_digits", 10)
            decimal_places = getattr(field, "decimal_places", 2)
            return f"DECIMAL({max_digits},{decimal_places})"

        return db_type

    def get_field_options(self, field: BaseField[Any]) -> Dict[str, Any]:
        """Get PostgreSQL field options.

        Args:
            field: Field instance to map

        Returns:
            Dictionary of field options
        """
        options = get_field_options("postgres")

        # Add index options
        if getattr(field, "index", False):
            options["index"] = True
            field_type = field.__class__.__name__.lower().replace("field", "")
            if field_type in ["list", "set", "tuple", "dict", "json"]:
                options["using"] = "gin"

        # Add unique constraint
        if getattr(field, "unique", False):
            options["unique"] = True

        # Add not null constraint
        if getattr(field, "required", False):
            options["nullable"] = False

        return options


class MySQLTypeMapper(DatabaseTypeMapper):
    """MySQL type mapper implementation."""

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get MySQL field type.

        Args:
            field: Field instance to map

        Returns:
            MySQL type name
        """
        field_type = field.__class__.__name__.lower().replace("field", "")
        db_type = get_field_type(field_type, "mysql")

        # Handle special cases
        if field_type == "string":
            max_length = getattr(field, "max_length", None)
            if max_length:
                return f"VARCHAR({max_length})"
        elif field_type == "decimal":
            max_digits = getattr(field, "max_digits", 10)
            decimal_places = getattr(field, "decimal_places", 2)
            return f"DECIMAL({max_digits},{decimal_places})"

        return db_type

    def get_field_options(self, field: BaseField[Any]) -> Dict[str, Any]:
        """Get MySQL field options.

        Args:
            field: Field instance to map

        Returns:
            Dictionary of field options
        """
        options = get_field_options("mysql")

        # Add index options
        if getattr(field, "index", False):
            options["index"] = True

        # Add unique constraint
        if getattr(field, "unique", False):
            options["unique"] = True

        # Add not null constraint
        if getattr(field, "required", False):
            options["nullable"] = False

        # Add character set for string fields
        field_type = field.__class__.__name__.lower().replace("field", "")
        if field_type == "string":
            options["charset"] = "utf8mb4"
            options["collate"] = "utf8mb4_unicode_ci"

        return options


def get_mapper(backend: str) -> DatabaseTypeMapper:
    """Get database type mapper for backend.

    Args:
        backend: Database backend name

    Returns:
        Database type mapper instance

    Raises:
        ValueError: If backend not supported
    """
    mappers = {
        "mongodb": MongoDBTypeMapper,
        "postgres": PostgresTypeMapper,
        "mysql": MySQLTypeMapper,
    }

    mapper_class = mappers.get(backend)
    if mapper_class is None:
        raise ValueError(f"Unsupported database backend: {backend}")

    return mapper_class()
