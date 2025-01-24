# Registry và Environment trong Odoo

## 1. Registry System

### 1.1 Tổng quan
Registry là một singleton object quản lý toàn bộ models trong Odoo. Nó đóng vai trò như một container cho:
- Model definitions
- Database connections
- Caches
- Other global resources

### 1.2 Registry Implementation

```python
class Registry(Mapping):
    """ Model registry for a particular database.
    
    - Quản lý model definitions
    - Quản lý database connections
    - Quản lý caches
    """
    
    def __new__(cls, db_name):
        """Singleton pattern implementation"""
        if db_name in cls.registries:
            return cls.registries[db_name]
        return super().__new__(cls)
        
    def __init__(self, db_name):
        self.models = {}  # model_name -> model_class
        self.cache = {}   # cache storage
        self._init = False
        self._lock = threading.RLock()
        self.db_name = db_name
        
    def setup_models(self, cr, partial=None):
        """Setup all models for this registry"""
        # Create model instances
        for model_name, model_class in self.models.items():
            model_class._build_model(self, cr)
            
        # Setup model inheritance
        for model in self.models.values():
            model._setup_inheritance(cr)
            
        # Initialize constraints
        for model in self.models.values():
            model._setup_constraints(cr)
```

### 1.3 Model Registration Process

```python
class MetaModel(type):
    """Metaclass for Odoo Models"""
    
    def __new__(meta, name, bases, attrs):
        """Register model in registry"""
        # Create new model class
        cls = super().__new__(meta, name, bases, attrs)
        
        # Skip registration for abstract models
        if attrs.get('_register', True):
            # Add model to registry
            registry = Registry(threading.current_thread().dbname)
            registry.models[cls._name] = cls
            
        return cls
```

## 2. Environment

### 2.1 Tổng quan
Environment là một execution context cho models, chứa:
- Database cursor
- Current user ID
- Current user context
- Model registry
- Cache

### 2.2 Environment Implementation

```python
class Environment(Mapping):
    """An environment wraps data for ORM records:
    - cr: database cursor
    - uid: current user id
    - context: current context dict
    - registry: registry for the database
    - cache: cache instance
    """
    
    def __init__(self, cr, uid, context):
        self.cr = cr          # database cursor
        self.uid = uid        # current user id
        self.context = context  # current context
        self.registry = Registry(cr.dbname)
        self.cache = Cache()
        
    def __getitem__(self, model_name):
        """Get model instance from registry"""
        return self.registry[model_name].with_env(self)
        
    def __call__(self, cr=None, user=None, context=None):
        """Create new environment with different cr/user/context"""
        cr = cr or self.cr
        uid = uid or self.uid
        context = context or self.context
        return Environment(cr, uid, context)
```

### 2.3 Environment Management

```python
class EnvironmentMixin:
    """Mixin to add environment support to models"""
    
    @property
    def env(self):
        """Get current environment"""
        return self._env
        
    def with_env(self, env):
        """Create new recordset with different environment"""
        # Create new instance with new environment
        return self.browse(self.ids).sudo(env.uid)
        
    def sudo(self, user=SUPERUSER_ID):
        """Create new recordset with different user"""
        return self.with_env(self.env(user=user))
        
    def with_context(self, **overrides):
        """Create new recordset with updated context"""
        context = dict(self.env.context, **overrides)
        return self.with_env(self.env(context=context))
```

## 3. Interaction Flow

### 3.1 Model Access Flow

```python
# 1. Get registry for database
registry = Registry(db_name)

# 2. Create environment
env = Environment(cr, uid, context)

# 3. Access model through environment
model = env['model.name']

# 4. Use model methods
records = model.search([...])
```

### 3.2 Transaction Management

```python
class Environment:
    def manage(self):
        """Context manager for environment"""
        return EnvironmentManager(self)
        
class EnvironmentManager:
    def __init__(self, env):
        self.env = env
        
    def __enter__(self):
        # Push environment to environment stack
        self.old = set_local_environment(self.env)
        return self.env
        
    def __exit__(self, exc_type, exc_value, traceback):
        # Restore previous environment
        set_local_environment(self.old)
        
        if exc_type is None:
            # Commit transaction if no exception
            self.env.cr.commit()
        else:
            # Rollback on exception
            self.env.cr.rollback()
```

## 4. Cache Management

### 4.1 Cache Structure

```python
class Cache:
    """Model cache implementation"""
    
    def __init__(self):
        self._data = {}  # {model: {field: {record_id: value}}}
        
    def get(self, model, field, ids):
        """Get cached values"""
        return {
            record_id: self._data[model][field][record_id]
            for record_id in ids
            if record_id in self._data.get(model, {}).get(field, {})
        }
        
    def set(self, model, field, items):
        """Set cached values"""
        self._data.setdefault(model, {}).setdefault(field, {}).update(items)
        
    def invalidate(self, spec=None):
        """Invalidate cache entries"""
        if spec is None:
            self._data.clear()
        else:
            for model, fields in spec.items():
                for field in fields:
                    self._data.get(model, {}).pop(field, None)
```

## 5. Best Practices

### 5.1 Registry Usage
1. Sử dụng singleton pattern để tránh duplicate registries
2. Implement thread safety cho registry access
3. Cache model metadata để tối ưu performance

### 5.2 Environment Usage
1. Sử dụng context manager cho transaction management
2. Tránh giữ references tới environments cũ
3. Clear caches khi cần thiết

### 5.3 Cache Usage
1. Implement cache invalidation strategy
2. Monitor cache size và memory usage
3. Use prefetching để optimize cache hits

## 6. Common Issues & Solutions

### 6.1 Performance Issues
1. **Registry loading slow**
   - Cache model metadata
   - Lazy load không cần thiết components
   
2. **Cache memory usage high**
   - Implement cache size limits
   - Regular cache cleanup
   - Monitor memory usage

### 6.2 Concurrency Issues
1. **Registry access conflicts**
   - Implement proper locking
   - Use thread-local storage
   
2. **Transaction conflicts**
   - Implement retry mechanism
   - Use proper isolation levels
``` 