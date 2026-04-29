from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtCore import Qt

from pyqt5_chart_widget import ChartWidget, _FunctionItem
from math_engine import (
    linspace, sample_y, sample_polar, sample_parametric,
    numerical_deriv, numerical_deriv2, numerical_integral, filter_none,
    _eval_np_batch, _finalize_y, _NP_OK
)
from config import Config

if TYPE_CHECKING:
    from core.panels import FunctionPanel

_POLAR_THETA_START = 0.0
_POLAR_THETA_END = 2 * math.pi
_EMPTY_XY: Tuple[List, List] = ([], [])


class _LiveFn:
    """Mutable callable backing a _FunctionItem; updates in-place without recreating the item."""

    __slots__ = ("_expr", "_extra")

    def __init__(self):
        self._expr: str = ""
        self._extra: dict = {}

    def update(self, expr: str, extra: dict) -> bool:
        """Return True if state changed."""
        changed = (expr != self._expr) or (extra != self._extra)
        if changed:
            self._expr = expr
            self._extra = dict(extra)
        return changed

    def __call__(self, xs: List[float]) -> List[Optional[float]]:
        if not self._expr:
            return [None] * len(xs)
        try:
            if _NP_OK:
                x_arr = np.asarray(xs, dtype=np.float64)
                arr = _eval_np_batch(self._expr, x_arr, self._extra)
                return _finalize_y(arr)
            return sample_y(self._expr, xs, self._extra)
        except Exception:
            return [None] * len(xs)


class _RowState:
    """Bundles a _FunctionItem and its _LiveFn for one function row."""

    __slots__ = ("item", "live_fn")

    def __init__(self, item: _FunctionItem, live_fn: _LiveFn):
        self.item = item
        self.live_fn = live_fn


class Plotter:
    """Evaluates all function rows and writes results into the ChartWidget."""

    _DERIV_COLORS = {"_d": "#9b59b6", "_d2": "#e74c3c", "_int": "#2ecc71"}
    _DERIV_LABELS = {"_d": "f'(x)", "_d2": "f''(x)", "_int": "integral f dx"}

    def __init__(self, chart: ChartWidget, panel: "FunctionPanel"):
        self._chart = chart
        self._panel = panel
        self._cfg = Config()
        self._is_animating = False
        self._row_states: Dict[int, _RowState] = {}

    def set_animating(self, val: bool):
        self._is_animating = val

    def _resolution(self) -> float:
        return getattr(self._cfg, "fn_resolution", 1.5)

    def _get_or_create_state(self, row_id: int, row) -> _RowState:
        if row_id not in self._row_states:
            live_fn = _LiveFn()
            pen = QPen(QColor(row.color), row.get_width())
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            item = _FunctionItem(
                self._chart, live_fn, pen, label="", resolution=self._resolution(),
            )
            self._chart._functions.append(item)
            self._row_states[row_id] = _RowState(item, live_fn)
        return self._row_states[row_id]

    def _remove_state(self, row_id: int):
        state = self._row_states.pop(row_id, None)
        if state is not None:
            self._chart.removeItem(state.item)

    def sync_fn_items(self):
        """Remove stale _RowState entries whose rows no longer exist in the panel."""
        live_ids = {id(row) for row in self._panel.func_rows}
        for rid in list(self._row_states):
            if rid not in live_ids:
                self._remove_state(rid)

    def replot(self):
        """Evaluate all function rows and update the chart."""
        s = self._panel.settings
        x_min, x_max = s.xmin(), s.xmax()
        if x_min >= x_max:
            return None
        any_anim = any(w._animating for w in self._panel._param_widgets.values())
        n = self._cfg.anim_samples if any_anim else s.samples()
        t_min, t_max = s.tmin(), s.tmax()
        infinite = s.infinite()
        x_vals = linspace(x_min, x_max, n)
        t_vals = linspace(t_min, t_max, n)
        extra = self._panel.get_params()
        self.sync_fn_items()
        total = 0
        for i, row in enumerate(self._panel.func_rows):
            expr = row.get_expr()
            mode = row.get_mode()
            label = f"f{i + 1}"
            row_id = id(row)
            if infinite and mode == "y=f(x)":
                state = self._get_or_create_state(row_id, row)
                if state.live_fn.update(expr, extra):
                    state.item.invalidateCache()
                    state.item._expr = expr
                    state.item._extra = dict(extra)
                    state.item._adaptive = True
                state.item.label = label
                state.item.pen.setColor(QColor(row.color))
                state.item.pen.setWidth(row.get_width())
                state.item.setVisible(row.is_enabled())
                if row.chart_line is not None:
                    row.chart_line.setData(xs=[], ys=[])
                continue
            self._remove_state(row_id)
            line = row.chart_line
            if line is None:
                continue
            if not expr:
                line.setData(xs=[], ys=[])
                continue
            try:
                cx, cy = self._eval_mode(mode, expr, row, x_vals, t_vals, extra)
                line.setLabel(label + ("" if mode == "y=f(x)" else (" (r)" if mode == "r=f(t)" else " (p)")))
                line.pen.setColor(QColor(row.color))
                line.pen.setWidth(row.get_width())
                line.setData(xs=list(cx), ys=list(cy))
                line.setVisible(row.is_enabled())
                total += len(cx)
            except Exception:
                line.setData(xs=[], ys=[])
        self._replot_derivs(x_vals, extra)
        return total, x_min, x_max, len(self._panel.func_rows)

    @staticmethod
    def _eval_mode(mode: str, expr: str, row, x_vals, t_vals, extra: dict) -> Tuple[List, List]:
        if mode == "y=f(x)":
            ys = sample_y(expr, x_vals, extra)
            return filter_none(x_vals, ys)
        if mode == "r=f(t)":
            theta = linspace(_POLAR_THETA_START, _POLAR_THETA_END, len(x_vals))
            return sample_polar(expr, theta, extra)
        if mode == "param":
            expr2 = row.get_expr2()
            if not expr2:
                return _EMPTY_XY
            return sample_parametric(expr, expr2, t_vals, extra)
        return _EMPTY_XY

    def _replot_derivs(self, x_vals, extra: dict):
        """Recompute derivative/integral overlay lines using finite sampling."""
        dp = self._panel.deriv_panel
        idx = dp.source_idx()
        rows = self._panel.func_rows
        dl = self._panel.get_deriv_lines()
        active_keys: set = set()
        if 0 <= idx < len(rows):
            row = rows[idx]
            expr = row.get_expr()
            if row.get_mode() == "y=f(x)" and expr:
                shows = {
                    "_d":   dp.show_d1(),
                    "_d2":  dp.show_d2(),
                    "_int": dp.show_ig(),
                }
                _samplers = {
                    "_d":   numerical_deriv,
                    "_d2":  numerical_deriv2,
                    "_int": numerical_integral,
                }
                rid = id(row)
                for sfx, visible in shows.items():
                    k = f"{rid}{sfx}"
                    if not visible:
                        continue
                    active_keys.add(k)
                    if k not in dl:
                        dl[k] = self._chart.plot(
                            label=self._DERIV_LABELS[sfx],
                            color=self._DERIV_COLORS[sfx],
                            width=1,
                        )
                    ys = _samplers[sfx](expr, x_vals, extra)
                    cx, cy = filter_none(x_vals, ys)
                    dl[k].setData(xs=list(cx), ys=list(cy))
                    dl[k].setVisible(True)
        for k in list(dl.keys()):
            if k not in active_keys:
                dl[k].setData(xs=[], ys=[])