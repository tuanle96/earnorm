# Config Module

This module provides configuration management functionality for the EarnORM framework.

## Overview

The config module consists of three main components:

1. Configuration Model (`model.py`)
2. Configuration Data (`data.py`) 
3. Configuration Loading (`__init__.py`)

### Configuration Model

The configuration model provides the main interface for working with configuration:

```python
from earnorm.config import SystemConfig

# Load from environment
config = SystemConfig.load_env(".env")
print(config.database_uri)

# Load from YAML
config = SystemConfig.load_yaml("config.yaml")
print(config.redis_host)

# Save to YAML
config.save_yaml("new_config.yaml")
```

### Configuration Data

The data module handles field definitions and validation:

```python
from earnorm.config.data import SystemConfigData

# Load and validate
config = await SystemConfigData.load_env()
config.validate()

# Access computed values
print(config.database_options)
```

## Directory Structure

```
config/
├── __init__.py      # Package exports
├── model.py        # Configuration model
├── data.py        # Field definitions
└── README.md      # This file
```

## Features

### 1. Configuration Sources

- Environment variables (.env)
- YAML files
- Default values
- Required fields
- Computed values

### 2. Database Configuration

- Multiple backends (MongoDB, MySQL, PostgreSQL)
- Connection pooling
- SSL/TLS support
- Authentication
- Connection options

### 3. Redis Configuration

- Server settings
- Pool management
- Database selection
- Authentication
- Timeout settings

### 4. Cache Configuration

- Backend selection
- TTL settings
- Prefix management
- Pool settings

### 5. Event Configuration

- Backend selection
- Queue settings
- Batch processing
- Handler configuration

## Usage Examples

### Basic Usage

```python
from earnorm.config import SystemConfig

# Load from environment
config = SystemConfig.load_env(".env")

# Access settings
print(config.database_uri)
print(config.redis_host)
print(config.cache_ttl)

# Save configuration
config.save_yaml("config.yaml")
```

### Database Configuration

```python
# MongoDB configuration
config = SystemConfig(
    database_backend="mongodb",
    database_uri="mongodb://localhost:27017",
    database_name="mydb",
    database_min_pool_size=5,
    database_max_pool_size=20
)

# Access database options
print(config.database_options)
```

### Redis Configuration

```python
# Redis settings
config = SystemConfig(
    redis_host="localhost",
    redis_port=6379,
    redis_db=0,
    redis_min_pool_size=5,
    redis_max_pool_size=20
)
```

### Cache Configuration

```python
# Cache settings
config = SystemConfig(
    cache_backend="redis",
    cache_prefix="myapp",
    cache_ttl=3600
)
```

### Event Configuration

```python
# Event system settings
config = SystemConfig(
    event_enabled=True,
    event_queue="myapp:events",
    event_batch_size=100
)
```

## Implementation Notes

### 1. Configuration Loading

- Environment variables take precedence
- Support for multiple formats
- Default value handling
- Missing value handling

### 2. Validation Rules

- Type checking
- Value constraints
- Required fields
- Cross-field validation
- Custom validators

### 3. Security

- Sensitive data handling
- SSL/TLS configuration
- Credential management
- Access control

## Best Practices

1. Configuration Files
- Use environment variables for sensitive data
- Keep YAML files for defaults
- Version control configuration templates
- Document all options

2. Validation
- Always validate configuration
- Use appropriate constraints
- Handle validation errors
- Log validation issues

3. Security
- Never commit credentials
- Use environment variables
- Enable SSL/TLS
- Rotate credentials

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
