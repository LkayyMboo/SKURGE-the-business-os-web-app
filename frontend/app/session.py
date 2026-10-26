"""
session.py

ONE source of truth for who is signed in and which business is active
for this run — same pattern as styles/theme.py's ThemeManager.

Phase 9: current_business is still the single "active" business the
rest of the app reads (dashboard, future modules), but the session
now also knows how to switch between a user's multiple businesses via
BusinessService, persisting that choice so it survives a restart.

Still in-memory for the User object itself within a run (the identity
of "who is this AppSession for" doesn't need its own persistence —
AuthService already persists credentials; session just holds today's
logged-in user object).

Phase 10 design note — cross-screen refresh:
FinanceScreen and DashboardScreen are SIBLING screens inside the same
inner ScreenManager; they are not torn down when you navigate between
them. When FinanceScreen records a transaction, it can safely rebuild
its OWN content in place (it caused the change, it knows). But
DashboardScreen has no way to know Finance's data changed — it's a
passive bystander. Rather than invent a new publish/subscribe system,
`data_version` reuses the SAME pattern already proven for theme and
business-switch changes: bump a Kivy property, app.py is already
listening and rebuilds the shell (keeping whatever section is open).
This is a small, deliberate reuse of an existing pattern, not a new
architectural system.
"""

from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, ObjectProperty

from services.business_service import BusinessService


class AppSession(EventDispatcher):
    """Holds the current user and current business for this app run."""

    current_user = ObjectProperty(None, allownone=True)
    current_business = ObjectProperty(None, allownone=True)
    data_version = NumericProperty(0)

    def set_user(self, user) -> None:
        self.current_user = user

    def set_business(self, business) -> None:
        self.current_business = business

    def switch_business(self, business_id: str) -> None:
        """Switch the active business for the current user and persist the choice."""
        if self.current_user is None:
            raise ValueError("No user is signed in.")
        business = BusinessService.set_active_business(self.current_user.id, business_id)
        self.current_business = business

    def get_user_businesses(self):
        """All businesses owned by the current user, or an empty list if none/no user."""
        if self.current_user is None:
            return []
        return BusinessService.get_businesses_for_user(self.current_user.id)

    def require_business(self):
        """
        Return the current business, or raise if none is set.

        Future screens that need a business (Employees, Finance, etc.)
        call this instead of checking `current_business is None`
        themselves everywhere — one clear failure point instead of
        scattered None-checks.
        """
        if self.current_business is None:
            raise ValueError("No business is active for this session.")
        return self.current_business

    def notify_data_changed(self) -> None:
        """
        Call this after any operation that changes data another screen
        might be displaying (e.g. recording a transaction). Bumps
        data_version, which app.py listens for to refresh the shell —
        see the module docstring above for why this mechanism was chosen.
        """
        self.data_version += 1

    def clear(self) -> None:
        self.current_user = None
        self.current_business = None


app_session = AppSession()
