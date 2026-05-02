from __future__ import annotations
import time
from typing import List, Optional, TYPE_CHECKING
from PyQt5.QtWidgets import QTextEdit, QAbstractScrollArea
from PyQt5.QtGui import (
    QTextCharFormat, QColor, QFont, QTextCursor,
    QKeySequence, QTextDocument,
)
from PyQt5.QtCore import Qt, QTimer
from .console_model import ConsoleLine, ConsoleBuffer, MsgKind
from .console_theme import (
    DEFAULT_COLORS, FONT_FAMILY, FONT_SIZE_PT, MAX_SCROLLBACK
)

_TIMESTAMP_FMT = "%H:%M:%S"
_BATCH_FLUSH_MS = 40

class ConsoleOutputWidget(QTextEdit):
    """
    Read-only rich-text display for console output.
    Supports ANSI colors, timestamps, source labels, and keyword highlighting.
    """
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._colors = DEFAULT_COLORS
        self._show_timestamps = False
        self._show_source = True
        self._auto_scroll = True
        self._pending: List[ConsoleLine] = []
        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(_BATCH_FLUSH_MS)
        self._flush_timer.timeout.connect(self._flush_pending)
        self._apply_style()
        self._setup_font()

    def _apply_style(self) -> None:
        c = self._colors
        self.setStyleSheet(
            f"QTextEdit{{background:{c.bg};color:{c.fg};border:none;"
            f"selection-background-color:{c.selection_bg};}}"
            f"QScrollBar:vertical{{background:{c.bg};width:10px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{c.scrollbar};border-radius:5px;min-height:20px;}}"
            f"QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0px;}}"
        )

    def _setup_font(self) -> None:
        families = [f.strip().strip("'") for f in FONT_FAMILY.split(",")]
        font = QFont()
        for fam in families:
            font.setFamily(fam)
            from PyQt5.QtGui import QFontDatabase
            if font.family().lower() == fam.lower():
                break
        font.setPointSize(FONT_SIZE_PT)
        font.setFixedPitch(True)
        self.setFont(font)

    def append_line(self, line: ConsoleLine) -> None:
        self._pending.append(line)
        if not self._flush_timer.isActive():
            self._flush_timer.start()

    def _flush_pending(self) -> None:
        if not self._pending:
            self._flush_timer.stop()
            return
        batch = self._pending[:]
        self._pending.clear()
        cur = self.textCursor()
        cur.movePosition(QTextCursor.End)
        for line in batch:
            self._write_line(cur, line)
        if self._auto_scroll:
            vsb = self.verticalScrollBar()
            vsb.setValue(vsb.maximum())
        if not self._pending:
            self._flush_timer.stop()

    def _write_line(self, cur: QTextCursor, line: ConsoleLine) -> None:
        doc = self.document()
        if doc.blockCount() > MAX_SCROLLBACK:
            tmp = QTextCursor(doc.begin())
            tmp.select(QTextCursor.BlockUnderCursor)
            tmp.removeSelectedText()
            tmp.deleteChar()
        if self._show_timestamps:
            ts = time.strftime(_TIMESTAMP_FMT, time.localtime(line.timestamp))
            self._insert_text(cur, ts + " ", self._colors.timestamp)
        if self._show_source and line.source:
            self._insert_text(cur, f"[{line.source}] ", self._colors.timestamp, bold=True)
        for span in line.spans:
            self._insert_text(cur, span.text, span.color, span.bold, span.italic, span.underline)
        self._insert_text(cur, "\n", None)

    def _insert_text(
        self, cur: QTextCursor, text: str, color: Optional[str],
        bold: bool = False, italic: bool = False, underline: bool = False,
    ) -> None:
        fmt = QTextCharFormat()
        if color:
            fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        if underline:
            fmt.setFontUnderline(True)
        cur.insertText(text, fmt)

    def clear_output(self) -> None:
        self.clear()

    def set_show_timestamps(self, v: bool) -> None:
        self._show_timestamps = v
    def set_show_source(self, v: bool) -> None:
        self._show_source = v
    def set_auto_scroll(self, v: bool) -> None:
        self._auto_scroll = v

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mod = event.modifiers()
        vsb = self.verticalScrollBar()
        if key == Qt.Key_Home and mod == Qt.ControlModifier:
            vsb.setValue(0)
        elif key == Qt.Key_End and mod == Qt.ControlModifier:
            vsb.setValue(vsb.maximum())
        elif key == Qt.Key_PageUp:
            vsb.setValue(vsb.value() - vsb.pageStep())
        elif key == Qt.Key_PageDown:
            vsb.setValue(vsb.value() + vsb.pageStep())
        else:
            super().keyPressEvent(event)