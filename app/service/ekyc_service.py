import asyncio
import logging
import mimetypes
import time
import uuid
from pathlib import Path
from typing import List

import firebase_admin
from firebase_admin import credentials, storage
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool

from app.core.config import configs
from app.core.ecode import Error
from app.core.exceptions import ErrInternalError
from app.dto.ekyc.response.upload_photos_response import UploadPhotosResponse
from app.repository import UserRepository
from app.service.base_service import BaseService

logger = logging.getLogger(__name__)

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        cred_path = Path(configs.FIREBASE_CREDENTIALS_PATH)
        if not cred_path.is_absolute():
            # Resolve relative path from project root (2 levels up from this file)
            cred_path = Path(__file__).resolve().parents[2] / cred_path
        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(
            cred, {"storageBucket": configs.GCS_BUCKET_NAME}
        )
        logger.info("Firebase Admin app initialized")
    return _firebase_app


class EkycService(BaseService):
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository
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
    ) -> tuple[UploadPhotosResponse | None, Error | None]:
        logger.info(f"Uploading eKYC face photos for user: {user_email}")

        try:
            started_at = time.perf_counter()
            session_id = str(uuid.uuid4())
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

            response_data = UploadPhotosResponse(
                left_face_urls=left_face_urls,
                right_face_urls=right_face_urls,
                front_face_urls=front_face_urls,
                session_id=session_id,
            )

            save_error = self._user_repository.save_ekyc_faces(
                email=user_email,
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

            total_uploaded = len(left_faces) + len(right_faces) + len(front_faces)
            elapsed_seconds = time.perf_counter() - started_at
            logger.info(
                f"{total_uploaded} face photos uploaded successfully for session: "
                f"{session_id} in {elapsed_seconds:.2f}s (max_concurrency={self._upload_max_concurrency})"
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
