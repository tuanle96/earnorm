"""Example of initializing an EarnORM application with DI and Registry.

This example demonstrates:
1. Initializing the DI container
2. Configuring MongoDB connection
3. Accessing models through the registry
4. Using both concrete and abstract models
"""

import asyncio
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from earnorm import BaseModel, env
from earnorm.di import container


# Define an abstract model
class MailThread(BaseModel):
    """Abstract model for mail threading functionality."""

    _abstract = True

    async def send_mail(self, subject: str, body: str, to: str) -> None:
        """Send mail to recipient.

        Args:
            subject: Email subject
            body: Email body
            to: Recipient email
        """
        print(f"Sending mail to {to}: {subject}")
        # Actual mail sending logic would go here


# Define a concrete model that inherits from MailThread
class User(MailThread):
    """User model with mail threading capability."""

    _collection = "users"
    _indexes = [
        {"keys": [("email", 1)], "unique": True},
        {"keys": [("username", 1)], "unique": True},
    ]

    async def welcome_email(self) -> None:
        """Send welcome email to user."""
        await self.send_mail(
            subject="Welcome to EarnORM",
            body="Thank you for registering!",
            to=self.email,
        )


async def main():
    # Initialize container with MongoDB connection
    await container.init_resources(
        mongo_uri="mongodb://localhost:27017", database="earnorm_example"
    )

    try:
        # Access concrete model through registry
        users = env["users"]

        # Create a new user
        user = await users.create(
            {"username": "john_doe", "email": "john@example.com", "name": "John Doe"}
        )

        # Send welcome email using inherited mail thread functionality
        await user.welcome_email()

        # Access abstract model through registry
        mail_thread = env["mail.thread"]

        # Use abstract model functionality directly
        await mail_thread.send_mail(
            subject="Test Email", body="This is a test", to="test@example.com"
        )

        # Query users
        active_users = await users.search([("active", "=", True)])
        print(f"Found {len(active_users)} active users")

    finally:
        # Cleanup resources
        await container.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
