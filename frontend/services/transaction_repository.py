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
