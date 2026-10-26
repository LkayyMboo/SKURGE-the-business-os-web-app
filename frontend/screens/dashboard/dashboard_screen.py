"""
dashboard_screen.py

The real Business OS Dashboard screen. Replaces the Step 4
PlaceholderScreen previously shown for the "dashboard" section.

Gets ALL of its numbers from DashboardService — never invents data
itself. Built from BaseScreen (Step 6) and Step 5's reusable
components (StatCard, Card). No second component system introduced.

Phase 8: reads the real onboarded business (if any) from
app.session.app_session, so the Business Summary card reflects actual
business data instead of always showing demo text.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from app.session import app_session
from components.cards.card import Card, StatCard
from screens.base_screen import BaseScreen
from services.dashboard_service import DashboardService
from styles.theme import Theme


class DashboardScreen(BaseScreen):
    """The main Business OS dashboard."""

    def __init__(self, **kwargs):
        super().__init__(title="Dashboard", subtitle="Overview of your business", **kwargs)

        data = DashboardService.get_dashboard_data(business=app_session.current_business)

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical",
            spacing=Theme.dimensions.SPACE_LG,
            size_hint=(1, None),
        )
        body.bind(minimum_height=body.setter("height"))

        # --- Business overview stat cards ---
        stats_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=100,
            spacing=Theme.dimensions.SPACE_MD,
        )
        stats_row.add_widget(
            StatCard(label="Revenue", value=data["revenue"], accent_color=Theme.colors.GOLD, size_hint=(1, 1))
        )
        stats_row.add_widget(StatCard(label="Expenses", value=data["expenses"], size_hint=(1, 1)))
        stats_row.add_widget(StatCard(label="Orders", value=data["orders"], size_hint=(1, 1)))
        stats_row.add_widget(StatCard(label="Employees", value=data["employees"], size_hint=(1, 1)))
        body.add_widget(stats_row)

        # --- Business summary ---
        summary_card = Card(title="Business Summary", size_hint=(1, None), height=100)
        summary_card.add_widget(
            Label(
                text=data["business_summary"],
                color=Theme.colors.TEXT_SECONDARY,
                font_size=Theme.typography.BODY,
            )
        )
        body.add_widget(summary_card)

        # --- Recent transactions ---
        transactions = data["recent_transactions"]
        transactions_card = Card(
            title="Recent Transactions",
            size_hint=(1, None),
            height=60 + max(1, len(transactions)) * 32,
        )
        for transaction in transactions:
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=28)
            row.add_widget(
                Label(text=transaction["description"], color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY)
            )
            row.add_widget(
                Label(text=transaction["amount"], color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY)
            )
            row.add_widget(
                Label(text=transaction["date"], color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.CAPTION)
            )
            transactions_card.add_widget(row)
        body.add_widget(transactions_card)

        # --- Alerts ---
        alerts = data["alerts"]
        alerts_card = Card(title="Alerts", size_hint=(1, None), height=60 + max(1, len(alerts)) * 28)
        for alert in alerts:
            alerts_card.add_widget(
                Label(text=alert["message"], color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY)
            )
        body.add_widget(alerts_card)

        scroll.add_widget(body)
        self.content.add_widget(scroll)
