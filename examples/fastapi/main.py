"""FastAPI example application."""

from contextlib import asynccontextmanager
from typing import List

from bson import ObjectId
from fastapi import FastAPI, HTTPException
from models import Post, PostCreate, PostResponse, User, UserCreate, UserResponse

from earnorm import init


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI."""
    await init(
        mongo_uri="mongodb://localhost:27017", database="earnorm_fastapi_example"
    )
    yield


# Create FastAPI app
app = FastAPI(title="EarnORM FastAPI Example", lifespan=lifespan)


# User endpoints
@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate):
    """Create a new user."""
    # Check if email exists
    existing = await User.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    new_user = User(name=user.name, email=user.email, age=user.age)

    await new_user.save()

    return new_user.to_response()


@app.get("/users/", response_model=List[UserResponse])
async def list_users():
    """List all users."""
    users = await User.find({})
    return [user.to_response() for user in users]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get a specific user."""
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.to_response()


# Post endpoints
@app.post("/posts/", response_model=PostResponse)
async def create_post(post: PostCreate):
    """Create a new post."""
    # Check if author exists
    author = await User.find_one({"_id": ObjectId(post.author_id)})
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    # Create post
    new_post = Post(title=post.title, content=post.content, author_id=author)
    await new_post.save()

    return new_post.to_response()


@app.get("/posts/", response_model=List[PostResponse])
async def list_posts():
    """List all posts."""
    posts = await Post.find({})
    return [post.to_response() for post in posts]


@app.get("/posts/{post_id}", response_model=PostResponse)
async def get_post(post_id: str):
    """Get a specific post."""
    post = await Post.find_one({"_id": ObjectId(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post.to_response()


@app.get("/users/{user_id}/posts", response_model=List[PostResponse])
async def get_user_posts(user_id: str):
    """Get all posts by a specific user."""
    user = await User.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    posts = await user.posts
    return [post.to_response() for post in posts]
