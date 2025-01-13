"""Example of advanced EarnORM features.

This example demonstrates:
1. Computed fields
2. Field validation and constraints
3. Model inheritance and mixins
4. Record rules and access control
5. Caching and performance optimization
6. Audit logging and encryption
7. Custom field types
8. Model hooks and signals
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from earnorm import BaseModel, env, fields
from earnorm.di import container
from earnorm.security import audit, encryption


# Custom field type
class DecimalField(fields.Field):
    """Custom field type for Decimal values."""

    def __init__(self, precision: int = 2, **kwargs):
        """Initialize decimal field.

        Args:
            precision: Number of decimal places
            **kwargs: Additional field options
        """
        super().__init__(**kwargs)
        self.precision = precision

    def validate(self, value: Any) -> None:
        """Validate decimal value.

        Args:
            value: Value to validate

        Raises:
            ValueError: If value is not a valid decimal
        """
        if not isinstance(value, (int, float, Decimal, str)):
            raise ValueError("Value must be numeric")

        try:
            Decimal(str(value))
        except:
            raise ValueError("Invalid decimal value")

    def to_db(self, value: Any) -> str:
        """Convert value to database format.

        Args:
            value: Value to convert

        Returns:
            String representation of decimal
        """
        if value is None:
            return None

        decimal = Decimal(str(value)).quantize(Decimal(f"0.{'0' * self.precision}"))
        return str(decimal)

    def from_db(self, value: str) -> Decimal:
        """Convert value from database format.

        Args:
            value: Value to convert

        Returns:
            Decimal value
        """
        if value is None:
            return None

        return Decimal(value)


# Base model with common fields
class CommonMixin(BaseModel):
    """Common fields and methods for all models."""

    _abstract = True

    active = fields.Boolean(string="Active", default=True)
    created_at = fields.DateTime(string="Created At", default=datetime.utcnow)
    updated_at = fields.DateTime(string="Updated At", default=datetime.utcnow)
    created_by = fields.Many2one(string="Created By", collection="users")
    updated_by = fields.Many2one(string="Updated By", collection="users")

    @fields.computed(depends=["created_at"])
    def age_days(self) -> int:
        """Compute age in days."""
        if not self.created_at:
            return 0

        delta = datetime.utcnow() - self.created_at
        return delta.days

    async def write(self, values: Dict) -> None:
        """Override write to update timestamps."""
        values["updated_at"] = datetime.utcnow()
        values["updated_by"] = env.user.id
        await super().write(values)

    @classmethod
    def _get_rules(cls) -> List[Dict]:
        """Define record rules."""
        return [
            {
                "name": "active_records",
                "domain": [("active", "=", True)],
                "groups": ["user", "admin"],
                "mode": ["read"],
            },
            {
                "name": "own_records",
                "domain": [("created_by", "=", "user.id")],
                "groups": ["user"],
                "mode": ["write", "unlink"],
            },
            {
                "name": "all_records",
                "domain": [],
                "groups": ["admin"],
                "mode": ["read", "write", "unlink"],
            },
        ]


# Product category model
class Category(CommonMixin):
    """Product category model."""

    _collection = "categories"
    _indexes = [{"keys": [("name", 1)], "unique": True}]

    name = fields.Char(string="Name", required=True, unique=True)
    parent_id = fields.Many2one(string="Parent Category", collection="categories")
    child_ids = fields.One2many(
        string="Child Categories", collection="categories", field="parent_id"
    )

    @fields.computed(depends=["parent_id", "parent_id.complete_name"])
    def complete_name(self) -> str:
        """Compute complete category path."""
        if not self.parent_id:
            return self.name

        return f"{self.parent_id.complete_name} / {self.name}"


# Product model with advanced features
class Product(CommonMixin):
    """Product model with advanced features."""

    _collection = "products"
    _indexes = [{"keys": [("sku", 1)], "unique": True}, {"keys": [("name", 1)]}]
    _audit_fields = ["name", "price", "category_id"]
    _encrypted_fields = ["notes"]

    name = fields.Char(string="Name", required=True, index=True)
    sku = fields.Char(string="SKU", required=True, unique=True)
    description = fields.Text(string="Description")
    category_id = fields.Many2one(
        string="Category", collection="categories", required=True
    )
    price = DecimalField(string="Price", required=True, precision=2)
    cost = DecimalField(string="Cost", required=True, precision=2)
    notes = fields.Text(string="Internal Notes", encrypted=True)
    tags = fields.List(string="Tags", field=fields.Char())
    attributes = fields.Dict(string="Attributes")
    image_url = fields.Url(string="Image URL")

    @fields.computed(depends=["price", "cost"])
    def margin(self) -> Decimal:
        """Compute profit margin."""
        if not self.price or not self.cost or self.cost == 0:
            return Decimal("0.00")

        margin = (self.price - self.cost) / self.cost * 100
        return margin.quantize(Decimal("0.01"))

    @fields.computed(store=True, depends=["category_id", "category_id.complete_name"])
    def category_path(self) -> str:
        """Compute full category path."""
        if not self.category_id:
            return ""

        return self.category_id.complete_name

    @fields.constrains("price", "cost")
    def _check_prices(self):
        """Validate price and cost."""
        if self.price and self.cost and self.price < self.cost:
            raise ValueError("Price cannot be lower than cost")

    async def copy(self, default: Optional[Dict] = None) -> "Product":
        """Copy product with a new SKU."""
        default = default or {}
        if "sku" not in default:
            default["sku"] = f"{self.sku}-COPY"

        return await super().copy(default)

    @classmethod
    async def _before_create(cls, values: Dict) -> None:
        """Pre-create hook."""
        if "sku" in values:
            values["sku"] = values["sku"].upper()

    @classmethod
    async def _after_create(cls, record: "Product") -> None:
        """Post-create hook."""
        await audit.log_change(
            model=cls._collection,
            record_id=record.id,
            action="create",
            changes=record.read(),
        )

    async def _before_write(self, values: Dict) -> None:
        """Pre-write hook."""
        if "sku" in values:
            values["sku"] = values["sku"].upper()

    async def _after_write(self, values: Dict) -> None:
        """Post-write hook."""
        await audit.log_change(
            model=self._collection, record_id=self.id, action="write", changes=values
        )

    async def _before_unlink(self) -> None:
        """Pre-delete hook."""
        if self.child_ids:
            raise ValueError("Cannot delete category with children")

    async def _after_unlink(self) -> None:
        """Post-delete hook."""
        await audit.log_change(
            model=self._collection, record_id=self.id, action="unlink", changes={}
        )


async def example_usage():
    """Example usage of advanced features."""
    # Initialize container
    await container.init_resources(
        mongo_uri="mongodb://localhost:27017", database="earnorm_example"
    )

    try:
        # Create categories
        electronics = await env["categories"].create({"name": "Electronics"})

        computers = await env["categories"].create(
            {"name": "Computers", "parent_id": electronics.id}
        )

        laptops = await env["categories"].create(
            {"name": "Laptops", "parent_id": computers.id}
        )

        # Create product
        product = await env["products"].create(
            {
                "name": "ThinkPad X1 Carbon",
                "sku": "tp-x1c-001",
                "description": "High-end business laptop",
                "category_id": laptops.id,
                "price": "1499.99",
                "cost": "1200.00",
                "notes": "Special order item",
                "tags": ["laptop", "business", "premium"],
                "attributes": {
                    "cpu": "Intel i7",
                    "ram": "16GB",
                    "storage": "512GB SSD",
                },
                "image_url": "https://example.com/thinkpad-x1.jpg",
            }
        )

        # Access computed fields
        print(f"Category path: {product.category_path}")
        print(f"Profit margin: {product.margin}%")
        print(f"Age in days: {product.age_days}")

        # Update product
        await product.write(
            {"price": "1599.99", "notes": "Price increased due to high demand"}
        )

        # Search with domain
        premium_products = await env["products"].search(
            [
                ("tags", "in", ["premium"]),
                ("price", ">=", 1000),
                ("category_id.complete_name", "ilike", "Laptop"),
            ]
        )

        # Get audit logs
        logs = await audit.get_logs(model="products", record_id=product.id)

        print("\nAudit logs:")
        for log in logs:
            print(f"- {log.action}: {log.changes}")

    finally:
        # Cleanup
        await container.cleanup()
