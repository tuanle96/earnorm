# API System

## Overview
The API System provides a comprehensive set of decorators and utilities for managing method behaviors, environment handling, and transaction management.

## Components

### 1. Method Decorators
```python
class api:
    @staticmethod
    def model(method):
        """Decorate methods that operate on model level"""
        method._api = 'model'
        return method
        
    @staticmethod
    def multi(method):
        """Decorate methods that operate on recordsets"""
        method._api = 'multi'
        return method
        
    @staticmethod
    def one(method):
        """Decorate methods that operate on single records"""
        method._api = 'one'
        return method
```

### 2. Environment Manager
```python
class Environment:
    def __init__(self, cr, uid, context):
        self.cr = cr          # Database cursor
        self.uid = uid        # User ID
        self.context = context  # Context dictionary
        self.registry = Registry(cr.dbname)
        self.cache = Cache()
```

### 3. Transaction Manager
```python
class Transaction:
    def __init__(self, connection):
        self.connection = connection
        self.closed = False
        self.cursors = set()
        self.environments = set()
```

## Features

### 1. Method Decorators
- Model level operations
- Multi-record operations
- Single record operations
- Computed fields
- Constraints

### 2. Environment Management
- Context handling
- User tracking
- Registry access
- Cache management

### 3. Transaction Control
- Savepoints
- Rollbacks
- Commits
- Cursor management

## Implementation Details

### 1. Method Decorators Implementation
```python
def _api_wrapper(method, api_type):
    """Wrap method with API type checking"""
    def wrapper(self, *args, **kwargs):
        # Check API type
        if api_type == 'one' and len(self) != 1:
            raise ValueError("Expected singleton")
        # Execute method
        return method(self, *args, **kwargs)
    return wrapper

def model(method):
    """Model method decorator"""
    wrapper = _api_wrapper(method, 'model')
    wrapper._api = 'model'
    return wrapper
```

### 2. Environment Management
```python
def manage_env():
    """Environment context manager"""
    try:
        yield env
    finally:
        # Clear caches
        env.cache.invalidate()
        # Clear environments
        env.clear()
```

### 3. Transaction Management
```python
def manage_transaction():
    """Transaction context manager"""
    try:
        yield
        env.cr.commit()
    except Exception:
        env.cr.rollback()
        raise
    finally:
        env.cr.close()
```

## Usage Examples

### 1. Method Decorators
```python
class Partner(models.Model):
    _name = 'res.partner'
    
    @api.model
    def create_partner(self, vals):
        """Create new partner (model method)"""
        return self.create(vals)
    
    @api.multi
    def write_partners(self, vals):
        """Update partners (multi-record method)"""
        return self.write(vals)
    
    @api.one
    def compute_name(self):
        """Compute name (single-record method)"""
        self.display_name = self.name
```

### 2. Environment Usage
```python
# Create new environment
env = Environment(cr, uid, context)

# Access models
partners = env['res.partner']

# Change context
with env.manage():
    env.context = dict(env.context, lang='en_US')
    partner.name = partner.with_context().name_get()[0][1]
```

### 3. Transaction Management
```python
# Transaction with automatic commit/rollback
with env.manage_transaction():
    partner = env['res.partner'].create({
        'name': 'Test Partner'
    })
    
# Manual transaction management
try:
    with env.cr.savepoint():
        partner.write({'name': 'New Name'})
except Exception:
    env.cr.rollback()
    raise
else:
    env.cr.commit()
```

## Best Practices

1. **Method Decorators**
- Use appropriate decorator
- Document method behavior
- Handle exceptions
- Follow API conventions

2. **Environment Management**
- Use context managers
- Clear cache when needed
- Handle user access
- Manage transactions

3. **Transaction Control**
- Use savepoints
- Handle rollbacks
- Commit explicitly
- Clean up resources

## Common Issues & Solutions

1. **Decorator Issues**
```python
# Handle singleton check
@api.one
def check_singleton(self):
    try:
        self.ensure_one()
        return self.do_something()
    except ValueError:
        return self.mapped(lambda r: r.do_something())
```

2. **Environment Issues**
```python
# Handle context changes
def with_company(self, company_id):
    return self.with_context(
        company_id=company_id,
        force_company=company_id
    )
```

3. **Transaction Issues**
```python
# Handle nested transactions
@api.model
def complex_operation(self):
    savepoint = self.env.cr.savepoint()
    try:
        # Do something
        savepoint.release()
    except Exception:
        savepoint.rollback()
        raise
``` 