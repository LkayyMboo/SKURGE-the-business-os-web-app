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
