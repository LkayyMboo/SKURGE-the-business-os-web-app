"""
dialogs.py

Reusable dialog foundation, built on Kivy's Popup.

MessageDialog: title + message + a single OK button.
ConfirmationDialog: title + message + Confirm/Cancel, calling back
into whatever the opening screen supplies. Neither dialog knows
anything about real business operations.

Step 7: background="" plus background_color/title_color/
separator_color re-skin Popup's default light-gray chrome so dialogs
match the dark SKURGE theme instead of appearing as a light box.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from components.buttons.buttons import PrimaryButton, SecondaryButton
from styles.theme import Theme


class MessageDialog(Popup):
    """A simple dialog with a message and a single dismiss button."""

    def __init__(self, title: str, message: str, **kwargs):
        content = BoxLayout(
            orientation="vertical",
            spacing=Theme.dimensions.SPACE_MD,
            padding=Theme.dimensions.SPACE_MD,
        )
        content.add_widget(
            Label(text=message, color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY)
        )
        ok_button = PrimaryButton(text="OK")
        ok_button.bind(on_release=lambda *_: self.dismiss())
        content.add_widget(ok_button)

        super().__init__(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(360, 200),
            background="",
            background_color=Theme.colors.SURFACE_ELEVATED,
            title_color=Theme.colors.TEXT_PRIMARY,
            separator_color=Theme.colors.BORDER,
            **kwargs,
        )


class ConfirmationDialog(Popup):
    """A dialog asking the user to confirm or cancel an action."""

    def __init__(self, title: str, message: str, on_confirm=None, on_cancel=None, **kwargs):
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        content = BoxLayout(
            orientation="vertical",
            spacing=Theme.dimensions.SPACE_MD,
            padding=Theme.dimensions.SPACE_MD,
        )
        content.add_widget(
            Label(text=message, color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY)
        )

        button_row = BoxLayout(
            orientation="horizontal",
            spacing=Theme.dimensions.SPACE_SM,
            size_hint=(1, None),
            height=Theme.dimensions.BUTTON_HEIGHT,
        )
        cancel_button = SecondaryButton(text="Cancel")
        cancel_button.bind(on_release=self._handle_cancel)
        confirm_button = PrimaryButton(text="Confirm")
        confirm_button.bind(on_release=self._handle_confirm)
        button_row.add_widget(cancel_button)
        button_row.add_widget(confirm_button)
        content.add_widget(button_row)

        super().__init__(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(400, 220),
            background="",
            background_color=Theme.colors.SURFACE_ELEVATED,
            title_color=Theme.colors.TEXT_PRIMARY,
            separator_color=Theme.colors.BORDER,
            **kwargs,
        )

    def _handle_confirm(self, *_args) -> None:
        self.dismiss()
        if self._on_confirm:
            self._on_confirm()

    def _handle_cancel(self, *_args) -> None:
        self.dismiss()
        if self._on_cancel:
            self._on_cancel()