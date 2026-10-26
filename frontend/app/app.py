"""
app.py

The root Kivy Application class for Business OS (SKURGE).

Owns the full startup flow:

    Splash -> Welcome -> Login/Register -> Business Setup -> Main App

Each onboarding screen only reports what happened via a callback
(e.g. on_login_success(user)) — it never decides what screen comes
next. This file owns all routing decisions, and app.session.app_session
holds the user/business so the rest of the app (e.g. DashboardScreen)
can read them without this file passing them around by hand.

Phase 9: app_session.current_business is now bound the same way
Theme.manager.mode already was — switching the active business (e.g.
from Settings) rebuilds MainLayout so DashboardScreen re-reads the
newly active business, without restarting the app.

Phase 10: app_session.data_version is bound the same way — recording
a transaction on the Finance screen bumps it, which refreshes
DashboardScreen's totals without a restart. See session.py's
docstring for why this reuses the rebuild pattern instead of a new
cross-screen messaging system.
"""

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen, ScreenManager, FadeTransition

from app.config import AppConfig
from app.session import app_session
from layouts.main_layout import MainLayout
from screens.business.business_registration import BusinessSetupScreen
from screens.onboarding.login_screen import LoginScreen
from screens.onboarding.register_screen import RegisterScreen
from screens.onboarding.welcome_screen import WelcomeScreen
from screens.splash.splash_screen import SplashScreen
from services.business_service import BusinessService
from styles.theme import Theme

SPLASH_SCREEN_NAME = "splash"
WELCOME_SCREEN_NAME = "welcome"
LOGIN_SCREEN_NAME = "login"
REGISTER_SCREEN_NAME = "register"
BUSINESS_SETUP_SCREEN_NAME = "business_setup"
MAIN_SCREEN_NAME = "main"
F12_KEY_CODE = 293  # DEV ONLY


class BusinessOSApp(App):
    """The main Business OS (SKURGE) Kivy application."""

    def build(self):
        self.title = AppConfig.APP_TITLE
        Window.size = (AppConfig.WINDOW_WIDTH, AppConfig.WINDOW_HEIGHT)
        Window.minimum_width = AppConfig.WINDOW_MIN_WIDTH
        Window.minimum_height = AppConfig.WINDOW_MIN_HEIGHT
        Window.clearcolor = Theme.colors.BACKGROUND

        self.root_manager = ScreenManager(transition=FadeTransition(duration=0.4))

        self.root_manager.add_widget(
            SplashScreen(name=SPLASH_SCREEN_NAME, on_complete=self._show_welcome)
        )
        self.root_manager.add_widget(
            WelcomeScreen(
                name=WELCOME_SCREEN_NAME,
                on_sign_in=self._show_login,
                on_create_account=self._show_register,
            )
        )
        self.root_manager.add_widget(
            LoginScreen(
                name=LOGIN_SCREEN_NAME,
                on_login_success=self._handle_authenticated,
                on_switch_to_register=self._show_register,
                on_back=self._show_welcome,
            )
        )
        self.root_manager.add_widget(
            RegisterScreen(
                name=REGISTER_SCREEN_NAME,
                on_register_success=self._handle_authenticated,
                on_switch_to_login=self._show_login,
                on_back=self._show_welcome,
            )
        )
        self.business_setup_screen = BusinessSetupScreen(
            name=BUSINESS_SETUP_SCREEN_NAME, on_complete=self._handle_business_created
        )
        self.root_manager.add_widget(self.business_setup_screen)

        self.main_screen = Screen(name=MAIN_SCREEN_NAME)
        self.main_layout = None
        self._build_main_layout()
        self.root_manager.add_widget(self.main_screen)

        Theme.manager.bind(mode=self._on_theme_changed)
        app_session.bind(current_business=self._on_business_changed)
        app_session.bind(data_version=self._on_data_changed)
        Window.bind(on_key_down=self._on_key_down)  # DEV ONLY (F12)

        self.root_manager.current = SPLASH_SCREEN_NAME
        return self.root_manager

    # --- Onboarding routing ---

    def _show_welcome(self, *_args) -> None:
        self.root_manager.current = WELCOME_SCREEN_NAME

    def _show_login(self, *_args) -> None:
        self.root_manager.current = LOGIN_SCREEN_NAME

    def _show_register(self, *_args) -> None:
        self.root_manager.current = REGISTER_SCREEN_NAME

    def _handle_authenticated(self, user) -> None:
        """Called after a successful login OR registration."""
        app_session.set_user(user)
        existing_business = BusinessService.get_business_for_user(user.id)
        if existing_business:
            app_session.set_business(existing_business)
            self._show_main_app()
        else:
            self.business_setup_screen.set_current_user(user)
            self.root_manager.current = BUSINESS_SETUP_SCREEN_NAME

    def _handle_business_created(self, business) -> None:
        app_session.set_business(business)
        self._show_main_app()

    # --- Main app / theme / business switch / dev showcase ---

    def _build_main_layout(self, initial_section: str = None) -> None:
        self.main_screen.clear_widgets()
        self.main_layout = MainLayout(initial_section=initial_section)
        self.main_screen.add_widget(self.main_layout)

    def _current_main_section(self):
        return self.main_layout.navigation_manager.current_section if self.main_layout else None

    def _on_theme_changed(self, _instance, _mode) -> None:
        current_section = self._current_main_section()
        Window.clearcolor = Theme.colors.BACKGROUND
        self._build_main_layout(initial_section=current_section)

    def _on_business_changed(self, _instance, _business) -> None:
        """Rebuilds the shell so DashboardScreen re-reads the newly
        active business — same mechanism as the theme-change rebuild.

        No "are we on the main screen yet" guard here: Kivy properties
        fire this callback THE INSTANT set_business() runs, which in
        _handle_authenticated happens BEFORE root_manager.current is
        switched to "main". A guard checking root_manager.current would
        (and did) skip the one rebuild that actually matters — the
        first one, right after login — leaving Dashboard/Settings
        permanently showing stale data from before the user signed in.
        Rebuilding while a non-main screen is visible is harmless: it's
        not on screen, so there's nothing to flicker."""
        current_section = self._current_main_section()
        self._build_main_layout(initial_section=current_section)

    def _on_data_changed(self, _instance, _version) -> None:
        """Called when any screen reports its data changed (e.g.
        Finance recording a transaction) — refreshes sibling screens
        like Dashboard that have no other way to know."""
        current_section = self._current_main_section()
        self._build_main_layout(initial_section=current_section)

    def _on_key_down(self, _window, key, *_args):  # DEV ONLY
        if (
            key == F12_KEY_CODE
            and self.main_layout
            and self.root_manager.current == MAIN_SCREEN_NAME
        ):
            self.main_layout.toggle_showcase()

    def _show_main_app(self) -> None:
        self.root_manager.current = MAIN_SCREEN_NAME
