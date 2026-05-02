from __future__ import annotations
from typing import List, Callable, Optional
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from .console_theme import DEFAULT_COLORS, FONT_FAMILY, FONT_SIZE_PT

class AutocompletePopup(QListWidget):
    """Floating autocomplete dropdown attached to the input widget."""
    item_chosen = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        c = DEFAULT_COLORS
        self.setStyleSheet(
            f"QListWidget{{background:{c.autocomplete_bg};color:{c.autocomplete_text};"
            f"border:1px solid {c.border};padding:2px;}}"
            f"QListWidget::item:selected{{background:{c.autocomplete_selected};color:{c.fg};}}"
            f"QListWidget::item{{padding:2px 6px;}}"
        )
        families = [f.strip().strip("'") for f in FONT_FAMILY.split(",")]
        font = QFont(families[0], FONT_SIZE_PT - 1)
        font.setFixedPitch(True)
        self.setFont(font)
        self.itemActivated.connect(self._on_activate)
        self._prefix: str = ""

    def show_completions(self, completions: List[str], prefix: str) -> None:
        self.clear()
        self._prefix = prefix
        for c in completions:
            self.addItem(QListWidgetItem(c))
        if self.count():
            self.setCurrentRow(0)
            h = min(self.count(), 10) * (self.fontMetrics().height() + 6) + 8
            self.setFixedHeight(h)
            self.setFixedWidth(max(160, max(len(c) for c in completions) * 9 + 20))
            self.show()
        else:
            self.hide()

    def _on_activate(self, item: QListWidgetItem) -> None:
        self.item_chosen.emit(item.text())
        self.hide()

    def select_next(self) -> None:
        r = self.currentRow()
        if r < self.count() - 1:
            self.setCurrentRow(r + 1)
    def select_prev(self) -> None:
        r = self.currentRow()
        if r > 0:
            self.setCurrentRow(r - 1)
    def current_text(self) -> Optional[str]:
        item = self.currentItem()
        return item.text() if item else None
    def accept_current(self) -> Optional[str]:
        text = self.current_text()
        if text:
            self.hide()
        return text