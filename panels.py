import math
from typing import List, Dict, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton,
    QLabel, QComboBox, QSizePolicy, QFrame, QLineEdit, QCheckBox,
    QDoubleSpinBox, QSpinBox, QGridLayout, QGroupBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
from pyqt5_chart_widget import ChartWidget
from constants import COLORS, PRESETS, DEFAULT_XMIN, DEFAULT_XMAX, DEFAULT_YMIN, DEFAULT_YMAX, DEFAULT_TMIN, DEFAULT_TMAX, DEFAULT_SAMPLES
from function_row import FunctionRow, _normalize_mode
from param_slider import ParamSliderWidget
from history import History, AddFunctionCmd, RemoveFunctionCmd, AddParamCmd, RemoveParamCmd
from expr_item import ExprItem
from config import Config

_TOOLBAR_BTN_STYLE = (
    "QPushButton{background:#f5f5f5;border:1px solid #ddd;border-radius:4px;"
    "font-size:12px;padding:3px 8px;}"
    "QPushButton:hover{background:#e8e8e8;}"
    "QPushButton:pressed{background:#d0d0d0;}"
)


class DerivativePanel(QGroupBox):
    changed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__("Derivatives & Integrals", parent)
        lay = QGridLayout(self)
        lay.setSpacing(4)
        self._src = QComboBox()
        self._src.currentIndexChanged.connect(self.changed.emit)
        self._d1 = QCheckBox("f'(x)")
        self._d2 = QCheckBox("f''(x)")
        self._ig = QCheckBox("integral")
        for cb in (self._d1, self._d2, self._ig):
            cb.toggled.connect(self.changed.emit)
        lay.addWidget(QLabel("Source:"), 0, 0)
        lay.addWidget(self._src, 0, 1, 1, 3)
        lay.addWidget(self._d1, 1, 0)
        lay.addWidget(self._d2, 1, 1)
        lay.addWidget(self._ig, 1, 2)
    def update_sources(self, names: List[str]):
        prev = self._src.currentText()
        self._src.blockSignals(True)
        self._src.clear()
        for n in names:
            self._src.addItem(n)
        idx = self._src.findText(prev)
        self._src.setCurrentIndex(idx if idx >= 0 else 0)
        self._src.blockSignals(False)
    def source_idx(self) -> int:       return self._src.currentIndex()
    def show_d1(self) -> bool:         return self._d1.isChecked()
    def show_d2(self) -> bool:         return self._d2.isChecked()
    def show_ig(self) -> bool:         return self._ig.isChecked()
    def to_state(self) -> dict:
        return {"d1": self.show_d1(), "d2": self.show_d2(), "ig": self.show_ig(), "src": self._src.currentText()}
    def apply_state(self, state: dict):
        self._d1.setChecked(state.get("d1", False))
        self._d2.setChecked(state.get("d2", False))
        self._ig.setChecked(state.get("ig", False))


class GraphSettings(QGroupBox):
    changed = pyqtSignal()
    infinite_changed = pyqtSignal(bool)
    def __init__(self, parent=None):
        super().__init__("View", parent)
        lay = QGridLayout(self)
        lay.setSpacing(3)
        def mk(lo, hi, val, dec=1, w=68):
            s = QDoubleSpinBox()
            s.setRange(lo, hi)
            s.setValue(val)
            s.setDecimals(dec)
            s.setFixedWidth(w)
            s.setSingleStep(0.5)
            s.valueChanged.connect(self.changed.emit)
            return s
        self._xmin = mk(-1e6, 0, DEFAULT_XMIN)
        self._xmax = mk(0, 1e6, DEFAULT_XMAX)
        self._ymin = mk(-1e6, 0, DEFAULT_YMIN)
        self._ymax = mk(0, 1e6, DEFAULT_YMAX)
        self._tmin = mk(-1e3, 0, DEFAULT_TMIN, dec=3)
        self._tmax = mk(0, 1e3, DEFAULT_TMAX, dec=3)
        self._samp = QSpinBox()
        self._samp.setRange(100, 8000)
        self._samp.setValue(DEFAULT_SAMPLES)
        self._samp.setFixedWidth(68)
        self._samp.valueChanged.connect(self.changed.emit)
        self._infinite = QCheckBox("Infinite graph")
        self._infinite.toggled.connect(self.changed.emit)
        self._infinite.toggled.connect(self.infinite_changed.emit)
        lbl = lambda t: QLabel(f"<small>{t}</small>")
        lay.addWidget(lbl("x:"), 0, 0);   lay.addWidget(self._xmin, 0, 1)
        lay.addWidget(lbl("to"), 0, 2);   lay.addWidget(self._xmax, 0, 3)
        lay.addWidget(lbl("y:"), 1, 0);   lay.addWidget(self._ymin, 1, 1)
        lay.addWidget(lbl("to"), 1, 2);   lay.addWidget(self._ymax, 1, 3)
        lay.addWidget(lbl("t:"), 2, 0);   lay.addWidget(self._tmin, 2, 1)
        lay.addWidget(lbl("to"), 2, 2);   lay.addWidget(self._tmax, 2, 3)
        lay.addWidget(lbl("pts:"), 3, 0); lay.addWidget(self._samp, 3, 1)
        lay.addWidget(self._infinite, 3, 2, 1, 2)
    def xmin(self) -> float:     return self._xmin.value()
    def xmax(self) -> float:     return self._xmax.value()
    def ymin(self) -> float:     return self._ymin.value()
    def ymax(self) -> float:     return self._ymax.value()
    def tmin(self) -> float:     return self._tmin.value()
    def tmax(self) -> float:     return self._tmax.value()
    def samples(self) -> int:    return self._samp.value()
    def infinite(self) -> bool:  return self._infinite.isChecked()
    def to_state(self) -> dict:
        return {k: getattr(self, k)() for k in ("xmin","xmax","ymin","ymax","tmin","tmax","samples","infinite")}
    def apply_state(self, s: dict):
        for attr, key in [("_xmin","xmin"),("_xmax","xmax"),("_ymin","ymin"),("_ymax","ymax"),("_tmin","tmin"),("_tmax","tmax")]:
            if key in s:
                getattr(self, attr).setValue(s[key])
        if "samples" in s: self._samp.setValue(s["samples"])
        if "infinite" in s: self._infinite.setChecked(s["infinite"])


class FunctionPanel(QWidget):
    """
    Main left-side panel managing function rows, parameter sliders,
    derivative overlays, and graph view settings.

    Holds a weak reference to the active Plotter via set_plotter() so that
    remove_function() can clean up eval-loop chart lines in addition to the
    standard derivative lines.
    """

    update_requested = pyqtSignal()
    anim_update_requested = pyqtSignal()

    def __init__(self, chart: ChartWidget, history: History, parent=None):
        super().__init__(parent)
        self._chart = chart
        self._history = history
        self._cfg = Config()
        self.func_rows: List[FunctionRow] = []
        self._params: Dict[str, float] = {}
        self._param_widgets: Dict[str, ParamSliderWidget] = {}
        self._deriv_lines: Dict[str, object] = {}
        self._items: List[ExprItem] = []
        self._plotter = None
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(self._cfg.anim_interval_ms)
        self._anim_timer.timeout.connect(self.anim_update_requested.emit)
        self._build_ui()

    def set_plotter(self, plotter) -> None:
        """
        Register the active Plotter instance.

        Called once by the main window after both FunctionPanel and Plotter
        are constructed.  Allows remove_function() to delegate eval-loop
        cleanup to the plotter.
        """
        self._plotter = plotter

    def set_anim_interval(self, ms: int):
        was_active = self._anim_timer.isActive()
        self._anim_timer.setInterval(ms)
        if was_active:
            self._anim_timer.start()

    def _build_ui(self):
        self.setStyleSheet("FunctionPanel{background:#ffffff;}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        toolbar = QWidget()
        toolbar.setFixedHeight(40)
        toolbar.setStyleSheet("background:#f8f8f8;border-bottom:1px solid #ddd;")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(6, 4, 6, 4)
        tl.setSpacing(4)
        btn_fn = QPushButton("+ f(x)")
        btn_fn.setStyleSheet(_TOOLBAR_BTN_STYLE)
        btn_fn.clicked.connect(lambda: self._history.push(
            AddFunctionCmd(self, {"expr":"","mode":"y=f(x)","color":COLORS[len(self.func_rows)%len(COLORS)],"width":2,"enabled":True,"expr2":"","type":"function"})))
        btn_param = QPushButton("+ param")
        btn_param.setStyleSheet(_TOOLBAR_BTN_STYLE)
        btn_param.clicked.connect(self._prompt_add_param)
        self._preset_combo = QComboBox()
        for k in PRESETS:
            self._preset_combo.addItem(k)
        self._preset_combo.setStyleSheet("QComboBox{border:1px solid #ddd;border-radius:4px;padding:2px 4px;font-size:11px;}")
        btn_preset = QPushButton("Add")
        btn_preset.setStyleSheet(_TOOLBAR_BTN_STYLE)
        btn_preset.clicked.connect(self._add_preset)
        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet(_TOOLBAR_BTN_STYLE)
        btn_clear.clicked.connect(self._clear_all)
        for w in (btn_fn, btn_param, self._preset_combo, btn_preset, btn_clear):
            tl.addWidget(w)
        tl.addStretch()
        lay.addWidget(toolbar)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:white;}")
        self._container = QWidget()
        self._container.setStyleSheet("background:white;")
        self._vlay = QVBoxLayout(self._container)
        self._vlay.setContentsMargins(0, 0, 0, 0)
        self._vlay.setSpacing(0)
        self._vlay.addStretch()
        self._scroll.setWidget(self._container)
        lay.addWidget(self._scroll, 1)
        bottom = QWidget()
        bottom.setStyleSheet("background:#f8f8f8;border-top:1px solid #ddd;")
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(4, 4, 4, 4)
        bl.setSpacing(4)
        self.deriv_panel = DerivativePanel()
        self.deriv_panel.changed.connect(self.update_requested.emit)
        self.settings = GraphSettings()
        self.settings.changed.connect(self.update_requested.emit)
        bl.addWidget(self.deriv_panel)
        bl.addWidget(self.settings)
        lay.addWidget(bottom)

    def _prompt_add_param(self):
        existing = set(self._param_widgets.keys())
        candidates = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in existing]
        if not candidates:
            return
        self._history.push(AddParamCmd(self, candidates[0]))

    def add_param(self, name: str, record: bool = True, state: dict = None):
        if name in self._params:
            return
        self._params[name] = state["val"] if state else 1.0
        w = ParamSliderWidget(name,
                              lo=state["lo"] if state else -5.0,
                              hi=state["hi"] if state else 5.0,
                              val=self._params[name])
        if state:
            w.apply_state(state)
        w.param_changed.connect(self._on_param_changed)
        w.name_changed.connect(self._on_param_renamed)
        w.removed.connect(lambda item: self._history.push(
            RemoveParamCmd(self, item.name, self._param_widgets[item.name].to_state())))
        self._param_widgets[name] = w
        self._items.append(w)
        self._vlay.insertWidget(self._vlay.count() - 1, w)
        self.update_requested.emit()

    def _on_param_renamed(self, old_name: str, new_name: str):
        if new_name in self._params and new_name != old_name:
            w = self._param_widgets.get(old_name)
            if w:
                w.name = old_name
                w._name_edit.setText(old_name)
            return
        if old_name not in self._param_widgets:
            return
        w = self._param_widgets.pop(old_name)
        val = self._params.pop(old_name, w.get_value())
        self._params[new_name] = val
        self._param_widgets[new_name] = w
        w.removed.disconnect()
        w.removed.connect(lambda item: self._history.push(
            RemoveParamCmd(self, item.name, self._param_widgets[item.name].to_state())))
        self.update_requested.emit()

    def remove_param(self, name: str, record: bool = True):
        if name not in self._param_widgets:
            return
        w = self._param_widgets.pop(name)
        if w in self._items:
            self._items.remove(w)
        self._vlay.removeWidget(w)
        w.deleteLater()
        self._params.pop(name, None)
        self.update_requested.emit()

    def _on_param_changed(self, name: str, val: float):
        self._params[name] = val
        any_anim = any(w._animating for w in self._param_widgets.values())
        if any_anim:
            if not self._anim_timer.isActive():
                self._anim_timer.start()
        else:
            if self._anim_timer.isActive():
                self._anim_timer.stop()
            self.update_requested.emit()

    def add_function_from_state(self, state: dict) -> FunctionRow:
        idx = len(self.func_rows)
        row = FunctionRow(idx, self)
        row.changed.connect(self.update_requested.emit)
        row.removed.connect(lambda r: self._history.push(RemoveFunctionCmd(self, r)))
        self.func_rows.append(row)
        self._items.append(row)
        self._vlay.insertWidget(self._vlay.count() - 1, row)
        if self._chart is not None:
            line = self._chart.plot(
                label=f"f{idx+1}",
                color=state.get("color", COLORS[idx % len(COLORS)]),
                width=state.get("width", 2))
            row.chart_line = line
        row.apply_state(state)
        self._sync_deriv_sources()
        self.update_requested.emit()
        return row

    def bind_chart(self, chart: ChartWidget):
        self._chart = chart
        for i, row in enumerate(self.func_rows):
            if row.chart_line is None:
                line = self._chart.plot(label=f"f{i+1}", color=row.color, width=row.get_width())
                row.chart_line = line

    def remove_function(self, row: FunctionRow, record: bool = True):
        if row not in self.func_rows:
            return
        if row.chart_line is not None and self._chart is not None:
            self._chart.removeItem(row.chart_line)
        for sfx in ("_d", "_d2", "_int"):
            k = f"{id(row)}{sfx}"
            if k in self._deriv_lines and self._chart is not None:
                self._chart.removeItem(self._deriv_lines.pop(k))
        if self._plotter is not None:
            self._plotter._remove_eval_loop_state(id(row))
        self.func_rows.remove(row)
        if row in self._items:
            self._items.remove(row)
        self._vlay.removeWidget(row)
        row.deleteLater()
        self._sync_deriv_sources()
        self.update_requested.emit()

    def _add_preset(self):
        name = self._preset_combo.currentText()
        if name in PRESETS:
            expr, mode, expr2 = PRESETS[name]
            norm_mode = _normalize_mode(mode or "y=f(x)")
            state = {"expr": expr, "mode": norm_mode, "expr2": expr2 or "",
                     "color": COLORS[len(self.func_rows) % len(COLORS)], "width": 2, "enabled": True, "type": "function"}
            self._history.push(AddFunctionCmd(self, state))

    def _clear_all(self):
        self._anim_timer.stop()
        for row in list(self.func_rows):
            self.remove_function(row, record=False)
        for name in list(self._param_widgets.keys()):
            self.remove_param(name, record=False)
        if self._chart is not None:
            for k in list(self._deriv_lines.keys()):
                self._chart.removeItem(self._deriv_lines.pop(k))
        else:
            self._deriv_lines.clear()
        self.update_requested.emit()

    def _sync_deriv_sources(self):
        self.deriv_panel.update_sources([f"f{i+1}" for i in range(len(self.func_rows))])

    def get_params(self) -> dict:           return dict(self._params)
    def get_deriv_lines(self) -> dict:      return self._deriv_lines
    def get_anim_t(self) -> float:          return 0.0

    def to_state(self) -> dict:
        return {
            "functions": [r.to_state() for r in self.func_rows],
            "params":    {n: w.to_state() for n, w in self._param_widgets.items()},
            "settings":  self.settings.to_state(),
            "derivs":    self.deriv_panel.to_state(),
        }

    def apply_state(self, state: dict):
        self._clear_all()
        for n, ps in state.get("params", {}).items():
            self.add_param(n, record=False, state=ps)
        for fs in state.get("functions", []):
            self.add_function_from_state(fs)
        if "settings" in state:
            self.settings.apply_state(state["settings"])
        if "derivs" in state:
            self.deriv_panel.apply_state(state["derivs"])