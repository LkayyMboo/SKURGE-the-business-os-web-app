"""
user_repository.py

Parameterized SQLite storage for users. ONLY the password hash and
salt are stored — never a plaintext password. This is still a
LOCAL, DEV-ONLY credential store: no real session tokens, no rate
limiting, no password reset, no backend verification. It exists so
AuthService's accounts survive an application restart, which is
required for Phase 9's business-persistence to be demonstrable
end-to-end (a business profile needs an owner to log back in as).

All SQL here uses parameterized queries (the `?` placeholders) —
never string-formatted SQL — to avoid SQL injection.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class UserRecord:
    id: str
    full_name: str
    email: str
    password_hash: bytes
    password_salt: bytes


class UserRepository:
    """Persistent storage for user accounts (hashed credentials only)."""

    def __init__(self, connection):
        self._conn = connection

    def create(self, user_id: str, full_name: str, email: str, password_hash: bytes, password_salt: bytes) -> None:
        self._conn.execute(
            "INSERT INTO users (id, full_name, email, password_hash, password_salt, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, full_name, email, password_hash, password_salt, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def get_by_email(self, email: str):
        row = self._conn.execute(
            "SELECT id, full_name, email, password_hash, password_salt FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            return None
        return UserRecord(id=row[0], full_name=row[1], email=row[2], password_hash=row[3], password_salt=row[4])

    def get_all(self):
        rows = self._conn.execute(
            "SELECT id, full_name, email, password_hash, password_salt FROM users"
        ).fetchall()
        return [
            UserRecord(id=r[0], full_name=r[1], email=r[2], password_hash=r[3], password_salt=r[4])
            for r in rows
        ]
