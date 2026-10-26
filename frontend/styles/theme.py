"""
theme.py

Single entry point for the Business OS / SKURGE design system, and
the ONE source of truth for the current theme mode (dark/light).

Everything elsewhere in the app keeps accessing colors exactly as
before:

    Theme.colors.PRIMARY
    Theme.colors.BACKGROUND

This now resolves DYNAMICALLY to whichever palette (DarkColors or
LightColors) is currently active. No component needs an
`if dark_mode: ... else: ...` check — that logic lives here, once.

To change the theme:
    Theme.manager.set_mode("light")
    Theme.manager.toggle()

app.py is the one place that reacts to a mode change (it rebuilds the
main application shell so every widget is freshly constructed against
the new palette). Anything else that needed to react could do:
    Theme.manager.bind(mode=my_callback)
"""

from kivy.event import EventDispatcher
from kivy.properties import StringProperty

from styles.colors import DarkColors, LightColors
from styles.dimensions import Dimensions
from styles.typography import Typography

DARK = "dark"
LIGHT = "light"
DEFAULT_MODE = DARK  # Preserves the original SKURGE identity on first launch.


class ThemeManager(EventDispatcher):
    """Holds the current theme mode. The ONE source of truth for it."""

    mode = StringProperty(DEFAULT_MODE)

    def set_mode(self, mode: str) -> None:
        if mode not in (DARK, LIGHT):
            raise ValueError(f"Unknown theme mode: {mode!r}")
        self.mode = mode

    def toggle(self) -> None:
        self.set_mode(LIGHT if self.mode == DARK else DARK)

    @property
    def is_dark(self) -> bool:
        return self.mode == DARK


theme_manager = ThemeManager()


class _ColorProxy:
    """Resolves Theme.colors.X against the CURRENTLY active palette, on every access."""

    def __getattr__(self, name):
        palette = DarkColors if theme_manager.mode == DARK else LightColors
        return getattr(palette, name)


class Theme:
    """Bundles the full Business OS / SKURGE design system into one object."""

    colors = _ColorProxy()
    typography = Typography
    dimensions = Dimensions
    manager = theme_manager