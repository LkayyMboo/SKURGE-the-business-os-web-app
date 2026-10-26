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
