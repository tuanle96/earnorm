"""MongoDB transaction implementation.

This module provides MongoDB-specific transaction implementation.

Examples:
    >>> with adapter.transaction(User) as tx:
    ...     user = User(name="John", age=25)
    ...     tx.insert(user)
    ...     tx.update(user)
    ...     tx.delete(user)
    ...     tx.commit()
"""

from types import TracebackType
from typing import Any, Dict, List, Optional, Type, TypeVar

from bson import ObjectId
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError
from pymongo.mongo_client import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import ReadPreference
from pymongo.write_concern import WriteConcern

from earnorm.base.database.transaction.base import (
    Transaction,
    TransactionError,
    TransactionManager,
)
from earnorm.types import DatabaseModel

ModelT = TypeVar("ModelT", bound=DatabaseModel)


class MongoTransactionError(TransactionError):
    """MongoDB-specific transaction error."""

    pass


class MongoTransaction(Transaction[ModelT]):
    """MongoDB transaction implementation."""

    def __init__(
        self, collection: Collection[Dict[str, Any]], session: ClientSession
    ) -> None:
        """Initialize transaction.

        Args:
            collection: MongoDB collection
            session: MongoDB session
        """
        self._collection = collection
        self._session = session

    def __enter__(self) -> "MongoTransaction[ModelT]":
        """Enter transaction context.

        Returns:
            Transaction instance
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """Exit transaction context.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        try:
            if exc_type is not None:
                self.rollback()
            else:
                self.commit()
        finally:
            self._session.end_session()

    def insert(self, model: ModelT) -> ModelT:
        """Insert model into database.

        Args:
            model: Model to insert

        Returns:
            Inserted model with ID

        Raises:
            MongoTransactionError: If model cannot be inserted
        """
        try:
            result = self._collection.insert_one(model.to_dict(), session=self._session)
            model.id = result.inserted_id
            return model
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to insert model: {e}") from e

    def insert_many(self, models: List[ModelT]) -> List[ModelT]:
        """Insert multiple models into database.

        Args:
            models: Models to insert

        Returns:
            Inserted models with IDs

        Raises:
            MongoTransactionError: If models cannot be inserted
        """
        try:
            result = self._collection.insert_many(
                [model.to_dict() for model in models], session=self._session
            )
            for model, id_ in zip(models, result.inserted_ids):
                model.id = id_
            return models
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to insert models: {e}") from e

    def update(self, model: ModelT) -> ModelT:
        """Update model in database.

        Args:
            model: Model to update

        Returns:
            Updated model

        Raises:
            ValueError: If model has no ID
            MongoTransactionError: If model cannot be updated
        """
        if not model.id:
            raise ValueError("Model has no ID")
        try:
            self._collection.update_one(
                {"_id": model.id}, {"$set": model.to_dict()}, session=self._session
            )
            return model
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to update model: {e}") from e

    def update_many(self, models: List[ModelT]) -> List[ModelT]:
        """Update multiple models in database.

        Args:
            models: Models to update

        Returns:
            Updated models

        Raises:
            ValueError: If any model has no ID
            MongoTransactionError: If models cannot be updated
        """
        try:
            for model in models:
                if not model.id:
                    raise ValueError("Model has no ID")
                self._collection.update_one(
                    {"_id": model.id}, {"$set": model.to_dict()}, session=self._session
                )
            return models
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to update models: {e}") from e

    def delete(self, model: ModelT) -> None:
        """Delete model from database.

        Args:
            model: Model to delete

        Raises:
            ValueError: If model has no ID
            MongoTransactionError: If model cannot be deleted
        """
        if not model.id:
            raise ValueError("Model has no ID")
        try:
            self._collection.delete_one({"_id": model.id}, session=self._session)
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to delete model: {e}") from e

    def delete_many(self, models: List[ModelT]) -> None:
        """Delete multiple models from database.

        Args:
            models: Models to delete

        Raises:
            ValueError: If any model has no ID
            MongoTransactionError: If models cannot be deleted
        """
        try:
            ids: List[ObjectId] = []
            for model in models:
                if not model.id:
                    raise ValueError("Model has no ID")
                ids.append(model.id)
            self._collection.delete_many({"_id": {"$in": ids}}, session=self._session)
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to delete models: {e}") from e

    def commit(self) -> None:
        """Commit transaction.

        Raises:
            MongoTransactionError: If transaction cannot be committed
        """
        try:
            self._session.commit_transaction()
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to commit transaction: {e}") from e

    def rollback(self) -> None:
        """Rollback transaction.

        Raises:
            MongoTransactionError: If transaction cannot be rolled back
        """
        try:
            self._session.abort_transaction()
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to rollback transaction: {e}") from e


class MongoTransactionManager(TransactionManager[ModelT]):
    """MongoDB transaction manager."""

    def __init__(self, db: Database[Dict[str, Any]]) -> None:
        """Initialize transaction manager.

        Args:
            db: MongoDB database instance
        """
        super().__init__()
        self._db = db
        self._model_type: Optional[Type[ModelT]] = None

    def set_model_type(self, model_type: Type[ModelT]) -> None:
        """Set model type for transaction.

        This method must be called before starting a transaction.
        It sets the type of model that will be used in the transaction.

        Args:
            model_type: Type of model to use in transaction
        """
        self._model_type = model_type

    def _begin_transaction(self) -> Transaction[ModelT]:
        """Begin new transaction.

        Returns:
            Transaction instance

        Raises:
            MongoTransactionError: If transaction cannot be started
            ValueError: If model type is not set
        """
        if self._model_type is None:
            raise ValueError("Model type not set")

        try:
            client: MongoClient[Dict[str, Any]] = self._db.client
            session = client.start_session()
            # Ignore type error from pymongo's incomplete type hints
            session.start_transaction(  # type: ignore
                read_concern=ReadConcern(),
                write_concern=WriteConcern(),
                read_preference=ReadPreference.PRIMARY,
                max_commit_time_ms=None,
            )
            collection = self._db[self._model_type.__collection__]
            return MongoTransaction(collection, session)
        except PyMongoError as e:
            raise MongoTransactionError(f"Failed to start transaction: {e}") from e
