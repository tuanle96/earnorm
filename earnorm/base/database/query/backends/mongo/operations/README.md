# MongoDB Operations

This directory contains MongoDB-specific implementations of query operations.

## Overview

The operations module provides:

1. Aggregate Operations
2. Join Operations
3. Window Operations

## Directory Structure

```
operations/
├── __init__.py      # Package exports
├── aggregate.py    # Aggregate operations
├── join.py        # Join operations
└── window.py      # Window operations
```

## Operations

### Aggregate Operations (`aggregate.py`)

MongoDB aggregation pipeline implementation:

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
).avg(
    "amount", "avg_amount"
).having(
    total_orders__gt=10
).execute()

# Time-based aggregation
monthly = await agg.group_by(
    year="$year(created_at)",
    month="$month(created_at)"
).sum(
    "amount", "monthly_total"
).execute()

# Custom pipeline stages
result = await agg.add_stage({
    "$match": {"status": "completed"}
}).add_stage({
    "$group": {
        "_id": "$category",
        "total": {"$sum": "$amount"}
    }
}).execute()
```

### Join Operations (`join.py`)

MongoDB $lookup implementation:

```python
from earnorm.base.database.query.backends.mongo.operations import MongoJoin

# Create join
join = MongoJoin(User)

# Simple join
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).select(
    "name", "posts.title"
).execute()

# Multiple joins
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).join(
    Comment
).on(
    Post.id == Comment.post_id
).select(
    "name",
    "posts.title",
    "comments.content"
).execute()

# Join with conditions
results = await join.join(
    Post
).on(
    User.id == Post.user_id,
    Post.status == "published"
).select(
    "name",
    "posts.title"
).execute()
```

### Window Operations (`window.py`)

MongoDB window functions implementation:

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
    "rank_in_dept"
).execute()

# Running total by department
results = await window.over(
    partition_by=["department"]
).order_by(
    "hire_date"
).sum(
    "salary",
    "running_total"
).execute()

# Moving average
results = await window.over(
    order_by=["hire_date"]
).frame(
    "rows",
    start=-2,
    end=0
).avg(
    "salary",
    "moving_avg"
).execute()
```

## Features

1. Aggregate Operations
- Group by fields
- Aggregation functions
- Having clauses
- Pipeline stages
- Custom aggregations

2. Join Operations
- $lookup stages
- Multiple joins
- Join conditions
- Field selection
- Cross-database joins

3. Window Operations
- Ranking functions
- Frame specifications
- Partitioning
- Custom functions

## Implementation Details

1. Pipeline Building
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
This directory contains MongoDB-specific implementations of query operations.

## Overview

The operations module provides:

1. Aggregate Operations
2. Join Operations
3. Window Operations

## Directory Structure

```
operations/
├── __init__.py      # Package exports
├── aggregate.py    # Aggregate operations
├── join.py        # Join operations
└── window.py      # Window operations
```

## Operations

### Aggregate Operations (`aggregate.py`)

MongoDB aggregation pipeline implementation:

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
).avg(
    "amount", "avg_amount"
).having(
    total_orders__gt=10
).execute()

# Time-based aggregation
monthly = await agg.group_by(
    year="$year(created_at)",
    month="$month(created_at)"
).sum(
    "amount", "monthly_total"
).execute()

# Custom pipeline stages
result = await agg.add_stage({
    "$match": {"status": "completed"}
}).add_stage({
    "$group": {
        "_id": "$category",
        "total": {"$sum": "$amount"}
    }
}).execute()
```

### Join Operations (`join.py`)

MongoDB $lookup implementation:

```python
from earnorm.base.database.query.backends.mongo.operations import MongoJoin

# Create join
join = MongoJoin(User)

# Simple join
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).select(
    "name", "posts.title"
).execute()

# Multiple joins
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).join(
    Comment
).on(
    Post.id == Comment.post_id
).select(
    "name",
    "posts.title",
    "comments.content"
).execute()

# Join with conditions
results = await join.join(
    Post
).on(
    User.id == Post.user_id,
    Post.status == "published"
).select(
    "name",
    "posts.title"
).execute()
```

### Window Operations (`window.py`)

MongoDB window functions implementation:

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
    "rank_in_dept"
).execute()

# Running total by department
results = await window.over(
    partition_by=["department"]
).order_by(
    "hire_date"
).sum(
    "salary",
    "running_total"
).execute()

# Moving average
results = await window.over(
    order_by=["hire_date"]
).frame(
    "rows",
    start=-2,
    end=0
).avg(
    "salary",
    "moving_avg"
).execute()
```

## Features

1. Aggregate Operations
- Group by fields
- Aggregation functions
- Having clauses
- Pipeline stages
- Custom aggregations

2. Join Operations
- $lookup stages
- Multiple joins
- Join conditions
- Field selection
- Cross-database joins

3. Window Operations
- Ranking functions
- Frame specifications
- Partitioning
- Custom functions

## Implementation Details

1. Pipeline Building
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

 