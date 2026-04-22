import math
from typing import TYPE_CHECKING
from PyQt5.QtGui import QColor
from pyqt5_chart_widget import ChartWidget
from math_engine import (
    linspace, sample_y, sample_polar, sample_parametric,
    numerical_deriv, numerical_deriv2, numerical_integral, filter_none
)
from constants import INFINITE_MARGIN
from config import Config
if TYPE_CHECKING:
    from panels import FunctionPanel
_POLAR_THETA_START = 0.0
_POLAR_THETA_END = 2 * math.pi
class Plotter:
    _DERIV_COLORS = {"_d": "#9b59b6", "_d2": "#e74c3c", "_int": "#2ecc71"}
    _DERIV_LABELS = {"_d": "f'(x)", "_d2": "f''(x)", "_int": "int f dx"}
    def __init__(self, chart: ChartWidget, panel: "FunctionPanel"):
        self._chart = chart
        self._panel = panel
        self._cfg = Config()
        self._is_animating = False
    def set_animating(self, val: bool):
        self._is_animating = val
    def replot(self):
        s = self._panel.settings
        x_min, x_max = s.xmin(), s.xmax()
        if x_min >= x_max:
            return None
        any_anim = any(w._animating for w in self._panel._param_widgets.values())
        n = self._cfg.anim_samples if any_anim else s.samples()
        t_min, t_max = s.tmin(), s.tmax()
        if s.infinite():
            vx0 = self._chart.vx0
            vx1 = self._chart.vx1
            if isinstance(vx0, float) and isinstance(vx1, float) and vx0 < vx1:
                span = vx1 - vx0
                x_min = vx0 - span * INFINITE_MARGIN
                x_max = vx1 + span * INFINITE_MARGIN
        x_vals = linspace(x_min, x_max, n)
        t_vals = linspace(t_min, t_max, n)
        extra = self._panel.get_params()
        total = 0
        for i, row in enumerate(self._panel.func_rows):
            expr = row.get_expr()
            mode = row.get_mode()
            label = f"f{i+1}"
            line = row.chart_line
            if line is None:
                continue
            if not expr:
                line.setData(xs=[], ys=[])
                continue
            try:
                if mode == "y=f(x)":
                    ys = sample_y(expr, x_vals, extra)
                    cx, cy = filter_none(x_vals, ys)
                    line.setLabel(label)
                    line.pen.setColor(QColor(row.color))
                    line.pen.setWidth(row.get_width())
                    line.setData(xs=list(cx), ys=list(cy))
                    total += len(cx)
                elif mode == "r=f(t)":
                    theta = linspace(_POLAR_THETA_START, _POLAR_THETA_END, n)
                    px, py = sample_polar(expr, theta, extra)
                    line.setLabel(label + " (r)")
                    line.pen.setColor(QColor(row.color))
                    line.pen.setWidth(row.get_width())
                    line.setData(xs=px, ys=py)
                    total += len(px)
                elif mode == "param":
                    expr2 = row.get_expr2()
                    if not expr2:
                        line.setData(xs=[], ys=[])
                        continue
                    px, py = sample_parametric(expr, expr2, t_vals, extra)
                    line.setLabel(label + " (p)")
                    line.pen.setColor(QColor(row.color))
                    line.pen.setWidth(row.get_width())
                    line.setData(xs=px, ys=py)
                    total += len(px)
                line.setVisible(row.is_enabled())
            except Exception:
                line.setData(xs=[], ys=[])
        self._replot_derivs(x_vals, extra)
        return total, x_min, x_max, len(self._panel.func_rows)
    def _replot_derivs(self, x_vals, extra):
        dp = self._panel.deriv_panel
        idx = dp.source_idx()
        rows = self._panel.func_rows
        dl = self._panel.get_deriv_lines()
        active_keys = set()
        if 0 <= idx < len(rows):
            row = rows[idx]
            expr = row.get_expr()
            if row.get_mode() == "y=f(x)" and expr:
                shows = {"_d": dp.show_d1(), "_d2": dp.show_d2(), "_int": dp.show_ig()}
                for sfx, visible in shows.items():
                    k = f"{id(row)}{sfx}"
                    if visible:
                        active_keys.add(k)
                        if k not in dl:
                            dl[k] = self._chart.plot(
                                label=self._DERIV_LABELS[sfx],
                                color=self._DERIV_COLORS[sfx],
                                width=1)
                        if sfx == "_d":
                            ys = numerical_deriv(expr, x_vals, extra)
                        elif sfx == "_d2":
                            ys = numerical_deriv2(expr, x_vals, extra)
                        else:
                            ys = numerical_integral(expr, x_vals, extra)
                        cx, cy = filter_none(x_vals, ys)
                        dl[k].setData(xs=list(cx), ys=list(cy))
                        dl[k].setVisible(True)
        for k in list(dl.keys()):
            if k not in active_keys:
                dl[k].setData(xs=[], ys=[])