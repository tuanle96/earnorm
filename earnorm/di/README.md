# EarnORM Dependency Injection

EarnORM DI is a simple yet powerful dependency injection system designed for Python applications, especially for use with FastAPI.

## Key Features

- Container-based dependency management
- Service providers with lifecycle management
- Protocol-based dependency injection
- Seamless FastAPI integration
- Flexible configuration management
- Service lifecycle management

## Installation

EarnORM DI is included in the EarnORM package:

```bash
pdm add earnorm
```

## Basic Usage

### 1. Define Services

```python
from earnorm.di.types import BaseManager
from earnorm.base.pool import MongoPoolManager
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any

class DatabaseService(BaseManager):
    """MongoDB database service."""
    
    def __init__(self) -> None:
        self.pool_manager: Optional[MongoPoolManager] = None
        
    async def init(self) -> None:
        """Initialize database service."""
        self.pool_manager = MongoPoolManager()
        
    async def cleanup(self) -> None:
        """Cleanup database connections."""
        if self.pool_manager:
            self.pool_manager.close_all()
            
    def get_database(self, name: str = "earnbase"):
        """Get database by name."""
        return self.pool_manager.get_database()
        
    def get_collection(self, name: str):
        """Get collection by name."""
        return self.pool_manager.get_collection(name)

class UserService(BaseManager):
    """User service with database dependency."""
    
    def __init__(self, db_service: DatabaseService) -> None:
        self.db = db_service
        self.collection = None
        
    async def init(self) -> None:
        """Initialize user collection."""
        self.collection = self.db.get_collection("users")
        
    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.collection = None
        
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        return await self.collection.find_one({"_id": user_id})
        
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create new user."""
        result = await self.collection.insert_one(user_data)
        return str(result.inserted_id)
        
    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update user data."""
        result = await self.collection.update_one(
            {"_id": user_id}, 
            {"$set": update_data}
        )
        return result.modified_count > 0
```

### 2. Register Services with Container

```python
from earnorm.di.container import Container
from earnorm.di.types import BaseManager

# Initialize container
container = Container[BaseManager]()

# Register services
container.register(DatabaseService, DatabaseService)
container.register(UserService, UserService)

# Initialize services
await container.init()
```

### 3. FastAPI Integration

```python
from fastapi import FastAPI, Depends, HTTPException
from earnorm.di.container import container
from typing import Dict, Any, List

app = FastAPI()

# Dependencies
async def get_user_service():
    return container.get(UserService)

# User model for request/response
class UserCreate(BaseModel):
    name: str
    email: str
    role: str = "user"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str

# Routes
@app.post("/users", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Create new user."""
    user_id = await user_service.create_user(user.dict())
    return {"id": user_id, **user.dict()}

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    user_service: UserService = Depends(get_user_service)
):
    """Update user data."""
    # Remove None values
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
    
    success = await user_service.update_user(user_id, update_dict)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Get updated user
    user = await user_service.get_user(user_id)
    return user

# Lifecycle events
@app.on_event("startup")
async def startup():
    """Initialize services."""
    await container.init()

@app.on_event("shutdown")
async def shutdown():
    """Cleanup services."""
    await container.cleanup()
```

## Complete Example with Models

Here's a complete example using EarnORM models and DI:

```python
from earnorm.base.model import BaseModel
from earnorm.di.container import Container
from earnorm.di.types import BaseManager
from fastapi import FastAPI, Depends, HTTPException
from typing import Optional, Dict, Any
import uvicorn

# 1. Define Model
class User(BaseModel):
    """User model."""
    
    _collection = "users"
    
    # Validators
    _validators = [
        lambda user: assert user._data.get("email"), "Email is required",
        lambda user: assert "@" in user._data.get("email", ""), "Invalid email"
    ]
    
    # Indexes
    _indexes = {
        "email_unique": {
            "keys": [("email", 1)],
            "unique": True
        }
    }
    
    # Access control
    _acl = {
        "create": ["admin"],
        "read": ["admin", "user"],
        "update": ["admin"],
        "delete": ["admin"]
    }
    
    # Audit config
    _audit = {
        "enabled": True,
        "events": ["create", "update", "delete"]
    }
    
    # Cache config
    _cache = {
        "enabled": True,
        "ttl": 300  # 5 minutes
    }

# 2. Define Services
class UserService(BaseManager):
    """User service."""
    
    def __init__(self) -> None:
        self.model = User
        
    async def init(self) -> None:
        """Initialize service."""
        pass
        
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
        
    async def create_user(self, data: Dict[str, Any]) -> str:
        """Create new user."""
        user = self.model(**data)
        await user.save()
        return str(user._data["_id"])
        
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        user = await self.model.find_one({"_id": user_id})
        return user._data if user else None
        
    async def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user."""
        user = await self.model.find_one({"_id": user_id})
        if not user:
            return False
            
        user._data.update(data)
        await user.save()
        return True
        
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        user = await self.model.find_one({"_id": user_id})
        if not user:
            return False
            
        await user.delete()
        return True

# 3. Setup Container
container = Container[BaseManager]()
container.register(UserService, UserService)

# 4. Create FastAPI App
app = FastAPI(title="EarnORM Example")

# 5. Define Dependencies
def get_user_service():
    return container.get(UserService)

# 6. Define Routes
@app.post("/users")
async def create_user(
    user: Dict[str, Any],
    user_service: UserService = Depends(get_user_service)
):
    """Create new user."""
    try:
        user_id = await user_service.create_user(user)
        return {"id": user_id, **user}
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Get user by ID."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: Dict[str, Any],
    user_service: UserService = Depends(get_user_service)
):
    """Update user."""
    try:
        success = await user_service.update_user(user_id, update_data)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return await user_service.get_user(user_id)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    user_service: UserService = Depends(get_user_service)
):
    """Delete user."""
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

# 7. Setup Lifecycle Events
@app.on_event("startup")
async def startup():
    """Initialize all services."""
    await container.init()

@app.on_event("shutdown")
async def shutdown():
    """Cleanup all services."""
    await container.cleanup()

# 8. Run Application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced Features

### 1. Lifecycle Hooks

```python
from earnorm.di.lifecycle import LifecycleHooks
from earnorm.base.pool import MongoPoolManager

class DatabaseService(BaseManager, LifecycleHooks):
    def __init__(self) -> None:
        self.pool_manager = MongoPoolManager()
        
    async def on_init(self):
        """Initialize database connections."""
        # Setup connection pools
        self.pool_manager.get_pool("mongodb://localhost:27017")
        
    async def on_start(self):
        """Start monitoring."""
        # Setup monitoring
        pass
        
    async def on_stop(self):
        """Stop monitoring."""
        # Cleanup monitoring
        pass
        
    async def on_cleanup(self):
        """Cleanup all resources."""
        self.pool_manager.close_all()
```

### 2. Service Provider Pattern

```python
from earnorm.di.providers import ServiceProvider
from earnorm.base.pool import MongoPoolManager

# Create provider
provider = ServiceProvider()

# Register core services
provider.register("database", DatabaseService)
provider.register("user", UserService)
provider.register("pool", MongoPoolManager)

# Initialize all services
await provider.start_all()

# Stop all services
await provider.stop_all()
```

## Best Practices

1. **Use Protocols**: Always define and use protocols for services to ensure loose coupling.

2. **Lifecycle Management**: Implement init() and cleanup() methods for each service properly.

3. **Dependency Chain**: Arrange dependencies in a logical initialization order.

4. **Configuration**: Use configuration injection through the container constructor.

5. **Testing**: Use mock services in testing by registering mock implementations.

## Testing

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from earnorm.base.pool import MongoPoolManager

class MockMongoPoolManager(MongoPoolManager):
    def __init__(self):
        super().__init__()
        self.collection = AsyncMock()
        
    def get_collection(self, name: str):
        return self.collection

class MockDatabaseService(DatabaseService):
    async def init(self):
        self.pool_manager = MockMongoPoolManager()

@pytest.fixture
async def test_container():
    container = Container()
    container.register(DatabaseService, MockDatabaseService)
    container.register(UserService, UserService)
    await container.init()
    yield container
    await container.cleanup()

async def test_user_service(test_container):
    user_service = test_container.get(UserService)
    
    # Setup mock return value
    user_service.db.pool_manager.collection.find_one.return_value = {
        "_id": "123",
        "name": "Test User",
        "email": "test@example.com"
    }
    
    # Test get_user
    user = await user_service.get_user("123")
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
