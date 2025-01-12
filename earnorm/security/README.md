# Security Components

Security management for EarnORM.

## Purpose

The security module provides comprehensive access control:
- Access Control Lists (ACL)
- Record-level Rules
- Permission Management
- Role-based Access Control
- Security Groups
- Audit Logging

## Concepts & Examples

### Access Control Lists (ACL)
```python
from earnorm.security import acl, groups

# Define security groups
@groups.define
class UserGroups:
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

# Define model with ACL
class Product(BaseModel):
    _collection = "products"
    _acl = {
        "create": ["admin", "manager"],
        "read": ["admin", "manager", "user"],
        "write": ["admin", "manager"],
        "delete": ["admin"]
    }
    
    name: str
    price: float
    
    # Method-level ACL
    @acl.requires(["admin", "manager"])
    async def update_price(self, new_price: float):
        self.price = new_price
        await self.save()

# Using ACL checks
async def handle_product(user, product_id):
    if not acl.can_access(user, "products", "write"):
        raise PermissionError("No write access")
        
    product = await Product.find_one(id=product_id)
    await product.update_price(99.99)
```

### Record Rules
```python
from earnorm.security import rules

# Define record rules
class OrderRules(rules.RecordRules):
    _collection = "orders"
    
    @rules.read
    def read_own_orders(self, user):
        if user.has_group("admin"):
            return {}  # No restrictions for admin
        return {"user_id": user.id}  # Users can only read their own orders
    
    @rules.write
    def write_own_orders(self, user):
        if user.has_group("manager"):
            return {"status": {"$ne": "completed"}}  # Managers can edit non-completed orders
        return {
            "user_id": user.id,
            "status": {"$in": ["draft", "pending"]}
        }  # Users can only edit their draft/pending orders

# Using record rules
class Order(BaseModel):
    _collection = "orders"
    _rules = OrderRules
    
    user_id: ObjectId
    status: str
    total: float
    
    async def process(self):
        # Rules are automatically applied
        await self.update({"status": "processing"})
```

### Role-based Access Control
```python
from earnorm.security import rbac

# Define roles and permissions
@rbac.role("sales_manager")
class SalesManager:
    permissions = {
        "products": ["read", "write"],
        "orders": ["read", "write", "approve"],
        "customers": ["read", "write"]
    }
    
    def can_approve_order(self, order):
        return order.total <= 10000

# Apply roles to users
class User(BaseModel):
    _collection = "users"
    
    name: str
    email: str
    roles: List[str] = []
    
    def has_permission(self, collection: str, operation: str) -> bool:
        return rbac.check_permission(self.roles, collection, operation)
    
    async def can_approve(self, order) -> bool:
        return await rbac.check_custom_rule(self.roles, "can_approve_order", order)
```

### Security Groups
```python
from earnorm.security import groups

# Define security groups
@groups.group
class SalesGroup:
    name = "sales"
    parent = "employee"
    
    implied_groups = ["base.group_user"]
    category = "Sales Management"
    
    permissions = {
        "products": ["read"],
        "orders": ["read", "write"],
        "customers": ["read"]
    }

# Check group membership
class User(BaseModel):
    _collection = "users"
    
    groups: List[str] = []
    
    def has_group(self, group: str) -> bool:
        return groups.check_membership(self.groups, group)
```

### Audit Logging
```python
from earnorm.security import audit

# Enable audit logging
class Order(BaseModel):
    _collection = "orders"
    _audit = {
        "create": True,
        "write": ["status", "total"],  # Track changes to specific fields
        "delete": True
    }
    
    # Custom audit log
    @audit.log("approve")
    async def approve(self, user):
        self.status = "approved"
        self.approved_by = user.id
        self.approved_at = datetime.utcnow()
        await self.save()

# Query audit logs
async def get_order_history(order_id):
    logs = await audit.get_logs("orders", order_id)
    return [
        {
            "action": log.action,
            "user": log.user_id,
            "timestamp": log.timestamp,
            "changes": log.changes
        }
        for log in logs
    ]
```

## Best Practices

1. **Access Control**
- Define clear security groups
- Use principle of least privilege
- Implement role-based access
- Document permissions
- Audit access regularly

2. **Record Rules**
- Keep rules simple and focused
- Cache rule results
- Handle edge cases
- Test thoroughly
- Monitor performance

3. **Security Groups**
- Use hierarchical structure
- Define clear categories
- Document implications
- Review regularly
- Handle inheritance

4. **Audit Logging**
- Log security events
- Track important changes
- Store sufficient context
- Implement retention
- Monitor suspicious activity

5. **Performance**
- Cache ACL checks
- Optimize rule evaluation
- Index security fields
- Batch permission checks
- Monitor overhead

## Future Features

1. **Access Control**
- [ ] Dynamic permissions
- [ ] Permission inheritance
- [ ] Custom rule engine
- [ ] Policy management
- [ ] Access analytics

2. **Record Rules**
- [ ] Rule templates
- [ ] Rule versioning
- [ ] Rule dependencies
- [ ] Rule testing tools
- [ ] Performance profiling

3. **Security Groups**
- [ ] Group templates
- [ ] Dynamic membership
- [ ] Group analytics
- [ ] Policy enforcement
- [ ] Compliance tools

4. **Audit Features**
- [ ] Audit dashboards
- [ ] Alert system
- [ ] Compliance reports
- [ ] Log analysis
- [ ] Retention policies

5. **Integration**
- [ ] SSO support
- [ ] OAuth integration
- [ ] LDAP support
- [ ] 2FA support
- [ ] API security 