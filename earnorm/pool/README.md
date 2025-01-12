# Connection Pool Components

Connection pooling system for EarnORM.

## Purpose

The pool module provides connection pooling capabilities:
- Connection management
- Pool configuration
- Resource monitoring
- Health checking
- Connection recycling
- Load balancing

## Concepts & Examples

### Basic Pool
```python
# Pool configuration
@pool_config
class MongoPool(ConnectionPool):
    min_size: int = 5
    max_size: int = 20
    timeout: float = 30.0
    max_lifetime: int = 3600
    idle_timeout: int = 300
    
    class Config:
        validate_on_borrow = True
        test_on_return = True
        fifo = True

# Pool usage
pool = MongoPool(
    uri="mongodb://localhost:27017",
    database="test"
)

async with pool.acquire() as conn:
    await conn.users.find_one({"id": 1})
```

### Pool Management
```python
# Pool manager
class PoolManager:
    def __init__(self):
        self.pools = {}
    
    def get_pool(self, name: str) -> ConnectionPool:
        if name not in self.pools:
            self.pools[name] = self.create_pool(name)
        return self.pools[name]
    
    def create_pool(self, name: str) -> ConnectionPool:
        config = load_pool_config(name)
        return ConnectionPool(**config)

# Pool metrics
@pool_metrics
class PoolMetrics:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "size": self.pool.size,
            "active": self.pool.active_connections,
            "idle": self.pool.idle_connections,
            "waiting": self.pool.waiting_requests
        }
```

### Health Checking
```python
# Health checker
@health_check
class PoolHealthCheck:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool
    
    async def check_health(self) -> bool:
        try:
            conn = await self.pool.acquire()
            await conn.ping()
            await self.pool.release(conn)
            return True
        except Exception:
            return False

# Connection validator
class ConnectionValidator:
    def validate(self, conn) -> bool:
        if conn.is_closed:
            return False
        if conn.idle_time > MAX_IDLE_TIME:
            return False
        return True
```

### Load Balancing
```python
# Load balancer
class PoolLoadBalancer:
    def __init__(self, pools: List[ConnectionPool]):
        self.pools = pools
    
    async def get_connection(self) -> Connection:
        pool = self.select_pool()
        return await pool.acquire()
    
    def select_pool(self) -> ConnectionPool:
        return min(
            self.pools,
            key=lambda p: p.active_connections
        )

# Connection routing
@connection_router
class ShardRouter:
    def get_pool(self, shard_key: str) -> ConnectionPool:
        shard_id = self.get_shard_id(shard_key)
        return self.pools[shard_id]
```

### Connection Lifecycle
```python
# Connection factory
class ConnectionFactory:
    def create_connection(self, **kwargs) -> Connection:
        conn = Connection(**kwargs)
        self.setup_connection(conn)
        return conn
    
    def setup_connection(self, conn: Connection):
        conn.set_codec_options(
            unicode_decode_error_handler='ignore'
        )
        conn.add_listener(ConnectionListener())

# Connection cleanup
@cleanup_handler
class ConnectionCleanup:
    def cleanup(self, pool: ConnectionPool):
        for conn in pool.get_idle_connections():
            if self.should_cleanup(conn):
                pool.remove(conn)
    
    def should_cleanup(self, conn: Connection) -> bool:
        return (
            conn.is_stale or
            conn.idle_time > MAX_IDLE_TIME or
            conn.lifetime > MAX_LIFETIME
        )
```

## Best Practices

1. **Pool Configuration**
- Set proper sizes
- Configure timeouts
- Enable validation
- Monitor usage
- Handle errors

2. **Connection Management**
- Validate connections
- Handle timeouts
- Recycle old connections
- Monitor health
- Log issues

3. **Performance**
- Optimize pool size
- Minimize waiting
- Handle peak loads
- Monitor metrics
- Tune settings

4. **Reliability**
- Health checks
- Connection validation
- Error handling
- Automatic recovery
- Monitoring

## Future Features

1. **Pool Features**
- [ ] Dynamic sizing
- [ ] Connection warming
- [ ] Priority queues
- [ ] Connection tagging
- [ ] Pool partitioning

2. **Management Features**
- [ ] Pool monitoring
- [ ] Auto recovery
- [ ] Connection profiling
- [ ] Usage analytics
- [ ] Health dashboard

3. **Performance Features**
- [ ] Async pooling
- [ ] Connection multiplexing
- [ ] Request pipelining
- [ ] Connection caching
- [ ] Query buffering

4. **Integration Features**
- [ ] Metrics export
- [ ] Tracing support
- [ ] Event notifications
- [ ] Admin interface
- [ ] Monitoring tools 