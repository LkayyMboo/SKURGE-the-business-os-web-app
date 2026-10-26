"""
employee_repository.py

Parameterized SQLite storage for employee HR records.

IMPORTANT DISTINCTION (do not blur this — see permission_service.py
for the table that actually matters for security):
An Employee row describes a PERSON this business employs — their
name, job title, contact details, a descriptive "role" label, and
whether they're currently active. It is NOT a login account, and
having `role='admin'` on an Employee row grants that person NOTHING.
Real permissions are checked against business_memberships via
PermissionService, a completely separate table. A business could
record 50 employees here and grant zero of them any system access —
that would be entirely normal and expected for most small businesses
whose staff don't need to log into SKURGE at all.

ACTIVE = "active"
INACTIVE = "inactive"
ON_LEAVE = "on_leave"

Deletion is intentionally NOT supported — ordinary departures are
handled by setting employment_status to INACTIVE, so the business
keeps its historical record.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

ACTIVE = "active"
INACTIVE = "inactive"
ON_LEAVE = "on_leave"
EMPLOYMENT_STATUSES = [ACTIVE, INACTIVE, ON_LEAVE]

# Same four role LABELS as business_memberships, but here they are
# descriptive only — see module docstring.
EMPLOYEE_ROLES = ["owner", "admin", "manager", "employee"]


@dataclass
class Employee:
    id: str
    business_id: str
    full_name: str
    job_title: str
    role: str
    employment_status: str
    start_date: str
    email: str = ""
    phone: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_COLUMNS = [
    "id", "business_id", "full_name", "email", "phone", "job_title",
    "role", "employment_status", "start_date", "created_at", "updated_at",
]


def _row_to_employee(row) -> Employee:
    return Employee(**dict(zip(_COLUMNS, row)))


class EmployeeRepository:
    """Persistent CRUD storage for employee HR records."""

    def __init__(self, connection):
        self._conn = connection

    def create(self, business_id: str, full_name: str, job_title: str, role: str,
               employment_status: str, start_date: str, email: str = "", phone: str = "") -> Employee:
        if not full_name or not full_name.strip():
            raise ValueError("Full name is required.")
        if not job_title or not job_title.strip():
            raise ValueError("Job title is required.")
        if role not in EMPLOYEE_ROLES:
            raise ValueError(f"Invalid role: {role!r}")
        if employment_status not in EMPLOYMENT_STATUSES:
            raise ValueError(f"Invalid employment_status: {employment_status!r}")
        if not start_date:
            raise ValueError("Start date is required.")

        employee = Employee(
            id=str(uuid.uuid4()), business_id=business_id, full_name=full_name.strip(),
            email=(email or "").strip(), phone=(phone or "").strip(), job_title=job_title.strip(),
            role=role, employment_status=employment_status, start_date=start_date,
        )

        self._conn.execute(
            f"INSERT INTO employees ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
            tuple(getattr(employee, column) for column in _COLUMNS),
        )
        self._conn.commit()
        return employee

    def get_by_id(self, employee_id: str) -> Optional[Employee]:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM employees WHERE id = ?", (employee_id,)
        ).fetchone()
        return _row_to_employee(row) if row else None

    def list_for_business(self, business_id: str, employment_status: str = None):
        query = f"SELECT {', '.join(_COLUMNS)} FROM employees WHERE business_id = ?"
        params = [business_id]
        if employment_status is not None:
            query += " AND employment_status = ?"
            params.append(employment_status)
        query += " ORDER BY full_name ASC"
        rows = self._conn.execute(query, tuple(params)).fetchall()
        return [_row_to_employee(row) for row in rows]

    def update(self, employee_id: str, **fields) -> Optional[Employee]:
        existing = self.get_by_id(employee_id)
        if existing is None:
            return None

        if "role" in fields and fields["role"] not in EMPLOYEE_ROLES:
            raise ValueError(f"Invalid role: {fields['role']!r}")
        if "employment_status" in fields and fields["employment_status"] not in EMPLOYMENT_STATUSES:
            raise ValueError(f"Invalid employment_status: {fields['employment_status']!r}")

        updatable_columns = [c for c in _COLUMNS if c not in ("id", "business_id", "created_at")]
        assignments = []
        values = []
        for column in updatable_columns:
            if column in fields:
                assignments.append(f"{column} = ?")
                values.append(fields[column])
        assignments.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(employee_id)

        self._conn.execute(
            f"UPDATE employees SET {', '.join(assignments)} WHERE id = ?", tuple(values)
        )
        self._conn.commit()
        return self.get_by_id(employee_id)

    def count_by_status(self, business_id: str) -> dict:
        """Returns {'active': n, 'inactive': n, 'on_leave': n} for a business."""
        rows = self._conn.execute(
            "SELECT employment_status, COUNT(*) FROM employees WHERE business_id = ? GROUP BY employment_status",
            (business_id,),
        ).fetchall()
        counts = {ACTIVE: 0, INACTIVE: 0, ON_LEAVE: 0}
        for status, count in rows:
            counts[status] = count
        return counts
