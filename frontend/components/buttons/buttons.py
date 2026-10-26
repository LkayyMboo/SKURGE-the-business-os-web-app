"""
buttons.py

Reusable Business OS button components.

All buttons share one base (_BaseButton): consistent height, padding,
typography, rounded corners, and pressed-state color feedback. Each
variant only supplies its own colors.

Buttons never decide what happens when clicked — the screen using
them attaches its own handler.
"""

from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.label import Label

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class _BaseButton(ButtonBehavior, BackgroundColorMixin, Label):
    """Shared button behavior. Not used directly — use a variant below."""

    def __init__(self, text: str, bg_color, bg_color_pressed, text_color, **kwargs):
        super().__init__(text=text, **kwargs)
        self._bg_color = bg_color
        self._bg_color_pressed = bg_color_pressed

        self.color = text_color
        self.font_size = Theme.typography.BODY
        self.bold = True
        self.size_hint = (None, None)
        self.height = Theme.dimensions.BUTTON_HEIGHT
        self.width = max(120, len(text) * 10 + 40)
        self.halign = "center"
        self.valign = "middle"
        self.set_background_color(bg_color, radius=Theme.dimensions.RADIUS_MD)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

    def on_press(self):
        self._bg_color_instruction.rgba = self._bg_color_pressed

    def on_release(self):
        self._bg_color_instruction.rgba = self._bg_color


class PrimaryButton(_BaseButton):
    """Main call-to-action button (e.g. Save, Submit, Create)."""

    def __init__(self, text: str = "Button", **kwargs):
        super().__init__(
            text=text,
            bg_color=Theme.colors.PRIMARY,
            bg_color_pressed=Theme.colors.PRIMARY_DARK,
            text_color=Theme.colors.TEXT_ON_GOLD,
            **kwargs,
        )


class SecondaryButton(_BaseButton):
    """Lower-emphasis button (e.g. Cancel, Back)."""

    def __init__(self, text: str = "Button", **kwargs):
        super().__init__(
            text=text,
            bg_color=Theme.colors.SURFACE,
            bg_color_pressed=Theme.colors.BORDER,
            text_color=Theme.colors.TEXT_PRIMARY,
            **kwargs,
        )


class DangerButton(_BaseButton):
    """Destructive action button (e.g. Delete, Remove)."""

    def __init__(self, text: str = "Button", **kwargs):
        super().__init__(
            text=text,
            bg_color=Theme.colors.DANGER,
            bg_color_pressed=Theme.colors.DANGER_DARK,
            text_color=Theme.colors.TEXT_ON_PRIMARY,
            **kwargs,
        )


class IconButton(ButtonBehavior, BackgroundColorMixin, Label):
    """A small square button for a single icon/glyph (e.g. '+', 'x')."""

    def __init__(self, text: str = "•", **kwargs):
        super().__init__(text=text, **kwargs)
        self.color = Theme.colors.TEXT_PRIMARY
        self.font_size = Theme.typography.LABEL
        self.size_hint = (None, None)
        self.size = (Theme.dimensions.BUTTON_HEIGHT, Theme.dimensions.BUTTON_HEIGHT)
        self.halign = "center"
        self.valign = "middle"
        self.set_background_color(Theme.colors.SURFACE, radius=Theme.dimensions.RADIUS_MD)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

    def on_press(self):
        self._bg_color_instruction.rgba = Theme.colors.BORDER

    def on_release(self):
        self._bg_color_instruction.rgba = Theme.colors.SURFACE