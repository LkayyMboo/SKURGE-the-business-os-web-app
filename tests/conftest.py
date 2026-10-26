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
