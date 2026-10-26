"""
inputs.py

Reusable Business OS input field components.

Each field is: an optional label, the input box, then an optional
helper/error message below it. Real validation RULES are not
implemented here — only the visual foundation.

Step 7: background_normal/background_active are set to "" so Kivy
actually honors our background_color instead of drawing its own
default light-gray texture over it — necessary now that the app uses
a dark theme.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from styles.theme import Theme


class _BaseInputField(BoxLayout):
    """Shared layout: label -> input box -> helper/error text."""

    def __init__(self, label: str = "", placeholder: str = "", password: bool = False, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("spacing", Theme.dimensions.SPACE_XS)
        super().__init__(**kwargs)
        self.height = 70  # label + input + helper text

        if label:
            label_widget = Label(
                text=label,
                color=Theme.colors.TEXT_SECONDARY,
                font_size=Theme.typography.LABEL,
                size_hint=(1, None),
                height=18,
                halign="left",
                valign="middle",
            )
            label_widget.bind(
                size=lambda *_: setattr(label_widget, "text_size", label_widget.size)
            )
            self.add_widget(label_widget)

        self.input = TextInput(
            hint_text=placeholder,
            password=password,
            multiline=False,
            size_hint=(1, None),
            height=Theme.dimensions.INPUT_HEIGHT,
            font_size=Theme.typography.BODY,
            background_normal="",
            background_active="",
            background_color=Theme.colors.SURFACE_ELEVATED,
            foreground_color=Theme.colors.TEXT_PRIMARY,
            cursor_color=Theme.colors.GOLD,
            hint_text_color=Theme.colors.TEXT_SECONDARY,
            padding=(Theme.dimensions.SPACE_SM, Theme.dimensions.SPACE_SM),
        )
        self.add_widget(self.input)

        self._helper_label = Label(
            text="",
            color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.CAPTION,
            size_hint=(1, None),
            height=16,
            halign="left",
            valign="middle",
        )
        self._helper_label.bind(
            size=lambda *_: setattr(self._helper_label, "text_size", self._helper_label.size)
        )
        self.add_widget(self._helper_label)

    @property
    def text(self) -> str:
        return self.input.text

    @text.setter
    def text(self, value: str) -> None:
        self.input.text = value

    def set_helper_text(self, message: str) -> None:
        """Show a normal (non-error) helper message below the field."""
        self._helper_label.color = Theme.colors.TEXT_SECONDARY
        self._helper_label.text = message

    def set_error(self, message: str) -> None:
        """Show a validation error message below the field."""
        self._helper_label.color = Theme.colors.DANGER
        self._helper_label.text = message

    def clear_message(self) -> None:
        self._helper_label.text = ""


class TextInputField(_BaseInputField):
    """A standard single-line labeled text field."""

    def __init__(self, label: str = "", placeholder: str = "", **kwargs):
        super().__init__(label=label, placeholder=placeholder, password=False, **kwargs)


class PasswordInputField(_BaseInputField):
    """A masked text field for passwords."""

    def __init__(self, label: str = "Password", placeholder: str = "", **kwargs):
        super().__init__(label=label, placeholder=placeholder, password=True, **kwargs)


class SearchInput(_BaseInputField):
    """A search field — no label, no helper row, placeholder-driven."""

    def __init__(self, placeholder: str = "Search...", **kwargs):
        super().__init__(label="", placeholder=placeholder, password=False, **kwargs)
        self.remove_widget(self._helper_label)
        self.height = Theme.dimensions.INPUT_HEIGHT