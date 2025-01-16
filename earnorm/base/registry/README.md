# Registry Module

## Overview
The Registry module provides a central system for managing model registration and metadata in EarnORM. It handles model discovery, registration, and database connection management.

## Components

### 1. Model Registry
The core class for managing model registration:

```python
class ModelRegistry:
    """Registry for managing model registration and metadata.
    
    Examples:
        >>> registry = ModelRegistry()
        >>> registry.register(User)
        >>> user_model = registry.get_model("User")
        >>> users = await user_model.search([("active", "=", True)])
    """
    
    def register(self, model_cls: Type[Model]) -> None:
        """Register a model class."""
        self._models[model_cls.__name__] = model_cls
        self._setup_model_metadata(model_cls)
        
    def get_model(self, name: str) -> Type[Model]:
        """Get a registered model by name."""
        if name not in self._models:
            raise ModelNotFoundError(f"Model {name} not found")
        return self._models[name]
```

### 2. Database Registry
Manages database connections and collections:

```python
class DatabaseRegistry:
    """Registry for managing database connections.
    
    Examples:
        >>> db_registry = DatabaseRegistry()
        >>> await db_registry.initialize(
        ...     uri="mongodb://localhost:27017",
        ...     database="earnbase"
        ... )
        >>> collection = await db_registry.get_collection("users")
    """
    
    async def initialize(
        self,
        uri: str,
        database: str,
        **options: Any
    ) -> None:
        """Initialize database connection."""
        self._client = AsyncIOMotorClient(uri, **options)
        self._db = self._client[database]
        
    async def get_collection(
        self,
        name: str
    ) -> AsyncIOMotorCollection:
        """Get a database collection."""
        return self._db[name]
```

### 3. Collection Manager
Handles collection operations and mapping:

```python
class CollectionManager:
    """Manager for collection operations.
    
    Examples:
        >>> manager = CollectionManager(db_registry)
        >>> await manager.ensure_indexes(User)
        >>> await manager.create_collection("users")
    """
    
    async def ensure_indexes(self, model: Type[Model]) -> None:
        """Ensure model indexes exist."""
        collection = await self.get_collection(model)
        for index in model._indexes:
            await collection.create_index(**index)
            
    async def create_collection(
        self,
        name: str,
        **options: Any
    ) -> None:
        """Create a new collection."""
        await self._db.create_collection(name, **options)
```

## Usage Examples

### 1. Basic Registration
```python
# Register models
registry = ModelRegistry()
registry.register(User)
registry.register(Post)

# Get models
user_model = registry.get_model("User")
post_model = registry.get_model("Post")

# Create records
user = await user_model.create({
    "name": "John",
    "email": "john@example.com"
})
```

### 2. Database Setup
```python
# Initialize database
db_registry = DatabaseRegistry()
await db_registry.initialize(
    uri="mongodb://localhost:27017",
    database="earnbase",
    maxPoolSize=100
)

# Setup collections
collection_manager = CollectionManager(db_registry)
await collection_manager.ensure_indexes(User)
await collection_manager.ensure_indexes(Post)
```

### 3. Advanced Usage
```python
# Custom collection naming
class User(Model):
    _collection = "system_users"
    _indexes = [
        {"fields": [("email", 1)], "unique": True},
        {"fields": [("status", 1), ("role", 1)]}
    ]

# Register with custom options
registry.register(User, {
    "collection": "custom_users",
    "indexes": [{"fields": [("username", 1)]}]
})
```

## Best Practices

1. **Model Registration**
- Register models early in application startup
- Use consistent naming conventions
- Validate model definitions
- Handle registration errors

2. **Database Management**
- Use connection pooling
- Configure appropriate timeouts
- Monitor connection health
- Handle reconnection gracefully

3. **Collection Management**
- Plan indexes carefully
- Monitor index usage
- Handle collection migrations
- Backup data regularly

4. **Error Handling**
- Handle registration errors
- Validate model definitions
- Monitor database operations
- Log important events

## Common Issues & Solutions

1. **Model Discovery**
```python
class ModelDiscovery:
    """Automatic model discovery."""
    
    def discover_models(self, package: str) -> List[Type[Model]]:
        """Discover models in package."""
        models = []
        for module in self._scan_modules(package):
            for name, obj in module.__dict__.items():
                if self._is_model_class(obj):
                    models.append(obj)
        return models
```

2. **Connection Management**
```python
class ConnectionManager:
    """Database connection manager."""
    
    async def ensure_connected(self) -> None:
        """Ensure database connection."""
        try:
            await self._client.admin.command("ping")
        except Exception:
            await self._reconnect()
            
    async def _reconnect(self) -> None:
        """Reconnect to database."""
        await self._client.close()
        self._client = AsyncIOMotorClient(self._uri, **self._options)
```

3. **Index Management**
```python
class IndexManager:
    """Manager for index operations."""
    
    async def sync_indexes(
        self,
        model: Type[Model]
    ) -> None:
        """Synchronize model indexes."""
        collection = await self.get_collection(model)
        current_indexes = await collection.list_indexes().to_list(None)
        desired_indexes = model._indexes
        
        # Remove obsolete indexes
        for index in current_indexes:
            if not self._is_index_needed(index, desired_indexes):
                await collection.drop_index(index["name"])
                
        # Create missing indexes
        for index in desired_indexes:
            if not self._has_index(current_indexes, index):
                await collection.create_index(**index)
```

## Implementation Details

### 1. Registry Configuration
```python
class RegistryConfig:
    """Configuration for registry."""
    
    def __init__(
        self,
        auto_discover: bool = False,
        case_sensitive: bool = True,
        allow_override: bool = False
    ):
        self.auto_discover = auto_discover
        self.case_sensitive = case_sensitive
        self.allow_override = allow_override
```

### 2. Model Metadata
```python
class ModelMetadata:
    """Metadata for model configuration."""
    
    def __init__(
        self,
        name: str,
        collection: str,
        indexes: List[Dict[str, Any]],
        options: Dict[str, Any]
    ):
        self.name = name
        self.collection = collection
        self.indexes = indexes
        self.options = options
```

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts 
