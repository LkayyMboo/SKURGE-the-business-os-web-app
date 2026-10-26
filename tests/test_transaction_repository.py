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
