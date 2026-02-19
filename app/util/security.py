import os
import binascii
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import Configs

_configs = Configs()
_bearer_scheme = HTTPBearer()


def create_access_token(subject: str) -> str:
    """Create a JWT access token for the given subject (e.g. user email)."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=_configs.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload, _configs.JWT_SECRET_KEY, algorithm=_configs.JWT_ALGORITHM
    )


def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            _configs.JWT_SECRET_KEY,
            algorithms=[_configs.JWT_ALGORITHM],
        )
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return subject
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from exc


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$", 1)
        salt = binascii.unhexlify(salt_hex.encode())
        expected = binascii.unhexlify(dk_hex.encode())
        computed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100_000
        )
        return hmac.compare_digest(expected, computed)
    except Exception:
        return False
