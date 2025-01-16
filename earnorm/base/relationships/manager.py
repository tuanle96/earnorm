"""Relationship manager implementation."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Type, cast

from motor.motor_asyncio import AsyncIOMotorCollection

from earnorm.base.models.interfaces import ModelInterface
from earnorm.base.types import ContainerProtocol, DocumentType
from earnorm.di import container


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
    """Relationship manager.

    This class manages model relationships:
    - Storing relationship definitions
    - Loading relationship data
    - Managing inverse relationships
    - Handling cascading deletes

    Attributes:
        _relationships: Dict mapping model names to their relationships
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

        Example:
            >>> manager = RelationshipManager()
            >>> relationship = manager.get_relationship("Post", "author")
        """
        return self._relationships.get(model, {}).get(name)

    def get_relationships(self, model: str) -> Dict[str, Relationship]:
        """Get all relationships for model.

        Args:
            model: Name of the model

        Returns:
            Dict mapping relationship names to definitions

        Example:
            >>> manager = RelationshipManager()
            >>> relationships = manager.get_relationships("Post")
        """
        return self._relationships.get(model, {})

    def get_inverse_relationships(self, model: str) -> List[Relationship]:
        """Get inverse relationships for model.

        Args:
            model: Name of the model

        Returns:
            List of relationships where this model is the target

        Example:
            >>> manager = RelationshipManager()
            >>> inverse = manager.get_inverse_relationships("User")
        """
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

    async def load_relationship(self, model: ModelInterface, name: str) -> Any:
        """Load relationship data.

        Args:
            model: Source model instance
            name: Name of the relationship field

        Returns:
            Loaded relationship data:
            - many2one: Single model instance or None
            - one2many/many2many: Sequence of model instances

        Raises:
            ValueError: If relationship not found or invalid

        Example:
            >>> post = Post(...)
            >>> author = await manager.load_relationship(post, "author")
        """
        relationship = self.get_relationship(model.__class__.__name__, name)
        if not relationship:
            raise ValueError(f"Relationship not found: {name}")

        # Get target model
        target_model = self._get_target_model(relationship.target_model)

        # Load based on type
        if relationship.relation_type == "many2one":
            return await self._load_many2one(model, relationship, target_model)
        elif relationship.relation_type == "one2many":
            return await self._load_one2many(model, relationship, target_model)
        elif relationship.relation_type == "many2many":
            return await self._load_many2many(model, relationship, target_model)
        else:
            raise ValueError(f"Invalid relation type: {relationship.relation_type}")

    def _get_target_model(self, model_name: str) -> Type[ModelInterface]:
        """Get target model class.

        Args:
            model_name: Name of the target model

        Returns:
            Target model class

        Raises:
            ValueError: If model not found
        """
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        model_cls = registry.get(model_name)
        if not model_cls:
            raise ValueError(f"Model not found: {model_name}")

        return cast(Type[ModelInterface], model_cls)

    async def _load_many2one(
        self,
        model: ModelInterface,
        relationship: Relationship,
        target_model: Type[ModelInterface],
    ) -> Optional[ModelInterface]:
        """Load many2one relationship.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            Target model instance if found, None otherwise
        """
        # Get foreign key value
        foreign_key = getattr(model, relationship.name + "_id", None)
        if not foreign_key:
            return None

        # Load target record
        return await target_model.find_one({"_id": foreign_key})

    async def _load_one2many(
        self,
        model: ModelInterface,
        relationship: Relationship,
        target_model: Type[ModelInterface],
    ) -> Sequence[ModelInterface]:
        """Load one2many relationship.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            Sequence of target model instances

        Raises:
            ValueError: If inverse_field not specified
        """
        if not relationship.inverse_field:
            raise ValueError("inverse_field required for one2many relationship")

        # Build query
        query = {relationship.inverse_field: model.id}
        if relationship.order:
            sort = [(relationship.order, 1)]
        else:
            sort = None

        # Load target records
        return await target_model.find(query, sort=sort)

    async def _load_many2many(
        self,
        model: ModelInterface,
        relationship: Relationship,
        target_model: Type[ModelInterface],
    ) -> Sequence[ModelInterface]:
        """Load many2many relationship.

        Args:
            model: Source model instance
            relationship: Relationship definition
            target_model: Target model class

        Returns:
            Sequence of target model instances

        Raises:
            ValueError: If relation collection not specified
        """
        # Get relation collection
        relation_name = relationship.options.get("relation")
        if not relation_name:
            raise ValueError("relation required for many2many relationship")

        # Load relation records
        container_instance = cast(ContainerProtocol, container)
        registry = container_instance.registry
        db = registry.db
        if db is None:  # type: ignore
            raise ValueError("Database not initialized")

        relation_collection: AsyncIOMotorCollection[DocumentType] = db[relation_name]

        # Get target IDs
        cursor = relation_collection.find({relationship.name + "_id": model.id})
        relations = await cursor.to_list(None)  # type: ignore

        target_ids = [r["target_id"] for r in cast(List[Dict[str, Any]], relations)]

        # Load target records
        if not target_ids:
            return []

        return await target_model.find({"_id": {"$in": target_ids}})
