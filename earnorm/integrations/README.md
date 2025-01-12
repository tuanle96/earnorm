# Integration Components

Integration components for EarnORM.

## Purpose

The integrations module provides external service integration:
- GraphQL integration
- REST API integration
- Elasticsearch integration
- Redis integration
- Kafka integration
- Cloud services integration

## Concepts & Examples

### GraphQL Integration
```python
# Define GraphQL types
@graphql_type
class User(BaseModel):
    name = StringField()
    email = EmailField()
    age = IntegerField()
    
    @graphql_field
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @graphql_mutation
    def update_email(self, email: str) -> bool:
        self.email = email
        self.save()
        return True

# Generate schema
schema = generate_graphql_schema([User, Order, Product])

# Query example
query = """
query {
    users(age_gte: 18) {
        name
        email
        full_name
    }
}
"""
```

### REST API Integration
```python
# API views
@api_resource
class UserAPI(BaseModel):
    class Meta:
        model = User
        fields = ["id", "name", "email"]
        methods = ["GET", "POST", "PUT", "DELETE"]
        
    @api_action
    def activate(self):
        self.status = "active"
        self.save()
        
    @api_filter
    def active_users(cls, queryset):
        return queryset.filter(status="active")

# Generate OpenAPI spec
spec = generate_openapi_spec([UserAPI, OrderAPI])

# FastAPI integration
app = FastAPI()
app.include_router(create_api_router([UserAPI]))
```

### Elasticsearch Integration
```python
# Search configuration
@searchable
class Product(BaseModel):
    name = StringField(search={"boost": 2.0})
    description = StringField(search={"analyzer": "text"})
    price = FloatField(search={"type": "range"})
    
    class SearchMeta:
        index = "products"
        settings = {
            "number_of_shards": 3,
            "number_of_replicas": 1
        }

# Search operations
results = Product.search().query(
    name__match="laptop",
    price__range=(100, 1000)
).execute()

# Index management
Product.create_search_index()
Product.update_search_mapping()
Product.reindex_all()
```

### Redis Integration
```python
# Cache configuration
@cacheable
class User(BaseModel):
    class CacheMeta:
        backend = "redis"
        ttl = 3600
        prefix = "user"
        
    @cached_property
    def activity_stats(self):
        return calculate_user_stats(self)
        
    @invalidates_cache
    def update_profile(self):
        self.save()

# Cache operations
user = User.get_by_id(1, use_cache=True)
users = User.find(age__gte=18).cache(ttl=300).all()
```

### Kafka Integration
```python
# Event streaming
@streamable
class Order(BaseModel):
    class StreamMeta:
        topic = "orders"
        key_field = "id"
        
    @on_event("created")
    def handle_creation(self):
        self.publish_event("order_created", {
            "order_id": self.id,
            "user_id": self.user_id,
            "total": self.total
        })
        
    @consume_event("payment_completed")
    def handle_payment(self, event):
        self.status = "paid"
        self.save()
```

## Best Practices

1. **API Design**
- Follow REST principles
- Version APIs
- Document endpoints
- Handle errors
- Secure endpoints

2. **Search Integration**
- Plan indexes
- Optimize mappings
- Handle updates
- Monitor performance
- Backup data

3. **Cache Strategy**
- Choose TTL wisely
- Handle invalidation
- Monitor hit rates
- Optimize storage
- Plan capacity

4. **Event Handling**
- Design topics
- Handle failures
- Monitor latency
- Scale consumers
- Backup events

## Future Features

1. **API Features**
- [ ] API versioning
- [ ] Rate limiting
- [ ] Authentication
- [ ] Documentation
- [ ] Client SDKs

2. **Search Features**
- [ ] Faceted search
- [ ] Aggregations
- [ ] Suggestions
- [ ] Highlighting
- [ ] Geosearch

3. **Cache Features**
- [ ] Cache sharding
- [ ] Cache replication
- [ ] Cache analytics
- [ ] Cache warming
- [ ] Cache policies

4. **Event Features**
- [ ] Event replay
- [ ] Event sourcing
- [ ] Event monitoring
- [ ] Event schemas
- [ ] Event routing 