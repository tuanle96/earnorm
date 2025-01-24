"""Log correlation for correlating log entries."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set


class LogCorrelation:
    """Class for correlating log entries.

    This class provides functionality to:
    - Generate correlation IDs
    - Track request flows
    - Group related log entries
    - Track request timing

    Examples:
        >>> # Track request flow
        >>> correlation = LogCorrelation()
        >>> request_id = correlation.start_request()
        >>> log_entry = {'message': 'Processing request'}
        >>> correlated = correlation.correlate(log_entry, request_id)
        >>> assert correlated['request_id'] == request_id
        >>> correlation.end_request(request_id)

        >>> # Group related entries
        >>> correlation = LogCorrelation()
        >>> group_id = correlation.start_group('batch_job')
        >>> for i in range(3):
        ...     log_entry = {'message': f'Processing item {i}'}
        ...     correlated = correlation.correlate(log_entry, group_id)
        ...     assert correlated['group_id'] == group_id
        >>> correlation.end_group(group_id)

        >>> # Track timing
        >>> correlation = LogCorrelation()
        >>> request_id = correlation.start_request()
        >>> # ... do some work ...
        >>> timing = correlation.get_request_timing(request_id)
        >>> assert timing.total_seconds() > 0
    """

    def __init__(self):
        """Initialize the log correlation."""
        self._active_requests: Dict[str, datetime] = {}
        self._active_groups: Dict[str, str] = {}
        self._request_parents: Dict[str, str] = {}
        self._group_members: Dict[str, Set[str]] = {}

    def start_request(self, parent_id: Optional[str] = None) -> str:
        """Start tracking a new request.

        Args:
            parent_id: ID of the parent request if this is a sub-request.

        Returns:
            str: The generated request ID.
        """
        request_id = str(uuid.uuid4())
        self._active_requests[request_id] = datetime.now()

        if parent_id:
            self._request_parents[request_id] = parent_id

        return request_id

    def end_request(self, request_id: str) -> None:
        """Stop tracking a request.

        Args:
            request_id: The request ID to stop tracking.
        """
        self._active_requests.pop(request_id, None)
        self._request_parents.pop(request_id, None)

    def start_group(self, group_type: str) -> str:
        """Start a new group of related log entries.

        Args:
            group_type: Type of the group (e.g. 'batch_job', 'transaction').

        Returns:
            str: The generated group ID.
        """
        group_id = str(uuid.uuid4())
        self._active_groups[group_id] = group_type
        self._group_members[group_id] = set()
        return group_id

    def end_group(self, group_id: str) -> None:
        """End a group of related log entries.

        Args:
            group_id: The group ID to end.
        """
        self._active_groups.pop(group_id, None)
        self._group_members.pop(group_id, None)

    def get_request_timing(self, request_id: str) -> Optional[timedelta]:
        """Get the time elapsed since a request started.

        Args:
            request_id: The request ID to check.

        Returns:
            Optional[timedelta]: The elapsed time if request is active.
        """
        if start_time := self._active_requests.get(request_id):
            return datetime.now() - start_time
        return None

    def get_request_chain(self, request_id: str) -> List[str]:
        """Get the chain of request IDs from root to this request.

        Args:
            request_id: The request ID to get the chain for.

        Returns:
            List[str]: List of request IDs from root to this request.
        """
        chain: List[str] = []
        current = request_id

        while current:
            chain.append(current)
            current = self._request_parents.get(current)

        return list(reversed(chain))

    def get_group_members(self, group_id: str) -> Set[str]:
        """Get the set of request IDs in a group.

        Args:
            group_id: The group ID to get members for.

        Returns:
            Set[str]: Set of request IDs in the group.
        """
        return self._group_members.get(group_id, set()).copy()

    def correlate(
        self, log_entry: Dict[str, Any], correlation_id: str
    ) -> Dict[str, Any]:
        """Correlate a log entry with a request or group.

        Args:
            log_entry: The log entry to correlate.
            correlation_id: The request or group ID to correlate with.

        Returns:
            Dict[str, Any]: The correlated log entry.
        """
        entry = log_entry.copy()

        # Check if this is a request ID
        if correlation_id in self._active_requests:
            entry["request_id"] = correlation_id

            # Add request chain
            chain = self.get_request_chain(correlation_id)
            if len(chain) > 1:
                entry["request_chain"] = chain
                entry["root_request_id"] = chain[0]

            # Add timing
            if timing := self.get_request_timing(correlation_id):
                entry["request_time"] = timing.total_seconds()

        # Check if this is a group ID
        if correlation_id in self._active_groups:
            entry["group_id"] = correlation_id
            entry["group_type"] = self._active_groups[correlation_id]

            # Track request ID as group member if this is also a request
            if request_id := entry.get("request_id"):
                self._group_members[correlation_id].add(request_id)

        return entry
