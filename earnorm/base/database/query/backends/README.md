# Query Backends

This directory contains database-specific implementations of the query system.

## Overview

The backends module provides concrete implementations for different database systems:

1. MongoDB Backend
   - Query translation
   - BSON conversion
   - Aggregation pipeline
   - Index management
   - Change streams

## Directory Structure

```
backends/
├── __init__.py         # Package exports
├── mongo/             # MongoDB implementation
│   ├── __init__.py    # MongoDB exports
│   ├── query.py      # Query implementation
│   ├── builder.py    # Query builder
│   ├── converter.py  # Type converter
│   └── operations/   # Operation implementations
│       ├── aggregate.py
│       ├── join.py
│       └── window.py
└── README.md         # This file
```

## MongoDB Backend

The MongoDB backend (`mongo/`) provides:

### Query Implementation (`query.py`)
```python
from earnorm.base.database.query.backends.mongo import MongoQuery

# Create query
query = MongoQuery(User)

# Add filters
query.filter(age__gt=18)

# Execute
results = await query.execute()
```

### Query Builder (`builder.py`)
```python
from earnorm.base.database.query.backends.mongo import MongoQueryBuilder

# Build query
builder = MongoQueryBuilder()
pipeline = builder.match(
    {"age": {"$gt": 18}}
).sort(
    {"created_at": -1}
).limit(10).build()
```

### Type Converter (`converter.py`)
```python
from earnorm.base.database.query.backends.mongo import MongoConverter

# Convert domain expression
converter = MongoConverter()
mongo_filter = converter.convert(domain.to_list())
```

### Operations

1. Aggregate Operations (`operations/aggregate.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoAggregate

# Create aggregate
agg = MongoAggregate(Order)
stats = await agg.group_by(
    "status"
).count("total").execute()
```

2. Join Operations (`operations/join.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoJoin

# Create join
join = MongoJoin(User)
results = await join.join(
    Post,
    on={"_id": "user_id"}
).execute()
```

3. Window Operations (`operations/window.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoWindow

# Create window
window = MongoWindow(Employee)
results = await window.over(
    partition_by=["department"]
).row_number("rank").execute()
```

## Features

1. Query Building
- Native query support
- Pipeline optimization
- Type conversion
- Result mapping

2. Operation Support
- Aggregation pipeline
- $lookup for joins
- Window functions
- Change streams

3. Type Safety
- BSON conversion
- ObjectId handling
- Date/time types
- Decimal support

## Implementation Guide

To add support for a new database:

1. Create Package Structure
```
backends/
└── new_db/
    ├── __init__.py
    ├── query.py
    ├── builder.py
    ├── converter.py
    └── operations/
        ├── aggregate.py
        ├── join.py
        └── window.py
```

2. Implement Query Builder
```python
from earnorm.base.database.query import QueryProtocol

class NewDBQuery(QueryProtocol[ModelT]):
    async def execute(self) -> List[ModelT]:
        # Convert query to native format
        native_query = self.to_native()
        # Execute query
        results = await self.connection.execute(native_query)
        # Map results to models
        return self.map_results(results)
```

3. Add Type Converter
```python
class NewDBConverter:
    def convert_value(self, value: Any, field_type: str) -> Any:
        # Convert Python type to database type
        pass
        
    def convert_back(self, value: Any, field_type: str) -> Any:
        # Convert database type to Python type
        pass
```

## Best Practices

1. Query Building
- Use parameterized queries
- Implement query optimization
- Handle complex joins
- Support all operations

2. Type Conversion
- Handle all data types
- Validate conversions
- Preserve precision
- Handle nulls

3. Error Handling
- Use custom exceptions
- Provide error context
- Log failures
- Handle edge cases

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
