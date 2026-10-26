"""
form_container.py

Reusable vertical form layout.

FormContainer stacks fields and an action-button row with consistent
spacing. It has no idea what "business registration" or "employee
creation" means — a screen builds its own fields and hands them to a
FormContainer for consistent layout.

Usage:
    form = FormContainer()
    form.add_field(TextInputField(label="Company name"))
    form.add_actions([SecondaryButton(text="Cancel"), PrimaryButton(text="Save")])
"""

from kivy.uix.boxlayout import BoxLayout

from styles.theme import Theme


class FormContainer(BoxLayout):
    """Vertical container that lays out form fields with consistent spacing."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", Theme.dimensions.SPACE_MD)
        kwargs.setdefault("padding", Theme.dimensions.SPACE_MD)
        kwargs.setdefault("size_hint", (1, None))
        super().__init__(**kwargs)
        self.bind(minimum_height=self.setter("height"))

    def add_field(self, field_widget) -> None:
        """Add a single field (e.g. TextInputField) to the form."""
        self.add_widget(field_widget)

    def add_actions(self, buttons: list) -> None:
        """Add a row of action buttons (e.g. Cancel + Save) at the bottom."""
        row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=Theme.dimensions.BUTTON_HEIGHT,
            spacing=Theme.dimensions.SPACE_SM,
        )
        for button in buttons:
            row.add_widget(button)
        self.add_widget(row)