"""
navigation.py

Centralized navigation for Business OS.

Instead of scattering "switch to screen X" logic inside every button
or screen, ALL navigation goes through NavigationManager. This means:

- Sidebar buttons only need to know WHICH section key they represent,
  not HOW navigation works.
- When a PlaceholderScreen is later replaced with a real screen
  (e.g. in Phase 7 for Payroll), only main_layout.py changes.
  sidebar.py and this file stay the same.

SECTIONS defines every top-level section in Business OS, in the order
they appear in the sidebar. Both sidebar.py and main_layout.py import
this same list so it only ever has to be defined in one place.
"""

from __future__ import annotations

SECTIONS = [
    ("dashboard", "Dashboard"),
    ("business", "Business"),
    ("employees", "Employees"),
    ("payroll", "Payroll"),
    ("finance", "Finance"),
    ("payments", "Payments"),
    ("orders", "Orders"),
    ("inventory", "Inventory"),
    ("suppliers", "Suppliers"),
    ("customers", "Customers"),
    ("tax", "Tax"),
    ("documents", "Documents"),
    ("calendar", "Calendar"),
    ("network", "Business Network"),
    ("notifications", "Notifications"),
    ("settings", "Settings"),
]

DEFAULT_SECTION = "dashboard"


class NavigationManager:
    """
    Manages switching between Business OS sections.

    Wraps a Kivy ScreenManager and a TopBar so that navigating to a
    section does both things together: swaps the visible screen AND
    updates the topbar's section title.
    """

    def __init__(self, screen_manager, topbar) -> None:
        self.screen_manager = screen_manager
        self.topbar = topbar
        self._current_section: str | None = None

    def navigate_to(self, section_key: str) -> None:
        """Switch the main content area to the given section."""
        if section_key == self._current_section:
            return

        self.screen_manager.current = section_key
        section_label = dict(SECTIONS).get(section_key, section_key.title())
        self.topbar.update_title(section_label)
        self._current_section = section_key

    @property
    def current_section(self) -> str | None:
        return self._current_section