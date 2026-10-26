"""
mobile_navigation.py

FOUNDATION STUB — not yet active.

This will eventually hold a bottom-navigation-bar widget shown
instead of the desktop Sidebar when the window drops below a defined
width breakpoint. That responsive breakpoint logic (deciding WHEN to
swap Sidebar for MobileNavigation) is deferred to a later phase.

app.py does not import or use this yet. It exists now only so the
target architecture's file exists and the intent is documented.
"""

from kivy.uix.boxlayout import BoxLayout

from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class MobileNavigation(BackgroundColorMixin, BoxLayout):
    """Placeholder for a future mobile bottom-navigation bar. Currently unused."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint=(1, None),
            height=Theme.dimensions.TOPBAR_HEIGHT,
            **kwargs,
        )
        self.set_background_color(Theme.colors.SURFACE)