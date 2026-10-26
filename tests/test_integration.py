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
