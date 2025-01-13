"""Type definitions for the base package."""

from typing import Any, Dict, List, Optional, TypeVar, Union

from bson import ObjectId

# Type definitions
Document = Dict[str, Any]
DocumentList = List[Document]
DocumentId = Union[str, ObjectId]
Filter = Dict[str, Any]
Update = Dict[str, Any]
Sort = Dict[str, int]
Projection = Dict[str, Union[int, bool]]

# Type variables
T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")

# MongoDB specific types
MongoDocument = Dict[str, Any]
MongoFilter = Dict[str, Any]
MongoUpdate = Dict[str, Any]
MongoSort = Dict[str, int]
MongoProjection = Dict[str, Union[int, bool]]

# Cache types
CacheKey = str
CacheValue = Any
CacheTTL = Optional[int]

# Event types
EventName = str
EventHandler = Any  # Will be properly typed in events module

# Validation types
ValidationResult = Dict[str, List[str]]
ValidationError = Dict[str, str]

# Security types
Credentials = Dict[str, str]
Token = str
TokenPayload = Dict[str, Any]

# API types
Headers = Dict[str, str]
QueryParams = Dict[str, str]
PathParams = Dict[str, str]
RequestBody = Any
ResponseBody = Any

# Common types
JsonDict = Dict[str, Any]
JsonList = List[Any]
Timestamp = float
Duration = float
