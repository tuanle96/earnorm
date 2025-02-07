# EarnORM Database Module

This module provides database type mapping and field mapping functionality for EarnORM.

## Overview

The database module consists of two main components:

1. Type Mapping System
2. Database Type Mappers

### Type Mapping System

The type mapping system provides mapping between Python types and database types for different database backends:

- MongoDB
- PostgreSQL
- MySQL

Example:
```python
from earnorm.database.type_mapping import get_field_type

# Get MongoDB type for a string field
mongo_type = get_field_type("string", "mongodb")  # Returns "string"

# Get PostgreSQL type for a list field
pg_type = get_field_type("list", "postgres")  # Returns "JSONB"
```

### Database Type Mappers

The mapper system provides concrete implementations for mapping field types and options to specific database backends:

```python
from earnorm.database.mappers import get_mapper

# Get MongoDB mapper
mongo_mapper = get_mapper("mongodb")

# Get field type and options
field_type = mongo_mapper.get_field_type(string_field)
field_opts = mongo_mapper.get_field_options(string_field)
```

## Features

- Comprehensive type mapping for common Python types
- Support for field options and constraints
- Extensible architecture for new database backends
- Type safety with mypy support
- Custom field type support

## Type Mappings

### MongoDB
| Python Type | MongoDB Type |
|------------|--------------|
| string     | string       |
| integer    | int          |
| float      | double       |
| list       | array        |
| dict       | object       |
| datetime   | date         |

### PostgreSQL
| Python Type | PostgreSQL Type |
|------------|----------------|
| string     | TEXT/VARCHAR   |
| integer    | INTEGER        |
| float      | DOUBLE PRECISION|
| list       | JSONB          |
| dict       | JSONB          |
| datetime   | TIMESTAMP      |

### MySQL
| Python Type | MySQL Type    |
|------------|---------------|
| string     | TEXT/VARCHAR  |
| integer    | INTEGER       |
| float      | DOUBLE        |
| list       | JSON          |
| dict       | JSON          |
| datetime   | DATETIME      |

## Field Options

Each database backend supports different field options:

### MongoDB
- index: Create index
- unique: Unique constraint
- sparse: Sparse index
- text: Text index (string fields)

### PostgreSQL
- index: Create index
- unique: Unique constraint
- nullable: NULL constraint
- using: Index type (GIN for JSON)

### MySQL
- index: Create index
- unique: Unique constraint
- nullable: NULL constraint
- charset: Character set
- collate: Collation

## Usage Examples

### Basic Type Mapping
```python
from earnorm.database.type_mapping import get_field_type

# Get database type
mongo_type = get_field_type("string", "mongodb")
pg_type = get_field_type("list", "postgres")
mysql_type = get_field_type("integer", "mysql")
```

### Using Mappers
```python
from earnorm.database.mappers import get_mapper
from earnorm.fields import StringField

# Create field
name_field = StringField(max_length=100, index=True)

# Get mapper
pg_mapper = get_mapper("postgres")

# Get field type and options
field_type = pg_mapper.get_field_type(name_field)  # VARCHAR(100)
field_opts = pg_mapper.get_field_options(name_field)  # {"index": True, ...}
```

### Custom Field Support
```python
from earnorm.fields import BaseField
from earnorm.database.mappers import DatabaseTypeMapper

class CustomMapper(DatabaseTypeMapper):
    def get_field_type(self, field: BaseField) -> str:
        # Custom type mapping logic
        return "CUSTOM_TYPE"

    def get_field_options(self, field: BaseField) -> dict:
        # Custom options logic
        return {"custom_option": True}
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
