"""Login and user management (Argon2 password hashing)."""

from __future__ import annotations

from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import User
from . import audit
from .errors import PermissionDenied, ServiceError

_hasher = PasswordHasher()
MIN_PASSWORD = 8


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def has_users(session: Session) -> bool:
    return (session.scalar(select(func.count(User.id))) or 0) > 0


def _check_password(password: str) -> None:
    if len(password) < MIN_PASSWORD:
        raise ServiceError(f"Password must be at least {MIN_PASSWORD} characters.")


def create_user(
    session: Session, actor: User | None, username: str, password: str, full_name: str = "", role: str = "officer"
) -> User:
    username = username.strip().lower()
    if not username:
        raise ServiceError("Username is required.")
    if role not in ("admin", "officer"):
        raise ServiceError("Role must be admin or officer.")
    if has_users(session):
        if actor is None or not actor.is_admin:
            raise PermissionDenied("Only an administrator can add users.")
    else:
        role = "admin"  # the first account is always an administrator
    if session.scalar(select(User).where(User.username == username)):
        raise ServiceError(f"User '{username}' already exists.")
    _check_password(password)
    user = User(username=username, full_name=full_name.strip(), password_hash=hash_password(password), role=role)
    session.add(user)
    session.flush()
    audit.record(session, actor.username if actor else username, "user.create", "user", user.id, f"{username} ({role})")
    return user


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = session.scalar(select(User).where(User.username == username.strip().lower()))
    if user is None or not user.is_active:
        audit.record(session, username, "login.failed", "user", summary="Unknown or inactive user")
        return None
    try:
        _hasher.verify(user.password_hash, password)
    except (VerificationError, InvalidHashError):
        audit.record(session, username, "login.failed", "user", user.id, "Wrong password")
        return None
    if _hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = datetime.now()
    audit.record(session, user.username, "login", "user", user.id)
    return user


def change_password(session: Session, actor: User, user_id: int, new_password: str) -> None:
    if actor.id != user_id and not actor.is_admin:
        raise PermissionDenied("Only an administrator can reset another user's password.")
    _check_password(new_password)
    user = session.get(User, user_id)
    if user is None:
        raise ServiceError("User not found.")
    user.password_hash = hash_password(new_password)
    audit.record(session, actor.username, "user.password", "user", user.id, user.username)


def set_active(session: Session, actor: User, user_id: int, active: bool) -> None:
    if not actor.is_admin:
        raise PermissionDenied("Only an administrator can change users.")
    if actor.id == user_id and not active:
        raise ServiceError("You cannot deactivate your own account.")
    user = session.get(User, user_id)
    if user is None:
        raise ServiceError("User not found.")
    user.is_active = active
    audit.record(session, actor.username, "user.activate" if active else "user.deactivate", "user", user.id, user.username)


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.username)))
