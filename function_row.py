from PyQt5.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QColorDialog, QComboBox,
    QSpinBox, QSizePolicy, QFrame, QWidget, QApplication
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from constants import COLORS
from latex_label import LatexLabel
from math_engine import expr_to_latex
from expr_item import ExprItem, ITEM_HEIGHT
from formula_input import FormulaInput
from formula_editor import FormulaEditorPanel
_MODE_ITEMS = ["y=f(x)", "r=f(t)", "param"]
_EDITOR_HEIGHT = 240
_ROW_COLLAPSED_H = ITEM_HEIGHT
_ROW_EXPANDED_H = ITEM_HEIGHT + _EDITOR_HEIGHT
def _normalize_mode(mode: str) -> str:
    if mode == "parametric":
        return "param"
    return mode if mode in _MODE_ITEMS else "y=f(x)"
class FunctionRow(ExprItem):
    changed = pyqtSignal()
    removed = pyqtSignal(object)
    _id_counter = 0
    def __init__(self, idx: int, parent=None):
        super().__init__(parent)
        FunctionRow._id_counter += 1
        self._uid = FunctionRow._id_counter
        self.color = COLORS[idx % len(COLORS)]
        self.chart_line = None
        self._enabled = True
        self._mode = "y=f(x)"
        self._expanded = False
        self.setFixedHeight(_ROW_COLLAPSED_H)
        self._build_ui()
        QApplication.instance().focusChanged.connect(self._on_app_focus_changed)
    def _build_ui(self):
        outer_v = QVBoxLayout(self)
        outer_v.setContentsMargins(0, 0, 0, 0)
        outer_v.setSpacing(0)
        top_row = QWidget()
        top_row.setFixedHeight(_ROW_COLLAPSED_H)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        self._color_bar = QFrame()
        self._color_bar.setFixedWidth(6)
        self._color_bar.setStyleSheet(f"background:{self.color};border-radius:3px;")
        self._color_bar.mousePressEvent = lambda e: self._pick_color()
        self._color_bar.setCursor(Qt.PointingHandCursor)
        top_layout.addWidget(self._color_bar)
        inner = QHBoxLayout()
        inner.setContentsMargins(6, 2, 4, 2)
        inner.setSpacing(4)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(_MODE_ITEMS)
        self._mode_combo.setFixedWidth(72)
        self._mode_combo.setStyleSheet(
            "QComboBox{border:none;background:#f7f7f7;font-size:11px;padding:2px;}"
        )
        self._mode_combo.currentTextChanged.connect(self._on_mode_change)
        self._input = FormulaInput()
        self._input.setPlaceholderText("f(x)  e.g. sin(x)")
        self._input.textChanged.connect(self._on_expr_change)
        self._input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._input.focused_in.connect(lambda: self._on_input_focused(self._input))
        self._input2 = FormulaInput()
        self._input2.setPlaceholderText("y(t)")
        self._input2.textChanged.connect(self._on_expr_change)
        self._input2.setFixedWidth(130)
        self._input2.setVisible(False)
        self._input2.focused_in.connect(lambda: self._on_input_focused(self._input2))
        self._latex = LatexLabel(self)
        self._latex.setFixedHeight(ITEM_HEIGHT - 12)
        self._latex.setMinimumWidth(80)
        self._latex.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._latex.setVisible(False)
        self._latex.mousePressEvent = lambda e: self._show_input_for_edit()
        self._latex.setCursor(Qt.PointingHandCursor)
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 6)
        self._width_spin.setValue(2)
        self._width_spin.setFixedWidth(36)
        self._width_spin.setStyleSheet("QSpinBox{border:none;font-size:11px;}")
        self._width_spin.valueChanged.connect(self.changed.emit)
        rm = self._mk_remove_btn()
        for w in (self._mode_combo, self._input, self._input2, self._latex,
                  self._width_spin, rm):
            inner.addWidget(w)
        top_layout.addLayout(inner)
        outer_v.addWidget(top_row)
        self._editor_panel = FormulaEditorPanel(self._input)
        self._editor_panel.setVisible(False)
        outer_v.addWidget(self._editor_panel)
    def _on_input_focused(self, inp: FormulaInput):
        self._editor_panel.set_target(inp)
        self._expand()
    def _on_app_focus_changed(self, old, new):
        if not self._expanded or new is None:
            return
        w = new
        while w is not None:
            if w is self:
                return
            w = w.parent()
        self._collapse()
    def _expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._latex.setVisible(False)
        self._input.setVisible(True)
        if self._mode == "param":
            self._input2.setVisible(True)
        self._editor_panel.setVisible(True)
        self.setFixedHeight(_ROW_EXPANDED_H)
    def _collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._editor_panel.setVisible(False)
        self.setFixedHeight(_ROW_COLLAPSED_H)
        self._refresh_latex()
    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self.color), self)
        if c.isValid():
            self.color = c.name()
            self._color_bar.setStyleSheet(f"background:{self.color};border-radius:3px;")
            if self.chart_line:
                self.chart_line.pen.setColor(QColor(self.color))
            self.changed.emit()
    def _on_mode_change(self, mode: str):
        self._mode = mode
        is_param = (mode == "param")
        self._input.setPlaceholderText(
            "x(t)" if is_param else ("r(t)  e.g. cos(3*t)" if mode == "r=f(t)" else "f(x)  e.g. sin(x)")
        )
        if self._expanded:
            self._input2.setVisible(is_param)
        self._refresh_latex()
        self.changed.emit()
    def _on_expr_change(self):
        if not self._expanded:
            self._refresh_latex()
        self.changed.emit()
    def _refresh_latex(self):
        if self._expanded:
            return
        expr = self._input.text().strip()
        if not expr:
            self._latex.setVisible(False)
            self._input.setVisible(True)
            if self._mode == "param":
                self._input2.setVisible(True)
            return
        try:
            if self._mode == "param":
                expr2 = self._input2.text().strip()
                lx = expr_to_latex(expr)
                if expr2:
                    lx = lx + r",\;" + expr_to_latex(expr2)
                self._latex.set_formula(lx, color="#111111")
            else:
                self._latex.set_formula(expr_to_latex(expr), color="#111111")
            self._latex.setVisible(True)
            self._input.setVisible(False)
            self._input2.setVisible(False)
        except Exception:
            self._latex.setVisible(False)
            self._input.setVisible(True)
            if self._mode == "param":
                self._input2.setVisible(True)
    def _show_input_for_edit(self):
        self._latex.setVisible(False)
        self._input.setVisible(True)
        if self._mode == "param":
            self._input2.setVisible(True)
        self._input.setFocus()
    def get_expr(self) -> str:
        return self._input.text().strip()
    def get_expr2(self) -> str:
        return self._input2.text().strip()
    def get_mode(self) -> str:
        return self._mode
    def is_enabled(self) -> bool:
        return self._enabled
    def get_width(self) -> int:
        return self._width_spin.value()
    def to_state(self) -> dict:
        return {
            "expr": self.get_expr(), "expr2": self.get_expr2(),
            "mode": self._mode, "color": self.color,
            "width": self.get_width(), "enabled": self._enabled,
            "type": "function",
        }
    def apply_state(self, state: dict):
        self._input.blockSignals(True)
        self._input2.blockSignals(True)
        self._mode_combo.blockSignals(True)
        self._input.setText(state.get("expr", ""))
        self._input2.setText(state.get("expr2", ""))
        mode = _normalize_mode(state.get("mode", "y=f(x)"))
        self._mode_combo.setCurrentText(mode)
        self._mode = mode
        self.color = state.get("color", self.color)
        self._color_bar.setStyleSheet(f"background:{self.color};border-radius:3px;")
        self._width_spin.setValue(state.get("width", 2))
        self._enabled = state.get("enabled", True)
        self._input.blockSignals(False)
        self._input2.blockSignals(False)
        self._mode_combo.blockSignals(False)
        self._refresh_latex()
        self.changed.emit()
    def set_expr(self, expr: str, mode: str = None, expr2: str = None):
        self._input.blockSignals(True)
        self._input2.blockSignals(True)
        self._mode_combo.blockSignals(True)
        self._input.setText(expr)
        if expr2:
            self._input2.setText(expr2)
        if mode:
            m = _normalize_mode(mode)
            self._mode_combo.setCurrentText(m)
            self._mode = m
        self._input.blockSignals(False)
        self._input2.blockSignals(False)
        self._mode_combo.blockSignals(False)
        self._refresh_latex()
        self.changed.emit()