"""
auth_service.py

LOCAL, DEV-ONLY authentication service.

Phase 8 kept users purely in memory (wiped on every restart). Phase 9
persists users to SQLite via UserRepository so that a business
profile (now also persisted) has someone who can actually log back in
to see it after an app restart — otherwise Phase 9's persistence
requirement would be unverifiable end-to-end through the UI.

This is STILL NOT a production authentication system:
- No real session tokens or expiry.
- No rate limiting or lockout.
- No password reset flow.
- No server-side verification — everything runs locally in this app.

Passwords are NEVER stored in plaintext: each is hashed with
PBKDF2-HMAC-SHA256 with a random per-user salt (Python's built-in
hashlib — no new dependency, no homemade crypto). Only the hash and
salt are persisted.

Public API (register, login) is unchanged from Phase 8 — screens
calling AuthService did not need to change.
"""

import hashlib
import os
import uuid
from dataclasses import dataclass

from services.database import get_connection
from services.user_repository import UserRepository


@dataclass
class User:
    id: str
    full_name: str
    email: str


class AuthService:
    """Dev-only user auth, backed by persistent (hashed-only) storage."""

    _repository = None
    _users_by_email_cache: dict = {}  # email -> {"user": User, "salt": bytes, "hash": bytes}
    _cache_loaded = False

    @classmethod
    def _repo(cls) -> UserRepository:
        if cls._repository is None:
            cls._repository = UserRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: UserRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository
        cls._users_by_email_cache = {}
        cls._cache_loaded = False

    @classmethod
    def _ensure_cache_loaded(cls) -> None:
        if cls._cache_loaded:
            return
        for record in cls._repo().get_all():
            cls._users_by_email_cache[record.email] = {
                "user": User(id=record.id, full_name=record.full_name, email=record.email),
                "salt": record.password_salt,
                "hash": record.password_hash,
            }
        cls._cache_loaded = True

    @classmethod
    def register(cls, full_name: str, email: str, password: str) -> User:
        cls._ensure_cache_loaded()
        email_key = email.strip().lower()
        if not full_name.strip() or not email_key or not password:
            raise ValueError("All fields are required.")
        if email_key in cls._users_by_email_cache:
            raise ValueError("An account with this email already exists.")

        salt = os.urandom(16)
        password_hash = cls._hash_password(password, salt)
        user = User(id=str(uuid.uuid4()), full_name=full_name.strip(), email=email_key)

        cls._repo().create(user.id, user.full_name, user.email, password_hash, salt)
        cls._users_by_email_cache[email_key] = {"user": user, "salt": salt, "hash": password_hash}
        return user

    @classmethod
    def login(cls, email: str, password: str) -> User:
        cls._ensure_cache_loaded()
        email_key = email.strip().lower()
        record = cls._users_by_email_cache.get(email_key)
        if not record:
            raise ValueError("No account found with this email.")
        if cls._hash_password(password, record["salt"]) != record["hash"]:
            raise ValueError("Incorrect password.")
        return record["user"]

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
