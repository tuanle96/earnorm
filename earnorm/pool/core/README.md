# Pool Core Module

This module provides core functionality for connection pooling in the EarnORM framework.

## Overview

The core module consists of three main components:

1. Circuit Breaker (`circuit.py`)
   - Fault detection
   - State management
   - Failure thresholds
   - Recovery timeouts

2. Retry Policy (`retry.py`)
   - Retry strategies
   - Backoff algorithms
   - Timeout handling
   - Error filtering

3. Resilience Patterns (`resilience.py`)
   - Combined patterns
   - Error handling
   - Timeout management
   - Health monitoring

## Features

### 1. Circuit Breaker
```python
from earnorm.pool.core import CircuitBreaker, CircuitState

# Create circuit breaker
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    half_open_timeout=30
)

# Use circuit breaker
async with breaker:
    # Protected operation
    result = await perform_operation()

# Check state
if breaker.state == CircuitState.OPEN:
    # Handle open circuit
    ...
```

### 2. Retry Policy
```python
from earnorm.pool.core import RetryPolicy

# Create retry policy
retry = RetryPolicy(
    max_retries=3,
    backoff_factor=2,
    max_timeout=30,
    retry_exceptions=[ConnectionError]
)

# Use retry policy
async with retry:
    # Operation with retries
    result = await perform_operation()
```

### 3. Resilience Patterns
```python
from earnorm.pool.core import with_resilience

# Combine patterns
@with_resilience(
    circuit_breaker=True,
    retry_policy=True,
    timeout=10
)
async def resilient_operation():
    # Protected operation
    ...
```

## Implementation Guide

### 1. Circuit Breaker Pattern

1. Basic usage:
```python
from earnorm.pool.core import CircuitBreaker

# Create breaker
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60
)

# Use breaker
async def operation():
    async with breaker:
        return await perform_operation()
```

2. Advanced configuration:
```python
# Custom failure detection
breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    half_open_timeout=30,
    failure_predicates=[
        lambda e: isinstance(e, ConnectionError)
    ]
)

# State listeners
breaker.on_state_change(lambda state: print(f"State: {state}"))
breaker.on_failure(lambda error: print(f"Error: {error}"))
```

### 2. Retry Policy Pattern

1. Basic usage:
```python
from earnorm.pool.core import RetryPolicy

# Create policy
retry = RetryPolicy(max_retries=3)

# Use policy
async def operation():
    async with retry:
        return await perform_operation()
```

2. Advanced configuration:
```python
# Custom backoff
retry = RetryPolicy(
    max_retries=3,
    backoff_factor=2,
    max_timeout=30,
    jitter=True
)

# Error filtering
retry = RetryPolicy(
    max_retries=3,
    retry_exceptions=[ConnectionError, TimeoutError],
    retry_predicates=[
        lambda e: "retryable" in str(e)
    ]
)
```

### 3. Combined Patterns

1. Decorator usage:
```python
@with_resilience(
    circuit_breaker=True,
    retry_policy=True,
    timeout=10
)
async def resilient_operation():
    return await perform_operation()
```

2. Context manager:
```python
from earnorm.pool.core import ResilienceContext

async with ResilienceContext(
    circuit_breaker=True,
    retry_policy=True,
    timeout=10
):
    result = await perform_operation()
```

## Best Practices

1. Circuit Breaker
   - Set appropriate thresholds
   - Configure timeouts
   - Handle state changes
   - Monitor failures
   - Log state transitions

2. Retry Policy
   - Limit max retries
   - Use exponential backoff
   - Add jitter
   - Filter errors
   - Set timeouts

3. Resilience Patterns
   - Combine appropriately
   - Handle timeouts
   - Monitor health
   - Log failures
   - Track metrics

4. Error Handling
   - Define failure criteria
   - Handle timeouts
   - Log errors
   - Monitor health
   - Track metrics

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit a pull request

## License

This module is part of the EarnORM framework and is licensed under the same terms. 
