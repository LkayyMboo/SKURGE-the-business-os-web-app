"""
branding.py

Central Business OS product identity.

SKURGE is the official VISIBLE product name; "THE BUSINESS OS" is its
subtitle. Internal code (BusinessOSApp, the business-os/ folder,
module names) keeps using "Business OS" per project convention — this
file exists so the user-facing name lives in exactly ONE place instead
of being retyped in topbar.py, app.py, dashboard screens, etc.

SKURGE will eventually be the AI agent layered on top of Business OS
services (see services/dashboard_service.py's docstring for how that
layering is meant to work). No AI logic exists yet — this file is
branding only.
"""


class Branding:
    """Official Business OS visible product identity."""

    APP_NAME = "SKURGE"
    APP_SUBTITLE = "THE BUSINESS OS"