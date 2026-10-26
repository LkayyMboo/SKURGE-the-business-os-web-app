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
