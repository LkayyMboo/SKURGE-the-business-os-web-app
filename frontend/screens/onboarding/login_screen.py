"""
login_screen.py

Login screen. Calls AuthService (dev-only, in-memory, see
services/auth_service.py) to verify credentials, then reports
success via callback — app.py decides what happens next.
"""

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from components.base.background_mixin import BackgroundColorMixin
from components.buttons.buttons import PrimaryButton, SecondaryButton
from components.inputs.inputs import PasswordInputField, TextInputField
from services.auth_service import AuthService
from styles.theme import Theme


class LoginScreen(BackgroundColorMixin, Screen):
    def __init__(self, on_login_success=None, on_switch_to_register=None, on_back=None, **kwargs):
        super().__init__(**kwargs)
        self._on_login_success = on_login_success
        self._on_switch_to_register = on_switch_to_register
        self._on_back = on_back
        self.set_background_color(Theme.colors.BACKGROUND)

        stack = BoxLayout(
            orientation="vertical", size_hint=(None, None), size=(380, 400),
            spacing=Theme.dimensions.FIELD_SPACING,
        )

        title_label = Label(
            text="Sign in to SKURGE", color=Theme.colors.TEXT_PRIMARY, bold=True,
            font_size=Theme.typography.HEADING, size_hint=(1, None), height=32,
        )
        title_spacer = Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING)

        self.email_field = TextInputField(label="Email", placeholder="you@business.co.za")
        self.password_field = PasswordInputField(label="Password")

        self._error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        sign_in_button = PrimaryButton(text="Sign In")
        sign_in_button.width = 380
        sign_in_button.bind(on_release=lambda *_: self._attempt_login())

        switch_row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=30,
            spacing=Theme.dimensions.SPACE_SM,
        )
        switch_row.add_widget(
            Label(text="Don't have an account?", color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.CAPTION)
        )
        register_link = SecondaryButton(text="Create one")
        register_link.bind(on_release=lambda *_: self._on_switch_to_register and self._on_switch_to_register())
        switch_row.add_widget(register_link)

        back_button = SecondaryButton(text="Back")
        back_button.bind(on_release=lambda *_: self._on_back and self._on_back())

        for widget in [
            title_label, title_spacer, self.email_field, self.password_field,
            self._error_label, sign_in_button, switch_row, back_button,
        ]:
            stack.add_widget(widget)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(stack)
        self.add_widget(anchor)

    def _attempt_login(self) -> None:
        self._error_label.text = ""
        self.email_field.clear_message()
        self.password_field.clear_message()

        email = self.email_field.text.strip()
        password = self.password_field.text

        if not email or not password:
            self._error_label.text = "Please enter your email and password."
            return

        try:
            user = AuthService.login(email, password)
        except ValueError as error:
            self._error_label.text = str(error)
            return

        if self._on_login_success:
            self._on_login_success(user)