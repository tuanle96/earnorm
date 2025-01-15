"""Type stubs for Celery."""

from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

T = TypeVar("T")

class Task:
    """Task class stub."""

    request: Any
    name: str
    id: str

    def retry(self, **kwargs: Any) -> None: ...
    def apply_async(
        self,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        countdown: Optional[int] = None,
        eta: Optional[Any] = None,
        expires: Optional[Any] = None,
        retry: bool = True,
        retry_policy: Optional[Dict[str, Any]] = None,
        queue: Optional[str] = None,
    ) -> "AsyncResult": ...

class AsyncResult:
    """AsyncResult class stub."""

    id: str

    def __init__(self, id: str) -> None: ...
    def failed(self) -> bool: ...
    def retry(self) -> None: ...
    def revoke(self, terminate: bool = False) -> None: ...

class Celery:
    """Celery class stub."""

    control: Any

    def __init__(self, name: str) -> None: ...
    def task(
        self, name: Optional[str] = None, bind: bool = False, **options: Any
    ) -> Callable[[Callable[..., Any]], Task]: ...
    def config_from_object(
        self, obj: Union[str, object], silent: bool = False, force: bool = False
    ) -> None: ...
