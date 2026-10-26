"""
register_screen.py

Registration screen. Calls AuthService (dev-only, in-memory) to
create a new account, then hands the new User back via callback —
app.py decides what happens next (business setup).
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

MIN_PASSWORD_LENGTH = 8


class RegisterScreen(BackgroundColorMixin, Screen):
    def __init__(self, on_register_success=None, on_switch_to_login=None, on_back=None, **kwargs):
        super().__init__(**kwargs)
        self._on_register_success = on_register_success
        self._on_switch_to_login = on_switch_to_login
        self._on_back = on_back
        self.set_background_color(Theme.colors.BACKGROUND)

        stack = BoxLayout(
            orientation="vertical", size_hint=(None, None), size=(380, 520),
            spacing=Theme.dimensions.FIELD_SPACING,
        )

        title_label = Label(
            text="Create your SKURGE account", color=Theme.colors.TEXT_PRIMARY, bold=True,
            font_size=Theme.typography.HEADING, size_hint=(1, None), height=32,
        )
        title_spacer = Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING)

        self.full_name_field = TextInputField(label="Full name", placeholder="Jane Doe")
        self.email_field = TextInputField(label="Email", placeholder="you@business.co.za")
        self.password_field = PasswordInputField(label="Password")
        self.confirm_password_field = PasswordInputField(label="Confirm password")

        self._error_label = Label(
            text="", color=Theme.colors.DANGER, font_size=Theme.typography.CAPTION,
            size_hint=(1, None), height=20,
        )

        create_button = PrimaryButton(text="Create Account")
        create_button.width = 380
        create_button.bind(on_release=lambda *_: self._attempt_register())

        switch_row = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=30,
            spacing=Theme.dimensions.SPACE_SM,
        )
        switch_row.add_widget(
            Label(text="Already have an account?", color=Theme.colors.TEXT_SECONDARY, font_size=Theme.typography.CAPTION)
        )
        login_link = SecondaryButton(text="Sign in")
        login_link.bind(on_release=lambda *_: self._on_switch_to_login and self._on_switch_to_login())
        switch_row.add_widget(login_link)

        back_button = SecondaryButton(text="Back")
        back_button.bind(on_release=lambda *_: self._on_back and self._on_back())

        for widget in [
            title_label, title_spacer, self.full_name_field, self.email_field,
            self.password_field, self.confirm_password_field,
            self._error_label, create_button, switch_row, back_button,
        ]:
            stack.add_widget(widget)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(stack)
        self.add_widget(anchor)

    def _attempt_register(self) -> None:
        self._error_label.text = ""

        full_name = self.full_name_field.text.strip()
        email = self.email_field.text.strip()
        password = self.password_field.text
        confirm_password = self.confirm_password_field.text

        if not full_name or not email or not password or not confirm_password:
            self._error_label.text = "All fields are required."
            return
        if password != confirm_password:
            self._error_label.text = "Passwords do not match."
            return
        if len(password) < MIN_PASSWORD_LENGTH:
            self._error_label.text = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            return

        try:
            user = AuthService.register(full_name, email, password)
        except ValueError as error:
            self._error_label.text = str(error)
            return

        if self._on_register_success:
            self._on_register_success(user)