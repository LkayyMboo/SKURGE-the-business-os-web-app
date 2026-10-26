"""
card.py

Reusable Card component — a rounded, padded surface used to group
related content (e.g. a dashboard metric, a summary panel, a form
section).

StatCard is a small preset for dashboard-style numeric summaries. It
only ever receives its label/value through parameters — it holds no
real business data.

Step 7: StatCard accepts an optional `accent_color`, drawn as a thin
bar across the top of the card — used sparingly (e.g. only the
Dashboard's Revenue card) as a controlled highlight, not a per-card
color scheme.
"""

from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class Card(BackgroundColorMixin, BoxLayout):
    """A rounded surface container for grouping related content."""

    def __init__(self, title: str = "", **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", Theme.dimensions.SPACE_MD)
        kwargs.setdefault("spacing", Theme.dimensions.SPACE_SM)
        super().__init__(**kwargs)
        self.set_background_color(Theme.colors.SURFACE, radius=Theme.dimensions.RADIUS_MD)

        if title:
            title_label = Label(
                text=title,
                color=Theme.colors.TEXT_PRIMARY,
                font_size=Theme.typography.LABEL,
                bold=True,
                size_hint=(1, None),
                height=24,
                halign="left",
                valign="middle",
            )
            title_label.bind(size=lambda *_: setattr(title_label, "text_size", title_label.size))
            self.add_widget(title_label)


class StatCard(Card):
    """A small preset Card for dashboard-style numeric summaries.

    Usage (values shown are examples only — this component holds no
    real data):
        StatCard(label="Revenue", value="R 0.00")
        StatCard(label="Revenue", value="R 0.00", accent_color=Theme.colors.GOLD)
    """

    def __init__(self, label: str, value: str, accent_color: tuple = None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (200, 100))
        super().__init__(title="", **kwargs)

        if accent_color:
            accent_bar = Widget(size_hint=(1, None), height=3)
            with accent_bar.canvas:
                Color(*accent_color)
                accent_rect = Rectangle(pos=accent_bar.pos, size=accent_bar.size)
            accent_bar.bind(
                pos=lambda *_: setattr(accent_rect, "pos", accent_bar.pos),
                size=lambda *_: setattr(accent_rect, "size", accent_bar.size),
            )
            self.add_widget(accent_bar)

        value_label = Label(
            text=value,
            color=Theme.colors.TEXT_PRIMARY,
            font_size=Theme.typography.HEADING,
            bold=True,
            size_hint=(1, None),
            height=32,
        )
        label_label = Label(
            text=label,
            color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.CAPTION,
            size_hint=(1, None),
            height=20,
        )
        self.add_widget(value_label)
        self.add_widget(label_label)