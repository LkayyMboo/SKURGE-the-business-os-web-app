"""
chart_placeholder.py

Reusable chart container foundation. No charting library is used —
this draws simple vertical bars directly on the canvas, scaled to
whatever values are passed in. Enough to represent "Revenue over
time" once real numbers exist, without adding a graphics dependency.

If richer charts (line, pie) are needed later, we introduce a real
charting library then and justify it first.

Usage:
    ChartPlaceholder(title="Revenue", values=[10, 40, 25, 60])
    ChartPlaceholder(title="Orders")  # shows "No data" state
"""

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class _BarCanvas(Widget):
    """Draws simple vertical bars scaled to the widget's height."""

    def __init__(self, values: list, **kwargs):
        super().__init__(**kwargs)
        self.values = values or []
        self.bind(size=self._redraw, pos=self._redraw)
        self._redraw()

    def _redraw(self, *_args) -> None:
        self.canvas.clear()
        if not self.values:
            return
        max_value = max(self.values) or 1
        bar_count = len(self.values)
        gap = 8
        bar_width = max(4, (self.width - gap * (bar_count + 1)) / bar_count)

        with self.canvas:
            Color(*Theme.colors.PRIMARY)
            x = self.x + gap
            for value in self.values:
                bar_height = (value / max_value) * (self.height - 10)
                Rectangle(pos=(x, self.y), size=(bar_width, bar_height))
                x += bar_width + gap


class ChartPlaceholder(BackgroundColorMixin, BoxLayout):
    """A simple bar-chart container. Shows a 'No data' state when empty."""

    def __init__(self, title: str = "", values: list = None, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", Theme.dimensions.SPACE_MD)
        kwargs.setdefault("spacing", Theme.dimensions.SPACE_SM)
        super().__init__(**kwargs)
        self.set_background_color(Theme.colors.SURFACE, radius=Theme.dimensions.RADIUS_MD)

        if title:
            self.add_widget(
                Label(
                    text=title,
                    color=Theme.colors.TEXT_PRIMARY,
                    font_size=Theme.typography.LABEL,
                    bold=True,
                    size_hint=(1, None),
                    height=24,
                )
            )

        if values:
            self.add_widget(_BarCanvas(values=values))
        else:
            self.add_widget(
                Label(text="No data", color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.BODY)
            )