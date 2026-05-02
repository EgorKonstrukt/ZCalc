from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow
from core.plugins.plugin_base import AnyPlugin, PanelPlugin, SidebarPlugin, MenuPlugin, DockPlugin
from core.plugins.plugin_loader import PluginLoader, PluginRecord
from core.plugins.app_context import AppContext

log = logging.getLogger(__name__)
_STATE_FILE = "plugin_state.json"
_DOCK_STATE_FILE = "dock_state.json"

_AREA_MAP = {
    1: Qt.LeftDockWidgetArea,
    2: Qt.RightDockWidgetArea,
    4: Qt.TopDockWidgetArea,
    8: Qt.BottomDockWidgetArea,
}
_AREA_REVERSE = {v: k for k, v in _AREA_MAP.items()}

class PluginManager:
    def __init__(self, plugins_dir: str | Path, state_dir: str | Path) -> None:
        self._loader = PluginLoader(plugins_dir)
        self._state_path = Path(state_dir) / _STATE_FILE
        self._dock_state_path = Path(state_dir) / _DOCK_STATE_FILE
        self._context: Optional[AppContext] = None
        self._panel_plugins: List[PanelPlugin] = []
        self._sidebar_plugins: List[SidebarPlugin] = []
        self._dock_plugins: List[DockPlugin] = []
        self._saved_enabled: Dict[str, bool] = {}
        self._saved_dock_states: Dict[str, dict] = {}

    def initialise(self, context: AppContext) -> None:
        self._context = context
        self._load_saved_state()
        self._load_dock_state()
        discovered = self._loader.discover()
        for pid in discovered:
            should_enable = self._saved_enabled.get(pid, True)
            if should_enable:
                self._loader.enable(pid, context)
                rec = self._loader.get(pid)
                if rec and rec.enabled:
                    self._integrate(rec)

    def shutdown(self, context: AppContext) -> None:
        self.save_dock_states(context)
        for pid in list(self._loader.records.keys()):
            rec = self._loader.get(pid)
            if rec and rec.enabled:
                try:
                    rec.plugin.on_unload(context)
                    rec.enabled = False
                except Exception as exc:
                    log.warning("on_unload failed for %s: %s", pid, exc)

    def save_dock_states(self, context: AppContext) -> None:
        mw = context.main_window
        if not isinstance(mw, QMainWindow):
            return
        state: Dict[str, dict] = {}
        for dock_id, dock in context.all_docks().items():
            area = mw.dockWidgetArea(dock)
            area_int = _AREA_REVERSE.get(area, 8)
            geo = dock.geometry()
            state[dock_id] = {
                "area": area_int,
                "floating": dock.isFloating(),
                "visible": dock.isVisible(),
                "geometry": [geo.x(), geo.y(), geo.width(), geo.height()],
            }
        try:
            self._dock_state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._dock_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            log.warning("Could not save dock state: %s", exc)

    def restore_dock_state(self, dock_id: str, dock, context: AppContext) -> None:
        mw = context.main_window
        if not isinstance(mw, QMainWindow):
            return
        saved = self._saved_dock_states.get(dock_id)
        if saved is None:
            plugin = self._find_dock_plugin(dock_id)
            saved = plugin.default_dock_state() if plugin else {"area": 8, "floating": False, "visible": True}
        area_int = saved.get("area", 8)
        qt_area = _AREA_MAP.get(area_int, Qt.BottomDockWidgetArea)
        mw.addDockWidget(qt_area, dock)
        if saved.get("floating", False):
            dock.setFloating(True)
            geo = saved.get("geometry")
            if geo and len(geo) == 4:
                from PyQt5.QtCore import QRect
                dock.setGeometry(QRect(*geo))
        dock.setVisible(saved.get("visible", True))

    def _find_dock_plugin(self, dock_id: str) -> Optional[DockPlugin]:
        for p in self._dock_plugins:
            if p.dock_id() == dock_id:
                return p
        return None

    def enable_plugin(self, plugin_id: str) -> bool:
        ok = self._loader.enable(plugin_id, self._context)
        if ok:
            rec = self._loader.get(plugin_id)
            if rec:
                self._integrate(rec)
        self._persist_state()
        return ok

    def disable_plugin(self, plugin_id: str) -> bool:
        ok = self._loader.disable(plugin_id, self._context)
        self._persist_state()
        return ok

    def records(self) -> List[PluginRecord]:
        return list(self._loader.records.values())
    def panel_plugins(self) -> List[PanelPlugin]:
        return list(self._panel_plugins)
    def sidebar_plugins(self) -> List[SidebarPlugin]:
        return list(self._sidebar_plugins)
    def dock_plugins(self) -> List[DockPlugin]:
        return list(self._dock_plugins)
    def get_plugin(self, plugin_id: str) -> Optional[AnyPlugin]:
        rec = self._loader.get(plugin_id)
        return rec.plugin if rec else None

    def _integrate(self, rec: PluginRecord) -> None:
        p = rec.plugin
        if isinstance(p, PanelPlugin) and p not in self._panel_plugins:
            self._panel_plugins.append(p)
        if isinstance(p, SidebarPlugin) and p not in self._sidebar_plugins:
            self._sidebar_plugins.append(p)
        if isinstance(p, MenuPlugin):
            p.register_actions(self._context)
        if isinstance(p, DockPlugin) and p not in self._dock_plugins:
            self._dock_plugins.append(p)
            self._attach_dock(p)

    def _attach_dock(self, p: DockPlugin) -> None:
        try:
            dock = p.create_dock(self._context)
            if dock is None:
                return
            dock_id = p.dock_id()
            self._context.register_dock(dock_id, dock)
            self.restore_dock_state(dock_id, dock, self._context)
        except Exception as exc:
            log.exception("create_dock failed for %s: %s", p.meta.id, exc)

    def _load_saved_state(self) -> None:
        if not self._state_path.exists():
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                self._saved_enabled = json.load(f)
        except Exception as exc:
            log.warning("Could not read plugin state: %s", exc)

    def _load_dock_state(self) -> None:
        if not self._dock_state_path.exists():
            return
        try:
            with open(self._dock_state_path, "r", encoding="utf-8") as f:
                self._saved_dock_states = json.load(f)
        except Exception as exc:
            log.warning("Could not read dock state: %s", exc)

    def _persist_state(self) -> None:
        state = {pid: rec.enabled for pid, rec in self._loader.records.items()}
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            log.warning("Could not save plugin state: %s", exc)