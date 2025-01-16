# Config Module

This module provides configuration management for EarnORM.

## Features

- Singleton pattern - only one config instance exists
- Multiple config file formats support (YAML, ENV)
- MongoDB persistence
- Global access via registry/environment
- Type safety and validation
- Default values for all settings
- Feature toggles for cache and events
- Encryption for sensitive data
- Config versioning and migration
- Backup/restore functionality
- Config change listeners

## Usage

### Basic Usage

```python
from earnorm.config import SystemConfig

# Get config instance
config = await SystemConfig.get_instance()

# Access config values
print(config.mongo_uri)
print(config.redis_host)

# Update config values
config.redis_port = 6380
await config.save()

# Update multiple values
await config.write({
    "redis_host": "localhost",
    "redis_port": 6379
})
```

### Loading Config Files

```python
from earnorm.config import ConfigManager

# Load from YAML file
config_data = await ConfigManager.load_config("config.yaml")

# Load from ENV file
config_data = await ConfigManager.load_config(".env")

# Update config with loaded data
config = await SystemConfig.get_instance()
await config.write(config_data)
```

### Encryption

```python
from cryptography.fernet import Fernet

# Generate encryption key
key = Fernet.generate_key()

# Set encryption key
SystemConfig.set_encryption_key(key)

# Sensitive fields will be encrypted automatically
config = await SystemConfig.get_instance()
config.mongo_uri = "mongodb://user:pass@localhost"
await config.save()
```

### Config Change Listeners

```python
async def on_config_change(config):
    print(f"Config changed: {config.data}")

# Add listener
SystemConfig.add_listener(on_config_change)

# Listener will be called after each save
config = await SystemConfig.get_instance()
config.redis_port = 6380
await config.save()  # Will trigger listener
```

### Backup/Restore

```python
# Backup config to file
config = await SystemConfig.get_instance()
await config.backup("config_backup.yaml")

# Restore config from file
config = await SystemConfig.restore("config_backup.yaml")
```

## Config Files

### YAML Format (config.yaml)

```yaml
# MongoDB Configuration
mongo_uri: mongodb://localhost:27017
mongo_database: earnbase
mongo_min_pool_size: 5
mongo_max_pool_size: 20
mongo_timeout: 30
mongo_max_lifetime: 3600
mongo_idle_timeout: 300

# Redis Configuration
redis_host: localhost
redis_port: 6379
redis_db: 0
redis_min_pool_size: 5
redis_max_pool_size: 20
redis_timeout: 30

# Cache Configuration
cache_enabled: true
cache_ttl: 3600
cache_prefix: earnorm:
cache_max_retries: 3

# Event Configuration
event_enabled: true
event_queue: earnorm:events
event_batch_size: 100
```

### ENV Format (.env)

```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=earnbase
MONGO_MIN_POOL_SIZE=5
MONGO_MAX_POOL_SIZE=20
MONGO_TIMEOUT=30
MONGO_MAX_LIFETIME=3600
MONGO_IDLE_TIMEOUT=300

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MIN_POOL_SIZE=5
REDIS_MAX_POOL_SIZE=20
REDIS_TIMEOUT=30

# Cache Configuration
CACHE_ENABLED=true
CACHE_TTL=3600
CACHE_PREFIX=earnorm:
CACHE_MAX_RETRIES=3

# Event Configuration
EVENT_ENABLED=true
EVENT_QUEUE=earnorm:events
EVENT_BATCH_SIZE=100
```

## Best Practices

1. **Config Files**
   - Use YAML for human-readable configs
   - Use ENV for environment-specific configs
   - Keep sensitive data in ENV files
   - Use version control for config files
   - Don't commit sensitive data

2. **Security**
   - Always encrypt sensitive data
   - Use environment variables for secrets
   - Rotate encryption keys regularly
   - Validate config values

3. **Maintenance**
   - Keep config files up to date
   - Document all config options
   - Use meaningful default values
   - Version config schema
   - Backup configs regularly

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Add tests for your changes
5. Run the test suite
6. Create a pull request 
