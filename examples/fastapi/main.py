"""FastAPI integration example."""

from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel as PydanticModel

import earnorm
from earnorm import BaseModel, Email, Int, String

app = FastAPI(title="EarnORM FastAPI Example")


class User(BaseModel):
    """User model."""

    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    name = String(required=True)
    email = Email(required=True, unique=True)
    age = Int(required=True)


class UserCreate(PydanticModel):
    """User creation schema."""

    name: str
    email: str
    age: int


class UserResponse(PydanticModel):
    """User response schema."""

    id: Optional[str] = None
    name: str
    email: str
    age: int


@app.on_event("startup")
async def startup():
    """Initialize EarnORM on startup."""
    await earnorm.init(
        mongo_uri="mongodb://localhost:27017",
        database="earnorm_example",
    )


@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user."""
    try:
        user_obj = User(**user.dict())
        await user_obj.save()
        return UserResponse(
            id=user_obj.id,
            name=user_obj.name,
            email=user_obj.email,
            age=user_obj.age,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users/", response_model=List[UserResponse])
async def list_users(age_gt: Optional[int] = None):
    """List all users with optional age filter."""
    domain = [("age", ">", age_gt)] if age_gt else None
    users = await User.search(domain)
    return [
        UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            age=user.age,
        )
        for user in users
    ]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        raise HTTPException(status_code=404, detail="User not found")
    record = user.ensure_one()
    return UserResponse(
        id=record.id,
        name=record.name,
        email=record.email,
        age=record.age,
    )


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    """Delete a user by ID."""
    user = await User.find_one([("_id", "=", user_id)])
    if not user.exists():
        raise HTTPException(status_code=404, detail="User not found")
    await user.unlink()
    return {"message": "User deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
