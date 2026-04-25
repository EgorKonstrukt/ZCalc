from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QColorDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget,
)

from expr_item import ExprItem

_COLORS = [
    ("#fff9c4", "#f9a825"),
    ("#e8f5e9", "#388e3c"),
    ("#e3f2fd", "#1565c0"),
    ("#fce4ec", "#c62828"),
    ("#f3e5f5", "#6a1b9a"),
]

_STRIP_STYLE = "border-radius:3px;"
_CARD_STYLE = (
    "QFrame#comment_card{{background:{bg};border-left:4px solid {border};"
    "border-radius:4px;margin:2px 0;}}"
)
_TEXT_STYLE = (
    "QTextEdit{{background:transparent;border:none;font-size:12px;"
    "color:#333;padding:2px;}}"
)
_BTN_STYLE = (
    "QPushButton{{background:transparent;border:none;color:{color};"
    "font-size:11px;padding:2px 4px;}}"
    "QPushButton:hover{{color:#333;}}"
)
_COUNTER = [0]


class CommentItem(QFrame):
    """
    A styled, editable text comment that can be inserted into the item list.

    Supports colour cycling, background colour picker, and collapsing.
    State is serialised as {text, color_idx, bg, border} for session save.
    """

    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, parent=None)-> None:
        super().__init__(parent)
        _COUNTER[0] += 1
        self._color_idx = (_COUNTER[0] - 1) % len(_COLORS)
        self._bg, self._border = _COLORS[self._color_idx]
        self.setObjectName("comment_card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setFixedHeight(100)
        self._build_ui()

    def _build_ui(self) -> None:
        self._apply_card_style()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 4, 4)
        outer.setSpacing(2)

        header = QHBoxLayout()
        header.setSpacing(4)

        self._icon = QLabel("💬")
        self._icon.setFixedWidth(20)
        self._icon.setStyleSheet("QLabel{font-size:13px;}")

        self._label = QLabel("Comment")
        self._label.setStyleSheet(
            f"QLabel{{font-size:10px;font-weight:bold;color:{self._border};}}"
        )
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._color_btn = QPushButton("◉")
        self._color_btn.setFixedSize(20, 20)
        self._color_btn.setStyleSheet(
            _BTN_STYLE.format(color=self._border)
        )
        self._color_btn.setToolTip("Change colour")
        self._color_btn.clicked.connect(self._cycle_color)

        self._rm_btn = QPushButton("✕")
        self._rm_btn.setFixedSize(18, 18)
        self._rm_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#aaa;font-size:11px;}"
            "QPushButton:hover{color:#e74c3c;}"
        )
        self._rm_btn.clicked.connect(lambda: self.removed.emit(self))

        for w in (self._icon, self._label, self._color_btn, self._rm_btn):
            header.addWidget(w)
        outer.addLayout(header)

        self._text = QTextEdit()
        self._text.setPlaceholderText("Add a comment…")
        self._text.setFixedHeight(64)
        self._text.setStyleSheet(_TEXT_STYLE)
        self._text.textChanged.connect(self.changed.emit)
        outer.addWidget(self._text)

    def _apply_card_style(self) -> None:
        self.setStyleSheet(
            _CARD_STYLE.format(bg=self._bg, border=self._border)
        )

    def _cycle_color(self) -> None:
        self._color_idx = (self._color_idx + 1) % len(_COLORS)
        self._bg, self._border = _COLORS[self._color_idx]
        self._apply_card_style()
        self._label.setStyleSheet(
            f"QLabel{{font-size:10px;font-weight:bold;color:{self._border};}}"
        )
        self._color_btn.setStyleSheet(_BTN_STYLE.format(color=self._border))
        self.changed.emit()

    def to_state(self) -> dict:
        return {
            "type": "plugin_item",
            "plugin_id": "zcalc.comments",
            "text": self._text.toPlainText(),
            "color_idx": self._color_idx,
            "bg": self._bg,
            "border": self._border,
        }

    def apply_state(self, state: dict) -> None:
        self._color_idx = state.get("color_idx", 0)
        self._bg = state.get("bg", _COLORS[0][0])
        self._border = state.get("border", _COLORS[0][1])
        self._apply_card_style()
        self._label.setStyleSheet(
            f"QLabel{{font-size:10px;font-weight:bold;color:{self._border};}}"
        )
        self._color_btn.setStyleSheet(_BTN_STYLE.format(color=self._border))
        self._text.blockSignals(True)
        self._text.setPlainText(state.get("text", ""))
        self._text.blockSignals(False)
