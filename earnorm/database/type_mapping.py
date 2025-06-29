"""Database type mapping constants and rules.

This module provides type mapping constants and rules for different database backends.
It is used by both field implementations and database mappers.

The module defines mappings between Python types and database types for:
- MongoDB
- PostgreSQL
- MySQL

It also provides default field options for each backend.

Examples:
    >>> from earnorm.database.type_mapping import get_field_type, get_field_options

    >>> # Get MongoDB type for string field
    >>> mongo_type = get_field_type("string", "mongodb")
    >>> print(mongo_type)  # "string"

    >>> # Get PostgreSQL type for list field
    >>> pg_type = get_field_type("list", "postgres")
    >>> print(pg_type)  # "JSONB"

    >>> # Get default MySQL field options
    >>> mysql_opts = get_field_options("mysql")
    >>> print(mysql_opts)  # {"index": False, "unique": False, ...}
"""

from typing import Any

# MongoDB type mapping
MONGODB_TYPE_MAPPING = {
    "list": "array",
    "set": "array",
    "tuple": "array",
    "dict": "object",
    "embedded": "object",
    "json": "object",
    "string": "string",
    "integer": "int",
    "float": "double",
    "decimal": "double",
    "boolean": "bool",
    "datetime": "date",
    "date": "date",
    "time": "string",
    "enum": "string",
    "file": "string",
    "objectid": "objectId",
    "uuid": "string",
}

# PostgreSQL type mapping
POSTGRES_TYPE_MAPPING = {
    "list": "JSONB",
    "set": "JSONB",
    "tuple": "JSONB",
    "dict": "JSONB",
    "embedded": "JSONB",
    "json": "JSONB",
    "string": "TEXT",  # Will be overridden with VARCHAR if max_length specified
    "integer": "INTEGER",
    "float": "DOUBLE PRECISION",
    "decimal": "DECIMAL",  # Will be formatted with precision/scale
    "boolean": "BOOLEAN",
    "datetime": "TIMESTAMP WITH TIME ZONE",
    "date": "DATE",
    "time": "TIME",
    "enum": "VARCHAR(255)",
    "file": "VARCHAR(255)",
    "objectid": "VARCHAR(24)",
    "uuid": "UUID",
}

# MySQL type mapping
MYSQL_TYPE_MAPPING = {
    "list": "JSON",
    "set": "JSON",
    "tuple": "JSON",
    "dict": "JSON",
    "embedded": "JSON",
    "json": "JSON",
    "string": "TEXT",  # Will be overridden with VARCHAR if max_length specified
    "integer": "INTEGER",
    "float": "DOUBLE",
    "decimal": "DECIMAL",  # Will be formatted with precision/scale
    "boolean": "BOOLEAN",
    "datetime": "DATETIME",
    "date": "DATE",
    "time": "TIME",
    "enum": "VARCHAR(255)",
    "file": "VARCHAR(255)",
    "objectid": "CHAR(24)",
    "uuid": "CHAR(36)",
}

# Default field options by backend
DEFAULT_FIELD_OPTIONS = {
    "mongodb": {
        "index": False,
        "unique": False,
        "sparse": True,
    },
    "postgres": {
        "index": False,
        "unique": False,
        "nullable": True,
    },
    "mysql": {
        "index": False,
        "unique": False,
        "nullable": True,
        "charset": "utf8mb4",
        "collate": "utf8mb4_unicode_ci",
    },
}


def get_field_type(field_type: str, backend: str) -> str:
    """Get database field type for backend.

    This function maps Python field types to their corresponding database types
    based on the specified backend.

    Args:
        field_type: Field type name (e.g. "string", "integer", "list")
        backend: Database backend name ("mongodb", "postgres", "mysql")

    Returns:
        Database type name for the specified backend

    Examples:
        >>> get_field_type("string", "mongodb")
        'string'
        >>> get_field_type("list", "postgres")
        'JSONB'
        >>> get_field_type("integer", "mysql")
        'INTEGER'
    """
    mapping = {
        "mongodb": MONGODB_TYPE_MAPPING,
        "postgres": POSTGRES_TYPE_MAPPING,
        "mysql": MYSQL_TYPE_MAPPING,
    }
    return mapping[backend][field_type]


def get_field_options(backend: str) -> dict[str, Any]:
    """Get default field options for backend.

    This function returns the default field options for the specified database backend.
    These options include settings like:
    - Index flags
    - Unique constraints
    - Nullability
    - Character sets (MySQL)

    Args:
        backend: Database backend name ("mongodb", "postgres", "mysql")

    Returns:
        Dictionary of default field options for the specified backend

    Examples:
        >>> get_field_options("mongodb")
        {'index': False, 'unique': False, 'sparse': True}
        >>> get_field_options("postgres")
        {'index': False, 'unique': False, 'nullable': True}
        >>> get_field_options("mysql")
        {'index': False, 'unique': False, 'nullable': True, 'charset': 'utf8mb4', 'collate': 'utf8mb4_unicode_ci'}
    """
    return DEFAULT_FIELD_OPTIONS[backend].copy()
