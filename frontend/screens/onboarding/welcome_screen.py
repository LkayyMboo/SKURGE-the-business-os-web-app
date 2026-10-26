"""
welcome_screen.py

First screen after boot. Introduces SKURGE and routes to Sign In or
Create Account. Not a marketing page — a plain, professional desktop
app entry point, built from the same components as everything else.
"""

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.branding import Branding
from components.base.background_mixin import BackgroundColorMixin
from components.buttons.buttons import PrimaryButton, SecondaryButton
from styles.theme import Theme

VALUE_PROPS = [
    "Manage your essential business information in one place",
    "Understand your income and expenses",
    "See your cash flow clearly",
    "Spot risks and opportunities early",
    "Build a more organised, sustainable business",
]


class WelcomeScreen(BackgroundColorMixin, Screen):
    """Entry point screen. Reports the user's choice via callbacks only."""

    def __init__(self, on_sign_in=None, on_create_account=None, **kwargs):
        super().__init__(**kwargs)
        self._on_sign_in = on_sign_in
        self._on_create_account = on_create_account
        self.set_background_color(Theme.colors.BACKGROUND)

        stack = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(520, 520),
            spacing=Theme.dimensions.FIELD_SPACING,
        )

        brand_label = Label(
            text=Branding.APP_NAME, color=Theme.colors.PURPLE, bold=True,
            font_size=44, size_hint=(1, None), height=56,
        )
        subtitle_label = Label(
            text=Branding.APP_SUBTITLE, color=Theme.colors.TEXT_SECONDARY,
            font_size=Theme.typography.LABEL, size_hint=(1, None), height=22,
        )
        tagline_label = Label(
            text="A business operating system built for South African small businesses.",
            color=Theme.colors.TEXT_PRIMARY, font_size=Theme.typography.BODY,
            size_hint=(1, None), height=28,
        )

        stack.add_widget(brand_label)
        stack.add_widget(subtitle_label)
        stack.add_widget(Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING))
        stack.add_widget(tagline_label)
        stack.add_widget(Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING))

        for value_prop in VALUE_PROPS:
            item = Label(
                text=f"•  {value_prop}", color=Theme.colors.TEXT_SECONDARY,
                font_size=Theme.typography.BODY, size_hint=(1, None), height=26,
                halign="left", valign="middle",
            )
            # Default-arg capture (item=item) avoids the classic Python
            # closure bug where every lambda in this loop would otherwise
            # end up referencing only the LAST item created.
            item.bind(size=lambda _inst, _val, i=item: setattr(i, "text_size", i.size))
            stack.add_widget(item)

        stack.add_widget(Widget(size_hint=(1, None), height=Theme.dimensions.SECTION_SPACING))

        button_row = BoxLayout(
            orientation="horizontal", size_hint=(1, None),
            height=Theme.dimensions.BUTTON_HEIGHT, spacing=Theme.dimensions.SPACE_SM,
        )
        sign_in_button = SecondaryButton(text="Sign In")
        sign_in_button.bind(on_release=lambda *_: self._on_sign_in and self._on_sign_in())
        create_account_button = PrimaryButton(text="Create Account")
        create_account_button.bind(on_release=lambda *_: self._on_create_account and self._on_create_account())
        button_row.add_widget(sign_in_button)
        button_row.add_widget(create_account_button)
        stack.add_widget(button_row)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(stack)
        self.add_widget(anchor)