from __future__ import annotations
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup,
)
from PyQt5.QtCore import Qt
from .theme_manager import ThemeManager

class ThemePanel(QWidget):
    """Sidebar panel for selecting the application theme."""
    def __init__(self, manager: ThemeManager, context, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._manager = manager
        self._ctx = context
        self._btns: dict[str, QPushButton] = {}
        self._build_ui()
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)
        hdr = QLabel("Theme")
        hdr.setStyleSheet("font-weight:bold;font-size:12px;")
        root.addWidget(hdr)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for tid, td in self._manager.available.items():
            btn = QPushButton(td.name)
            btn.setCheckable(True)
            btn.setChecked(tid == self._manager.current_id)
            btn.clicked.connect(lambda checked, _id=tid: self._on_select(_id))
            grp.addButton(btn)
            btn_row.addWidget(btn)
            self._btns[tid] = btn
        root.addLayout(btn_row)
        root.addStretch()
    def _on_select(self, theme_id: str) -> None:
        self._manager.apply(theme_id)
        self._ctx.config.set("theme_id", theme_id)
        self._ctx.config.save()
        for tid, btn in self._btns.items():
            btn.setChecked(tid == theme_id)