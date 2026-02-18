import logging
from typing import Optional

from app.core.ecode import Error
from app.core.exceptions import ErrInvalidCredentials
from app.util.security import hash_password, verify_password
from app.model import UserModel
from app.repository import UserRepository
from app.service.base_service import BaseService

logger = logging.getLogger(__name__)


class UserService(BaseService):
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository
        super().__init__(user_repository)
        logger.info("UserService initialized")

    def get_user_by_email(self, email: str) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Getting user by email: {email}")
        user, error = self._user_repository.get_by_email(email)
        if error:
            logger.warning(f"Failed to get user '{email}': {error.message}")
        else:
            logger.info(f"Successfully retrieved user '{email}'")
        return user, error

    def register_user(
        self,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Registering user: {email}")
        pwd_hash = hash_password(password)
        user, error = self._user_repository.create(
            email=email,
            password_hashed=pwd_hash,
            full_name=full_name,
            phone_number=phone_number,
        )
        if error:
            logger.warning(f"Failed to register '{email}': {error.message}")
        else:
            logger.info(f"Registered '{email}' successfully")
        return user, error

    def login(self, email: str, password: str) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Login attempt: {email}")
        user, error = self._user_repository.get_by_email(email)
        if error:
            logger.warning(f"Login failed, user not found: {email}")
            return None, error
        if not verify_password(password, user.password_hashed):
            logger.warning(f"Login failed, invalid credentials: {email}")
            return None, Error(ErrInvalidCredentials.code, "invalid email or password")
        logger.info(f"Login successful: {email}")
        return user, None
