"""
base_screen.py

Shared foundation for every real Business OS screen.

Provides a themed background, a ScreenHeader (title + optional
subtitle), and a `content` container that subclasses fill with their
own widgets (typically a ScrollView). This is the pattern every real
module screen (Dashboard now; Employees, Payroll, Finance later)
builds on, so screen structure is written once, not per module.

BaseScreen has NO business logic — subclasses own their own data
and behavior.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import Screen

from components.base.background_mixin import BackgroundColorMixin
from components.base.screen_header import ScreenHeader
from styles.theme import Theme


class BaseScreen(BackgroundColorMixin, Screen):
    """Base class for every real (non-placeholder) Business OS screen."""

    def __init__(self, title: str, subtitle: str = "", header_actions: list = None, **kwargs):
        super().__init__(**kwargs)
        self.set_background_color(Theme.colors.BACKGROUND)

        outer = BoxLayout(
            orientation="vertical",
            padding=Theme.dimensions.SPACE_LG,
            spacing=Theme.dimensions.SPACE_LG,
        )

        self.header = ScreenHeader(title=title, subtitle=subtitle, actions=header_actions)
        outer.add_widget(self.header)

        # Subclasses add their own widgets (usually a ScrollView) here.
        self.content = BoxLayout(orientation="vertical", spacing=Theme.dimensions.SPACE_LG)
        outer.add_widget(self.content)

        self.add_widget(outer)