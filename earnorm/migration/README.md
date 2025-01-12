# Migration Components

Migration system components for EarnORM.

## Purpose

The migration module provides schema and data migration capabilities:
- Schema migrations
- Data migrations
- Migration versioning
- Rollback support
- Migration history
- Migration dependencies

## Concepts & Examples

### Schema Migrations
```python
# Define migration
class AddUserEmailMigration(Migration):
    version = "20240320_01"
    description = "Add email field to User model"
    
    def upgrade(self):
        self.add_field("User", "email", EmailField(required=True))
        self.create_index("User", [("email", 1)], unique=True)
    
    def downgrade(self):
        self.drop_index("User", "email_1")
        self.remove_field("User", "email")

# Run migrations
migrate = MigrationManager()
migrate.upgrade()  # Run all pending migrations
migrate.upgrade("20240320_01")  # Run specific migration
migrate.downgrade("20240315_01")  # Rollback to specific version
```

### Data Migrations
```python
class UpdateUserNamesMigration(Migration):
    version = "20240320_02"
    description = "Update user names to title case"
    
    def upgrade(self):
        users = self.db.users.find({})
        for user in users:
            self.db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {"name": user["name"].title()}}
            )
    
    def downgrade(self):
        # Data migration downgrade not supported
        pass

class SplitNameFieldMigration(Migration):
    version = "20240320_03"
    description = "Split name into first_name and last_name"
    
    def upgrade(self):
        self.add_field("User", "first_name", StringField())
        self.add_field("User", "last_name", StringField())
        
        users = self.db.users.find({})
        for user in users:
            names = user["name"].split(" ", 1)
            self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "first_name": names[0],
                        "last_name": names[1] if len(names) > 1 else ""
                    }
                }
            )
        
        self.remove_field("User", "name")
```

### Migration Dependencies
```python
class AddUserProfileMigration(Migration):
    version = "20240320_04"
    description = "Add user profile model"
    depends_on = ["20240320_01"]  # Depends on email field
    
    def upgrade(self):
        self.create_collection("Profile")
        self.add_field("Profile", "user", ReferenceField("User"))
        self.add_field("Profile", "bio", StringField())
        self.create_index("Profile", [("user", 1)], unique=True)
    
    def downgrade(self):
        self.drop_collection("Profile")
```

## Best Practices

1. **Migration Design**
- Keep migrations atomic
- Handle dependencies
- Test migrations
- Document changes
- Support rollback

2. **Data Safety**
- Backup before migrating
- Validate data integrity
- Handle errors gracefully
- Log all changes
- Test with real data

3. **Performance**
- Optimize large migrations
- Use batch operations
- Handle timeouts
- Monitor progress
- Consider downtime

4. **Maintenance**
- Track migration history
- Clean up old migrations
- Monitor migration status
- Document procedures
- Plan maintenance windows

## Future Features

1. **Migration Types**
- [ ] Online migrations
- [ ] Partial migrations
- [ ] Async migrations
- [ ] Distributed migrations
- [ ] Custom migrations

2. **Migration Tools**
- [ ] Migration generator
- [ ] Migration viewer
- [ ] Migration validator
- [ ] Migration scheduler
- [ ] Migration reporter

3. **Safety Features**
- [ ] Dry run mode
- [ ] Automatic backups
- [ ] Data validation
- [ ] Progress tracking
- [ ] Error recovery

4. **Integration**
- [ ] CI/CD integration
- [ ] Monitoring tools
- [ ] Backup systems
- [ ] Version control
- [ ] Deployment tools 