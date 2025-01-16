"""Relationship manager implementation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, TypedDict, TypeVar, cast

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor

from earnorm.base.types import (
    ContainerProtocol,
    DocumentType,
    ModelProtocol,
    RecordSetProtocol,
)
from earnorm.di import container

M = TypeVar("M", bound=ModelProtocol)


class RelationDict(TypedDict):
    """Type definition for relation document."""

    source_id: str
    target_id: str


@dataclass
class Relationship:
    """Relationship definition.

    This class defines a relationship between two models with various options:
    - many2one: Foreign key relationship (e.g. Post -> User)
    - one2many: Inverse of many2one (e.g. User -> Posts)
    - many2many: Many-to-many relationship through a relation collection

    Attributes:
        name: Name of the relationship field
        target_model: Name of the target model
        relation_type: Type of relationship ("many2one", "one2many", "many2many")
        inverse_field: Name of the inverse relationship field (required for one2many)
        lazy: Whether to load the relationship data lazily
        cascade: Cascade behavior on delete ("delete", "nullify")
        order: Field to order by for one2many relationships
        options: Additional options (e.g. relation collection for many2many)

    Example:
        >>> relationship = Relationship(
        ...     name="author",
        ...     target_model="User",
        ...     relation_type="many2one",
        ...     inverse_field="posts",
        ...     cascade="nullify"
        ... )
    """

    name: str
    target_model: str
    relation_type: str  # "many2one", "one2many", "many2many"
    inverse_field: Optional[str] = None
    lazy: bool = True
    cascade: Optional[str] = None  # "delete", "nullify"
    order: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)


class RelationshipManager:
    """Manages relationships between models.

    This class handles loading and managing relationships between models:
    - many2one: Foreign key relationships (e.g. Post -> User)
    - one2many: Inverse of many2one (e.g. User -> Posts)
    - many2many: Many-to-many relationships through a relation collection

    Examples:
        >>> manager = RelationshipManager()
        >>> # Load many2one relationship
        >>> user = await manager._load_many2one(post, relationship, User)
        >>> # Load one2many relationship
        >>> posts = await manager._load_one2many(user, relationship, Post)
        >>> # Load many2many relationship
        >>> tags = await manager._load_many2many(post, relationship, Tag)
    """

    def __init__(self) -> None:
        """Initialize manager with empty relationships."""
        self._relationships: Dict[str, Dict[str, Relationship]] = {}

    def add_relationship(
        self,
        model: str,
        name: str,
        target_model: str,
        relation_type: str,
        **options: Any,
    ) -> None:
        """Add relationship definition.

        Args:
            model: Name of the source model
            name: Name of the relationship field
            target_model: Name of the target model
            relation_type: Type of relationship
            **options: Additional relationship options

        Raises:
            ValueError: If model name, field name or target model is empty
            ValueError: If relation type is invalid
            ValueError: If inverse field is missing for one2many relationship

        Example:
            >>> manager = RelationshipManager()
            >>> manager.add_relationship(
            ...     model="Post",
            ...     name="author",
            ...     target_model="User",
            ...     relation_type="many2one",
            ...     inverse_field="posts"
            ... )
        """
        if not model:
            raise ValueError("Model name cannot be empty")
        if not name:
            raise ValueError("Field name cannot be empty")
        if not target_model:
            raise ValueError("Target model cannot be empty")
        if relation_type not in ("many2one", "one2many", "many2many"):
            raise ValueError("Invalid relation type")
        if relation_type == "one2many" and "inverse_field" not in options:
            raise ValueError("Inverse field is required for one2many relationship")

        if model not in self._relationships:
            self._relationships[model] = {}

        self._relationships[model][name] = Relationship(
            name=name, target_model=target_model, relation_type=relation_type, **options
        )

    def get_relationship(self, model: str, name: str) -> Optional[Relationship]:
        """Get relationship by name.

        Args:
            model: Name of the source model
            name: Name of the relationship field

        Returns:
            Relationship definition if found, None otherwise

        Raises:
            ValueError: If model name or field name is empty

        Example:
            >>> manager = RelationshipManager()
            >>> relationship = manager.get_relationship("Post", "author")
        """
        if not model:
            raise ValueError("Model name cannot be empty")
        if not name:
            raise ValueError("Field name cannot be empty")
        return self._relationships.get(model, {}).get(name)

    def get_relationships(self, model: str) -> Dict[str, Relationship]:
        """Get all relationships for model.

        Args:
            model: Name of the model

        Returns:
            Dict mapping relationship names to definitions

        Raises:
            ValueError: If model name is empty

        Example:
            >>> manager = RelationshipManager()
            >>> relationships = manager.get_relationships("Post")
        """
        if not model:
            raise ValueError("Model name cannot be empty")
        return self._relationships.get(model, {})

    def get_inverse_relationships(self, model: str) -> List[Relationship]:
        """Get inverse relationships for model.

        Args:
            model: Name of the model

        Returns:
            List of relationships where this model is the target

        Raises:
            ValueError: If model name is empty

        Example:
            >>> manager = RelationshipManager()
            >>> inverse = manager.get_inverse_relationships("User")
        """
        if not model:
            raise ValueError("Model name cannot be empty")

        inverse: List[Relationship] = []

        # Search all models
        for _, relationships in self._relationships.items():
            # Search relationships
            for relationship in relationships.values():
                if (
                    relationship.target_model == model
                    and relationship.inverse_field is not None
                ):
                    inverse.append(relationship)

        return inverse

    async def load(
        self,
        model: ModelProtocol,
        relationship: Relationship,
    ) -> Optional[RecordSetProtocol[ModelProtocol]]:
        """Load relationship data.

        Args:
            model: Source model instance
            relationship: Relationship definition

        Returns:
            RecordSet containing related records or None if not found

        Raises:
            ValueError: If relationship type is invalid
        """
        target_model = self._get_target_model(relationship.target_model)

        if relationship.relation_type == "many2one":
            return await self._load_many2one(model, relationship, target_model)
        elif relationship.relation_type == "one2many":
            return await self._load_one2many(model, relationship, target_model)
        elif relationship.relation_type == "many2many":
            return await self._load_many2many(model, relationship, target_model)
        else:
            raise ValueError(f"Invalid relationship type: {relationship.relation_type}")

    def _get_target_model(self, model_name: str) -> Type[ModelProtocol]:
        """Get target model class.

        Args:
            model_name: Name of the target model

        Returns:
            Target model class

        Raises:
            ValueError: If model name is empty or model not found

        Example:
            >>> manager = RelationshipManager()
            >>> user_model = manager._get_target_model("User")
        """
        if not model_name:
            raise ValueError("Model name cannot be empty")

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        model_cls = registry.get(model_name)
        if not model_cls:
            raise ValueError(f"Model not found: {model_name}")

        return model_cls  # type: ignore

    async def _load_many2one(
        self,
        model: ModelProtocol,
        relationship: Relationship,
        target_model: Type[ModelProtocol],
    ) -> Optional[RecordSetProtocol[ModelProtocol]]:
        """Load many2one relationship.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            Target model instance if found, None otherwise

        Raises:
            ValueError: If foreign key field is missing
        """
        # Get foreign key value
        foreign_key = getattr(model, relationship.name + "_id", None)
        if not foreign_key:
            return None

        # Load target record
        return await target_model.find_one([("_id", "=", foreign_key)])

    async def _load_one2many(
        self,
        model: ModelProtocol,
        relationship: Relationship,
        target_model: Type[ModelProtocol],
    ) -> RecordSetProtocol[ModelProtocol]:
        """Load one2many relationship data.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            RecordSet containing related records
        """
        if not relationship.inverse_field:
            raise ValueError("Inverse field is required for one2many relationship")

        # Get target records
        target_records = await target_model.search(
            [[relationship.inverse_field, "=", model.id]]
        )
        return target_records

    async def _load_many2many(
        self,
        model: ModelProtocol,
        relationship: Relationship,
        target_model: Type[ModelProtocol],
    ) -> RecordSetProtocol[ModelProtocol]:
        """Load many2many relationship data.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            RecordSet containing related records
        """
        # Get relation collection
        relation_collection = self._get_relation_collection(relationship)

        # Get relations
        cursor: AsyncIOMotorCursor[RelationDict] = relation_collection.find(
            {"source_id": model.id}
        )  # type: ignore
        relations: List[RelationDict] = await cursor.to_list(None)  # type: ignore

        # Get target IDs
        target_ids = [str(rel["target_id"]) for rel in relations if rel["target_id"]]

        # Get target records
        if not target_ids:
            return await target_model.search([["_id", "in", []]])

        target_records = await target_model.search([["_id", "in", target_ids]])
        return target_records

    def _get_relation_collection(
        self, relationship: Relationship
    ) -> AsyncIOMotorCollection[DocumentType]:
        """Get relation collection for many2many relationship.

        Args:
            relationship: Relationship definition

        Returns:
            MongoDB collection for storing relations

        Raises:
            ValueError: If relation collection is missing
        """
        relation_collection = relationship.options.get("relation_collection")
        if not relation_collection:
            raise ValueError(
                "Relation collection is required for many2many relationship"
            )

        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        return db[relation_collection]
