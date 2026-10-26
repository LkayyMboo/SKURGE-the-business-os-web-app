"""
finance_screen.py

The first real bookkeeping screen: record income/expense transactions,
see running totals, and view transaction history. This is a FOCUSED
FIRST VERSION — not a complete accounting package. Totals are a
straightforward sum of what the user has entered; nothing here is a
verified bank balance or a tax calculation.

Refresh behavior:
- After recording a transaction, this screen rebuilds its OWN content
  in place (it caused the change, so it can refresh itself directly).
- It also calls app_session.notify_data_changed() so DashboardScreen
  (a sibling screen with no other way to know) gets refreshed too —
  see app/session.py's docstring for why that mechanism exists.
"""

from datetime import date

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton
from components.cards.card import Card, StatCard
from components.inputs.inputs import TextInputField
from components.tables.table import DataTable
from screens.base_screen import BaseScreen
from services.finance_service import FinanceService
from services.transaction_repository import EXPENSE, INCOME
from styles.theme import Theme
from utils.formatters import format_cents_as_rand
from utils.validators import parse_rand_input_to_cents, validate_iso_date

CATEGORY_OPTIONS = [
    "Sales", "Services", "Rent", "Utilities", "Supplies",
    "Wages", "Transport", "Other",
]
TRANSACTION_TYPE_LABELS = {INCOME: "Income", EXPENSE: "Expense"}
TRANSACTION_TYPE_BY_LABEL = {label: code for code, label in TRANSACTION_TYPE_LABELS.items()}


class FinanceScreen(BaseScreen):
    """Record income/expenses and view totals + history for the active business."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Finance", subtitle="Record income and expenses, and track your cash flow", **kwargs
        )
        self._render()

    def _render(self) -> None:
        """(Re)builds this screen's entire content from current data.
        Safe to call repeatedly — always reflects the latest state."""
        self.content.clear_widgets()
        business = app_session.current_business

        if business is None:
            self.content.add_widget(
                Label(
                    text="No active business. Complete business setup to record transactions.",
                    color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
                )
            )
            return

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical", spacing=Theme.dimensions.SECTION_SPACING, size_hint=(1, None)
        )
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(self._build_summary_row(business.id))
        body.add_widget(self._build_record_form(business.id))
        body.add_widget(self._build_history_card(business.id))

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_summary_row(self, business_id: str):
        totals = FinanceService.get_totals(business_id)
        row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=100,
            spacing=Theme.dimensions.SPACE_MD,
        )
        row.add_widget(StatCard(
            label="Total Income", value=format_cents_as_rand(totals["income_cents"]),
            accent_color=Theme.colors.SAGE, size_hint=(1, 1),
        ))
        row.add_widget(StatCard(
            label="Total Expenses", value=format_cents_as_rand(totals["expense_cents"]),
            size_hint=(1, 1),
        ))
        row.add_widget(StatCard(
            label="Net Cash Movement", value=format_cents_as_rand(totals["net_cents"]),
            accent_color=Theme.colors.GOLD, size_hint=(1, 1),
        ))
        return row

    def _build_record_form(self, business_id: str):
        card = Card(title="Record Transaction", size_hint=(1, None), height=400)

        type_spinner = Spinner(
            text=TRANSACTION_TYPE_LABELS[INCOME], values=list(TRANSACTION_TYPE_LABELS.values()),
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        description_field = TextInputField(label="Description", placeholder="e.g. Product sale to customer")
        amount_field = TextInputField(label="Amount (R)", placeholder="e.g. 350.00")
        category_spinner = Spinner(
            text=CATEGORY_OPTIONS[0], values=CATEGORY_OPTIONS,
            size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
            background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
        )
        date_field = TextInputField(label="Date (YYYY-MM-DD)", placeholder="e.g. 2026-10-11")
        date_field.text = date.today().isoformat()

        error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        def on_submit(*_args):
            error_label.text = ""
            description = description_field.text.strip()
            category = category_spinner.text

            if not description:
                error_label.text = "Description is required."
                return

            try:
                amount_cents = parse_rand_input_to_cents(amount_field.text)
            except ValueError as error:
                error_label.text = str(error)
                return

            try:
                transaction_date = validate_iso_date(date_field.text).isoformat()
            except ValueError as error:
                error_label.text = str(error)
                return

            transaction_type = TRANSACTION_TYPE_BY_LABEL[type_spinner.text]

            try:
                if transaction_type == INCOME:
                    FinanceService.record_income(
                        business_id=business_id, description=description, amount_cents=amount_cents,
                        category=category, transaction_date=transaction_date,
                    )
                else:
                    FinanceService.record_expense(
                        business_id=business_id, description=description, amount_cents=amount_cents,
                        category=category, transaction_date=transaction_date,
                    )
            except ValueError as error:
                error_label.text = f"Could not save: {error}"
                return

            # Success: refresh this screen's own data, and tell the
            # Dashboard (which can't see this change on its own) to
            # refresh too.
            self._render()
            app_session.notify_data_changed()

        submit_button = PrimaryButton(text="Record Transaction")
        submit_button.width = 440
        submit_button.bind(on_release=on_submit)

        for widget in [
            type_spinner, description_field, amount_field, category_spinner,
            date_field, error_label, submit_button,
        ]:
            card.add_widget(widget)

        return card

    def _build_history_card(self, business_id: str):
        transactions = FinanceService.list_transactions(business_id)

        if not transactions:
            card = Card(title="Transaction History", size_hint=(1, None), height=90)
            card.add_widget(
                Label(
                    text="No transactions recorded yet.", color=Theme.colors.TEXT_SECONDARY,
                    font_size=Theme.typography.BODY,
                )
            )
            return card

        rows = [
            (
                t.transaction_date,
                TRANSACTION_TYPE_LABELS[t.transaction_type],
                t.description,
                t.category,
                format_cents_as_rand(t.amount_cents if t.transaction_type == INCOME else -t.amount_cents),
            )
            for t in transactions
        ]
        card = Card(title="Transaction History", size_hint=(1, None), height=90 + min(len(rows), 10) * 40)
        card.add_widget(
            DataTable(
                columns=["Date", "Type", "Description", "Category", "Amount"],
                rows=rows,
                size_hint=(1, None),
                height=40 + min(len(rows), 10) * 40,
            )
        )
        return card
