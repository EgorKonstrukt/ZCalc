from __future__ import annotations
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal
from .console_output import ConsoleOutputWidget
from .console_model import ConsoleLine
from .console_theme import DEFAULT_COLORS

_BTN = (
    "QPushButton{{background:{bg};color:#cdd6f4;border:none;border-radius:3px;"
    "font-size:10px;padding:2px 8px;}}"
    "QPushButton:hover{{background:{hv};}}"
)
_BTN_SAVE  = _BTN.format(bg="#313244", hv="#45475a")
_BTN_CLEAR = _BTN.format(bg="#313244", hv="#45475a")
_BTN_TS    = _BTN.format(bg="#313244", hv="#45475a")
_BAR_STYLE = f"QWidget{{background:{DEFAULT_COLORS.tab_active};border-bottom:1px solid {DEFAULT_COLORS.border};}}"

class ScriptTabWidget(QWidget):
    """Output tab for one script: toolbar + scrollable output."""
    save_requested = pyqtSignal(str)

    def __init__(self, tab_id: str, label: str, parent=None) -> None:
        super().__init__(parent)
        self._tab_id = tab_id
        self._label = label
        self._show_ts = False
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QWidget()
        bar.setStyleSheet(_BAR_STYLE)
        bar.setFixedHeight(28)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(6, 2, 6, 2)
        bl.setSpacing(4)
        lbl = QLabel(self._label)
        lbl.setStyleSheet("QLabel{color:#89b4fa;font-size:10px;font-weight:bold;}")
        bl.addWidget(lbl)
        bl.addStretch()
        ts_btn = QPushButton("TS")
        ts_btn.setStyleSheet(_BTN_TS)
        ts_btn.setFixedHeight(20)
        ts_btn.setCheckable(True)
        ts_btn.setToolTip("Toggle timestamps")
        ts_btn.toggled.connect(self._toggle_ts)
        bl.addWidget(ts_btn)
        src_btn = QPushButton("SRC")
        src_btn.setStyleSheet(_BTN_TS)
        src_btn.setFixedHeight(20)
        src_btn.setCheckable(True)
        src_btn.setChecked(True)
        src_btn.setToolTip("Toggle source labels")
        src_btn.toggled.connect(self._toggle_src)
        bl.addWidget(src_btn)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(_BTN_SAVE)
        save_btn.setFixedHeight(20)
        save_btn.clicked.connect(self._on_save)
        bl.addWidget(save_btn)
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(_BTN_CLEAR)
        clear_btn.setFixedHeight(20)
        clear_btn.clicked.connect(self._on_clear)
        bl.addWidget(clear_btn)
        lay.addWidget(bar)
        self._output = ConsoleOutputWidget()
        lay.addWidget(self._output)

    def append_line(self, line: ConsoleLine) -> None:
        self._output.append_line(line)

    def clear_output(self) -> None:
        self._output.clear_output()

    def _toggle_ts(self, checked: bool) -> None:
        self._output.set_show_timestamps(checked)
    def _toggle_src(self, checked: bool) -> None:
        self._output.set_show_source(checked)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Console Output", f"{self._label}_{int(time.time())}.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            self.save_requested.emit(path)

    def _on_clear(self) -> None:
        self.clear_output()

    @property
    def tab_id(self) -> str:
        return self._tab_id

    @property
    def output(self) -> ConsoleOutputWidget:
        return self._output