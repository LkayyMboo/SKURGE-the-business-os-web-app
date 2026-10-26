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
