# Relationships Module

## Overview
The Relationships module provides tools for defining and managing relationships between models in EarnORM. It supports various types of relationships including one-to-one, one-to-many, and many-to-many.

## Components

### 1. Relationship Manager
The core class for managing relationships:

```python
class RelationshipManager:
    """Manager for handling model relationships.
    
    Examples:
        >>> class User(Model):
        ...     posts = RelationshipManager("Post", "author_id")
        ...     comments = RelationshipManager("Comment", "user_id")
        
        >>> user = await User.get(user_id)
        >>> user_posts = await user.posts.all()
    """
    
    def __init__(self, target_model: str, foreign_key: str):
        self.target_model = target_model
        self.foreign_key = foreign_key
        
    async def all(self) -> List[Model]:
        """Get all related records."""
        return await self.target_model.find({
            self.foreign_key: self.instance.id
        })
```

### 2. Relationship Types
Supported relationship types:

```python
class OneToOne(RelationshipManager):
    """One-to-one relationship.
    
    Examples:
        >>> class User(Model):
        ...     profile = OneToOne("Profile", "user_id")
        
        >>> user = await User.get(user_id)
        >>> profile = await user.profile.get()
    """
    
    async def get(self) -> Optional[Model]:
        """Get the related record."""
        return await self.target_model.find_one({
            self.foreign_key: self.instance.id
        })

class OneToMany(RelationshipManager):
    """One-to-many relationship.
    
    Examples:
        >>> class User(Model):
        ...     posts = OneToMany("Post", "author_id")
        
        >>> user = await User.get(user_id)
        >>> posts = await user.posts.all()
    """
    
    async def add(self, record: Model) -> None:
        """Add a related record."""
        record[self.foreign_key] = self.instance.id
        await record.save()
```

### 3. Relationship Configuration
Configuration for relationships:

```python
class RelationshipConfig:
    """Configuration for relationships.
    
    Examples:
        >>> config = RelationshipConfig(
        ...     cascade_delete=True,
        ...     lazy_load=True,
        ...     back_populates="user"
        ... )
    """
    
    def __init__(
        self,
        cascade_delete: bool = False,
        lazy_load: bool = True,
        back_populates: Optional[str] = None
    ):
        self.cascade_delete = cascade_delete
        self.lazy_load = lazy_load
        self.back_populates = back_populates
```

## Usage Examples

### 1. Basic Relationships
```python
class User(Model):
    # One-to-one relationship
    profile = OneToOne("Profile", "user_id")
    
    # One-to-many relationship
    posts = OneToMany("Post", "author_id")
    
    # Many-to-many relationship
    groups = ManyToMany("Group", "UserGroup")

# Using relationships
user = await User.get(user_id)
profile = await user.profile.get()
posts = await user.posts.all()
groups = await user.groups.all()
```

### 2. Relationship Configuration
```python
class User(Model):
    # Cascade delete profile when user is deleted
    profile = OneToOne(
        "Profile",
        "user_id",
        config=RelationshipConfig(cascade_delete=True)
    )
    
    # Lazy load posts
    posts = OneToMany(
        "Post",
        "author_id",
        config=RelationshipConfig(lazy_load=True)
    )
    
    # Bidirectional relationship
    comments = OneToMany(
        "Comment",
        "user_id",
        config=RelationshipConfig(back_populates="author")
    )
```

### 3. Advanced Usage
```python
class Post(Model):
    # Filtered relationship
    active_comments = OneToMany(
        "Comment",
        "post_id",
        filter={"status": "active"}
    )
    
    # Ordered relationship
    recent_comments = OneToMany(
        "Comment",
        "post_id",
        order_by=[("created_at", -1)]
    )
    
    # Limited relationship
    top_comments = OneToMany(
        "Comment",
        "post_id",
        limit=10,
        order_by=[("likes", -1)]
    )
```

## Best Practices

1. **Relationship Design**
- Choose appropriate relationship types
- Configure cascade delete when needed
- Use lazy loading for large collections
- Use meaningful relationship names

2. **Performance**
- Use indexes for foreign keys
- Avoid N+1 query problem
- Batch load related records
- Optimize query filters

3. **Data Integrity**
- Validate foreign keys
- Handle orphaned records
- Implement referential integrity
- Clean up related records

4. **Code Organization**
- Group related models
- Use consistent naming
- Document relationships
- Test relationship behavior

## Common Issues & Solutions

1. **N+1 Query Problem**
```python
class OptimizedManager(RelationshipManager):
    """Manager with batch loading."""
    
    async def batch_load(self, instances: List[Model]) -> Dict[str, List[Model]]:
        ids = [instance.id for instance in instances]
        records = await self.target_model.find({
            self.foreign_key: {"$in": ids}
        })
        
        # Group by foreign key
        result = defaultdict(list)
        for record in records:
            result[record[self.foreign_key]].append(record)
        return result
```

2. **Circular Dependencies**
```python
class LazyRelationship(RelationshipManager):
    """Lazy loading relationship to avoid circular imports."""
    
    def __init__(self, target_model_name: str, foreign_key: str):
        self.target_model_name = target_model_name
        self.foreign_key = foreign_key
        self._target_model = None
        
    @property
    def target_model(self) -> Type[Model]:
        if self._target_model is None:
            self._target_model = self._load_model()
        return self._target_model
```

3. **Cascade Operations**
```python
class CascadeManager(RelationshipManager):
    """Manager with cascade operations."""
    
    async def cascade_delete(self) -> None:
        """Delete all related records."""
        await self.target_model.delete_many({
            self.foreign_key: self.instance.id
        })
        
    async def cascade_update(self, update: Dict[str, Any]) -> None:
        """Update all related records."""
        await self.target_model.update_many(
            {self.foreign_key: self.instance.id},
            {"$set": update}
        )
```

## Implementation Details

### 1. Relationship Metadata
```python
class RelationshipMetadata:
    """Metadata for relationship configuration."""
    
    def __init__(
        self,
        name: str,
        target: str,
        type: str,
        foreign_key: str,
        config: RelationshipConfig
    ):
        self.name = name
        self.target = target
        self.type = type
        self.foreign_key = foreign_key
        self.config = config
```

### 2. Query Building
```python
class RelationshipQuery:
    """Query builder for relationships."""
    
    def build_query(self) -> Dict[str, Any]:
        """Build MongoDB query for relationship."""
        query = {self.foreign_key: self.instance.id}
        
        if self.filter:
            query.update(self.filter)
            
        return query
        
    def build_options(self) -> Dict[str, Any]:
        """Build query options."""
        options = {}
        
        if self.order_by:
            options["sort"] = self.order_by
            
        if self.limit:
            options["limit"] = self.limit
            
        return options
```

## Contributing

1. Follow code style guidelines
2. Add comprehensive tests
3. Document new features
4. Update type hints
5. Benchmark performance impacts
