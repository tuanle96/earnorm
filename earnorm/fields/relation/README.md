# Relation Fields

This module provides relation field types for the EarnORM framework.

## Overview

The relation fields module includes relationship types:

1. One-to-One Relations (`one2one.py`)
2. One-to-Many Relations (`one2many.py`)
3. Many-to-Many Relations (`many2many.py`)

## Field Types

### One-to-One Relations
```python
from earnorm.fields.relation import One2OneField

class User(BaseModel):
    # One-to-one relation
    profile = One2OneField("Profile")

class Profile(BaseModel):
    # Inverse relation
    user = One2OneField("User", inverse="profile")
```

### One-to-Many Relations
```python
from earnorm.fields.relation import One2ManyField, One2OneField

class User(BaseModel):
    # One-to-many relation
    posts = One2ManyField("Post")

class Post(BaseModel):
    # Many-to-one relation
    author = One2OneField("User", inverse="posts")
```

### Many-to-Many Relations
```python
from earnorm.fields.relation import Many2ManyField

class Post(BaseModel):
    # Many-to-many relation
    tags = Many2ManyField("Tag")

class Tag(BaseModel):
    # Inverse relation
    posts = Many2ManyField("Post", inverse="tags")
```

## Features

1. One-to-One Relations
   - Unique constraints
   - Cascade options
   - Inverse relations
   - Lazy loading
   - Validation

2. One-to-Many Relations
   - Collection management
   - Ordering options
   - Filtering options
   - Cascade deletion
   - Batch operations

3. Many-to-Many Relations
   - Junction tables
   - Extra fields
   - Ordering
   - Filtering
   - Pagination

## Implementation Guide

### 1. One-to-One Relations

1. Basic usage:
```python
class User(BaseModel):
    profile = One2OneField("Profile")

class Profile(BaseModel):
    user = One2OneField("User", inverse="profile")
```

2. Options:
```python
# Required relation
profile = One2OneField("Profile", required=True)

# Cascade deletion
profile = One2OneField("Profile", ondelete="cascade")

# Lazy loading
profile = One2OneField("Profile", lazy=True)
```

### 2. One-to-Many Relations

1. Basic usage:
```python
class User(BaseModel):
    posts = One2ManyField("Post")

class Post(BaseModel):
    author = One2OneField("User", inverse="posts")
```

2. Options:
```python
# Ordering
posts = One2ManyField("Post", order="created_at desc")

# Filtering
posts = One2ManyField("Post", domain=[("status", "=", "published")])

# Cascade
posts = One2ManyField("Post", ondelete="cascade")
```

### 3. Many-to-Many Relations

1. Basic usage:
```python
class Post(BaseModel):
    tags = Many2ManyField("Tag")

class Tag(BaseModel):
    posts = Many2ManyField("Post", inverse="tags")
```

2. Options:
```python
# Custom junction table
tags = Many2ManyField("Tag", relation="post_tags")

# Extra fields
tags = Many2ManyField("Tag", extra_fields={
    "added_at": DateTimeField(auto_now_add=True)
})

# Ordering
tags = Many2ManyField("Tag", order="name")
```

3. Operations:
```python
# Add relations
await post.tags.add(tag1, tag2)

# Remove relations
await post.tags.remove(tag1)

# Clear relations
await post.tags.clear()

# Replace relations
await post.tags.replace([tag1, tag2])
```

## Best Practices

1. One-to-One Relations
   - Define both sides
   - Set cascade options
   - Handle null values
   - Consider performance
   - Use lazy loading

2. One-to-Many Relations
   - Set proper ordering
   - Use filtering wisely
   - Handle deletions
   - Manage collections
   - Consider batching

3. Many-to-Many Relations
   - Name junction tables
   - Add extra fields
   - Handle ordering
   - Manage relations
   - Use pagination

## Advanced Features

### 1. Relation Loading
```python
# Eager loading
users = await User.search([]).load("profile", "posts")

# Nested loading
users = await User.search([]).load({
    "posts": {
        "comments": ["author"]
    }
})
```

### 2. Relation Filtering
```python
# Filter by relation
users = await User.search([
    ("posts.status", "=", "published")
])

# Complex filtering
posts = await Post.search([
    ("tags.category", "=", "tech"),
    ("author.is_active", "=", True)
])
```

### 3. Relation Updates
```python
# Update related records
await user.posts.write({
    "status": "archived"
})

# Update through relation
await Post.search([
    ("author.id", "=", user.id)
]).write({
    "status": "archived"
})
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
