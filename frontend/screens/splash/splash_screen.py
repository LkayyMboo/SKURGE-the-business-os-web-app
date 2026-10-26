"""
splash_screen.py

The SKURGE boot/startup screen — the first thing shown when the
application launches, before the main application shell appears.

This screen intentionally does NOT follow the user's Dark/Light
setting — it uses FixedColors, not Theme.colors, for anything that
must render correctly against its always-dark background. The SKURGE
brand name uses Theme.colors.PURPLE anyway, which is identical in
both palettes, so it's safe to read normally.

_startup_triggered guards against on_enter firing more than once and
starting a second overlapping boot timer.
"""

from kivy.graphics import Color, Rectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.branding import Branding
from components.base.background_mixin import BackgroundColorMixin
from components.loading.loading_indicator import LoadingIndicator
from services.startup_service import StartupService
from styles.colors import FixedColors
from styles.theme import Theme


class SplashScreen(BackgroundColorMixin, Screen):
    """SKURGE boot screen. Calls on_complete() once the boot sequence finishes."""

    def __init__(self, on_complete=None, **kwargs):
        super().__init__(**kwargs)
        self._on_complete = on_complete
        self._startup_triggered = False
        self.set_background_color(FixedColors.SPLASH_BACKGROUND)

        stack = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            size=(480, 230),
            spacing=Theme.dimensions.SPACE_MD,
        )

        brand_label = Label(
            text=Branding.APP_NAME,
            color=Theme.colors.PURPLE,  # Identity color — same in both modes
            font_size=56,
            bold=True,
            size_hint=(1, None),
            height=64,
        )

        accent_line = Widget(size_hint=(None, None), size=(120, 3), pos_hint={"center_x": 0.5})
        with accent_line.canvas:
            Color(*Theme.colors.GOLD)  # Identity color — same in both modes
            accent_rect = Rectangle(pos=accent_line.pos, size=accent_line.size)
        accent_line.bind(
            pos=lambda *_: setattr(accent_rect, "pos", accent_line.pos),
            size=lambda *_: setattr(accent_rect, "size", accent_line.size),
        )
        accent_wrapper = AnchorLayout(size_hint=(1, None), height=12, anchor_x="center")
        accent_wrapper.add_widget(accent_line)

        subtitle_label = Label(
            text=Branding.APP_SUBTITLE,
            color=FixedColors.SPLASH_TEXT_SECONDARY,
            font_size=Theme.typography.LABEL,
            size_hint=(1, None),
            height=24,
        )

        loading_wrapper = AnchorLayout(size_hint=(1, None), height=48, anchor_x="center")
        self._loading_indicator = LoadingIndicator(
            text="Starting SKURGE...",
            text_color=FixedColors.SPLASH_TEXT_SECONDARY,
        )
        loading_wrapper.add_widget(self._loading_indicator)

        stack.add_widget(brand_label)
        stack.add_widget(accent_wrapper)
        stack.add_widget(subtitle_label)
        stack.add_widget(Widget(size_hint=(1, None), height=Theme.dimensions.SPACE_LG))
        stack.add_widget(loading_wrapper)

        anchor = AnchorLayout(anchor_x="center", anchor_y="center")
        anchor.add_widget(stack)
        self.add_widget(anchor)

    def on_enter(self, *args):
        """Start the boot sequence once this screen actually becomes visible."""
        if self._startup_triggered:
            return
        self._startup_triggered = True
        StartupService.run_startup(on_complete=self._handle_boot_complete)

    def _handle_boot_complete(self) -> None:
        self._loading_indicator.stop()
        if self._on_complete:
            self._on_complete()
