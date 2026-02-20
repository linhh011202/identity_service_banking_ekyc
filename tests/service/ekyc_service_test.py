import pytest
import asyncio
from unittest.mock import ANY, AsyncMock, Mock, patch

from fastapi import UploadFile
from app.service.ekyc.ekyc_service import EkycService
from app.service.pubsub.pubsub_service import PubsubService
from app.repository import UserFaceRepository, UserRepository


@pytest.fixture
def mock_user_repository():
    return Mock(spec=UserRepository)


@pytest.fixture
def mock_user_face_repository():
    return Mock(spec=UserFaceRepository)


@pytest.fixture
def mock_pubsub_service():
    return Mock(spec=PubsubService)


@pytest.fixture
def ekyc_service(mock_user_repository, mock_user_face_repository, mock_pubsub_service):
    with (
        patch("app.service.ekyc.ekyc_service.firebase_admin"),
        patch("app.service.ekyc.ekyc_service.storage"),
        patch("app.service.ekyc.ekyc_service.configs") as mock_configs,
    ):
        mock_configs.GCS_BUCKET_NAME = "test-bucket"
        mock_configs.GCS_UPLOAD_PREFIX = "test-uploads"
        mock_configs.FIREBASE_UPLOAD_MAX_CONCURRENCY = 2

        service = EkycService(
            mock_user_repository, mock_user_face_repository, mock_pubsub_service
        )
        # Mock _get_bucket to avoid firebase init
        service._get_bucket = Mock()
        return service


def test_upload_photos_success_publishes_event(
    ekyc_service, mock_pubsub_service, mock_user_repository, mock_user_face_repository
):
    # Arrange
    user_email = "test@example.com"
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.file = Mock()

    # Mock concurrent upload
    ekyc_service._upload_group = AsyncMock(return_value=["http://url1"])

    # Mock repository success
    mock_user = Mock()
    mock_user_repository.get_by_email.return_value = (mock_user, None)
    mock_user_face_repository.save_ekyc_faces.return_value = None
    mock_user_repository.mark_ekyc_uploaded.return_value = None

    async def _test():
        return await ekyc_service.upload_photos(
            user_email=user_email,
            left_faces=[mock_file],
            right_faces=[mock_file],
            front_faces=[mock_file],
            fcm_token="test-fcm-token",
        )

    # Act
    # Run the async function synchronously
    response, error = asyncio.run(_test())

    # Assert
    assert error is None
    assert response is not None

    # Verify PubSub event published
    mock_pubsub_service.publish_signup_event.assert_called_once_with(
        user_id=ANY, session_id=ANY
    )


def test_upload_photos_failure_no_publish(
    ekyc_service, mock_pubsub_service, mock_user_repository
):
    # Arrange
    user_email = "test@example.com"
    mock_file = Mock(spec=UploadFile)

    # Mock upload causing exception
    ekyc_service._upload_group = AsyncMock(side_effect=RuntimeError("Upload failed"))

    async def _test():
        return await ekyc_service.upload_photos(
            user_email=user_email,
            left_faces=[mock_file],
            right_faces=[mock_file],
            front_faces=[mock_file],
            fcm_token="test-fcm-token",
        )

    # Act
    response, error = asyncio.run(_test())

    # Assert
    assert error is not None

    # Verify PubSub event NOT published
    mock_pubsub_service.publish_signup_event.assert_not_called()


def test_login_success_publishes_signin_event(
    ekyc_service, mock_pubsub_service, mock_user_repository, mock_user_face_repository
):
    # Arrange
    user_email = "test@example.com"
    mock_file = Mock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.file = Mock()

    # Mock concurrent upload
    ekyc_service._upload_group = AsyncMock(return_value=["http://url1"])

    # Mock repository success
    mock_user = Mock()
    mock_user_repository.get_by_email.return_value = (mock_user, None)
    mock_user_face_repository.save_login_faces.return_value = None

    async def _test():
        return await ekyc_service.login(
            user_email=user_email,
            faces=[mock_file, mock_file, mock_file],
            fcm_token="test-fcm-token",
        )

    # Act
    # Run the async function synchronously
    success, error = asyncio.run(_test())

    # Assert
    # Assert
    assert error is None
    assert success is not None
    assert success.session_id is not None

    # Verify PubSub event published
    mock_pubsub_service.publish_signin_event.assert_called_once_with(
        user_id=ANY, session_id=ANY
    )

    # Verify save_login_faces called
    mock_user_face_repository.save_login_faces.assert_called_once()


def test_login_failure_no_publish(
    ekyc_service, mock_pubsub_service, mock_user_repository
):
    # Arrange
    user_email = "test@example.com"
    mock_file = Mock(spec=UploadFile)

    # Mock user lookup (called before upload in login)
    mock_user_repository.get_by_email.return_value = (Mock(), None)

    # Mock upload causing exception
    ekyc_service._upload_group = AsyncMock(side_effect=RuntimeError("Upload failed"))

    async def _test():
        return await ekyc_service.login(
            user_email=user_email,
            faces=[mock_file, mock_file, mock_file],
            fcm_token="test-fcm-token",
        )

    # Act
    success, error = asyncio.run(_test())

    # Assert
    assert success is None
    assert error is not None

    # Verify PubSub event NOT published
    mock_pubsub_service.publish_signin_event.assert_not_called()


def test_login_failure_invalid_photo_count(
    ekyc_service, mock_pubsub_service, mock_user_repository
):
    # Arrange
    user_email = "test@example.com"
    mock_file = Mock(spec=UploadFile)

    async def _test():
        return await ekyc_service.login(
            user_email=user_email,
            faces=[mock_file],  # Only 1 photo
            fcm_token="test-fcm-token",
        )

    # Act
    success, error = asyncio.run(_test())

    # Assert
    # Assert
    assert success is None
    assert error is not None
    assert error.code == 400

    # Verify PubSub event NOT published
    mock_pubsub_service.publish_signin_event.assert_not_called()
