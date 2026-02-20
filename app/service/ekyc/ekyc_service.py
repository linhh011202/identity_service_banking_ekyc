import asyncio
import logging
import mimetypes
import time
import uuid
from pathlib import Path
from typing import List

import firebase_admin
from firebase_admin import credentials, db, storage
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.config import configs
from app.core.ecode import Error
from app.core.exceptions import ErrInternalError
from app.service.ekyc.ekyc_service_login_result import EkycServiceLoginResult
from app.service.ekyc.ekyc_service_upload_result import EkycServiceUploadResult
from app.repository import UserFaceRepository, UserRepository
from app.service.base.base_service import BaseService
from app.service.pubsub.pubsub_service import PubsubService

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        cred_path = Path(configs.FIREBASE_CREDENTIALS_PATH)
        if not cred_path.is_absolute():
            # Resolve relative path from project root (3 levels up from this file)
            cred_path = Path(__file__).resolve().parents[3] / cred_path
        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(
            cred,
            {
                "storageBucket": configs.GCS_BUCKET_NAME,
                "databaseURL": configs.FIREBASE_RTDB_URL,
            },
        )
        logger.info("Firebase Admin app initialized")
    return _firebase_app


class EkycService(BaseService):
    def __init__(
        self,
        user_repository: UserRepository,
        user_face_repository: UserFaceRepository,
        pubsub_service: PubsubService,
    ) -> None:
        self._user_repository = user_repository
        self._user_face_repository = user_face_repository
        self._pubsub_service = pubsub_service
        super().__init__(user_repository)
        self._bucket_name = configs.GCS_BUCKET_NAME
        self._upload_prefix = (configs.GCS_UPLOAD_PREFIX or "uploads").strip("/")
        self._upload_max_concurrency = max(1, configs.FIREBASE_UPLOAD_MAX_CONCURRENCY)
        logger.info("EkycService initialized")

    def _get_bucket(self):
        if not self._bucket_name:
            raise ValueError("Firebase Storage bucket is not configured")
        _get_firebase_app()
        return storage.bucket()

    @staticmethod
    def _save_fcm_token(session_id: str, fcm_token: str) -> None:
        """Save FCM registration token to Firebase Realtime Database."""
        try:
            _get_firebase_app()
            ref = db.reference(f"/sessions/{session_id}")
            ref.set({"fcm_token": fcm_token})
            logger.info(f"Saved FCM token to RTDB for session: {session_id}")
        except Exception as e:
            logger.error(
                f"Failed to save FCM token to RTDB for session {session_id}: {e}"
            )

    @staticmethod
    def _resolve_extension(upload_file: UploadFile) -> str:
        suffix = Path(upload_file.filename or "").suffix.lower()
        if suffix:
            return suffix
        if upload_file.content_type:
            guessed = mimetypes.guess_extension(
                upload_file.content_type.split(";")[0].strip()
            )
            if guessed:
                return guessed
        return ".jpg"

    async def _upload_group(
        self,
        *,
        bucket,
        session_id: str,
        semaphore: asyncio.Semaphore,
        face_prefix: str,
        files: List[UploadFile],
    ) -> list[str]:
        async def upload_one(index: int, upload_file: UploadFile) -> str:
            extension = self._resolve_extension(upload_file)
            base_path = (
                f"{self._upload_prefix}/{session_id}"
                if self._upload_prefix
                else session_id
            )
            object_name = (
                f"{base_path}/{face_prefix}_{index}_{uuid.uuid4().hex}{extension}"
            )
            blob = bucket.blob(object_name)
            async with semaphore:
                await run_in_threadpool(
                    blob.upload_from_file,
                    upload_file.file,
                    content_type=upload_file.content_type,
                    rewind=True,
                )
            return blob.public_url

        tasks = [
            upload_one(index, upload_file)
            for index, upload_file in enumerate(files, start=1)
        ]
        return list(await asyncio.gather(*tasks))

    async def upload_photos(
        self,
        user_email: str,
        left_faces: List[UploadFile],
        right_faces: List[UploadFile],
        front_faces: List[UploadFile],
        fcm_token: str,
    ) -> tuple[EkycServiceUploadResult | None, Error | None]:
        logger.info(f"Uploading eKYC face photos for user: {user_email}")

        try:
            started_at = time.perf_counter()
            session_id = str(uuid.uuid4())

            # Save FCM token to Firebase Realtime Database
            await run_in_threadpool(self._save_fcm_token, session_id, fcm_token)

            bucket = self._get_bucket()
            semaphore = asyncio.Semaphore(self._upload_max_concurrency)

            left_task = self._upload_group(
                bucket=bucket,
                session_id=session_id,
                semaphore=semaphore,
                face_prefix="left_face",
                files=left_faces,
            )
            right_task = self._upload_group(
                bucket=bucket,
                session_id=session_id,
                semaphore=semaphore,
                face_prefix="right_face",
                files=right_faces,
            )
            front_task = self._upload_group(
                bucket=bucket,
                session_id=session_id,
                semaphore=semaphore,
                face_prefix="front_face",
                files=front_faces,
            )
            left_face_urls, right_face_urls, front_face_urls = await asyncio.gather(
                left_task, right_task, front_task
            )

            response_data = EkycServiceUploadResult(
                session_id=session_id,
            )

            user, user_err = self._user_repository.get_by_email(user_email)
            if user_err:
                logger.error(f"User not found during eKYC upload: {user_email}")
                return None, user_err

            save_error = self._user_face_repository.save_ekyc_faces(
                user_id=user.id,
                left_face_urls=left_face_urls,
                right_face_urls=right_face_urls,
                front_face_urls=front_face_urls,
            )
            if save_error:
                logger.error(
                    f"Uploaded photos but failed to persist eKYC DB records for user "
                    f"{user_email}: {save_error.message}"
                )
                return None, save_error

            mark_error = self._user_repository.mark_ekyc_uploaded(user.id)
            if mark_error:
                logger.warning(
                    f"Faces saved but failed to mark eKYC as uploaded for {user_email}: "
                    f"{mark_error.message}"
                )

            total_uploaded = len(left_faces) + len(right_faces) + len(front_faces)
            elapsed_seconds = time.perf_counter() - started_at
            logger.info(
                f"{total_uploaded} face photos uploaded successfully for session: "
                f"{session_id} in {elapsed_seconds:.2f}s (max_concurrency={self._upload_max_concurrency})"
            )

            # Fire-and-forget: publish sign-up event to Pub/Sub
            self._pubsub_service.publish_signup_event(
                user_id=str(user.id), session_id=session_id
            )

            return response_data, None

        except (RuntimeError, ValueError) as e:
            logger.error(f"Failed to upload photos to Firebase Storage: {str(e)}")
            return None, Error(ErrInternalError.code, "Photo upload failed")
        except Exception as e:
            logger.error(f"Failed to upload photos: {str(e)}")
            return None, Error(
                ErrInternalError.code, "Internal server error during photo upload"
            )

    async def login(
        self,
        user_email: str,
        faces: List[UploadFile],
        fcm_token: str,
    ) -> tuple[EkycServiceLoginResult | None, Error | None]:
        logger.info(f"Processing eKYC login for user: {user_email}")

        if len(faces) != 3:
            return None, Error(400, "Exactly 3 face photos are required for login")

        try:
            started_at = time.perf_counter()
            session_id = str(uuid.uuid4())

            # Save FCM token to Firebase Realtime Database
            await run_in_threadpool(self._save_fcm_token, session_id, fcm_token)

            bucket = self._get_bucket()
            semaphore = asyncio.Semaphore(self._upload_max_concurrency)

            # Upload faces
            face_urls = await self._upload_group(
                bucket=bucket,
                session_id=session_id,
                semaphore=semaphore,
                face_prefix="login_face",
                files=faces,
            )

            # Verify user exists and get user_id
            user, user_err = self._user_repository.get_by_email(user_email)
            if user_err:
                logger.error(f"User not found during eKYC login: {user_email}")
                return None, user_err

            # Save to database
            save_error = self._user_face_repository.save_login_faces(
                user_id=user.id, face_urls=face_urls
            )
            if save_error:
                logger.error(
                    f"Uploaded login photos but failed to persist DB records for user "
                    f"{user_email}: {save_error.message}"
                )
                return None, save_error

            elapsed_seconds = time.perf_counter() - started_at
            logger.info(
                f"Login photos uploaded successfully for session: "
                f"{session_id} in {elapsed_seconds:.2f}s"
            )

            # Fire-and-forget: publish sign-in event
            self._pubsub_service.publish_signin_event(
                user_id=str(user.id), session_id=session_id
            )

            return (
                EkycServiceLoginResult(session_id=session_id),
                None,
            )

        except (RuntimeError, ValueError) as e:
            logger.error(f"Failed to upload login photos to Firebase Storage: {str(e)}")
            return None, Error(ErrInternalError.code, "Photo upload failed")
        except Exception as e:
            logger.error(f"Failed to upload photos for login: {str(e)}")
            return None, Error(
                ErrInternalError.code, "Internal server error during login photo upload"
            )
