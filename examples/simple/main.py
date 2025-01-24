"""Simple example usage with detailed logging."""

import logging

from earnorm import fields
from earnorm.base.model import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model."""

    # Collection configuration
    _collection = "users"
    _name = "user"
    _indexes = [{"email": 1}]

    # Fields
    name = fields.StringField(required=True)
    email = fields.StringField(required=True, unique=True)
    age = fields.IntegerField(required=True)

    async def get_all_users(self):
        users = await User.search([])

        for user in users:
            print(user.name)
        return users
