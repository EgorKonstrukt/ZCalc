from __future__ import annotations
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from pyqt5_math_widget import MathView, FormulaModel
from pyqt5_math_widget._renderer import SeqNode

_VIEW_ZOOM = 0.6
_MIN_HEIGHT = 36


class MathDisplay(MathView):
    """Read-only formula display; renders sympy expressions as structured math."""
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.set_transparent(True)
        self.set_zoom(_VIEW_ZOOM)
        self.set_padding(4, 2)
        self.setMinimumHeight(_MIN_HEIGHT)
        self.setMinimumWidth(40)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setCursor(Qt.PointingHandCursor)

    def set_formula(self, sympy_expr: str, color: str = "#111111") -> None:
        """Render expression string as structured math formula."""
        self.set_foreground(QColor(color))
        if not sympy_expr:
            self.set_model(FormulaModel())
            return
        try:
            from sympy_to_nodes import expr_str_to_node
            node = expr_str_to_node(sympy_expr)
            if node is not None:
                model = FormulaModel()
                model._root = node if isinstance(node, SeqNode) else SeqNode([node])
                self.set_model(model)
                return
        except Exception:
            pass
        model = FormulaModel()
        model.set_from_text(sympy_expr)
        self.set_model(model)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)