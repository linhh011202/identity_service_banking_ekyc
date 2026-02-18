import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.ecode import Error
from app.core.exceptions import ErrInvalidCredentials, ErrUserNotFound
from app.model import UserModel
from app.service.user_service import UserService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_user(**overrides) -> UserModel:
    """Helper to build a UserModel with sensible defaults."""
    defaults = dict(
        id=uuid.uuid4(),
        email="linh@example.com",
        full_name="Linh Nguyen",
        phone_number="0901234567",
        password_hashed="abc123salt$abc123hash",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    return UserModel(**defaults)


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    return UserService(user_repository=mock_repo)


# ---------------------------------------------------------------------------
# get_user_by_email
# ---------------------------------------------------------------------------


class TestGetUserByEmail:
    def test_success(self, service, mock_repo):
        user = _make_user()
        mock_repo.get_by_email.return_value = (user, None)

        result_user, result_error = service.get_user_by_email("linh@example.com")

        mock_repo.get_by_email.assert_called_once_with("linh@example.com")
        assert result_user == user
        assert result_error is None

    def test_user_not_found(self, service, mock_repo):
        error = Error(ErrUserNotFound.code, "user not found")
        mock_repo.get_by_email.return_value = (None, error)

        result_user, result_error = service.get_user_by_email("unknown@example.com")

        mock_repo.get_by_email.assert_called_once_with("unknown@example.com")
        assert result_user is None
        assert result_error.code == ErrUserNotFound.code


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------


class TestRegisterUser:
    @patch("app.service.user_service.hash_password", return_value="hashed_pw")
    def test_success(self, mock_hash, service, mock_repo):
        user = _make_user(password_hashed="hashed_pw")
        mock_repo.create.return_value = (user, None)

        result_user, result_error = service.register_user(
            email="linh@example.com",
            password="secret123",
            full_name="Linh Nguyen",
            phone_number="0901234567",
        )

        mock_hash.assert_called_once_with("secret123")
        mock_repo.create.assert_called_once_with(
            email="linh@example.com",
            password_hashed="hashed_pw",
            full_name="Linh Nguyen",
            phone_number="0901234567",
        )
        assert result_user == user
        assert result_error is None

    @patch("app.service.user_service.hash_password", return_value="hashed_pw")
    def test_duplicate_email(self, mock_hash, service, mock_repo):
        error = Error(4090001, "user already exists")
        mock_repo.create.return_value = (None, error)

        result_user, result_error = service.register_user(
            email="dup@example.com",
            password="secret123",
        )

        assert result_user is None
        assert result_error.code == 4090001

    @patch("app.service.user_service.hash_password", return_value="hashed_pw")
    def test_optional_fields_default_to_none(self, mock_hash, service, mock_repo):
        mock_repo.create.return_value = (_make_user(), None)

        service.register_user(email="a@b.com", password="pw")

        mock_repo.create.assert_called_once_with(
            email="a@b.com",
            password_hashed="hashed_pw",
            full_name=None,
            phone_number=None,
        )


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class TestLogin:
    @patch("app.service.user_service.verify_password", return_value=True)
    def test_success(self, mock_verify, service, mock_repo):
        user = _make_user()
        mock_repo.get_by_email.return_value = (user, None)

        result_user, result_error = service.login("linh@example.com", "correct_pw")

        mock_repo.get_by_email.assert_called_once_with("linh@example.com")
        mock_verify.assert_called_once_with("correct_pw", user.password_hashed)
        assert result_user == user
        assert result_error is None

    def test_user_not_found(self, service, mock_repo):
        error = Error(ErrUserNotFound.code, "user not found")
        mock_repo.get_by_email.return_value = (None, error)

        result_user, result_error = service.login("unknown@example.com", "pw")

        assert result_user is None
        assert result_error.code == ErrUserNotFound.code

    @patch("app.service.user_service.verify_password", return_value=False)
    def test_invalid_password(self, mock_verify, service, mock_repo):
        user = _make_user()
        mock_repo.get_by_email.return_value = (user, None)

        result_user, result_error = service.login("linh@example.com", "wrong_pw")

        mock_verify.assert_called_once_with("wrong_pw", user.password_hashed)
        assert result_user is None
        assert result_error.code == ErrInvalidCredentials.code
        assert "invalid email or password" in result_error.message
