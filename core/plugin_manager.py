from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from core.plugin_base import AnyPlugin, PanelPlugin, SidebarPlugin, MenuPlugin
from core.plugin_loader import PluginLoader, PluginRecord
from core.app_context import AppContext

log = logging.getLogger(__name__)

_STATE_FILE = "plugin_state.json"


class PluginManager:
    """
    Owns the plugin lifecycle: discovery, enable/disable, serialisation.

    The manager is created by MainWindow, which passes its AppContext.
    Plugins are loaded from <app_dir>/plugins/ and their enabled/disabled
    state is persisted to plugin_state.json next to the executable.
    """

    def __init__(self, plugins_dir: str | Path, state_dir: str | Path) -> None:
        self._loader = PluginLoader(plugins_dir)
        self._state_path = Path(state_dir) / _STATE_FILE
        self._context: Optional[AppContext] = None
        self._panel_plugins: List[PanelPlugin] = []
        self._sidebar_plugins: List[SidebarPlugin] = []
        self._saved_enabled: Dict[str, bool] = {}

    def initialise(self, context: AppContext) -> None:
        """
        Discover all plugins and restore their enabled state.

        Must be called once after AppContext is fully constructed.
        """
        self._context = context
        self._load_saved_state()
        discovered = self._loader.discover()
        for pid in discovered:
            should_enable = self._saved_enabled.get(pid, True)
            if should_enable:
                self._loader.enable(pid, context)
                rec = self._loader.get(pid)
                if rec and rec.enabled:
                    self._integrate(rec)

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a loaded plugin and integrate it into the UI."""
        ok = self._loader.enable(plugin_id, self._context)
        if ok:
            rec = self._loader.get(plugin_id)
            if rec:
                self._integrate(rec)
        self._persist_state()
        return ok

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin and save the new state."""
        ok = self._loader.disable(plugin_id, self._context)
        self._persist_state()
        return ok

    def records(self) -> List[PluginRecord]:
        """Return all discovered plugin records."""
        return list(self._loader.records.values())

    def panel_plugins(self) -> List[PanelPlugin]:
        return list(self._panel_plugins)

    def sidebar_plugins(self) -> List[SidebarPlugin]:
        return list(self._sidebar_plugins)

    def get_plugin(self, plugin_id: str) -> Optional[AnyPlugin]:
        rec = self._loader.get(plugin_id)
        return rec.plugin if rec else None

    def _integrate(self, rec: PluginRecord) -> None:
        p = rec.plugin
        if isinstance(p, PanelPlugin):
            if p not in self._panel_plugins:
                self._panel_plugins.append(p)
        if isinstance(p, SidebarPlugin):
            if p not in self._sidebar_plugins:
                self._sidebar_plugins.append(p)
        if isinstance(p, MenuPlugin):
            p.register_actions(self._context)

    def _load_saved_state(self) -> None:
        if not self._state_path.exists():
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as f:
                self._saved_enabled = json.load(f)
        except Exception as exc:
            log.warning("Could not read plugin state: %s", exc)

    def _persist_state(self) -> None:
        state = {pid: rec.enabled for pid, rec in self._loader.records.items()}
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as exc:
            log.warning("Could not save plugin state: %s", exc)
