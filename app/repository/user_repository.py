import logging
import uuid
from contextlib import AbstractContextManager
from typing import Callable, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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

    def get_by_email(self, email: str) -> tuple[UserModel | None, Error | None]:
        logger.debug(f"Querying database for user with email: {email}")
        try:
            with self.session_factory() as session:
                user = (
                    session.query(self.model).filter(self.model.email == email).first()
                )
                if user is None:
                    logger.warning(f"User not found: {email}")
                    return None, Error(
                        ErrUserNotFound.code,
                        f"User with email '{email}' not found",
                    )
                logger.info(f"User found in database: {email}")
                return user, None
        except Exception as e:
            logger.error(
                f"Database error while querying user '{email}': {str(e)}",
                exc_info=True,
            )
            return None, Error(ErrDatabaseError.code, f"Database error: {str(e)}")

    def create(
        self,
        email: str,
        password_hashed: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> tuple[UserModel | None, Error | None]:
        logger.debug(f"Creating user: {email}")
        try:
            with self.session_factory() as session:
                try:
                    user = self.model(
                        email=email,
                        password_hashed=password_hashed,
                        full_name=full_name,
                        phone_number=phone_number,
                    )
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    logger.info(f"User created: {email}")
                    return user, None
                except IntegrityError:
                    session.rollback()
                    logger.warning(f"Duplicate email or phone_number: {email}")
                    return None, Error(
                        ErrUserAlreadyExists.code,
                        f"User with email '{email}' or phone number already exists",
                    )
        except Exception as e:
            logger.error(
                f"Database error while creating user '{email}': {str(e)}",
                exc_info=True,
            )
            return None, Error(ErrDatabaseError.code, f"Database error: {str(e)}")

    def mark_ekyc_uploaded(self, user_id: uuid.UUID) -> Error | None:
        logger.info(f"Marking eKYC as uploaded for user_id: {user_id}")
        try:
            with self.session_factory() as session:
                updated = (
                    session.query(self.model)
                    .filter(self.model.id == user_id)
                    .update({"is_ekyc_uploaded": True})
                )
                if updated == 0:
                    logger.warning(
                        f"User not found while marking eKYC uploaded: {user_id}"
                    )
                    return Error(ErrUserNotFound.code, f"User '{user_id}' not found")
                session.commit()
                logger.info(f"Marked eKYC as uploaded for user_id: {user_id}")
                return None
        except Exception as e:
            logger.error(
                f"Database error while marking eKYC uploaded for '{user_id}': {str(e)}",
                exc_info=True,
            )
            return Error(ErrDatabaseError.code, f"Database error: {str(e)}")
