"""
placeholder_screen.py

A reusable "Coming Soon" screen.

One instance of this is created for every section in
app.navigation.SECTIONS. As each real module is built (Employees,
Payroll, Finance, etc.), its PlaceholderScreen will be swapped out
for a real screen — nothing else in the navigation system needs to
change when that happens.
"""

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class PlaceholderScreen(BackgroundColorMixin, Screen):
    """Generic placeholder shown for sections that aren't built yet."""

    def __init__(self, section_title: str, **kwargs):
        super().__init__(**kwargs)
        self.set_background_color(Theme.colors.BACKGROUND)

        content = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(420, 120),
            spacing=Theme.dimensions.SPACE_SM,
        )

        title_label = Label(
            text=section_title,
            font_size=Theme.typography.TITLE,
            color=Theme.colors.TEXT_PRIMARY,
            bold=True,
        )
        subtitle_label = Label(
            text="Coming soon",
            font_size=Theme.typography.BODY,
            color=Theme.colors.TEXT_SECONDARY,
        )

        content.add_widget(title_label)
        content.add_widget(subtitle_label)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(content)
        self.add_widget(anchor)