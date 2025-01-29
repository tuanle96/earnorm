"""Base type definitions."""

from typing import Any, Dict, List, Literal, TypeAlias, Union

# JSON types
JsonValue = Union[str, int, float, bool, None, List[Any], Dict[str, Any]]
JsonDict: TypeAlias = Dict[str, Any]

# Domain operator type
DomainOperator: TypeAlias = Literal[
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "in",
    "not in",
    "like",
    "ilike",
    "not like",
    "not ilike",
    "=like",
    "=ilike",
    "contains",
    "not contains",
]

# Basic value type
ValueType = Union[str, int, float, bool, None]

__all__ = ["JsonValue", "JsonDict", "DomainOperator", "ValueType"]
