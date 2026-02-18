import logging

from app.core.ecode import Error
from app.core.exceptions import ErrInvalidCredentials  # thêm import
from app.util.security import hash_password, verify_password  # thêm import
from app.model import UserModel
from app.repository import UserRepository
from app.service.base_service import BaseService

logger = logging.getLogger(__name__)


class UserService(BaseService):
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository
        super().__init__(user_repository)
        logger.info("UserService initialized")

    def get_user_by_username(
        self, username: str
    ) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Getting user by username: {username}")
        user, error = self._user_repository.get_by_username(username)
        if error:
            logger.warning(f"Failed to get user '{username}': {error.message}")
        else:
            logger.info(f"Successfully retrieved user '{username}'")
        return user, error

    def register_user(
        self, username: str, password: str
    ) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Registering user: {username}")
        pwd_hash = hash_password(password)
        user, error = self._user_repository.create(username, pwd_hash)
        if error:
            logger.warning(f"Failed to register '{username}': {error.message}")
        else:
            logger.info(f"Registered '{username}' successfully")
        return user, error

    def login(
        self, username: str, password: str
    ) -> tuple[UserModel | None, Error | None]:
        logger.info(f"Login attempt: {username}")
        user, error = self._user_repository.get_by_username(username)
        if error:
            logger.warning(f"Login failed, user not found: {username}")
            return None, error
        if not verify_password(password, user.password_hash):
            logger.warning(f"Login failed, invalid credentials: {username}")
            return None, Error(
                ErrInvalidCredentials.code, "invalid username or password"
            )
        logger.info(f"Login successful: {username}")
        return user, None
