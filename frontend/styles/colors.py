"""
colors.py

Central color palette for Business OS / SKURGE — now with Dark and
Light modes.

_IdentityColors holds colors that must NEVER differ between modes:
purple (SKURGE/AI identity), gold (premium/actions), sage
(success/positive), and danger (destructive/error). DarkColors and
LightColors both inherit these, so they are defined ONCE and cannot
drift apart between themes.

DarkColors / LightColors then each define the mode-specific
foundation: background, surface, border, and text colors.

FixedColors holds colors that must stay constant regardless of the
selected app theme — currently only used by the SKURGE splash screen,
which is boot identity, not a themed surface.

Every color anywhere in the app is still accessed as
Theme.colors.SOMETHING (see styles/theme.py) — never as a raw RGBA
tuple in a component file.
"""


def rgba(r: int, g: int, b: int, a: float = 1.0) -> tuple:
    """Convert a 0-255 RGB color (plus optional alpha 0-1) to Kivy's 0-1 RGBA format."""
    return (r / 255, g / 255, b / 255, a)


class _IdentityColors:
    """SKURGE identity colors — identical in Dark and Light mode."""

    PURPLE = rgba(142, 110, 210)
    PURPLE_DARK = rgba(110, 84, 168)
    SKURGE_ACCENT = PURPLE  # Semantic alias for future AI features

    GOLD = rgba(199, 162, 88)
    GOLD_DARK = rgba(163, 130, 62)

    SAGE = rgba(140, 168, 136)
    SAGE_DARK = rgba(108, 133, 104)

    DANGER = rgba(173, 63, 58)
    DANGER_DARK = rgba(138, 48, 45)

    WARNING = rgba(197, 149, 68)
    INFO = PURPLE

    # Text placed ON TOP of saturated accent-colored buttons/badges.
    TEXT_ON_PRIMARY = rgba(245, 245, 247)  # On DANGER (always dark enough for white text)
    TEXT_ON_GOLD = rgba(28, 24, 16)        # On GOLD (light — needs near-black text)


class DarkColors(_IdentityColors):
    """The default SKURGE appearance: black foundation, light text."""

    BLACK = rgba(14, 14, 16)
    BLACK_SOFT = rgba(22, 22, 25)
    SURFACE = BLACK_SOFT
    SURFACE_ELEVATED = rgba(32, 32, 36)
    BACKGROUND = BLACK
    BORDER = rgba(48, 48, 54)

    TEXT_PRIMARY = rgba(236, 236, 240)
    TEXT_SECONDARY = rgba(162, 162, 172)

    PRIMARY = _IdentityColors.GOLD
    PRIMARY_DARK = _IdentityColors.GOLD_DARK
    SECONDARY = _IdentityColors.SAGE
    SUCCESS = _IdentityColors.SAGE

    SIDEBAR_BACKGROUND = rgba(10, 10, 12)
    SIDEBAR_TEXT = rgba(170, 170, 178)
    SIDEBAR_TEXT_ACTIVE = _IdentityColors.GOLD
    SIDEBAR_ITEM_ACTIVE = SURFACE_ELEVATED
    SIDEBAR_ITEM_ACCENT = _IdentityColors.GOLD


class LightColors(_IdentityColors):
    """The professional light equivalent — same identity, inverted foundation."""

    WHITE = rgba(250, 249, 246)  # Slightly warm white, not stark white
    SURFACE = rgba(255, 255, 255)
    SURFACE_ELEVATED = rgba(244, 243, 238)
    BACKGROUND = WHITE
    BORDER = rgba(222, 219, 212)

    TEXT_PRIMARY = rgba(28, 27, 25)
    TEXT_SECONDARY = rgba(103, 100, 95)

    PRIMARY = _IdentityColors.GOLD
    PRIMARY_DARK = _IdentityColors.GOLD_DARK
    SECONDARY = _IdentityColors.SAGE
    SUCCESS = _IdentityColors.SAGE

    SIDEBAR_BACKGROUND = rgba(250, 249, 246)
    SIDEBAR_TEXT = rgba(96, 93, 88)
    SIDEBAR_TEXT_ACTIVE = rgba(28, 27, 25)
    SIDEBAR_ITEM_ACTIVE = rgba(238, 235, 227)
    SIDEBAR_ITEM_ACCENT = _IdentityColors.GOLD


class FixedColors:
    """
    Colors that never change with the app's theme setting.

    Used only by the SKURGE splash screen, which is boot identity —
    not a themed application surface — per Step 7 requirements.
    """

    SPLASH_BACKGROUND = rgba(14, 14, 16)
    SPLASH_TEXT_SECONDARY = rgba(162, 162, 172)