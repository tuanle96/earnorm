# Environment-based Caching Implementation Plan

## 1. Current State Analysis

The current Environment class has basic initialization and adapter management:

```python
class Environment:
    def __init__(self) -> None:
        self._initialized = False
        self._adapter: Optional[DatabaseAdapter[DatabaseModel]] = None
        Environment._instance = self
```

## 2. Required Enhancements

### 2.1 Add Cache Storage to Environment

```python
class Environment:
    def __init__(self) -> None:
        self._initialized = False
        self._adapter = None
        
        # Cache for record data
        self._cache = {}  # {model_name: {id: {field: value}}}
        
        # Track loaded fields
        self._loaded_fields = {}  # {model_name: {id: set(field_names)}}
        
        # Prefetch records
        self._prefetch = {}  # {model_name: set(ids)}
```

### 2.2 Example Usage Cases

#### Case 1: Basic Field Access
```python
# Current implementation
user = await User.browse("user_1")
name = await user.name  # Queries DB every time

# Enhanced implementation with cache
user = await User.browse("user_1")
name = await user.name  # First time: DB query + cache
name = await user.name  # Subsequent calls: from cache
```

#### Case 2: Multiple Record Loading
```python
# Current implementation
users = await User.search([("age", ">", 18)])
for user in users:
    print(await user.name)  # N queries for N users

# Enhanced implementation with prefetch
users = await User.search([("age", ">", 18)])
await users._prefetch_records(["name"])  # 1 query for all users
for user in users:
    print(await user.name)  # All from cache
```

#### Case 3: Converting to Dictionary
```python
# Current implementation
user_dict = await user.to_dict()  # Queries all fields

# Enhanced implementation with selective loading
user_dict = await user.to_dict(fields=["name", "email"])  # Only loads required fields
```

## 3. Implementation Plan

### 3.1 Environment Cache Management

```python
class Environment:
    def clear_cache(self, model_name: Optional[str] = None) -> None:
        """Clear cache for specific model or all models."""
        if model_name:
            self._cache.pop(model_name, None)
            self._loaded_fields.pop(model_name, None)
        else:
            self._cache.clear()
            self._loaded_fields.clear()
            
    def invalidate_record(self, model_name: str, record_id: str) -> None:
        """Invalidate specific record in cache."""
        if model_name in self._cache:
            self._cache[model_name].pop(record_id, None)
            self._loaded_fields[model_name].pop(record_id, None)
```

### 3.2 BaseModel Enhancements

#### Lazy Loading with Cache
```python
class BaseModel:
    async def __getattr__(self, name: str) -> Any:
        """Lazy load with cache check."""
        if name in self.__fields__:
            # Check cache first
            cached_value = self._env._cache.get(self._name, {}).get(self.id, {}).get(name)
            if cached_value is not None:
                return cached_value
                
            # Load from DB if not in cache
            query = await self._where_calc([("id", "=", self.id)])
            result = await query.execute()
            if result:
                # Update cache
                self._env._cache.setdefault(self._name, {}).setdefault(self.id, {})[name] = result[0][name]
                # Mark field as loaded
                self._env._loaded_fields.setdefault(self._name, {}).setdefault(self.id, set()).add(name)
                return result[0][name]
```

#### Efficient Prefetching
```python
class BaseModel:
    async def _prefetch_records(self, fields: List[str]) -> None:
        """Prefetch multiple records efficiently."""
        # Get uncached records
        uncached_ids = [
            id_ for id_ in self._ids 
            if not all(
                f in self._env._loaded_fields.get(self._name, {}).get(id_, set())
                for f in fields
            )
        ]
        
        if uncached_ids:
            # Load from DB
            query = await self._where_calc([("id", "in", uncached_ids)])
            query.select(fields)
            results = await query.execute()
            
            # Update cache
            for record in results:
                record_id = record["id"]
                for field in fields:
                    self._env._cache.setdefault(self._name, {}).setdefault(record_id, {})[field] = record[field]
                    self._env._loaded_fields.setdefault(self._name, {}).setdefault(record_id, set()).add(field)
```

#### Optimized to_dict()
```python
class BaseModel:
    async def to_dict(self, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Convert to dictionary using cache."""
        self.ensure_one()
        if not self.id:
            return {}
            
        # Determine fields to get
        fields_to_get = fields or list(self.__fields__.keys())
        
        # Prefetch if needed
        await self._prefetch_records(fields_to_get)
        
        # Get from cache
        return {
            field: self._env._cache[self._name][self.id].get(field)
            for field in fields_to_get
        }
```

## 4. Benefits

1. **Performance Optimization**
   - Reduced database queries
   - Efficient batch loading
   - Memory-efficient caching

2. **Consistency**
   - Shared cache across recordsets
   - Consistent data access patterns
   - Clear invalidation strategy

3. **Flexibility**
   - Selective field loading
   - Easy cache management
   - Extensible design

## 5. Example Usage Scenarios

### Scenario 1: Complex User Management
```python
# Create user management system
class UserManager:
    def __init__(self, env: Environment):
        self.env = env
        
    async def get_user_details(self, user_ids: List[str]) -> List[Dict[str, Any]]:
        users = await User.browse(user_ids)
        # Prefetch commonly accessed fields
        await users._prefetch_records(["name", "email", "status"])
        return [await user.to_dict(["name", "email", "status"]) for user in users]
        
    async def update_user(self, user_id: str, values: Dict[str, Any]) -> None:
        user = await User.browse(user_id)
        await user.write(values)
        # Invalidate cache after update
        self.env.invalidate_record("user", user_id)
```

### Scenario 2: Batch Processing
```python
async def process_orders(order_ids: List[str]) -> None:
    orders = await Order.browse(order_ids)
    # Prefetch all needed fields in one query
    await orders._prefetch_records(["status", "amount", "customer_id"])
    
    for order in orders:
        # All data comes from cache
        if await order.status == "pending" and await order.amount > 1000:
            customer_id = await order.customer_id
            # Process order...
```

## 6. Next Steps

1. Implement base cache structure in Environment
2. Add cache-aware field access in BaseModel
3. Implement prefetch mechanism
4. Update to_dict() to use cache
5. Add cache invalidation hooks
6. Write tests for cache behavior
7. Document cache usage patterns

## 7. Future Enhancements

1. Cache expiration policies
2. Redis-based shared cache
3. Cache warming strategies
4. Cache size limits
5. Cache statistics and monitoring 
