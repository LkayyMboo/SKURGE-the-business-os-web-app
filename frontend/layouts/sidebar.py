"""
sidebar.py

The Business OS desktop sidebar.

Builds one SidebarButton per entry in app.navigation.SECTIONS. Each
button only knows its own section key — pressing it asks the
NavigationManager to navigate, and stops caring what happens next.

initial_section lets MainLayout tell the sidebar which item should
start highlighted — used when the app rebuilds the shell after a
theme or active-business change, so the user's current section stays
highlighted correctly instead of always resetting to Dashboard.

The active item is shown with a subtle elevated background plus a
thin gold accent bar on its left edge, rather than a solid block of
color, per the SKURGE visual identity (Step 7).
"""

from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.navigation import SECTIONS, DEFAULT_SECTION
from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class SidebarButton(ButtonBehavior, BackgroundColorMixin, Label):
    """A single clickable, highlightable sidebar entry."""

    def __init__(self, text: str, **kwargs):
        super().__init__(text=text, **kwargs)
        self.color = Theme.colors.SIDEBAR_TEXT
        self.font_size = Theme.typography.BODY
        self.size_hint_y = None
        self.height = Theme.dimensions.BUTTON_HEIGHT
        self.halign = "left"
        self.valign = "middle"
        self.padding = (Theme.dimensions.SPACE_MD, 0)
        self.set_background_color(Theme.colors.SIDEBAR_BACKGROUND)

        with self.canvas.before:
            self._accent_color = Color(*Theme.colors.SIDEBAR_ITEM_ACCENT)
            self._accent_color.a = 0
            self._accent_rect = Rectangle(pos=self.pos, size=(3, self.height))

        self.bind(size=self._on_layout_change, pos=self._on_layout_change)

    def _on_layout_change(self, *_args) -> None:
        self.text_size = self.size
        self._accent_rect.pos = self.pos
        self._accent_rect.size = (3, self.height)

    def set_active(self, is_active: bool) -> None:
        if is_active:
            self._bg_color_instruction.rgba = Theme.colors.SIDEBAR_ITEM_ACTIVE
            self.color = Theme.colors.SIDEBAR_TEXT_ACTIVE
            self.bold = True
            self._accent_color.a = 1
        else:
            self._bg_color_instruction.rgba = Theme.colors.SIDEBAR_BACKGROUND
            self.color = Theme.colors.SIDEBAR_TEXT
            self.bold = False
            self._accent_color.a = 0


class Sidebar(BackgroundColorMixin, BoxLayout):
    """Fixed-width vertical navigation panel."""

    def __init__(self, navigation_manager, initial_section: str = DEFAULT_SECTION, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(None, 1),
            width=Theme.dimensions.SIDEBAR_WIDTH,
            padding=(0, Theme.dimensions.SPACE_SM),
            **kwargs,
        )
        self.navigation_manager = navigation_manager
        self.set_background_color(Theme.colors.SIDEBAR_BACKGROUND)

        self._buttons: dict[str, SidebarButton] = {}
        for key, label in SECTIONS:
            button = SidebarButton(text=label)
            button.bind(on_release=lambda _instance, k=key: self._on_item_pressed(k))
            self._buttons[key] = button
            self.add_widget(button)

        self._set_active_button(initial_section)

    def _on_item_pressed(self, key: str) -> None:
        self.navigation_manager.navigate_to(key)
        self._set_active_button(key)

    def _set_active_button(self, key: str) -> None:
        for button_key, button in self._buttons.items():
            button.set_active(button_key == key)
