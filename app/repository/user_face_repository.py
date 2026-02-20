import logging
import uuid
from contextlib import AbstractContextManager
from typing import Callable

from sqlalchemy.orm import Session

from app.core.ecode import Error
from app.core.exceptions import ErrDatabaseError
from app.model import UserFaceModel
from app.repository.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserFaceRepository(BaseRepository):
    def __init__(
        self, session_factory: Callable[..., AbstractContextManager[Session]]
    ) -> None:
        super().__init__(session_factory, UserFaceModel)
        logger.info("UserFaceRepository initialized")

    def save_ekyc_faces(
        self,
        user_id: uuid.UUID,
        left_face_urls: list[str],
        right_face_urls: list[str],
        front_face_urls: list[str],
    ) -> Error | None:
        logger.info(f"Saving eKYC face upload info for user_id: {user_id}")
        try:
            with self.session_factory() as session:
                session.query(UserFaceModel).filter(
                    UserFaceModel.user_id == user_id,
                    UserFaceModel.pose.in_(["left", "right", "straight"]),
                ).delete(synchronize_session=False)

                session.add_all(
                    [
                        UserFaceModel(user_id=user_id, pose=pose, source_images=urls)
                        for pose, urls in [
                            ("left", left_face_urls),
                            ("right", right_face_urls),
                            ("straight", front_face_urls),
                        ]
                    ]
                )

                session.commit()
                logger.info(
                    f"Saved eKYC face upload info successfully for user_id: {user_id}"
                )
                return None
        except Exception as e:
            logger.error(
                f"Database error while saving eKYC faces for user_id '{user_id}': {str(e)}",
                exc_info=True,
            )
            return Error(ErrDatabaseError.code, f"Database error: {str(e)}")

    def save_login_faces(
        self, user_id: uuid.UUID, face_urls: list[str]
    ) -> Error | None:
        logger.info(f"Saving login faces for user_id: {user_id}")
        try:
            with self.session_factory() as session:
                session.add(
                    UserFaceModel(
                        user_id=user_id, pose="login", source_images=face_urls
                    )
                )
                session.commit()
                logger.info(f"Saved login faces successfully for user_id: {user_id}")
                return None
        except Exception as e:
            logger.error(
                f"Database error while saving login faces for user_id '{user_id}': {str(e)}",
                exc_info=True,
            )
            return Error(ErrDatabaseError.code, f"Database error: {str(e)}")
