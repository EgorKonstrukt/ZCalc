from __future__ import annotations
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QSplitter,
)
from PyQt5.QtCore import Qt
from .console_output import ConsoleOutputWidget
from .repl_input import ReplInput
from .console_model import make_line, MsgKind
from .console_theme import DEFAULT_COLORS

_BTN = (
    "QPushButton{{background:{bg};color:#cdd6f4;border:none;border-radius:3px;"
    "font-size:10px;padding:2px 8px;}}"
    "QPushButton:hover{{background:{hv};}}"
)
_BAR_STYLE = (
    f"QWidget{{background:{DEFAULT_COLORS.tab_active};"
    f"border-bottom:1px solid {DEFAULT_COLORS.border};}}"
)

class ReplTabWidget(QWidget):
    """Interactive Python REPL tab with output display and input line."""
    def __init__(self, api, parent=None) -> None:
        super().__init__(parent)
        self._api = api
        self._build_ui()
        self._connect_api()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = self._make_toolbar()
        lay.addWidget(bar)
        self._output = ConsoleOutputWidget()
        lay.addWidget(self._output, 1)
        self._input = ReplInput()
        self._input.submitted.connect(self._on_submit)
        lay.addWidget(self._input)
        self._input.setFocus()

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(_BAR_STYLE)
        bar.setFixedHeight(28)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 2, 6, 2)
        bl.setSpacing(4)
        lbl = QLabel("Python REPL")
        lbl.setStyleSheet("QLabel{color:#a6e3a1;font-size:10px;font-weight:bold;}")
        bl.addWidget(lbl)
        bl.addStretch()
        for label, tooltip, slot in [
            ("TS",    "Toggle timestamps",   self._toggle_ts),
            ("SRC",   "Toggle source",       self._toggle_src),
            ("AS",    "Toggle auto-scroll",  self._toggle_as),
            ("Save",  "Save output to file", self._on_save),
            ("Clear", "Clear output",        self._on_clear),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(_BTN.format(bg="#313244", hv="#45475a"))
            btn.setFixedHeight(20)
            btn.setToolTip(tooltip)
            if label in ("TS", "SRC", "AS"):
                btn.setCheckable(True)
                btn.setChecked(label == "AS")
            btn.clicked.connect(slot) if label not in ("TS", "SRC", "AS") else btn.toggled.connect(slot)
            bl.addWidget(btn)
        return bar

    def _connect_api(self) -> None:
        self._api.line_appended.connect(self._on_line)
        self._api.cleared.connect(self._output.clear_output)

    def _on_line(self, payload) -> None:
        tab_id, line = payload
        if tab_id == "__repl__":
            self._output.append_line(line)

    def _on_submit(self, text: str) -> None:
        self._api.execute(text)
        self._input.set_namespace(self._api.executor.namespace)

    def _toggle_ts(self, checked: bool) -> None:
        self._output.set_show_timestamps(checked)
    def _toggle_src(self, checked: bool) -> None:
        self._output.set_show_source(checked)
    def _toggle_as(self, checked: bool) -> None:
        self._output.set_auto_scroll(checked)

    def _on_clear(self) -> None:
        self._api.clear("__repl__")
        self._output.clear_output()

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save REPL Output", f"repl_{int(time.time())}.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self._api.save_to_file(path, "__repl__")

    def focus_input(self) -> None:
        self._input.setFocus()

    def refresh_namespace(self) -> None:
        self._input.set_namespace(self._api.executor.namespace)