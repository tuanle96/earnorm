"""Example of integrating EarnORM with Django.

This example demonstrates:
1. Initializing EarnORM with Django
2. Using Django views with EarnORM models
3. Creating REST API endpoints
4. Handling authentication and authorization
5. Using Django REST framework for serialization
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from earnorm import BaseModel, env, fields
from earnorm.di import container


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


# Django REST framework Serializers
class ProductSerializer(serializers.Serializer):
    """Serializer for product model."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(required=True)
    sku = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.FloatField(required=True)
    active = serializers.BooleanField(default=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


# Django app config
class EarnORMConfig:
    """EarnORM app configuration."""

    name = "earnorm_example"
    verbose_name = "EarnORM Example"

    @classmethod
    async def ready(cls):
        """Initialize EarnORM when Django starts."""
        await container.init_resources(
            mongo_uri=settings.MONGODB_URI, database=settings.MONGODB_NAME
        )


# API Views
@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def list_products(request: Request) -> Response:
    """List products with pagination and search."""
    # Get query parameters
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 10))
    search = request.query_params.get("search")

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
    serializer = ProductSerializer(products, many=True)

    return Response(
        {
            "items": serializer.data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
async def create_product(request: Request) -> Response:
    """Create a new product."""
    # Validate input
    serializer = ProductSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        # Check if SKU exists
        existing = await env["products"].search(
            [("sku", "=", serializer.validated_data["sku"])]
        )
        if existing:
            return Response({"error": "SKU already exists"}, status=400)

        # Create product
        product = await env["products"].create(serializer.validated_data)

        return Response(ProductSerializer(product).data, status=201)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
async def get_product(request: Request, product_id: str) -> Response:
    """Get product by ID."""
    try:
        product = await env["products"].get(product_id)
        if not product:
            return Response({"error": "Product not found"}, status=404)

        return Response(ProductSerializer(product).data)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["PUT"])
@permission_classes([IsAuthenticated])
async def update_product(request: Request, product_id: str) -> Response:
    """Update product."""
    # Validate input
    serializer = ProductSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        # Get product
        product = await env["products"].get(product_id)
        if not product:
            return Response({"error": "Product not found"}, status=404)

        # Check if SKU exists
        if serializer.validated_data["sku"] != product.sku:
            existing = await env["products"].search(
                [
                    ("sku", "=", serializer.validated_data["sku"]),
                    ("id", "!=", product_id),
                ]
            )
            if existing:
                return Response({"error": "SKU already exists"}, status=400)

        # Update product
        await product.write(serializer.validated_data)

        return Response(ProductSerializer(product).data)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
async def delete_product(request: Request, product_id: str) -> Response:
    """Delete product."""
    try:
        # Get product
        product = await env["products"].get(product_id)
        if not product:
            return Response({"error": "Product not found"}, status=404)

        # Delete product
        await product.unlink()

        return Response(status=204)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


# URL patterns
urlpatterns = [
    path("products/", list_products, name="list_products"),
    path("products/", create_product, name="create_product"),
    path("products/<str:product_id>/", get_product, name="get_product"),
    path("products/<str:product_id>/", update_product, name="update_product"),
    path("products/<str:product_id>/", delete_product, name="delete_product"),
]
