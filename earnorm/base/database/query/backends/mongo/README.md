# MongoDB Backend

This directory contains the MongoDB-specific implementation of EarnORM's query system.

## Overview

The MongoDB backend provides:

1. Query Implementation
2. Pipeline Building
3. Type Conversion
4. Operation Support

## Directory Structure

```
mongo/
├── __init__.py         # Package exports
├── query.py           # Query implementation
├── builder.py         # Query builder
├── converter.py       # Type converter
└── operations/        # Operation implementations
    ├── __init__.py    # Operation exports
    ├── aggregate.py  # Aggregate operations
    ├── join.py      # Join operations
    └── window.py    # Window operations
```

## Components

### Query Implementation (`query.py`)

The main query class for MongoDB:

```python
from earnorm.base.database.query.backends.mongo import MongoQuery

# Create query
query = MongoQuery(User)

# Add filters
query.filter(age__gt=18, status="active")

# Add sorting
query.order_by("-created_at", "name")

# Set pagination
query.limit(10).offset(20)

# Execute query
results = await query.execute()
```

### Query Builder (`builder.py`)

Pipeline builder for MongoDB:

```python
from earnorm.base.database.query.backends.mongo import MongoQueryBuilder

# Create builder
builder = MongoQueryBuilder()

# Build pipeline
pipeline = builder.match(
    {"age": {"$gt": 18}}
).sort(
    {"created_at": -1}
).limit(10).build()

# Custom stages
pipeline = builder.add_stage({
    "$match": {"status": "active"}
}).add_stage({
    "$group": {
        "_id": "$category",
        "total": {"$sum": "$amount"}
    }
}).build()
```

### Type Converter (`converter.py`)

Type conversion between Python and MongoDB:

```python
from earnorm.base.database.query.backends.mongo import MongoConverter

# Create converter
converter = MongoConverter()

# Convert domain expression
mongo_filter = converter.convert(domain.to_list())

# Convert field values
object_id = converter.to_object_id("507f1f77bcf86cd799439011")
datetime_val = converter.to_datetime("2024-02-07T12:00:00Z")
decimal_val = converter.to_decimal128("123.45")
```

### Operations

1. Aggregate Operations (`operations/aggregate.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoAggregate

# Create aggregate
agg = MongoAggregate(Order)

# Group by with aggregates
stats = await agg.group_by(
    "status", "category"
).count(
    "total_orders"
).sum(
    "amount", "total_amount"
).execute()
```

2. Join Operations (`operations/join.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoJoin

# Create join
join = MongoJoin(User)

# Join with conditions
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).select(
    "name", "posts.title"
).execute()
```

3. Window Operations (`operations/window.py`)
```python
from earnorm.base.database.query.backends.mongo.operations import MongoWindow

# Create window
window = MongoWindow(Employee)

# Row number by department
results = await window.over(
    partition_by=["department"]
).order_by(
    "-salary"
).row_number(
    "rank"
).execute()
```

## Features

1. Query Building
- Native MongoDB query support
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

## Implementation Details

1. Query Building
- Stage generation
- Pipeline optimization
- Result mapping
- Error handling

2. Type Conversion
- BSON conversion
- ObjectId handling
- Date/time types
- Decimal support

3. Performance
- Index usage
- Memory usage
- Batch processing
- Connection pooling

## Best Practices

1. Query Building
- Use indexes
- Limit results
- Project fields
- Handle large datasets

2. Pipeline Optimization
- Minimize stages
- Use early filtering
- Avoid memory limits
- Monitor performance

3. Error Handling
- Handle timeouts
- Validate inputs
- Log errors
- Provide context

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
