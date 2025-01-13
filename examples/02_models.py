"""Example of defining and using models in EarnORM.

This example demonstrates:
1. Defining abstract and concrete models
2. Using fields with validation
3. Implementing model methods and computed fields
4. Using model inheritance
5. Working with relationships
"""

from datetime import datetime
from typing import List, Optional

from earnorm import BaseModel, fields


# Abstract base model for common fields and methods
class CommonMixin(BaseModel):
    """Common fields and methods for all models."""

    _abstract = True

    active = fields.Boolean(string="Active", default=True)
    created_at = fields.DateTime(string="Created At", default=datetime.utcnow)
    updated_at = fields.DateTime(string="Updated At", default=datetime.utcnow)

    async def archive(self) -> None:
        """Archive the record."""
        await self.write({"active": False})

    async def unarchive(self) -> None:
        """Unarchive the record."""
        await self.write({"active": True})


# Product Category model
class Category(CommonMixin):
    """Product category model."""

    _collection = "categories"
    _indexes = [{"keys": [("name", 1)], "unique": True}]

    name = fields.Char(string="Name", required=True, index=True)
    description = fields.Text(string="Description")
    parent_id = fields.Many2one("categories", string="Parent Category")
    child_ids = fields.One2many("categories", "parent_id", string="Child Categories")

    @property
    def full_name(self) -> str:
        """Get full category name including parent names."""
        if self.parent_id:
            return f"{self.parent_id.full_name} / {self.name}"
        return self.name


# Product model
class Product(CommonMixin):
    """Product model."""

    _collection = "products"
    _indexes = [
        {"keys": [("sku", 1)], "unique": True},
        {"keys": [("name", 1)]},
        {"keys": [("category_id", 1)]},
    ]

    name = fields.Char(string="Name", required=True, index=True)
    sku = fields.Char(string="SKU", required=True, unique=True)
    description = fields.Text(string="Description")
    price = fields.Float(string="Price", required=True)
    category_id = fields.Many2one("categories", string="Category", required=True)
    tag_ids = fields.Many2many("tags", string="Tags")
    image_url = fields.URL(string="Image URL")

    @property
    def category_name(self) -> str:
        """Get category name."""
        return self.category_id.name if self.category_id else ""

    def _validate_price(self):
        """Validate price is positive."""
        if self.price <= 0:
            raise ValueError("Price must be positive")

    _validators = [_validate_price]


# Tag model for products
class Tag(CommonMixin):
    """Tag model for products."""

    _collection = "tags"
    _indexes = [{"keys": [("name", 1)], "unique": True}]

    name = fields.Char(string="Name", required=True, unique=True)
    color = fields.Char(string="Color", default="#000000")
    product_ids = fields.Many2many("products", string="Products")


async def example_usage():
    """Example of using the models."""
    from earnorm import env

    # Create categories
    electronics = await env["categories"].create({"name": "Electronics"})

    phones = await env["categories"].create(
        {"name": "Phones", "parent_id": electronics.id}
    )

    # Create tags
    new_tag = await env["tags"].create({"name": "New", "color": "#ff0000"})

    sale_tag = await env["tags"].create({"name": "Sale", "color": "#00ff00"})

    # Create product
    iphone = await env["products"].create(
        {
            "name": "iPhone 15",
            "sku": "IP15-128",
            "price": 999.99,
            "category_id": phones.id,
            "tag_ids": [new_tag.id, sale_tag.id],
            "description": "Latest iPhone model",
            "image_url": "https://example.com/iphone15.jpg",
        }
    )

    # Get products in Electronics category and its subcategories
    electronics_products = await env["products"].search(
        [("category_id.parent_id", "=", electronics.id)]
    )

    # Get products with specific tag
    sale_products = await env["products"].search([("tag_ids", "in", [sale_tag.id])])

    # Archive old products
    old_products = await env["products"].search(
        [("created_at", "<", datetime(2023, 1, 1))]
    )
    await old_products.archive()

    # Print product info
    print(f"Product: {iphone.name}")
    print(f"Category: {iphone.category_name}")
    print(f"Full Category: {iphone.category_id.full_name}")
    print(f"Tags: {', '.join(tag.name for tag in iphone.tag_ids)}")
    print(f"Found {len(electronics_products)} products in Electronics category")
    print(f"Found {len(sale_products)} products on sale")
