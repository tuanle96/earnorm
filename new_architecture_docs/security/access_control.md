# Access Control trong Odoo

## 1. Tổng quan

Odoo sử dụng hai cơ chế chính để quản lý quyền truy cập:

1. **Access Rights**: Kiểm soát quyền CRUD (Create/Read/Update/Delete) trên model level
2. **Record Rules**: Kiểm soát quyền truy cập ở record level (row-level security)

## 2. Access Rights (ir.model.access)

### 2.1 Định nghĩa

```xml
<record id="access_hr_employee_user" model="ir.model.access">
    <field name="name">hr.employee.user</field>
    <field name="model_id" ref="model_hr_employee"/>
    <field name="group_id" ref="base.group_user"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_write" eval="0"/>
    <field name="perm_create" eval="0"/>
    <field name="perm_unlink" eval="0"/>
</record>
```

### 2.2 Các thành phần chính

- **name**: Tên định danh của quyền
- **model_id**: Model được áp dụng quyền
- **group_id**: Security group được áp dụng
- **perm_read/write/create/unlink**: Các quyền CRUD

### 2.3 Cách hoạt động

```python
def check_access_rights(self, operation, raise_exception=True):
    """
    Kiểm tra quyền truy cập trên model level
    - operation: 'read', 'write', 'create', 'unlink'
    """
    if self.env.su:
        # Super user có tất cả quyền
        return True
        
    # Kiểm tra quyền từ ir.model.access
    access_rights = self.env['ir.model.access'].get_access(self._name)
    return access_rights.get(operation, False)
```

## 3. Record Rules (ir.rule)

### 3.1 Định nghĩa

```xml
<record id="hr_employee_rule_employee" model="ir.rule">
    <field name="name">Employee: read own records only</field>
    <field name="model_id" ref="model_hr_employee"/>
    <field name="domain_force">[('user_id','=',user.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="perm_read" eval="1"/>
    <field name="perm_write" eval="0"/>
    <field name="perm_create" eval="0"/>
    <field name="perm_unlink" eval="0"/>
</record>
```

### 3.2 Các thành phần chính

- **name**: Tên định danh của rule
- **model_id**: Model được áp dụng rule
- **domain_force**: Domain filter để xác định records được phép truy cập
- **groups**: Security groups được áp dụng rule
- **perm_read/write/create/unlink**: Các operation được áp dụng rule

### 3.3 Cách hoạt động

```python
def check_access_rule(self, operation):
    """
    Kiểm tra quyền truy cập trên record level
    - operation: 'read', 'write', 'create', 'unlink'
    """
    if self.env.su:
        return
        
    # Lấy tất cả rules áp dụng cho model và operation
    rules = self.env['ir.rule'].get_rules(self._name, operation)
    
    if not rules:
        return
        
    # Kết hợp domain từ tất cả rules
    domain = OR([rule.domain for rule in rules])
    
    # Kiểm tra records có match với domain
    if not self.filtered_domain(domain):
        raise AccessError(...)
```

## 4. Best Practices

### 4.1 Access Rights

1. Định nghĩa quyền mặc định trong file `security/ir.model.access.csv`
2. Sử dụng groups để phân quyền thay vì gán trực tiếp cho users
3. Tuân thủ principle of least privilege

### 4.2 Record Rules

1. Sử dụng domain expressions đơn giản và được index
2. Tránh phức tạp hóa logic trong domain
3. Cân nhắc performance impact với large datasets

## 5. Common Issues & Solutions

### 5.1 Performance Issues

1. **Vấn đề**: Record rules phức tạp ảnh hưởng đến query performance
   **Giải pháp**: 
   - Optimize domain expressions
   - Sử dụng index cho các fields trong domain
   - Cache kết quả nếu có thể

2. **Vấn đề**: Access check overhead với nhiều rules
   **Giải pháp**:
   - Combine rules khi có thể
   - Sử dụng sudo() có chọn lọc
   - Cache access results

### 5.2 Security Issues

1. **Vấn đề**: Unintended access through related fields
   **Giải pháp**:
   - Kiểm tra access rights trên related models
   - Sử dụng computed fields thay vì related khi cần

2. **Vấn đề**: Inconsistent rules across operations
   **Giải pháp**:
   - Review và test rules cho tất cả operations
   - Maintain documentation cho security rules
``` 