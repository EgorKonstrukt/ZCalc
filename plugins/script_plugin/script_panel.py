from __future__ import annotations
from typing import List, TYPE_CHECKING

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QGroupBox, QScrollArea,
)
from PyQt5.QtCore import pyqtSignal, Qt

if TYPE_CHECKING:
    from core import AppContext

from .script_row import ScriptRow
from .script_history import AddScriptCmd, RemoveScriptCmd

_GROUP_STYLE = (
    "QGroupBox{font-size:11px;font-weight:bold;color:#1a6b1a;"
    "border:1px solid #88cc88;border-radius:6px;margin-top:8px;"
    "padding:8px 4px 4px 4px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:8px;padding:0 4px;}"
)
_ADD_BTN_STYLE = (
    "QPushButton{background:#27ae60;color:white;border:none;border-radius:4px;"
    "font-size:11px;padding:4px 12px;font-weight:bold;}"
    "QPushButton:hover{background:#219a52;}"
)


class ScriptPanel(QGroupBox):
    """
    Sidebar panel that hosts all ScriptRow items.

    Delegates undo/redo to the AppContext History and exposes
    to_state / apply_state for .zcalc session serialisation.
    """
    state_changed = pyqtSignal()

    def __init__(self, context: "AppContext", parent=None):
        super().__init__("Scripts", parent)
        self.setStyleSheet(_GROUP_STYLE)
        self._ctx = context
        self._script_rows: List[ScriptRow] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 16, 4, 4)
        outer.setSpacing(4)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("+ New Script")
        add_btn.setStyleSheet(_ADD_BTN_STYLE)
        add_btn.setFixedHeight(26)
        add_btn.clicked.connect(self._on_add)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        outer.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        self._container = QWidget()
        self._vlay = QVBoxLayout(self._container)
        self._vlay.setContentsMargins(0, 0, 0, 0)
        self._vlay.setSpacing(4)
        self._vlay.addStretch()
        scroll.setWidget(self._container)
        outer.addWidget(scroll)

    def _on_add(self):
        state = {
            "type": "script",
            "plugin_id": "zcalc.script",
            "script_path": "",
            "running": False,
        }
        self._ctx.history.push(AddScriptCmd(self, state))
        self.state_changed.emit()

    def add_script_from_state(self, state: dict) -> ScriptRow:
        """Create a ScriptRow from state dict, wire signals, insert into layout."""
        path = state.get("script_path") or None
        row = ScriptRow(self._ctx, script_path=path, parent=self._container)
        row.removed.connect(self._on_row_removed)
        row.changed.connect(self.state_changed.emit)
        self._script_rows.append(row)
        self._vlay.insertWidget(self._vlay.count() - 1, row)
        return row

    def _on_row_removed(self, row: ScriptRow):
        self._ctx.history.push(RemoveScriptCmd(self, row))
        self.state_changed.emit()

    def _remove_script(self, row: ScriptRow, record: bool = True):
        """Stop and destroy a ScriptRow."""
        if row not in self._script_rows:
            return
        row._on_stop()
        self._script_rows.remove(row)
        lay = self._container.layout()
        if lay:
            lay.removeWidget(row)
        row.deleteLater()
        self.state_changed.emit()

    def to_state(self) -> list:
        """Serialise all rows to a list of dicts for session save."""
        return [r.to_state() for r in self._script_rows]

    def apply_state(self, states: list):
        """Restore all rows from a list of dicts."""
        for row in list(self._script_rows):
            self._remove_script(row, record=False)
        for state in states:
            row = self.add_script_from_state(state)
            row.apply_state(state)
