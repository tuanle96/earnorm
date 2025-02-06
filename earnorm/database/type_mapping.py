"""Database type mapping constants and rules.

This module provides type mapping constants and rules for different database backends.
It is used by both field implementations and database mappers.
"""

from typing import Any, Dict

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

    Args:
        field_type: Field type name
        backend: Database backend name

    Returns:
        Database type name
    """
    mapping = {
        "mongodb": MONGODB_TYPE_MAPPING,
        "postgres": POSTGRES_TYPE_MAPPING,
        "mysql": MYSQL_TYPE_MAPPING,
    }
    return mapping[backend][field_type]


def get_field_options(backend: str) -> Dict[str, Any]:
    """Get default field options for backend.

    Args:
        backend: Database backend name

    Returns:
        Default field options
    """
    return DEFAULT_FIELD_OPTIONS[backend].copy()
