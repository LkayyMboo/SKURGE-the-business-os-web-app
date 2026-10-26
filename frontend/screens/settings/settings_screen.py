"""
settings_screen.py

Business OS Settings screen.

Contains:
- Business: shows the active business and lets the user switch to
  another one of their businesses, if they have more than one.
- Appearance: Dark/Light mode toggle (Phase 7).

Other settings (account, security, company) stay placeholders until
later phases. Business-switching logic lives in AppSession /
BusinessService — this screen only calls app_session.switch_business()
and displays the result; it does not touch the database directly.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner

from app.session import app_session
from components.buttons.buttons import PrimaryButton, SecondaryButton
from components.cards.card import Card
from screens.base_screen import BaseScreen
from styles.theme import DARK, LIGHT, Theme


class SettingsScreen(BaseScreen):
    """The Business OS settings screen."""

    def __init__(self, **kwargs):
        super().__init__(
            title="Settings", subtitle="Manage your application preferences", **kwargs
        )

        scroll = ScrollView(size_hint=(1, 1))
        body = BoxLayout(
            orientation="vertical", spacing=Theme.dimensions.SECTION_SPACING, size_hint=(1, None)
        )
        body.bind(minimum_height=body.setter("height"))

        body.add_widget(self._build_business_card())
        body.add_widget(self._build_appearance_card())

        scroll.add_widget(body)
        self.content.add_widget(scroll)

    def _build_business_card(self):
        businesses = app_session.get_user_businesses()
        current = app_session.current_business

        card = Card(title="Business", size_hint=(1, None), height=150)

        if not businesses:
            card.add_widget(
                Label(
                    text="No business profile found for this account.",
                    color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
                    size_hint=(1, None), height=24,
                )
            )
            return card

        active_label = Label(
            text=f"Active business: {current.name if current else 'None selected'}",
            color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=24, halign="left", valign="middle",
        )
        active_label.bind(size=lambda *_: setattr(active_label, "text_size", active_label.size))
        card.add_widget(active_label)

        if len(businesses) > 1:
            names_by_id = {b.id: b.name for b in businesses}
            id_by_name = {b.name: b.id for b in businesses}

            switch_row = BoxLayout(
                orientation="horizontal", size_hint=(1, None),
                height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM,
            )
            spinner = Spinner(
                text=current.name if current else businesses[0].name,
                values=list(names_by_id.values()),
                size_hint=(1, None), height=Theme.dimensions.INPUT_HEIGHT,
                background_color=Theme.colors.SURFACE_ELEVATED, color=Theme.colors.TEXT_PRIMARY,
            )
            switch_button = SecondaryButton(text="Switch")
            switch_button.bind(
                on_release=lambda *_: app_session.switch_business(id_by_name[spinner.text])
            )
            switch_row.add_widget(spinner)
            switch_row.add_widget(switch_button)
            card.add_widget(switch_row)
        else:
            card.height = 90  # No switcher needed for a single business.

        return card

    def _build_appearance_card(self):
        card = Card(title="Appearance", size_hint=(1, None), height=140)

        description = Label(
            text="Choose how SKURGE looks on this device.",
            color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=24, halign="left", valign="middle",
        )
        description.bind(size=lambda *_: setattr(description, "text_size", description.size))
        card.add_widget(description)

        button_row = BoxLayout(
            orientation="horizontal", size_hint=(1, None),
            height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM,
        )
        current_mode = Theme.manager.mode

        dark_button = (PrimaryButton if current_mode == DARK else SecondaryButton)(text="Dark")
        dark_button.bind(on_release=lambda *_: Theme.manager.set_mode(DARK))

        light_button = (PrimaryButton if current_mode == LIGHT else SecondaryButton)(text="Light")
        light_button.bind(on_release=lambda *_: Theme.manager.set_mode(LIGHT))

        button_row.add_widget(dark_button)
        button_row.add_widget(light_button)
        card.add_widget(button_row)

        return card
