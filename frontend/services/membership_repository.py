"""
membership_repository.py

Stores the REAL permission-bearing relationship: which authenticated
user has which role on which business. This is deliberately a
separate table from `employees` — see employee_repository.py's
docstring for why conflating the two would be unsafe.

OWNER, ADMIN, MANAGER, EMPLOYEE are the same four role names used on
Employee records, but here they mean something different: here, the
role is actually checked before a protected operation is allowed to
run (see permission_service.py). On an Employee record, the same
word is only a label.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

OWNER = "owner"
ADMIN = "admin"
MANAGER = "manager"
EMPLOYEE = "employee"
ROLES = [OWNER, ADMIN, MANAGER, EMPLOYEE]


@dataclass
class Membership:
    id: str
    business_id: str
    user_id: str
    role: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class MembershipRepository:
    """Persistent storage for business_memberships."""

    def __init__(self, connection):
        self._conn = connection

    def create(self, business_id: str, user_id: str, role: str) -> Membership:
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role!r}")

        membership = Membership(id=str(uuid.uuid4()), business_id=business_id, user_id=user_id, role=role)
        self._conn.execute(
            "INSERT INTO business_memberships (id, business_id, user_id, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (membership.id, membership.business_id, membership.user_id, membership.role, membership.created_at),
        )
        self._conn.commit()
        return membership

    def get_role(self, business_id: str, user_id: str) -> Optional[str]:
        """Returns the user's role on this business, or None if they have no membership at all."""
        row = self._conn.execute(
            "SELECT role FROM business_memberships WHERE business_id = ? AND user_id = ?",
            (business_id, user_id),
        ).fetchone()
        return row[0] if row else None
