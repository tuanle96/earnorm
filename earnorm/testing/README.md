# Testing Components

Testing tools and utilities for EarnORM.

## Purpose

The testing module provides comprehensive testing capabilities:
- Test fixtures
- Model factories
- Mock database
- Assertions
- Performance testing
- Integration testing

## Concepts & Examples

### Test Fixtures
```python
# Database fixtures
@fixture
def test_db():
    db = TestDatabase()
    yield db
    db.cleanup()

# Collection fixtures
@fixture
def users_collection(test_db):
    collection = test_db.get_collection("users")
    yield collection
    collection.drop()

# Model fixtures
@fixture
def test_user(users_collection):
    user = User(name="Test User", email="test@example.com")
    user.save()
    yield user
    user.delete()
```

### Model Factories
```python
# Basic factory
class UserFactory(ModelFactory):
    name = faker.name()
    email = faker.email()
    age = faker.random_int(min=18, max=80)
    
    class Meta:
        model = User

# Factory with traits
class OrderFactory(ModelFactory):
    user = SubFactory(UserFactory)
    total = faker.decimal(2)
    status = "pending"
    
    class Params:
        completed = Trait(
            status="completed",
            completed_at=faker.date_time()
        )
        
        cancelled = Trait(
            status="cancelled",
            cancelled_at=faker.date_time()
        )

# Create instances
user = UserFactory.create()
orders = OrderFactory.create_batch(size=10)
completed_order = OrderFactory(completed=True)
```

### Mock Database
```python
# Mock database
class MockDatabase(TestDatabase):
    def setup(self):
        self.users = MockCollection("users")
        self.orders = MockCollection("orders")
    
    def teardown(self):
        self.users.clear()
        self.orders.clear()

# Mock queries
with mock_query() as mock:
    mock.expect(User.find(age__gte=18)).return_value([user1, user2])
    mock.expect(Order.find(user=user1)).return_value([order1])
    
    results = User.find(age__gte=18).all()
    assert len(results) == 2
```

### Assertions
```python
# Model assertions
def test_user_creation():
    user = UserFactory.create()
    assert user.exists()
    assert user.is_valid()
    assert user.has_index("email")
    assert user.matches({"name": str, "email": str})

# Query assertions
def test_user_query():
    users = UserFactory.create_batch(5)
    query = User.find(age__gte=18)
    
    assert query.has_filter("age")
    assert query.uses_index("age_1")
    assert query.count() == 5
    assert query.explain().is_optimized()

# Performance assertions
def test_query_performance():
    with query_profiler() as profiler:
        users = User.find().all()
        
    assert profiler.duration < 100  # ms
    assert profiler.docs_scanned < 1000
    assert profiler.is_optimized()
```

## Best Practices

1. **Test Organization**
- Group related tests
- Use descriptive names
- Share common fixtures
- Clean up resources
- Document test cases

2. **Factory Design**
- Keep factories focused
- Use realistic data
- Handle relationships
- Support customization
- Test factory output

3. **Mock Usage**
- Mock external services
- Verify interactions
- Handle edge cases
- Clean up mocks
- Document behavior

4. **Performance Testing**
- Define benchmarks
- Test with real data
- Monitor resources
- Compare results
- Document findings

## Future Features

1. **Testing Tools**
- [ ] Test generators
- [ ] Scenario testing
- [ ] Load testing
- [ ] Fuzzy testing
- [ ] Coverage tools

2. **Factory Features**
- [ ] Advanced traits
- [ ] Sequence support
- [ ] Lazy attributes
- [ ] Association rules
- [ ] Factory states

3. **Mock Features**
- [ ] Smart mocking
- [ ] Record/Replay
- [ ] Mock storage
- [ ] Mock validation
- [ ] Mock metrics

4. **Integration**
- [ ] CI/CD integration
- [ ] Test reporters
- [ ] Coverage reports
- [ ] Performance reports
- [ ] Documentation tools 