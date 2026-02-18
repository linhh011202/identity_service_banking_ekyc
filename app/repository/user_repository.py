import logging
from contextlib import AbstractContextManager
from typing import Callable

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.ecode import Error
from app.core.exceptions import ErrDatabaseError, ErrUserNotFound, ErrUserAlreadyExists
from app.model import UserModel
from app.repository.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    def __init__(self, session_factory: Callable[..., AbstractContextManager[Session]]):
        self.session_factory = session_factory
        super().__init__(session_factory, UserModel)
        logger.info("UserRepository initialized")

    def get_by_username(self, username: str) -> tuple[UserModel | None, Error | None]:
        logger.debug(f"Querying database for user with username: {username}")
        try:
            with self.session_factory() as session:
                user = (
                    session.query(self.model)
                    .filter(self.model.username == username)
                    .first()
                )
                if user is None:
                    logger.warning(f"User not found: {username}")
                    return None, Error(
                        ErrUserNotFound.code,
                        f"User with username '{username}' not found",
                    )
                logger.info(f"User found in database: {username}")
                return user, None
        except Exception as e:
            logger.error(
                f"Database error while querying user '{username}': {str(e)}",
                exc_info=True,
            )
            return None, Error(ErrDatabaseError.code, f"Database error: {str(e)}")

    def create(
        self, username: str, password_hash: str
    ) -> tuple[UserModel | None, Error | None]:
        logger.debug(f"Creating user: {username}")
        try:
            with self.session_factory() as session:
                try:
                    user = self.model(username=username, password_hash=password_hash)
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    logger.info(f"User created: {username}")
                    return user, None
                except IntegrityError:
                    session.rollback()
                    logger.warning(f"Duplicate username: {username}")
                    return None, Error(
                        ErrUserAlreadyExists.code,
                        f"Username '{username}' already exists",
                    )
        except Exception as e:
            logger.error(
                f"Database error while creating user '{username}': {str(e)}",
                exc_info=True,
            )
            return None, Error(ErrDatabaseError.code, f"Database error: {str(e)}")
