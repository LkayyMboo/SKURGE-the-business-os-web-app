"""
typography.py

Central font-size scale for Business OS.

We are not loading custom font files yet (that comes later if needed).
For now this defines a consistent SIZE SCALE so every screen uses the
same handful of text sizes instead of random numbers everywhere.
"""


class Typography:
    """Business OS typography scale (font sizes in sp)."""

    # --- Font sizes ---
    SIZE_XS = 12
    SIZE_SM = 14
    SIZE_BASE = 16
    SIZE_LG = 18
    SIZE_XL = 22
    SIZE_XXL = 28

    # --- Semantic aliases (use these in real components) ---
    BODY = SIZE_BASE
    LABEL = SIZE_SM
    CAPTION = SIZE_XS
    HEADING = SIZE_XL
    TITLE = SIZE_XXL

    # --- Font name ---
    # "Roboto" is Kivy's built-in default font — no custom font file
    # needed yet. We reference it by name here so that if we add a
    # custom font later, we change ONE line instead of every widget.
    FONT_DEFAULT = "Roboto"