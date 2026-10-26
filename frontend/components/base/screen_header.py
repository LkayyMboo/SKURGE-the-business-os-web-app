"""
screen_header.py

Reusable screen header: title + optional subtitle + optional
right-side action area (e.g. an "Add Employee" button later).

Used by BaseScreen so every real screen gets a consistent header
without duplicating this layout code. Holds no business logic.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from styles.theme import Theme


class ScreenHeader(BoxLayout):
    """A title/subtitle row with an optional action area on the right."""

    def __init__(self, title: str, subtitle: str = "", actions: list = None, **kwargs):
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 64)
        kwargs.setdefault("spacing", Theme.dimensions.SPACE_MD)
        super().__init__(**kwargs)

        text_column = BoxLayout(orientation="vertical", size_hint=(1, 1))

        title_label = Label(
            text=title,
            color=Theme.colors.TEXT_PRIMARY,
            font_size=Theme.typography.TITLE,
            bold=True,
            size_hint=(1, None),
            height=32,
            halign="left",
            valign="middle",
        )
        title_label.bind(size=lambda *_: setattr(title_label, "text_size", title_label.size))
        text_column.add_widget(title_label)

        if subtitle:
            subtitle_label = Label(
                text=subtitle,
                color=Theme.colors.TEXT_SECONDARY,
                font_size=Theme.typography.BODY,
                size_hint=(1, None),
                height=24,
                halign="left",
                valign="middle",
            )
            subtitle_label.bind(
                size=lambda *_: setattr(subtitle_label, "text_size", subtitle_label.size)
            )
            text_column.add_widget(subtitle_label)

        self.add_widget(text_column)

        if actions:
            action_area = BoxLayout(
                orientation="horizontal",
                size_hint=(None, 1),
                spacing=Theme.dimensions.SPACE_SM,
            )
            action_area.width = sum(getattr(a, "width", 120) for a in actions) + (
                Theme.dimensions.SPACE_SM * len(actions)
            )
            for action in actions:
                action_area.add_widget(action)
            self.add_widget(action_area)