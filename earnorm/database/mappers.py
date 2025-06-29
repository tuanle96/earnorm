"""Database type mappers.

This module provides type mapping between field types and database types.
It supports multiple database backends and custom type mapping.

The module implements the Strategy pattern through the DatabaseTypeMapper
abstract base class and concrete implementations for:
- MongoDB
- PostgreSQL
- MySQL

Each mapper handles:
- Field type mapping
- Field options mapping
- Special cases (e.g. VARCHAR length, DECIMAL precision)
- Index options
- Constraints

Examples:
    >>> from earnorm.database.mappers import get_mapper
    >>> from earnorm.fields import StringField

    >>> # Create a field
    >>> name = StringField(max_length=100, index=True)

    >>> # Get PostgreSQL mapper
    >>> mapper = get_mapper("postgres")

    >>> # Get field type and options
    >>> field_type = mapper.get_field_type(name)  # Returns "VARCHAR(100)"
    >>> field_opts = mapper.get_field_options(name)  # Returns {"index": True, ...}
"""

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from earnorm.database.type_mapping import get_field_options, get_field_type
from earnorm.fields.base import BaseField

T = TypeVar("T")


class DatabaseTypeMapper(ABC):
    """Abstract base class for database type mapping.

    This class defines the interface for mapping field types to database types.
    Each database backend should implement its own mapper.

    The class follows the Strategy pattern, allowing different mapping strategies
    for different database backends while maintaining a consistent interface.

    Examples:
        >>> class CustomMapper(DatabaseTypeMapper):
        ...     def get_field_type(self, field):
        ...         return "CUSTOM_TYPE"
        ...     def get_field_options(self, field):
        ...         return {"custom_option": True}

        >>> mapper = CustomMapper()
        >>> field_type = mapper.get_field_type(some_field)
        >>> field_opts = mapper.get_field_options(some_field)
    """

    @abstractmethod
    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get database field type.

        This method should map the field instance to its corresponding
        database type name.

        Args:
            field: Field instance to map

        Returns:
            Database type name

        Examples:
            >>> mapper = PostgresTypeMapper()
            >>> field = StringField(max_length=100)
            >>> mapper.get_field_type(field)
            'VARCHAR(100)'
        """
        pass

    @abstractmethod
    def get_field_options(self, field: BaseField[Any]) -> dict[str, Any]:
        """Get database field options.

        This method should return a dictionary of options for the field
        in the target database.

        Args:
            field: Field instance to map

        Returns:
            Dictionary of field options

        Examples:
            >>> mapper = MongoDBTypeMapper()
            >>> field = StringField(index=True, unique=True)
            >>> mapper.get_field_options(field)
            {'index': True, 'unique': True, 'sparse': True}
        """
        pass


class MongoDBTypeMapper(DatabaseTypeMapper):
    """MongoDB type mapper implementation.

    This mapper handles MongoDB-specific type mapping and options:
    - BSON type mapping
    - Index options
    - Unique constraints
    - Sparse indexes
    - Text indexes for string fields

    Examples:
        >>> mapper = MongoDBTypeMapper()
        >>> field = StringField(text_index=True)
        >>> field_type = mapper.get_field_type(field)  # Returns "string"
        >>> field_opts = mapper.get_field_options(field)  # Returns {"text": True, ...}
    """

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get MongoDB field type.

        Maps Python field types to MongoDB BSON types.

        Args:
            field: Field instance to map

        Returns:
            MongoDB type name

        Examples:
            >>> mapper = MongoDBTypeMapper()
            >>> field = StringField()
            >>> mapper.get_field_type(field)
            'string'
        """
        field_type = field.__class__.__name__.lower().replace("field", "")
        return get_field_type(field_type, "mongodb")

    def get_field_options(self, field: BaseField[Any]) -> dict[str, Any]:
        """Get MongoDB field options.

        Handles MongoDB-specific field options including:
        - Index creation
        - Unique constraints
        - Sparse indexes
        - Text indexes for string fields

        Args:
            field: Field instance to map

        Returns:
            Dictionary of MongoDB field options

        Examples:
            >>> mapper = MongoDBTypeMapper()
            >>> field = StringField(index=True, text_index=True)
            >>> mapper.get_field_options(field)
            {'index': True, 'sparse': True, 'text': True}
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
    """PostgreSQL type mapper implementation.

    This mapper handles PostgreSQL-specific type mapping and options:
    - SQL type mapping
    - VARCHAR length
    - DECIMAL precision/scale
    - Index options including GIN for JSON
    - Unique and NOT NULL constraints

    Examples:
        >>> mapper = PostgresTypeMapper()
        >>> field = StringField(max_length=100)
        >>> field_type = mapper.get_field_type(field)  # Returns "VARCHAR(100)"
        >>> field_opts = mapper.get_field_options(field)  # Returns {"nullable": True, ...}
    """

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get PostgreSQL field type.

        Maps Python field types to PostgreSQL SQL types, handling special cases:
        - VARCHAR with length
        - DECIMAL with precision/scale

        Args:
            field: Field instance to map

        Returns:
            PostgreSQL type name

        Examples:
            >>> mapper = PostgresTypeMapper()
            >>> field = StringField(max_length=50)
            >>> mapper.get_field_type(field)
            'VARCHAR(50)'
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

    def get_field_options(self, field: BaseField[Any]) -> dict[str, Any]:
        """Get PostgreSQL field options.

        Handles PostgreSQL-specific field options including:
        - Index creation (including GIN for JSON)
        - Unique constraints
        - NOT NULL constraints

        Args:
            field: Field instance to map

        Returns:
            Dictionary of PostgreSQL field options

        Examples:
            >>> mapper = PostgresTypeMapper()
            >>> field = StringField(index=True, required=True)
            >>> mapper.get_field_options(field)
            {'index': True, 'nullable': False}
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
    """MySQL type mapper implementation.

    This mapper handles MySQL-specific type mapping and options:
    - SQL type mapping
    - VARCHAR length
    - DECIMAL precision/scale
    - Character sets and collations
    - Index options
    - Unique and NOT NULL constraints

    Examples:
        >>> mapper = MySQLTypeMapper()
        >>> field = StringField(max_length=100)
        >>> field_type = mapper.get_field_type(field)  # Returns "VARCHAR(100)"
        >>> field_opts = mapper.get_field_options(field)  # Returns {"charset": "utf8mb4", ...}
    """

    def get_field_type(self, field: BaseField[Any]) -> str:
        """Get MySQL field type.

        Maps Python field types to MySQL SQL types, handling special cases:
        - VARCHAR with length
        - DECIMAL with precision/scale

        Args:
            field: Field instance to map

        Returns:
            MySQL type name

        Examples:
            >>> mapper = MySQLTypeMapper()
            >>> field = StringField(max_length=50)
            >>> mapper.get_field_type(field)
            'VARCHAR(50)'
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

    def get_field_options(self, field: BaseField[Any]) -> dict[str, Any]:
        """Get MySQL field options.

        Handles MySQL-specific field options including:
        - Index creation
        - Unique constraints
        - NOT NULL constraints
        - Character sets and collations for string fields

        Args:
            field: Field instance to map

        Returns:
            Dictionary of MySQL field options

        Examples:
            >>> mapper = MySQLTypeMapper()
            >>> field = StringField(index=True, required=True)
            >>> mapper.get_field_options(field)
            {'index': True, 'nullable': False, 'charset': 'utf8mb4', ...}
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

    Factory function to create the appropriate mapper instance
    for the specified database backend.

    Args:
        backend: Database backend name ("mongodb", "postgres", "mysql")

    Returns:
        Database type mapper instance

    Raises:
        ValueError: If backend not supported

    Examples:
        >>> mapper = get_mapper("mongodb")
        >>> isinstance(mapper, MongoDBTypeMapper)
        True

        >>> mapper = get_mapper("postgres")
        >>> isinstance(mapper, PostgresTypeMapper)
        True

        >>> mapper = get_mapper("invalid")
        Traceback (most recent call last):
            ...
        ValueError: Unsupported database backend: invalid
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
