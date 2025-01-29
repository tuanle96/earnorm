"""Script to update imports after moving types."""

import os


def update_file(file_path: str) -> None:
    """Update imports in a file.

    Args:
        file_path: Path to file to update
    """
    with open(file_path, "r") as f:
        content = f.read()

    # Update imports
    content = content.replace(
        "from earnorm.fields.types import", "from earnorm.types.fields import"
    )
    content = content.replace("from earnorm.types import", "from earnorm.types import")

    with open(file_path, "w") as f:
        f.write(content)


def main():
    """Main function."""
    # Get all Python files
    for root, _, files in os.walk("earnorm"):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                update_file(file_path)


if __name__ == "__main__":
    main()
