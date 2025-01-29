"""Script to fix MRO issues in field classes.

This script fixes Method Resolution Order issues by:
1. Moving Generic[T] to first position in inheritance list
2. Keeping BaseField[T] second
3. Keeping FieldComparisonMixin last
"""

import os
import re


def fix_class_definition(content: str) -> str:
    """Fix class definition to have correct MRO.

    Args:
        content: File content

    Returns:
        Fixed content
    """
    # Pattern to match class definitions with BaseField, Generic and FieldComparisonMixin
    pattern = r"class\s+(\w+)\s*\((BaseField\[[^\]]+\])\s*,\s*(Generic\[[^\]]+\])\s*,\s*(FieldComparisonMixin)\)"

    # Replace with correct order: Generic, BaseField, FieldComparisonMixin
    replacement = r"class \1(\3, \2, \4)"

    return re.sub(pattern, replacement, content)


def process_file(file_path: str) -> None:
    """Process a single file.

    Args:
        file_path: Path to file
    """
    print(f"Processing {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    # Fix class definitions
    new_content = fix_class_definition(content)

    # Only write if content changed
    if new_content != content:
        print(f"Fixing MRO in {file_path}")
        with open(file_path, "w") as f:
            f.write(new_content)


def main():
    """Main function."""
    # Paths to check
    paths = ["earnorm/fields/primitive", "earnorm/fields/composite"]

    # Process all Python files in paths
    for base_path in paths:
        if not os.path.exists(base_path):
            print(f"Path {base_path} does not exist")
            continue

        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    process_file(file_path)


if __name__ == "__main__":
    main()
