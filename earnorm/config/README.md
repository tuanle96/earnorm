# Configuration Components

Configuration management for EarnORM with MongoDB backend storage.

## Purpose

The config module provides configuration capabilities:
- Database-backed configuration storage
- Environment-specific configuration
- Dynamic configuration updates
- Configuration versioning and history
- Type-safe configuration classes
- Multi-environment support
- Security and access control

## Core Components

### 1. Config Model

The core model for storing configurations in MongoDB:

```python
class ConfigModel(BaseModel):
    """Config model for MongoDB storage"""
    
    _collection = "system.config"
    _indexes = [
        {"keys": [("key", 1)], "unique": True},
        {"keys": [("environment", 1), ("key", 1)], "unique": True}
    ]
    
    key: str = String(required=True)
    value: Any = Dict(required=True)
    environment: str = String(required=True)
    description: str = String(required=False)
    created_at: datetime = DateTime(default_factory=datetime.utcnow)
    updated_at: datetime = DateTime(default_factory=datetime.utcnow)
    version: int = Int(default=1)
    is_active: bool = Bool(default=True)
```

### 2. Config Manager

Central configuration management:

```python
class ConfigManager:
    """Configuration manager"""
    
    async def init(self) -> None:
        """Initialize config manager"""
        configs = await ConfigModel.search([
            ("is_active", "=", True),
            ("environment", "=", Environment.current())
        ])
        for config in configs:
            self._cache[config.key] = config.value
            
    async def get(self, key: str, default: Any = None) -> Any:
        """Get config value"""
        if not self._initialized:
            await self.init()
        return self._cache.get(key, default)
        
    async def set(
        self,
        key: str,
        value: Any,
        description: Optional[str] = None
    ) -> None:
        """Set config value"""
        await ConfigModel.set_config(key, value, description)
        self._cache[key] = value
```

## Usage Examples

### 1. Basic Configuration

```python
# Define configuration class
class DatabaseConfig(BaseConfig):
    """Database configuration"""
    uri: str = Field(..., description="MongoDB connection URI")
    database: str = Field(..., description="Database name")
    min_pool_size: int = Field(5, ge=1, le=100)
    max_pool_size: int = Field(20, ge=1, le=1000)
    
    class Config:
        env_prefix = "EARNORM_DB_"

# Load configuration
config_manager = ConfigManager()
await config_manager.init()
db_config = await config_manager.load_config(DatabaseConfig)

# Use configuration
print(f"Database URI: {db_config.uri}")
print(f"Pool Size: {db_config.min_pool_size}-{db_config.max_pool_size}")
```

### 2. Environment-Specific Config

```python
# Set environment-specific config
await ConfigModel.set_config(
    key="databaseconfig",
    value={
        "uri": "mongodb://prod:27017",
        "database": "earnbase_prod",
        "min_pool_size": 10,
        "max_pool_size": 50
    },
    environment="production",
    description="Production database config"
)

# Load environment config
env = Environment.current()
db_config = await config_manager.load_config(DatabaseConfig)
```

### 3. Dynamic Updates

```python
# Update configuration
await config_manager.set(
    key="cacheconfig",
    value={
        "ttl": 7200,
        "max_size": 1000
    },
    description="Updated cache settings"
)

# Configuration will be updated without restart
cache_config = await config_manager.load_config(CacheConfig)
```

### 4. Version History

```python
# Get config history
history = await ConfigModel.search([
    ("key", "=", "databaseconfig"),
    ("environment", "=", Environment.current())
], order_by=[("version", -1)])

# Rollback to previous version
if len(history) > 1:
    previous = history[1]
    await config_manager.set(
        key="databaseconfig",
        value=previous.value,
        description="Rollback to version " + str(previous.version)
    )
```

## Best Practices

### 1. Configuration Design

- Use type hints for all config fields
- Add field descriptions and validation rules
- Keep configurations focused and modular
- Use environment-specific defaults
- Document all configuration options

### 2. Security

- Store sensitive data encrypted
- Use environment variables for secrets
- Implement access control for config changes
- Audit all configuration changes
- Validate configuration values

### 3. Performance

- Use caching for frequently accessed configs
- Batch load configurations on startup
- Implement lazy loading for large configs
- Monitor configuration access patterns
- Optimize database queries

### 4. Operations

- Backup configurations regularly
- Monitor configuration changes
- Implement health checks
- Set up alerts for critical changes
- Document operational procedures

### 5. Development

- Use type checking tools
- Write tests for configurations
- Follow naming conventions
- Document configuration dependencies
- Use version control

## Future Features

### 1. Configuration Features

- [ ] Schema evolution support
- [ ] Configuration templates
- [ ] Configuration inheritance
- [ ] Default value management
- [ ] Configuration validation rules

### 2. Security Features

- [ ] Field-level encryption
- [ ] Role-based access control
- [ ] Audit logging
- [ ] Secret rotation
- [ ] Compliance reporting

### 3. Management Features

- [ ] Web UI for configuration
- [ ] Bulk configuration updates
- [ ] Import/export functionality
- [ ] Search and filtering
- [ ] Configuration comparison

### 4. Integration Features

- [ ] Service discovery integration
- [ ] Configuration events
- [ ] External system notifications
- [ ] API endpoints
- [ ] Webhook support

### 5. Monitoring Features

- [ ] Usage analytics
- [ ] Performance metrics
- [ ] Health monitoring
- [ ] Alert management
- [ ] Dashboard integration

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of EarnORM and is licensed under the same terms. 
