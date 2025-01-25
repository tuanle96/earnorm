"""Pool constants module.

This module contains all constants used in the pool module.
"""

# Default pool configuration
DEFAULT_MIN_POOL_SIZE = 1
DEFAULT_MAX_POOL_SIZE = 10
DEFAULT_MAX_IDLE_TIME = 300  # 5 minutes
DEFAULT_MAX_LIFETIME = 3600  # 1 hour
DEFAULT_CONNECTION_TIMEOUT = 30.0  # 30 seconds

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 5.0
DEFAULT_EXPONENTIAL_BASE = 2.0
DEFAULT_JITTER = 0.1

# Circuit breaker configuration
DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_RESET_TIMEOUT = 60.0  # 1 minute
DEFAULT_HALF_OPEN_TIMEOUT = 5.0

# Connection states
CONNECTION_AVAILABLE = "available"
CONNECTION_IN_USE = "in_use"
CONNECTION_CLOSED = "closed"
CONNECTION_ERROR = "error"

# Pool states
POOL_INITIALIZING = "initializing"
POOL_READY = "ready"
POOL_CLOSING = "closing"
POOL_CLOSED = "closed"
POOL_ERROR = "error"

# Operation timeouts (in seconds)
OPERATION_TIMEOUT = {
    "default": 30.0,
    "long": 300.0,  # 5 minutes
    "short": 5.0,
}

# Backend types
BACKEND_MONGODB = "mongodb"
BACKEND_REDIS = "redis"
BACKEND_MYSQL = "mysql"
BACKEND_POSTGRESQL = "postgresql"

# Health check intervals
HEALTH_CHECK_INTERVAL = 60.0  # 1 minute
CLEANUP_INTERVAL = 300.0  # 5 minutes
METRICS_INTERVAL = 60.0  # 1 minute
