"""File field implementation.

This field type provides support for storing and managing files with proper validation.
It supports multiple storage backends:
- Local filesystem storage
- MongoDB GridFS storage
- Extensible for cloud storage

Features:
- File upload/download with streaming support
- Automatic content type detection
- File size validation
- MIME type validation
- Metadata management
- Async operations

Examples:
    Local storage:
    >>> class Document(Model):
    ...     title = StringField()
    ...     file = FileField(
    ...         storage="local",
    ...         upload_to="uploads/%Y/%m/%d/",
    ...         allowed_types=["application/pdf"],
    ...         max_size=10 * 1024 * 1024  # 10MB
    ...     )
    ...
    >>> # Upload file
    >>> doc = Document(title="Report")
    >>> await doc.file.save("report.pdf")
    >>> # Get file info
    >>> info = await doc.file.get_info()
    >>> print(info.path)
    'uploads/2024/03/21/report.pdf'

    GridFS storage:
    >>> class ImageDocument(Model):
    ...     name = StringField()
    ...     image = FileField(
    ...         storage="gridfs",
    ...         allowed_types=["image/jpeg", "image/png"],
    ...         max_size=5 * 1024 * 1024  # 5MB
    ...     )
    ...
    >>> # Upload with metadata
    >>> doc = ImageDocument(name="Profile")
    >>> await doc.image.save(
    ...     "profile.jpg",
    ...     metadata={"author": "John", "tags": ["profile", "avatar"]}
    ... )

Best Practices:
1. Always set appropriate max_size to prevent large file uploads
2. Use allowed_types to restrict file types for security
3. Handle storage-specific errors appropriately
4. Use streaming for large files
5. Clean up unused files by calling delete()
6. Add relevant metadata during upload
"""

import io
import mimetypes
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Set, Tuple, Union, cast

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from earnorm.fields.base import Field, ValidationError


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


class FileField(Field[Union[str, ObjectId]]):
    """Field for file storage with multiple backend support.

    This field handles:
    - File validation and storage
    - Multiple storage backends
    - Size and type validation
    - Metadata management
    - Streaming support

    Attributes:
        storage: Storage backend type ('local' or 'gridfs')
        upload_to: Upload directory template (for local storage)
        allowed_types: Set of allowed MIME types
        max_size: Maximum file size in bytes
        required: Whether field is required
        unique: Whether field value must be unique
        default: Default value

    Raises:
        ValidationError: With codes:
            - invalid_type: Value is not a valid file type
            - invalid_size: File exceeds maximum size
            - invalid_content_type: File type not allowed
            - file_not_found: File does not exist
            - storage_error: Storage backend error
    """

    def __init__(
        self,
        *,
        storage: Union[str, StorageType] = StorageType.LOCAL,
        upload_to: str = "",
        allowed_types: Optional[Set[str]] = None,
        max_size: Optional[int] = None,
        required: bool = False,
        unique: bool = False,
        **options: Any,
    ) -> None:
        """Initialize file field.

        Args:
            storage: Storage backend type ('local' or 'gridfs')
            upload_to: Upload directory template (for local storage)
            allowed_types: Set of allowed MIME types
            max_size: Maximum file size in bytes
            required: Whether field is required
            unique: Whether field value must be unique
            **options: Additional field options
        """
        super().__init__(
            required=required,
            unique=unique,
            **options,
        )
        self.storage = StorageType(storage)
        self.upload_to = upload_to
        self.allowed_types = allowed_types
        self.max_size = max_size
        self._fs: Optional[AsyncIOMotorGridFSBucket] = None
        self._value: Optional[Union[str, ObjectId]] = None

    async def validate(self, value: Any) -> None:
        """Validate file value.

        Validates:
        - Value is valid file path or ID
        - File exists in storage
        - Not None if required

        Args:
            value: Value to validate

        Raises:
            ValidationError: With codes:
                - invalid_type: Value is not a valid file type
                - file_not_found: File does not exist
                - required: Value is required but None
        """
        await super().validate(value)

        if value is not None:
            if self.storage == StorageType.LOCAL:
                if not isinstance(value, (str, Path)):
                    raise ValidationError(
                        message=f"Value must be string or Path, got {type(value).__name__}",
                        field_name=self.name,
                        code="invalid_type",
                    )
                path = Path(value)
                if not path.exists():
                    raise ValidationError(
                        message=f"File {path} does not exist",
                        field_name=self.name,
                        code="file_not_found",
                    )
            else:  # GridFS
                if not isinstance(value, (str, ObjectId)):
                    raise ValidationError(
                        message=f"Value must be string or ObjectId, got {type(value).__name__}",
                        field_name=self.name,
                        code="invalid_type",
                    )
                # GridFS existence check is done during operations

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
            ValidationError: With codes:
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
            raise ValidationError(
                message=f"File size {len(data)} bytes exceeds maximum {self.max_size} bytes",
                field_name=self.name,
                code="invalid_size",
            )

        # Validate content type
        if (
            content_type
            and self.allowed_types
            and content_type not in self.allowed_types
        ):
            raise ValidationError(
                message=f"Content type {content_type} not allowed. Allowed types: {', '.join(sorted(self.allowed_types))}",
                field_name=self.name,
                code="invalid_content_type",
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
            raise ValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            )

    async def read(
        self,
        chunk_size: int = 256 * 1024,  # 256KB
    ) -> Optional[bytes]:
        """Read file from storage.

        Args:
            chunk_size: Size of chunks to read

        Returns:
            File contents as bytes or None if file not found

        Raises:
            ValidationError: With code "storage_error" if read fails
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
                await fs.download_to_stream(ObjectId(self._value), buffer)
                return buffer.getvalue()
        except Exception as e:
            raise ValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            )

    async def delete(self) -> None:
        """Delete file from storage.

        Raises:
            ValidationError: With code "storage_error" if deletion fails
        """
        if self._value is None:
            return

        try:
            if self.storage == StorageType.LOCAL:
                os.unlink(str(self._value))
            else:
                fs = await self._get_fs()
                await fs.delete(ObjectId(self._value))
        except Exception as e:
            raise ValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            )

    async def get_info(self) -> Optional[FileInfo]:
        """Get file information.

        Returns:
            FileInfo object or None if file not found

        Raises:
            ValidationError: With code "storage_error" if info retrieval fails
        """
        if self._value is None:
            return None

        try:
            if self.storage == StorageType.LOCAL:
                path = Path(str(self._value))
                guess_result = cast(
                    Tuple[Optional[str], Optional[str]],
                    mimetypes.guess_type(str(path)),  # type: ignore
                )
                content_type = guess_result[0]
                return FileInfo(
                    filename=path.name,
                    path=str(path),
                    content_type=content_type,
                    size=path.stat().st_size,
                    created_at=datetime.fromtimestamp(path.stat().st_ctime),
                )
            else:
                fs = await self._get_fs()
                grid_out = await fs.open_download_stream(ObjectId(self._value))
                if grid_out.filename is None:
                    raise ValidationError(
                        message="File has no filename",
                        field_name=self.name,
                        code="invalid_file",
                    )
                metadata = grid_out.metadata or {}
                return FileInfo(
                    filename=grid_out.filename,
                    path=grid_out._id,
                    content_type=metadata.get("content_type"),
                    size=grid_out.length,
                    created_at=grid_out.upload_date,
                    metadata=dict(metadata),
                )
        except Exception as e:
            raise ValidationError(
                message=f"Storage error: {str(e)}",
                field_name=self.name,
                code="storage_error",
            )

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
                raise ValidationError(
                    message=f"File {path} does not exist",
                    field_name=self.name,
                    code="file_not_found",
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
        guess_result = cast(
            Tuple[Optional[str], Optional[str]], mimetypes.guess_type(filename)  # type: ignore
        )
        return guess_result[0]

    def _get_upload_path(self, filename: str) -> Path:
        """Get upload path for local storage."""
        if not self.upload_to:
            return Path(filename)

        # Format upload path with date placeholders
        upload_path = datetime.now().strftime(self.upload_to)
        return Path(upload_path) / filename
