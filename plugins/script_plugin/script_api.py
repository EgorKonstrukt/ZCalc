from __future__ import annotations
import math
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtCore import QTimer

if TYPE_CHECKING:
    from core.app_context import AppContext


class PlotWindow(QDialog):
    """Standalone chart window created by a script."""
    def __init__(self, title: str = "Script Plot", parent=None):
        super().__init__(parent)
        from pyqt5_chart_widget import ChartWidget
        self.setWindowTitle(title)
        self.resize(800, 600)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self._chart = ChartWidget(
            show_toolbar=True, show_legend=True,
            show_sidebar=False, threaded_fit=False, anim_duration=60,
        )
        lay.addWidget(self._chart)
        self._lines: Dict[str, Any] = {}

    @property
    def chart(self):
        return self._chart

    def plot(self, xs: List[float], ys: List[float], label: str = "",
             color: str = "#3498db", width: int = 2) -> Any:
        """Add or update a named line on this window's chart."""
        from PyQt5.QtGui import QColor
        key = label or f"_line{len(self._lines)}"
        if key not in self._lines:
            self._lines[key] = self._chart.plot(label=label, color=color, width=width)
        line = self._lines[key]
        line.pen.setColor(QColor(color))
        line.pen.setWidth(width)
        if label:
            line.setLabel(label)
        line.setData(xs=list(xs), ys=list(ys))
        line.setVisible(True)
        return line

    def clear(self):
        """Remove all lines from this window's chart."""
        for line in self._lines.values():
            try:
                line.setData(xs=[], ys=[])
            except Exception:
                pass
        self._lines.clear()


class AnimHandle:
    """Token returned by api.animate(); call stop() to cancel."""
    def __init__(self, api: "ScriptAPI", handle_id: int):
        self._api = api
        self._id = handle_id

    def stop(self):
        """Stop the animation associated with this handle."""
        self._api._stop_anim(self._id)

    @property
    def t(self) -> float:
        """Elapsed time in seconds since the animation started."""
        return self._api._get_anim_t(self._id)


class ScriptAPI:
    """
    Public interface injected as `api` into every script namespace.

    Provides chart access, parameter sliders, animation, new windows,
    and status bar messaging.  All resources are cleaned up on stop().
    """
    def __init__(self, context: "AppContext", owner_row):
        self._ctx = context
        self._row = owner_row
        self._anim_records: Dict[int, Dict] = {}
        self._anim_timers: Dict[int, QTimer] = {}
        self._anim_counter = 0
        self._plot_windows: List[PlotWindow] = []

    def plot(self, xs, ys, label: str = "", color: str = "#3498db", width: int = 2) -> Any:
        """Plot xs/ys on the main chart, keyed by label. Returns the line object."""
        from PyQt5.QtGui import QColor
        key = f"_sr_{id(self._row)}_{label or id((xs, ys))}"
        lines = self._row._script_lines
        if key not in lines:
            lines[key] = self._ctx.chart.plot(
                label=label or "script", color=color, width=width
            )
        line = lines[key]
        line.pen.setColor(QColor(color))
        line.pen.setWidth(width)
        if label:
            line.setLabel(label)
        line.setData(xs=list(xs), ys=list(ys))
        line.setVisible(True)
        return line

    def clear_plots(self):
        """Remove all chart lines this script created on the main chart."""
        for line in list(self._row._script_lines.values()):
            try:
                self._ctx.chart.removeItem(line)
            except Exception:
                pass
        self._row._script_lines.clear()

    def add_function(self, expr: str, mode: str = "y=f(x)",
                     color: str = "#e74c3c", width: int = 2):
        """Add a function row to the main panel."""
        from constants import COLORS
        panel = self._ctx.panel
        idx = len(panel.func_rows)
        state = {
            "expr": expr, "mode": mode, "expr2": "",
            "color": color or COLORS[idx % len(COLORS)],
            "width": width, "enabled": True, "type": "function",
        }
        return panel.add_function_from_state(state)

    def add_param(self, name: str, lo: float = -5.0, hi: float = 5.0, val: float = 1.0):
        """Add a parameter slider to the main panel if it does not already exist."""
        panel = self._ctx.panel
        if name not in panel._param_widgets:
            panel.add_param(name, record=False, state={
                "name": name, "lo": lo, "hi": hi, "val": val,
                "speed": 1.0, "anim_mode": "loop", "type": "param",
            })

    def get_param(self, name: str, default: float = 0.0) -> float:
        """Return the current value of a panel parameter slider."""
        return self._ctx.panel.get_params().get(name, default)

    def get_t(self) -> float:
        """Return the current t from AnimPanel, or 0.0 if unavailable."""
        panel = self._ctx.panel
        anim = getattr(panel, "anim_panel", None)
        if anim is not None:
            return anim.get_t()
        return 0.0

    def new_window(self, title: str = "Script Plot") -> PlotWindow:
        """Open and return a new standalone chart window."""
        win = PlotWindow(title, self._ctx.main_window)
        self._plot_windows.append(win)
        win.show()
        return win

    def animate(self, callback: Callable[[float], None],
                fps: int = 30, duration_ms: int = 0) -> AnimHandle:
        """
        Call callback(t) at fps frames/sec, where t is elapsed seconds.
        duration_ms=0 means infinite.  Returns an AnimHandle.
        """
        handle_id = self._anim_counter
        self._anim_counter += 1
        interval = max(8, 1000 // max(1, fps))
        record: Dict = {"elapsed_ms": 0, "interval": interval, "cb": callback}
        self._anim_records[handle_id] = record
        timer = QTimer()
        timer.setInterval(interval)
        def _tick():
            record["elapsed_ms"] += interval
            if duration_ms > 0 and record["elapsed_ms"] >= duration_ms:
                timer.stop()
                self._anim_records.pop(handle_id, None)
                self._anim_timers.pop(handle_id, None)
                return
            try:
                callback(record["elapsed_ms"] / 1000.0)
            except Exception as exc:
                self._row._set_status(f"Anim error: {exc}", error=True)
                timer.stop()
                self._anim_records.pop(handle_id, None)
                self._anim_timers.pop(handle_id, None)
        timer.timeout.connect(_tick)
        self._anim_timers[handle_id] = timer
        timer.start()
        return AnimHandle(self, handle_id)

    def linspace(self, start: float, stop: float, n: int) -> List[float]:
        """Return n evenly-spaced floats from start to stop inclusive."""
        from math_engine import linspace as _ls
        return _ls(start, stop, n)

    def status(self, msg: str, timeout_ms: int = 4000):
        """Display a message in the main window status bar."""
        self._ctx.show_status(msg, timeout_ms)

    def replot(self):
        """Request an immediate replot of the main chart."""
        self._ctx.request_replot()

    def _stop_anim(self, handle_id: int):
        timer = self._anim_timers.pop(handle_id, None)
        if timer:
            timer.stop()
        self._anim_records.pop(handle_id, None)

    def _get_anim_t(self, handle_id: int) -> float:
        rec = self._anim_records.get(handle_id)
        return rec["elapsed_ms"] / 1000.0 if rec else 0.0

    def cleanup(self):
        """Stop all timers, remove all chart lines, close all windows."""
        for timer in list(self._anim_timers.values()):
            try:
                timer.stop()
            except Exception:
                pass
        self._anim_timers.clear()
        self._anim_records.clear()
        self.clear_plots()
        for win in list(self._plot_windows):
            try:
                win.close()
            except Exception:
                pass
        self._plot_windows.clear()
