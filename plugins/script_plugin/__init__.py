from __future__ import annotations
from typing import TYPE_CHECKING

from core.plugin_base import SidebarPlugin, PluginMeta

if TYPE_CHECKING:
    from core.app_context import AppContext
    from PyQt5.QtWidgets import QWidget

PLUGIN_META = PluginMeta(
    id="zcalc.script",
    name="Script Engine",
    version="1.0.0",
    author="ZCalc",
    description="Python scripting panel with animation and chart integration.",
    dependencies=[],
)


class ScriptPlugin(SidebarPlugin):
    """Sidebar plugin providing the Python script execution panel."""

    meta = PLUGIN_META

    def __init__(self):
        self._panel = None

    def create_panel(self, context: "AppContext") -> "QWidget":
        from .script_panel import ScriptPanel
        self._panel = ScriptPanel(context)
        context.register_service("script_panel", self._panel)
        return self._panel

    def on_load(self, context: "AppContext") -> None:
        pass

    def on_unload(self, context: "AppContext") -> None:
        if self._panel is not None:
            for row in list(self._panel._script_rows):
                row._on_stop()


def get_plugin() -> ScriptPlugin:
    return ScriptPlugin()
