# Transaction System

This directory contains the transaction management system for EarnORM.

## Overview

The transaction system provides ACID-compliant transaction support for database operations. It includes:

1. Transaction Management
2. Savepoint Support
3. Nested Transactions
4. Error Handling

## Directory Structure

```
transaction/
├── base.py          # Base transaction interface
├── backends/        # Backend-specific implementations
└── __init__.py     # Package exports
```

## Usage

### Basic Transactions

```python
# Using context manager
async with adapter.transaction() as txn:
    # Create user
    user = await txn.create(User, {
        "name": "John Doe",
        "email": "john@example.com"
    })
    
    # Create order
    order = await txn.create(Order, {
        "user_id": user.id,
        "amount": 100.00
    })
    
    # Transaction will be committed if no errors occur
    # or rolled back if any error is raised

# Manual transaction management
txn = await adapter.begin_transaction()
try:
    user = await txn.create(User, {...})
    order = await txn.create(Order, {...})
    await txn.commit()
except Exception:
    await txn.rollback()
    raise
```

### Savepoints

```python
async with adapter.transaction() as txn:
    user = await txn.create(User, {...})
    
    # Create savepoint
    await txn.savepoint("after_user")
    
    try:
        order = await txn.create(Order, {...})
    except Exception:
        # Rollback to savepoint
        await txn.rollback_to("after_user")
```

### Nested Transactions

```python
async with adapter.transaction() as txn1:
    user = await txn1.create(User, {...})
    
    async with txn1.nested() as txn2:
        order = await txn2.create(Order, {...})
        # Nested transaction can be committed/rolled back independently
```

## Features

### 1. ACID Properties

- **Atomicity**: All operations succeed or all fail
- **Consistency**: Database remains in valid state
- **Isolation**: Transactions are isolated from each other
- **Durability**: Committed changes are permanent

### 2. Transaction Management

```python
class Transaction:
    async def begin(self):
        """Start transaction"""
        
    async def commit(self):
        """Commit changes"""
        
    async def rollback(self):
        """Rollback changes"""
        
    async def savepoint(self, name: str):
        """Create savepoint"""
        
    async def rollback_to(self, name: str):
        """Rollback to savepoint"""
```

### 3. Error Handling

```python
try:
    async with adapter.transaction() as txn:
        # Operations
except TransactionError as e:
    # Handle transaction-specific errors
except DatabaseError as e:
    # Handle database errors
except Exception as e:
    # Handle other errors
```

## Backend Support

Each database backend must implement:

1. Transaction Support
- Begin/commit/rollback
- Savepoints
- Nested transactions
- Error handling

2. Isolation Levels
- Read uncommitted
- Read committed
- Repeatable read
- Serializable

## Best Practices

### 1. Transaction Scope

- Keep transactions short
- Minimize number of operations
- Avoid external calls
- Handle timeouts

### 2. Error Handling

- Use specific exceptions
- Provide error context
- Log transaction events
- Handle edge cases

### 3. Resource Management

- Close connections properly
- Release locks
- Handle deadlocks
- Monitor performance

### 4. Concurrency

- Use appropriate isolation levels
- Handle concurrent access
- Prevent race conditions
- Implement retry logic

## Implementation Guide

To implement transaction support for a new database backend:

1. Create Transaction Class
```python
from earnorm.base.database.transaction import Transaction

class PostgresTransaction(Transaction):
    async def begin(self):
        await self.connection.execute("BEGIN")
        
    async def commit(self):
        await self.connection.execute("COMMIT")
        
    async def rollback(self):
        await self.connection.execute("ROLLBACK")
```

2. Implement Savepoints
```python
class PostgresTransaction(Transaction):
    async def savepoint(self, name: str):
        await self.connection.execute(f"SAVEPOINT {name}")
        
    async def rollback_to(self, name: str):
        await self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
```

3. Add Error Handling
```python
class PostgresTransaction(Transaction):
    async def begin(self):
        try:
            await self.connection.execute("BEGIN")
        except Exception as e:
            raise TransactionError("Failed to begin transaction") from e
```

## Contributing

To contribute:

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
