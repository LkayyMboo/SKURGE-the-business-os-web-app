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
from screens.employees.employees_screen import EmployeesScreen
from screens.finance.finance_screen import FinanceScreen
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

        # 1. Build the content area. "dashboard", "settings",
        #    "finance", and "employees" get real screens; every other
        #    section still gets a placeholder.
        # NoTransition: see the module docstring above for why this
        # matters — it is the fix for the theme/business-switch glitch.
        self.screen_manager = ScreenManager(transition=NoTransition())
        for key, label in SECTIONS:
            if key == "dashboard":
                self.screen_manager.add_widget(DashboardScreen(name=key))
            elif key == "settings":
                self.screen_manager.add_widget(SettingsScreen(name=key))
            elif key == "finance":
                self.screen_manager.add_widget(FinanceScreen(name=key))
            elif key == "employees":
                self.screen_manager.add_widget(EmployeesScreen(name=key))
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
