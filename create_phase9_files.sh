#!/usr/bin/env bash
set -e
cd ~/business-os

# Create directories (safe even if they already exist)
mkdir -p frontend/app frontend/screens/business frontend/screens/settings frontend/services tests

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

cat > frontend/services/user_repository.py << 'PYEOF_FILE'
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
PYEOF_FILE

cat > frontend/services/business_repository.py << 'PYEOF_FILE'
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
        return cls._repo().create(owner_user_id=owner_user_id, **fields)

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

cat > frontend/services/auth_service.py << 'PYEOF_FILE'
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
PYEOF_FILE

cat > frontend/services/dashboard_service.py << 'PYEOF_FILE'
"""
dashboard_service.py

Supplies data to the Dashboard screen. Revenue/expenses/orders/
employees remain MOCK — no finance module exists yet. business_summary
reflects the real, persisted Business profile when one is available.
"""

from typing import List, TypedDict

from services.business_repository import REGISTRATION_STATUS_CHOICES, VERIFIED


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
    """Provides dashboard data. Mock numbers only — no finance backend yet."""

    @staticmethod
    def get_dashboard_data(business=None) -> DashboardData:
        if business:
            business_summary = (
                f"{business.name} — {business.business_type}, {business.industry} "
                f"({business.province}). Registration: {_status_label(business.registration_status)}."
            )
        else:
            business_summary = "No business profile found — demo data shown."

        return {
            "revenue": "R 0.00",
            "expenses": "R 0.00",
            "orders": "0",
            "employees": "0",
            "business_summary": business_summary,
            "recent_transactions": [
                {"description": "Demo transaction", "amount": "R 0.00", "date": "—"},
            ],
            "alerts": [
                {
                    "message": "This is demo data. Connect a backend to see real information.",
                    "level": "info",
                },
            ],
        }
PYEOF_FILE

cat > frontend/app/session.py << 'PYEOF_FILE'
"""
session.py

ONE source of truth for who is signed in and which business is active
for this run — same pattern as styles/theme.py's ThemeManager.

Phase 9: current_business is still the single "active" business the
rest of the app reads (dashboard, future modules), but the session
now also knows how to switch between a user's multiple businesses via
BusinessService, persisting that choice so it survives a restart.

Still in-memory for the User object itself within a run (the identity
of "who is this AppSession for" doesn't need its own persistence —
AuthService already persists credentials; session just holds today's
logged-in user object).
"""

from kivy.event import EventDispatcher
from kivy.properties import ObjectProperty

from services.business_service import BusinessService


class AppSession(EventDispatcher):
    """Holds the current user and current business for this app run."""

    current_user = ObjectProperty(None, allownone=True)
    current_business = ObjectProperty(None, allownone=True)

    def set_user(self, user) -> None:
        self.current_user = user

    def set_business(self, business) -> None:
        self.current_business = business

    def switch_business(self, business_id: str) -> None:
        """Switch the active business for the current user and persist the choice."""
        if self.current_user is None:
            raise ValueError("No user is signed in.")
        business = BusinessService.set_active_business(self.current_user.id, business_id)
        self.current_business = business

    def get_user_businesses(self):
        """All businesses owned by the current user, or an empty list if none/no user."""
        if self.current_user is None:
            return []
        return BusinessService.get_businesses_for_user(self.current_user.id)

    def require_business(self):
        """
        Return the current business, or raise if none is set.

        Future screens that need a business (Employees, Finance, etc.)
        call this instead of checking `current_business is None`
        themselves everywhere — one clear failure point instead of
        scattered None-checks.
        """
        if self.current_business is None:
            raise ValueError("No business is active for this session.")
        return self.current_business

    def clear(self) -> None:
        self.current_user = None
        self.current_business = None


app_session = AppSession()
PYEOF_FILE

cat > frontend/app/app.py << 'PYEOF_FILE'
"""
app.py

The root Kivy Application class for Business OS (SKURGE).

Owns the full startup flow:

    Splash -> Welcome -> Login/Register -> Business Setup -> Main App

Each onboarding screen only reports what happened via a callback
(e.g. on_login_success(user)) — it never decides what screen comes
next. This file owns all routing decisions, and app.session.app_session
holds the user/business so the rest of the app (e.g. DashboardScreen)
can read them without this file passing them around by hand.

Phase 9: app_session.current_business is now bound the same way
Theme.manager.mode already was — switching the active business (e.g.
from Settings) rebuilds MainLayout so DashboardScreen re-reads the
newly active business, without restarting the app.
"""

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition

from app.config import AppConfig
from app.session import app_session
from layouts.main_layout import MainLayout
from screens.business.business_registration import BusinessSetupScreen
from screens.onboarding.login_screen import LoginScreen
from screens.onboarding.register_screen import RegisterScreen
from screens.onboarding.welcome_screen import WelcomeScreen
from screens.splash.splash_screen import SplashScreen
from services.business_service import BusinessService
from styles.theme import Theme

SPLASH_SCREEN_NAME = "splash"
WELCOME_SCREEN_NAME = "welcome"
LOGIN_SCREEN_NAME = "login"
REGISTER_SCREEN_NAME = "register"
BUSINESS_SETUP_SCREEN_NAME = "business_setup"
MAIN_SCREEN_NAME = "main"
F12_KEY_CODE = 293  # DEV ONLY


class BusinessOSApp(App):
    """The main Business OS (SKURGE) Kivy application."""

    def build(self):
        self.title = AppConfig.APP_TITLE
        Window.size = (AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        Window.minimum_width = AppConfig.WINDOW_MIN_WIDTH
        Window.minimum_height = AppConfig.WINDOW_MIN_HEIGHT
        Window.clearcolor = Theme.colors.BACKGROUND

        self.root_manager = ScreenManager(transition=FadeTransition(duration=0.4))

        self.root_manager.add_widget(
            SplashScreen(name=SPLASH_SCREEN_NAME, on_complete=self._show_welcome)
        )
        self.root_manager.add_widget(
            WelcomeScreen(
                name=WELCOME_SCREEN_NAME,
                on_sign_in=self._show_login,
                on_create_account=self._show_register,
            )
        )
        self.root_manager.add_widget(
            LoginScreen(
                name=LOGIN_SCREEN_NAME,
                on_login_success=self._handle_authenticated,
                on_switch_to_register=self._show_register,
                on_back=self._show_welcome,
            )
        )
        self.root_manager.add_widget(
            RegisterScreen(
                name=REGISTER_SCREEN_NAME,
                on_register_success=self._handle_authenticated,
                on_switch_to_login=self._show_login,
                on_back=self._show_welcome,
            )
        )
        self.business_setup_screen = BusinessSetupScreen(
            name=BUSINESS_SETUP_SCREEN_NAME, on_complete=self._handle_business_created
        )
        self.root_manager.add_widget(self.business_setup_screen)

        self.main_screen = Screen(name=MAIN_SCREEN_NAME)
        self.main_layout = None
        self._build_main_layout()
        self.root_manager.add_widget(self.main_screen)

        Theme.manager.bind(mode=self._on_theme_changed)
        app_session.bind(current_business=self._on_business_changed)
        Window.bind(on_key_down=self._on_key_down)  # DEV ONLY (F12)

        self.root_manager.current = SPLASH_SCREEN_NAME
        return self.root_manager

    # --- Onboarding routing ---

    def _show_welcome(self, *_args) -> None:
        self.root_manager.current = WELCOME_SCREEN_NAME

    def _show_login(self, *_args) -> None:
        self.root_manager.current = LOGIN_SCREEN_NAME

    def _show_register(self, *_args) -> None:
        self.root_manager.current = REGISTER_SCREEN_NAME

    def _handle_authenticated(self, user) -> None:
        """Called after a successful login OR registration."""
        app_session.set_user(user)
        existing_business = BusinessService.get_business_for_user(user.id)
        if existing_business:
            app_session.set_business(existing_business)
            self._show_main_app()
        else:
            self.business_setup_screen.set_current_user(user)
            self.root_manager.current = BUSINESS_SETUP_SCREEN_NAME

    def _handle_business_created(self, business) -> None:
        app_session.set_business(business)
        self._show_main_app()

    # --- Main app / theme / business switch / dev showcase ---

    def _build_main_layout(self, initial_section: str = None) -> None:
        self.main_screen.clear_widgets()
        self.main_layout = MainLayout(initial_section=initial_section)
        self.main_screen.add_widget(self.main_layout)

    def _current_main_section(self):
        return self.main_layout.navigation_manager.current_section if self.main_layout else None

    def _on_theme_changed(self, _instance, _mode) -> None:
        current_section = self._current_main_section()
        Window.clearcolor = Theme.colors.BACKGROUND
        self._build_main_layout(initial_section=current_section)

    def _on_business_changed(self, _instance, _business) -> None:
        """Rebuilds the shell so DashboardScreen re-reads the newly
        active business — same mechanism as the theme-change rebuild."""
        if self.root_manager.current != MAIN_SCREEN_NAME:
            return  # Business was just set during onboarding; no main shell exists to refresh yet.
        current_section = self._current_main_section()
        self._build_main_layout(initial_section=current_section)

    def _on_key_down(self, _window, key, *_args):  # DEV ONLY
        if (
            key == F12_KEY_CODE
            and self.main_layout
            and self.root_manager.current == MAIN_SCREEN_NAME
        ):
            self.main_layout.toggle_showcase()

    def _show_main_app(self) -> None:
        self.root_manager.current = MAIN_SCREEN_NAME
PYEOF_FILE

cat > frontend/screens/business/business_registration.py << 'PYEOF_FILE'
"""
business_registration.py

Business setup screen — collects the new business's basic profile
right after sign-up/sign-in. Pure data entry: NO CIPC/SARS
verification happens here.

Phase 9: registration status is now one of the explicit backend
status codes (business_repository.DRAFT / REGISTRATION_IN_PROGRESS /
REGISTERED_DECLARED) rather than a free-text string the UI invented.
REGISTERED_DECLARED is explicitly labeled "as declared by you" —
SKURGE has not verified this with CIPC. VERIFIED is never offered
here; nothing in this app can set it yet.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.widget import Widget

from components.base.background_mixin import BackgroundColorMixin
from components.buttons.buttons import PrimaryButton
from components.inputs.inputs import TextInputField
from services.business_repository import REGISTRATION_STATUS_CHOICES
from services.business_service import BusinessService
from styles.theme import Theme

# label (shown to user) -> status code (stored in the database)
_STATUS_LABEL_TO_CODE = {label: code for code, label in REGISTRATION_STATUS_CHOICES.items()}
_STATUS_LABELS = list(_STATUS_LABEL_TO_CODE.keys())

BUSINESS_TYPE_OPTIONS = ["Sole Proprietor", "Partnership", "Pty Ltd", "Co-operative", "Other"]
INDUSTRY_OPTIONS = ["Retail", "Services", "Food & Beverage", "Manufacturing", "Technology", "Agriculture", "Other"]
PROVINCE_OPTIONS = [
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
    "Mpumalanga", "Northern Cape", "North West", "Western Cape",
]
TAX_STATUS_OPTIONS = ["Not registered", "Registered", "Not sure"]


def _labeled_spinner(label_text: str, options: list, default_text: str):
    """A label + Spinner pair, styled to match the rest of the inputs."""
    column = BoxLayout(
        orientation="vertical", size_hint=(1, None), height=62, spacing=Theme.dimensions.SPACE_XS
    )
    label = Label(
        text=label_text, color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.LABEL,
        size_hint=(1, None), height=18, halign="left", valign="middle",
    )
    label.bind(size=lambda *_: setattr(label, "text_size", label.size))
    spinner = Spinner(
        text=default_text, values=options, size_hint=(1, None),
        height=Theme.dimensions.INPUT_HEIGHT,
        background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
    )
    column.add_widget(label)
    column.add_widget(spinner)
    return column, spinner


class BusinessSetupScreen(BackgroundColorMixin, Screen):
    """Collects the new business's profile. Calls on_complete(business) when done."""

    def __init__(self, on_complete=None, **kwargs):
        super().__init__(**kwargs)
        self._on_complete = on_complete
        self._current_user = None
        self.set_background_color(Theme.colors.BACKGROUND)

        scroll = ScrollView(size_hint=(1, 1))

        outer = BoxLayout(orientation="vertical", size_hint=(1, None))
        outer.bind(minimum_height=outer.setter("height"))

        form = BoxLayout(
            orientation="vertical", size_hint=(None, None), width=480,
            spacing=Theme.dimensions.FIELD_SPACING, padding=(0, Theme.dimensions.SPACE_LG),
            pos_hint={"center_x": 0.5},
        )
        form.bind(minimum_height=form.setter("height"))

        title_label = Label(
            text="Tell us about your business", color=Theme.colors.TEXT_PRIMARY, bold=True,
            font_size=Theme.typography.TITLE, size_hint=(1, None), height=36,
        )
        subtitle_label = Label(
            text="This sets up your business profile. You can update it later in Business Settings.",
            color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=40,
        )
        subtitle_label.bind(size=lambda *_: setattr(subtitle_label, "text_size", subtitle_label.size))
        title_spacer = Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING)

        self.name_field = TextInputField(label="Business name *", placeholder="e.g. Khumalo Retail Pty Ltd")

        status_row, self.registration_status_spinner = _labeled_spinner(
            "Registration status *", _STATUS_LABELS, _STATUS_LABELS[0]
        )
        self.cipc_field = TextInputField(
            label="CIPC registration number (optional)",
            placeholder="Leave blank if not yet registered",
        )

        type_row, self.business_type_spinner = _labeled_spinner(
            "Business type *", BUSINESS_TYPE_OPTIONS, "Select business type"
        )
        industry_row, self.industry_spinner = _labeled_spinner(
            "Industry *", INDUSTRY_OPTIONS, "Select industry"
        )
        province_row, self.province_spinner = _labeled_spinner(
            "Province *", PROVINCE_OPTIONS, "Select province"
        )

        self.city_field = TextInputField(label="City / Town", placeholder="e.g. Mahikeng")
        self.primary_contact_field = TextInputField(
            label="Primary contact person", placeholder="e.g. Thandiwe Khumalo"
        )
        self.phone_field = TextInputField(label="Business phone", placeholder="e.g. 071 234 5678")
        self.contact_email_field = TextInputField(label="Business email", placeholder="e.g. info@business.co.za")

        tax_row, self.tax_status_spinner = _labeled_spinner(
            "Tax registration status (optional)", TAX_STATUS_OPTIONS, TAX_STATUS_OPTIONS[0]
        )

        self._error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        continue_button = PrimaryButton(text="Continue to Dashboard")
        continue_button.width = 480
        continue_button.bind(on_release=lambda *_: self._attempt_submit())

        required_note = Label(
            text="* Required field", color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.CAPTION, size_hint=(1, None), height=18,
        )

        for widget in [
            title_label, subtitle_label, title_spacer,
            self.name_field, status_row, self.cipc_field,
            type_row, industry_row, province_row, self.city_field,
            self.primary_contact_field, self.phone_field, self.contact_email_field,
            tax_row, required_note, self._error_label, continue_button,
        ]:
            form.add_widget(widget)

        outer.add_widget(form)
        scroll.add_widget(outer)
        self.add_widget(scroll)

    def set_current_user(self, user) -> None:
        """Called by app.py right before this screen is shown."""
        self._current_user = user
        if user and not self.contact_email_field.text:
            self.contact_email_field.text = user.email

    def _attempt_submit(self) -> None:
        self._error_label.text = ""

        name = self.name_field.text.strip()
        business_type = self.business_type_spinner.text
        industry = self.industry_spinner.text
        province = self.province_spinner.text
        phone = self.phone_field.text.strip()
        contact_email = self.contact_email_field.text.strip()

        if not name:
            self._error_label.text = "Business name is required."
            return
        if business_type == "Select business type":
            self._error_label.text = "Please select a business type."
            return
        if industry == "Select industry":
            self._error_label.text = "Please select an industry."
            return
        if province == "Select province":
            self._error_label.text = "Please select a province."
            return
        if not phone and not contact_email:
            self._error_label.text = "Please provide a business phone number or email."
            return
        if not self._current_user:
            self._error_label.text = "You must be signed in to continue."
            return

        registration_status_code = _STATUS_LABEL_TO_CODE[self.registration_status_spinner.text]

        try:
            business = BusinessService.create_business(
                owner_user_id=self._current_user.id,
                name=name,
                registration_status=registration_status_code,
                cipc_number=self.cipc_field.text.strip(),
                business_type=business_type,
                industry=industry,
                province=province,
                city=self.city_field.text.strip(),
                primary_contact_name=self.primary_contact_field.text.strip(),
                phone=phone,
                email=contact_email,
                tax_status=self.tax_status_spinner.text,
            )
        except ValueError as error:
            self._error_label.text = str(error)
            return

        if self._on_complete:
            self._on_complete(business)
PYEOF_FILE

cat > frontend/screens/settings/settings_screen.py << 'PYEOF_FILE'
"""
settings_screen.py

Business OS Settings screen.

Contains:
- Business: shows the active business and lets the user switch to
  another one of their businesses, if they have more than one.
- Appearance: Dark/Light mode toggle (Phase 7).

Other settings (account, security, company) stay placeholders until
later phases. Business-switching logic lives in AppSession /
BusinessService — this screen only calls app_session.switch_business()
and displays the result; it does not touch the database directly.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton, SecondaryButton
from components.cards.card import Card
from screens.base_screen import BaseScreen
from styles.theme import DARK, LIGHT, Theme


class SettingsScreen(BaseScreen):
    """The Business OS settings screen."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Settings", subtitle="Manage your application preferences", **kwargs
        )

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical", spacing=Theme.dimensions.SECTION_SPACING, size_hint=(1, None)
        )
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(self._build_business_card())
        body.add_widget(self._build_appearance_card())

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_business_card(self):
        businesses = app_session.get_user_businesses()
        current = app_session.current_business

        card = Card(title="Business", size_hint=(1, None), height=150)

        if not businesses:
            card.add_widget(
                Label(
                    text="No business profile found for this account.",
                    color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
                    size_hint=(1, None), height=24,
                )
            )
            return card

        active_label = Label(
            text=f"Active business: {current.name if current else 'None selected'}",
            color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=24, halign="left", valign="middle",
        )
        active_label.bind(size=lambda *_: setattr(active_label, "text_size", active_label.size))
        card.add_widget(active_label)

        if len(businesses) > 1:
            names_by_id = {b.id: b.name for b in businesses}
            id_by_name = {b.name: b.id for b in businesses}

            switch_row = BoxLayout(
                orientation="horizontal", size_hint=(1, None),
                height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM,
            )
            spinner = Spinner(
                text=current.name if current else businesses[0].name,
                values=list(names_by_id.values()),
                size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
                background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
            )
            switch_button = SecondaryButton(text="Switch")
            switch_button.bind(
                on_release=lambda *_: app_session.switch_business(id_by_name[spinner.text])
            )
            switch_row.add_widget(spinner)
            switch_row.add_widget(switch_button)
            card.add_widget(switch_row)
        else:
            card.height = 90  # No switcher needed for a single business.

        return card

    def _build_appearance_card(self):
        card = Card(title="Appearance", size_hint=(1, None), height=140)

        description = Label(
            text="Choose how SKURGE looks on this device.",
            color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=24, halign="left", valign="middle",
        )
        description.bind(size=lambda *_: setattr(description, "text_size", description.size))
        card.add_widget(description)

        button_row = BoxLayout(
            orientation="horizontal", size_hint=(1, None),
            height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM,
        )
        current_mode = Theme.manager.mode

        dark_button = (PrimaryButton if current_mode == DARK else SecondaryButton)(text="Dark")
        dark_button.bind(on_release=lambda *_: Theme.manager.set_mode(DARK))

        light_button = (PrimaryButton if current_mode == LIGHT else SecondaryButton)(text="Light")
        light_button.bind(on_release=lambda *_: Theme.manager.set_mode(LIGHT))

        button_row.add_widget(dark_button)
        button_row.add_widget(light_button)
        card.add_widget(button_row)

        return card
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
def business_service(business_repo):
    BusinessService.configure_repository(business_repo)
    yield BusinessService
    BusinessService.configure_repository(None)


@pytest.fixture
def auth_service(user_repo):
    AuthService.configure_repository(user_repo)
    yield AuthService
    AuthService.configure_repository(None)
PYEOF_FILE

cat > tests/test_business_repository.py << 'PYEOF_FILE'
from services.business_repository import BusinessRepository, DRAFT, REGISTERED_DECLARED
from services.database import get_connection


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


def test_create_business_persists_fields(business_repo):
    business = business_repo.create(owner_user_id="user-1", **_sample_fields())
    assert business.id
    assert business.name == "Khumalo Retail"
    assert business.registration_status == DRAFT


def test_create_rejects_invalid_registration_status(business_repo):
    try:
        business_repo.create(owner_user_id="user-1", **_sample_fields(registration_status="bogus"))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_by_id_retrieves_created_business(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    fetched = business_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == created.name


def test_get_by_id_returns_none_for_missing_business(business_repo):
    assert business_repo.get_by_id("does-not-exist") is None


def test_update_changes_fields_without_duplicating_row(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    updated = business_repo.update(created.id, name="Khumalo Retail (Pty) Ltd", registration_status=REGISTERED_DECLARED)
    assert updated.name == "Khumalo Retail (Pty) Ltd"
    assert updated.registration_status == REGISTERED_DECLARED
    assert updated.id == created.id  # same row, not a new one

    all_for_owner = business_repo.get_by_owner("user-1")
    assert len(all_for_owner) == 1


def test_update_missing_business_returns_none(business_repo):
    assert business_repo.update("does-not-exist", name="X") is None


def test_update_rejects_invalid_registration_status(business_repo):
    created = business_repo.create(owner_user_id="user-1", **_sample_fields())
    try:
        business_repo.update(created.id, registration_status="bogus")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_by_owner_supports_multiple_businesses(business_repo):
    business_repo.create(owner_user_id="user-1", **_sample_fields(name="Business A"))
    business_repo.create(owner_user_id="user-1", **_sample_fields(name="Business B"))
    business_repo.create(owner_user_id="user-2", **_sample_fields(name="Someone Else's Business"))

    user_1_businesses = business_repo.get_by_owner("user-1")
    assert len(user_1_businesses) == 2
    names = {b.name for b in user_1_businesses}
    assert names == {"Business A", "Business B"}


def test_empty_database_returns_empty_list(business_repo):
    assert business_repo.get_by_owner("nobody") == []


def test_active_business_selection_persists(business_repo):
    business = business_repo.create(owner_user_id="user-1", **_sample_fields())
    assert business_repo.get_active_business_id("user-1") is None

    business_repo.set_active_business_id("user-1", business.id)
    assert business_repo.get_active_business_id("user-1") == business.id

    # Switching again updates rather than erroring/duplicating.
    business_2 = business_repo.create(owner_user_id="user-1", **_sample_fields(name="Second Business"))
    business_repo.set_active_business_id("user-1", business_2.id)
    assert business_repo.get_active_business_id("user-1") == business_2.id


def test_data_survives_closing_and_reopening_database(tmp_path):
    db_path = tmp_path / "persist_test.db"

    connection_1 = get_connection(db_path=db_path)
    repo_1 = BusinessRepository(connection_1)
    created = repo_1.create(owner_user_id="user-1", **_sample_fields())
    connection_1.close()

    connection_2 = get_connection(db_path=db_path)
    repo_2 = BusinessRepository(connection_2)
    fetched = repo_2.get_by_id(created.id)
    connection_2.close()

    assert fetched is not None
    assert fetched.name == created.name
    assert fetched.id == created.id
PYEOF_FILE

cat > tests/test_business_service.py << 'PYEOF_FILE'
from services.business_repository import DRAFT, REGISTERED_DECLARED


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


def test_create_business_valid(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    assert business.name == "Khumalo Retail"


def test_create_business_rejects_empty_name(business_service):
    try:
        business_service.create_business(owner_user_id="user-1", **_sample_fields(name="   "))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_update_business(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    updated = business_service.update_business(business.id, registration_status=REGISTERED_DECLARED)
    assert updated.registration_status == REGISTERED_DECLARED


def test_update_missing_business_raises(business_service):
    try:
        business_service.update_business("does-not-exist", name="X")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_get_business_for_user_returns_none_when_no_business(business_service):
    assert business_service.get_business_for_user("nobody") is None


def test_get_business_for_user_returns_active_business(business_service):
    b1 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    b2 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))

    business_service.set_active_business("user-1", b1.id)
    assert business_service.get_business_for_user("user-1").id == b1.id

    business_service.set_active_business("user-1", b2.id)
    assert business_service.get_business_for_user("user-1").id == b2.id


def test_get_businesses_for_user_lists_all(business_service):
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))
    businesses = business_service.get_businesses_for_user("user-1")
    assert len(businesses) == 2


def test_set_active_business_rejects_other_users_business(business_service):
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    try:
        business_service.set_active_business("user-2", business.id)
        assert False, "expected ValueError"
    except ValueError:
        pass
PYEOF_FILE

cat > tests/test_auth_service.py << 'PYEOF_FILE'
def test_register_creates_user(auth_service):
    user = auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    assert user.full_name == "Jane Doe"
    assert user.email == "jane@business.co.za"


def test_register_rejects_duplicate_email(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    try:
        auth_service.register("Someone Else", "jane@business.co.za", "anotherpassword")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_login_succeeds_with_correct_password(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    user = auth_service.login("jane@business.co.za", "supersecret1")
    assert user.email == "jane@business.co.za"


def test_login_fails_with_wrong_password(auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    try:
        auth_service.login("jane@business.co.za", "wrongpassword")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_login_fails_for_unknown_email(auth_service):
    try:
        auth_service.login("ghost@business.co.za", "whatever")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_password_is_never_stored_in_plaintext(user_repo, auth_service):
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")
    record = user_repo.get_by_email("jane@business.co.za")
    assert record is not None
    assert record.password_hash != b"supersecret1"
    assert b"supersecret1" not in record.password_hash


def test_user_survives_service_restart_simulation(user_repo, auth_service):
    """Simulates an app restart: register, then force the in-memory
    cache to reload from the (same) database, confirming login still
    works without re-registering."""
    auth_service.register("Jane Doe", "jane@business.co.za", "supersecret1")

    # Simulate restart: clear the in-memory cache but keep the same DB.
    auth_service._users_by_email_cache = {}
    auth_service._cache_loaded = False

    user = auth_service.login("jane@business.co.za", "supersecret1")
    assert user.email == "jane@business.co.za"
PYEOF_FILE

cat > tests/test_session.py << 'PYEOF_FILE'
import pytest

from app.session import AppSession
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


@pytest.fixture
def session(business_service):
    s = AppSession()
    yield s
    s.clear()


def test_set_and_get_user(session):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    assert session.current_user.id == "user-1"


def test_require_business_raises_when_missing(session):
    with pytest.raises(ValueError):
        session.require_business()


def test_require_business_returns_active_business(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    session.set_business(business)
    assert session.require_business().id == business.id


def test_switch_business_updates_current_business(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    b1 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    b2 = business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))

    session.set_business(b1)
    assert session.current_business.id == b1.id

    session.switch_business(b2.id)
    assert session.current_business.id == b2.id


def test_switch_business_without_user_raises(session):
    with pytest.raises(ValueError):
        session.switch_business("some-id")


def test_get_user_businesses_empty_without_user(session):
    assert session.get_user_businesses() == []


def test_get_user_businesses_lists_all(session, business_service):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="First"))
    business_service.create_business(owner_user_id="user-1", **_sample_fields(name="Second"))
    assert len(session.get_user_businesses()) == 2


def test_clear_resets_user_and_business(session):
    class FakeUser:
        id = "user-1"

    session.set_user(FakeUser())
    session.clear()
    assert session.current_user is None
    assert session.current_business is None
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


def test_saved_business_is_available_to_dashboard_service(business_service):
    """Mirrors what BusinessSetupScreen -> DashboardScreen actually do:
    create through the service layer, then read it back the same way
    DashboardService.get_dashboard_data(business=...) would."""
    from services.dashboard_service import DashboardService

    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    data = DashboardService.get_dashboard_data(business=business)
    assert "Khumalo Retail" in data["business_summary"]


def test_dashboard_handles_missing_business_without_crashing():
    from services.dashboard_service import DashboardService

    data = DashboardService.get_dashboard_data(business=None)
    assert "business_summary" in data
    assert isinstance(data["business_summary"], str)
PYEOF_FILE

echo "All Phase 9 files created."