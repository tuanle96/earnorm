# Logging Module

The logging module provides a comprehensive logging solution for EarnORM, with features like:
- Multiple output handlers (console, MongoDB)
- Log processing (filtering, formatting, context)
- Analytics and reporting
- Log maintenance and archiving

## Components

### Handlers

Handlers are responsible for sending log entries to their destinations:

- `ConsoleHandler`: Outputs logs to console with color support
- `MongoHandler`: Stores logs in MongoDB with retry logic

Example:
```python
# Console output
handler = ConsoleHandler(
    format_string='[{level}] {message}',
    color=True
)

# MongoDB storage
handler = MongoHandler(
    batch_size=100,
    max_retries=3
)
```

### Processors

Processors modify log entries before they are sent to handlers:

- `ContextProcessor`: Adds context like environment, hostname
- `FilterProcessor`: Filters logs based on level, patterns
- `FormatterProcessor`: Formats errors, stack traces

Example:
```python
# Add context
processor = ContextProcessor(
    environment='production',
    hostname='web-1'
)

# Filter logs
processor = FilterProcessor(
    min_level='WARNING',
    exclude_patterns=['debug.*']
)

# Format errors
processor = FormatterProcessor(
    max_trace_length=50
)
```

### Analytics & Reporting

Tools for analyzing logs and generating reports:

- Error distribution
- Log volume by level
- Slow operations
- Error trends

Example:
```python
# Get error distribution
analytics = logger.get_analytics()
errors = await analytics.get_error_distribution(
    start_time=datetime.now() - timedelta(days=1),
    end_time=datetime.now()
)

# Generate daily report
reports = logger.get_reports()
report = await reports.generate_daily_report(
    date=datetime.now()
)
```

### Maintenance

Tools for managing logs:

- Cleanup old logs
- Archive logs
- Monitor storage
- Backup logs

Example:
```python
# Clean up old logs
maintenance = logger.get_maintenance()
await maintenance.cleanup_old_logs(
    max_age_days=30,
    exclude_levels=['ERROR', 'CRITICAL']
)

# Archive logs
archiver = logger.get_archiver()
await archiver.archive_logs(
    start_time=datetime.now() - timedelta(days=7),
    end_time=datetime.now()
)
```

## Usage

### Basic Setup

```python
from earnorm.logging import logger

# Set up logging
await logger.setup(
    level='INFO',
    handlers=['console', 'mongo'],
    console_format='[{level}] {message}'
)

# Log messages
await logger.info('Application started')
await logger.error('Operation failed', error=ValueError('Invalid input'))
```

### Context Management

```python
# Add context to logs
with logger.context(user_id='123', request_id='abc'):
    await logger.info('Processing request')
    await logger.error('Request failed', error=Exception('Database error'))
```

### Convenience Functions

```python
from earnorm.logging import debug, info, warning, error, critical

# Log messages directly
await info('Application started')
await error('Operation failed', error=ValueError('Invalid input'))
```

## Best Practices

1. **Log Levels**
   - DEBUG: Detailed information for debugging
   - INFO: General information about program execution
   - WARNING: Indicate a potential problem
   - ERROR: A more serious problem
   - CRITICAL: Program may not be able to continue

2. **Context**
   - Always include relevant context (user, request, etc.)
   - Use context managers for request-scoped context
   - Don't include sensitive information

3. **Performance**
   - Use batching for database handlers
   - Filter logs early to reduce processing
   - Archive old logs regularly

4. **Error Handling**
   - Include full error information
   - Use stack traces for debugging
   - Don't expose sensitive error details in production

5. **Maintenance**
   - Set up log rotation
   - Monitor disk usage
   - Archive important logs
   - Clean up old logs regularly 
