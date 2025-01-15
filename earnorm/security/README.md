# Security Components

Security management for EarnORM.

## Overview

The security module provides comprehensive security features:
- Access Control Lists (ACL)
- Record-level Rules
- Permission Management
- Role-based Access Control (RBAC)
- Security Groups
- Audit Logging

## Architecture

### 1. Core Components

```python
# Security Models
class SecurityGroup(BaseModel):
    """Security group definition."""
    _collection = "security_groups"
    _indexes = [
        {"keys": [("code", 1)], "unique": True}
    ]
    
    name: str = StringField(required=True)
    code: str = StringField(required=True, unique=True)
    description: str = StringField(required=False)
    parent_id: Optional[ObjectId] = ObjectIdField(required=False)
    implied_groups: List[str] = ListField(StringField(), default_factory=list)
    active: bool = BooleanField(default=True)
    
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    updated_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    created_by: ObjectId = ObjectIdField(required=True)
    updated_by: ObjectId = ObjectIdField(required=True)

class SecurityRole(BaseModel):
    """Security role definition."""
    _collection = "security_roles"
    _indexes = [
        {"keys": [("code", 1)], "unique": True}
    ]
    
    name: str = StringField(required=True)
    code: str = StringField(required=True, unique=True)
    description: str = StringField(required=False)
    active: bool = BooleanField(default=True)
    
    # Permissions config
    model_permissions: Dict[str, List[str]] = DictField(default_factory=dict)
    field_permissions: Dict[str, Dict[str, List[str]]] = DictField(default_factory=dict)
    method_permissions: Dict[str, List[str]] = DictField(default_factory=dict)
    
    # Custom rules
    rules: Dict[str, Any] = DictField(default_factory=dict)
    
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    updated_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    created_by: ObjectId = ObjectIdField(required=True)
    updated_by: ObjectId = ObjectIdField(required=True)

class AccessControlRule(BaseModel):
    """Dynamic access control rules."""
    _collection = "access_control_rules"
    _indexes = [
        {"keys": [("model", 1), ("operation", 1), ("priority", -1)]}
    ]
    
    name: str = StringField(required=True)
    description: str = StringField(required=False)
    model: str = StringField(required=True)
    operation: str = StringField(required=True)
    groups: List[str] = ListField(StringField(), default_factory=list)
    roles: List[str] = ListField(StringField(), default_factory=list)
    priority: int = IntegerField(default=10)
    active: bool = BooleanField(default=True)
    
    # Dynamic conditions
    conditions: Dict[str, Any] = DictField(default_factory=dict)
    
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    updated_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    created_by: ObjectId = ObjectIdField(required=True)
    updated_by: ObjectId = ObjectIdField(required=True)

class RecordRule(BaseModel):
    """Dynamic record-level rules."""
    _collection = "record_rules"
    _indexes = [
        {"keys": [("model", 1), ("operation", 1), ("priority", -1)]}
    ]
    
    name: str = StringField(required=True)
    description: str = StringField(required=False)
    model: str = StringField(required=True)
    operation: str = StringField(required=True)
    rule_type: str = StringField(required=True)
    
    # Rule definition
    domain: List[Tuple[str, str, Any]] = ListField(
        TupleField(StringField(), StringField(), AnyField()),
        default_factory=list
    )
    python_code: Optional[str] = StringField(required=False)
    
    priority: int = IntegerField(default=10)
    active: bool = BooleanField(default=True)
    
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    updated_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    created_by: ObjectId = ObjectIdField(required=True)
    updated_by: ObjectId = ObjectIdField(required=True)

class UserGroup(BaseModel):
    """User group assignments."""
    _collection = "user_groups"
    _indexes = [
        {"keys": [("user_id", 1), ("group_id", 1)], "unique": True}
    ]
    
    user_id: ObjectId = ObjectIdField(required=True)
    group_id: ObjectId = ObjectIdField(required=True)
    granted_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    granted_by: ObjectId = ObjectIdField(required=True)
    active: bool = BooleanField(default=True)

class UserRole(BaseModel):
    """User role assignments."""
    _collection = "user_roles"
    _indexes = [
        {"keys": [("user_id", 1), ("role_id", 1)], "unique": True}
    ]
    
    user_id: ObjectId = ObjectIdField(required=True)
    role_id: ObjectId = ObjectIdField(required=True)
    granted_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    granted_by: ObjectId = ObjectIdField(required=True)
    active: bool = BooleanField(default=True)
```

### 2. Security Manager

```python
class SecurityManager:
    """Security manager for handling all security operations."""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    async def init(self):
        """Initialize security manager."""
        # Create indexes
        await self._create_indexes()
        # Create default groups and roles
        await self._create_defaults()
        # Create admin user
        await self._create_admin_user()
        
    async def _create_indexes(self):
        """Create indexes for all security collections."""
        collections = [
            SecurityGroup, SecurityRole, AccessControlRule,
            RecordRule, UserGroup, UserRole, User
        ]
        for model in collections:
            collection = await model._get_collection()
            indexes = model.get_indexes()
            if indexes:
                await collection.create_indexes(indexes)
                
    async def _create_defaults(self):
        """Create default security configurations."""
        # Create admin group
        admin_group = await SecurityGroup.create({
            "name": "Administrator",
            "code": "admin",
            "description": "System administrator group",
            "created_by": ObjectId(),  # System
            "updated_by": ObjectId()
        })
        
        # Create admin role
        admin_role = await SecurityRole.create({
            "name": "Administrator",
            "code": "admin",
            "description": "Full system access",
            "model_permissions": {"*": ["create", "read", "write", "delete"]},
            "created_by": ObjectId(),
            "updated_by": ObjectId()
        })
        
    async def _create_admin_user(self):
        """Create default admin user if not exists."""
        # Check if admin exists
        admin = await User.find_one([("email", "=", "admin@earnbase.com")])
        if admin:
            return
            
        # Create admin user
        admin = await User.create({
            "username": "admin",
            "email": "admin@earnbase.com",
            "is_active": True,
            "is_superuser": True,
            "groups": ["admin"],
            "roles": ["admin"],
            "created_by": ObjectId(),
            "updated_by": ObjectId()
        })
        
        # Set password
        await admin.set_password("admin@123")  # Should be changed on first login
        
        # Create group assignment
        admin_group = await SecurityGroup.find_one([("code", "=", "admin")])
        if admin_group:
            await UserGroup.create({
                "user_id": admin.id,
                "group_id": admin_group.id,
                "granted_by": ObjectId()
            })
            
        # Create role assignment
        admin_role = await SecurityRole.find_one([("code", "=", "admin")])
        if admin_role:
            await UserRole.create({
                "user_id": admin.id,
                "role_id": admin_role.id,
                "granted_by": ObjectId()
            })
```

### 3. Security Mixin

```python
class SecurityMixin:
    """Security mixin for BaseModel."""
    
    async def _check_access(self, operation: str) -> bool:
        """Check if current user has access to perform operation."""
        if not security_context.user:
            return False
            
        # Get security manager
        security_manager = self.get_container().get_security_manager()
        
        # Check model access
        return await security_manager.check_access(
            user_id=security_context.user.id,
            model=self._name,
            operation=operation
        )
        
    async def _apply_rules(self, operation: str) -> Dict[str, Any]:
        """Apply record rules for operation."""
        if not security_context.user:
            return {}
            
        # Get security manager
        security_manager = self.get_container().get_security_manager()
        
        # Get rules
        rules = await security_manager.get_record_rules(
            user_id=security_context.user.id,
            model=self._name,
            operation=operation
        )
        
        # Convert rules to query
        return self._domain_to_query(rules)
```

### 4. Secure Base Model

```python
class SecureBaseModel(BaseModel, SecurityMixin):
    """Base model with security features."""
    
    async def save(self) -> None:
        """Save model with security checks."""
        # Determine operation
        operation = "create" if not self.id else "write"
        
        # Check access
        if not await self._check_access(operation):
            raise PermissionError(
                f"Access denied: {operation} not allowed on {self._name}"
            )
            
        # Apply record rules
        rule_conditions = await self._apply_rules("write")
        if rule_conditions and self.id:
            # For existing records, verify they match rules
            collection = await self._get_collection()
            query = {"_id": ObjectId(self.id)}
            query.update(rule_conditions)
            
            if not await collection.find_one(query):
                raise PermissionError(
                    f"Record rules prevent {operation} operation"
                )
                
        # Track changes for audit
        old_values = {}
        if self.id and self._audit.get("write"):
            old_record = await self.browse([self.id])
            if old_record:
                old_values = old_record[0].data
                
        # Perform save
        await super().save()
        
        # Audit log
        if old_values:
            changes = {
                k: v for k, v in self.data.items()
                if k in old_values and old_values[k] != v
            }
            await self._log_audit(operation, changes)
        else:
            await self._log_audit(operation)
            
    @classmethod
    async def search(
        cls,
        domain: Optional[List[Any]] = None,
        **kwargs: Any
    ) -> "RecordSetProtocol[ModelT]":
        """Search with security checks."""
        # Check read access
        if not await cls._check_access("read"):
            raise PermissionError(
                f"Access denied: read not allowed on {cls._name}"
            )
            
        # Apply record rules
        rule_conditions = await cls._apply_rules("read")
        if rule_conditions:
            # Combine with existing domain
            domain = domain or []
            if isinstance(domain, (list, tuple)):
                domain.extend(rule_conditions.items())
            else:
                domain = [("&", domain, rule_conditions)]
                
        # Perform search
        return await super().search(domain, **kwargs)
        
    @classmethod
    async def browse(
        cls,
        ids: List[str]
    ) -> "RecordSetProtocol[ModelT]":
        """Browse with security checks."""
        # Check read access
        if not await cls._check_access("read"):
            raise PermissionError(
                f"Access denied: read not allowed on {cls._name}"
            )
            
        # Apply record rules
        rule_conditions = await cls._apply_rules("read")
        if rule_conditions:
            # Combine with ID filter
            domain = [
                ("&",
                    [("_id", "in", [ObjectId(id) for id in ids])],
                    rule_conditions
                )
            ]
            return await cls.search(domain)
            
        # Perform browse
        return await super().browse(ids)
        
    async def delete(self) -> None:
        """Delete with security checks."""
        # Check delete access
        if not await self._check_access("delete"):
            raise PermissionError(
                f"Access denied: delete not allowed on {self._name}"
            )
            
        # Apply record rules
        rule_conditions = await self._apply_rules("write")
        if rule_conditions:
            # Verify record matches rules
            collection = await self._get_collection()
            query = {"_id": ObjectId(self.id)}
            query.update(rule_conditions)
            
            if not await collection.find_one(query):
                raise PermissionError("Record rules prevent deletion")
                
        # Audit log before delete
        await self._log_audit("delete")
        
        # Perform delete
        await super().delete()
```

## Usage Examples

### 1. Model Definition

```python
class User(SecureBaseModel):
    """User model with security.
    
    This model uses dynamic security configurations from database:
    - ACL rules from AccessControlRule collection
    - Record rules from RecordRule collection
    - Audit logging is handled by AuditLog collection
    """
    _collection = "users"
    
    # Basic fields
    username: str = StringField(
        required=True,
        min_length=3,
        index=True,
        unique=True
    )
    email: str = StringField(
        required=True,
        index=True,
        unique=True
    )
    password: str = StringField(required=True)
    is_active: bool = BooleanField(default=True)
    
    # Metadata
    created_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    updated_at: datetime = DateTimeField(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = DateTimeField(required=False)
    
    async def set_password(self, password: str) -> None:
        """Set hashed password."""
        from passlib.hash import pbkdf2_sha256
        self.password = pbkdf2_sha256.hash(password)
        
    async def verify_password(self, password: str) -> bool:
        """Verify password."""
        from passlib.hash import pbkdf2_sha256
        return pbkdf2_sha256.verify(password, self.password)
        
    async def update_last_login(self) -> None:
        """Update last login time."""
        self.last_login = datetime.utcnow()
        await self.save()
```

### 2. Security Rules Setup

```python
# 1. Create ACL rules
await AccessControlRule.create({
    "name": "User Create",
    "description": "Only admin can create users",
    "model": "users",
    "operation": "create",
    "groups": ["admin"],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

await AccessControlRule.create({
    "name": "User Read",
    "description": "Everyone can read users",
    "model": "users", 
    "operation": "read",
    "groups": ["*"],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

await AccessControlRule.create({
    "name": "User Write",
    "description": "Admin and user can write",
    "model": "users",
    "operation": "write", 
    "groups": ["admin", "user"],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

await AccessControlRule.create({
    "name": "User Delete",
    "description": "Only admin can delete users",
    "model": "users",
    "operation": "delete",
    "groups": ["admin"],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

# 2. Create Record rules
await RecordRule.create({
    "name": "Active Users Only",
    "description": "Users can only read active records",
    "model": "users",
    "operation": "read",
    "rule_type": "domain",
    "domain": [("is_active", "=", True)],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

await RecordRule.create({
    "name": "Same Group Users",
    "description": "Users can only read records in their groups",
    "model": "users", 
    "operation": "read",
    "rule_type": "domain",
    "domain": [("groups", "overlap", "user.groups")],
    "priority": 20,
    "created_by": admin_id,
    "updated_by": admin_id
})

await RecordRule.create({
    "name": "Own Record Only",
    "description": "Users can only edit their own record",
    "model": "users",
    "operation": "write",
    "rule_type": "domain", 
    "domain": [("id", "=", "user.id")],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})
```

### 3. CRUD Operations

```python
# Create - requires admin access based on ACL rule
user = await User.create({
    "username": "test",
    "email": "test@example.com",
    "password": "secret123"
})

# Read - filtered by record rules automatically
users = await User.search([
    ("email", "like", "%@example.com")
])
# Final query will include:
# - is_active = True (from Active Users Only rule)
# - groups overlap with current user's groups (from Same Group Users rule)

# Update - checks write access and rules
user.email = "new@example.com"
await user.save()
# Will only succeed if:
# - Current user has admin/user group (from ACL rule)
# - Current user owns the record (from Own Record Only rule)

# Delete - requires admin access based on ACL rule
await user.delete()
```

### 4. Security Groups

```python
# Create group
sales_group = await SecurityGroup.create({
    "name": "Sales Team",
    "code": "sales",
    "description": "Sales department users",
    "created_by": admin_id,
    "updated_by": admin_id
})

# Create ACL rules for sales group
await AccessControlRule.create({
    "name": "Sales Product Access",
    "description": "Sales team product permissions",
    "model": "products",
    "operation": "read",
    "groups": ["sales"],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

# Assign user to group
await UserGroup.create({
    "user_id": user.id,
    "group_id": sales_group.id,
    "granted_by": admin_id
})
```

### 5. Security Roles

```python
# Create role
sales_role = await SecurityRole.create({
    "name": "Sales Manager",
    "code": "sales_manager",
    "description": "Sales team manager role",
    "model_permissions": {
        "products": ["read", "write"],
        "orders": ["read", "write", "approve"],
        "customers": ["read", "write"]
    },
    "created_by": admin_id,
    "updated_by": admin_id
})

# Create ACL rules for sales manager role
await AccessControlRule.create({
    "name": "Sales Manager Order Approval",
    "description": "Sales managers can approve orders",
    "model": "orders",
    "operation": "approve",
    "roles": ["sales_manager"],
    "conditions": {
        "total": {"$lte": 10000}  # Can only approve orders up to $10,000
    },
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

# Assign role to user
await UserRole.create({
    "user_id": user.id,
    "role_id": sales_role.id,
    "granted_by": admin_id
})
```

### 6. Complex Rules Example

```python
# Multi-condition rule
await RecordRule.create({
    "name": "Regional Sales Access",
    "description": "Sales team can only access their region's data",
    "model": "orders",
    "operation": "read",
    "rule_type": "domain",
    "domain": [
        "&",
        ("region_id", "=", "user.region_id"),
        "|",
        ("status", "=", "approved"),
        ("created_by", "=", "user.id")
    ],
    "priority": 10,
    "created_by": admin_id,
    "updated_by": admin_id
})

# Python code rule
await RecordRule.create({
    "name": "Complex Order Access",
    "description": "Complex order access logic",
    "model": "orders",
    "operation": "write",
    "rule_type": "python",
    "python_code": """
async def check_access(user, order):
    # Check order status
    if order.status == 'completed':
        return False
        
    # Check user role
    if 'sales_manager' in user.roles:
        return True
        
    # Check order amount
    if order.total > 1000 and 'sales' in user.groups:
        return False
        
    # Check customer assignment
    customer = await order.get_customer()
    return customer.assigned_to == user.id
    """,
    "priority": 20,
    "created_by": admin_id,
    "updated_by": admin_id
})
```

## Best Practices

### 1. Security

1. **Access Control**:
- Define clear security groups
- Use principle of least privilege
- Implement role-based access
- Document permissions
- Audit access regularly

2. **Record Rules**:
- Keep rules simple and focused
- Cache rule results
- Handle edge cases
- Test thoroughly
- Monitor performance

3. **Security Groups**:
- Use hierarchical structure
- Define clear categories
- Document implications
- Review regularly
- Handle inheritance

4. **Audit Logging**:
- Log security events
- Track important changes
- Store sufficient context
- Implement retention
- Monitor suspicious activity

### 2. Performance

1. **Caching**:
- Cache strategy phù hợp
- Cache invalidation
- Cache consistency

2. **Database**:
- Index optimization
- Query optimization
- Batch operations

3. **Security Checks**:
- Cache ACL results
- Optimize rule evaluation
- Batch permission checks

### 3. Development

1. **Code Organization**:
- Clear separation of concerns
- Consistent naming
- Proper documentation
- Error handling
- Type safety

2. **Testing**:
- Unit tests
- Integration tests
- Security tests
- Performance tests
- Edge cases

3. **Monitoring**:
- Performance metrics
- Error tracking
- Security events
- Usage analytics
- Audit trails

## Implementation Guide

### 1. Setup

1. **Database**:
- Create collections
- Setup indexes
- Initial data

2. **Security Manager**:
- Initialize manager
- Create defaults
- Setup caching

3. **Models**:
- Define secure models
- Configure ACL
- Set record rules

### 2. Integration

1. **Application**:
- Add middleware
- Configure security
- Setup logging

2. **Authentication**:
- User authentication
- Session management
- Token handling

3. **Authorization**:
- Permission checks
- Rule evaluation
- Access control

### 3. Maintenance

1. **Monitoring**:
- Setup logging
- Configure alerts
- Track metrics

2. **Updates**:
- Security patches
- Feature updates
- Bug fixes

3. **Backup**:
- Regular backups
- Data retention
- Recovery testing

## Future Features

1. **Access Control**:
- Dynamic permissions
- Permission inheritance
- Custom rule engine
- Policy management
- Access analytics

2. **Record Rules**:
- Rule templates
- Rule versioning
- Rule dependencies
- Rule testing tools
- Performance profiling

3. **Security Groups**:
- Group templates
- Dynamic membership
- Group analytics
- Policy enforcement
- Compliance tools

4. **Audit Features**:
- Audit dashboards
- Alert system
- Compliance reporting
- Data retention
- Analytics tools 
