import io
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt

_mpl_ok: bool = False
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _plt
    _mpl_ok = True
except ImportError:
    pass

_RENDER_DPI = 130
_RENDER_FONTSIZE = 12
_RENDER_FIGSIZE = (6.0, 0.45)
_MAX_LABEL_HEIGHT = 28


def _render_latex(latex: str, color: str = "#222222") -> QPixmap:
    if not _mpl_ok:
        return QPixmap()
    try:
        fig = _plt.figure(figsize=_RENDER_FIGSIZE)
        fig.patch.set_alpha(0.0)
        fig.text(0.01, 0.5, f"${latex}$",
                 fontsize=_RENDER_FONTSIZE,
                 color=color,
                 va="center",
                 ha="left")
        buf = io.BytesIO()
        fig.savefig(buf,
                    format="png",
                    bbox_inches="tight",
                    pad_inches=0.03,
                    transparent=True,
                    dpi=_RENDER_DPI)
        _plt.close(fig)
        buf.seek(0)
        data = buf.read()
        img = QImage.fromData(data)
        if img.isNull():
            return QPixmap()
        px = QPixmap.fromImage(img)
        if px.height() > _MAX_LABEL_HEIGHT:
            px = px.scaledToHeight(_MAX_LABEL_HEIGHT, Qt.SmoothTransformation)
        return px
    except Exception:
        return QPixmap()


class LatexLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._latex = ""
        self._color = "#222222"
        self.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.setMinimumHeight(_MAX_LABEL_HEIGHT)
        self.setScaledContents(False)

    def set_formula(self, latex: str, color: str = "#222222"):
        self._latex = latex
        self._color = color
        if not latex:
            self.clear()
            self.setText("")
            return
        px = _render_latex(latex, color=color)
        if px.isNull():
            self.setPixmap(QPixmap())
            self.setText(f"  {latex}")
        else:
            self.setPixmap(px)
            self.setToolTip(f"${latex}$")