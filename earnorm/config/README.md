# Configuration Components

Configuration management for EarnORM.

## Purpose

The config module provides configuration capabilities:
- Configuration management
- Environment management
- Feature flags
- Settings validation
- Dynamic configuration
- Configuration versioning

## Concepts & Examples

### Basic Configuration
```python
# Configuration definition
@config
class DatabaseConfig(BaseConfig):
    host: str = "localhost"
    port: int = 27017
    database: str = "test"
    username: str = Field(env="DB_USER")
    password: str = Field(env="DB_PASS")
    
    class Config:
        env_prefix = "EARNORM_"
        case_sensitive = False

# Load configuration
config = DatabaseConfig.load()
print(f"Database URL: mongodb://{config.host}:{config.port}")
```

### Environment Management
```python
# Environment configuration
@environment
class Environment:
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def is_production(cls):
        return cls.current() == cls.PRODUCTION
    
    @classmethod
    def load_config(cls):
        return ConfigFactory.for_environment(cls.current())

# Environment-specific config
class ProductionConfig(BaseConfig):
    debug: bool = False
    cache_ttl: int = 3600
    pool_size: int = 100
```

### Feature Flags
```python
# Feature flag definition
@feature_flags
class Features:
    NEW_QUERY_BUILDER = Flag(
        name="new_query_builder",
        default=False,
        description="Use new query builder"
    )
    
    ASYNC_CACHE = Flag(
        name="async_cache",
        default=True,
        description="Use async cache backend"
    )

# Feature checking
if Features.NEW_QUERY_BUILDER.enabled:
    query = NewQueryBuilder()
else:
    query = LegacyQueryBuilder()
```

### Dynamic Configuration
```python
# Dynamic settings
@dynamic_config
class CacheConfig(BaseConfig):
    ttl: int = 3600
    max_size: int = 1000
    
    @on_change("ttl")
    def update_ttl(self, old_value, new_value):
        cache.set_ttl(new_value)
        
    @validate("max_size")
    def validate_size(self, value):
        if value < 100:
            raise ValueError("max_size must be >= 100")

# Update configuration
config.update({
    "ttl": 7200,
    "max_size": 2000
})
```

### Configuration Validation
```python
# Validation rules
class MongoConfig(BaseConfig):
    uri: str = Field(regex=r"mongodb://.*")
    pool_size: int = Field(ge=1, le=1000)
    timeout: float = Field(gt=0)
    
    @validator("uri")
    def validate_uri(cls, v):
        try:
            urlparse(v)
            return v
        except Exception:
            raise ValueError("Invalid MongoDB URI")

# Load and validate
try:
    config = MongoConfig.parse_file("config.json")
except ValidationError as e:
    print(f"Invalid configuration: {e}")
```

## Best Practices

1. **Configuration Design**
- Use type hints
- Validate inputs
- Document options
- Handle defaults
- Support overrides

2. **Security**
- Protect secrets
- Use environment vars
- Encrypt sensitive data
- Control access
- Audit changes

3. **Maintenance**
- Version configs
- Backup settings
- Monitor changes
- Clean up old configs
- Document updates

4. **Integration**
- Support multiple formats
- Handle migrations
- Validate changes
- Notify services
- Log updates

## Future Features

1. **Configuration Features**
- [ ] Schema evolution
- [ ] Config migration
- [ ] Config templates
- [ ] Config inheritance
- [ ] Config validation

2. **Management Features**
- [ ] UI management
- [ ] Version control
- [ ] Change tracking
- [ ] Rollback support
- [ ] Audit logging

3. **Integration Features**
- [ ] Service discovery
- [ ] Config server
- [ ] Change notifications
- [ ] Health checks
- [ ] Metrics collection

4. **Security Features**
- [ ] Encryption
- [ ] Access control
- [ ] Audit trails
- [ ] Secret management
- [ ] Compliance checks 