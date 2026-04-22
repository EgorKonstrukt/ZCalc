from PyQt5.QtWidgets import QLineEdit, QCompleter
from PyQt5.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt5.QtGui import QFocusEvent, QKeyEvent
_AUTO_CLOSE = {"(": ")", "[": "]", "{": "}"}
_COMPLETIONS = [
    "sin(", "cos(", "tan(", "asin(", "acos(", "atan(", "atan2(",
    "sinh(", "cosh(", "tanh(",
    "sqrt(", "exp(", "log(", "log2(", "log10(",
    "abs(", "floor(", "ceil(", "round(",
    "sign(", "frac(", "clamp(", "mod(", "hypot(",
    "sigmoid(", "sinc(", "gaussian(", "lerp(",
    "sawtooth(", "square(", "step(", "rect(", "tri(",
    "factorial(", "degrees(", "radians(",
    "pi", "e", "inf",
]
class FormulaInput(QLineEdit):
    focused_in = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_completer()
        self.setStyleSheet(
            "QLineEdit{"
            "border:none;background:transparent;"
            "font-size:14px;font-family:monospace;"
            "padding:2px 4px;color:#1a1a2e;"
            "selection-background-color:#3498db40;"
            "}"
        )
    def _setup_completer(self):
        model = QStringListModel(_COMPLETIONS)
        c = QCompleter(model, self)
        c.setCaseSensitivity(Qt.CaseInsensitive)
        c.setCompletionMode(QCompleter.PopupCompletion)
        c.activated.connect(self._on_complete)
        self.setCompleter(c)
    def _on_complete(self, text: str):
        cur = self.text()
        pos = self.cursorPosition()
        start = pos - 1
        while start > 0 and (cur[start - 1].isalnum() or cur[start - 1] == "_"):
            start -= 1
        new_text = cur[:start] + text + cur[pos:]
        self.setText(new_text)
        self.setCursorPosition(start + len(text))
    def focusInEvent(self, event: QFocusEvent):
        super().focusInEvent(event)
        self.focused_in.emit()
    def keyPressEvent(self, e: QKeyEvent):
        key = e.key()
        text = e.text()
        pos = self.cursorPosition()
        cur = self.text()
        sel_start = self.selectionStart()
        sel_len = len(self.selectedText())
        if text in _AUTO_CLOSE:
            close = _AUTO_CLOSE[text]
            if sel_len > 0:
                selected = self.selectedText()
                new_text = cur[:sel_start] + text + selected + close + cur[sel_start + sel_len:]
                self.setText(new_text)
                self.setCursorPosition(sel_start + 1 + len(selected))
                return
            super().keyPressEvent(e)
            self._insert_at(close)
            self.setCursorPosition(self.cursorPosition() - 1)
            return
        if text == ")" and pos < len(cur) and cur[pos] == ")":
            self.setCursorPosition(pos + 1)
            return
        if text == "^":
            if sel_len > 0:
                selected = self.selectedText()
                new_text = cur[:sel_start] + selected + "**(" + ")" + cur[sel_start + sel_len:]
                self.setText(new_text)
                self.setCursorPosition(sel_start + len(selected) + 3)
            else:
                self._insert_at("**(")
                self._insert_at(")")
                self.setCursorPosition(self.cursorPosition() - 1)
            return
        super().keyPressEvent(e)
    def _insert_at(self, text: str):
        pos = self.cursorPosition()
        cur = self.text()
        self.setText(cur[:pos] + text + cur[pos:])
        self.setCursorPosition(pos + len(text))
    def insert_template(self, template: str, cursor_back: int):
        pos = self.cursorPosition()
        cur = self.text()
        sel_start = self.selectionStart()
        sel = self.selectedText()
        if sel:
            filled = template.replace("{}", sel, 1)
            remaining = filled.replace("{}", "", 1)
            new_text = cur[:sel_start] + remaining + cur[sel_start + len(sel):]
            self.setText(new_text)
            new_pos = sel_start + len(remaining) - cursor_back if cursor_back else sel_start + len(remaining)
            self.setCursorPosition(new_pos)
        else:
            new_text = cur[:pos] + template + cur[pos:]
            self.setText(new_text)
            self.setCursorPosition(pos + len(template) - cursor_back)
        self.setFocus()