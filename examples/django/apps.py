"""Django example app configuration."""

from django.apps import AppConfig

from earnorm import init


class EarnORMConfig(AppConfig):
    """EarnORM Django app configuration."""

    name = "earnorm_django"
    verbose_name = "EarnORM Django Example"

    async def ready(self) -> None:
        """Initialize EarnORM when Django starts."""
        await init(
            mongo_uri="mongodb://localhost:27017", database="earnorm_django_example"
        )
