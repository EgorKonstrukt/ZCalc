from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QSizePolicy, QLineEdit,
    QGroupBox, QToolButton, QSplitter, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF, QPointF, QTimer
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QFont, QKeyEvent, QMouseEvent,
    QWheelEvent, QFontMetricsF
)
from formula_renderer import (
    HitRegion, RENDER_BG_COLOR, RENDER_FG_COLOR, RENDER_CURSOR_COLOR,
    RENDER_CURSOR_WIDTH, RENDER_FG_COLOR
)
from formula_model import FormulaModel

_CANVAS_PAD_X = 20
_CANVAS_PAD_Y = 16
_CANVAS_MIN_H = 80
_CANVAS_BG = QColor(255, 255, 255)
_CANVAS_BORDER = QColor(200, 210, 230)
_CANVAS_BORDER_FOCUS = QColor(52, 152, 219)
_CURSOR_BLINK_MS = 530

_BTN_STYLE = (
    "QPushButton{border:1px solid #ddd;border-radius:4px;background:#fafafa;"
    "font-size:12px;padding:3px 6px;color:#222;min-width:28px;}"
    "QPushButton:hover{background:#e8f4fd;border-color:#3498db;color:#1a6fa3;}"
    "QPushButton:pressed{background:#d0eaf9;}"
)
_BTN_OP_STYLE = (
    "QPushButton{border:1px solid #e0e0e0;border-radius:4px;background:#f5f0ff;"
    "font-size:12px;padding:3px 6px;color:#5b2d8e;min-width:28px;}"
    "QPushButton:hover{background:#e8deff;border-color:#8e44ad;}"
    "QPushButton:pressed{background:#d5c5ff;}"
)
_BTN_FN_STYLE = (
    "QPushButton{border:1px solid #e0e0e0;border-radius:4px;background:#f0fff4;"
    "font-size:11px;padding:3px 5px;color:#1a6b3a;min-width:28px;}"
    "QPushButton:hover{background:#d4f5e0;border-color:#27ae60;}"
    "QPushButton:pressed{background:#bde8cc;}"
)
_GROUP_STYLE = (
    "QGroupBox{font-size:10px;font-weight:bold;color:#777;"
    "border:1px solid #e8e8e8;border-radius:5px;margin-top:6px;"
    "padding:4px 4px 4px 4px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:6px;padding:0 3px;}"
)
_SYMPY_STYLE = (
    "QTextEdit{border:1px solid #ddd;border-radius:4px;background:#f8f8f8;"
    "font-family:monospace;font-size:11px;color:#444;padding:4px;}"
)


class FormulaCanvas(QWidget):
    cursor_moved = pyqtSignal()
    formula_changed = pyqtSignal()
    def __init__(self, model: FormulaModel, parent=None):
        super().__init__(parent)
        self._model = model
        self._hit_regions: list = []
        self._focused = False
        self._cursor_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(_CURSOR_BLINK_MS)
        self._blink_timer.timeout.connect(self._blink)
        self._zoom = 1.0
        self.setMinimumHeight(_CANVAS_MIN_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setCursor(Qt.IBeamCursor)
    def _blink(self):
        self._cursor_visible = not self._cursor_visible
        self.update()
    def focusInEvent(self, event):
        self._focused = True
        self._cursor_visible = True
        self._blink_timer.start()
        self.update()
    def focusOutEvent(self, event):
        self._focused = False
        self._blink_timer.stop()
        self._cursor_visible = False
        self.update()
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, _CANVAS_BG)
        border_color = _CANVAS_BORDER_FOCUS if self._focused else _CANVAS_BORDER
        p.setPen(QPen(border_color, 1.5))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)
        p.save()
        p.scale(self._zoom, self._zoom)
        self._hit_regions = []
        root = self._model.get_root()
        m = root.measure(p)
        cx = _CANVAS_PAD_X / self._zoom
        cy = _CANVAS_PAD_Y / self._zoom + m.ascent
        cursor_id = self._model.get_cursor_id() if (self._focused and self._cursor_visible) else None
        root.draw(p, cx, cy, self._hit_regions, self._model.get_selected_ids(), cursor_id)
        new_h = max(_CANVAS_MIN_H, int((m.height + _CANVAS_PAD_Y * 2) * self._zoom) + 4)
        p.restore()
        p.end()
        if self.height() != new_h:
            self.setFixedHeight(new_h)
    def mousePressEvent(self, event: QMouseEvent):
        self.setFocus()
        lx = event.x() / self._zoom
        ly = event.y() / self._zoom
        best = None
        best_dist = float("inf")
        for hr in self._hit_regions:
            if hr.rect.contains(QPointF(lx, ly)):
                cx = (hr.cursor_before_x + hr.cursor_after_x) / 2
                dist = abs(lx - cx)
                if dist < best_dist:
                    best_dist = dist
                    best = hr
        if best:
            self._model.set_cursor_by_id(best.node_id)
            self.cursor_moved.emit()
            self.update()
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        mods = event.modifiers()
        text = event.text()
        if mods & Qt.ControlModifier:
            if key == Qt.Key_Z:
                self._model.undo()
            elif key == Qt.Key_Y:
                self._model.redo()
            self.formula_changed.emit()
            self.update()
            return
        if key == Qt.Key_Left:
            self._model.move_cursor_left()
            self.cursor_moved.emit()
            self.update()
            return
        if key == Qt.Key_Right:
            self._model.move_cursor_right()
            self.cursor_moved.emit()
            self.update()
            return
        if key in (Qt.Key_Backspace, Qt.Key_Delete):
            self._model.delete_at_cursor()
            self.formula_changed.emit()
            self.update()
            return
        if text and text.isprintable():
            self._model.insert_text(text)
            self.formula_changed.emit()
            self.update()
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom = min(3.0, self._zoom * 1.1)
            else:
                self._zoom = max(0.4, self._zoom / 1.1)
            self.update()
    def set_zoom(self, zoom: float):
        self._zoom = max(0.4, min(3.0, zoom))
        self.update()


class _Btn(QPushButton):
    def __init__(self, label: str, style: str, tooltip: str = "", parent=None):
        super().__init__(label, parent)
        self.setStyleSheet(style)
        self.setFocusPolicy(Qt.NoFocus)
        if tooltip:
            self.setToolTip(tooltip)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


def _grp(title: str) -> QGroupBox:
    g = QGroupBox(title)
    g.setStyleSheet(_GROUP_STYLE)
    return g


def _wrap_row(*widgets) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(3)
    for w in widgets:
        if w is None:
            row.addStretch()
        else:
            row.addWidget(w)
    return row


class FormulaEditorWidget(QWidget):
    formula_changed = pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = FormulaModel()
        self._build_ui()
    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)
        self._canvas = FormulaCanvas(self._model)
        self._canvas.formula_changed.connect(self._on_formula_changed)
        root_layout.addWidget(self._canvas)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(280)
        toolbar_widget = QWidget()
        tbl = QVBoxLayout(toolbar_widget)
        tbl.setContentsMargins(4, 4, 4, 4)
        tbl.setSpacing(6)
        struct_grp = _grp("Structure")
        sl = QHBoxLayout(struct_grp)
        sl.setContentsMargins(4, 8, 4, 4)
        sl.setSpacing(3)
        struct_btns = [
            ("a/b", "frac", _BTN_STYLE, "Fraction"),
            ("\u221Ax", "sqrt", _BTN_STYLE, "Square root"),
            ("x^n", "power", _BTN_STYLE, "Superscript / Power"),
            ("x_n", "sub", _BTN_STYLE, "Subscript"),
            ("(x)", "parens", _BTN_STYLE, "Parentheses"),
            ("\u222B", "integral", _BTN_OP_STYLE, "Integral"),
            ("\u03A3", "sum", _BTN_OP_STYLE, "Sum"),
            ("\u03A0", "prod", _BTN_OP_STYLE, "Product"),
        ]
        for lbl, action, style, tip in struct_btns:
            b = _Btn(lbl, style, tip)
            b.clicked.connect(lambda _, a=action: self._struct_action(a))
            sl.addWidget(b)
        sl.addStretch()
        tbl.addWidget(struct_grp)
        ops_grp = _grp("Operators & Relations")
        ol = QHBoxLayout(ops_grp)
        ol.setContentsMargins(4, 8, 4, 4)
        ol.setSpacing(3)
        ops = [
            ("+", "+"), ("\u2212", "-"), ("\u00B7", "*"), ("\u00D7", "times"),
            ("\u00F7", "div"), ("=", "="), ("\u2260", "!="),
            ("\u2264", "<="), ("\u2265", ">="), ("\u00B1", "pm"),
            ("\u2248", "approx"), ("\u2202", "partial"), ("\u2207", "nabla"),
            ("\u2208", "in"), ("\u2282", "subset"),
        ]
        for lbl, op in ops:
            b = _Btn(lbl, _BTN_STYLE, op)
            b.clicked.connect(lambda _, o=op: self._insert_op(o))
            ol.addWidget(b)
        ol.addStretch()
        tbl.addWidget(ops_grp)
        greek_grp = _grp("Greek Letters")
        gl = QHBoxLayout(greek_grp)
        gl.setContentsMargins(4, 8, 4, 4)
        gl.setSpacing(3)
        greeks = [
            ("\u03B1","alpha"), ("\u03B2","beta"), ("\u03B3","gamma"),
            ("\u03B4","delta"), ("\u03B5","epsilon"), ("\u03B8","theta"),
            ("\u03BB","lambda"), ("\u03BC","mu"), ("\u03BD","nu"),
            ("\u03C0","pi"), ("\u03C1","rho"), ("\u03C3","sigma"),
            ("\u03C4","tau"), ("\u03C6","phi"), ("\u03C8","psi"),
            ("\u03C9","omega"), ("\u03A3","Sigma"), ("\u03A0","Pi"),
            ("\u0394","Delta"), ("\u03A9","Omega"), ("\u221E","inf"),
        ]
        for sym, name in greeks:
            b = _Btn(sym, _BTN_OP_STYLE, name)
            b.clicked.connect(lambda _, n=name: self._insert_greek(n))
            gl.addWidget(b)
        gl.addStretch()
        tbl.addWidget(greek_grp)
        fn_grp = _grp("Functions")
        fl = QHBoxLayout(fn_grp)
        fl.setContentsMargins(4, 8, 4, 4)
        fl.setSpacing(3)
        funcs = ["sin", "cos", "tan", "arcsin", "arccos", "arctan",
                 "sinh", "cosh", "tanh", "log", "ln", "exp", "lim",
                 "max", "min", "gcd"]
        for fn in funcs:
            b = _Btn(fn, _BTN_FN_STYLE, fn)
            b.clicked.connect(lambda _, f=fn: self._insert_func(f))
            fl.addWidget(b)
        fl.addStretch()
        tbl.addWidget(fn_grp)
        ctrl_grp = _grp("Edit")
        cl = QHBoxLayout(ctrl_grp)
        cl.setContentsMargins(4, 8, 4, 4)
        cl.setSpacing(3)
        ctrl_btns = [
            ("\u232B Del", self._delete, _BTN_STYLE, "Delete at cursor"),
            ("\u21E4 Clear", self._clear, _BTN_STYLE, "Clear formula"),
            ("\u2190", self._move_left, _BTN_STYLE, "Move cursor left"),
            ("\u2192", self._move_right, _BTN_STYLE, "Move cursor right"),
            ("Undo", self._undo, _BTN_STYLE, "Undo (Ctrl+Z)"),
            ("Redo", self._redo, _BTN_STYLE, "Redo (Ctrl+Y)"),
        ]
        for lbl, fn, style, tip in ctrl_btns:
            b = _Btn(lbl, style, tip)
            b.clicked.connect(fn)
            cl.addWidget(b)
        cl.addStretch()
        tbl.addWidget(ctrl_grp)
        scroll.setWidget(toolbar_widget)
        root_layout.addWidget(scroll)
        out_grp = _grp("SymPy Output")
        out_l = QVBoxLayout(out_grp)
        out_l.setContentsMargins(4, 8, 4, 4)
        self._sympy_output = QTextEdit()
        self._sympy_output.setReadOnly(True)
        self._sympy_output.setStyleSheet(_SYMPY_STYLE)
        self._sympy_output.setMaximumHeight(72)
        out_l.addWidget(self._sympy_output)
        root_layout.addWidget(out_grp)
        self._update_sympy()
    def _focus_canvas(self):
        self._canvas.setFocus()
    def _struct_action(self, action: str):
        m = {
            "frac": self._model.insert_frac,
            "sqrt": self._model.insert_sqrt,
            "power": self._model.insert_power,
            "sub": self._model.insert_subscript,
            "parens": self._model.insert_parens,
            "integral": self._model.insert_integral,
            "sum": self._model.insert_sum,
            "prod": self._model.insert_product,
        }
        if action in m:
            m[action]()
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _insert_op(self, op: str):
        self._model.insert_operator(op)
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _insert_greek(self, name: str):
        self._model.insert_greek(name)
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _insert_func(self, name: str):
        self._model.insert_func(name)
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _delete(self):
        self._model.delete_at_cursor()
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _clear(self):
        self._model.clear()
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _move_left(self):
        self._model.move_cursor_left()
        self._canvas.update()
        self._focus_canvas()
    def _move_right(self):
        self._model.move_cursor_right()
        self._canvas.update()
        self._focus_canvas()
    def _undo(self):
        self._model.undo()
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _redo(self):
        self._model.redo()
        self._canvas.update()
        self._update_sympy()
        self._focus_canvas()
    def _on_formula_changed(self):
        self._update_sympy()
        self.formula_changed.emit(self._model.to_sympy_str())
    def _update_sympy(self):
        raw = self._model.to_sympy_str()
        simplified = raw
        try:
            import sympy
            expr = sympy.sympify(raw, evaluate=True)
            simplified = str(expr)
            pretty = sympy.pretty(expr, use_unicode=True)
            self._sympy_output.setPlainText(f"sympy: {simplified}\n\n{pretty}")
        except Exception:
            self._sympy_output.setPlainText(f"raw: {raw}")
        self.formula_changed.emit(raw)
    def get_sympy_str(self) -> str:
        return self._model.to_sympy_str()
    def get_model(self) -> FormulaModel:
        return self._model
