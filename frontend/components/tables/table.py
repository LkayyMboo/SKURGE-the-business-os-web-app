"""
table.py

Reusable table foundation.

DataTable takes column headers and row tuples and renders them as a
simple scrollable, styled grid. It has no idea what the data
represents (employees, orders, products) — a screen builds the
columns/rows and passes them in. Not connected to a database.

Usage:
    DataTable(
        columns=["Name", "Role"],
        rows=[("Jane Doe", "Manager"), ("John Smith", "Accountant")],
    )
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class _TableCell(BackgroundColorMixin, Label):
    def __init__(self, text: str, is_header: bool = False, **kwargs):
        super().__init__(text=text, **kwargs)
        self.size_hint_y = None
        self.height = 40
        self.halign = "left"
        self.valign = "middle"
        self.padding = (Theme.dimensions.SPACE_SM, 0)
        self.font_size = Theme.typography.LABEL if is_header else Theme.typography.BODY
        self.bold = is_header
        self.color = Theme.colors.TEXT_PRIMARY
        self.set_background_color(Theme.colors.BORDER if is_header else Theme.colors.SURFACE)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class DataTable(BoxLayout):
    """A simple, scrollable, styled table."""

    def __init__(self, columns: list, rows: list, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, 1))
        super().__init__(**kwargs)

        header_row = GridLayout(cols=len(columns), size_hint=(1, None), height=40)
        for column_name in columns:
            header_row.add_widget(_TableCell(text=column_name, is_header=True))
        self.add_widget(header_row)

        body_grid = GridLayout(cols=len(columns), size_hint_y=None)
        body_grid.bind(minimum_height=body_grid.setter("height"))
        for row in rows:
            for cell_value in row:
                body_grid.add_widget(_TableCell(text=str(cell_value)))

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(body_grid)
        self.add_widget(scroll)