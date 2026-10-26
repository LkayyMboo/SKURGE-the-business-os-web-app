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
