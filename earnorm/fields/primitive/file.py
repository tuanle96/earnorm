"""File field implementation.

This module provides file field type for handling file uploads and storage.
It supports:
- File validation
- Size limits
- MIME type validation
- Storage backends
- Database type mapping
- File comparison operations

Examples:
    >>> class Document(Model):
    ...     file = FileField(
    ...         max_size=10 * 1024 * 1024,  # 10MB
    ...         allowed_types=["application/pdf", "image/*"],
    ...     )
    ...     image = FileField(
    ...         max_size=5 * 1024 * 1024,  # 5MB
    ...         allowed_types=["image/jpeg", "image/png"],
    ...     )
    ...
    ...     # Query examples
    ...     large_files = Document.find(Document.file.size_greater_than(5 * 1024 * 1024))
    ...     pdfs = Document.find(Document.file.has_type("application/pdf"))
    ...     recent = Document.find(Document.file.created_after(datetime(2024, 1, 1)))
"""

import io
import mimetypes
import os
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Sequence, Union, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from earnorm.exceptions import FieldValidationError
from earnorm.fields.base import BaseField
from earnorm.types.fields import ComparisonOperator, DatabaseValue, FieldComparisonMixin
from earnorm.fields.validators.base import TypeValidator, Validator


class StorageType(str, Enum):
    """Storage backend types."""

    LOCAL = "local"  # Local filesystem
    GRIDFS = "gridfs"  # MongoDB GridFS


class FileInfo:
    """File information container.

    Attributes:
        filename: Original filename
        path: Storage path or ID
        content_type: MIME type
        size: File size in bytes
        created_at: Creation timestamp
        metadata: Additional metadata
    """

    def __init__(
        self,
        filename: str,
        path: Union[str, ObjectId],
        content_type: Optional[str] = None,
        size: Optional[int] = None,
        created_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.filename = filename
        self.path = path
        self.content_type = content_type
        self.size = size
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}


class FileField(BaseField[Union[Path, str, ObjectId]], FieldComparisonMixin):
    """Field for file uploads.

    This field type handles file uploads, with support for:
    - File validation
    - Size limits
    - MIME type validation
    - Storage backends
    - Database type mapping
    - File comparison operations

    Attributes:
        max_size: Maximum file size in bytes
        allowed_types: List of allowed MIME types (with wildcards)
        upload_to: Upload directory path
        backend_options: Database backend options
        storage: Storage backend type
        _value: Current file value
        _fs: GridFS bucket instance
    """

    max_size: int
    allowed_types: tuple[str, ...]
    upload_to: str
    backend_options: dict[str, Any]
    storage: StorageType
    _value: Optional[Union[Path, str, ObjectId]]
    _fs: Optional[AsyncIOMotorGridFSBucket]

    def __init__(
        self,
        *,
        storage: Union[str, StorageType] = StorageType.LOCAL,
        max_size: int = 100 * 1024 * 1024,  # 100MB
        allowed_types: Optional[Sequence[str]] = None,
        upload_to: str = "uploads",
        **options: Any,
    ) -> None:
        """Initialize file field.

        Args:
            storage: Storage backend type
            max_size: Maximum file size in bytes
            allowed_types: List of allowed MIME types (with wildcards)
            upload_to: Upload directory path
            **options: Additional field options

        Raises:
            ValueError: If max_size is negative or allowed_types is invalid
        """
        if max_size < 0:
            raise ValueError("max_size must be non-negative")

        field_validators: list[Validator[Any]] = [TypeValidator(Path)]
        super().__init__(validators=field_validators, **options)

        self.storage = StorageType(storage)
        self.max_size = max_size
        self.allowed_types = tuple(allowed_types or ("*/*",))
        self.upload_to = upload_to
        self._value = None
        self._fs = None

        # Create upload directory if it doesn't exist
        if self.storage == StorageType.LOCAL:
            os.makedirs(upload_to, exist_ok=True)

        # Initialize backend options
        self.backend_options = {
            "mongodb": {"type": "string"},
            "postgres": {"type": "VARCHAR"},
            "mysql": {"type": "VARCHAR(255)"},
        }

    def _is_mime_type_allowed(self, mime_type: str) -> bool:
        """Check if MIME type is allowed.

        Supports wildcards in allowed types (e.g., "image/*").

        Args:
            mime_type: MIME type to check

        Returns:
            Whether MIME type is allowed
        """
        if "*/*" in self.allowed_types:
            return True

        mime_category, mime_subtype = mime_type.split("/", 1)
        for allowed_type in self.allowed_types:
            allowed_category, allowed_subtype = allowed_type.split("/", 1)
            if allowed_category == "*" or (
                allowed_category == mime_category
                and (allowed_subtype == "*" or allowed_subtype == mime_subtype)
            ):
                return True
        return False

    async def validate(self, value: Any) -> None:
        """Validate file value.

        This method validates:
        - Value is Path type
        - File exists
        - File size is within limit
        - File type is allowed

        Args:
            value: Value to validate

        Raises:
            FieldValidationError: If validation fails
        """
        await super().validate(value)

        if value is not None:
            if not isinstance(value, Path):
                raise FieldValidationError(
                    message=f"Value must be a Path, got {type(value).__name__}",
                    field_name=self.name,
                    code="invalid_type",
                )

            # Check if file exists
            if not value.is_file():
                raise FieldValidationError(
                    message=f"File does not exist: {value}",
                    field_name=self.name,
                    code="file_not_found",
                )

            # Check file size
            file_size = value.stat().st_size
            if file_size > self.max_size:
                raise FieldValidationError(
                    message=(
                        f"File size {file_size} bytes exceeds maximum "
                        f"size of {self.max_size} bytes"
                    ),
                    field_name=self.name,
                    code="file_too_large",
                )

            # Check MIME type
            mime_type, _ = mimetypes.guess_type(value)
            if mime_type is None:
                raise FieldValidationError(
                    message=f"Cannot determine MIME type for file: {value}",
                    field_name=self.name,
                    code="unknown_mime_type",
                )

            if not self._is_mime_type_allowed(mime_type):
                raise FieldValidationError(
                    message=(
                        f"File type {mime_type} is not allowed. "
                        f"Allowed types: {self.allowed_types}"
                    ),
                    field_name=self.name,
                    code="invalid_mime_type",
                )

    async def convert(self, value: Any) -> Optional[Path]:
        """Convert value to Path.

        Handles:
        - None values
        - Path instances
        - String values (file paths)

        Args:
            value: Value to convert

        Returns:
            Converted Path value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, Path):
                return value
            elif isinstance(value, str):
                return Path(value)
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to Path")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert value to Path: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def to_db(
        self, value: Optional[Union[Path, str, ObjectId]], backend: str
    ) -> DatabaseValue:
        """Convert file path to database format.

        Args:
            value: Path/ID value to convert
            backend: Database backend type

        Returns:
            Converted path/ID value or None
        """
        if value is None:
            return None

        if isinstance(value, (str, ObjectId)):
            return value  # type: ignore

        # Store relative path from upload directory
        try:
            relative_path = value.relative_to(self.upload_to)
            return str(relative_path)
        except ValueError:
            return str(value)

    async def from_db(
        self, value: DatabaseValue, backend: str
    ) -> Optional[Union[Path, str, ObjectId]]:
        """Convert database value to file path/ID.

        Args:
            value: Database value to convert
            backend: Database backend type

        Returns:
            Converted Path/ID value or None

        Raises:
            FieldValidationError: If value cannot be converted
        """
        if value is None:
            return None

        try:
            if isinstance(value, (str, ObjectId)):
                if self.storage == StorageType.LOCAL:
                    # Combine upload directory with stored path
                    return Path(self.upload_to) / str(value)
                return value
            elif isinstance(value, Path):
                return value
            else:
                raise TypeError(f"Cannot convert {type(value).__name__} to Path/ID")
        except (TypeError, ValueError) as e:
            raise FieldValidationError(
                message=f"Cannot convert database value to Path/ID: {str(e)}",
                field_name=self.name,
                code="conversion_error",
            ) from e

    async def save(
        self,
        file: Union[BinaryIO, bytes, str, Path],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[str, ObjectId]:
        """Save file to storage.

        Args:
            file: File to save (file object, bytes, string path or Path object)
            filename: Original filename
            content_type: MIME type of file
            metadata: Additional metadata

        Returns:
            File path (local) or ID (GridFS)

        Raises:
            FieldValidationError: With codes:
                - invalid_size: File exceeds maximum size
                - invalid_content_type: File type not allowed
                - storage_error: Storage backend error
        """
        # Convert file to bytes and validate
        data = await self._read_file(file)
        filename = filename or self._get_filename(file)
        content_type = content_type or self._guess_content_type(filename)

        # Validate size
        if self.max_size and len(data) > self.max_size:
            raise FieldValidationError(
                message=f"File size {len(data)} bytes exceeds maximum {self.max_size} bytes",
                field_name=self.name,
            )

        # Validate content type
        allowed = self.allowed_types
        if (
            content_type
            and allowed
            and content_type
            not in allowed  # pylint: disable=unsupported-membership-test
        ):
            raise FieldValidationError(
                message=f"Content type {content_type} not allowed. Allowed \
                types: {', '.join(sorted(allowed))}",
                field_name=self.name,
            )

        try:
            if self.storage == StorageType.LOCAL:
                # Save to local filesystem
                path = self._get_upload_path(filename)
                os.makedirs(path.parent, exist_ok=True)
                with open(path, "wb") as f:
                    f.write(data)
                return str(path)
            else:
                # Save to GridFS
                fs = await self._get_fs()
                file_id = await fs.upload_from_stream(
                    filename=filename,
                    source=data,
                    metadata={
                        "content_type": content_type,
                        **(metadata or {}),
                    },
                )
                return file_id
        except Exception as e:
            raise FieldValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
            ) from e

    async def read(self) -> Optional[bytes]:
        """Read file from storage.

        Returns:
            File contents as bytes or None if file not found

        Raises:
            FieldValidationError: With code "storage_error" if read fails
        """
        if self._value is None:
            return None

        try:
            if self.storage == StorageType.LOCAL:
                with open(str(self._value), "rb") as f:
                    return f.read()
            else:
                fs = await self._get_fs()
                buffer = io.BytesIO()
                await fs.download_to_stream(
                    cast(Union[str, ObjectId, bytes], self._value), buffer
                )
                return buffer.getvalue()
        except Exception as e:
            raise FieldValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            ) from e

    async def delete(self) -> None:
        """Delete file from storage.

        Raises:
            FieldValidationError: With code "storage_error" if deletion fails
        """
        if self._value is None:
            return

        try:
            if self.storage == StorageType.LOCAL:
                os.unlink(str(self._value))
            else:
                fs = await self._get_fs()
                await fs.delete(cast(Union[str, ObjectId, bytes], self._value))
        except Exception as e:
            raise FieldValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            ) from e

    async def get_info(self) -> Optional[FileInfo]:
        """Get file information.

        Returns:
            FileInfo object or None if file not found

        Raises:
            FieldValidationError: With code "storage_error" if info retrieval fails
        """
        if self._value is None:
            return None

        try:
            if self.storage == StorageType.LOCAL:
                path = Path(str(self._value))
                mime_type, _ = mimetypes.guess_type(str(path))
                return FileInfo(
                    filename=path.name,
                    path=str(path),
                    content_type=mime_type,
                    size=path.stat().st_size,
                    created_at=datetime.fromtimestamp(path.stat().st_ctime),
                )
            else:
                fs = await self._get_fs()
                grid_out = await fs.open_download_stream(
                    cast(Union[str, ObjectId, bytes], self._value)
                )
                if grid_out.filename is None:
                    raise FieldValidationError(
                        message="File has no filename",
                        field_name=self.name,
                        code="missing_filename",
                    )
                metadata = grid_out.metadata or {}
                return FileInfo(
                    filename=grid_out.filename,
                    path=grid_out._id,  # pylint: disable=protected-access
                    content_type=metadata.get("content_type"),
                    size=grid_out.length,
                    created_at=grid_out.upload_date,
                    metadata=dict(metadata),
                )
        except Exception as e:
            raise FieldValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            ) from e

    async def _get_fs(self) -> AsyncIOMotorGridFSBucket:
        """Get GridFS bucket for MongoDB storage."""
        if self._fs is None:
            from earnorm.di import container

            db = await container.get("db")
            self._fs = AsyncIOMotorGridFSBucket(db)
        return self._fs

    async def _read_file(self, file: Union[BinaryIO, bytes, str, Path]) -> bytes:
        """Read file content to bytes."""
        if isinstance(file, (str, Path)):
            path = Path(file)
            if not path.exists():
                raise FieldValidationError(
                    message=f"File {path} does not exist",
                    field_name=self.name,
                )
            with open(path, "rb") as f:
                return f.read()
        elif isinstance(file, bytes):
            return file
        else:
            return file.read()

    def _get_filename(self, file: Union[BinaryIO, bytes, str, Path]) -> str:
        """Get original filename from file object."""
        if isinstance(file, (str, Path)):
            return Path(file).name
        elif isinstance(file, bytes):
            return "unnamed"
        elif hasattr(file, "name"):
            name = getattr(file, "name", None)
            if isinstance(name, str):
                return Path(name).name
        return "unnamed"

    def _guess_content_type(self, filename: str) -> Optional[str]:
        """Guess MIME type from filename.

        Args:
            filename: Name of file to check

        Returns:
            MIME type string or None if cannot be determined
        """
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type

    def _get_upload_path(self, filename: str) -> Path:
        """Get upload path for local storage."""
        if not self.upload_to:
            return Path(filename)

        # Format upload path with date placeholders
        upload_path = datetime.now().strftime(self.upload_to)
        return Path(upload_path) / filename

    def _prepare_value(self, value: Any) -> DatabaseValue:
        """Prepare file value for comparison.

        Converts file path/ID to string for database comparison.

        Args:
            value: Value to prepare

        Returns:
            Prepared file value or None
        """
        if value is None:
            return None

        try:
            if isinstance(value, (str, ObjectId)):
                return str(value)
            elif isinstance(value, Path):
                return str(value)
            return None
        except (TypeError, ValueError):
            return None

    def size_equals(self, size: int) -> ComparisonOperator:
        """Check if file size equals value.

        Args:
            size: Size in bytes to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "size_eq", size)

    def size_greater_than(self, size: int) -> ComparisonOperator:
        """Check if file size is greater than value.

        Args:
            size: Size in bytes to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "size_gt", size)

    def size_less_than(self, size: int) -> ComparisonOperator:
        """Check if file size is less than value.

        Args:
            size: Size in bytes to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "size_lt", size)

    def has_type(self, mime_type: str) -> ComparisonOperator:
        """Check if file has specific MIME type.

        Supports wildcards (e.g., "image/*").

        Args:
            mime_type: MIME type to check

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "mime_type", mime_type)

    def created_before(self, date: datetime) -> ComparisonOperator:
        """Check if file was created before date.

        Args:
            date: Date to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "created_before", date.isoformat())

    def created_after(self, date: datetime) -> ComparisonOperator:
        """Check if file was created after date.

        Args:
            date: Date to compare with

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "created_after", date.isoformat())

    def created_between(self, start: datetime, end: datetime) -> ComparisonOperator:
        """Check if file was created between dates.

        Args:
            start: Start date
            end: End date

        Returns:
            ComparisonOperator: Comparison operator with field name and values
        """
        return ComparisonOperator(
            self.name, "created_between", [start.isoformat(), end.isoformat()]
        )

    def created_days_ago(self, days: int) -> ComparisonOperator:
        """Check if file was created within last N days.

        Args:
            days: Number of days to look back

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        date = datetime.now() - timedelta(days=days)
        return self.created_after(date)

    def has_extension(self, extension: str) -> ComparisonOperator:
        """Check if file has specific extension.

        Args:
            extension: File extension to check (without dot)

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "extension", extension.lower())

    def in_directory(self, directory: str) -> ComparisonOperator:
        """Check if file is in specific directory.

        Args:
            directory: Directory path to check

        Returns:
            ComparisonOperator: Comparison operator with field name and value
        """
        return ComparisonOperator(self.name, "directory", directory)

    def exists(self) -> ComparisonOperator:
        """Check if file exists in storage.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "exists", None)

    def not_exists(self) -> ComparisonOperator:
        """Check if file does not exist in storage.

        Returns:
            ComparisonOperator: Comparison operator with field name
        """
        return ComparisonOperator(self.name, "not_exists", None)
