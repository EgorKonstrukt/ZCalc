from __future__ import annotations
from typing import Callable, Optional
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from .themes import ThemeDef, THEMES

_PALETTE_BUILDERS: dict[str, Callable[[], QPalette]] = {}

def _build_light() -> QPalette:
    return QApplication.style().standardPalette()

def _build_dark() -> QPalette:
    p = QPalette()
    c = {
        QPalette.Window:          QColor("#2b2b2b"),
        QPalette.WindowText:      QColor("#bbbbbb"),
        QPalette.Base:            QColor("#45494a"),
        QPalette.AlternateBase:   QColor("#3c3f41"),
        QPalette.ToolTipBase:     QColor("#3c3f41"),
        QPalette.ToolTipText:     QColor("#bbbbbb"),
        QPalette.Text:            QColor("#bbbbbb"),
        QPalette.Button:          QColor("#4c5052"),
        QPalette.ButtonText:      QColor("#bbbbbb"),
        QPalette.BrightText:      QColor("#ffffff"),
        QPalette.Highlight:       QColor("#4b6eaf"),
        QPalette.HighlightedText: QColor("#ffffff"),
        QPalette.Link:            QColor("#589df6"),
        QPalette.Disabled + QPalette.Text:       QColor("#777777"),
        QPalette.Disabled + QPalette.ButtonText: QColor("#777777"),
        QPalette.Disabled + QPalette.WindowText: QColor("#777777"),
    }
    for role, color in c.items():
        p.setColor(role, color)
    return p

def _build_high_contrast() -> QPalette:
    p = QPalette()
    c = {
        QPalette.Window:          QColor("#000000"),
        QPalette.WindowText:      QColor("#ffffff"),
        QPalette.Base:            QColor("#0d0d0d"),
        QPalette.AlternateBase:   QColor("#1a1a1a"),
        QPalette.ToolTipBase:     QColor("#1a1a1a"),
        QPalette.ToolTipText:     QColor("#ffffff"),
        QPalette.Text:            QColor("#ffffff"),
        QPalette.Button:          QColor("#1a1a1a"),
        QPalette.ButtonText:      QColor("#ffffff"),
        QPalette.BrightText:      QColor("#ff8c00"),
        QPalette.Highlight:       QColor("#ff8c00"),
        QPalette.HighlightedText: QColor("#000000"),
        QPalette.Link:            QColor("#ff8c00"),
        QPalette.Disabled + QPalette.Text:       QColor("#555555"),
        QPalette.Disabled + QPalette.ButtonText: QColor("#555555"),
        QPalette.Disabled + QPalette.WindowText: QColor("#555555"),
    }
    for role, color in c.items():
        p.setColor(role, color)
    return p

_PALETTE_BUILDERS = {
    "light":         _build_light,
    "dark":          _build_dark,
    "high_contrast": _build_high_contrast,
}

class ThemeManager:
    """Applies and tracks the active visual theme for the application."""
    def __init__(self) -> None:
        self._current_id: str = "light"
    @property
    def current_id(self) -> str:
        return self._current_id
    @property
    def available(self) -> dict[str, ThemeDef]:
        return THEMES
    def apply(self, theme_id: str) -> bool:
        td = THEMES.get(theme_id)
        if td is None:
            return False
        app = QApplication.instance()
        if app is None:
            return False
        builder = _PALETTE_BUILDERS.get(td.palette_fn)
        if builder:
            app.setPalette(builder())
        app.setStyleSheet(td.stylesheet)
        self._current_id = theme_id
        return True