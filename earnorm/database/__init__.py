"""Database module for EarnORM.

This module provides database type mapping and field mapping functionality.
It includes:

1. Type Mapping System
   - Mapping between Python types and database types
   - Support for MongoDB, PostgreSQL, and MySQL
   - Default field options for each backend

2. Database Type Mappers
   - Abstract mapper interface
   - Concrete implementations for each backend
   - Field type and options mapping
   - Special case handling

Examples:
    >>> from earnorm.database import get_mapper
    >>> from earnorm.fields import StringField

    >>> # Create a field
    >>> name = StringField(max_length=100, index=True)

    >>> # Get mapper for backend
    >>> mapper = get_mapper("postgres")

    >>> # Get field type and options
    >>> field_type = mapper.get_field_type(name)  # Returns "VARCHAR(100)"
    >>> field_opts = mapper.get_field_options(name)  # Returns {"index": True, ...}
"""

from earnorm.database.mappers import (
    DatabaseTypeMapper,
    MongoDBTypeMapper,
    MySQLTypeMapper,
    PostgresTypeMapper,
    get_mapper,
)
from earnorm.database.type_mapping import get_field_options, get_field_type

__all__ = [
    "DatabaseTypeMapper",
    "MongoDBTypeMapper",
    "PostgresTypeMapper",
    "MySQLTypeMapper",
    "get_mapper",
    "get_field_type",
    "get_field_options",
]
