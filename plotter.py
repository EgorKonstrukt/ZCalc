from __future__ import annotations

import math
from typing import TYPE_CHECKING, Dict, List, Optional

from PyQt5.QtGui import QColor, QPen
from PyQt5.QtCore import Qt

from pyqt5_chart_widget import ChartWidget, _FunctionItem
from math_engine import (
    linspace, sample_y, sample_polar, sample_parametric,
    numerical_deriv, numerical_deriv2, numerical_integral, filter_none
)
from config import Config

if TYPE_CHECKING:
    from panels import FunctionPanel

_POLAR_THETA_START = 0.0
_POLAR_THETA_END = 2 * math.pi


class _LiveFn:
    """
    Mutable container for a function expression and its parameters.

    The ChartWidget stores a reference to the callable (self.__call__), which
    reads self._expr and self._extra at evaluation time.  This means the
    expression and parameters can be updated in-place without ever calling
    _FunctionItem.setFunction() or invalidateCache() — the next paint simply
    uses the new values automatically.

    invalidateCache() on the item is only called when the expression or
    parameters actually change, so panning / zooming never causes a redundant
    re-evaluation; the _FunctionItem cache key (x_lo, x_hi, n_pts) handles
    that transparently.
    """

    def __init__(self):
        self._expr: str = ""
        self._extra: dict = {}

    def update(self, expr: str, extra: dict) -> bool:
        """
        Update expression and parameters.  Returns True if anything changed
        so the caller knows whether to invalidate the item's sample cache.
        """
        changed = (expr != self._expr) or (extra != self._extra)
        self._expr = expr
        self._extra = dict(extra)
        return changed

    def __call__(self, xs: List[float]) -> List[Optional[float]]:
        if not self._expr:
            return [None] * len(xs)
        try:
            ys = sample_y(self._expr, xs, self._extra)
        except Exception:
            return [None] * len(xs)
        try:
            import numpy as _np
            arr = _np.asarray(ys, dtype=_np.float64)
            mask = _np.isfinite(arr)
            return [float(arr[i]) if mask[i] else None for i in range(len(arr))]
        except Exception:
            _isfinite = math.isfinite
            return [
                (y if (y is not None and type(y) is float and _isfinite(y)) else
                 (float(y) if y is not None and _isfinite(float(y)) else None))
                for y in ys
            ]


class _RowState:
    """Bundles the _FunctionItem and its _LiveFn for one function row."""

    def __init__(self, item: _FunctionItem, live_fn: _LiveFn):
        self.item = item
        self.live_fn = live_fn


class Plotter:
    """
    Evaluates all function rows and writes results into the ChartWidget.

    Infinite mode (y=f(x) only)
    ----------------------------
    Each row gets one _FunctionItem backed by a _LiveFn.  The callable is set
    once and never replaced; only its internal state (_expr, _extra) is
    updated.  The _FunctionItem cache is invalidated only when the expression
    or parameters change — not on every pan/zoom.  The library itself handles
    re-evaluation when the viewport key changes.

    Finite / polar / parametric modes
    -----------------------------------
    Use plain chart.plot() lines with setData(), same as before.

    Derivative / integral overlays
    --------------------------------
    Always use finite sampling.
    """

    _DERIV_COLORS = {"_d": "#9b59b6", "_d2": "#e74c3c", "_int": "#2ecc71"}
    _DERIV_LABELS = {"_d": "f'(x)", "_d2": "f''(x)", "_int": "∫f dx"}

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
        """Return existing _RowState or create one with a new _FunctionItem."""
        if row_id not in self._row_states:
            live_fn = _LiveFn()
            pen = QPen(QColor(row.color), row.get_width())
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            item = _FunctionItem(
                self._chart,
                live_fn,
                pen,
                label="",
                resolution=self._resolution(),
            )
            self._chart._functions.append(item)
            self._row_states[row_id] = _RowState(item, live_fn)
        return self._row_states[row_id]

    def _remove_state(self, row_id: int):
        """Remove the _FunctionItem and _RowState for a row."""
        state = self._row_states.pop(row_id, None)
        if state is not None:
            self._chart.removeItem(state.item)

    def sync_fn_items(self):
        """
        Remove _RowState entries whose rows no longer exist in the panel.
        Call before replot() and on _new_session().
        """
        live_ids = {id(row) for row in self._panel.func_rows}
        for rid in list(self._row_states):
            if rid not in live_ids:
                self._remove_state(rid)

    def replot(self):
        """
        Evaluate all function rows and update the chart.

        Returns (total_pts, x_min, x_max, n_functions) or None if the
        x-range is invalid.
        """
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

                changed = state.live_fn.update(expr, extra)
                if changed:
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
        """Recompute derivative / integral overlay lines using finite sampling."""
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
                for sfx, visible in shows.items():
                    k = f"{id(row)}{sfx}"
                    if visible:
                        active_keys.add(k)
                        if k not in dl:
                            dl[k] = self._chart.plot(
                                label=self._DERIV_LABELS[sfx],
                                color=self._DERIV_COLORS[sfx],
                                width=1,
                            )
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