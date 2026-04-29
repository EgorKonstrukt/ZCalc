from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy
from PyQt5.QtCore import pyqtSignal
ITEM_HEIGHT = 42
REMOVE_BTN_SIZE = 22
class ExprItem(QWidget):
    changed = pyqtSignal()
    removed = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    def _mk_remove_btn(self):
        b = QPushButton("X")
        b.setFixedSize(REMOVE_BTN_SIZE, REMOVE_BTN_SIZE)
        b.setStyleSheet(
            "QPushButton{color:#8c2f2b;}"
            "QPushButton:hover{color:#e74c3c;}"
        )
        b.clicked.connect(lambda: self.removed.emit(self))
        return b
    def to_state(self) -> dict:
        return {}
    def apply_state(self, state: dict):
        pass