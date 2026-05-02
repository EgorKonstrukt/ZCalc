from __future__ import annotations
from typing import Dict, Any, Callable, Optional
from PyQt5.QtWidgets import QLineEdit, QSizePolicy
from PyQt5.QtGui import QFont, QColor, QPalette, QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint
from .console_theme import (
    DEFAULT_COLORS, FONT_FAMILY, FONT_SIZE_PT,
    DEBOUNCE_AUTOCOMPLETE_MS, AUTOCOMPLETE_MIN_CHARS, AUTOCOMPLETE_MAX_ITEMS,
)
from .autocomplete import get_completions, InputHistory
from .autocomplete_popup import AutocompletePopup

class ReplInput(QLineEdit):
    """Single-line REPL input with history navigation and autocomplete."""
    submitted = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ns: Dict[str, Any] = {}
        self._history = InputHistory()
        self._popup = AutocompletePopup(self.window() if parent else None)
        self._popup.item_chosen.connect(self._apply_completion)
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_AUTOCOMPLETE_MS)
        self._debounce.timeout.connect(self._trigger_autocomplete)
        self.textChanged.connect(self._on_text_changed)
        self._apply_style()

    def _apply_style(self) -> None:
        c = DEFAULT_COLORS
        families = [f.strip().strip("'") for f in FONT_FAMILY.split(",")]
        font = QFont(families[0], FONT_SIZE_PT)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setStyleSheet(
            f"QLineEdit{{background:{c.bg};color:{c.stdin};border:none;"
            f"border-top:1px solid {c.border};padding:4px 6px;"
            f"selection-background-color:{c.selection_bg};}}"
        )
        self.setPlaceholderText(">>> Enter Python expression or command...")

    def set_namespace(self, ns: Dict[str, Any]) -> None:
        self._ns = ns

    def _on_text_changed(self, _: str) -> None:
        if len(self.text()) >= AUTOCOMPLETE_MIN_CHARS:
            self._debounce.start()
        else:
            self._popup.hide()

    def _trigger_autocomplete(self) -> None:
        text = self.text()
        if not text.strip():
            self._popup.hide()
            return
        completions, prefix = get_completions(text, self.cursorPosition(), self._ns)
        completions = completions[:AUTOCOMPLETE_MAX_ITEMS]
        if len(completions) == 1 and completions[0] == prefix:
            self._popup.hide()
            return
        if completions:
            self._show_popup(completions, prefix)
        else:
            self._popup.hide()

    def _show_popup(self, completions, prefix) -> None:
        self._popup.setParent(self.window())
        self._popup.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        pos = self.mapTo(self.window(), QPoint(0, -self._popup.sizeHint().height() - 4))
        self._popup.move(pos)
        self._popup.show_completions(completions, prefix)

    def _apply_completion(self, text: str) -> None:
        prefix = self._popup._prefix
        cur = self.text()
        pos = self.cursorPosition()
        dot_idx = cur.rfind(".", 0, pos)
        space_idx = max(
            cur.rfind(" ", 0, pos), cur.rfind("(", 0, pos),
            cur.rfind(",", 0, pos), cur.rfind("[", 0, pos),
            cur.rfind("=", 0, pos),
        )
        if dot_idx > space_idx:
            before = cur[:dot_idx + 1]
            after = cur[pos:]
            new_text = before + text + after
            new_pos = dot_idx + 1 + len(text)
        else:
            token_start = space_idx + 1
            before = cur[:token_start]
            after = cur[pos:]
            new_text = before + text + after
            new_pos = token_start + len(text)
        self.setText(new_text)
        self.setCursorPosition(new_pos)
        self._popup.hide()

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if self._popup.isVisible():
            if key == Qt.Key_Down:
                self._popup.select_next()
                return
            elif key == Qt.Key_Up:
                self._popup.select_prev()
                return
            elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
                result = self._popup.accept_current()
                if result:
                    self._apply_completion(result)
                    return
            elif key == Qt.Key_Escape:
                self._popup.hide()
                return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text()
            if text.strip():
                self._history.push(text)
                self.submitted.emit(text)
                self.clear()
            return
        if key == Qt.Key_Up:
            prev = self._history.up(self.text())
            if prev is not None:
                self.setText(prev)
                self.end(False)
            return
        if key == Qt.Key_Down:
            nxt = self._history.down()
            if nxt is not None:
                self.setText(nxt)
                self.end(False)
            return
        super().keyPressEvent(event)

    def history(self) -> InputHistory:
        return self._history