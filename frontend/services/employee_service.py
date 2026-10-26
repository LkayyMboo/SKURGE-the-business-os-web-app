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
