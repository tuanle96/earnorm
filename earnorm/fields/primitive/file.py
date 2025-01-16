"""File field type using GridFS."""

import io
import mimetypes
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Type, Union

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorGridFSBucket
from pymongo.errors import PyMongoError

from earnorm.fields.base import Field
from earnorm.validators.types import ValidatorFunc


class GridFSError(PyMongoError):
    """GridFS operation error.

    This exception is raised when a GridFS operation fails, such as:
    - File upload fails
    - File download fails
    - File deletion fails
    - File info retrieval fails
    """


class FileField(Field[ObjectId]):
    """File field using GridFS.

    Examples:
        >>> class Document(BaseModel):
        ...     title = StringField()
        ...     file = FileField(allowed_types=["application/pdf"])
        ...
        >>> # Upload file
        >>> doc = Document(title="Report")
        >>> with open("report.pdf", "rb") as f:
        ...     await doc.file.save(f, filename="report.pdf")
        ...
        >>> # Download file
        >>> with open("downloaded.pdf", "wb") as f:
        ...     await doc.file.download(f)
        ...
        >>> # Get file info
        >>> info = await doc.file.get_info()
        >>> print(info.filename)
        'report.pdf'
        >>> print(info.content_type)
        'application/pdf'
        >>> print(info.length)
        12345
    """

    def __init__(
        self,
        *,
        required: bool = False,
        unique: bool = False,
        default: Any = None,
        validators: Optional[List[ValidatorFunc]] = None,
        allowed_types: Optional[List[str]] = None,
        max_size: Optional[int] = None,  # in bytes
        **kwargs: Any,
    ) -> None:
        """Initialize field.

        Args:
            required: Whether field is required
            unique: Whether field value must be unique
            default: Default value
            validators: List of validator functions
            allowed_types: List of allowed MIME types
            max_size: Maximum file size in bytes
        """
        super().__init__(
            required=required,
            unique=unique,
            default=default,
            validators=validators,
            **kwargs,
        )
        self.allowed_types = allowed_types
        self.max_size = max_size
        self._fs: Optional[AsyncIOMotorGridFSBucket] = None
        self._value: Optional[ObjectId] = None
        self._files: Optional[AsyncIOMotorCollection[Dict[str, Any]]] = None

    def _get_field_type(self) -> Type[Any]:
        """Get field type."""
        return ObjectId

    async def _get_fs(self) -> AsyncIOMotorGridFSBucket:
        """Get GridFS bucket."""
        if self._fs is None:
            from earnorm.di import container

            db = await container.get("db")
            self._fs = AsyncIOMotorGridFSBucket(db)
            # Get files collection
            self._files = AsyncIOMotorCollection(db, "fs.files")
        return self._fs

    def convert(self, value: Any) -> ObjectId:
        """Convert value to ObjectId."""
        if value is None:
            return ObjectId()
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    def to_mongo(self, value: Optional[ObjectId]) -> Optional[ObjectId]:
        """Convert Python ObjectId to MongoDB ObjectId."""
        return value

    def from_mongo(self, value: Any) -> ObjectId:
        """Convert MongoDB ObjectId to Python ObjectId."""
        if value is None:
            return ObjectId()
        if isinstance(value, ObjectId):
            return value
        return ObjectId(str(value))

    async def save(
        self,
        file: Union[BinaryIO, bytes, str, Path],
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
        **metadata: Any,
    ) -> ObjectId:
        """Save file to GridFS.

        Args:
            file: File to save (file object, bytes, string path or Path object)
            filename: Original filename
            content_type: MIME type of file
            **metadata: Additional metadata

        Returns:
            ObjectId of saved file

        Raises:
            ValueError: If file type is not allowed or file is too large
            GridFSError: If error occurs while saving file
        """
        fs = await self._get_fs()

        # Convert file to bytes
        if isinstance(file, (str, Path)):
            path = Path(file)
            if not path.exists():
                raise ValueError(f"File not found: {path}")
            with open(path, "rb") as f:
                data = f.read()
            filename = filename or str(path.name)
        elif isinstance(file, bytes):
            data = file
        else:
            data = file.read()

        # Validate file size
        if self.max_size and len(data) > self.max_size:
            raise ValueError(
                f"File size ({len(data)} bytes) exceeds maximum allowed size "
                f"({self.max_size} bytes)"
            )

        # Get content type
        if content_type is None and filename:
            content_type, _ = mimetypes.guess_type(filename)

        # Validate content type
        if (
            content_type
            and self.allowed_types
            and content_type not in self.allowed_types
        ):
            raise ValueError(
                f"File type {content_type} not allowed. "
                f"Allowed types: {', '.join(self.allowed_types)}"
            )

        try:
            file_id = await fs.upload_from_stream(
                filename=filename or "unnamed",
                source=data,
                metadata={
                    "content_type": content_type,
                    **metadata,
                },
            )
            return file_id
        except Exception as e:
            raise GridFSError(f"Error saving file: {e}") from e

    async def download(
        self,
        file: Optional[Union[BinaryIO, str, Path]] = None,
        chunk_size: int = 255 * 1024,  # 255KB
    ) -> Optional[bytes]:
        """Download file from GridFS.

        Args:
            file: File object or path to save to (if None, returns bytes)
            chunk_size: Size of chunks to read

        Returns:
            File contents as bytes if no file object provided

        Raises:
            GridFSError: If error occurs while downloading file
        """
        fs = await self._get_fs()
        file_id = self.convert(self._value)

        try:
            if file is None:
                # Return bytes
                buffer = io.BytesIO()
                await fs.download_to_stream(file_id, buffer)
                return buffer.getvalue()

            # Save to file
            if isinstance(file, (str, Path)):
                path = Path(file)
                with open(path, "wb") as f:
                    await fs.download_to_stream(file_id, f)
            else:
                await fs.download_to_stream(file_id, file)
            return None

        except Exception as e:
            raise GridFSError(f"Error downloading file: {e}") from e

    async def delete(self) -> None:
        """Delete file from GridFS.

        Raises:
            GridFSError: If error occurs while deleting file
        """
        fs = await self._get_fs()
        file_id = self.convert(self._value)

        try:
            await fs.delete(file_id)
        except Exception as e:
            raise GridFSError(f"Error deleting file: {e}") from e

    async def get_info(self) -> Optional[Dict[str, Any]]:
        """Get file information.

        Returns:
            Dict containing file information including:
            - filename: Original filename
            - content_type: MIME type
            - length: File size in bytes
            - upload_date: Upload timestamp
            - metadata: Additional metadata
            Or None if file not found

        Raises:
            GridFSError: If error occurs while getting file info
        """
        if self._files is None:
            _ = await self._get_fs()

        file_id = self.convert(self._value)
        try:
            if self._files is None:
                return None
            file_info: Optional[Dict[str, Any]] = await self._files.find_one(
                {"_id": file_id}
            )
            return file_info
        except Exception as e:
            raise GridFSError(f"Error getting file info: {e}") from e
