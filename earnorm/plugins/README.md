# Plugin Components

Plugin system components for EarnORM.

## Purpose

The plugins module provides extensibility features:
- Plugin registration
- Plugin hooks
- Plugin configuration
- Plugin discovery
- Plugin management
- Plugin marketplace

## Concepts & Examples

### Basic Plugins
```python
# Timestamp plugin
@plugin("timestamp")
class TimestampPlugin:
    def before_save(self, instance):
        instance.updated_at = datetime.now()
        if not instance.id:
            instance.created_at = datetime.now()

# Soft delete plugin
@plugin("softdelete")
class SoftDeletePlugin:
    def before_delete(self, instance):
        instance.deleted_at = datetime.now()
        instance.save()
        return False  # Prevent actual deletion
        
    def get_queryset(self, queryset):
        return queryset.filter(deleted_at=None)

# Apply plugins
class User(BaseModel):
    class Meta:
        plugins = ["timestamp", "softdelete"]
```

### Plugin Configuration
```python
# Configurable plugin
@plugin("cache")
class CachePlugin:
    def __init__(self, ttl=3600, prefix="cache"):
        self.ttl = ttl
        self.prefix = prefix
        
    def after_get(self, instance):
        key = f"{self.prefix}:{instance.id}"
        cache.set(key, instance, ttl=self.ttl)
        
    def before_save(self, instance):
        key = f"{self.prefix}:{instance.id}"
        cache.delete(key)

# Apply with config
class User(BaseModel):
    class Meta:
        plugins = {
            "cache": {"ttl": 1800, "prefix": "user"}
        }
```

### Custom Hooks
```python
# Define custom hooks
class AuditPlugin(BasePlugin):
    @hook("after_change")
    def log_change(self, instance, changes):
        AuditLog.create(
            model=instance.__class__.__name__,
            instance_id=instance.id,
            changes=changes
        )
    
    @hook("after_access")
    def log_access(self, instance, user):
        AccessLog.create(
            model=instance.__class__.__name__,
            instance_id=instance.id,
            user=user
        )

# Multiple hooks
class ValidationPlugin(BasePlugin):
    @hook(["before_save", "before_update"])
    def validate_data(self, instance):
        if not instance.is_valid():
            raise ValidationError()
```

### Plugin Management
```python
# Register plugin
registry = PluginRegistry()
registry.register("audit", AuditPlugin)
registry.register_many({
    "timestamp": TimestampPlugin,
    "softdelete": SoftDeletePlugin
})

# Get plugin info
plugin = registry.get_plugin("audit")
print(f"Name: {plugin.name}")
print(f"Version: {plugin.version}")
print(f"Hooks: {plugin.hooks}")

# Enable/disable plugins
registry.enable("audit")
registry.disable("softdelete")
```

## Best Practices

1. **Plugin Design**
- Keep plugins focused
- Handle errors gracefully
- Document behavior
- Support configuration
- Test thoroughly

2. **Hook Management**
- Define clear hooks
- Handle dependencies
- Order hooks properly
- Document side effects
- Monitor performance

3. **Configuration**
- Validate settings
- Provide defaults
- Document options
- Handle changes
- Version configs

4. **Maintenance**
- Monitor usage
- Track performance
- Update regularly
- Handle conflicts
- Clean up resources

## Future Features

1. **Plugin Types**
- [ ] Field plugins
- [ ] Query plugins
- [ ] Validation plugins
- [ ] Migration plugins
- [ ] UI plugins

2. **Hook System**
- [ ] Async hooks
- [ ] Hook priorities
- [ ] Hook chains
- [ ] Hook events
- [ ] Hook debugging

3. **Management Features**
- [ ] Plugin store
- [ ] Version control
- [ ] Dependency management
- [ ] Health monitoring
- [ ] Analytics

4. **Integration**
- [ ] Package management
- [ ] CI/CD pipeline
- [ ] Documentation
- [ ] Testing tools
- [ ] Deployment tools 