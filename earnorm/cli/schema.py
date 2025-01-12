"""Schema management commands."""

import asyncio

import click
from motor.motor_asyncio import AsyncIOMotorClient

from ..base.schema import schema_manager


@click.group()
def schema():
    """Schema management commands."""
    pass


@schema.command()
@click.option("--uri", default="mongodb://localhost:27017", help="MongoDB URI")
@click.option("--database", required=True, help="Database name")
def upgrade(uri: str, database: str):
    """Upgrade database schema."""
    # Create client
    client = AsyncIOMotorClient(uri)
    db = client[database]

    # Set database
    schema_manager.set_database(db)

    # Run upgrade
    try:
        click.echo("Upgrading schema...")
        asyncio.run(schema_manager.upgrade())
        click.echo("Schema upgrade completed.")
    except Exception as e:
        click.echo(f"Error upgrading schema: {e}", err=True)
    finally:
        client.close()


@schema.command()
@click.option("--uri", default="mongodb://localhost:27017", help="MongoDB URI")
@click.option("--database", required=True, help="Database name")
def info(uri: str, database: str):
    """Show schema information."""
    # Create client
    client = AsyncIOMotorClient(uri)
    db = client[database]

    # Set database
    schema_manager.set_database(db)

    # Show info
    try:
        click.echo("\nRegistered Models:")
        for collection, model in schema_manager._models.items():
            click.echo(f"\n{collection}:")
            click.echo("  Abstract:", getattr(model, "_abstract", False))

            if hasattr(model, "_indexes"):
                click.echo("\n  Indexes:")
                for index in model._indexes:
                    keys = ", ".join(f"{k[0]} ({k[1]})" for k in index["keys"])
                    unique = "UNIQUE " if index.get("unique") else ""
                    click.echo(f"    {unique}{keys}")
    except Exception as e:
        click.echo(f"Error getting schema info: {e}", err=True)
    finally:
        client.close()
