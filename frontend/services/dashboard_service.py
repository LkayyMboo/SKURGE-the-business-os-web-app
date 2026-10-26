"""
dashboard_service.py

Supplies data to the Dashboard screen.

Phase 10: revenue, expenses, and net cash movement are now REAL
figures calculated from persisted transactions via FinanceService —
no longer mock "R 0.00".

Phase 11: employee count is now REAL too — the count of employees
with employment_status='active' for this business, via
EmployeeService. Orders remains the one mock figure left, and the
alert text below has been updated accordingly so nothing invented is
silently presented as real.
"""

from typing import List, TypedDict

from services.business_repository import REGISTRATION_STATUS_CHOICES, VERIFIED
from services.employee_service import EmployeeService
from services.finance_service import FinanceService
from utils.formatters import format_cents_as_rand


class Transaction(TypedDict):
    description: str
    amount: str
    date: str


class Alert(TypedDict):
    message: str
    level: str


class DashboardData(TypedDict):
    revenue: str
    expenses: str
    net_cash_movement: str
    orders: str
    employees: str
    business_summary: str
    recent_transactions: List[Transaction]
    alerts: List[Alert]


def _status_label(status: str) -> str:
    if status == VERIFIED:
        return "Verified"
    return REGISTRATION_STATUS_CHOICES.get(status, status)


class DashboardService:
    """Provides dashboard data. Revenue, expenses, and employee count are real; orders is still mock."""

    @staticmethod
    def get_dashboard_data(business=None) -> DashboardData:
        if business:
            business_summary = (
                f"{business.name} — {business.business_type}, {business.industry} "
                f"({business.province}). Registration: {_status_label(business.registration_status)}."
            )
            totals = FinanceService.get_totals(business.id)
            revenue = format_cents_as_rand(totals["income_cents"])
            expenses = format_cents_as_rand(totals["expense_cents"])
            net_cash_movement = format_cents_as_rand(totals["net_cents"])

            recent = FinanceService.list_transactions(business.id)[:5]
            recent_transactions = [
                {
                    "description": t.description,
                    "amount": format_cents_as_rand(
                        t.amount_cents if t.transaction_type == "income" else -t.amount_cents
                    ),
                    "date": t.transaction_date,
                }
                for t in recent
            ]
            if not recent_transactions:
                recent_transactions = [
                    {"description": "No transactions recorded yet.", "amount": "", "date": ""}
                ]

            employee_counts = EmployeeService.get_counts(business.id)
            employees = str(employee_counts["active"])

            alerts = [
                {
                    "message": "Orders shown below is demo data — that module is not yet "
                               "implemented. Revenue, expenses, and active employee count "
                               "reflect your actual recorded data.",
                    "level": "info",
                },
            ]
        else:
            business_summary = "No business profile found — demo data shown."
            revenue = "R 0.00"
            expenses = "R 0.00"
            net_cash_movement = "R 0.00"
            employees = "0"
            recent_transactions = [
                {"description": "Demo transaction", "amount": "R 0.00", "date": "—"},
            ]
            alerts = [
                {
                    "message": "This is demo data. Connect a backend to see real information.",
                    "level": "info",
                },
            ]

        return {
            "revenue": revenue,
            "expenses": expenses,
            "net_cash_movement": net_cash_movement,
            "orders": "0",
            "employees": employees,
            "business_summary": business_summary,
            "recent_transactions": recent_transactions,
            "alerts": alerts,
        }
