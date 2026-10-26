#!/usr/bin/env bash
set -e
cd ~/business-os

mkdir -p frontend/layouts frontend/screens/splash frontend/services

cat > frontend/services/startup_service.py << 'PYEOF_FILE'
"""
startup_service.py

Coordinates SKURGE's startup/boot sequence.

Currently performs only a short, fixed delay to establish the SKURGE
product identity before the main application appears. No real
initialization work exists yet.

DEFAULT_BOOT_DURATION_SECONDS is the ONE place this duration is
configured — do not hardcode a startup delay anywhere else.
"""

from kivy.clock import Clock

DEFAULT_BOOT_DURATION_SECONDS = 4.0


class StartupService:
    """Runs SKURGE's startup sequence and reports completion."""

    @staticmethod
    def run_startup(on_complete, duration: float = DEFAULT_BOOT_DURATION_SECONDS) -> None:
        Clock.schedule_once(lambda _dt: on_complete(), duration)
PYEOF_FILE

cat > frontend/screens/splash/splash_screen.py << 'PYEOF_FILE'
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
            spacing=Theme.dimensions.SPACE_SM,
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
PYEOF_FILE

cat > frontend/layouts/sidebar.py << 'PYEOF_FILE'
"""
sidebar.py

The Business OS desktop sidebar.

Builds one SidebarButton per entry in app.navigation.SECTIONS. Each
button only knows its own section key — pressing it asks the
NavigationManager to navigate, and stops caring what happens next.

initial_section lets MainLayout tell the sidebar which item should
start highlighted — used when the app rebuilds the shell after a
theme or active-business change, so the user's current section stays
highlighted correctly instead of always resetting to Dashboard.

The active item is shown with a subtle elevated background plus a
thin gold accent bar on its left edge, rather than a solid block of
color, per the SKURGE visual identity (Step 7).
"""

from kivy.graphics import Color, Rectangle
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.navigation import SECTIONS, DEFAULT_SECTION
from components.base.background_mixin import BackgroundColorMixin
from styles.theme import Theme


class SidebarButton(ButtonBehavior, BackgroundColorMixin, Label):
    """A single clickable, highlightable sidebar entry."""

    def __init__(self, text: str, **kwargs):
        super().__init__(text=text, **kwargs)
        self.color = Theme.colors.SIDEBAR_TEXT
        self.font_size = Theme.typography.BODY
        self.size_hint_y = None
        self.height = Theme.dimensions.BUTTON_HEIGHT
        self.halign = "left"
        self.valign = "middle"
        self.padding = (Theme.dimensions.SPACE_MD, 0)
        self.set_background_color(Theme.colors.SIDEBAR_BACKGROUND)

        with self.canvas.before:
            self._accent_color = Color(*Theme.colors.SIDEBAR_ITEM_ACCENT)
            self._accent_color.a = 0
            self._accent_rect = Rectangle(pos=self.pos, size=(3, self.height))

        self.bind(size=self._on_layout_change, pos=self._on_layout_change)

    def _on_layout_change(self, *_args) -> None:
        self.text_size = self.size
        self._accent_rect.pos = self.pos
        self._accent_rect.size = (3, self.height)

    def set_active(self, is_active: bool) -> None:
        if is_active:
            self._bg_color_instruction.rgba = Theme.colors.SIDEBAR_ITEM_ACTIVE
            self.color = Theme.colors.SIDEBAR_TEXT_ACTIVE
            self.bold = True
            self._accent_color.a = 1
        else:
            self._bg_color_instruction.rgba = Theme.colors.SIDEBAR_BACKGROUND
            self.color = Theme.colors.SIDEBAR_TEXT
            self.bold = False
            self._accent_color.a = 0


class Sidebar(BackgroundColorMixin, BoxLayout):
    """Fixed-width vertical navigation panel."""

    def __init__(self, navigation_manager, initial_section: str = DEFAULT_SECTION, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(None, 1),
            width=Theme.dimensions.SIDEBAR_WIDTH,
            padding=(0, Theme.dimensions.SPACE_SM),
            **kwargs,
        )
        self.navigation_manager = navigation_manager
        self.set_background_color(Theme.colors.SIDEBAR_BACKGROUND)

        self._buttons: dict[str, SidebarButton] = {}
        for key, label in SECTIONS:
            button = SidebarButton(text=label)
            button.bind(on_release=lambda _instance, k=key: self._on_item_pressed(k))
            self._buttons[key] = button
            self.add_widget(button)

        self._set_active_button(initial_section)

    def _on_item_pressed(self, key: str) -> None:
        self.navigation_manager.navigate_to(key)
        self._set_active_button(key)

    def _set_active_button(self, key: str) -> None:
        for button_key, button in self._buttons.items():
            button.set_active(button_key == key)
PYEOF_FILE

cat > frontend/layouts/main_layout.py << 'PYEOF_FILE'
"""
main_layout.py

Assembles the full Business OS application shell:

    ┌───────────────────────────────┐
    │            TopBar             │
    ├───────────┬────────────────────┤
    │  Sidebar  │   ScreenManager    │
    │           │  (active section)  │
    └───────────┴────────────────────┘

Rebuilt from scratch by app.py whenever the theme mode OR the active
business changes (see app.py's _on_theme_changed / _on_business_changed),
so every widget here always reads the CURRENTLY active palette/business.
initial_section lets app.py restore whichever section the user was
viewing before that rebuild.

IMPORTANT: this inner ScreenManager uses NoTransition. A ScreenManager
always auto-selects its FIRST added screen as `.current` — here,
Dashboard is added before other sections, so the instant this
ScreenManager is built, `.current` silently becomes "dashboard". Then,
at the end of __init__, navigate_to(start_section) changes `.current`
a SECOND time to whatever section the user actually had open (e.g.
"settings"). With the default SlideTransition, that second change
animates visibly — this is exactly what caused the "theme switch
flashes Dashboard, then slides back to Settings" bug. NoTransition
makes that second change instant, so there is nothing to see.

The F12 key binding lives in app.py, NOT here — MainLayout only
exposes toggle_showcase(). Binding Window.on_key_down inside this
class would stack a NEW duplicate handler on the global Window every
single time MainLayout is rebuilt (every theme change, every business
switch) — old handlers are never removed, so pressing F12 would fire
all of them at once.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, NoTransition

from app.navigation import SECTIONS, DEFAULT_SECTION, NavigationManager
from components.base.background_mixin import BackgroundColorMixin
from layouts.sidebar import Sidebar
from layouts.topbar import TopBar
from screens.dashboard.dashboard_screen import DashboardScreen
from screens.dev.component_showcase_screen import ComponentShowcaseScreen  # DEV ONLY
from screens.placeholder.placeholder_screen import PlaceholderScreen
from screens.settings.settings_screen import SettingsScreen
from styles.theme import Theme

DEV_SHOWCASE_SCREEN_NAME = "dev_showcase"  # DEV ONLY


class MainLayout(BackgroundColorMixin, BoxLayout):
    """The root shell widget for the entire Business OS application."""

    def __init__(self, initial_section: str = None, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.set_background_color(Theme.colors.BACKGROUND)

        start_section = initial_section or DEFAULT_SECTION

        # 1. Build the content area. "dashboard" and "settings" get real
        #    screens; every other section still gets a placeholder.
        # NoTransition: see the module docstring above for why this
        # matters — it is the fix for the theme/business-switch glitch.
        self.screen_manager = ScreenManager(transition=NoTransition())
        for key, label in SECTIONS:
            if key == "dashboard":
                self.screen_manager.add_widget(DashboardScreen(name=key))
            elif key == "settings":
                self.screen_manager.add_widget(SettingsScreen(name=key))
            else:
                self.screen_manager.add_widget(PlaceholderScreen(section_title=label, name=key))

        # DEV ONLY — register the component showcase screen (not a real section).
        self.screen_manager.add_widget(ComponentShowcaseScreen(name=DEV_SHOWCASE_SCREEN_NAME))
        self._pre_showcase_section = None

        # 2. Build the topbar and wire up centralized navigation.
        self.topbar = TopBar()
        self.navigation_manager = NavigationManager(self.screen_manager, self.topbar)

        # 3. Build the sidebar, restoring whichever section was active.
        self.sidebar = Sidebar(navigation_manager=self.navigation_manager, initial_section=start_section)

        # 4. Assemble: topbar on top, sidebar + content area below it.
        body = BoxLayout(orientation="horizontal")
        body.add_widget(self.sidebar)
        body.add_widget(self.screen_manager)

        self.add_widget(self.topbar)
        self.add_widget(body)

        # 5. Show the correct starting section.
        self.navigation_manager.navigate_to(start_section)

    def toggle_showcase(self) -> None:  # DEV ONLY
        """Toggle the F12 component showcase screen. Called by app.py's key handler."""
        if self.screen_manager.current == DEV_SHOWCASE_SCREEN_NAME:
            self.navigation_manager._current_section = None  # force topbar/title refresh
            self.navigation_manager.navigate_to(self._pre_showcase_section or DEFAULT_SECTION)
        else:
            self._pre_showcase_section = self.navigation_manager.current_section
            self.screen_manager.current = DEV_SHOWCASE_SCREEN_NAME
            self.topbar.update_title("Component Showcase (Dev)")
PYEOF_FILE

echo "Splash/theme/F12 fix files created."