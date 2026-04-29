from __future__ import annotations
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QGroupBox,
)
from core.plugins.settings_page import SettingsPage
from .theme_manager import ThemeManager
if TYPE_CHECKING:
    from core import AppContext

_GROUP_STYLE = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#555;"
    "border:1px solid #ddd;border-radius:6px;margin-top:8px;"
    "padding:8px 6px 6px 6px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}"
)

class ThemeSettingsPage(SettingsPage):
    """Settings tab for theme selection."""
    tab_label = "Theme"
    def __init__(self, manager: ThemeManager) -> None:
        self._manager = manager
        self._ctx: "AppContext" = None
        self._btns: dict[str, QPushButton] = {}
        self._pending_id: str = manager.current_id
    def create_widget(self, context: "AppContext") -> QWidget:
        self._ctx = context
        w = QWidget()
        root = QVBoxLayout(w)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(10)
        grp = QGroupBox("Application Theme")
        grp.setStyleSheet(_GROUP_STYLE)
        gl = QVBoxLayout(grp)
        gl.setSpacing(6)
        hint = QLabel("Choose a visual theme. Changes apply immediately on Apply.")
        hint.setStyleSheet("QLabel{font-size:11px;color:#888;}")
        hint.setWordWrap(True)
        gl.addWidget(hint)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        grp_btns = QButtonGroup(w)
        grp_btns.setExclusive(True)
        for tid, td in self._manager.available.items():
            btn = QPushButton(td.name)
            btn.setCheckable(True)
            btn.setMinimumWidth(130)
            btn.clicked.connect(lambda checked, _id=tid: self._on_select(_id))
            grp_btns.addButton(btn)
            btn_row.addWidget(btn)
            self._btns[tid] = btn
        btn_row.addStretch()
        gl.addLayout(btn_row)
        root.addWidget(grp)
        root.addStretch()
        return w
    def load(self) -> None:
        self._pending_id = self._manager.current_id
        self._sync_buttons()
    def apply(self) -> None:
        self._manager.apply(self._pending_id)
        if self._ctx:
            self._ctx.config.set("theme_id", self._pending_id)
            self._ctx.config.save()
    def reset(self) -> None:
        self._pending_id = "light"
        self._sync_buttons()
    def _on_select(self, theme_id: str) -> None:
        self._pending_id = theme_id
        self._sync_buttons()
    def _sync_buttons(self) -> None:
        for tid, btn in self._btns.items():
            btn.setChecked(tid == self._pending_id)