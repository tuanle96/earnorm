# Admin Components

Administration interface for EarnORM.

## Purpose

The admin module provides administration capabilities:
- Model administration
- Data management
- User management
- System monitoring
- Configuration management
- Task scheduling

## Concepts & Examples

### Model Admin
```python
# Model registration
@admin.register
class UserAdmin(ModelAdmin):
    model = User
    list_display = ["username", "email", "status"]
    list_filter = ["status", "role"]
    search_fields = ["username", "email"]
    ordering = ["-created_at"]
    
    def get_queryset(self):
        return super().get_queryset().filter(deleted=False)
        
    @admin.action
    def activate_users(self, request, queryset):
        queryset.update(status="active")
        self.message_user(request, "Users activated successfully")

# Custom views
@admin.view("User Statistics")
class UserStatsView(AdminView):
    template_name = "admin/user_stats.html"
    
    def get_context_data(self):
        return {
            "total_users": User.count(),
            "active_users": User.find(status="active").count(),
            "new_users": User.find(
                created_at__gte=datetime.now() - timedelta(days=7)
            ).count()
        }
```

### Data Management
```python
# Bulk operations
@admin.register
class OrderAdmin(ModelAdmin):
    actions = ["mark_shipped", "generate_invoice"]
    import_export = True
    
    @admin.action
    def mark_shipped(self, request, queryset):
        queryset.update(status="shipped")
        
    def get_export_formats(self):
        return ["csv", "xlsx", "json"]
        
    def get_import_formats(self):
        return ["csv", "xlsx"]

# Custom forms
class UserForm(AdminForm):
    class Meta:
        model = User
        fields = ["username", "email", "role"]
        widgets = {
            "role": Select(choices=ROLE_CHOICES)
        }
```

### System Monitoring
```python
# Dashboard widgets
@admin.widget
class SystemStatus(DashboardWidget):
    template_name = "admin/widgets/system_status.html"
    refresh_interval = 60  # seconds
    
    def get_context_data(self):
        return {
            "cpu_usage": system.get_cpu_usage(),
            "memory_usage": system.get_memory_usage(),
            "disk_usage": system.get_disk_usage(),
            "active_connections": db.get_active_connections()
        }

# Health checks
@admin.health_check
def database_health():
    try:
        db.ping()
        return HealthStatus.OK
    except Exception as e:
        return HealthStatus.ERROR(str(e))
```

### Task Management
```python
# Scheduled tasks
@admin.task
class DataCleanupTask(ScheduledTask):
    schedule = "0 0 * * *"  # Daily at midnight
    
    def run(self):
        # Clean up old data
        deleted = cleanup_old_records()
        self.log_info(f"Cleaned up {deleted} records")

# Task monitoring
@admin.view("Task Monitor")
class TaskMonitorView(AdminView):
    def get_context_data(self):
        return {
            "active_tasks": Task.find(status="running"),
            "failed_tasks": Task.find(status="failed"),
            "scheduled_tasks": Task.find(
                next_run__lte=datetime.now() + timedelta(hours=24)
            )
        }
```

## Best Practices

1. **Interface Design**
- Keep it simple
- Group related actions
- Provide clear feedback
- Support bulk operations
- Add helpful documentation

2. **Data Management**
- Validate imports
- Preview changes
- Backup before bulk ops
- Log all changes
- Handle errors gracefully

3. **Security**
- Restrict access
- Audit actions
- Validate input
- Secure endpoints
- Monitor usage

4. **Performance**
- Optimize queries
- Cache results
- Paginate data
- Handle timeouts
- Monitor resources

## Future Features

1. **Interface Features**
- [ ] Custom themes
- [ ] Mobile support
- [ ] Rich text editor
- [ ] File manager
- [ ] Activity stream

2. **Data Features**
- [ ] Data validation
- [ ] Version control
- [ ] Data recovery
- [ ] Batch processing
- [ ] Data migration

3. **Monitoring Features**
- [ ] Alert system
- [ ] Performance graphs
- [ ] Audit logging
- [ ] Error tracking
- [ ] Usage analytics

4. **Integration**
- [ ] SSO support
- [ ] API access
- [ ] Export tools
- [ ] Backup tools
- [ ] Reporting tools 