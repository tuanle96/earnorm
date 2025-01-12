# CLI Components

Command Line Interface tools for EarnORM.

## Purpose

The CLI module provides development and management tools:
- Code generation
- Schema management
- Development server
- Database operations
- Monitoring tools
- Documentation tools

## Concepts & Examples

### Code Generation
```bash
# Generate models
earnorm generate model User --fields "name:str email:str age:int"
earnorm generate model Order --fields "user:ref:User total:float status:str"

# Generate migrations
earnorm generate migration AddUserEmail
earnorm generate migration UpdateOrderStatus

# Generate indexes
earnorm generate index UserEmailIndex --fields "email:1" --unique
earnorm generate index OrderUserIndex --fields "user:1 created_at:-1"
```

### Schema Management
```bash
# Apply migrations
earnorm migrate up
earnorm migrate down
earnorm migrate reset

# Manage indexes
earnorm index create
earnorm index list
earnorm index analyze
```

### Development Server
```bash
# Run development server
earnorm runserver --host localhost --port 8000 --debug

# Run interactive shell
earnorm shell --ipython
earnorm shell --bpython
```

### Database Operations
```bash
# Database management
earnorm db create
earnorm db drop
earnorm db seed

# Collection operations
earnorm collection list
earnorm collection clear users
earnorm collection stats orders
```

### Monitoring Tools
```bash
# Start monitoring
earnorm monitor --port 8080

# View statistics
earnorm stats queries
earnorm stats performance
earnorm stats resources
```

### Documentation Tools
```bash
# Generate documentation
earnorm docs generate --format openapi
earnorm docs generate --format markdown

# Serve documentation
earnorm docs serve --port 8000
```

## Commands

1. **Model Commands**
- `generate model`: Generate new model
- `list models`: List all models
- `show model`: Show model details
- `validate model`: Validate model schema

2. **Migration Commands**
- `generate migration`: Create new migration
- `migrate up`: Apply migrations
- `migrate down`: Rollback migrations
- `migrate status`: Show migration status

3. **Index Commands**
- `generate index`: Create new index
- `create indexes`: Create all indexes
- `analyze indexes`: Analyze index usage
- `optimize indexes`: Optimize indexes

4. **Development Commands**
- `runserver`: Run development server
- `shell`: Run interactive shell
- `test`: Run tests
- `lint`: Run linters

5. **Database Commands**
- `db create`: Create database
- `db drop`: Drop database
- `db seed`: Seed test data
- `db backup`: Backup database

6. **Documentation Commands**
- `docs generate`: Generate documentation
- `docs serve`: Serve documentation
- `docs validate`: Validate documentation
- `docs export`: Export documentation

## Best Practices

1. **Code Generation**
- Use consistent naming
- Follow conventions
- Validate input
- Handle errors
- Generate tests

2. **Schema Management**
- Version control migrations
- Test migrations
- Backup before migrating
- Monitor progress
- Handle failures

3. **Development**
- Use debug mode
- Monitor resources
- Handle errors
- Log operations
- Test thoroughly

4. **Documentation**
- Keep docs updated
- Include examples
- Validate content
- Use templates
- Version docs

## Future Features

1. **Generation Features**
- [ ] Custom templates
- [ ] Code scaffolding
- [ ] API generation
- [ ] Test generation
- [ ] Doc generation

2. **Management Tools**
- [ ] GUI interface
- [ ] Remote management
- [ ] Batch operations
- [ ] Task scheduling
- [ ] Backup management

3. **Development Tools**
- [ ] Hot reload
- [ ] Debug tools
- [ ] Profile tools
- [ ] Test runners
- [ ] Code analysis

4. **Integration**
- [ ] IDE plugins
- [ ] CI/CD tools
- [ ] Cloud platforms
- [ ] Container tools
- [ ] Monitoring systems 