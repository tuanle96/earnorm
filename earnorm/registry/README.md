# Registry Components

Model registry and metadata management for EarnORM.

## Purpose

The registry module provides model registration and discovery:
- Model registration
- Model metadata
- Model relationships
- Plugin registry
- Model discovery

## Concepts & Examples

### Model Registration
```python
# Automatic registration
class User(BaseModel):
    _collection = "users"
    name = StringField()
    email = EmailField()

# Manual registration
registry = ModelRegistry()
registry.register(User)
registry.register_many([Order, Product])

# Get registered models
user_model = registry.get_model("User")
all_models = registry.get_all_models()
```

### Model Metadata
```python
class User(BaseModel):
    class Meta:
        collection = "users"
        indexes = [
            {"fields": [("email", 1)], "unique": True}
        ]
        validators = [
            UniqueValidator("email")
        ]
        plugins = ["timestamp", "softdelete"]

# Access metadata
metadata = registry.get_metadata(User)
collection = metadata.collection
indexes = metadata.indexes
```

### Model Relationships
```python
class Order(BaseModel):
    user = ReferenceField("User")
    items = ListField(ReferenceField("Product"))

# Get relationships
relations = registry.get_relationships(Order)
dependent_models = registry.get_dependents(User)
referenced_models = registry.get_references(User)
```

### Plugin Registry
```python
# Register plugin
@registry.plugin("timestamp")
class TimestampPlugin:
    def before_save(self, instance):
        instance.updated_at = datetime.now()
        if not instance.id:
            instance.created_at = datetime.now()

# Apply plugin
class User(BaseModel):
    class Meta:
        plugins = ["timestamp"]
```

## Best Practices

1. **Model Registration**
- Register models early
- Handle duplicates
- Validate metadata
- Document relationships
- Clean up unused models

2. **Metadata Management**
- Keep metadata focused
- Version metadata
- Cache metadata
- Handle changes
- Monitor conflicts

3. **Plugin Management**
- Test plugin compatibility
- Document dependencies
- Handle conflicts
- Monitor performance
- Version plugins

4. **Maintenance**
- Monitor registry size
- Clean up old entries
- Track changes
- Backup registry
- Validate integrity

## Future Features

1. **Registry Features**
- [ ] Dynamic registration
- [ ] Registry replication
- [ ] Registry events
- [ ] Registry API
- [ ] Registry UI

2. **Metadata Features**
- [ ] Metadata versioning
- [ ] Metadata validation
- [ ] Metadata inheritance
- [ ] Metadata API
- [ ] Metadata UI

3. **Plugin Features**
- [ ] Plugin dependencies
- [ ] Plugin versioning
- [ ] Plugin marketplace
- [ ] Plugin testing
- [ ] Plugin metrics

4. **Integration**
- [ ] Schema registry
- [ ] Service discovery
- [ ] API documentation
- [ ] Code generation
- [ ] Development tools 