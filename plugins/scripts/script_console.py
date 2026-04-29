from __future__ import annotations
import sys
import time
from typing import Optional
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QPlainTextEdit, QLabel, QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QMetaObject, Q_ARG
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QFont


_MAX_LINES = 2000

_CONSOLE_STYLE = """
QPlainTextEdit {
    background: #1e1e1e;
    color: #d4d4d4;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 11px;
    border: none;
}
"""

_DOCK_BTN = (
    "QPushButton{background:#333;color:#ccc;border:1px solid #555;"
    "border-radius:3px;font-size:10px;padding:2px 8px;}"
    "QPushButton:hover{background:#444;}"
)


class ScriptConsole(QDockWidget):
    """
    Dockable console window that captures stdout/stderr from scripts
    and displays timestamped, color-coded output.

    Thread-safe: append_text() can be called from any thread.
    """

    def __init__(self, parent=None):
        super().__init__("Script Console", parent)
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable,
        )
        self._build_ui()
        self._orig_stdout = None
        self._orig_stderr = None

    def _build_ui(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        toolbar = QWidget()
        toolbar.setStyleSheet("background:#252526;border-bottom:1px solid #3c3c3c;")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(6, 3, 6, 3)
        tl.setSpacing(6)

        lbl = QLabel("Output")
        lbl.setStyleSheet("QLabel{color:#ccc;font-size:11px;font-weight:bold;}")

        self._auto_scroll = QCheckBox("Auto-scroll")
        self._auto_scroll.setChecked(True)
        self._auto_scroll.setStyleSheet("QCheckBox{color:#aaa;font-size:10px;}")

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(_DOCK_BTN)
        clear_btn.setFixedHeight(20)
        clear_btn.clicked.connect(self.clear)

        self._line_count_lbl = QLabel("0 lines")
        self._line_count_lbl.setStyleSheet("QLabel{color:#888;font-size:10px;}")

        tl.addWidget(lbl)
        tl.addStretch()
        tl.addWidget(self._line_count_lbl)
        tl.addWidget(self._auto_scroll)
        tl.addWidget(clear_btn)

        self._text = QPlainTextEdit()
        self._text.setStyleSheet(_CONSOLE_STYLE)
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(_MAX_LINES)
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.Monospace)
        self._text.setFont(font)

        lay.addWidget(toolbar)
        lay.addWidget(self._text)
        self.setWidget(w)

    def append_text(self, text: str, color: str = "#d4d4d4", script_name: str = ""):
        """Thread-safe append. color is a hex string."""
        if not text:
            return
        QMetaObject.invokeMethod(
            self, "_append_main_thread",
            Qt.QueuedConnection,
            Q_ARG(str, text),
            Q_ARG(str, color),
            Q_ARG(str, script_name),
        )

    def _append_main_thread(self, text: str, color: str, script_name: str):
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt_time = QTextCharFormat()
        fmt_time.setForeground(QColor("#608b4e"))
        ts = time.strftime("%H:%M:%S")
        cursor.insertText(f"[{ts}]", fmt_time)

        if script_name:
            fmt_name = QTextCharFormat()
            fmt_name.setForeground(QColor("#9cdcfe"))
            cursor.insertText(f" [{script_name}]", fmt_name)

        fmt_sep = QTextCharFormat()
        fmt_sep.setForeground(QColor("#555"))
        cursor.insertText(" ", fmt_sep)

        fmt_msg = QTextCharFormat()
        fmt_msg.setForeground(QColor(color))
        if not text.endswith("\n"):
            text += "\n"
        cursor.insertText(text, fmt_msg)

        n = self._text.blockCount()
        self._line_count_lbl.setText(f"{n} lines")

        if self._auto_scroll.isChecked():
            self._text.setTextCursor(cursor)
            self._text.ensureCursorVisible()

    def append_stdout(self, text: str, script_name: str = ""):
        self.append_text(text, "#d4d4d4", script_name)

    def append_stderr(self, text: str, script_name: str = ""):
        self.append_text(text, "#f44747", script_name)

    def append_info(self, text: str, script_name: str = ""):
        self.append_text(text, "#4ec9b0", script_name)

    def append_warn(self, text: str, script_name: str = ""):
        self.append_text(text, "#dcdcaa", script_name)

    def clear(self):
        self._text.clear()
        self._line_count_lbl.setText("0 lines")


class ConsoleStream:
    """
    File-like object that redirects writes to ScriptConsole.
    Used to capture print() output from scripts.
    """
    def __init__(self, console: ScriptConsole, script_name: str, is_err: bool = False):
        self._console = console
        self._name = script_name
        self._is_err = is_err

    def write(self, text: str):
        if text.strip():
            if self._is_err:
                self._console.append_stderr(text.rstrip(), self._name)
            else:
                self._console.append_stdout(text.rstrip(), self._name)

    def flush(self):
        pass

    def fileno(self):
        raise OSError("ConsoleStream has no file descriptor")
