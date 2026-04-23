import io
import math
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from PyQt5.QtGui import (
    QPainter, QFont, QFontMetricsF, QPen, QColor, QPixmap, QImage
)
from PyQt5.QtCore import Qt, QRectF, QPointF, QSizeF

RENDER_FONT_FAMILY = "Times New Roman"
RENDER_FONT_SIZE = 22
RENDER_ITALIC_FONT_SIZE = 22
RENDER_SMALL_FONT_SIZE = 15
RENDER_TINY_FONT_SIZE = 11
RENDER_OP_FONT_SIZE = 20
FRAC_BAR_THICKNESS = 1.5
FRAC_BAR_MARGIN = 3.0
SQRT_BAR_OVERHANG = 4.0
SQRT_TICK_WIDTH = 8.0
SQRT_TICK_HEIGHT_RATIO = 0.4
SUP_OFFSET_RATIO = 0.45
SUB_OFFSET_RATIO = 0.25
PAREN_SCALE_MARGIN = 4.0
INTEGRAL_WIDTH_RATIO = 0.45
INTEGRAL_HEIGHT_EXTRA = 14.0
SUM_PROD_EXTRA = 10.0
RENDER_BG_COLOR = QColor(255, 255, 255, 0)
RENDER_FG_COLOR = QColor(30, 30, 30)
RENDER_PLACEHOLDER_COLOR = QColor(180, 180, 180)
RENDER_SELECT_COLOR = QColor(180, 210, 255, 160)
RENDER_CURSOR_COLOR = QColor(30, 30, 200)
RENDER_CURSOR_WIDTH = 2
RENDER_PLACEHOLDER_TEXT = "..."


@dataclass
class RenderMetrics:
    width: float = 0.0
    ascent: float = 0.0
    descent: float = 0.0
    @property
    def height(self) -> float:
        return self.ascent + self.descent
    @property
    def baseline(self) -> float:
        return self.ascent


@dataclass
class HitRegion:
    node_id: int = 0
    rect: QRectF = field(default_factory=QRectF)
    cursor_before_x: float = 0.0
    cursor_after_x: float = 0.0
    is_placeholder: bool = False


class FormulaNode:
    _id_counter = 0
    def __init__(self):
        FormulaNode._id_counter += 1
        self.node_id = FormulaNode._id_counter
        self._metrics: Optional[RenderMetrics] = None
        self._pos: QPointF = QPointF(0, 0)
    def measure(self, painter: QPainter) -> RenderMetrics:
        raise NotImplementedError
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        raise NotImplementedError
    def collect_ids(self) -> List[int]:
        return [self.node_id]
    def to_text(self) -> str:
        return ""
    def to_sympy(self) -> str:
        return ""


def _make_font(painter: QPainter, size: int, italic=False, bold=False) -> QFont:
    f = QFont(RENDER_FONT_FAMILY, size)
    f.setItalic(italic)
    f.setBold(bold)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def _fm(painter: QPainter, font: QFont) -> QFontMetricsF:
    painter.setFont(font)
    return QFontMetricsF(font)


class TextNode(FormulaNode):
    def __init__(self, text: str, size: int = RENDER_FONT_SIZE,
                 italic: bool = True, bold: bool = False,
                 color: Optional[QColor] = None):
        super().__init__()
        self.text = text
        self.size = size
        self.italic = italic
        self.bold = bold
        self.color = color or RENDER_FG_COLOR
    def measure(self, painter: QPainter) -> RenderMetrics:
        f = _make_font(painter, self.size, self.italic, self.bold)
        fm = _fm(painter, f)
        w = fm.horizontalAdvance(self.text)
        return RenderMetrics(w, fm.ascent(), fm.descent())
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        f = _make_font(painter, self.size, self.italic, self.bold)
        fm = _fm(painter, f)
        w = fm.horizontalAdvance(self.text)
        m = RenderMetrics(w, fm.ascent(), fm.descent())
        r = QRectF(x, y - m.ascent, w, m.height)
        if self.node_id in selected_ids:
            painter.fillRect(r, RENDER_SELECT_COLOR)
        if cursor_id == self.node_id:
            pen = painter.pen()
            painter.setPen(QPen(RENDER_CURSOR_COLOR, RENDER_CURSOR_WIDTH))
            painter.drawLine(QPointF(x, y - m.ascent), QPointF(x, y + m.descent))
            painter.setPen(pen)
        painter.setFont(f)
        painter.setPen(QPen(self.color))
        painter.drawText(QPointF(x, y), self.text)
        hit_regions.append(HitRegion(self.node_id, r, x, x + w))


class PlaceholderNode(FormulaNode):
    def __init__(self, size: int = RENDER_FONT_SIZE):
        super().__init__()
        self.size = size
    def measure(self, painter: QPainter) -> RenderMetrics:
        f = _make_font(painter, self.size, False)
        fm = _fm(painter, f)
        w = fm.horizontalAdvance(RENDER_PLACEHOLDER_TEXT)
        return RenderMetrics(w, fm.ascent(), fm.descent())
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        f = _make_font(painter, self.size, False)
        fm = _fm(painter, f)
        w = fm.horizontalAdvance(RENDER_PLACEHOLDER_TEXT)
        m = RenderMetrics(w, fm.ascent(), fm.descent())
        r = QRectF(x, y - m.ascent, w, m.height)
        if self.node_id in selected_ids:
            painter.fillRect(r, RENDER_SELECT_COLOR)
        if cursor_id == self.node_id:
            pen = painter.pen()
            painter.setPen(QPen(RENDER_CURSOR_COLOR, RENDER_CURSOR_WIDTH))
            painter.drawLine(QPointF(x, y - m.ascent), QPointF(x, y + m.descent))
            painter.setPen(pen)
        painter.setFont(f)
        painter.setPen(QPen(RENDER_PLACEHOLDER_COLOR))
        painter.drawText(QPointF(x, y), RENDER_PLACEHOLDER_TEXT)
        hit_regions.append(HitRegion(self.node_id, r, x, x + w, True))
    def to_text(self) -> str:
        return "_"
    def to_sympy(self) -> str:
        return "x"


class HSeqNode(FormulaNode):
    def __init__(self, children: List[FormulaNode]):
        super().__init__()
        self.children = children
    def measure(self, painter: QPainter) -> RenderMetrics:
        if not self.children:
            return RenderMetrics(0, 0, 0)
        total_w = 0.0
        max_asc = 0.0
        max_desc = 0.0
        for c in self.children:
            m = c.measure(painter)
            total_w += m.width
            max_asc = max(max_asc, m.ascent)
            max_desc = max(max_desc, m.descent)
        return RenderMetrics(total_w, max_asc, max_desc)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        cx = x
        for c in self.children:
            m = c.measure(painter)
            c.draw(painter, cx, y, hit_regions, selected_ids, cursor_id)
            cx += m.width
    def collect_ids(self) -> List[int]:
        ids = [self.node_id]
        for c in self.children:
            ids.extend(c.collect_ids())
        return ids
    def to_text(self) -> str:
        return "".join(c.to_text() for c in self.children)
    def to_sympy(self) -> str:
        return "".join(c.to_sympy() for c in self.children)


class FracNode(FormulaNode):
    def __init__(self, num: FormulaNode, den: FormulaNode):
        super().__init__()
        self.num = num
        self.den = den
    def measure(self, painter: QPainter) -> RenderMetrics:
        nm = self.num.measure(painter)
        dm = self.den.measure(painter)
        w = max(nm.width, dm.width) + FRAC_BAR_MARGIN * 2
        asc = nm.height + FRAC_BAR_MARGIN + FRAC_BAR_THICKNESS
        desc = dm.height + FRAC_BAR_MARGIN
        return RenderMetrics(w, asc, desc)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        nm = self.num.measure(painter)
        dm = self.den.measure(painter)
        m = self.measure(painter)
        num_x = x + (m.width - nm.width) / 2
        den_x = x + (m.width - dm.width) / 2
        bar_y = y
        num_y = bar_y - FRAC_BAR_MARGIN - nm.descent
        den_y = bar_y + FRAC_BAR_MARGIN + dm.ascent
        pen = painter.pen()
        painter.setPen(QPen(RENDER_FG_COLOR, FRAC_BAR_THICKNESS))
        painter.drawLine(QPointF(x, bar_y), QPointF(x + m.width, bar_y))
        painter.setPen(pen)
        self.num.draw(painter, num_x, num_y, hit_regions, selected_ids, cursor_id)
        self.den.draw(painter, den_x, den_y, hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        return [self.node_id] + self.num.collect_ids() + self.den.collect_ids()
    def to_sympy(self) -> str:
        return f"({self.num.to_sympy()})/({self.den.to_sympy()})"


class SqrtNode(FormulaNode):
    def __init__(self, body: FormulaNode, index: Optional[FormulaNode] = None):
        super().__init__()
        self.body = body
        self.index = index
    def measure(self, painter: QPainter) -> RenderMetrics:
        bm = self.body.measure(painter)
        extra_top = SQRT_BAR_OVERHANG
        return RenderMetrics(
            SQRT_TICK_WIDTH + bm.width + SQRT_BAR_OVERHANG,
            bm.ascent + extra_top,
            bm.descent
        )
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        bm = self.body.measure(painter)
        m = self.measure(painter)
        top_y = y - m.ascent
        body_x = x + SQRT_TICK_WIDTH
        body_y = y
        tick_bot_y = y + bm.descent
        tick_mid_x = x + SQRT_TICK_WIDTH * 0.4
        tick_top_x = x + SQRT_TICK_WIDTH
        pen = painter.pen()
        painter.setPen(QPen(RENDER_FG_COLOR, FRAC_BAR_THICKNESS))
        pts = [
            QPointF(x, y - bm.height * SQRT_TICK_HEIGHT_RATIO),
            QPointF(tick_mid_x, tick_bot_y),
            QPointF(tick_top_x, top_y),
            QPointF(x + m.width - SQRT_BAR_OVERHANG / 2, top_y),
        ]
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i+1])
        painter.setPen(pen)
        self.body.draw(painter, body_x, body_y, hit_regions, selected_ids, cursor_id)
        if self.index:
            idx_m = self.index.measure(painter)
            self.index.draw(painter, x, top_y + idx_m.ascent / 2,
                            hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        ids = [self.node_id] + self.body.collect_ids()
        if self.index:
            ids.extend(self.index.collect_ids())
        return ids
    def to_sympy(self) -> str:
        if self.index:
            return f"({self.body.to_sympy()})**({self.index.to_sympy()})"
        return f"sqrt({self.body.to_sympy()})"


class PowerNode(FormulaNode):
    def __init__(self, base: FormulaNode, exp: FormulaNode):
        super().__init__()
        self.base = base
        self.exp = exp
    def measure(self, painter: QPainter) -> RenderMetrics:
        bm = self.base.measure(painter)
        em = self.exp.measure(painter)
        asc = bm.ascent + em.height * SUP_OFFSET_RATIO
        return RenderMetrics(bm.width + em.width, asc, bm.descent)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        bm = self.base.measure(painter)
        em = self.exp.measure(painter)
        self.base.draw(painter, x, y, hit_regions, selected_ids, cursor_id)
        exp_y = y - bm.ascent + em.ascent * (1 - SUP_OFFSET_RATIO)
        self.exp.draw(painter, x + bm.width, exp_y, hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        return [self.node_id] + self.base.collect_ids() + self.exp.collect_ids()
    def to_sympy(self) -> str:
        return f"({self.base.to_sympy()})**({self.exp.to_sympy()})"


class SubNode(FormulaNode):
    def __init__(self, base: FormulaNode, sub: FormulaNode):
        super().__init__()
        self.base = base
        self.sub = sub
    def measure(self, painter: QPainter) -> RenderMetrics:
        bm = self.base.measure(painter)
        sm = self.sub.measure(painter)
        desc = bm.descent + sm.height * SUB_OFFSET_RATIO
        return RenderMetrics(bm.width + sm.width, bm.ascent, desc)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        bm = self.base.measure(painter)
        sm = self.sub.measure(painter)
        self.base.draw(painter, x, y, hit_regions, selected_ids, cursor_id)
        sub_y = y + bm.descent + sm.ascent * SUB_OFFSET_RATIO
        self.sub.draw(painter, x + bm.width, sub_y, hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        return [self.node_id] + self.base.collect_ids() + self.sub.collect_ids()
    def to_sympy(self) -> str:
        return self.base.to_sympy()


class ParenNode(FormulaNode):
    def __init__(self, body: FormulaNode, left: str = "(", right: str = ")"):
        super().__init__()
        self.body = body
        self.left = left
        self.right = right
    def measure(self, painter: QPainter) -> RenderMetrics:
        bm = self.body.measure(painter)
        f = _make_font(painter, RENDER_FONT_SIZE, False)
        fm = _fm(painter, f)
        pw = fm.horizontalAdvance("(")
        return RenderMetrics(bm.width + pw * 2, bm.ascent + PAREN_SCALE_MARGIN,
                             bm.descent + PAREN_SCALE_MARGIN)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        bm = self.body.measure(painter)
        m = self.measure(painter)
        f = _make_font(painter, RENDER_FONT_SIZE, False)
        fm = _fm(painter, f)
        pw = fm.horizontalAdvance("(")
        scale = m.height / (fm.ascent() + fm.descent())
        painter.save()
        painter.translate(x, y - bm.ascent / 2 + bm.descent / 2)
        painter.scale(1.0, scale)
        painter.setFont(f)
        painter.setPen(QPen(RENDER_FG_COLOR))
        painter.drawText(QPointF(0, 0), self.left)
        painter.restore()
        self.body.draw(painter, x + pw, y, hit_regions, selected_ids, cursor_id)
        painter.save()
        painter.translate(x + pw + bm.width, y - bm.ascent / 2 + bm.descent / 2)
        painter.scale(1.0, scale)
        painter.setFont(f)
        painter.setPen(QPen(RENDER_FG_COLOR))
        painter.drawText(QPointF(0, 0), self.right)
        painter.restore()
    def collect_ids(self) -> List[int]:
        return [self.node_id] + self.body.collect_ids()
    def to_sympy(self) -> str:
        return f"({self.body.to_sympy()})"


class IntegralNode(FormulaNode):
    def __init__(self, body: FormulaNode, var: FormulaNode,
                 lower: Optional[FormulaNode] = None,
                 upper: Optional[FormulaNode] = None):
        super().__init__()
        self.body = body
        self.var = var
        self.lower = lower
        self.upper = upper
    def _sign_metrics(self, painter: QPainter) -> Tuple[float, float, float]:
        f = _make_font(painter, RENDER_FONT_SIZE + 10, False)
        fm = _fm(painter, f)
        w = fm.horizontalAdvance("S") * INTEGRAL_WIDTH_RATIO + 4
        h = fm.height() + INTEGRAL_HEIGHT_EXTRA
        return w, h / 2 + 4, h / 2
    def measure(self, painter: QPainter) -> RenderMetrics:
        sw, sa, sd = self._sign_metrics(painter)
        bm = self.body.measure(painter)
        vm = self.var.measure(painter)
        dx_w = vm.width
        lim_w = 0.0
        if self.lower:
            lim_w = max(lim_w, self.lower.measure(painter).width)
        if self.upper:
            lim_w = max(lim_w, self.upper.measure(painter).width)
        total_w = sw + lim_w + bm.width + 6 + dx_w + 10
        return RenderMetrics(total_w, max(sa, bm.ascent), max(sd, bm.descent))
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        sw, sa, sd = self._sign_metrics(painter)
        bm = self.body.measure(painter)
        lim_w = 0.0
        if self.lower:
            lim_w = max(lim_w, self.lower.measure(painter).width)
        if self.upper:
            lim_w = max(lim_w, self.upper.measure(painter).width)
        f_big = _make_font(painter, RENDER_FONT_SIZE + 10, False)
        painter.setFont(f_big)
        painter.setPen(QPen(RENDER_FG_COLOR))
        painter.drawText(QPointF(x, y + sa * 0.3), "\u222B")
        cx = x + sw + lim_w
        if self.lower:
            lm = self.lower.measure(painter)
            self.lower.draw(painter, x + sw, y + sd * 0.6, hit_regions, selected_ids, cursor_id)
        if self.upper:
            um = self.upper.measure(painter)
            self.upper.draw(painter, x + sw, y - sa * 0.7, hit_regions, selected_ids, cursor_id)
        self.body.draw(painter, cx, y, hit_regions, selected_ids, cursor_id)
        dx_x = cx + bm.width + 4
        f_dx = _make_font(painter, RENDER_FONT_SIZE, False)
        painter.setFont(f_dx)
        painter.setPen(QPen(RENDER_FG_COLOR))
        painter.drawText(QPointF(dx_x, y), "d")
        vm = self.var.measure(painter)
        self.var.draw(painter, dx_x + _fm(painter, f_dx).horizontalAdvance("d"), y,
                      hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        ids = [self.node_id] + self.body.collect_ids() + self.var.collect_ids()
        if self.lower:
            ids.extend(self.lower.collect_ids())
        if self.upper:
            ids.extend(self.upper.collect_ids())
        return ids
    def to_sympy(self) -> str:
        v = self.var.to_sympy()
        b = self.body.to_sympy()
        if self.lower and self.upper:
            return f"integrate({b}, ({v}, {self.lower.to_sympy()}, {self.upper.to_sympy()}))"
        return f"integrate({b}, {v})"


class SumProdNode(FormulaNode):
    def __init__(self, kind: str, body: FormulaNode,
                 var: Optional[FormulaNode] = None,
                 lower: Optional[FormulaNode] = None,
                 upper: Optional[FormulaNode] = None):
        super().__init__()
        self.kind = kind
        self.body = body
        self.var = var
        self.lower = lower
        self.upper = upper
        self._sym = "\u03A3" if kind == "sum" else "\u03A0"
    def measure(self, painter: QPainter) -> RenderMetrics:
        bm = self.body.measure(painter)
        f = _make_font(painter, RENDER_FONT_SIZE + 6, False, True)
        fm = _fm(painter, f)
        sw = fm.horizontalAdvance(self._sym) + 4
        lim_w = 0.0
        if self.lower:
            lim_w = max(lim_w, self.lower.measure(painter).width)
        if self.upper:
            lim_w = max(lim_w, self.upper.measure(painter).width)
        w = max(sw, lim_w) + bm.width + 4
        lim_extra = SUM_PROD_EXTRA
        return RenderMetrics(w, bm.ascent + lim_extra, bm.descent + lim_extra)
    def draw(self, painter: QPainter, x: float, y: float,
             hit_regions: List[HitRegion], selected_ids: set, cursor_id: Optional[int]):
        bm = self.body.measure(painter)
        f = _make_font(painter, RENDER_FONT_SIZE + 6, False, True)
        fm = _fm(painter, f)
        sw = fm.horizontalAdvance(self._sym) + 4
        lim_w = 0.0
        if self.lower:
            lim_w = max(lim_w, self.lower.measure(painter).width)
        if self.upper:
            lim_w = max(lim_w, self.upper.measure(painter).width)
        sym_w = max(sw, lim_w)
        painter.setFont(f)
        painter.setPen(QPen(RENDER_FG_COLOR))
        painter.drawText(QPointF(x + (sym_w - sw) / 2, y), self._sym)
        if self.lower:
            lm = self.lower.measure(painter)
            self.lower.draw(painter, x + (sym_w - lm.width) / 2,
                            y + bm.descent + SUM_PROD_EXTRA * 0.7,
                            hit_regions, selected_ids, cursor_id)
        if self.upper:
            um = self.upper.measure(painter)
            self.upper.draw(painter, x + (sym_w - um.width) / 2,
                            y - bm.ascent - SUM_PROD_EXTRA * 0.3,
                            hit_regions, selected_ids, cursor_id)
        self.body.draw(painter, x + sym_w + 4, y, hit_regions, selected_ids, cursor_id)
    def collect_ids(self) -> List[int]:
        ids = [self.node_id] + self.body.collect_ids()
        if self.var:
            ids.extend(self.var.collect_ids())
        if self.lower:
            ids.extend(self.lower.collect_ids())
        if self.upper:
            ids.extend(self.upper.collect_ids())
        return ids
    def to_sympy(self) -> str:
        b = self.body.to_sympy()
        v = self.var.to_sympy() if self.var else "k"
        if self.lower and self.upper:
            fn = "Sum" if self.kind == "sum" else "Product"
            return f"{fn}({b}, ({v}, {self.lower.to_sympy()}, {self.upper.to_sympy()}))"
        return b
