# Metrics Components

Performance monitoring and metrics collection for EarnORM.

## Purpose

The metrics module provides monitoring capabilities:
- Performance monitoring
- Query profiling
- Operation statistics
- Resource usage
- Health checks
- Alerting system

## Concepts & Examples

### Basic Metrics
```python
# Initialize metrics
metrics = MetricsManager()

# Record timing
with metrics.timer("query.execution"):
    results = User.find().all()

# Count operations
metrics.increment("user.created")
metrics.decrement("active_connections")

# Record values
metrics.gauge("cache.size", cache.size())
metrics.histogram("response_time", duration)
```

### Query Profiling
```python
# Profile query
with QueryProfiler() as profiler:
    users = User.find().filter(age__gte=18).all()
    
# Get profile results
profile = profiler.get_profile()
print(f"Query time: {profile.duration}ms")
print(f"Documents examined: {profile.docs_examined}")
print(f"Keys examined: {profile.keys_examined}")

# Analyze slow queries
slow_queries = profiler.get_slow_queries()
for query in slow_queries:
    print(f"Slow query: {query.operation}")
    print(f"Duration: {query.duration}ms")
    print(f"Suggestion: {query.optimization_hint}")
```

### Resource Monitoring
```python
# Monitor connections
conn_stats = metrics.get_connection_stats()
print(f"Active connections: {conn_stats.active}")
print(f"Available connections: {conn_stats.available}")

# Monitor memory
mem_stats = metrics.get_memory_stats()
print(f"Memory usage: {mem_stats.used_mb}MB")
print(f"Cache size: {mem_stats.cache_mb}MB")

# Monitor operations
op_stats = metrics.get_operation_stats()
print(f"Queries/sec: {op_stats.query_rate}")
print(f"Writes/sec: {op_stats.write_rate}")
```

### Health Checks
```python
# Define health checks
@health_check("database")
async def check_database():
    try:
        await db.admin.command("ping")
        return HealthStatus.OK
    except Exception as e:
        return HealthStatus.ERROR(str(e))

# Run health checks
health = HealthChecker()
status = await health.check_all()

# Get health report
report = health.get_report()
for check in report.checks:
    print(f"{check.name}: {check.status}")
    if check.error:
        print(f"Error: {check.error}")
```

## Best Practices

1. **Metric Collection**
- Choose meaningful metrics
- Use appropriate types
- Set proper intervals
- Handle errors gracefully
- Consider performance

2. **Profiling**
- Profile selectively
- Analyze patterns
- Document findings
- Implement improvements
- Monitor impact

3. **Resource Management**
- Set proper thresholds
- Monitor trends
- Handle alerts
- Plan capacity
- Optimize usage

4. **Health Monitoring**
- Define critical checks
- Set proper timeouts
- Handle dependencies
- Document procedures
- Plan recovery

## Future Features

1. **Metric Types**
- [ ] Custom metrics
- [ ] Composite metrics
- [ ] Derived metrics
- [ ] Business metrics
- [ ] SLA metrics

2. **Profiling Tools**
- [ ] Query analyzer
- [ ] Performance advisor
- [ ] Bottleneck detector
- [ ] Impact analyzer
- [ ] Trend analyzer

3. **Monitoring Features**
- [ ] Real-time monitoring
- [ ] Predictive analytics
- [ ] Anomaly detection
- [ ] Capacity planning
- [ ] Cost analysis

4. **Integration**
- [ ] Prometheus integration
- [ ] Grafana dashboards
- [ ] Alert managers
- [ ] Log aggregators
- [ ] APM tools 