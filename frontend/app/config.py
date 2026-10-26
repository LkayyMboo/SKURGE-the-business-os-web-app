"""
config.py

Application-wide configuration for Business OS.

This file holds non-visual application settings — window title and
default window size. Visual/design values (colors, fonts, spacing)
belong in styles/. The visible product NAME comes from
app.branding.Branding, not from a string hardcoded here.
"""

from app.branding import Branding


class AppConfig:
    """Core Business OS application configuration."""

    APP_NAME = Branding.APP_NAME
    APP_TITLE = f"{Branding.APP_NAME} — {Branding.APP_SUBTITLE}"

    WINDOW_WIDTH = 1280
    WINDOW_HEIGHT = 800
    WINDOW_MIN_WIDTH = 1024
    WINDOW_MIN_HEIGHT = 640