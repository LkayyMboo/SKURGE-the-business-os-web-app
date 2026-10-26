"""
background_mixin.py

Reusable mixin that gives any Kivy widget a solid, optionally rounded,
background color.

Kivy widgets have no background color by default — you must draw one
manually on the canvas. Sidebar, TopBar, cards, buttons, and dialogs
all need this, so it's written ONCE here.

Pass radius=0 (default) for a sharp-cornered rectangle (used by
Sidebar/TopBar/PlaceholderScreen). Pass radius > 0 for a rounded
rectangle (used by Cards, Buttons, and Dialog content) — this is how
Business OS gets a modern look without any extra graphics library.
"""

from kivy.graphics import Color, Rectangle, RoundedRectangle


class BackgroundColorMixin:
    """Adds a solid, auto-resizing, optionally rounded background color."""

    def set_background_color(self, color: tuple, radius: int = 0) -> None:
        with self.canvas.before:
            self._bg_color_instruction = Color(*color)
            if radius > 0:
                self._bg_rect = RoundedRectangle(
                    size=self.size, pos=self.pos, radius=[radius]
                )
            else:
                self._bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_background_rect, pos=self._update_background_rect)

    def _update_background_rect(self, instance, value) -> None:
        self._bg_rect.size = instance.size
        self._bg_rect.pos = instance.pos