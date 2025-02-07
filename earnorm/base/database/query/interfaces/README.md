# Query Interfaces

This directory contains the interface definitions for EarnORM's query system.

## Overview

The interfaces module provides:

1. Query Protocols
2. Operation Protocols
3. Domain Expressions
4. Field References

### Query Protocol

The query protocol defines the interface for query builders:

```python
from earnorm.base.database.query.interfaces import QueryProtocol
from earnorm.types import DatabaseModel

class CustomQuery(QueryProtocol[ModelT]):
    async def execute(self) -> List[ModelT]:
        """Execute query and return results."""
        pass
        
    def filter(self, **conditions) -> Self:
        """Add filter conditions."""
        pass
        
    def select(self, *fields: str) -> Self:
        """Select fields to return."""
        pass
```

### Operation Protocols

The operation protocols define interfaces for different operation types:

```python
from earnorm.base.database.query.interfaces.operations import (
    AggregateProtocol,
    JoinProtocol,
    WindowProtocol
)

class CustomAggregate(AggregateProtocol[ModelT]):
    def group_by(self, *fields: str) -> Self:
        """Group results by fields."""
        pass
        
    def having(self, **conditions) -> Self:
        """Add having conditions."""
        pass

class CustomJoin(JoinProtocol[ModelT, JoinT]):
    def on(self, *conditions) -> Self:
        """Add join conditions."""
        pass
        
    def select(self, *fields: str) -> Self:
        """Select fields to return."""
        pass

class CustomWindow(WindowProtocol[ModelT]):
    def over(self, partition_by: List[str]) -> Self:
        """Set window specification."""
        pass
        
    def frame(self, type: str, start: int, end: int) -> Self:
        """Set frame specification."""
        pass
```

### Domain Expressions

The domain expressions provide a type-safe way to build query conditions:

```python
from earnorm.base.database.query.interfaces.domain import (
    DomainBuilder,
    DomainExpression
)

# Build domain expression
domain = DomainBuilder().field(
    "age"
).greater_than(
    18
).and_().field(
    "status"
).equals(
    "active"
).build()

# Use in query
results = await query.filter(domain).all()
```

### Field References

The field references provide a type-safe way to reference model fields:

```python
from earnorm.base.database.query.interfaces.field import Field

class User(DatabaseModel):
    name = Field[str]()
    age = Field[int]()
    
# Use in query
results = await query.filter(
    User.age > 18,
    User.name.startswith("J")
).all()
```

## Directory Structure

```
interfaces/
├── __init__.py         # Package exports
├── domain.py          # Domain expression interfaces
├── field.py          # Field reference interfaces
├── query.py         # Query builder interfaces
└── operations/      # Operation interfaces
    ├── __init__.py  # Operation exports
    ├── base.py     # Base operation interface
    ├── aggregate.py # Aggregate interface
    ├── join.py    # Join interface
    └── window.py  # Window interface
```

## Features

1. Query Interfaces
- Type safety
- Method chaining
- Result validation
- Custom operations

2. Operation Interfaces
- Operation composition
- Result processing
- Pipeline building
- Error handling

3. Domain Expressions
- Type-safe conditions
- Complex expressions
- Custom operators
- Validation

4. Field References
- Type-safe fields
- Field operations
- Custom field types
- Validation

## Implementation Guide

To implement a new interface:

1. Define Protocol
```python
from typing import Protocol, TypeVar

ModelT = TypeVar("ModelT", bound=DatabaseModel)

class CustomProtocol(Protocol[ModelT]):
    def custom_method(self) -> None:
        """Custom method documentation."""
        pass
```

2. Add Type Hints
```python
from typing import List, Optional

class CustomProtocol(Protocol[ModelT]):
    def get_items(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelT]:
        """Get items with optional filters."""
        pass
```

3. Add Documentation
```python
class CustomProtocol(Protocol[ModelT]):
    """Custom protocol documentation.
    
    This protocol defines:
    - Method requirements
    - Type constraints
    - Usage examples
    """
    pass
```

## Best Practices

1. Protocol Design
- Keep interfaces focused
- Use type variables
- Document requirements
- Add examples

2. Type Safety
- Use generics
- Add constraints
- Validate types
- Handle errors

3. Documentation
- Add docstrings
- Include examples
- List requirements
- Note limitations

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
