#!/usr/bin/env bash
set -e
cd ~/business-os

mkdir -p frontend/layouts frontend/screens/employees frontend/services tests

cat > frontend/services/database.py << 'PYEOF_FILE'
"""
database.py

Thin SQLite connection + schema setup for Business OS / SKURGE local
persistence.

No ORM is introduced — the project explicitly avoids unnecessary
dependencies, and SQLite via Python's built-in `sqlite3` module is
sufficient for a single-user local desktop app at this stage.

The database file lives at <project_root>/database/skurge.db by
default, resolved relative to THIS file's location so it works
regardless of the current working directory (e.g. whether you ran
`python main.py` from frontend/ or elsewhere).

DB_PATH can be overridden (see get_connection's db_path parameter) —
this is how tests use a temporary, isolated database instead of
touching real application data.
"""

import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "database" / "skurge.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash BLOB NOT NULL,
    password_salt BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS businesses (
    id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    business_type TEXT NOT NULL,
    industry TEXT NOT NULL,
    registration_status TEXT NOT NULL,
    cipc_number TEXT,
    province TEXT NOT NULL,
    city TEXT,
    phone TEXT,
    email TEXT,
    primary_contact_name TEXT,
    tax_status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS session_state (
    user_id TEXT PRIMARY KEY,
    active_business_id TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (active_business_id) REFERENCES businesses(id)
);

-- Phase 10: bookkeeping. amount_cents is an INTEGER (never REAL) to
-- avoid floating-point rounding errors in financial totals.
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

-- Speeds up "this business's transaction history, newest first" —
-- the query every Finance/Dashboard screen load runs.
CREATE INDEX IF NOT EXISTS idx_transactions_business_date
    ON transactions(business_id, transaction_date DESC, created_at DESC);

-- Phase 11: Employees.
--
-- IMPORTANT: this is an HR record, NOT a login account. Its `role`
-- column is a descriptive label only (e.g. "this person's job-level
-- role is Admin") and grants NOTHING by itself — see
-- business_memberships below for the table that actually controls
-- permissions. employment_status is kept separate from role/
-- permissions on purpose: an inactive employee record must not be
-- confused with a revoked permission.
CREATE TABLE IF NOT EXISTS employees (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    job_title TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'manager', 'employee')),
    employment_status TEXT NOT NULL CHECK (employment_status IN ('active', 'inactive', 'on_leave')),
    start_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE INDEX IF NOT EXISTS idx_employees_business
    ON employees(business_id, employment_status);

-- Phase 11: the REAL permission-bearing relationship. Links an
-- authenticated user to a business with an enforced role. One row is
-- created automatically (role='owner') whenever a business is
-- created. Nothing in this app currently creates any OTHER row in
-- this table — there is no "invite a user to this business" screen
-- yet — so today every authorized action resolves to the owner. The
-- table and the permission checks against it are real and tested;
-- only the "invite someone else" UI is future work.
CREATE TABLE IF NOT EXISTS business_memberships (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'manager', 'employee')),
    created_at TEXT NOT NULL,
    UNIQUE(business_id, user_id),
    FOREIGN KEY (business_id) REFERENCES businesses(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    """
    Open a connection to the SKURGE local database, creating the
    schema if it does not exist yet.

    db_path lets callers (mainly tests) point at an isolated, temporary
    database file instead of the real one.
    """
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(path))
    # Foreign keys are declared in the schema for documentation and
    # future enforcement, but NOT turned on here: BusinessRepository
    # and UserRepository are deliberately independently testable, and
    # the real application flow (register -> business setup) already
    # guarantees owner_user_id refers to a real user.
    connection.executescript(SCHEMA)
    connection.commit()
    return connection
PYEOF_FILE

cat > frontend/services/membership_repository.py << 'PYEOF_FILE'
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
PYEOF_FILE

cat > frontend/services/permission_service.py << 'PYEOF_FILE'
"""
permission_service.py

The permission matrix, and the one place protected operations check
"is this authenticated user actually allowed to do this on this
business?" — not just "is this business currently selected?".

Selecting a business (app_session.current_business) is never, by
itself, proof of authorization. A protected service method must be
given the ACTING user's ID and check it here.

CURRENT LIMITATION (stated plainly, not hidden): the only way a
MembershipRepository row is ever created today is automatically, as
'owner', when BusinessService.create_business() runs. There is no
"invite a teammate to this business" screen yet. So in practice,
every authorized action today resolves to the business owner — the
Admin/Manager/Employee rows of the matrix below are implemented and
tested, but cannot currently be exercised by a second real user
through the UI. That is future work, not something this phase
pretends to have finished.
"""

from services.database import get_connection
from services.membership_repository import ADMIN, EMPLOYEE, MANAGER, MembershipRepository, OWNER

# Permission matrix: which roles may perform which protected operations.
PERMISSIONS = {
    "manage_employees": {OWNER, ADMIN},
    "change_employment_status": {OWNER, ADMIN},
    "record_transactions": {OWNER, ADMIN, MANAGER},
    "view_finance": {OWNER, ADMIN, MANAGER},
}


class PermissionError(Exception):
    """Raised when an authenticated user lacks permission for an operation."""


class PermissionService:
    """Checks whether a user may perform a given operation on a business."""

    _repository = None

    @classmethod
    def _repo(cls) -> MembershipRepository:
        if cls._repository is None:
            cls._repository = MembershipRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: MembershipRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @classmethod
    def grant_owner(cls, business_id: str, user_id: str) -> None:
        """Called once, automatically, when a business is created."""
        cls._repo().create(business_id=business_id, user_id=user_id, role=OWNER)

    @classmethod
    def get_role(cls, business_id: str, user_id: str):
        return cls._repo().get_role(business_id, user_id)

    @classmethod
    def has_permission(cls, business_id: str, user_id: str, permission: str) -> bool:
        if permission not in PERMISSIONS:
            raise ValueError(f"Unknown permission: {permission!r}")
        role = cls.get_role(business_id, user_id)
        if role is None:
            return False
        return role in PERMISSIONS[permission]

    @classmethod
    def require_permission(cls, business_id: str, user_id: str, permission: str) -> None:
        """Raises PermissionError if the user lacks the given permission."""
        if not cls.has_permission(business_id, user_id, permission):
            raise PermissionError(
                f"You do not have permission to perform this action on this business."
            )
PYEOF_FILE

cat > frontend/services/employee_repository.py << 'PYEOF_FILE'
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
PYEOF_FILE

cat > frontend/services/employee_service.py << 'PYEOF_FILE'
"""
employee_service.py

Employee HR operations: validation lives here once, not duplicated
between the screen and the repository.

Mutating operations (create, update, change employment status)
require acting_user_id and check PermissionService BEFORE touching
the repository — this is the actual enforcement point, not just a
hidden/disabled button in the UI. Read operations (listing, counts)
are not permission-gated in this phase: viewing the employee list for
whichever business is currently selected is treated the same way
viewing Finance totals already is elsewhere in the app.
"""

import re

from services.database import get_connection
from services.employee_repository import EmployeeRepository
from services.permission_service import PermissionService
from utils.validators import validate_iso_date

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmployeeService:
    """Employee HR operations. Delegates storage to EmployeeRepository."""

    _repository = None

    @classmethod
    def _repo(cls) -> EmployeeRepository:
        if cls._repository is None:
            cls._repository = EmployeeRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: EmployeeRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @staticmethod
    def _validate_email(email: str) -> None:
        if email and not EMAIL_PATTERN.match(email):
            raise ValueError("Enter a valid email address, e.g. name@example.com.")

    @classmethod
    def add_employee(cls, acting_user_id: str, business_id: str, full_name: str, job_title: str,
                      role: str, employment_status: str, start_date: str, email: str = "", phone: str = ""):
        PermissionService.require_permission(business_id, acting_user_id, "manage_employees")

        cls._validate_email(email)
        validate_iso_date(start_date)  # Raises ValueError with a clear message if invalid.

        return cls._repo().create(
            business_id=business_id, full_name=full_name, job_title=job_title, role=role,
            employment_status=employment_status, start_date=start_date, email=email, phone=phone,
        )

    @classmethod
    def update_employee(cls, acting_user_id: str, business_id: str, employee_id: str, **fields):
        PermissionService.require_permission(business_id, acting_user_id, "manage_employees")

        if "email" in fields:
            cls._validate_email(fields["email"])
        if "start_date" in fields:
            validate_iso_date(fields["start_date"])

        updated = cls._repo().update(employee_id, **fields)
        if updated is None:
            raise ValueError("No employee found with that ID.")
        return updated

    @classmethod
    def set_employment_status(cls, acting_user_id: str, business_id: str, employee_id: str, employment_status: str):
        PermissionService.require_permission(business_id, acting_user_id, "change_employment_status")

        updated = cls._repo().update(employee_id, employment_status=employment_status)
        if updated is None:
            raise ValueError("No employee found with that ID.")
        return updated

    @classmethod
    def list_employees(cls, business_id: str, employment_status: str = None):
        return cls._repo().list_for_business(business_id, employment_status=employment_status)

    @classmethod
    def get_employee(cls, employee_id: str):
        return cls._repo().get_by_id(employee_id)

    @classmethod
    def get_counts(cls, business_id: str) -> dict:
        return cls._repo().count_by_status(business_id)
PYEOF_FILE

cat > frontend/services/business_service.py << 'PYEOF_FILE'
"""
business_service.py

Business profile operations, now backed by persistent SQLite storage
(via BusinessRepository) instead of an in-memory dict.

Public API is intentionally unchanged from the Phase 8 in-memory
version (create_business, update_business, get_business_for_user)
so existing callers (BusinessSetupScreen, app.py) did not need to
change their call sites — only their imports, and only because
Business/registration-status constants moved to business_repository.

New in Phase 9: get_businesses_for_user (list, supports multiple
businesses per owner) and active-business selection, backed by the
session_state table.

Phase 11: creating a business now also grants its creator the
'owner' role in business_memberships — the real permission-bearing
record PermissionService checks. This is the ONLY place a membership
row is currently created; see permission_service.py's docstring for
what that means and does not yet mean.
"""

from services.business_repository import (
    Business,
    BusinessRepository,
    DRAFT,
    REGISTRATION_IN_PROGRESS,
    REGISTERED_DECLARED,
    VERIFIED,
    REGISTRATION_STATUSES,
    REGISTRATION_STATUS_CHOICES,
)
from services.database import get_connection
from services.permission_service import PermissionService


class BusinessService:
    """Business profile operations. Delegates all storage to BusinessRepository."""

    _repository = None

    @classmethod
    def _repo(cls) -> BusinessRepository:
        if cls._repository is None:
            cls._repository = BusinessRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: BusinessRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @classmethod
    def create_business(cls, owner_user_id: str, **fields) -> Business:
        if not fields.get("name", "").strip():
            raise ValueError("Business name is required.")
        business = cls._repo().create(owner_user_id=owner_user_id, **fields)
        PermissionService.grant_owner(business_id=business.id, user_id=owner_user_id)
        return business

    @classmethod
    def update_business(cls, business_id: str, **fields) -> Business:
        updated = cls._repo().update(business_id, **fields)
        if updated is None:
            raise ValueError("No business found with that ID.")
        return updated

    @classmethod
    def get_business_for_user(cls, owner_user_id: str):
        """Returns the user's ACTIVE business, or their most recently
        updated one if no active selection has been made yet."""
        businesses = cls._repo().get_by_owner(owner_user_id)
        if not businesses:
            return None

        active_id = cls._repo().get_active_business_id(owner_user_id)
        if active_id:
            for business in businesses:
                if business.id == active_id:
                    return business
        return businesses[0]  # Most recently updated, per get_by_owner's ORDER BY.

    @classmethod
    def get_businesses_for_user(cls, owner_user_id: str):
        """Returns ALL businesses owned by this user (supports multiple businesses)."""
        return cls._repo().get_by_owner(owner_user_id)

    @classmethod
    def set_active_business(cls, owner_user_id: str, business_id: str) -> Business:
        business = cls._repo().get_by_id(business_id)
        if business is None or business.owner_user_id != owner_user_id:
            raise ValueError("That business does not belong to this user.")
        cls._repo().set_active_business_id(owner_user_id, business_id)
        return business
PYEOF_FILE

cat > frontend/services/dashboard_service.py << 'PYEOF_FILE'
"""
dashboard_service.py

Supplies data to the Dashboard screen.

Phase 10: revenue, expenses, and net cash movement are now REAL
figures calculated from persisted transactions via FinanceService —
no longer mock "R 0.00".

Phase 11: employee count is now REAL too — the count of employees
with employment_status='active' for this business, via
EmployeeService. Orders remains the one mock figure left, and the
alert text below has been updated accordingly so nothing invented is
silently presented as real.
"""

from typing import List, TypedDict

from services.business_repository import REGISTRATION_STATUS_CHOICES, VERIFIED
from services.employee_service import EmployeeService
from services.finance_service import FinanceService
from utils.formatters import format_cents_as_rand


class Transaction(TypedDict):
    description: str
    amount: str
    date: str


class Alert(TypedDict):
    message: str
    level: str


class DashboardData(TypedDict):
    revenue: str
    expenses: str
    net_cash_movement: str
    orders: str
    employees: str
    business_summary: str
    recent_transactions: List[Transaction]
    alerts: List[Alert]


def _status_label(status: str) -> str:
    if status == VERIFIED:
        return "Verified"
    return REGISTRATION_STATUS_CHOICES.get(status, status)


class DashboardService:
    """Provides dashboard data. Revenue, expenses, and employee count are real; orders is still mock."""

    @staticmethod
    def get_dashboard_data(business=None) -> DashboardData:
        if business:
            business_summary = (
                f"{business.name} — {business.business_type}, {business.industry} "
                f"({business.province}). Registration: {_status_label(business.registration_status)}."
            )
            totals = FinanceService.get_totals(business.id)
            revenue = format_cents_as_rand(totals["income_cents"])
            expenses = format_cents_as_rand(totals["expense_cents"])
            net_cash_movement = format_cents_as_rand(totals["net_cents"])

            recent = FinanceService.list_transactions(business.id)[:5]
            recent_transactions = [
                {
                    "description": t.description,
                    "amount": format_cents_as_rand(
                        t.amount_cents if t.transaction_type == "income" else -t.amount_cents
                    ),
                    "date": t.transaction_date,
                }
                for t in recent
            ]
            if not recent_transactions:
                recent_transactions = [
                    {"description": "No transactions recorded yet.", "amount": "", "date": ""}
                ]

            employee_counts = EmployeeService.get_counts(business.id)
            employees = str(employee_counts["active"])

            alerts = [
                {
                    "message": "Orders shown below is demo data — that module is not yet "
                               "implemented. Revenue, expenses, and active employee count "
                               "reflect your actual recorded data.",
                    "level": "info",
                },
            ]
        else:
            business_summary = "No business profile found — demo data shown."
            revenue = "R 0.00"
            expenses = "R 0.00"
            net_cash_movement = "R 0.00"
            employees = "0"
            recent_transactions = [
                {"description": "Demo transaction", "amount": "R 0.00", "date": "—"},
            ]
            alerts = [
                {
                    "message": "This is demo data. Connect a backend to see real information.",
                    "level": "info",
                },
            ]

        return {
            "revenue": revenue,
            "expenses": expenses,
            "net_cash_movement": net_cash_movement,
            "orders": "0",
            "employees": employees,
            "business_summary": business_summary,
            "recent_transactions": recent_transactions,
            "alerts": alerts,
        }
PYEOF_FILE

cat > frontend/screens/employees/employees_screen.py << 'PYEOF_FILE'
"""
employees_screen.py

Employee management for the active business: summary counts, an
add-employee form, and a list of recorded employees with the ability
to change employment status.

Every mutating action (add, change status) passes
app_session.current_user.id as acting_user_id — EmployeeService
checks real permissions against business_memberships before doing
anything, it does not just trust that this screen is open.

IMPORTANT: changing an employee's "Role" dropdown here is an HR
label only. It does NOT grant that person any system permission —
see services/employee_repository.py's docstring. This screen does
not pretend otherwise; there is no "make this an admin login" control
here, because no such feature exists yet.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton, SecondaryButton
from components.cards.card import Card, StatCard
from components.inputs.inputs import TextInputField
from components.tables.table import DataTable
from screens.base_screen import BaseScreen
from services.employee_repository import ACTIVE, EMPLOYEE_ROLES, EMPLOYMENT_STATUSES, INACTIVE, ON_LEAVE
from services.employee_service import EmployeeService
from services.permission_service import PermissionError
from styles.theme import Theme
from utils.validators import validate_iso_date

ROLE_LABELS = {"owner": "Owner", "admin": "Admin", "manager": "Manager", "employee": "Employee"}
ROLE_BY_LABEL = {label: code for code, label in ROLE_LABELS.items()}

STATUS_LABELS = {ACTIVE: "Active", INACTIVE: "Inactive", ON_LEAVE: "On Leave"}
STATUS_BY_LABEL = {label: code for code, label in STATUS_LABELS.items()}


class EmployeesScreen(BaseScreen):
    """Employee management for the active business."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Employees", subtitle="Manage who works at your business", **kwargs
        )
        self._render()

    def _render(self) -> None:
        """(Re)builds this screen's entire content from current data."""
        self.content.clear_widgets()
        business = app_session.current_business

        if business is None:
            self.content.add_widget(
                Label(
                    text="No active business. Complete business setup first.",
                    color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
                )
            )
            return

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical", spacing=Theme.dimensions.SECTION_SPACING, size_hint=(1, None)
        )
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(self._build_summary_row(business.id))
        body.add_widget(self._build_add_form(business.id))
        body.add_widget(self._build_employee_list(business.id))

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_summary_row(self, business_id: str):
        counts = EmployeeService.get_counts(business_id)
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=100,
            spacing=Theme.dimensions.SPACE_MD,
        )
        row.add_widget(StatCard(
            label="Active", value=str(counts["active"]),
            accent_color=Theme.colors.SAGE, size_hint=(1, 1),
        ))
        row.add_widget(StatCard(label="On Leave", value=str(counts["on_leave"]), size_hint=(1, 1)))
        row.add_widget(StatCard(label="Inactive", value=str(counts["inactive"]), size_hint=(1, 1)))
        return row

    def _build_add_form(self, business_id: str):
        card = Card(title="Add Employee", size_hint=(1, None), height=460)

        name_field = TextInputField(label="Full name", placeholder="e.g. Thandiwe Khumalo")
        email_field = TextInputField(label="Email (optional)", placeholder="e.g. thandiwe@example.com")
        phone_field = TextInputField(label="Phone (optional)", placeholder="e.g. 071 234 5678")
        job_title_field = TextInputField(label="Job title", placeholder="e.g. Sales Associate")

        role_spinner = Spinner(
            text=ROLE_LABELS["employee"], values=list(ROLE_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        status_spinner = Spinner(
            text=STATUS_LABELS[ACTIVE], values=list(STATUS_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        start_date_field = TextInputField(label="Start date (YYYY-MM-DD)", placeholder="e.g. 2026-10-11")

        error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        def on_submit(*_args):
            error_label.text = ""
            user = app_session.current_user

            if user is None:
                error_label.text = "You must be signed in to add an employee."
                return
            if not name_field.text.strip():
                error_label.text = "Full name is required."
                return
            if not job_title_field.text.strip():
                error_label.text = "Job title is required."
                return
            try:
                start_date = validate_iso_date(start_date_field.text).isoformat()
            except ValueError as error:
                error_label.text = str(error)
                return

            try:
                EmployeeService.add_employee(
                    acting_user_id=user.id, business_id=business_id,
                    full_name=name_field.text.strip(), job_title=job_title_field.text.strip(),
                    role=ROLE_BY_LABEL[role_spinner.text],
                    employment_status=STATUS_BY_LABEL[status_spinner.text],
                    start_date=start_date, email=email_field.text.strip(), phone=phone_field.text.strip(),
                )
            except PermissionError as error:
                error_label.text = str(error)
                return
            except ValueError as error:
                error_label.text = f"Could not save: {error}"
                return

            self._render()  # Refresh in place — same pattern as FinanceScreen.

        submit_button = PrimaryButton(text="Add Employee")
        submit_button.width = 440
        submit_button.bind(on_release=on_submit)

        for widget in [
            name_field, email_field, phone_field, job_title_field,
            role_spinner, status_spinner, start_date_field, error_label, submit_button,
        ]:
            card.add_widget(widget)

        return card

    def _build_employee_list(self, business_id: str):
        employees = EmployeeService.list_employees(business_id)

        if not employees:
            card = Card(title="Employees", size_hint=(1, None), height=90)
            card.add_widget(
                Label(
                    text="No employees recorded yet.", color=Theme.colors.TEXT_SECONDARY,
                    font_size=Theme.typography.BODY,
                )
            )
            return card

        rows = [
            (e.full_name, e.job_title, ROLE_LABELS[e.role], STATUS_LABELS[e.employment_status], e.start_date)
            for e in employees
        ]
        card = Card(title="Employees", size_hint=(1, None), height=90 + min(len(rows), 10) * 40 + 70)
        card.add_widget(
            DataTable(
                columns=["Name", "Job Title", "Role", "Status", "Start Date"],
                rows=rows,
                size_hint=(1, None),
                height=40 + min(len(rows), 10) * 40,
            )
        )
        card.add_widget(self._build_status_change_row(business_id, employees))
        return card

    def _build_status_change_row(self, business_id: str, employees: list):
        """A simple control to change one employee's employment status
        without a separate detail screen — picks an employee by name,
        picks a new status, applies it."""
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            spacing=Theme.dimensions.SPACE_SM,
        )
        names_to_ids = {e.full_name: e.id for e in employees}

        employee_spinner = Spinner(
            text=employees[0].full_name, values=list(names_to_ids.keys()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        new_status_spinner = Spinner(
            text=STATUS_LABELS[ACTIVE], values=list(STATUS_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )

        def on_change_status(*_args):
            user = app_session.current_user
            if user is None:
                return
            employee_id = names_to_ids[employee_spinner.text]
            try:
                EmployeeService.set_employment_status(
                    acting_user_id=user.id, business_id=business_id,
                    employee_id=employee_id, employment_status=STATUS_BY_LABEL[new_status_spinner.text],
                )
            except (PermissionError, ValueError):
                pass  # Status-change row has no error label; a full detail screen is future work.
            self._render()

        change_button = SecondaryButton(text="Change Status")
        change_button.bind(on_release=on_change_status)

        row.add_widget(employee_spinner)
        row.add_widget(new_status_spinner)
        row.add_widget(change_button)
        return row
PYEOF_FILE

cat > frontend/layouts/main_layout.py << 'PYEOF_FILE'
"""
main_layout.py

Assembles the full Business OS application shell:

    ┌───────────────────────────────┐
    │            TopBar             │
    ├───────────┬────────────────────┤
    │  Sidebar  │   ScreenManager    │
    │           │  (active section)  │
    └───────────┴────────────────────┘

Rebuilt from scratch by app.py whenever the theme mode OR the active
business changes (see app.py's _on_theme_changed / _on_business_changed),
so every widget here always reads the CURRENTLY active palette/business.
initial_section lets app.py restore whichever section the user was
viewing before that rebuild.

IMPORTANT: this inner ScreenManager uses NoTransition. A ScreenManager
always auto-selects its FIRST added screen as `.current` — here,
Dashboard is added before other sections, so the instant this
ScreenManager is built, `.current` silently becomes "dashboard". Then,
at the end of __init__, navigate_to(start_section) changes `.current`
a SECOND time to whatever section the user actually had open (e.g.
"settings"). With the default SlideTransition, that second change
animates visibly — this is exactly what caused the "theme switch
flashes Dashboard, then slides back to Settings" bug. NoTransition
makes that second change instant, so there is nothing to see.

The F12 key binding lives in app.py, NOT here — MainLayout only
exposes toggle_showcase(). Binding Window.on_key_down inside this
class would stack a NEW duplicate handler on the global Window every
single time MainLayout is rebuilt (every theme change, every business
switch) — old handlers are never removed, so pressing F12 would fire
all of them at once.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, NoTransition

from app.navigation import SECTIONS, DEFAULT_SECTION, NavigationManager
from components.base.background_mixin import BackgroundColorMixin
from layouts.sidebar import Sidebar
from layouts.topbar import TopBar
from screens.dashboard.dashboard_screen import DashboardScreen
from screens.dev.component_showcase_screen import ComponentShowcaseScreen  # DEV ONLY
from screens.employees.employees_screen import EmployeesScreen
from screens.finance.finance_screen import FinanceScreen
from screens.placeholder.placeholder_screen import PlaceholderScreen
from screens.settings.settings_screen import SettingsScreen
from styles.theme import Theme

DEV_SHOWCASE_SCREEN_NAME = "dev_showcase"  # DEV ONLY


class MainLayout(BackgroundColorMixin, BoxLayout):
    """The root shell widget for the entire Business OS application."""

    def __init__(self, initial_section: str = None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.set_background_color(Theme.colors.BACKGROUND)

        start_section = initial_section or DEFAULT_SECTION

        # 1. Build the content area. "dashboard", "settings",
        #    "finance", and "employees" get real screens; every other
        #    section still gets a placeholder.
        # NoTransition: see the module docstring above for why this
        # matters — it is the fix for the theme/business-switch glitch.
        self.screen_manager = ScreenManager(transition=NoTransition())
        for key, label in SECTIONS:
            if key == "dashboard":
                self.screen_manager.add_widget(DashboardScreen(name=key))
            elif key == "settings":
                self.screen_manager.add_widget(SettingsScreen(name=key))
            elif key == "finance":
                self.screen_manager.add_widget(FinanceScreen(name=key))
            elif key == "employees":
                self.screen_manager.add_widget(EmployeesScreen(name=key))
            else:
                self.screen_manager.add_widget(PlaceholderScreen(section_title=label, name=key))

        # DEV ONLY — register the component showcase screen (not a real section).
        self.screen_manager.add_widget(ComponentShowcaseScreen(name=DEV_SHOWCASE_SCREEN_NAME))
        self._pre_showcase_section = None

        # 2. Build the topbar and wire up centralized navigation.
        self.topbar = TopBar()
        self.navigation_manager = NavigationManager(self.screen_manager, self.topbar)

        # 3. Build the sidebar, restoring whichever section was active.
        self.sidebar = Sidebar(navigation_manager=self.navigation_manager, initial_section=start_section)

        # 4. Assemble: topbar on top, sidebar + content area below it.
        body = BoxLayout(orientation="horizontal")
        body.add_widget(self.sidebar)
        body.add_widget(self.screen_manager)

        self.add_widget(self.topbar)
        self.add_widget(body)

        # 5. Show the correct starting section.
        self.navigation_manager.navigate_to(start_section)

    def toggle_showcase(self) -> None:  # DEV ONLY
        """Toggle the F12 component showcase screen. Called by app.py's key handler."""
        if self.screen_manager.current == DEV_SHOWCASE_SCREEN_NAME:
            self.navigation_manager._current_section = None  # force topbar/title refresh
            self.navigation_manager.navigate_to(self._pre_showcase_section or DEFAULT_SECTION)
        else:
            self._pre_showcase_section = self.navigation_manager.current_section
            self.screen_manager.current = DEV_SHOWCASE_SCREEN_NAME
            self.topbar.update_title("Component Showcase (Dev)")
PYEOF_FILE

cat > tests/conftest.py << 'PYEOF_FILE'
import sys
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
sys.path.insert(0, str(FRONTEND_DIR))

from services.database import get_connection  # noqa: E402
from services.business_repository import BusinessRepository  # noqa: E402
from services.user_repository import UserRepository  # noqa: E402
from services.business_service import BusinessService  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.transaction_repository import TransactionRepository  # noqa: E402
from services.finance_service import FinanceService  # noqa: E402
from services.membership_repository import MembershipRepository  # noqa: E402
from services.permission_service import PermissionService  # noqa: E402
from services.employee_repository import EmployeeRepository  # noqa: E402
from services.employee_service import EmployeeService  # noqa: E402


@pytest.fixture
def temp_db(tmp_path):
    """A fresh, isolated SQLite database file per test — never touches real app data."""
    db_path = tmp_path / "test_skurge.db"
    connection = get_connection(db_path=db_path)
    yield connection
    connection.close()


@pytest.fixture
def business_repo(temp_db):
    return BusinessRepository(temp_db)


@pytest.fixture
def user_repo(temp_db):
    return UserRepository(temp_db)


@pytest.fixture
def business_service(business_repo, temp_db):
    # BusinessService.create_business() now also calls
    # PermissionService.grant_owner() internally (Phase 11) — wire
    # PermissionService to the SAME temp database so that call never
    # falls through to the real one.
    from services.membership_repository import MembershipRepository
    from services.permission_service import PermissionService as _PermissionService

    BusinessService.configure_repository(business_repo)
    _PermissionService.configure_repository(MembershipRepository(temp_db))
    yield BusinessService
    BusinessService.configure_repository(None)
    _PermissionService.configure_repository(None)


@pytest.fixture
def auth_service(user_repo):
    AuthService.configure_repository(user_repo)
    yield AuthService
    AuthService.configure_repository(None)


@pytest.fixture
def transaction_repo(temp_db):
    return TransactionRepository(temp_db)


@pytest.fixture
def finance_service(transaction_repo):
    FinanceService.configure_repository(transaction_repo)
    yield FinanceService
    FinanceService.configure_repository(None)


@pytest.fixture
def membership_repo(temp_db):
    return MembershipRepository(temp_db)


@pytest.fixture
def permission_service(membership_repo):
    PermissionService.configure_repository(membership_repo)
    yield PermissionService
    PermissionService.configure_repository(None)


@pytest.fixture
def employee_repo(temp_db):
    return EmployeeRepository(temp_db)


@pytest.fixture
def employee_service(employee_repo, permission_service):
    EmployeeService.configure_repository(employee_repo)
    yield EmployeeService
    EmployeeService.configure_repository(None)
PYEOF_FILE

cat > tests/test_permission_service.py << 'PYEOF_FILE'
import pytest

from services.membership_repository import ADMIN, OWNER


def test_grant_owner_creates_membership(permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    assert permission_service.get_role("biz-1", "user-1") == OWNER


def test_user_with_no_membership_has_no_role(permission_service):
    assert permission_service.get_role("biz-1", "stranger") is None


def test_owner_has_manage_employees_permission(permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    assert permission_service.has_permission("biz-1", "user-1", "manage_employees") is True


def test_stranger_lacks_permission(permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    assert permission_service.has_permission("biz-1", "stranger", "manage_employees") is False


def test_require_permission_raises_for_unauthorized_user(permission_service):
    from services.permission_service import PermissionError

    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    with pytest.raises(PermissionError):
        permission_service.require_permission("biz-1", "stranger", "manage_employees")


def test_require_permission_passes_silently_for_authorized_user(permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    permission_service.require_permission("biz-1", "user-1", "manage_employees")  # should not raise


def test_employee_role_label_has_no_permissions(permission_service, membership_repo):
    """An employee-role membership (not owner/admin) should NOT be
    able to manage employees or change employment status."""
    membership_repo.create(business_id="biz-1", user_id="user-2", role="employee")
    assert permission_service.has_permission("biz-1", "user-2", "manage_employees") is False
    assert permission_service.has_permission("biz-1", "user-2", "change_employment_status") is False


def test_manager_can_record_transactions_but_not_manage_employees(permission_service, membership_repo):
    membership_repo.create(business_id="biz-1", user_id="user-3", role="manager")
    assert permission_service.has_permission("biz-1", "user-3", "record_transactions") is True
    assert permission_service.has_permission("biz-1", "user-3", "manage_employees") is False


def test_membership_scoped_to_business(permission_service):
    permission_service.grant_owner(business_id="biz-A", user_id="user-1")
    # Same user has NO role on a different business.
    assert permission_service.get_role("biz-B", "user-1") is None


def test_unknown_permission_name_raises(permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="user-1")
    with pytest.raises(ValueError):
        permission_service.has_permission("biz-1", "user-1", "launch_nuclear_missiles")
PYEOF_FILE

cat > tests/test_employee_repository.py << 'PYEOF_FILE'
import pytest

from services.database import get_connection
from services.employee_repository import ACTIVE, EmployeeRepository, INACTIVE, ON_LEAVE


def _sample(**overrides):
    fields = dict(
        business_id="biz-1", full_name="Thandiwe Khumalo", job_title="Sales Associate",
        role="employee", employment_status=ACTIVE, start_date="2026-01-15",
    )
    fields.update(overrides)
    return fields


def test_create_employee(employee_repo):
    e = employee_repo.create(**_sample())
    assert e.id
    assert e.full_name == "Thandiwe Khumalo"
    assert e.employment_status == ACTIVE


def test_reject_missing_full_name(employee_repo):
    with pytest.raises(ValueError):
        employee_repo.create(**_sample(full_name="  "))


def test_reject_missing_job_title(employee_repo):
    with pytest.raises(ValueError):
        employee_repo.create(**_sample(job_title=""))


def test_reject_invalid_role(employee_repo):
    with pytest.raises(ValueError):
        employee_repo.create(**_sample(role="superadmin"))


def test_reject_invalid_employment_status(employee_repo):
    with pytest.raises(ValueError):
        employee_repo.create(**_sample(employment_status="on_vacation"))


def test_reject_missing_start_date(employee_repo):
    with pytest.raises(ValueError):
        employee_repo.create(**_sample(start_date=""))


def test_get_by_id(employee_repo):
    created = employee_repo.create(**_sample())
    fetched = employee_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.full_name == "Thandiwe Khumalo"


def test_get_by_id_missing_returns_none(employee_repo):
    assert employee_repo.get_by_id("does-not-exist") is None


def test_list_for_business_sorted_by_name(employee_repo):
    employee_repo.create(**_sample(full_name="Zanele Dube"))
    employee_repo.create(**_sample(full_name="Amahle Nkosi"))
    results = employee_repo.list_for_business("biz-1")
    assert [e.full_name for e in results] == ["Amahle Nkosi", "Zanele Dube"]


def test_list_filters_by_employment_status(employee_repo):
    employee_repo.create(**_sample(full_name="Active One", employment_status=ACTIVE))
    employee_repo.create(**_sample(full_name="Inactive One", employment_status=INACTIVE))
    active_only = employee_repo.list_for_business("biz-1", employment_status=ACTIVE)
    assert len(active_only) == 1
    assert active_only[0].full_name == "Active One"


def test_update_employee_details(employee_repo):
    created = employee_repo.create(**_sample())
    updated = employee_repo.update(created.id, job_title="Senior Sales Associate")
    assert updated.job_title == "Senior Sales Associate"
    assert updated.id == created.id  # same row, not a new one


def test_update_missing_employee_returns_none(employee_repo):
    assert employee_repo.update("does-not-exist", job_title="X") is None


def test_change_employment_status(employee_repo):
    created = employee_repo.create(**_sample(employment_status=ACTIVE))
    updated = employee_repo.update(created.id, employment_status=ON_LEAVE)
    assert updated.employment_status == ON_LEAVE


def test_business_isolation(employee_repo):
    employee_repo.create(**_sample(business_id="biz-A", full_name="A's employee"))
    employee_repo.create(**_sample(business_id="biz-B", full_name="B's employee"))
    a_employees = employee_repo.list_for_business("biz-A")
    assert len(a_employees) == 1
    assert a_employees[0].full_name == "A's employee"


def test_counts_by_status(employee_repo):
    employee_repo.create(**_sample(full_name="Active 1", employment_status=ACTIVE))
    employee_repo.create(**_sample(full_name="Active 2", employment_status=ACTIVE))
    employee_repo.create(**_sample(full_name="Inactive 1", employment_status=INACTIVE))
    employee_repo.create(**_sample(full_name="On Leave 1", employment_status=ON_LEAVE))
    counts = employee_repo.count_by_status("biz-1")
    assert counts == {"active": 2, "inactive": 1, "on_leave": 1}


def test_counts_for_business_with_no_employees_are_zero(employee_repo):
    assert employee_repo.count_by_status("biz-empty") == {"active": 0, "inactive": 0, "on_leave": 0}


def test_data_survives_closing_and_reopening_database(tmp_path):
    db_path = tmp_path / "employee_persist_test.db"

    conn_1 = get_connection(db_path=db_path)
    repo_1 = EmployeeRepository(conn_1)
    created = repo_1.create(**_sample())
    conn_1.close()

    conn_2 = get_connection(db_path=db_path)
    repo_2 = EmployeeRepository(conn_2)
    fetched = repo_2.get_by_id(created.id)
    conn_2.close()

    assert fetched is not None
    assert fetched.full_name == "Thandiwe Khumalo"
PYEOF_FILE

cat > tests/test_employee_service.py << 'PYEOF_FILE'
import pytest

from services.employee_repository import ACTIVE, ON_LEAVE
from services.permission_service import PermissionError


def _sample(**overrides):
    fields = dict(
        business_id="biz-1", full_name="Thandiwe Khumalo", job_title="Sales Associate",
        role="employee", employment_status=ACTIVE, start_date="2026-01-15",
    )
    fields.update(overrides)
    return fields


def test_owner_can_add_employee(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    e = employee_service.add_employee(acting_user_id="owner-1", **_sample())
    assert e.full_name == "Thandiwe Khumalo"


def test_user_without_membership_cannot_add_employee(employee_service, permission_service):
    with pytest.raises(PermissionError):
        employee_service.add_employee(acting_user_id="stranger", **_sample())


def test_employee_role_user_cannot_add_employee(employee_service, permission_service, membership_repo):
    membership_repo.create(business_id="biz-1", user_id="user-2", role="employee")
    with pytest.raises(PermissionError):
        employee_service.add_employee(acting_user_id="user-2", **_sample())


def test_admin_can_add_employee(employee_service, permission_service, membership_repo):
    membership_repo.create(business_id="biz-1", user_id="admin-1", role="admin")
    e = employee_service.add_employee(acting_user_id="admin-1", **_sample())
    assert e.full_name == "Thandiwe Khumalo"


def test_invalid_email_rejected(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    with pytest.raises(ValueError):
        employee_service.add_employee(acting_user_id="owner-1", **_sample(email="not-an-email"))


def test_valid_email_accepted(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    e = employee_service.add_employee(acting_user_id="owner-1", **_sample(email="thandiwe@example.com"))
    assert e.email == "thandiwe@example.com"


def test_empty_email_is_allowed(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    e = employee_service.add_employee(acting_user_id="owner-1", **_sample(email=""))
    assert e.email == ""


def test_invalid_start_date_rejected(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    with pytest.raises(ValueError):
        employee_service.add_employee(acting_user_id="owner-1", **_sample(start_date="15/01/2026"))


def test_update_employee_requires_permission(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    created = employee_service.add_employee(acting_user_id="owner-1", **_sample())

    with pytest.raises(PermissionError):
        employee_service.update_employee(
            acting_user_id="stranger", business_id="biz-1", employee_id=created.id, job_title="Hacked"
        )


def test_update_employee_succeeds_for_owner(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    created = employee_service.add_employee(acting_user_id="owner-1", **_sample())

    updated = employee_service.update_employee(
        acting_user_id="owner-1", business_id="biz-1", employee_id=created.id, job_title="Senior Sales Associate"
    )
    assert updated.job_title == "Senior Sales Associate"


def test_set_employment_status_requires_permission(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    created = employee_service.add_employee(acting_user_id="owner-1", **_sample())

    with pytest.raises(PermissionError):
        employee_service.set_employment_status(
            acting_user_id="stranger", business_id="biz-1", employee_id=created.id, employment_status=ON_LEAVE
        )


def test_set_employment_status_succeeds_for_owner(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-1", user_id="owner-1")
    created = employee_service.add_employee(acting_user_id="owner-1", **_sample())

    updated = employee_service.set_employment_status(
        acting_user_id="owner-1", business_id="biz-1", employee_id=created.id, employment_status=ON_LEAVE
    )
    assert updated.employment_status == ON_LEAVE


def test_list_employees_business_isolation(employee_service, permission_service):
    permission_service.grant_owner(business_id="biz-A", user_id="owner-1")
    permission_service.grant_owner(business_id="biz-B", user_id="owner-2")
    employee_service.add_employee(acting_user_id="owner-1", **_sample(business_id="biz-A", full_name="A's employee"))
    employee_service.add_employee(acting_user_id="owner-2", **_sample(business_id="biz-B", full_name="B's employee"))

    a_only = employee_service.list_employees("biz-A")
    assert len(a_only) == 1
    assert a_only[0].full_name == "A's employee"


def test_get_counts_empty_business(employee_service):
    assert employee_service.get_counts("biz-empty") == {"active": 0, "inactive": 0, "on_leave": 0}
PYEOF_FILE

cat > tests/test_integration.py << 'PYEOF_FILE'
from services.business_repository import DRAFT


def _sample_fields(**overrides):
    fields = dict(
        name="Khumalo Retail",
        business_type="Pty Ltd",
        industry="Retail",
        registration_status=DRAFT,
        province="Gauteng",
    )
    fields.update(overrides)
    return fields


def test_saved_business_is_available_to_dashboard_service(business_service, finance_service, employee_service):
    """Mirrors what BusinessSetupScreen -> DashboardScreen actually do:
    create through the service layer, then read it back the same way
    DashboardService.get_dashboard_data(business=...) would."""
    from services.dashboard_service import DashboardService

    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    data = DashboardService.get_dashboard_data(business=business)
    assert "Khumalo Retail" in data["business_summary"]
    assert data["revenue"] == "R 0.00"  # no transactions recorded yet
    assert data["employees"] == "0"  # no employees recorded yet


def test_dashboard_handles_missing_business_without_crashing():
    from services.dashboard_service import DashboardService

    data = DashboardService.get_dashboard_data(business=None)
    assert "business_summary" in data
    assert isinstance(data["business_summary"], str)


def test_recorded_transactions_flow_through_to_dashboard_totals(business_service, finance_service, employee_service):
    """The real end-to-end seam Phase 10 is about: FinanceService ->
    DashboardService, using real persisted transactions."""
    from services.dashboard_service import DashboardService

    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    finance_service.record_income(
        business_id=business.id, description="Product sale", amount_cents=500000,
        category="Sales", transaction_date="2026-10-01",
    )
    finance_service.record_expense(
        business_id=business.id, description="Rent", amount_cents=200000,
        category="Rent", transaction_date="2026-10-02",
    )

    data = DashboardService.get_dashboard_data(business=business)
    assert data["revenue"] == "R 5,000.00"
    assert data["expenses"] == "R 2,000.00"
    assert data["net_cash_movement"] == "R 3,000.00"
    assert len(data["recent_transactions"]) == 2


def test_dashboard_totals_isolated_by_business(business_service, finance_service, employee_service):
    business_a = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Business A"))
    business_b = business_service.create_business(owner_user_id="user-2", **_sample_fields(name="Business B"))

    finance_service.record_income(
        business_id=business_a.id, description="A sale", amount_cents=100000,
        category="Sales", transaction_date="2026-10-01",
    )
    finance_service.record_income(
        business_id=business_b.id, description="B sale", amount_cents=999999,
        category="Sales", transaction_date="2026-10-01",
    )

    from services.dashboard_service import DashboardService
    data_a = DashboardService.get_dashboard_data(business=business_a)
    assert data_a["revenue"] == "R 1,000.00"  # NOT mixed with business B's figure


def test_recorded_employees_flow_through_to_dashboard_count(business_service, finance_service, employee_service, permission_service):
    """The real end-to-end seam Phase 11 is about: EmployeeService ->
    DashboardService, using real persisted, permission-checked employee records."""
    from services.dashboard_service import DashboardService
    from services.employee_repository import ACTIVE, ON_LEAVE

    business = business_service.create_business(owner_user_id="owner-1", **_sample_fields())

    employee_service.add_employee(
        acting_user_id="owner-1", business_id=business.id, full_name="Active Employee",
        job_title="Cashier", role="employee", employment_status=ACTIVE, start_date="2026-01-01",
    )
    employee_service.add_employee(
        acting_user_id="owner-1", business_id=business.id, full_name="On Leave Employee",
        job_title="Cashier", role="employee", employment_status=ON_LEAVE, start_date="2026-01-01",
    )

    data = DashboardService.get_dashboard_data(business=business)
    assert data["employees"] == "1"  # only the ACTIVE one is counted


def test_employee_counts_isolated_by_business(business_service, finance_service, employee_service, permission_service):
    from services.dashboard_service import DashboardService
    from services.employee_repository import ACTIVE

    business_a = business_service.create_business(owner_user_id="owner-a", **_sample_fields(name="Business A"))
    business_b = business_service.create_business(owner_user_id="owner-b", **_sample_fields(name="Business B"))

    employee_service.add_employee(
        acting_user_id="owner-a", business_id=business_a.id, full_name="A's Employee",
        job_title="Cashier", role="employee", employment_status=ACTIVE, start_date="2026-01-01",
    )
    employee_service.add_employee(
        acting_user_id="owner-b", business_id=business_b.id, full_name="B's Employee 1",
        job_title="Cashier", role="employee", employment_status=ACTIVE, start_date="2026-01-01",
    )
    employee_service.add_employee(
        acting_user_id="owner-b", business_id=business_b.id, full_name="B's Employee 2",
        job_title="Cashier", role="employee", employment_status=ACTIVE, start_date="2026-01-01",
    )

    data_a = DashboardService.get_dashboard_data(business=business_a)
    assert data_a["employees"] == "1"  # NOT mixed with business B's 2 employees
PYEOF_FILE

touch frontend/screens/employees/__init__.py
echo "Phase 11 (Employees & Permissions) files created."