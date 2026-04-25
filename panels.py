from __future__ import annotations

import math
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout,
    QLabel, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
    QPushButton, QComboBox, QMenu, QToolButton, QSizePolicy,
)
from pyqt5_chart_widget import ChartWidget

from constants import (
    COLORS, PRESETS,
    DEFAULT_XMIN, DEFAULT_XMAX, DEFAULT_YMIN, DEFAULT_YMAX,
    DEFAULT_TMIN, DEFAULT_TMAX, DEFAULT_SAMPLES,
)
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
_ADD_BTN_STYLE = (
    "QToolButton{background:#3498db;color:white;border:none;border-radius:4px;"
    "font-size:13px;padding:3px 10px;font-weight:bold;}"
    "QToolButton:hover{background:#2980b9;}"
    "QToolButton::menu-indicator{image:none;}"
)


class DragFilter(QObject):
    """Handles initiating drag operations for items within the function panel."""

    def __init__(self, container: QWidget) -> None:
        super().__init__(container)
        self.container = container
        self.start_pos = None

    def eventFilter(self, obj: QObject, e: QEvent) -> bool:
        if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            self.start_pos = e.pos()
        elif e.type() == QEvent.MouseMove and self.start_pos:
            if (e.pos() - self.start_pos).manhattanLength() > 5:
                drag = QDrag(self.container)
                mime = QMimeData()
                mime.setText(f"drag_item_{id(obj)}")
                drag.setMimeData(mime)
                px = obj.grab()
                drag.setPixmap(px)
                drag.setHotSpot(e.pos())
                obj.hide()
                drag.exec_(Qt.MoveAction)
                obj.show()
                self.start_pos = None
                return True
        elif e.type() == QEvent.MouseButtonRelease:
            self.start_pos = None
        return False


class ReorderContainer(QWidget):
    """Container that accepts drops for reordering and nesting items hierarchically."""

    def __init__(self, panel: FunctionPanel, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.panel = panel
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasText() and e.mimeData().text().startswith("drag_item_"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e) -> None:
        e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        txt = e.mimeData().text()
        wid = int(txt.split("_")[-1])
        w = next((x for x in self.panel._items if id(x) == wid), None)
        if not w:
            return

        pos = e.pos()
        target_layout = self.layout()
        insert_idx = target_layout.count() - 1

        for i in range(target_layout.count() - 1):
            child = target_layout.itemAt(i).widget()
            if child:
                if child.geometry().contains(pos):
                    if type(child).__name__ == "FolderItem" and pos.y() > child.y() + 34:
                        if getattr(w, "_body_layout", None) == getattr(child, "_body_layout", object()):
                            return
                        target_layout = child._body_layout
                        insert_idx = target_layout.count()
                        local_y = pos.y() - (child.y() + 34)
                        for j in range(target_layout.count()):
                            c2 = target_layout.itemAt(j).widget()
                            if c2 and local_y < c2.y() + c2.height() / 2:
                                insert_idx = j
                                break
                        break
                    elif pos.y() < child.y() + child.height() / 2:
                        insert_idx = i
                        break

        old_parent = w.parentWidget()
        if old_parent and old_parent.layout():
            old_parent.layout().removeWidget(w)

        target_layout.insertWidget(insert_idx, w)
        w.show()
        e.acceptProposedAction()
        self.panel.update_requested.emit()


class DerivativePanel(QGroupBox):
    """Controls for numerical derivative and integral overlays."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Derivatives & Integrals", parent)
        from PyQt5.QtWidgets import QGridLayout
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

    def update_sources(self, names: List[str]) -> None:
        prev = self._src.currentText()
        self._src.blockSignals(True)
        self._src.clear()
        for n in names:
            self._src.addItem(n)
        idx = self._src.findText(prev)
        self._src.setCurrentIndex(idx if idx >= 0 else 0)
        self._src.blockSignals(False)

    def source_idx(self) -> int:
        return self._src.currentIndex()

    def show_d1(self) -> bool:
        return self._d1.isChecked()

    def show_d2(self) -> bool:
        return self._d2.isChecked()

    def show_ig(self) -> bool:
        return self._ig.isChecked()

    def to_state(self) -> dict:
        return {
            "d1": self.show_d1(), "d2": self.show_d2(),
            "ig": self.show_ig(), "src": self._src.currentText(),
        }

    def apply_state(self, state: dict) -> None:
        self._d1.setChecked(state.get("d1", False))
        self._d2.setChecked(state.get("d2", False))
        self._ig.setChecked(state.get("ig", False))


class GraphSettings(QGroupBox):
    """Spinbox controls for x/y/t range, sample count, and infinite mode."""

    changed = pyqtSignal()
    infinite_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__("View", parent)
        from PyQt5.QtWidgets import QGridLayout
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
        self._infinite.setChecked(True)
        self._infinite.toggled.connect(self.changed.emit)
        self._infinite.toggled.connect(self.infinite_changed.emit)

        lbl = lambda t: QLabel(f"<small>{t}</small>")
        lay.addWidget(lbl("x:"), 0, 0);
        lay.addWidget(self._xmin, 0, 1)
        lay.addWidget(lbl("to"), 0, 2);
        lay.addWidget(self._xmax, 0, 3)
        lay.addWidget(lbl("y:"), 1, 0);
        lay.addWidget(self._ymin, 1, 1)
        lay.addWidget(lbl("to"), 1, 2);
        lay.addWidget(self._ymax, 1, 3)
        lay.addWidget(lbl("t:"), 2, 0);
        lay.addWidget(self._tmin, 2, 1)
        lay.addWidget(lbl("to"), 2, 2);
        lay.addWidget(self._tmax, 2, 3)
        lay.addWidget(lbl("pts:"), 3, 0);
        lay.addWidget(self._samp, 3, 1)
        lay.addWidget(self._infinite, 3, 2, 1, 2)

    def xmin(self) -> float:
        return self._xmin.value()

    def xmax(self) -> float:
        return self._xmax.value()

    def ymin(self) -> float:
        return self._ymin.value()

    def ymax(self) -> float:
        return self._ymax.value()

    def tmin(self) -> float:
        return self._tmin.value()

    def tmax(self) -> float:
        return self._tmax.value()

    def samples(self) -> int:
        return self._samp.value()

    def infinite(self) -> bool:
        return self._infinite.isChecked()

    def to_state(self) -> dict:
        return {k: getattr(self, k)() for k in
                ("xmin", "xmax", "ymin", "ymax", "tmin", "tmax", "samples", "infinite")}

    def apply_state(self, s: dict) -> None:
        for attr, key in [
            ("_xmin", "xmin"), ("_xmax", "xmax"),
            ("_ymin", "ymin"), ("_ymax", "ymax"),
            ("_tmin", "tmin"), ("_tmax", "tmax"),
        ]:
            if key in s:
                getattr(self, attr).setValue(s[key])
        if "samples" in s:
            self._samp.setValue(s["samples"])
        if "infinite" in s:
            self._infinite.setChecked(s["infinite"])


class FunctionPanel(QWidget):
    """
    Main left-side panel managing function rows, parameter sliders,
    derivative overlays, graph view settings, and plugin-contributed items.
    """

    update_requested = pyqtSignal()
    anim_update_requested = pyqtSignal()

    def __init__(self, chart: Optional[ChartWidget], history: History,
                 parent=None) -> None:
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
        self._plugin_item_types: List[tuple] = []
        self._context = None
        self._drag_filter = DragFilter(self)
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(self._cfg.anim_interval_ms)
        self._anim_timer.timeout.connect(self.anim_update_requested.emit)
        self._build_ui()

    def set_context(self, context) -> None:
        """Store the AppContext for forwarding to plugin item factories."""
        self._context = context

    def register_plugin_item_type(self, label: str, plugin) -> None:
        """Register a PanelPlugin so its item type appears in the drop-down menu."""
        self._plugin_item_types.append((label, plugin))
        self._rebuild_add_menu()

    def set_plotter(self, plotter) -> None:
        self._plotter = plotter

    def set_anim_interval(self, ms: int) -> None:
        was_active = self._anim_timer.isActive()
        self._anim_timer.setInterval(ms)
        if was_active:
            self._anim_timer.start()

    def _build_ui(self) -> None:
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

        self._add_btn = QToolButton()
        self._add_btn.setText("+ Add")
        self._add_btn.setStyleSheet(_ADD_BTN_STYLE)
        self._add_btn.setPopupMode(QToolButton.InstantPopup)
        self._add_menu = QMenu(self._add_btn)
        self._add_btn.setMenu(self._add_menu)
        self._rebuild_add_menu()

        btn_param = QPushButton("+ param")
        btn_param.setStyleSheet(_TOOLBAR_BTN_STYLE)
        btn_param.clicked.connect(self._prompt_add_param)

        self._preset_combo = QComboBox()
        self._preset_combo.addItems(["Preset…"] + list(PRESETS.keys()))
        self._preset_combo.setFixedWidth(110)
        self._preset_combo.currentTextChanged.connect(
            lambda t: self._add_preset() if t != "Preset…" else None
        )

        tl.addWidget(self._add_btn)
        tl.addWidget(btn_param)
        tl.addWidget(self._preset_combo)
        tl.addStretch()
        lay.addWidget(toolbar)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:white;}")
        self._container = ReorderContainer(self)
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

    def _rebuild_add_menu(self) -> None:
        self._add_menu.clear()
        fn_act = self._add_menu.addAction("Function f(x)")
        fn_act.triggered.connect(self._add_default_function)
        if self._plugin_item_types:
            self._add_menu.addSeparator()
        for label, plugin in self._plugin_item_types:
            act = self._add_menu.addAction(label)
            act.triggered.connect(
                lambda checked=False, p=plugin: self._add_plugin_item(p)
            )

    def _add_default_function(self) -> None:
        state = {
            "expr": "", "mode": "y=f(x)",
            "color": COLORS[len(self.func_rows) % len(COLORS)],
            "width": 2, "enabled": True, "expr2": "", "type": "function",
        }
        self._history.push(AddFunctionCmd(self, state))

    def _add_plugin_item(self, plugin) -> Optional[QWidget]:
        if self._context is None:
            return None
        widget = plugin.create_item(self._context)
        if widget is None:
            return None
        widget.setProperty("_plugin_id", plugin.meta.id)
        if hasattr(widget, "changed"):
            widget.changed.connect(self.update_requested.emit)
        if hasattr(widget, "removed"):
            widget.removed.connect(lambda w: self._remove_plugin_item(w))
        self._items.append(widget)
        self._vlay.insertWidget(self._vlay.count() - 1, widget)
        widget.installEventFilter(self._drag_filter)
        return widget

    def _remove_plugin_item(self, widget) -> None:
        if widget in self._items:
            self._items.remove(widget)
        if widget.parentWidget() and widget.parentWidget().layout():
            widget.parentWidget().layout().removeWidget(widget)
        widget.deleteLater()

    def _prompt_add_param(self) -> None:
        existing = set(self._param_widgets.keys())
        candidates = [c for c in "abcdefghijklmnopqrstuvwxyz" if c not in existing]
        if not candidates:
            return
        self._history.push(AddParamCmd(self, candidates[0]))

    def add_param(self, name: str, record: bool = True, state: dict = None) -> Optional[QWidget]:
        if name in self._params:
            return self._param_widgets.get(name)
        self._params[name] = state["val"] if state else 1.0
        w = ParamSliderWidget(
            name,
            lo=state["lo"] if state else -5.0,
            hi=state["hi"] if state else 5.0,
            val=self._params[name],
        )
        if state:
            w.apply_state(state)
        w.param_changed.connect(self._on_param_changed)
        w.name_changed.connect(self._on_param_renamed)
        w.removed.connect(lambda item: self._history.push(
            RemoveParamCmd(self, item.name,
                           self._param_widgets[item.name].to_state())))
        self._param_widgets[name] = w
        self._items.append(w)
        self._vlay.insertWidget(self._vlay.count() - 1, w)
        w.installEventFilter(self._drag_filter)
        self.update_requested.emit()
        return w

    def _on_param_renamed(self, old_name: str, new_name: str) -> None:
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
            RemoveParamCmd(self, item.name,
                           self._param_widgets[item.name].to_state())))
        self.update_requested.emit()

    def remove_param(self, name: str, record: bool = True) -> None:
        if name not in self._param_widgets:
            return
        w = self._param_widgets.pop(name)
        if w in self._items:
            self._items.remove(w)
        if w.parentWidget() and w.parentWidget().layout():
            w.parentWidget().layout().removeWidget(w)
        w.deleteLater()
        self._params.pop(name, None)
        self.update_requested.emit()

    def _on_param_changed(self, name: str, val: float) -> None:
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
        row.installEventFilter(self._drag_filter)
        if self._chart is not None:
            line = self._chart.plot(
                label=f"f{idx + 1}",
                color=state.get("color", COLORS[idx % len(COLORS)]),
                width=state.get("width", 2),
            )
            row.chart_line = line
        row.apply_state(state)
        self._sync_deriv_sources()
        self.update_requested.emit()
        return row

    def bind_chart(self, chart: ChartWidget) -> None:
        self._chart = chart
        for i, row in enumerate(self.func_rows):
            if row.chart_line is None:
                line = self._chart.plot(
                    label=f"f{i + 1}", color=row.color, width=row.get_width()
                )
                row.chart_line = line

    def remove_function(self, row: FunctionRow, record: bool = True) -> None:
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
        if row.parentWidget() and row.parentWidget().layout():
            row.parentWidget().layout().removeWidget(row)
        row.deleteLater()
        self._sync_deriv_sources()
        self.update_requested.emit()

    def _add_preset(self) -> None:
        name = self._preset_combo.currentText()
        if name in PRESETS:
            expr, mode, expr2 = PRESETS[name]
            norm_mode = _normalize_mode(mode or "y=f(x)")
            state = {
                "expr": expr, "mode": norm_mode, "expr2": expr2 or "",
                "color": COLORS[len(self.func_rows) % len(COLORS)],
                "width": 2, "enabled": True, "type": "function",
            }
            self._history.push(AddFunctionCmd(self, state))
        self._preset_combo.blockSignals(True)
        self._preset_combo.setCurrentIndex(0)
        self._preset_combo.blockSignals(False)

    def _clear_all(self) -> None:
        self._anim_timer.stop()
        for row in list(self.func_rows):
            self.remove_function(row, record=False)
        for name in list(self._param_widgets.keys()):
            self.remove_param(name, record=False)
        plugin_items = [
            w for w in self._items
            if w.property("_plugin_id") is not None
        ]
        for w in plugin_items:
            self._items.remove(w)
            if w.parentWidget() and w.parentWidget().layout():
                w.parentWidget().layout().removeWidget(w)
            w.deleteLater()
        if self._chart is not None:
            for k in list(self._deriv_lines.keys()):
                self._chart.removeItem(self._deriv_lines.pop(k))
        else:
            self._deriv_lines.clear()
        self.update_requested.emit()

    def _sync_deriv_sources(self) -> None:
        self.deriv_panel.update_sources(
            [f"f{i + 1}" for i in range(len(self.func_rows))]
        )

    def get_params(self) -> dict:
        return dict(self._params)

    def get_deriv_lines(self) -> dict:
        return self._deriv_lines

    def get_anim_t(self) -> float:
        return 0.0

    def to_state(self) -> dict:
        def serialize_layout(layout):
            res = []
            for i in range(layout.count()):
                item = layout.itemAt(i)
                w = item.widget() if item else None
                if w in self._items:
                    st = w.to_state()
                    if type(w).__name__ == "FolderItem":
                        st["children"] = serialize_layout(w._body_layout)
                    res.append(st)
            return res

        return {
            "items": serialize_layout(self._vlay),
            "settings": self.settings.to_state(),
            "derivs": self.deriv_panel.to_state(),
        }

    def apply_state(self, state: dict) -> None:
        self._clear_all()
        if "items" in state:
            self._restore_items(state["items"], self._vlay)
        else:
            for n, ps in state.get("params", {}).items():
                self.add_param(n, record=False, state=ps)
            for fs in state.get("functions", []):
                self.add_function_from_state(fs)
            for pit in state.get("plugin_items", []):
                pid = pit.get("plugin_id")
                plugin = next((p for l, p in self._plugin_item_types if p.meta.id == pid), None)
                if plugin:
                    w = self._add_plugin_item(plugin)
                    if w and hasattr(w, "apply_state"):
                        w.apply_state(pit.get("state", {}))

        if "settings" in state:
            self.settings.apply_state(state["settings"])
        if "derivs" in state:
            self.deriv_panel.apply_state(state["derivs"])

    def _restore_items(self, items_state: list, target_layout) -> None:
        for item in items_state:
            t = item.get("type")
            w = None
            if t == "function":
                w = self.add_function_from_state(item)
            elif t == "param":
                w = self.add_param(item["name"], record=False, state=item)
            elif t == "plugin_item":
                pid = item.get("plugin_id")
                plugin = next((p for l, p in self._plugin_item_types if p.meta.id == pid), None)
                if plugin:
                    w = self._add_plugin_item(plugin)
                    if w and hasattr(w, "apply_state"):
                        w.apply_state(item)

            if w:
                if target_layout != self._vlay:
                    self._vlay.removeWidget(w)
                    target_layout.addWidget(w)
                if type(w).__name__ == "FolderItem" and "children" in item:
                    self._restore_items(item["children"], w._body_layout)

    def add_sidebar_panel(self, widget: QWidget) -> None:
        """Append a sidebar panel widget to the bottom fixed area."""
        bottom = self.findChild(QWidget, "sidebar_area")
        if bottom is None:
            return
        layout = bottom.layout()
        if layout:
            layout.addWidget(widget)