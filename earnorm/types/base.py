"""Base type definitions."""

from typing import Any, Literal, TypeAlias, Union

# JSON types
JsonValue = Union[str, int, float, bool, None, list[Any], dict[str, Any]]
JsonDict: TypeAlias = dict[str, Any]

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

__all__ = ["DomainOperator", "JsonDict", "JsonValue", "ValueType"]
