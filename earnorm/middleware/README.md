# Middleware Components

Middleware system components for EarnORM.

## Purpose

The middleware module provides request/response processing:
- Query preprocessing
- Result postprocessing
- Cross-cutting concerns
- Custom middleware chains
- Performance monitoring
- Error handling

## Concepts & Examples

### Query Middleware
```python
# Query transformation middleware
class QueryLoggerMiddleware(QueryMiddleware):
    def process_query(self, query):
        logger.info(f"Executing query: {query}")
        return query
        
    def process_result(self, result):
        logger.info(f"Query returned {len(result)} documents")
        return result

# Apply middleware
User.find().middleware(QueryLoggerMiddleware()).all()
```

### Model Middleware
```python
# Data transformation middleware
class TimestampMiddleware(ModelMiddleware):
    def before_save(self, instance):
        instance.updated_at = datetime.now()
        return instance
        
    def after_save(self, instance):
        cache.delete(f"user:{instance.id}")
        return instance

# Apply middleware
class User(BaseModel):
    class Meta:
        middleware = [TimestampMiddleware()]
```

### Middleware Chain
```python
# Chain multiple middleware
middleware_chain = MiddlewareChain([
    QueryLoggerMiddleware(),
    CacheMiddleware(),
    ValidationMiddleware(),
    AuthorizationMiddleware()
])

# Apply chain
User.find().middleware(middleware_chain).all()
```

### Custom Middleware
```python
class MetricsMiddleware(BaseMiddleware):
    def __init__(self, metrics_client):
        self.metrics = metrics_client
        
    def before_execute(self, context):
        context.start_time = time.time()
        
    def after_execute(self, context, result):
        duration = time.time() - context.start_time
        self.metrics.record(
            operation=context.operation,
            duration=duration,
            status="success"
        )
        return result
        
    def on_error(self, context, error):
        self.metrics.record(
            operation=context.operation,
            error=str(error),
            status="error"
        )
        raise error
```

## Best Practices

1. **Middleware Design**
- Keep middleware focused
- Handle errors properly
- Document behavior
- Consider order
- Monitor performance

2. **Chain Management**
- Order middleware correctly
- Handle dependencies
- Monitor chain length
- Document flow
- Test combinations

3. **Performance**
- Keep processing light
- Cache when possible
- Monitor overhead
- Handle timeouts
- Profile chains

4. **Error Handling**
- Handle all errors
- Provide context
- Log failures
- Clean up resources
- Maintain state

## Future Features

1. **Middleware Types**
- [ ] Caching middleware
- [ ] Security middleware
- [ ] Validation middleware
- [ ] Transformation middleware
- [ ] Monitoring middleware

2. **Chain Features**
- [ ] Dynamic chains
- [ ] Chain optimization
- [ ] Chain validation
- [ ] Chain visualization
- [ ] Chain metrics

3. **Management Features**
- [ ] Middleware registry
- [ ] Configuration API
- [ ] Hot reloading
- [ ] Health checks
- [ ] Performance monitoring

4. **Integration**
- [ ] Framework integration
- [ ] Plugin system
- [ ] External services
- [ ] Monitoring tools
- [ ] Development tools 