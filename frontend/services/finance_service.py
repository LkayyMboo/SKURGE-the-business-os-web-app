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
