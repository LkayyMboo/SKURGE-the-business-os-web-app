"""
loading_indicator.py

Reusable loading indicator — a pulsing label. Purely visual; not
wired to any real asynchronous operation yet.

text_color defaults to the current theme's secondary text color, so
it looks correct in either Dark or Light mode automatically. Pass an
explicit text_color for a context that must NOT follow the app's
theme (currently only the SKURGE splash screen, which stays dark
regardless of the selected Dark/Light setting).
"""

from kivy.animation import Animation
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from styles.theme import Theme


class LoadingIndicator(BoxLayout):
    """A simple pulsing loading indicator."""

    def __init__(self, text: str = "Loading...", text_color: tuple = None, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (200, 40))
        super().__init__(**kwargs)

        color = text_color if text_color is not None else Theme.colors.TEXT_SECONDARY
        self._label = Label(text=text, color=color, font_size=Theme.typography.BODY)
        self.add_widget(self._label)

        self._animation = Animation(opacity=0.3, duration=0.6) + Animation(opacity=1.0, duration=0.6)
        self._animation.repeat = True
        self._animation.start(self._label)

    def stop(self) -> None:
        """Stop the pulsing animation (call when the real operation finishes)."""
        Animation.cancel_all(self._label)
        self._label.opacity = 1.0