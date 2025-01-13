"""Rule system for EarnORM."""

import time
from typing import Any, Dict, List, Optional, Set, Type

from motor.motor_asyncio import AsyncIOMotorClientSession

from ..cache.cache import cached
from ..db.connection import ConnectionManager
from .model import BaseModel


class Rule:
    """Record rule for access control."""

    MODES = {"read", "write", "create", "unlink"}

    def __init__(
        self,
        name: str,
        model_cls: Type[BaseModel],
        domain: Optional[str] = None,
        groups: Optional[Set[str]] = None,
        modes: Optional[Set[str]] = None,
        active: bool = True,
    ) -> None:
        """Initialize rule.

        Args:
            name: Rule name
            model_cls: Model class
            domain: Domain expression
            groups: User groups
            modes: Access modes
            active: Whether rule is active
        """
        self.name = name
        self.model_cls = model_cls
        self.domain = domain
        self.groups = groups or set()
        self.modes = modes or self.MODES.copy()
        self.active = active

        # Validate modes
        invalid_modes = self.modes - self.MODES
        if invalid_modes:
            raise ValueError(f"Invalid modes: {invalid_modes}")

    def eval_context(
        self, session: Optional[AsyncIOMotorClientSession] = None
    ) -> Dict[str, Any]:
        """Get evaluation context for domain.

        Args:
            session: Optional database session

        Returns:
            dict: Evaluation context
        """
        # TODO: Add user context
        return {
            "time": time,
            "session": session,
        }

    @cached(ttl=300)  # Cache for 5 minutes
    async def check_access(
        self,
        records: List[BaseModel],
        mode: str,
        user_groups: Set[str],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if access is allowed.

        Args:
            records: Records to check
            mode: Access mode
            user_groups: User groups
            session: Optional database session

        Returns:
            bool: True if access is allowed
        """
        if not self.active:
            return True

        if mode not in self.modes:
            return True

        if self.groups and not (self.groups & user_groups):
            return True

        if not self.domain:
            return True

        # Evaluate domain
        context = self.eval_context(session)
        try:
            domain = eval(self.domain, context)  # TODO: Use safe_eval
        except Exception as e:
            raise ValueError(f"Invalid domain: {str(e)}")

        # Check domain
        conn = ConnectionManager()
        collection = conn.get_collection(self.model_cls.get_collection())

        cursor = collection.find(
            {
                "_id": {"$in": [r.id for r in records]},
                **domain,
            },
            session=session,
        )
        matching = await cursor.count_documents()
        return matching == len(records)


class RuleManager:
    """Record Rule manager."""

    def __init__(self) -> None:
        """Initialize rule manager."""
        self._rules: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    async def check_access(
        self,
        records: List[BaseModel],
        mode: str,
        groups: Set[str],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> bool:
        """Check if records can be accessed in given mode.

        Args:
            records: List of records to check
            mode: Access mode (read/write/create/unlink)
            groups: User groups
            session: Optional database session

        Returns:
            bool: True if access is allowed
        """
        if not records:
            return True

        # Get rules for collection and mode
        collection = records[0].get_collection()
        rules = self._rules.get(collection, {}).get(mode, [])
        if not rules:
            return True

        # Check each rule
        for rule in rules:
            if not rule.get("groups") or groups & set(rule["groups"]):
                # TODO: Apply domain to records when implementing domain evaluation
                pass

        return True

    @cached(ttl=300, key_pattern="rule_domain:{0.__name__}:{1}:{2}")
    async def get_domain(
        self,
        model_cls: Type[BaseModel],
        mode: str,
        groups: Set[str],
        session: Optional[AsyncIOMotorClientSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get security domain for model and mode.

        Args:
            model_cls: Model class
            mode: Access mode (read/write/create/unlink)
            groups: User groups
            session: Optional database session

        Returns:
            dict: Security domain or None
        """
        # Get rules for collection and mode
        collection = model_cls.get_collection()
        rules = self._rules.get(collection, {}).get(mode, [])
        if not rules:
            return None

        # Combine domains from matching rules
        domains: List[Dict[str, Any]] = []
        for rule in rules:
            if not rule.get("groups") or groups & set(rule["groups"]):
                domain = rule.get("domain")
                if domain:
                    domains.append(domain)

        if not domains:
            return None
        elif len(domains) == 1:
            return domains[0]
        else:
            return {"$or": domains}

    def register_rule(
        self,
        collection: str,
        mode: str,
        domain: Optional[Dict[str, Any]] = None,
        groups: Optional[List[str]] = None,
    ) -> None:
        """Register record rule.

        Args:
            collection: Collection name
            mode: Access mode (read/write/create/unlink)
            domain: Optional security domain
            groups: Optional list of groups
        """
        if collection not in self._rules:
            self._rules[collection] = {}
        if mode not in self._rules[collection]:
            self._rules[collection][mode] = []

        self._rules[collection][mode].append(
            {
                "domain": domain,
                "groups": groups,
            }
        )
