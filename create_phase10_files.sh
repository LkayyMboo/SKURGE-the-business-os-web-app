#!/usr/bin/env bash
set -e
cd ~/business-os

mkdir -p frontend/app frontend/layouts frontend/screens/finance frontend/services frontend/utils tests

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

cat > frontend/services/transaction_repository.py << 'PYEOF_FILE'
"""
transaction_repository.py

Parameterized SQLite storage for income/expense transactions. The UI
and FinanceService never write SQL directly — everything goes
through this repository, same pattern as BusinessRepository.

Every operation is scoped to a business_id — there is no "list all
transactions" method that could accidentally leak one business's
records into another's view.

Money is always amount_cents (an integer). Never pass or store a
float Rand amount — see utils/formatters.py and utils/validators.py
for the conversion points at the UI boundary.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

INCOME = "income"
EXPENSE = "expense"
TRANSACTION_TYPES = [INCOME, EXPENSE]


@dataclass
class Transaction:
    id: str
    business_id: str
    transaction_type: str
    description: str
    amount_cents: int
    category: str
    transaction_date: str  # ISO format: YYYY-MM-DD
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_COLUMNS = [
    "id", "business_id", "transaction_type", "description", "amount_cents",
    "category", "transaction_date", "notes", "created_at",
]


def _row_to_transaction(row) -> Transaction:
    return Transaction(**dict(zip(_COLUMNS, row)))


class TransactionRepository:
    """Persistent CRUD + aggregate storage for transactions."""

    def __init__(self, connection):
        self._conn = connection

    def create(self, business_id: str, transaction_type: str, description: str,
               amount_cents: int, category: str, transaction_date: str, notes: str = "") -> Transaction:
        if transaction_type not in TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction_type: {transaction_type!r}")
        if not description or not description.strip():
            raise ValueError("Description is required.")
        if not category or not category.strip():
            raise ValueError("Category is required.")
        if amount_cents <= 0:
            raise ValueError("Amount must be greater than zero.")
        if not transaction_date:
            raise ValueError("Transaction date is required.")

        transaction = Transaction(
            id=str(uuid.uuid4()),
            business_id=business_id,
            transaction_type=transaction_type,
            description=description.strip(),
            amount_cents=amount_cents,
            category=category.strip(),
            transaction_date=transaction_date,
            notes=(notes or "").strip(),
        )

        self._conn.execute(
            f"INSERT INTO transactions ({', '.join(_COLUMNS)}) "
            f"VALUES ({', '.join('?' for _ in _COLUMNS)})",
            tuple(getattr(transaction, column) for column in _COLUMNS),
        )
        self._conn.commit()
        return transaction

    def get_by_id(self, transaction_id: str) -> Optional[Transaction]:
        row = self._conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM transactions WHERE id = ?", (transaction_id,)
        ).fetchone()
        return _row_to_transaction(row) if row else None

    def list_for_business(self, business_id: str, transaction_type: str = None,
                           start_date: str = None, end_date: str = None):
        """
        Transaction history for one business, newest first (ordered by
        transaction_date DESC, then created_at DESC as a consistent
        tie-breaker for same-day entries).
        """
        query = f"SELECT {', '.join(_COLUMNS)} FROM transactions WHERE business_id = ?"
        params = [business_id]

        if transaction_type is not None:
            query += " AND transaction_type = ?"
            params.append(transaction_type)
        if start_date is not None:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date is not None:
            query += " AND transaction_date <= ?"
            params.append(end_date)

        query += " ORDER BY transaction_date DESC, created_at DESC"

        rows = self._conn.execute(query, tuple(params)).fetchall()
        return [_row_to_transaction(row) for row in rows]

    def get_totals(self, business_id: str, start_date: str = None, end_date: str = None) -> dict:
        """
        Returns {"income_cents": int, "expense_cents": int} for one
        business. Totals reflect ALL recorded transactions for that
        business unless start_date/end_date narrow the range.
        """
        query = (
            "SELECT transaction_type, COALESCE(SUM(amount_cents), 0) "
            "FROM transactions WHERE business_id = ?"
        )
        params = [business_id]

        if start_date is not None:
            query += " AND transaction_date >= ?"
            params.append(start_date)
        if end_date is not None:
            query += " AND transaction_date <= ?"
            params.append(end_date)

        query += " GROUP BY transaction_type"

        rows = self._conn.execute(query, tuple(params)).fetchall()
        totals = {INCOME: 0, EXPENSE: 0}
        for transaction_type, total in rows:
            totals[transaction_type] = total

        return {"income_cents": totals[INCOME], "expense_cents": totals[EXPENSE]}
PYEOF_FILE

cat > frontend/services/finance_service.py << 'PYEOF_FILE'
"""
finance_service.py

Bookkeeping operations: record income/expenses, list transaction
history, and calculate totals. This is a FOCUSED FIRST VERSION:

- Totals are a simple sum of recorded entries — NOT a verified bank
  balance, NOT a tax calculation, NOT a complete accounting package.
- Nothing here invents, estimates, or predicts financial data. Every
  figure comes directly from a transaction the user actually entered.

Same pattern as BusinessService: a thin class delegating all storage
to a repository, with configure_repository() for test injection.
"""

from services.database import get_connection
from services.transaction_repository import EXPENSE, INCOME, TransactionRepository


class FinanceService:
    """Bookkeeping operations for a business. Delegates storage to TransactionRepository."""

    _repository = None

    @classmethod
    def _repo(cls) -> TransactionRepository:
        if cls._repository is None:
            cls._repository = TransactionRepository(get_connection())
        return cls._repository

    @classmethod
    def configure_repository(cls, repository: TransactionRepository) -> None:
        """Used by tests to inject a repository backed by a temporary database."""
        cls._repository = repository

    @classmethod
    def record_income(cls, business_id: str, description: str, amount_cents: int,
                       category: str, transaction_date: str, notes: str = ""):
        return cls._repo().create(
            business_id=business_id, transaction_type=INCOME, description=description,
            amount_cents=amount_cents, category=category, transaction_date=transaction_date, notes=notes,
        )

    @classmethod
    def record_expense(cls, business_id: str, description: str, amount_cents: int,
                        category: str, transaction_date: str, notes: str = ""):
        return cls._repo().create(
            business_id=business_id, transaction_type=EXPENSE, description=description,
            amount_cents=amount_cents, category=category, transaction_date=transaction_date, notes=notes,
        )

    @classmethod
    def list_transactions(cls, business_id: str, transaction_type: str = None):
        return cls._repo().list_for_business(business_id, transaction_type=transaction_type)

    @classmethod
    def get_totals(cls, business_id: str) -> dict:
        """
        Returns {"income_cents", "expense_cents", "net_cents"} for a
        business, calculated from ALL persisted transactions.

        net_cents = income_cents - expense_cents. This is a simple
        cash-movement figure, not a verified bank balance.
        """
        raw = cls._repo().get_totals(business_id)
        income_cents = raw["income_cents"]
        expense_cents = raw["expense_cents"]
        return {
            "income_cents": income_cents,
            "expense_cents": expense_cents,
            "net_cents": income_cents - expense_cents,
        }
PYEOF_FILE

cat > frontend/services/dashboard_service.py << 'PYEOF_FILE'
"""
dashboard_service.py

Supplies data to the Dashboard screen.

Phase 10: revenue, expenses, and net cash movement are now REAL
figures calculated from persisted transactions via FinanceService —
no longer mock "R 0.00". Orders and employees remain mock (no
orders/employee module exists yet) and are explicitly labeled as
demo data in the alerts list, so the interface never silently
presents invented figures as real.
"""

from typing import List, TypedDict

from services.business_repository import REGISTRATION_STATUS_CHOICES, VERIFIED
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
    """Provides dashboard data. Revenue/expenses are real; orders/employees are still mock."""

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

            alerts = [
                {
                    "message": "Orders and employee counts shown below are demo data — "
                               "those modules are not yet implemented. Revenue and expenses "
                               "reflect your actual recorded transactions.",
                    "level": "info",
                },
            ]
        else:
            business_summary = "No business profile found — demo data shown."
            revenue = "R 0.00"
            expenses = "R 0.00"
            net_cash_movement = "R 0.00"
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
            "employees": "0",
            "business_summary": business_summary,
            "recent_transactions": recent_transactions,
            "alerts": alerts,
        }
PYEOF_FILE

cat > frontend/utils/formatters.py << 'PYEOF_FILE'
"""
formatters.py

Shared display-formatting helpers. Currently just currency.

All money in SKURGE is stored and calculated as INTEGER CENTS
(amount_cents), never as float Rand values — floats cannot represent
amounts like 0.10 exactly, which causes cumulative rounding errors in
totals. This module is the one place that converts cents to a
human-readable Rand string for display.
"""


def format_cents_as_rand(amount_cents: int) -> str:
    """
    Format integer cents as a Rand string, e.g. 350000 -> 'R 3,500.00'.
    Negative amounts (e.g. a negative net cash movement) are shown
    with a leading minus sign: -150000 -> '-R 1,500.00'.
    """
    sign = "-" if amount_cents < 0 else ""
    whole_rand = abs(amount_cents) // 100
    remainder_cents = abs(amount_cents) % 100
    return f"{sign}R {whole_rand:,.0f}.{remainder_cents:02d}"
PYEOF_FILE

cat > frontend/utils/validators.py << 'PYEOF_FILE'
"""
validators.py

Shared input-validation helpers used across screens/services.
"""

from decimal import Decimal, InvalidOperation


def parse_rand_input_to_cents(text: str) -> int:
    """
    Parse a user-typed Rand amount (e.g. "350", "350.00", "R 350.50",
    "3,500.00") into integer cents (e.g. 35000, 35000, 35050, 350000).

    Uses Decimal rather than float, specifically to avoid the classic
    floating-point problem where amounts like 0.10 cannot be
    represented exactly in binary and silently accumulate rounding
    errors across many transactions.

    Raises ValueError with a clear message if the input is not a
    valid positive monetary amount.
    """
    if text is None:
        raise ValueError("Amount is required.")

    cleaned = text.strip().replace("R", "").replace(",", "").strip()
    if not cleaned:
        raise ValueError("Amount is required.")

    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError("Enter a valid amount, e.g. 350.00.")

    if value <= 0:
        raise ValueError("Amount must be greater than zero.")

    cents = int((value * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    return cents


def validate_iso_date(text: str):
    """
    Validate a date string is a real calendar date in YYYY-MM-DD
    format. Returns the parsed datetime.date on success, or raises
    ValueError with a clear message.
    """
    from datetime import date

    if not text or not text.strip():
        raise ValueError("Date is required.")
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValueError("Enter a valid date in YYYY-MM-DD format, e.g. 2026-10-11.")
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

Phase 10 design note — cross-screen refresh:
FinanceScreen and DashboardScreen are SIBLING screens inside the same
inner ScreenManager; they are not torn down when you navigate between
them. When FinanceScreen records a transaction, it can safely rebuild
its OWN content in place (it caused the change, it knows). But
DashboardScreen has no way to know Finance's data changed — it's a
passive bystander. Rather than invent a new publish/subscribe system,
`data_version` reuses the SAME pattern already proven for theme and
business-switch changes: bump a Kivy property, app.py is already
listening and rebuilds the shell (keeping whatever section is open).
This is a small, deliberate reuse of an existing pattern, not a new
architectural system.
"""

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, ObjectProperty

from services.business_service import BusinessService


class AppSession(EventDispatcher):
    """Holds the current user and current business for this app run."""

    current_user = ObjectProperty(None, allownone=True)
    current_business = ObjectProperty(None, allownone=True)
    data_version = NumericProperty(0)

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

    def notify_data_changed(self) -> None:
        """
        Call this after any operation that changes data another screen
        might be displaying (e.g. recording a transaction). Bumps
        data_version, which app.py listens for to refresh the shell —
        see the module docstring above for why this mechanism was chosen.
        """
        self.data_version += 1

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

Phase 10: app_session.data_version is bound the same way — recording
a transaction on the Finance screen bumps it, which refreshes
DashboardScreen's totals without a restart. See session.py's
docstring for why this reuses the rebuild pattern instead of a new
cross-screen messaging system.
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
        app_session.bind(data_version=self._on_data_changed)
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
        active business — same mechanism as the theme-change rebuild.

        No "are we on the main screen yet" guard here: Kivy properties
        fire this callback THE INSTANT set_business() runs, which in
        _handle_authenticated happens BEFORE root_manager.current is
        switched to "main". A guard checking root_manager.current would
        (and did) skip the one rebuild that actually matters — the
        first one, right after login — leaving Dashboard/Settings
        permanently showing stale data from before the user signed in.
        Rebuilding while a non-main screen is visible is harmless: it's
        not on screen, so there's nothing to flicker."""
        current_section = self._current_main_section()
        self._build_main_layout(initial_section=current_section)

    def _on_data_changed(self, _instance, _version) -> None:
        """Called when any screen reports its data changed (e.g.
        Finance recording a transaction) — refreshes sibling screens
        like Dashboard that have no other way to know."""
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

cat > frontend/screens/finance/finance_screen.py << 'PYEOF_FILE'
"""
finance_screen.py

The first real bookkeeping screen: record income/expense transactions,
see running totals, and view transaction history. This is a FOCUSED
FIRST VERSION — not a complete accounting package. Totals are a
straightforward sum of what the user has entered; nothing here is a
verified bank balance or a tax calculation.

Refresh behavior:
- After recording a transaction, this screen rebuilds its OWN content
  in place (it caused the change, so it can refresh itself directly).
- It also calls app_session.notify_data_changed() so DashboardScreen
  (a sibling screen with no other way to know) gets refreshed too —
  see app/session.py's docstring for why that mechanism exists.
"""

from datetime import date

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton
from components.cards.card import Card, StatCard
from components.inputs.inputs import TextInputField
from components.tables.table import DataTable
from screens.base_screen import BaseScreen
from services.finance_service import FinanceService
from services.transaction_repository import EXPENSE, INCOME
from styles.theme import Theme
from utils.formatters import format_cents_as_rand
from utils.validators import parse_rand_input_to_cents, validate_iso_date

CATEGORY_OPTIONS = [
    "Sales", "Services", "Rent", "Utilities", "Supplies",
    "Wages", "Transport", "Other",
]
TRANSACTION_TYPE_LABELS = {INCOME: "Income", EXPENSE: "Expense"}
TRANSACTION_TYPE_BY_LABEL = {label: code for code, label in TRANSACTION_TYPE_LABELS.items()}


class FinanceScreen(BaseScreen):
    """Record income/expenses and view totals + history for the active business."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Finance", subtitle="Record income and expenses, and track your cash flow", **kwargs
        )
        self._render()

    def _render(self) -> None:
        """(Re)builds this screen's entire content from current data.
        Safe to call repeatedly — always reflects the latest state."""
        self.content.clear_widgets()
        business = app_session.current_business

        if business is None:
            self.content.add_widget(
                Label(
                    text="No active business. Complete business setup to record transactions.",
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
        body.add_widget(self._build_record_form(business.id))
        body.add_widget(self._build_history_card(business.id))

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_summary_row(self, business_id: str):
        totals = FinanceService.get_totals(business_id)
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=100,
            spacing=Theme.dimensions.SPACE_MD,
        )
        row.add_widget(StatCard(
            label="Total Income", value=format_cents_as_rand(totals["income_cents"]),
            accent_color=Theme.colors.SAGE, size_hint=(1, 1),
        ))
        row.add_widget(StatCard(
            label="Total Expenses", value=format_cents_as_rand(totals["expense_cents"]),
            size_hint=(1, 1),
        ))
        row.add_widget(StatCard(
            label="Net Cash Movement", value=format_cents_as_rand(totals["net_cents"]),
            accent_color=Theme.colors.GOLD, size_hint=(1, 1),
        ))
        return row

    def _build_record_form(self, business_id: str):
        card = Card(title="Record Transaction", size_hint=(1, None), height=400)

        type_spinner = Spinner(
            text=TRANSACTION_TYPE_LABELS[INCOME], values=list(TRANSACTION_TYPE_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        description_field = TextInputField(label="Description", placeholder="e.g. Product sale to customer")
        amount_field = TextInputField(label="Amount (R)", placeholder="e.g. 350.00")
        category_spinner = Spinner(
            text=CATEGORY_OPTIONS[0], values=CATEGORY_OPTIONS,
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        date_field = TextInputField(label="Date (YYYY-MM-DD)", placeholder="e.g. 2026-10-11")
        date_field.text = date.today().isoformat()

        error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        def on_submit(*_args):
            error_label.text = ""
            description = description_field.text.strip()
            category = category_spinner.text

            if not description:
                error_label.text = "Description is required."
                return

            try:
                amount_cents = parse_rand_input_to_cents(amount_field.text)
            except ValueError as error:
                error_label.text = str(error)
                return

            try:
                transaction_date = validate_iso_date(date_field.text).isoformat()
            except ValueError as error:
                error_label.text = str(error)
                return

            transaction_type = TRANSACTION_TYPE_BY_LABEL[type_spinner.text]

            try:
                if transaction_type == INCOME:
                    FinanceService.record_income(
                        business_id=business_id, description=description, amount_cents=amount_cents,
                        category=category, transaction_date=transaction_date,
                    )
                else:
                    FinanceService.record_expense(
                        business_id=business_id, description=description, amount_cents=amount_cents,
                        category=category, transaction_date=transaction_date,
                    )
            except ValueError as error:
                error_label.text = f"Could not save: {error}"
                return

            # Success: refresh this screen's own data, and tell the
            # Dashboard (which can't see this change on its own) to
            # refresh too.
            self._render()
            app_session.notify_data_changed()

        submit_button = PrimaryButton(text="Record Transaction")
        submit_button.width = 440
        submit_button.bind(on_release=on_submit)

        for widget in [
            type_spinner, description_field, amount_field, category_spinner,
            date_field, error_label, submit_button,
        ]:
            card.add_widget(widget)

        return card

    def _build_history_card(self, business_id: str):
        transactions = FinanceService.list_transactions(business_id)

        if not transactions:
            card = Card(title="Transaction History", size_hint=(1, None), height=90)
            card.add_widget(
                Label(
                    text="No transactions recorded yet.", color=Theme.colors.TEXT_SECONDARY,
                    font_size=Theme.typography.BODY,
                )
            )
            return card

        rows = [
            (
                t.transaction_date,
                TRANSACTION_TYPE_LABELS[t.transaction_type],
                t.description,
                t.category,
                format_cents_as_rand(t.amount_cents if t.transaction_type == INCOME else -t.amount_cents),
            )
            for t in transactions
        ]
        card = Card(title="Transaction History", size_hint=(1, None), height=90 + min(len(rows), 10) * 40)
        card.add_widget(
            DataTable(
                columns=["Date", "Type", "Description", "Category", "Amount"],
                rows=rows,
                size_hint=(1, None),
                height=40 + min(len(rows), 10) * 40,
            )
        )
        return card
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

        # 1. Build the content area. "dashboard", "settings", and
        #    "finance" get real screens; every other section still
        #    gets a placeholder.
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


@pytest.fixture
def transaction_repo(temp_db):
    return TransactionRepository(temp_db)


@pytest.fixture
def finance_service(transaction_repo):
    FinanceService.configure_repository(transaction_repo)
    yield FinanceService
    FinanceService.configure_repository(None)
PYEOF_FILE

cat > tests/test_transaction_repository.py << 'PYEOF_FILE'
import pytest

from services.database import get_connection
from services.transaction_repository import EXPENSE, INCOME, TransactionRepository


def test_create_income_transaction(transaction_repo):
    t = transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="Product sale",
        amount_cents=350000, category="Sales", transaction_date="2026-10-01",
    )
    assert t.id
    assert t.transaction_type == INCOME
    assert t.amount_cents == 350000


def test_create_expense_transaction(transaction_repo):
    t = transaction_repo.create(
        business_id="biz-1", transaction_type=EXPENSE, description="Stock purchase",
        amount_cents=120000, category="Supplies", transaction_date="2026-10-02",
    )
    assert t.transaction_type == EXPENSE


def test_reject_zero_amount(transaction_repo):
    with pytest.raises(ValueError):
        transaction_repo.create(
            business_id="biz-1", transaction_type=INCOME, description="X",
            amount_cents=0, category="Sales", transaction_date="2026-10-01",
        )


def test_reject_negative_amount(transaction_repo):
    with pytest.raises(ValueError):
        transaction_repo.create(
            business_id="biz-1", transaction_type=INCOME, description="X",
            amount_cents=-500, category="Sales", transaction_date="2026-10-01",
        )


def test_reject_missing_description(transaction_repo):
    with pytest.raises(ValueError):
        transaction_repo.create(
            business_id="biz-1", transaction_type=INCOME, description="   ",
            amount_cents=5000, category="Sales", transaction_date="2026-10-01",
        )


def test_reject_invalid_transaction_type(transaction_repo):
    with pytest.raises(ValueError):
        transaction_repo.create(
            business_id="biz-1", transaction_type="refund", description="X",
            amount_cents=5000, category="Sales", transaction_date="2026-10-01",
        )


def test_reject_missing_date(transaction_repo):
    with pytest.raises(ValueError):
        transaction_repo.create(
            business_id="biz-1", transaction_type=INCOME, description="X",
            amount_cents=5000, category="Sales", transaction_date="",
        )


def test_retrieve_saved_transaction(transaction_repo):
    created = transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="Product sale",
        amount_cents=350000, category="Sales", transaction_date="2026-10-01",
    )
    fetched = transaction_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.description == "Product sale"


def test_list_for_business_orders_newest_first(transaction_repo):
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="Earlier",
        amount_cents=1000, category="Sales", transaction_date="2026-10-01",
    )
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="Later",
        amount_cents=2000, category="Sales", transaction_date="2026-10-05",
    )
    results = transaction_repo.list_for_business("biz-1")
    assert results[0].description == "Later"
    assert results[1].description == "Earlier"


def test_list_filters_by_type(transaction_repo):
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="In",
        amount_cents=1000, category="Sales", transaction_date="2026-10-01",
    )
    transaction_repo.create(
        business_id="biz-1", transaction_type=EXPENSE, description="Out",
        amount_cents=500, category="Supplies", transaction_date="2026-10-01",
    )
    income_only = transaction_repo.list_for_business("biz-1", transaction_type=INCOME)
    assert len(income_only) == 1
    assert income_only[0].description == "In"


def test_totals_sum_correctly(transaction_repo):
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="A",
        amount_cents=100000, category="Sales", transaction_date="2026-10-01",
    )
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="B",
        amount_cents=50000, category="Sales", transaction_date="2026-10-02",
    )
    transaction_repo.create(
        business_id="biz-1", transaction_type=EXPENSE, description="C",
        amount_cents=30000, category="Rent", transaction_date="2026-10-03",
    )
    totals = transaction_repo.get_totals("biz-1")
    assert totals["income_cents"] == 150000
    assert totals["expense_cents"] == 30000


def test_totals_for_business_with_no_transactions_are_zero(transaction_repo):
    totals = transaction_repo.get_totals("biz-nonexistent")
    assert totals == {"income_cents": 0, "expense_cents": 0}


def test_date_range_filtering(transaction_repo):
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="January",
        amount_cents=10000, category="Sales", transaction_date="2026-01-15",
    )
    transaction_repo.create(
        business_id="biz-1", transaction_type=INCOME, description="October",
        amount_cents=20000, category="Sales", transaction_date="2026-10-15",
    )
    october_totals = transaction_repo.get_totals("biz-1", start_date="2026-10-01", end_date="2026-10-31")
    assert october_totals["income_cents"] == 20000


def test_business_isolation(transaction_repo):
    transaction_repo.create(
        business_id="biz-A", transaction_type=INCOME, description="A's sale",
        amount_cents=100000, category="Sales", transaction_date="2026-10-01",
    )
    transaction_repo.create(
        business_id="biz-B", transaction_type=INCOME, description="B's sale",
        amount_cents=999999, category="Sales", transaction_date="2026-10-01",
    )
    a_transactions = transaction_repo.list_for_business("biz-A")
    assert len(a_transactions) == 1
    assert a_transactions[0].description == "A's sale"

    a_totals = transaction_repo.get_totals("biz-A")
    assert a_totals["income_cents"] == 100000  # NOT mixed with biz-B's 999999


def test_data_survives_closing_and_reopening_database(tmp_path):
    db_path = tmp_path / "finance_persist_test.db"

    conn_1 = get_connection(db_path=db_path)
    repo_1 = TransactionRepository(conn_1)
    created = repo_1.create(
        business_id="biz-1", transaction_type=INCOME, description="Persisted sale",
        amount_cents=75000, category="Sales", transaction_date="2026-10-01",
    )
    conn_1.close()

    conn_2 = get_connection(db_path=db_path)
    repo_2 = TransactionRepository(conn_2)
    fetched = repo_2.get_by_id(created.id)
    totals = repo_2.get_totals("biz-1")
    conn_2.close()

    assert fetched is not None
    assert fetched.description == "Persisted sale"
    assert totals["income_cents"] == 75000
PYEOF_FILE

cat > tests/test_finance_service.py << 'PYEOF_FILE'
def test_record_income(finance_service):
    t = finance_service.record_income(
        business_id="biz-1", description="Product sale", amount_cents=350000,
        category="Sales", transaction_date="2026-10-01",
    )
    assert t.transaction_type == "income"


def test_record_expense(finance_service):
    t = finance_service.record_expense(
        business_id="biz-1", description="Stock purchase", amount_cents=120000,
        category="Supplies", transaction_date="2026-10-02",
    )
    assert t.transaction_type == "expense"


def test_get_totals_calculates_net_correctly(finance_service):
    finance_service.record_income(
        business_id="biz-1", description="Sale", amount_cents=500000,
        category="Sales", transaction_date="2026-10-01",
    )
    finance_service.record_expense(
        business_id="biz-1", description="Rent", amount_cents=200000,
        category="Rent", transaction_date="2026-10-02",
    )
    totals = finance_service.get_totals("biz-1")
    assert totals["income_cents"] == 500000
    assert totals["expense_cents"] == 200000
    assert totals["net_cents"] == 300000


def test_empty_state_totals_are_zero(finance_service):
    totals = finance_service.get_totals("biz-with-no-transactions")
    assert totals == {"income_cents": 0, "expense_cents": 0, "net_cents": 0}


def test_decimal_currency_amounts_sum_without_rounding_errors(finance_service):
    """Ten income entries of R 0.10 (10 cents) should sum to exactly
    R 1.00 (100 cents) — the classic case where float arithmetic
    would silently drift (0.1 + 0.1 + ... != 1.0 in binary floats)."""
    for _ in range(10):
        finance_service.record_income(
            business_id="biz-1", description="Small sale", amount_cents=10,
            category="Sales", transaction_date="2026-10-01",
        )
    totals = finance_service.get_totals("biz-1")
    assert totals["income_cents"] == 100


def test_net_can_be_negative(finance_service):
    finance_service.record_income(
        business_id="biz-1", description="Sale", amount_cents=10000,
        category="Sales", transaction_date="2026-10-01",
    )
    finance_service.record_expense(
        business_id="biz-1", description="Big expense", amount_cents=50000,
        category="Rent", transaction_date="2026-10-02",
    )
    totals = finance_service.get_totals("biz-1")
    assert totals["net_cents"] == -40000


def test_list_transactions_business_isolation(finance_service):
    finance_service.record_income(
        business_id="biz-A", description="A sale", amount_cents=1000,
        category="Sales", transaction_date="2026-10-01",
    )
    finance_service.record_income(
        business_id="biz-B", description="B sale", amount_cents=2000,
        category="Sales", transaction_date="2026-10-01",
    )
    a_only = finance_service.list_transactions("biz-A")
    assert len(a_only) == 1
    assert a_only[0].description == "A sale"
PYEOF_FILE

cat > tests/test_currency_helpers.py << 'PYEOF_FILE'
import pytest

from utils.formatters import format_cents_as_rand
from utils.validators import parse_rand_input_to_cents, validate_iso_date


def test_format_basic_amount():
    assert format_cents_as_rand(350000) == "R 3,500.00"


def test_format_small_amount():
    assert format_cents_as_rand(50) == "R 0.50"


def test_format_zero():
    assert format_cents_as_rand(0) == "R 0.00"


def test_format_negative_amount():
    assert format_cents_as_rand(-150000) == "-R 1,500.00"


def test_parse_plain_number():
    assert parse_rand_input_to_cents("350") == 35000


def test_parse_decimal_number():
    assert parse_rand_input_to_cents("350.50") == 35050


def test_parse_with_rand_symbol_and_commas():
    assert parse_rand_input_to_cents("R 3,500.00") == 350000


def test_parse_rejects_zero():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("0")


def test_parse_rejects_negative():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("-50")


def test_parse_rejects_garbage():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("not a number")


def test_parse_rejects_empty():
    with pytest.raises(ValueError):
        parse_rand_input_to_cents("")


def test_validate_iso_date_accepts_valid_date():
    result = validate_iso_date("2026-10-11")
    assert result.year == 2026 and result.month == 10 and result.day == 11


def test_validate_iso_date_rejects_invalid_date():
    with pytest.raises(ValueError):
        validate_iso_date("2026-13-40")


def test_validate_iso_date_rejects_wrong_format():
    with pytest.raises(ValueError):
        validate_iso_date("11/10/2026")


def test_validate_iso_date_rejects_empty():
    with pytest.raises(ValueError):
        validate_iso_date("")
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


def test_saved_business_is_available_to_dashboard_service(business_service, finance_service):
    """Mirrors what BusinessSetupScreen -> DashboardScreen actually do:
    create through the service layer, then read it back the same way
    DashboardService.get_dashboard_data(business=...) would."""
    from services.dashboard_service import DashboardService

    business = business_service.create_business(owner_user_id="user-1", **_sample_fields())
    data = DashboardService.get_dashboard_data(business=business)
    assert "Khumalo Retail" in data["business_summary"]
    assert data["revenue"] == "R 0.00"  # no transactions recorded yet


def test_dashboard_handles_missing_business_without_crashing():
    from services.dashboard_service import DashboardService

    data = DashboardService.get_dashboard_data(business=None)
    assert "business_summary" in data
    assert isinstance(data["business_summary"], str)


def test_recorded_transactions_flow_through_to_dashboard_totals(business_service, finance_service):
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


def test_dashboard_totals_isolated_by_business(business_service, finance_service):
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
PYEOF_FILE

touch frontend/screens/finance/__init__.py
echo "Phase 10 (Finance/Bookkeeping) files created."