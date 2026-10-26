"""
dimensions.py

Central spacing and sizing scale for Business OS.

Using a fixed scale (instead of random pixel values) keeps padding,
margins, and component sizes visually consistent across every screen.
"""


class Dimensions:
    """Business OS spacing and sizing scale (in dp)."""

    # --- Spacing scale ---
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 16
    SPACE_LG = 24
    SPACE_XL = 32
        # --- Semantic spacing aliases (use these in screens/forms) ---
    FIELD_SPACING = SPACE_MD      # Between stacked form fields
    SECTION_SPACING = SPACE_LG    # Between a heading and its content, or between sections
    SCREEN_PADDING = SPACE_LG     # Outer padding around full-screen content
    CARD_PADDING = SPACE_MD       # Inner padding inside Card/StatCard

    # --- Layout structure sizes ---
    SIDEBAR_WIDTH = 220
    TOPBAR_HEIGHT = 56

    # --- Component sizes ---
    BUTTON_HEIGHT = 44
    INPUT_HEIGHT = 44
    ICON_SIZE = 24

    # --- Border radius (for future rounded-corner widgets) ---
    RADIUS_SM = 4
    RADIUS_MD = 8
    RADIUS_LG = 16