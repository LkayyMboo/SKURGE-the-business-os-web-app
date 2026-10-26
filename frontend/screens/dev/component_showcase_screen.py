"""
component_showcase_screen.py

DEVELOPMENT-ONLY screen.

Demonstrates every reusable component built in Step 5 so we can
visually verify them together. NOT one of the 16 Business OS
sections and NOT linked from the sidebar — opened only via the F12
shortcut wired in main_layout.py. Deleting this file and its
registration in main_layout.py removes it with zero impact on
navigation.py, sidebar.py, or SECTIONS.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from components.base.background_mixin import BackgroundColorMixin
from components.buttons.buttons import PrimaryButton, SecondaryButton, DangerButton, IconButton
from components.cards.card import Card, StatCard
from components.charts.chart_placeholder import ChartPlaceholder
from components.dialogs.dialogs import ConfirmationDialog, MessageDialog
from components.forms.form_container import FormContainer
from components.inputs.inputs import TextInputField, PasswordInputField, SearchInput
from components.loading.loading_indicator import LoadingIndicator
from components.tables.table import DataTable
from styles.theme import Theme


def _section_label(text: str) -> Label:
    label = Label(
        text=text,
        color=Theme.colors.TEXT_PRIMARY,
        font_size=Theme.typography.HEADING,
        bold=True,
        size_hint=(1, None),
        height=32,
        halign="left",
        valign="middle",
    )
    label.bind(size=lambda *_: setattr(label, "text_size", label.size))
    return label


class ComponentShowcaseScreen(BackgroundColorMixin, Screen):
    """DEV ONLY — visual test bed for every Step 5 component."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_background_color(Theme.colors.BACKGROUND)

        root = ScrollView(size_hint=(1, 1))
        content = BoxLayout(
            orientation="vertical",
            spacing=Theme.dimensions.SPACE_LG,
            padding=Theme.dimensions.SPACE_LG,
            size_hint=(1, None),
        )
        content.bind(minimum_height=content.setter("height"))

        # --- Buttons ---
        content.add_widget(_section_label("Buttons"))
        button_row = BoxLayout(size_hint=(1, None), height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM)
        button_row.add_widget(PrimaryButton(text="Save"))
        button_row.add_widget(SecondaryButton(text="Cancel"))
        button_row.add_widget(DangerButton(text="Delete"))
        button_row.add_widget(IconButton(text="+"))
        content.add_widget(button_row)

        # --- Cards ---
        content.add_widget(_section_label("Cards"))
        card_row = BoxLayout(size_hint=(1, None), height=120, spacing=Theme.dimensions.SPACE_MD)
        card_row.add_widget(StatCard(label="Revenue", value="R 0.00"))
        card_row.add_widget(StatCard(label="Orders", value="0"))
        card_row.add_widget(StatCard(label="Employees", value="0"))
        content.add_widget(card_row)

        info_card = Card(title="Business Summary", size_hint=(1, None), height=100)
        info_card.add_widget(Label(text="Card content goes here.", color=Theme.colors.TEXT_SECONDARY))
        content.add_widget(info_card)

        # --- Inputs ---
        content.add_widget(_section_label("Inputs"))
        content.add_widget(TextInputField(label="Company name", placeholder="e.g. Acme Pty Ltd"))
        content.add_widget(PasswordInputField())
        content.add_widget(SearchInput())

        # --- Form ---
        content.add_widget(_section_label("Form"))
        form = FormContainer(size_hint=(1, None))
        form.add_field(TextInputField(label="Email"))
        form.add_actions([SecondaryButton(text="Cancel"), PrimaryButton(text="Submit")])
        content.add_widget(form)

        # --- Dialogs ---
        content.add_widget(_section_label("Dialogs"))
        dialog_row = BoxLayout(size_hint=(1, None), height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM)
        message_button = SecondaryButton(text="Show Message Dialog")
        message_button.bind(on_release=lambda *_: MessageDialog(title="Notice", message="This is a message dialog.").open())
        confirm_button = SecondaryButton(text="Show Confirmation Dialog")
        confirm_button.bind(
            on_release=lambda *_: ConfirmationDialog(
                title="Confirm action",
                message="Are you sure?",
                on_confirm=lambda: print("Confirmed"),
                on_cancel=lambda: print("Cancelled"),
            ).open()
        )
        dialog_row.add_widget(message_button)
        dialog_row.add_widget(confirm_button)
        content.add_widget(dialog_row)

        # --- Table ---
        content.add_widget(_section_label("Table"))
        content.add_widget(
            DataTable(
                columns=["Name", "Role"],
                rows=[("Jane Doe", "Manager"), ("John Smith", "Accountant")],
                size_hint=(1, None),
                height=160,
            )
        )

        # --- Chart ---
        content.add_widget(_section_label("Chart placeholder"))
        chart_row = BoxLayout(size_hint=(1, None), height=150, spacing=Theme.dimensions.SPACE_MD)
        chart_row.add_widget(ChartPlaceholder(title="Revenue", values=[10, 40, 25, 60, 30]))
        chart_row.add_widget(ChartPlaceholder(title="Orders"))  # no-data state
        content.add_widget(chart_row)

        # --- Loading ---
        content.add_widget(_section_label("Loading indicator"))
        content.add_widget(LoadingIndicator())

        root.add_widget(content)
        self.add_widget(root)