from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QFrame, QSizePolicy, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QFontMetrics
_BTN_H = 32
_BTN_W = 38
_BTN_SMALL_W = 32
_SECTION_STYLE = (
    "QLabel{font-size:9px;color:#999;font-weight:bold;"
    "letter-spacing:1px;padding:2px 0 1px 2px;}"
)
_BTN_BASE = (
    "QPushButton{"
    "border:1px solid #e0e0e0;border-radius:4px;"
    "background:#fafafa;font-size:12px;"
    "padding:0px;color:#222;"
    "}"
    "QPushButton:hover{background:#e8f4fd;border-color:#3498db;color:#1a6fa3;}"
    "QPushButton:pressed{background:#d0eaf9;}"
)
_BTN_FN = (
    "QPushButton{"
    "border:1px solid #e0e0e0;border-radius:4px;"
    "background:#f5f0ff;font-size:11px;"
    "padding:0px;color:#5b2d8e;"
    "}"
    "QPushButton:hover{background:#e8deff;border-color:#8e44ad;}"
    "QPushButton:pressed{background:#d5c5ff;}"
)
_BTN_OP = (
    "QPushButton{"
    "border:1px solid #e0e0e0;border-radius:4px;"
    "background:#f0fff4;font-size:12px;"
    "padding:0px;color:#1a6b3a;"
    "}"
    "QPushButton:hover{background:#d4f5e0;border-color:#27ae60;}"
    "QPushButton:pressed{background:#bde8cc;}"
)
_TEMPLATES = [
    ("Basic", [
        ("x^n",      "**()",      1,   _BTN_BASE),
        ("x^2",      "**2",       0,   _BTN_BASE),
        ("x^3",      "**3",       0,   _BTN_BASE),
        ("sqrt",     "sqrt()",    1,   _BTN_BASE),
        ("cbrt",     "**(1/3)",   0,   _BTN_BASE),
        ("x/y",      "/()",       1,   _BTN_BASE),
        ("(  )",     "()",        1,   _BTN_BASE),
        ("|x|",      "abs()",     1,   _BTN_BASE),
        ("pi",       "pi",        0,   _BTN_OP),
        ("e",        "e",         0,   _BTN_OP),
        ("inf",      "inf",       0,   _BTN_OP),
    ]),
    ("Trig", [
        ("sin",      "sin()",     1,   _BTN_FN),
        ("cos",      "cos()",     1,   _BTN_FN),
        ("tan",      "tan()",     1,   _BTN_FN),
        ("asin",     "asin()",    1,   _BTN_FN),
        ("acos",     "acos()",    1,   _BTN_FN),
        ("atan",     "atan()",    1,   _BTN_FN),
        ("sinh",     "sinh()",    1,   _BTN_FN),
        ("cosh",     "cosh()",    1,   _BTN_FN),
        ("tanh",     "tanh()",    1,   _BTN_FN),
    ]),
    ("Log / Exp", [
        ("exp",      "exp()",     1,   _BTN_FN),
        ("ln",       "log()",     1,   _BTN_FN),
        ("log2",     "log2()",    1,   _BTN_FN),
        ("log10",    "log10()",   1,   _BTN_FN),
        ("e^x",      "exp()",     1,   _BTN_BASE),
        ("10^x",     "10**()",    1,   _BTN_BASE),
    ]),
    ("Rounding", [
        ("floor",    "floor()",   1,   _BTN_FN),
        ("ceil",     "ceil()",    1,   _BTN_FN),
        ("round",    "round()",   1,   _BTN_FN),
        ("frac",     "frac()",    1,   _BTN_FN),
        ("sign",     "sign()",    1,   _BTN_FN),
    ]),
    ("Special", [
        ("sinc",     "sinc()",    1,   _BTN_FN),
        ("gauss",    "gaussian()",1,   _BTN_FN),
        ("sigmoid",  "sigmoid()", 1,   _BTN_FN),
        ("step",     "step()",    1,   _BTN_FN),
        ("rect",     "rect()",    1,   _BTN_FN),
        ("tri",      "tri()",     1,   _BTN_FN),
        ("saw",      "sawtooth()",1,   _BTN_FN),
        ("square",   "square()",  1,   _BTN_FN),
    ]),
    ("Multi-arg", [
        ("clamp",    "clamp(,,)", 3,   _BTN_FN),
        ("mod",      "mod(,)",    2,   _BTN_FN),
        ("hypot",    "hypot(,)",  2,   _BTN_FN),
        ("atan2",    "atan2(,)",  2,   _BTN_FN),
        ("lerp",     "lerp(,,)",  3,   _BTN_FN),
        ("n!",       "factorial()",1,  _BTN_FN),
    ]),
]
_QUICK_KEYS = [
    ("7", "7"), ("8", "8"), ("9", "9"),
    ("4", "4"), ("5", "5"), ("6", "6"),
    ("1", "1"), ("2", "2"), ("3", "3"),
    ("0", "0"), (".", "."), (",", ","),
    ("+", "+"), ("-", "-"), ("*", "*"),
    ("(", "("), (")", ")"), ("^", "^"),
    ("x", "x"), ("t", "t"), ("pi", "pi"),
]
class _MathBtn(QPushButton):
    def __init__(self, label: str, style: str, w: int = _BTN_W, h: int = _BTN_H, parent=None):
        super().__init__(label, parent)
        self.setFixedSize(w, h)
        self.setStyleSheet(style)
        self.setFocusPolicy(Qt.NoFocus)
class FormulaEditorPanel(QWidget):
    insert_text = pyqtSignal(str, int)
    def __init__(self, target_input=None, parent=None):
        super().__init__(parent)
        self._target = target_input
        self._build_ui()
    def set_target(self, inp):
        self._target = inp
    def _build_ui(self):
        self.setStyleSheet(
            "FormulaEditorPanel{"
            "background:#f8f8f8;"
            "border-top:1px solid #ddd;"
            "}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 2)
        root.setSpacing(3)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        scroll.setMaximumHeight(220)
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        for section_name, items in _TEMPLATES:
            lbl = QLabel(section_name.upper())
            lbl.setStyleSheet(_SECTION_STYLE)
            cl.addWidget(lbl)
            row_wrap = QWidget()
            row_wrap.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row_wrap)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(3)
            for label, tmpl, offset, style in items:
                btn = _MathBtn(label, style)
                btn.clicked.connect(lambda _, t=tmpl, o=offset: self._do_insert(t, o))
                rl.addWidget(btn)
            rl.addStretch()
            cl.addWidget(row_wrap)
        scroll.setWidget(content)
        root.addWidget(scroll)
    def _do_insert(self, template: str, cursor_back: int):
        if self._target is not None:
            self._target.insert_template(template, cursor_back)
        self.insert_text.emit(template, cursor_back)