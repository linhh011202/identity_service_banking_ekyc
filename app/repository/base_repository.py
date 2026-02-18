import logging
from contextlib import AbstractContextManager
from typing import Callable, Type, TypeVar

from app.model import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class BaseRepository:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        model: Type[T],
    ) -> None:
        self.session_factory = session_factory
        self.model = model
        logger.debug(
            f"Initialized {self.__class__.__name__} for model {model.__name__}"
        )
