"""Example of integrating EarnORM with FastAPI.

This example demonstrates:
1. Initializing EarnORM with FastAPI
2. Using dependency injection for database access
3. Creating API endpoints with EarnORM models
4. Handling authentication and authorization
5. Using Pydantic models with EarnORM
"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel as PydanticModel

from earnorm import BaseModel, env, fields
from earnorm.di import container


# EarnORM Models
class User(BaseModel):
    """User model."""

    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True},
        {"keys": [("username", 1)], "unique": True},
    ]

    username = fields.Char(string="Username", required=True, unique=True)
    email = fields.Email(string="Email", required=True, unique=True)
    password = fields.Password(string="Password", required=True)
    name = fields.Char(string="Full Name", required=True)
    is_active = fields.Boolean(string="Active", default=True)


# Pydantic Models for API
class UserCreate(PydanticModel):
    """Schema for creating a user."""

    username: str
    email: str
    password: str
    name: str


class UserResponse(PydanticModel):
    """Schema for user response."""

    id: str
    username: str
    email: str
    name: str
    is_active: bool


# Create FastAPI app
app = FastAPI(title="EarnORM FastAPI Example")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
async def startup():
    """Initialize EarnORM on application startup."""
    await container.init_resources(
        mongo_uri="mongodb://localhost:27017", database="earnorm_example"
    )


@app.on_event("shutdown")
async def shutdown():
    """Cleanup EarnORM resources on application shutdown."""
    await container.cleanup()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from token.

    Args:
        token: JWT token from request

    Returns:
        User: Current user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # In real app, verify JWT token and get user ID
        user_id = "verify_token_and_get_user_id(token)"

        user = await env["users"].get(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate) -> dict:
    """Create a new user.

    Args:
        user_data: User data from request

    Returns:
        dict: Created user data

    Raises:
        HTTPException: If username or email already exists
    """
    try:
        # Check if username or email exists
        existing = await env["users"].search(
            [
                "|",
                ("username", "=", user_data.username),
                ("email", "=", user_data.email),
            ]
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already exists",
            )

        # Create user
        user = await env["users"].create(user_data.dict())

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> dict:
    """Get current user info.

    Args:
        current_user: Current user from token

    Returns:
        dict: User data
    """
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
    }


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> List[dict]:
    """List users with pagination and search.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        search: Search term for name or email
        current_user: Current user from token

    Returns:
        List[dict]: List of users
    """
    # Build domain
    domain = [("is_active", "=", True)]
    if search:
        domain.extend(["|", ("name", "ilike", search), ("email", "ilike", search)])

    # Get users
    users = await env["users"].search(
        domain=domain, offset=skip, limit=limit, order="name asc"
    )

    return [
        {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
        }
        for user in users
    ]


@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, user_data: UserCreate, current_user: User = Depends(get_current_user)
) -> dict:
    """Update user.

    Args:
        user_id: User ID to update
        user_data: New user data
        current_user: Current user from token

    Returns:
        dict: Updated user data

    Raises:
        HTTPException: If user not found or update fails
    """
    try:
        # Get user
        user = await env["users"].get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Check if username/email exists
        if user_data.username != user.username or user_data.email != user.email:
            existing = await env["users"].search(
                [
                    "|",
                    ("username", "=", user_data.username),
                    ("email", "=", user_data.email),
                    ("id", "!=", user_id),
                ]
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already exists",
                )

        # Update user
        await user.write(user_data.dict())

        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "is_active": user.is_active,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str, current_user: User = Depends(get_current_user)
) -> None:
    """Delete user.

    Args:
        user_id: User ID to delete
        current_user: Current user from token

    Raises:
        HTTPException: If user not found or delete fails
    """
    try:
        # Get user
        user = await env["users"].get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        # Delete user
        await user.unlink()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
