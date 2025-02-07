# Operation Interfaces

This directory contains the interface definitions for query operations.

## Overview

The operations module defines protocols for:

1. Base Operations
2. Aggregate Operations
3. Join Operations
4. Window Operations

## Directory Structure

```
operations/
├── __init__.py      # Package exports
├── base.py         # Base operation protocol
├── aggregate.py    # Aggregate operation protocol
├── join.py        # Join operation protocol
└── window.py      # Window operation protocol
```

## Protocols

### Base Operation Protocol (`base.py`)

The base protocol for all operations:

```python
from earnorm.base.database.query.interfaces.operations import OperationProtocol
from earnorm.types import DatabaseModel

class CustomOperation(OperationProtocol[ModelT]):
    async def execute(self) -> List[ModelT]:
        """Execute operation."""
        pass
        
    def add_processor(self, processor: Callable[[Any], Any]) -> Self:
        """Add result processor."""
        pass
        
    def validate(self) -> None:
        """Validate operation configuration."""
        pass
```

### Aggregate Operation Protocol (`aggregate.py`)

Protocol for aggregate operations:

```python
from earnorm.base.database.query.interfaces.operations import AggregateProtocol

class CustomAggregate(AggregateProtocol[ModelT]):
    def group_by(self, *fields: str) -> Self:
        """Group results by fields."""
        pass
        
    def count(self, field: str = "*", alias: str = None) -> Self:
        """Count records."""
        pass
        
    def sum(self, field: str, alias: str = None) -> Self:
        """Sum field values."""
        pass
        
    def avg(self, field: str, alias: str = None) -> Self:
        """Average field values."""
        pass
        
    def having(self, **conditions) -> Self:
        """Add having conditions."""
        pass
```

### Join Operation Protocol (`join.py`)

Protocol for join operations:

```python
from earnorm.base.database.query.interfaces.operations import JoinProtocol

class CustomJoin(JoinProtocol[ModelT, JoinT]):
    def join(
        self,
        model: Type[JoinT],
        on: Dict[str, str] = None,
        join_type: str = "inner"
    ) -> Self:
        """Add join."""
        pass
        
    def on(self, *conditions) -> Self:
        """Add join conditions."""
        pass
        
    def select(self, *fields: str) -> Self:
        """Select fields to return."""
        pass
```

### Window Operation Protocol (`window.py`)

Protocol for window operations:

```python
from earnorm.base.database.query.interfaces.operations import WindowProtocol

class CustomWindow(WindowProtocol[ModelT]):
    def over(
        self,
        partition_by: List[str] = None,
        order_by: List[str] = None
    ) -> Self:
        """Set window specification."""
        pass
        
    def frame(
        self,
        frame_type: str,
        start: int,
        end: int
    ) -> Self:
        """Set frame specification."""
        pass
        
    def row_number(self, alias: str = "row_number") -> Self:
        """Add ROW_NUMBER function."""
        pass
```

## Features

1. Base Protocol
- Operation execution
- Result processing
- Configuration validation
- Error handling

2. Aggregate Protocol
- Group by operations
- Aggregation functions
- Having clauses
- Custom aggregations

3. Join Protocol
- Multiple join types
- Join conditions
- Field selection
- Cross-database joins

4. Window Protocol
- Window functions
- Frame specifications
- Partitioning
- Custom functions

## Implementation Guide

To implement a new operation:

1. Create Protocol
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
