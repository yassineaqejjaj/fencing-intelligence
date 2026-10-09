import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def expiry_from_now(*, days: int = 0, hours: int = 0) -> datetime:
    return utcnow() + timedelta(days=days, hours=hours)


def validate_password_strength(password: str) -> None:
    from fencing_api.errors import AppError

    if len(password) < 10:
        raise AppError("weak_password", 422, "Password must be at least 10 characters")
    if password.lower() in {"password123", "fencing123", "changeme123"}:
        raise AppError("weak_password", 422, "Password is too common")
