"""Example of integrating EarnORM with Flask.

This example demonstrates:
1. Initializing EarnORM with Flask
2. Using Flask blueprints with EarnORM models
3. Creating REST API endpoints
4. Handling authentication and authorization
5. Using Flask-Marshmallow for serialization
"""

from datetime import datetime
from functools import wraps
from typing import List, Optional

from flask import Blueprint, Flask, g, jsonify, request
from flask_marshmallow import Marshmallow
from marshmallow import fields as ma_fields

from earnorm import BaseModel, env, fields
from earnorm.di import container

# Initialize Flask app
app = Flask(__name__)
ma = Marshmallow(app)


# EarnORM Models
class Product(BaseModel):
    """Product model."""

    _collection = "products"
    _indexes = [{"keys": [("sku", 1)], "unique": True}, {"keys": [("name", 1)]}]

    name = fields.Char(string="Name", required=True, index=True)
    sku = fields.Char(string="SKU", required=True, unique=True)
    description = fields.Text(string="Description")
    price = fields.Float(string="Price", required=True)
    active = fields.Boolean(string="Active", default=True)
    created_at = fields.DateTime(string="Created At", default=datetime.utcnow)
    updated_at = fields.DateTime(string="Updated At", default=datetime.utcnow)


# Marshmallow Schemas
class ProductSchema(ma.Schema):
    """Schema for product serialization."""

    id = ma_fields.String(dump_only=True)
    name = ma_fields.String(required=True)
    sku = ma_fields.String(required=True)
    description = ma_fields.String()
    price = ma_fields.Float(required=True)
    active = ma_fields.Boolean()
    created_at = ma_fields.DateTime(dump_only=True)
    updated_at = ma_fields.DateTime(dump_only=True)


# Initialize schemas
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)


# Create blueprint
products_bp = Blueprint("products", __name__)


def require_auth(f):
    """Decorator to require authentication."""

    @wraps(f)
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return jsonify({"error": "No authorization header"}), 401

        try:
            # In real app, verify token and get user
            token = auth_header.split(" ")[1]
            g.current_user = "verify_token_and_get_user(token)"
            return await f(*args, **kwargs)

        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401

    return decorated


@app.before_first_request
async def init_earnorm():
    """Initialize EarnORM before first request."""
    await container.init_resources(
        mongo_uri="mongodb://localhost:27017", database="earnorm_example"
    )


@app.teardown_appcontext
async def cleanup_earnorm(exception=None):
    """Cleanup EarnORM resources."""
    await container.cleanup()


@products_bp.route("/", methods=["GET"])
@require_auth
async def list_products():
    """List products with pagination and search."""
    # Get query parameters
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    search = request.args.get("search")

    # Build domain
    domain = [("active", "=", True)]
    if search:
        domain.extend(["|", ("name", "ilike", search), ("sku", "ilike", search)])

    # Get products
    products = await env["products"].search(
        domain=domain, offset=(page - 1) * per_page, limit=per_page, order="name asc"
    )

    # Get total count
    total = await env["products"].search_count(domain)

    # Serialize response
    data = products_schema.dump(products)

    return jsonify(
        {
            "items": data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    )


@products_bp.route("/", methods=["POST"])
@require_auth
async def create_product():
    """Create a new product."""
    # Validate input
    data = product_schema.load(request.get_json())

    try:
        # Check if SKU exists
        existing = await env["products"].search([("sku", "=", data["sku"])])
        if existing:
            return jsonify({"error": "SKU already exists"}), 400

        # Create product
        product = await env["products"].create(data)

        return jsonify(product_schema.dump(product)), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@products_bp.route("/<string:product_id>", methods=["GET"])
@require_auth
async def get_product(product_id):
    """Get product by ID."""
    try:
        product = await env["products"].get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        return jsonify(product_schema.dump(product))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@products_bp.route("/<string:product_id>", methods=["PUT"])
@require_auth
async def update_product(product_id):
    """Update product."""
    # Validate input
    data = product_schema.load(request.get_json())

    try:
        # Get product
        product = await env["products"].get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Check if SKU exists
        if data["sku"] != product.sku:
            existing = await env["products"].search(
                [("sku", "=", data["sku"]), ("id", "!=", product_id)]
            )
            if existing:
                return jsonify({"error": "SKU already exists"}), 400

        # Update product
        await product.write(data)

        return jsonify(product_schema.dump(product))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@products_bp.route("/<string:product_id>", methods=["DELETE"])
@require_auth
async def delete_product(product_id):
    """Delete product."""
    try:
        # Get product
        product = await env["products"].get(product_id)
        if not product:
            return jsonify({"error": "Product not found"}), 404

        # Delete product
        await product.unlink()

        return "", 204

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Register blueprint
app.register_blueprint(products_bp, url_prefix="/api/products")
