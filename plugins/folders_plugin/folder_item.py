from __future__ import annotations

from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QApplication, QColorDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

_FOLDER_COLORS = [
    "#3498db", "#e74c3c", "#2ecc71", "#f39c12",
    "#9b59b6", "#1abc9c", "#e67e22",
]

_HEADER_STYLE = (
    "QFrame#folder_header{{background:{color};"
    "border-radius:4px;margin:2px 0;}}"
)
_TITLE_STYLE = (
    "QLineEdit{{background:transparent;border:none;color:white;"
    "font-size:12px;font-weight:bold;padding:0px;}}"
    "QLineEdit:focus{{background:rgba(255,255,255,0.15);border-radius:3px;}}"
)
_BODY_STYLE = (
    "QFrame#folder_body{background:#f8faff;"
    "border:1px solid #c8d8f0;border-top:none;border-radius:0 0 4px 4px;"
    "margin:0 2px 2px 2px;}"
)
_BTN_WHITE = (
    "QPushButton{background:transparent;border:none;color:rgba(255,255,255,0.8);"
    "font-size:12px;padding:2px 4px;}"
    "QPushButton:hover{color:white;}"
)
_COUNTER = [0]


class FolderItem(QFrame):
    """
    Collapsible folder widget (Desmos-style) that visually groups items below it.

    The folder itself does not own child items — it acts as a visual separator
    and collapse/expand toggle.  Items added via '+ Add' after a folder header
    appear indented until the next folder or end of list.

    A future extension could move child widgets into an internal layout;
    for now the folder header + collapse button provides the core interaction.
    """

    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, context=None, parent: QWidget = None) -> None:
        super().__init__(parent)
        _COUNTER[0] += 1
        self._color_idx = (_COUNTER[0] - 1) % len(_FOLDER_COLORS)
        self._color = _FOLDER_COLORS[self._color_idx]
        self._collapsed = False
        self._context = context
        self._child_widgets: list = []
        self.setObjectName("folder_root")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header = QFrame()
        self._header.setObjectName("folder_header")
        self._header.setFixedHeight(34)
        self._apply_header_style()
        h_lay = QHBoxLayout(self._header)
        h_lay.setContentsMargins(8, 0, 6, 0)
        h_lay.setSpacing(4)

        self._arrow_btn = QPushButton("▼")
        self._arrow_btn.setFixedSize(18, 18)
        self._arrow_btn.setStyleSheet(_BTN_WHITE)
        self._arrow_btn.clicked.connect(self._toggle_collapse)

        self._name_edit = QLineEdit(f"Folder {_COUNTER[0]}")
        self._name_edit.setStyleSheet(_TITLE_STYLE)
        self._name_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._name_edit.textChanged.connect(self.changed.emit)

        self._color_btn = QPushButton("◉")
        self._color_btn.setFixedSize(20, 20)
        self._color_btn.setStyleSheet(_BTN_WHITE)
        self._color_btn.setToolTip("Change folder colour")
        self._color_btn.clicked.connect(self._cycle_color)

        self._vis_btn = QPushButton("👁")
        self._vis_btn.setFixedSize(22, 22)
        self._vis_btn.setCheckable(True)
        self._vis_btn.setChecked(True)
        self._vis_btn.setStyleSheet(_BTN_WHITE)
        self._vis_btn.setToolTip("Toggle visibility of folder contents")
        self._vis_btn.toggled.connect(self._on_visibility_toggled)

        self._rm_btn = QPushButton("✕")
        self._rm_btn.setFixedSize(18, 18)
        self._rm_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;"
            "color:rgba(255,255,255,0.6);font-size:11px;}"
            "QPushButton:hover{color:white;}"
        )
        self._rm_btn.clicked.connect(lambda: self.removed.emit(self))

        for w in (self._arrow_btn, self._name_edit,
                  self._color_btn, self._vis_btn, self._rm_btn):
            h_lay.addWidget(w)
        root.addWidget(self._header)

        self._body = QFrame()
        self._body.setObjectName("folder_body")
        self._body.setStyleSheet(_BODY_STYLE)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(12, 4, 4, 4)
        self._body_layout.setSpacing(2)

        self._empty_label = QLabel("(empty folder — add items below)")
        self._empty_label.setStyleSheet(
            "QLabel{font-size:10px;color:#aaa;padding:4px 0;}"
        )
        self._body_layout.addWidget(self._empty_label)
        root.addWidget(self._body)

    def _apply_header_style(self) -> None:
        self._header.setStyleSheet(
            _HEADER_STYLE.format(color=self._color)
        )

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self._body.setVisible(not self._collapsed)
        self._arrow_btn.setText("▶" if self._collapsed else "▼")
        self.changed.emit()

    def update_empty_state(self):
        count = self._body_layout.count()

        has_content = False
        for i in range(count):
            item = self._body_layout.itemAt(i)
            widget = item.widget()
            if widget and widget != self._empty_label:
                has_content = True
                break

        self._empty_label.setVisible(not has_content)
    def _cycle_color(self) -> None:
        self._color_idx = (self._color_idx + 1) % len(_FOLDER_COLORS)
        self._color = _FOLDER_COLORS[self._color_idx]
        self._apply_header_style()
        self.changed.emit()

    def _on_visibility_toggled(self, visible: bool) -> None:
        self._vis_btn.setText("👁" if visible else "🚫")
        self.changed.emit()

    def get_name(self) -> str:
        return self._name_edit.text()

    def is_visible_folder(self) -> bool:
        return self._vis_btn.isChecked()

    def is_collapsed(self) -> bool:
        return self._collapsed

    def to_state(self) -> dict:
        return {
            "type": "plugin_item",
            "plugin_id": "zcalc.folders",
            "name": self.get_name(),
            "color_idx": self._color_idx,
            "color": self._color,
            "collapsed": self._collapsed,
            "folder_visible": self.is_visible_folder(),
        }

    def apply_state(self, state: dict) -> None:
        self._name_edit.blockSignals(True)
        self._name_edit.setText(state.get("name", "Folder"))
        self._name_edit.blockSignals(False)
        self._color_idx = state.get("color_idx", 0)
        self._color = state.get("color", _FOLDER_COLORS[0])
        self._apply_header_style()
        collapsed = state.get("collapsed", False)
        if collapsed != self._collapsed:
            self._toggle_collapse()
        vis = state.get("folder_visible", True)
        self._vis_btn.setChecked(vis)
