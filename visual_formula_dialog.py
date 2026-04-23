from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QWidget, QScrollArea, QFrame, QSizePolicy, QGroupBox,
    QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QFont, QKeyEvent, QMouseEvent,
    QWheelEvent, QFontMetricsF
)
from formula_renderer import (
    RENDER_BG_COLOR, RENDER_FG_COLOR, RENDER_CURSOR_COLOR,
    RENDER_CURSOR_WIDTH, HitRegion
)
from formula_model import FormulaModel

_CANVAS_PAD_X = 20
_CANVAS_PAD_Y = 16
_CANVAS_MIN_H = 70
_CANVAS_BG = QColor(255, 255, 255)
_CANVAS_BORDER = QColor(200, 210, 230)
_CANVAS_BORDER_FOCUS = QColor(52, 152, 219)
_CURSOR_BLINK_MS = 530
_BTN = (
    "QPushButton{border:1px solid #ddd;border-radius:4px;background:#fafafa;"
    "font-size:12px;padding:3px 6px;color:#222;min-width:26px;}"
    "QPushButton:hover{background:#e8f4fd;border-color:#3498db;color:#1a6fa3;}"
    "QPushButton:pressed{background:#d0eaf9;}"
)
_BTN_OP = (
    "QPushButton{border:1px solid #e0e0e0;border-radius:4px;background:#f5f0ff;"
    "font-size:12px;padding:3px 6px;color:#5b2d8e;min-width:26px;}"
    "QPushButton:hover{background:#e8deff;border-color:#8e44ad;}"
    "QPushButton:pressed{background:#d5c5ff;}"
)
_BTN_FN = (
    "QPushButton{border:1px solid #e0e0e0;border-radius:4px;background:#f0fff4;"
    "font-size:11px;padding:3px 5px;color:#1a6b3a;min-width:26px;}"
    "QPushButton:hover{background:#d4f5e0;border-color:#27ae60;}"
    "QPushButton:pressed{background:#bde8cc;}"
)
_BTN_ACCEPT = (
    "QPushButton{background:#3498db;color:white;border:none;border-radius:5px;"
    "font-size:12px;padding:6px 20px;}"
    "QPushButton:hover{background:#2980b9;}"
    "QPushButton:pressed{background:#2471a3;}"
)
_BTN_CANCEL = (
    "QPushButton{background:#f0f0f0;color:#333;border:1px solid #ddd;border-radius:5px;"
    "font-size:12px;padding:6px 18px;}"
    "QPushButton:hover{background:#e0e0e0;}"
)
_GRP = (
    "QGroupBox{font-size:10px;font-weight:bold;color:#777;"
    "border:1px solid #e8e8e8;border-radius:5px;margin-top:6px;"
    "padding:4px 4px 4px 4px;}"
    "QGroupBox::title{subcontrol-origin:margin;left:6px;padding:0 3px;}"
)
_SYMPY_OUT = (
    "QTextEdit{border:1px solid #ddd;border-radius:4px;background:#f8f8f8;"
    "font-family:monospace;font-size:10px;color:#555;padding:3px;}"
)


class _FormulaCanvas(QWidget):
    formula_changed = pyqtSignal()
    def __init__(self, model: FormulaModel, parent=None):
        super().__init__(parent)
        self._model = model
        self._hit_regions: list = []
        self._focused = False
        self._cursor_visible = True
        self._zoom = 1.0
        self._blink = QTimer(self)
        self._blink.setInterval(_CURSOR_BLINK_MS)
        self._blink.timeout.connect(self._blink_tick)
        self.setMinimumHeight(_CANVAS_MIN_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.IBeamCursor)
    def _blink_tick(self):
        self._cursor_visible = not self._cursor_visible
        self.update()
    def focusInEvent(self, e):
        self._focused = True
        self._cursor_visible = True
        self._blink.start()
        self.update()
    def focusOutEvent(self, e):
        self._focused = False
        self._blink.stop()
        self._cursor_visible = False
        self.update()
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, _CANVAS_BG)
        border_c = _CANVAS_BORDER_FOCUS if self._focused else _CANVAS_BORDER
        p.setPen(QPen(border_c, 1.5))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)
        p.save()
        p.scale(self._zoom, self._zoom)
        self._hit_regions = []
        root = self._model.get_root()
        m = root.measure(p)
        cx = _CANVAS_PAD_X / self._zoom
        cy = _CANVAS_PAD_Y / self._zoom + m.ascent
        cid = self._model.get_cursor_id() if (self._focused and self._cursor_visible) else None
        root.draw(p, cx, cy, self._hit_regions, self._model.get_selected_ids(), cid)
        new_h = max(_CANVAS_MIN_H, int((m.height + _CANVAS_PAD_Y * 2) * self._zoom) + 4)
        p.restore()
        p.end()
        if self.height() != new_h:
            self.setFixedHeight(new_h)
    def mousePressEvent(self, e: QMouseEvent):
        self.setFocus()
        lx = e.x() / self._zoom
        ly = e.y() / self._zoom
        best, best_d = None, float("inf")
        for hr in self._hit_regions:
            if hr.rect.contains(QPointF(lx, ly)):
                cx = (hr.cursor_before_x + hr.cursor_after_x) / 2
                d = abs(lx - cx)
                if d < best_d:
                    best_d = d
                    best = hr
        if best:
            self._model.set_cursor_by_id(best.node_id)
            self.update()
    def keyPressEvent(self, e: QKeyEvent):
        key = e.key()
        mods = e.modifiers()
        text = e.text()
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
            self.update()
            return
        if key == Qt.Key_Right:
            self._model.move_cursor_right()
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
    def wheelEvent(self, e: QWheelEvent):
        if e.modifiers() & Qt.ControlModifier:
            d = e.angleDelta().y()
            self._zoom = max(0.5, min(3.0, self._zoom * (1.1 if d > 0 else 1 / 1.1)))
            self.update()


def _btn(label: str, style: str, tip: str = "") -> QPushButton:
    b = QPushButton(label)
    b.setStyleSheet(style)
    b.setFocusPolicy(Qt.NoFocus)
    b.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    if tip:
        b.setToolTip(tip)
    return b


def _grp(title: str) -> QGroupBox:
    g = QGroupBox(title)
    g.setStyleSheet(_GRP)
    return g


class VisualFormulaDialog(QDialog):
    def __init__(self, initial_expr: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visual Formula Editor")
        self.setMinimumWidth(720)
        self.setModal(True)
        self.setStyleSheet("QDialog{background:#fafafa;}")
        self._model = FormulaModel()
        self._result_expr: str = initial_expr
        if initial_expr:
            for ch in initial_expr:
                if ch.isprintable():
                    self._model.insert_text(ch)
        self._build_ui()
        self._update_sympy()
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)
        root.setSpacing(8)
        self._canvas = _FormulaCanvas(self._model)
        self._canvas.formula_changed.connect(self._on_changed)
        self._canvas.setMinimumHeight(80)
        root.addWidget(self._canvas)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(240)
        tb = QWidget()
        tl = QVBoxLayout(tb)
        tl.setContentsMargins(2, 2, 2, 2)
        tl.setSpacing(5)
        struct_grp = _grp("Structure")
        sl = QHBoxLayout(struct_grp)
        sl.setContentsMargins(4, 8, 4, 4)
        sl.setSpacing(3)
        for lbl, action, style, tip in [
            ("a/b",  "frac",     _BTN,    "Fraction"),
            ("\u221Ax", "sqrt",  _BTN,    "Square root"),
            ("x^n",  "power",    _BTN,    "Power / Superscript"),
            ("x_n",  "sub",      _BTN,    "Subscript"),
            ("(x)",  "parens",   _BTN,    "Parentheses"),
            ("\u222B", "integral", _BTN_OP, "Integral with limits"),
            ("\u03A3", "sum",    _BTN_OP, "Sum"),
            ("\u03A0", "prod",   _BTN_OP, "Product"),
        ]:
            b = _btn(lbl, style, tip)
            b.clicked.connect(lambda _, a=action: self._struct(a))
            sl.addWidget(b)
        sl.addStretch()
        tl.addWidget(struct_grp)
        ops_grp = _grp("Operators & Relations")
        ol = QHBoxLayout(ops_grp)
        ol.setContentsMargins(4, 8, 4, 4)
        ol.setSpacing(3)
        for sym, op in [
            ("+","+"), ("\u2212","-"), ("\u00B7","*"), ("\u00D7","times"),
            ("=","="), ("\u2260","!="), ("\u2264","<="), ("\u2265",">="),
            ("\u00B1","pm"), ("\u2248","approx"),
            ("\u2202","partial"), ("\u2207","nabla"),
            ("\u2208","in"), ("\u2282","subset"),
        ]:
            b = _btn(sym, _BTN, op)
            b.clicked.connect(lambda _, o=op: self._op(o))
            ol.addWidget(b)
        ol.addStretch()
        tl.addWidget(ops_grp)
        greek_grp = _grp("Greek Letters")
        gl = QHBoxLayout(greek_grp)
        gl.setContentsMargins(4, 8, 4, 4)
        gl.setSpacing(3)
        for sym, name in [
            ("\u03B1","alpha"), ("\u03B2","beta"), ("\u03B3","gamma"),
            ("\u03B4","delta"), ("\u03B5","epsilon"), ("\u03B8","theta"),
            ("\u03BB","lambda"), ("\u03BC","mu"), ("\u03BD","nu"),
            ("\u03C0","pi"), ("\u03C1","rho"), ("\u03C3","sigma"),
            ("\u03C4","tau"), ("\u03C6","phi"), ("\u03C8","psi"),
            ("\u03C9","omega"), ("\u03A3","Sigma"), ("\u03A0","Pi"),
            ("\u0394","Delta"), ("\u03A9","Omega"), ("\u221E","inf"),
        ]:
            b = _btn(sym, _BTN_OP, name)
            b.clicked.connect(lambda _, n=name: self._greek(n))
            gl.addWidget(b)
        gl.addStretch()
        tl.addWidget(greek_grp)
        fn_grp = _grp("Functions")
        fl = QHBoxLayout(fn_grp)
        fl.setContentsMargins(4, 8, 4, 4)
        fl.setSpacing(3)
        for fn in ["sin","cos","tan","arcsin","arccos","arctan",
                   "sinh","cosh","tanh","log","ln","exp","lim","max","min","gcd"]:
            b = _btn(fn, _BTN_FN, fn)
            b.clicked.connect(lambda _, f=fn: self._func(f))
            fl.addWidget(b)
        fl.addStretch()
        tl.addWidget(fn_grp)
        edit_grp = _grp("Edit")
        el = QHBoxLayout(edit_grp)
        el.setContentsMargins(4, 8, 4, 4)
        el.setSpacing(3)
        for lbl, fn, tip in [
            ("\u232B Del",  self._del,        "Backspace"),
            ("Clear",       self._clear,       "Clear all"),
            ("\u2190",      self._left,        "Move cursor left"),
            ("\u2192",      self._right,       "Move cursor right"),
            ("Undo",        self._undo,        "Ctrl+Z"),
            ("Redo",        self._redo,        "Ctrl+Y"),
        ]:
            b = _btn(lbl, _BTN, tip)
            b.clicked.connect(fn)
            el.addWidget(b)
        el.addStretch()
        tl.addWidget(edit_grp)
        scroll.setWidget(tb)
        root.addWidget(scroll)
        out_grp = _grp("SymPy Expression")
        oul = QVBoxLayout(out_grp)
        oul.setContentsMargins(4, 8, 4, 4)
        self._sympy_out = QTextEdit()
        self._sympy_out.setReadOnly(True)
        self._sympy_out.setStyleSheet(_SYMPY_OUT)
        self._sympy_out.setMaximumHeight(60)
        oul.addWidget(self._sympy_out)
        root.addWidget(out_grp)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel_btn = _btn("Cancel", _BTN_CANCEL)
        cancel_btn.clicked.connect(self.reject)
        accept_btn = _btn("Insert Formula", _BTN_ACCEPT)
        accept_btn.clicked.connect(self._accept)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(accept_btn)
        root.addLayout(btn_row)
    def _focus(self):
        self._canvas.setFocus()
    def _struct(self, action: str):
        m = {
            "frac": self._model.insert_frac, "sqrt": self._model.insert_sqrt,
            "power": self._model.insert_power, "sub": self._model.insert_subscript,
            "parens": self._model.insert_parens, "integral": self._model.insert_integral,
            "sum": self._model.insert_sum, "prod": self._model.insert_product,
        }
        if action in m:
            m[action]()
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _op(self, op: str):
        self._model.insert_operator(op)
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _greek(self, name: str):
        self._model.insert_greek(name)
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _func(self, name: str):
        self._model.insert_func(name)
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _del(self):
        self._model.delete_at_cursor()
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _clear(self):
        self._model.clear()
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _left(self):
        self._model.move_cursor_left()
        self._canvas.update()
        self._focus()
    def _right(self):
        self._model.move_cursor_right()
        self._canvas.update()
        self._focus()
    def _undo(self):
        self._model.undo()
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _redo(self):
        self._model.redo()
        self._canvas.update()
        self._update_sympy()
        self._focus()
    def _on_changed(self):
        self._update_sympy()
    def _update_sympy(self):
        raw = self._model.to_sympy_str()
        self._result_expr = raw
        try:
            import sympy
            expr = sympy.sympify(raw, evaluate=True)
            simplified = str(expr)
            self._sympy_out.setPlainText(f"{simplified}")
        except Exception:
            self._sympy_out.setPlainText(raw)
    def _accept(self):
        self._result_expr = self._model.to_sympy_str()
        self.accept()
    def get_result(self) -> str:
        return self._result_expr