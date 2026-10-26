"""
business_repository.py

Parameterized SQLite storage for business profiles. The UI and
BusinessService never write SQL directly — everything goes through
this repository.

Explicit registration states (per Phase 9 requirement — distinct from
any future real CIPC verification):

    DRAFT                 - profile started, not yet marked as registered
    REGISTRATION_IN_PROGRESS
    REGISTERED_DECLARED   - the USER has stated it's registered;
                            SKURGE has not verified this with CIPC
    VERIFIED              - reserved for a future real CIPC/SARS
                            integration; never set by this code today
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

DRAFT = "draft"
REGISTRATION_IN_PROGRESS = "registration_in_progress"
REGISTERED_DECLARED = "registered_declared"
VERIFIED = "verified"  # Never set anywhere yet — reserved for a real future integration.

REGISTRATION_STATUSES = [DRAFT, REGISTRATION_IN_PROGRESS, REGISTERED_DECLARED, VERIFIED]

# User-facing labels for the statuses a person can actually choose today.
# VERIFIED is intentionally excluded — no screen lets a user set it,
# because SKURGE cannot verify a business itself yet.
REGISTRATION_STATUS_CHOICES = {
    DRAFT: "Not yet registered",
    REGISTRATION_IN_PROGRESS: "Registration in progress",
    REGISTERED_DECLARED: "Registered (as declared by you)",
}


@dataclass
class Business:
    id: str
    owner_user_id: str
    name: str
    business_type: str
    industry: str
    registration_status: str
    province: str
    cipc_number: str = ""
    city: str = ""
    phone: str = ""
    email: str = ""
    primary_contact_name: str = ""
    tax_status: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_COLUMNS = [
    "id", "owner_user_id", "name", "business_type", "industry", "registration_status",
    "cipc_number", "province", "city", "phone", "email", "primary_contact_name",
    "tax_status", "created_at", "updated_at",
]


def _row_to_business(row) -> Business:
    return Business(**dict(zip(_COLUMNS, row)))


class BusinessRepository:
    """Persistent CRUD storage for business profiles."""

    def __init__(self, connection):
        self._conn = connection

    def create(self, owner_user_id: str, **fields) -> Business:
        if fields.get("registration_status") not in REGISTRATION_STATUSES:
            raise ValueError(f"Invalid registration_status: {fields.get('registration_status')!r}")

        business = Business(id=str(uuid.uuid4()), owner_user_id=owner_user_id, **fields)

        self._conn.execute(
            f"INSERT INTO businesses ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
            tuple(getattr(business, column) for column in _COLUMNS),
        )
        self._conn.commit()
        return business

    def update(self, business_id: str, **fields) -> Optional[Business]:
        existing = self.get_by_id(business_id)
        if existing is None:
            return None

        if "registration_status" in fields and fields["registration_status"] not in REGISTRATION_STATUSES:
            raise ValueError(f"Invalid registration_status: {fields['registration_status']!r}")

        updatable_columns = [c for c in _COLUMNS if c not in ("id", "owner_user_id", "created_at")]
        set_clause = ", ".join(f"{column} = ?" for column in updatable_columns if column in fields or column == "updated_at")

        values = []
        assignments = []
        for column in updatable_columns:
            if column in fields:
                assignments.append(f"{column} = ?")
                values.append(fields[column])
        assignments.append("updated_at = ?")
        updated_at = datetime.now(timezone.utc).isoformat()
        values.append(updated_at)
        values.append(business_id)

        self._conn.execute(
            f"UPDATE businesses SET {', '.join(assignments)} WHERE id = ?",
            tuple(values),
        )
        self._conn.commit()
        return self.get_by_id(business_id)

    def get_by_id(self, business_id: str) -> Optional[Business]:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM businesses WHERE id = ?", (business_id,)
        ).fetchone()
        return _row_to_business(row) if row else None

    def get_by_owner(self, owner_user_id: str):
        rows = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM businesses WHERE owner_user_id = ? ORDER BY updated_at DESC",
            (owner_user_id,),
        ).fetchall()
        return [_row_to_business(row) for row in rows]

    def get_active_business_id(self, user_id: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT active_business_id FROM session_state WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row[0] if row else None

    def set_active_business_id(self, user_id: str, business_id: str) -> None:
        self._conn.execute(
            "INSERT INTO session_state (user_id, active_business_id) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET active_business_id = excluded.active_business_id",
            (user_id, business_id),
        )
        self._conn.commit()
