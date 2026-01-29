# fonts.py
from __future__ import annotations
from PySide6.QtGui import QFontDatabase, QFont
from pathlib import Path
from typing import Optional

_font_id: int = -1  # unloaded state
_main_family: Optional[str] = None


def _load_fonts():
    """Called to load the .ttf files at launch only."""
    global _font_id, _main_family

    # return if already loaded
    if _font_id != -1:
        return

    font_path = (
        Path(__file__).parent.parent / "resources/Nunito/static/Nunito-Regular.ttf"
    )
    if not font_path.is_file():
        raise FileNotFoundError(f"Main font not found at {font_path}.")

    _font_id = QFontDatabase.addApplicationFont(str(font_path))
    if _font_id == -1:
        raise RuntimeError("Failed to load fonts via QFontDatabase.")

    _main_family = QFontDatabase.applicationFontFamilies(_font_id)[0]


def _reset_for_tests() -> None:
    """Private helper to clear the module‑level cache, only for testing."""
    global _font_id, _roboto_family
    _font_id = -1
    _roboto_family = None


def get_main_font(
    point_size: int = 11, weight: int = QFont.Normal, italic: bool = False
) -> QFont:
    """Returns a QFont instance configured as the main font."""
    _load_fonts()
    return QFont(_main_family, point_size, weight, italic)


def get_family_name() -> str:
    """Family font getter to retrieve the family for stylesheets."""
    _load_fonts()
    return str(_main_family)
