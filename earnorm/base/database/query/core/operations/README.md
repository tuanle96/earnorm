# Query Operations

This directory contains the core operation implementations for EarnORM's query system.

## Overview

The operations module provides:

1. Base Operation
2. Aggregate Operations
3. Join Operations
4. Window Operations

### Base Operation

The base operation (`base.py`) provides:

```python
from earnorm.base.database.query.core.operations import Operation

# Create operation
op = Operation(User)

# Add result processor
def process_result(result):
    result["full_name"] = f"{result['first_name']} {result['last_name']}"
    return result

op.add_processor(process_result)

# Execute operation
results = await op.execute()
```

### Aggregate Operations

The aggregate operations (`aggregate.py`) support:

```python
from earnorm.base.database.query.core.operations import AggregateOperation

# Create aggregate
agg = AggregateOperation(Order)

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
```

### Join Operations

The join operations (`join.py`) support:

```python
from earnorm.base.database.query.core.operations import JoinOperation

# Create join
join = JoinOperation(User)

# Join with conditions
results = await join.join(
    Post
).on(
    User.id == Post.user_id
).select(
    "name", "posts.title"
).execute()
```

### Window Operations

The window operations (`window.py`) support:

```python
from earnorm.base.database.query.core.operations import WindowOperation

# Create window
window = WindowOperation(Employee)

# Ranking and moving averages
results = await window.over(
    partition_by=["department"],
    order_by=["-salary"]
).frame(
    "rows",
    start=-2,
    end=0
).avg(
    "salary",
    "moving_avg"
).execute()
```

## Directory Structure

```
operations/
├── __init__.py     # Package exports
├── base.py        # Base operation class
├── aggregate.py   # Aggregate operations
├── join.py       # Join operations
└── window.py     # Window operations
```

## Features

1. Base Operation
- Operation chaining
- Result processing
- Pipeline building
- Validation

2. Aggregate Operations
- Group by fields
- Aggregation functions
- Having clauses
- Custom stages

3. Join Operations
- Multiple join types
- Join conditions
- Field selection
- Cross-database joins

4. Window Operations
- Ranking functions
- Frame specifications
- Partitioning
- Custom functions

## Implementation Guide

To implement a new operation:

1. Create Operation Class
```python
from earnorm.base.database.query.core.operations import Operation

class CustomOperation(Operation[ModelT]):
    def __init__(self, model_type: Type[ModelT]) -> None:
        super().__init__(model_type)
        self._custom_options = {}
        
    def custom_method(self, option: str) -> Self:
        self._custom_options[option] = True
        return self
```

2. Add Pipeline Building
```python
def to_pipeline(self) -> List[Dict[str, Any]]:
    pipeline = []
    if self._custom_options:
        pipeline.append({
            "$customStage": self._custom_options
        })
    return pipeline
```

3. Add Validation
```python
def validate(self) -> None:
    if not self._custom_options:
        raise ValueError("No custom options specified")
```

## Best Practices

1. Operation Design
- Keep operations focused
- Use method chaining
- Validate inputs
- Handle errors

2. Pipeline Building
- Optimize stages
- Handle edge cases
- Support all features
- Document limitations

3. Result Processing
- Type safety
- Data validation
- Error handling
- Performance

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
