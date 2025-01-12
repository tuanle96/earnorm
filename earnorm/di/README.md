# Dependency Injection Components

Dependency Injection system for EarnORM using dependency-injector.

## Purpose

The DI module provides dependency injection capabilities:
- Container management
- Service providers
- Dependency resolution
- Lifecycle management
- Scoped dependencies
- Configuration injection

## Concepts & Examples

### Basic Container
```python
# Container definition
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # Database
    db = providers.Singleton(
        Database,
        uri=config.db.uri,
        pool_size=config.db.pool_size
    )
    
    # Services
    user_service = providers.Factory(
        UserService,
        db=db,
        cache=cache
    )
    
    # Repositories
    user_repository = providers.Factory(
        UserRepository,
        db=db
    )

# Container usage
container = Container()
container.config.from_dict({
    "db": {
        "uri": "mongodb://localhost:27017",
        "pool_size": 10
    }
})

user_service = container.user_service()
```

### Service Providers
```python
# Service definition
@injectable
class UserService:
    def __init__(self, db: Database, cache: Cache):
        self.db = db
        self.cache = cache
    
    @inject
    def get_user(self, user_id: str, auth: AuthService):
        if not auth.can_access(user_id):
            raise PermissionError()
        return self.db.users.find_one(id=user_id)

# Provider registration
class ServiceProvider(providers.Provider):
    def __init__(self):
        self.services = {
            "user": UserService,
            "auth": AuthService,
            "email": EmailService
        }
    
    def get_service(self, name):
        return self.services[name]()
```

### Scoped Dependencies
```python
# Request scope
class RequestScope(containers.DeclarativeContainer):
    request = providers.Object()
    
    session = providers.Singleton(
        Session,
        request=request
    )
    
    current_user = providers.Factory(
        get_current_user,
        session=session
    )

# Scope usage
@inject
def handle_request(request, scope: RequestScope):
    scope.override(request=request)
    user = scope.current_user()
    return process_request(user)
```

### Configuration Injection
```python
# Config injection
class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    db_pool = providers.Singleton(
        ConnectionPool,
        uri=config.db.uri,
        min_size=config.db.pool.min_size,
        max_size=config.db.pool.max_size
    )
    
    cache = providers.Singleton(
        Cache,
        host=config.cache.host,
        port=config.cache.port
    )

# Load config
container = AppContainer()
container.config.from_yaml('config.yml')
```

### Lifecycle Management
```python
# Resource lifecycle
class ResourceContainer(containers.DeclarativeContainer):
    @providers.singleton
    def database(self) -> Database:
        db = Database()
        yield db
        db.close()
    
    @providers.factory
    def session(self, db=database) -> Session:
        session = Session(db)
        yield session
        session.close()

# Cleanup
def shutdown():
    container.shutdown_resources()
```

## Best Practices

1. **Container Design**
- Single responsibility
- Clear dependencies
- Proper scoping
- Resource management
- Error handling

2. **Service Management**
- Interface based
- Loose coupling
- Clear lifecycle
- Easy testing
- Good documentation

3. **Configuration**
- Environment aware
- Validation
- Overrides
- Defaults
- Documentation

4. **Testing**
- Mock dependencies
- Test containers
- Verify injection
- Check lifecycles
- Monitor resources

## Future Features

1. **Container Features**
- [ ] Auto-discovery
- [ ] Hot reload
- [ ] Dependency graph
- [ ] Circular detection
- [ ] Plugin support

2. **Service Features**
- [ ] Async support
- [ ] Event system
- [ ] Middleware
- [ ] Interceptors
- [ ] Decorators

3. **Configuration Features**
- [ ] Schema validation
- [ ] Dynamic config
- [ ] Config inheritance
- [ ] Environment vars
- [ ] Secret management

4. **Development Features**
- [ ] Debug tools
- [ ] Performance monitoring
- [ ] Testing utilities
- [ ] Documentation gen
- [ ] IDE integration 