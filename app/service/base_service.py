import logging

from app.repository import BaseRepository

logger = logging.getLogger(__name__)


class BaseService:
    def __init__(self, repository: BaseRepository) -> None:
        self._repository = repository
        logger.debug(f"Initialized {self.__class__.__name__}")
