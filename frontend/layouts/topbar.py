"""
topbar.py

The Business OS top bar.

Shows the official SKURGE / THE BUSINESS OS brand identity (from
app.branding.Branding), the current section's title (kept in sync by
NavigationManager), and placeholders for notifications and the user
account area. No real notification or account logic exists yet.

Step 7: the brand name "SKURGE" now uses the purple SKURGE/AI accent
color rather than the generic PRIMARY (gold, used for actions).
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.branding import Branding
from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class TopBar(BackgroundColorMixin, BoxLayout):
    """Fixed-height header bar shown across every section."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint=(1, None),
            height=Theme.dimensions.TOPBAR_HEIGHT,
            padding=(Theme.dimensions.SPACE_MD, 0),
            spacing=Theme.dimensions.SPACE_MD,
            **kwargs,
        )
        self.set_background_color(Theme.colors.SURFACE)

        # --- Brand identity: SKURGE / THE BUSINESS OS ---
        brand_column = BoxLayout(orientation="vertical", size_hint=(None, 1), width=200)

        self.brand_name_label = Label(
            text=Branding.APP_NAME,
            color=Theme.colors.PURPLE,
            font_size=Theme.typography.HEADING,
            bold=True,
            size_hint=(1, None),
            height=26,
            halign="left",
            valign="bottom",
        )
        self.brand_name_label.bind(
            size=lambda *_: setattr(self.brand_name_label, "text_size", self.brand_name_label.size)
        )

        self.brand_subtitle_label = Label(
            text=Branding.APP_SUBTITLE,
            color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.CAPTION,
            size_hint=(1, None),
            height=14,
            halign="left",
            valign="top",
        )
        self.brand_subtitle_label.bind(
            size=lambda *_: setattr(
                self.brand_subtitle_label, "text_size", self.brand_subtitle_label.size
            )
        )

        brand_column.add_widget(self.brand_name_label)
        brand_column.add_widget(self.brand_subtitle_label)

        # --- Current section title (kept in sync by NavigationManager) ---
        self.section_title_label = Label(
            text="Dashboard",
            color=Theme.colors.TEXT_PRIMARY,
            font_size=Theme.typography.LABEL,
            size_hint=(1, 1),
            halign="left",
            valign="middle",
        )
        self.section_title_label.bind(
            size=lambda *_: setattr(
                self.section_title_label, "text_size", self.section_title_label.size
            )
        )

        # Placeholders only — real functionality comes in later phases.
        self.notifications_label = Label(
            text="Notifications",
            color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.LABEL,
            size_hint=(None, 1),
            width=140,
        )
        self.account_label = Label(
            text="Account",
            color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.LABEL,
            size_hint=(None, 1),
            width=100,
        )

        self.add_widget(brand_column)
        self.add_widget(self.section_title_label)
        self.add_widget(self.notifications_label)
        self.add_widget(self.account_label)

    def update_title(self, title: str) -> None:
        """Update the visible section title. Called by NavigationManager."""
        self.section_title_label.text = title