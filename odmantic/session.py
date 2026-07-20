from __future__ import annotations

from abc import ABCMeta
from types import TracebackType
from typing import (
    Any,
    AsyncContextManager,
    ContextManager,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

from motor.motor_asyncio import AsyncIOMotorClientSession
from pymongo.client_session import ClientSession

import odmantic.engine as ODMEngine
from odmantic.query import QueryExpression


class AIOSessionBase(metaclass=ABCMeta):
    engine: ODMEngine.AIOEngine

    def find(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[
            QueryExpression, Dict, bool
        ],  # bool: allow using binary operators with mypy
        sort: Optional[Any] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> ODMEngine.AIOCursor[ODMEngine.ModelType]:
        """Search for Model instances matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            sort: sort expression
            skip: number of document to skip
            limit: maximum number of instance fetched

        Returns:
            [odmantic.engine.AIOCursor][] of the query

        """
        return self.engine.find(
            model,
            *queries,
            sort=sort,
            skip=skip,
            limit=limit,
            session=self.engine._get_session(self),
        )

    async def find_one(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[
            QueryExpression, Dict, bool
        ],  # bool: allow using binary operators w/o plugin
        sort: Optional[Any] = None,
    ) -> Optional[ODMEngine.ModelType]:
        """Search for a Model instance matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            sort: sort expression

        Raises:
            DocumentParsingError: unable to parse the resulting document

        Returns:
            the fetched instance if found otherwise None

        <!---
        #noqa: DAR402 DocumentParsingError
        -->
        """
        return await self.engine.find_one(
            model, *queries, sort=sort, session=self.engine._get_session(self)
        )

    async def count(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[QueryExpression, Dict, bool],
    ) -> int:
        """Get the count of documents matching a query

        Args:
            model: model to perform the operation on
            *queries: query filters to apply

        Returns:
            number of document matching the query
        """
        return await self.engine.count(
            model, *queries, session=self.engine._get_session(self)
        )

    async def save(
        self,
        instance: ODMEngine.ModelType,
    ) -> ODMEngine.ModelType:
        """Persist an instance to the database

        This method behaves as an 'upsert' operation. If a document already exists
        with the same primary key, it will be overwritten.

        All the other models referenced by this instance will be saved as well.

        Args:
            instance: instance to persist

        Returns:
            the saved instance

        NOTE:
            The save operation actually modify the instance argument in place. However,
            the instance is still returned for convenience.
        """
        return await self.engine.save(instance, session=self.engine._get_session(self))

    async def save_all(
        self,
        instances: Sequence[ODMEngine.ModelType],
    ) -> List[ODMEngine.ModelType]:
        """Persist instances to the database

        This method behaves as multiple 'upsert' operations. If one of the document
        already exists with the same primary key, it will be overwritten.

        All the other models referenced by this instance will be recursively saved as
        well.

        Args:
            instances: instances to persist

        Returns:
            the saved instances

        NOTE:
            The save_all operation actually modify the arguments in place. However, the
            instances are still returned for convenience.
        """
        return await self.engine.save_all(
            instances, session=self.engine._get_session(self)
        )

    async def delete(
        self,
        instance: ODMEngine.ModelType,
    ) -> None:
        """Delete an instance from the database

        Args:
            instance: the instance to delete

        Raises:
            DocumentNotFoundError: the instance has not been persisted to the database

        <!---
        #noqa: DAR402 DocumentNotFoundError
        #noqa: DAR201
        -->
        """
        return await self.engine.delete(
            instance, session=self.engine._get_session(self)
        )

    async def remove(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[QueryExpression, Dict, bool],
        just_one: bool = False,
    ) -> int:
        """Delete Model instances matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            just_one: limit the deletion to just one document

        Returns:
            the number of instances deleted from the database.
        """
        return await self.engine.remove(
            model, *queries, just_one=just_one, session=self.engine._get_session(self)
        )


class AIOSession(AIOSessionBase, AsyncContextManager):

    def __init__(self, engine: ODMEngine.AIOEngine):
        self.engine = engine
        self.session: Optional[AsyncIOMotorClientSession] = None

    @property
    def is_started(self) -> bool:
        pass

    def get_driver_session(self) -> AsyncIOMotorClientSession:
        """Return the underlying Motor Session"""
        if self.session is None:
            raise RuntimeError("session not started")
        return self.session

    async def start(self) -> None:
        pass

    async def end(self) -> None:
        pass

    async def __aenter__(self) -> "AIOSession":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.end()

    def transaction(self) -> AIOTransaction:
        pass


class AIOTransaction(AIOSessionBase, AsyncContextManager):

    def __init__(self, context: Union[ODMEngine.AIOEngine, ODMEngine.AIOSession]):
        self._session_provided = isinstance(context, ODMEngine.AIOSession)
        if self._session_provided:
            assert isinstance(context, ODMEngine.AIOSession)
            if not context.is_started:
                raise RuntimeError("provided session is not started")
            self.session = context
            self.engine = context.engine
        else:
            assert isinstance(context, ODMEngine.AIOEngine)
            self.session = AIOSession(context)
            self.engine = context

        self._transaction_started = False
        self._transaction_context: Optional[AsyncContextManager] = None

    def get_driver_session(self) -> AsyncIOMotorClientSession:
        """Return the underlying Motor Session"""
        if not self._transaction_started:
            raise RuntimeError("transaction not started")
        return self.session.get_driver_session()

    async def start(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def abort(self) -> None:
        pass

    async def __aenter__(self) -> "AIOTransaction":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        assert self._transaction_context is not None
        await self._transaction_context.__aexit__(exc_type, exc, traceback)
        self._transaction_started = False


class SyncSessionBase(metaclass=ABCMeta):
    engine: ODMEngine.SyncEngine

    def find(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[
            QueryExpression, Dict, bool
        ],  # bool: allow using binary operators with mypy
        sort: Optional[Any] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> ODMEngine.SyncCursor[ODMEngine.ModelType]:
        """Search for Model instances matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            sort: sort expression
            skip: number of document to skip
            limit: maximum number of instance fetched

        Returns:
            [odmantic.engine.SyncCursor][] of the query

        """
        return self.engine.find(
            model,
            *queries,
            sort=sort,
            skip=skip,
            limit=limit,
            session=self.engine._get_session(self),
        )

    def find_one(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[
            QueryExpression, Dict, bool
        ],  # bool: allow using binary operators w/o plugin
        sort: Optional[Any] = None,
    ) -> Optional[ODMEngine.ModelType]:
        """Search for a Model instance matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            sort: sort expression

        Raises:
            DocumentParsingError: unable to parse the resulting document

        Returns:
            the fetched instance if found otherwise None

        <!---
        #noqa: DAR402 DocumentParsingError
        -->
        """
        return self.engine.find_one(
            model, *queries, sort=sort, session=self.engine._get_session(self)
        )

    def count(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[QueryExpression, Dict, bool],
    ) -> int:
        """Get the count of documents matching a query

        Args:
            model: model to perform the operation on
            *queries: query filters to apply

        Returns:
            number of document matching the query
        """
        return self.engine.count(
            model, *queries, session=self.engine._get_session(self)
        )

    def save(
        self,
        instance: ODMEngine.ModelType,
    ) -> ODMEngine.ModelType:
        """Persist an instance to the database

        This method behaves as an 'upsert' operation. If a document already exists
        with the same primary key, it will be overwritten.

        All the other models referenced by this instance will be saved as well.

        Args:
            instance: instance to persist

        Returns:
            the saved instance

        NOTE:
            The save operation actually modify the instance argument in place. However,
            the instance is still returned for convenience.
        """
        return self.engine.save(instance, session=self.engine._get_session(self))

    def save_all(
        self,
        instances: Sequence[ODMEngine.ModelType],
    ) -> List[ODMEngine.ModelType]:
        """Persist instances to the database

        This method behaves as multiple 'upsert' operations. If one of the document
        already exists with the same primary key, it will be overwritten.

        All the other models referenced by this instance will be recursively saved as
        well.

        Args:
            instances: instances to persist

        Returns:
            the saved instances

        NOTE:
            The save_all operation actually modify the arguments in place. However, the
            instances are still returned for convenience.
        """
        return self.engine.save_all(instances, session=self.engine._get_session(self))

    def delete(
        self,
        instance: ODMEngine.ModelType,
    ) -> None:
        """Delete an instance from the database

        Args:
            instance: the instance to delete

        Raises:
            DocumentNotFoundError: the instance has not been persisted to the database

        <!---
        #noqa: DAR402 DocumentNotFoundError
        #noqa: DAR201
        -->
        """
        return self.engine.delete(instance, session=self.engine._get_session(self))

    def remove(
        self,
        model: Type[ODMEngine.ModelType],
        *queries: Union[QueryExpression, Dict, bool],
        just_one: bool = False,
    ) -> int:
        """Delete Model instances matching the query filter provided

        Args:
            model: model to perform the operation on
            *queries: query filter to apply
            just_one: limit the deletion to just one document

        Returns:
            the number of instances deleted from the database.

        """
        return self.engine.remove(
            model, *queries, just_one=just_one, session=self.engine._get_session(self)
        )


class SyncSession(SyncSessionBase, ContextManager):

    def __init__(self, engine: ODMEngine.SyncEngine):
        self.engine = engine
        self.session: Optional[ClientSession] = None

    @property
    def is_started(self) -> bool:
        pass

    def get_driver_session(self) -> ClientSession:
        """Return the underlying PyMongo Session"""
        if self.session is None:
            raise RuntimeError("session not started")
        return self.session

    def start(self) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> "SyncSession":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.end()

    def transaction(self) -> SyncTransaction:
        pass


class SyncTransaction(SyncSessionBase, ContextManager):

    def __init__(self, context: Union[ODMEngine.SyncEngine, ODMEngine.SyncSession]):
        self._session_provided = isinstance(context, ODMEngine.SyncSession)
        if self._session_provided:
            assert isinstance(context, ODMEngine.SyncSession)
            if not context.is_started:
                raise RuntimeError("provided session is not started")
            self.session = context
            self.engine = context.engine
        else:
            assert isinstance(context, ODMEngine.SyncEngine)
            self.session = SyncSession(context)
            self.engine = context

        self._transaction_started = False
        self._transaction_context: Optional[ContextManager] = None

    def get_driver_session(self) -> ClientSession:
        """Return the underlying PyMongo Session"""
        if not self._transaction_started:
            raise RuntimeError("transaction not started")
        return self.session.get_driver_session()

    def start(self) -> None:
        pass

    def commit(self) -> None:
        pass

    def abort(self) -> None:
        pass

    def __enter__(self) -> "SyncTransaction":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        assert self._transaction_context is not None
        self._transaction_context.__exit__(exc_type, exc, traceback)
        self._transaction_started = False
