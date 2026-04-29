from __future__ import annotations

from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QColorDialog, QSpinBox,
    QSizePolicy, QFrame, QWidget, QApplication, QLabel,
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QColor
from pyqt5_math_widget import MathEditor
from constants import COLORS
from core.items.expr_item import ExprItem, ITEM_HEIGHT
from sympy_engine import normalize_editor_expr
from math_display import MathDisplay

_EDITOR_HEIGHT   = 260
_ROW_COLLAPSED_H = ITEM_HEIGHT
_ROW_EXPANDED_H  = ITEM_HEIGHT + _EDITOR_HEIGHT
_PARAM_ROW_EXPANDED_H = ITEM_HEIGHT + _EDITOR_HEIGHT + 100
_TOOLBAR_GROUPS  = ["struct", "operators", "greek", "functions", "edit"]
_REVALIDATE_MS   = 300

_TYPE_META = {
    "y=f(x)": {
        "label":    "f(x)",
        "bg":       "#dbeafe",
        "fg":       "#1d4ed8",
        "border":   "#93c5fd",
        "hover_bg": "#bfdbfe",
        "desc":     "Cartesian  y = f(x)",
    },
    "r=f(t)": {
        "label":    "r(θ)",
        "bg":       "#fce7f3",
        "fg":       "#be185d",
        "border":   "#f9a8d4",
        "hover_bg": "#fbcfe8",
        "desc":     "Polar  r = f(θ)",
    },
    "param": {
        "label":    "(x,y)",
        "bg":       "#dcfce7",
        "fg":       "#15803d",
        "border":   "#86efac",
        "hover_bg": "#bbf7d0",
        "desc":     "Parametric  (x(t), y(t))",
    },
}


def _normalize_mode(mode: str) -> str:
    if mode == "parametric":
        return "param"
    return mode if mode in _TYPE_META else "y=f(x)"


class _InlineEditor(MathEditor):
    """Compact MathEditor configured for inline row use."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(
            parent=parent,
            show_toolbar=True,
            toolbar_groups=_TOOLBAR_GROUPS,
            zoom=0.9,
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


class FunctionRow(ExprItem):
    """
    Base class for a single expression row.

    Subclasses set _MODE to fix the curve type.
    The mode combo-box from the old design is replaced by a read-only
    type badge whose style is determined by _TYPE_META.
    """

    changed = pyqtSignal()
    removed = pyqtSignal(object)

    _id_counter = 0
    _MODE: str = "y=f(x)"

    def __init__(self, idx: int, parent: QWidget = None) -> None:
        super().__init__(parent)
        FunctionRow._id_counter += 1
        self._uid         = FunctionRow._id_counter
        self.color        = COLORS[idx % len(COLORS)]
        self.chart_line   = None
        self._enabled     = True
        self._mode        = self._MODE
        self._expanded    = False
        self._sympy_expr  = ""
        self._sympy_expr2 = ""

        self._revalidate_timer = QTimer(self)
        self._revalidate_timer.setSingleShot(True)
        self._revalidate_timer.timeout.connect(self._on_revalidate)

        self._build_ui()
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)

    def _build_ui(self) -> None:
        meta = _TYPE_META[self._mode]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        top_row = QWidget()
        top_row.setMinimumHeight(_ROW_COLLAPSED_H)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)

        self._color_bar = QFrame()
        self._color_bar.setFixedWidth(16)
        self._color_bar.setStyleSheet(
            f"background:{self.color};border-radius:3px;"
        )
        self._color_bar.mousePressEvent = lambda _e: self._pick_color()
        self._color_bar.setCursor(Qt.PointingHandCursor)
        top_layout.addWidget(self._color_bar)

        inner = QHBoxLayout()
        inner.setContentsMargins(6, 2, 4, 2)
        inner.setSpacing(4)

        self._type_badge = QLabel(meta["label"])
        self._type_badge.setFixedWidth(38)
        self._type_badge.setAlignment(Qt.AlignCenter)
        self._type_badge.setToolTip(meta["desc"])
        self._type_badge.setStyleSheet(
            f"QLabel{{"
            f"background:{meta['bg']};"
            f"color:{meta['fg']};"
            f"border:1px solid {meta['border']};"
            f"border-radius:3px;"
            f"font-size:9px;"
            f"font-weight:bold;"
            f"padding:1px 2px;"
            f"}}"
        )

        self._display = MathDisplay(self)
        self._display.clicked.connect(self._expand)

        self._display2 = MathDisplay(self)
        self._display2.clicked.connect(self._expand)
        self._display2.setMinimumWidth(40)
        self._display2.setVisible(False)

        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 10)
        self._width_spin.setValue(2)
        self._width_spin.setFixedWidth(36)
        self._width_spin.valueChanged.connect(self.changed.emit)

        rm = self._mk_remove_btn()

        for w in (self._type_badge, self._display, self._display2,
                  self._width_spin, rm):
            inner.addWidget(w)

        top_layout.addLayout(inner)
        outer.addWidget(top_row)

        editor_wrap = QWidget()
        editor_wrap.setFixedHeight(_EDITOR_HEIGHT)
        ew_lay = QVBoxLayout(editor_wrap)
        ew_lay.setContentsMargins(4, 2, 4, 2)
        ew_lay.setSpacing(4)

        self._editor = _InlineEditor(editor_wrap)
        self._editor.formula_changed.connect(self._on_editor1_changed)
        ew_lay.addWidget(self._editor)

        self._editor2_wrap = QWidget()
        e2w_lay = QVBoxLayout(self._editor2_wrap)
        e2w_lay.setContentsMargins(0, 0, 0, 0)
        e2w_lay.setSpacing(0)
        lbl2 = QLabel("y(t):")
        lbl2.setStyleSheet("font-size:10px;color:#666;")
        e2w_lay.addWidget(lbl2)
        self._editor2 = _InlineEditor(self._editor2_wrap)
        self._editor2.formula_changed.connect(self._on_editor2_changed)
        e2w_lay.addWidget(self._editor2)
        self._editor2_wrap.setVisible(False)
        ew_lay.addWidget(self._editor2_wrap)

        self._editor_wrap = editor_wrap
        self._editor_wrap.setVisible(False)
        outer.addWidget(self._editor_wrap)

        self._post_build(outer)

    def _post_build(self, outer_layout: QVBoxLayout) -> None:
        """Hook for subclasses to extend the layout after base construction."""

    def _pick_color(self) -> None:
        c = QColorDialog.getColor(QColor(self.color), self)
        if c.isValid():
            self.color = c.name()
            self._color_bar.setStyleSheet(
                f"background:{self.color};border-radius:3px;"
            )
            if self.chart_line:
                self.chart_line.pen.setColor(QColor(self.color))
            self.changed.emit()

    def _on_editor1_changed(self, sympy_str: str) -> None:
        var = "t" if self._mode in ("r=f(t)", "param") else "x"
        self._sympy_expr = normalize_editor_expr(sympy_str, var=var)
        self._revalidate_timer.start(_REVALIDATE_MS)

    def _on_editor2_changed(self, sympy_str: str) -> None:
        self._sympy_expr2 = normalize_editor_expr(sympy_str, var="t")
        self._revalidate_timer.start(_REVALIDATE_MS)

    def _on_revalidate(self) -> None:
        self.changed.emit()

    def _on_app_focus_changed(self, old, new) -> None:
        if not self._expanded or new is None:
            return
        w = new
        while w is not None:
            if w is self:
                return
            w = w.parent()
        self._collapse()

    def _expand(self) -> None:
        if self._expanded:
            return
        self._expanded = True
        self._editor_wrap.setVisible(True)
        self.setFixedHeight(_ROW_EXPANDED_H)

    def _collapse(self) -> None:
        if not self._expanded:
            return
        self._expanded = False
        self._editor_wrap.setVisible(False)
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.adjustSize()
        self._refresh_displays()

    def _refresh_displays(self) -> None:
        self._display.set_formula(self._sympy_expr)
        self._display2.set_formula("")
        self._display2.setVisible(False)

    def get_expr(self) -> str:
        return self._sympy_expr

    def get_expr2(self) -> str:
        return self._sympy_expr2

    def get_mode(self) -> str:
        return self._mode

    def is_enabled(self) -> bool:
        return self._enabled

    def get_width(self) -> int:
        return self._width_spin.value()

    def to_state(self) -> dict:
        return {
            "expr":    self.get_expr(),
            "expr2":   self.get_expr2(),
            "mode":    self._mode,
            "color":   self.color,
            "width":   self.get_width(),
            "enabled": self._enabled,
            "type":    "function",
        }

    def apply_state(self, state: dict) -> None:
        expr  = state.get("expr", "")
        expr2 = state.get("expr2", "")
        self._sympy_expr  = expr
        self._sympy_expr2 = expr2
        if expr:
            self._editor.model().set_from_text(expr)
        else:
            self._editor.clear()
        if expr2:
            self._editor2.model().set_from_text(expr2)
        else:
            self._editor2.clear()
        self.color = state.get("color", self.color)
        self._color_bar.setStyleSheet(
            f"background:{self.color};border-radius:3px;"
        )
        self._width_spin.setValue(state.get("width", 2))
        self._enabled = state.get("enabled", True)
        self._refresh_displays()
        self.changed.emit()

    def set_expr(
        self,
        expr: str,
        mode: str = None,
        expr2: str = None,
    ) -> None:
        """Programmatically set expression strings. mode arg is accepted but ignored."""
        self._sympy_expr = expr
        if expr:
            self._editor.model().set_from_text(expr)
        else:
            self._editor.clear()
        if expr2 is not None:
            self._sympy_expr2 = expr2
            if expr2:
                self._editor2.model().set_from_text(expr2)
            else:
                self._editor2.clear()
        self._refresh_displays()
        self.changed.emit()


class CartesianRow(FunctionRow):
    """Cartesian function row: y = f(x)."""

    _MODE = "y=f(x)"


class PolarRow(FunctionRow):
    """Polar curve row: r = f(θ)."""

    _MODE = "r=f(t)"


class ParametricRow(FunctionRow):
    """Parametric curve row: (x(t), y(t))."""

    _MODE = "param"

    def _post_build(self, outer_layout: QVBoxLayout) -> None:
        self._display2.setVisible(True)

    def _expand(self) -> None:
        if self._expanded:
            return
        self._expanded = True
        self._editor_wrap.setVisible(True)
        self._editor2_wrap.setVisible(True)
        self.setFixedHeight(_PARAM_ROW_EXPANDED_H)

    def _collapse(self) -> None:
        if not self._expanded:
            return
        self._expanded = False
        self._editor_wrap.setVisible(False)
        self._editor2_wrap.setVisible(False)
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.adjustSize()
        self._refresh_displays()

    def _refresh_displays(self) -> None:
        self._display.set_formula(self._sympy_expr)
        self._display2.set_formula(self._sympy_expr2)
        self._display2.setVisible(True)


_MODE_TO_CLASS = {
    "y=f(x)":     CartesianRow,
    "r=f(t)":     PolarRow,
    "param":      ParametricRow,
    "parametric": ParametricRow,
}


def make_function_row(mode: str, idx: int, parent: QWidget = None) -> FunctionRow:
    """Instantiate the correct FunctionRow subclass for the given mode string."""
    cls = _MODE_TO_CLASS.get(_normalize_mode(mode), CartesianRow)
    return cls(idx=idx, parent=parent)


def function_row_from_state(state: dict, idx: int, parent: QWidget = None) -> FunctionRow:
    """Create and populate a typed FunctionRow from a saved state dict."""
    mode = _normalize_mode(state.get("mode", "y=f(x)"))
    row  = make_function_row(mode, idx, parent)
    row.apply_state(state)
    return row