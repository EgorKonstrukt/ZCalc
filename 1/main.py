import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QStatusBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from formula_editor_widget import FormulaEditorWidget

_WINDOW_TITLE = "Formula Editor"
_WINDOW_W = 860
_WINDOW_H = 640
_HINT_STYLE = (
    "QLabel{color:#888;font-size:11px;"
    "padding:4px 8px;border-top:1px solid #eee;}"
)
_TITLE_STYLE = (
    "QLabel{font-size:16px;font-weight:bold;color:#1a1a2e;"
    "padding:8px 4px 4px 4px;}"
)
_MAIN_STYLE = "QMainWindow{background:#f5f6fa;}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self.resize(_WINDOW_W, _WINDOW_H)
        self.setStyleSheet(_MAIN_STYLE)
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)
        title = QLabel("Mathematical Formula Editor")
        title.setStyleSheet(_TITLE_STYLE)
        layout.addWidget(title)
        self._editor = FormulaEditorWidget()
        self._editor.formula_changed.connect(self._on_change)
        layout.addWidget(self._editor)
        layout.addStretch()
        hint = QLabel(
            "Click formula canvas and type  |  "
            "Ctrl+Scroll = zoom  |  "
            "Arrow keys = navigate  |  "
            "Backspace = delete  |  "
            "Ctrl+Z/Y = undo/redo"
        )
        hint.setStyleSheet(_HINT_STYLE)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        self.setCentralWidget(central)
        sb = QStatusBar()
        sb.showMessage("Ready")
        self.setStatusBar(sb)
    def _on_change(self, sympy_str: str):
        self.statusBar().showMessage(f"Formula: {sympy_str}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    f = QFont("Segoe UI", 10)
    app.setFont(f)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
