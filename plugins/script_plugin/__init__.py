from __future__ import annotations
from typing import TYPE_CHECKING

from core.plugin_base import PanelPlugin, PluginMeta

if TYPE_CHECKING:
    from core.app_context import AppContext
    from PyQt5.QtWidgets import QWidget

PLUGIN_META = PluginMeta(
    id="zcalc.script",
    name="Script",
    version="1.1.0",
    author="ZCalc",
    description="Python script item with chart/animation integration and profiler.",
    dependencies=[],
)


class ScriptPlugin(PanelPlugin):
    """
    PanelPlugin that contributes a Script item type to the + Add menu.
    Script rows appear in the main function list alongside functions,
    comments, and folders — they can be nested inside folders.
    """

    meta = PLUGIN_META

    @property
    def menu_label(self) -> str:
        return "Script"

    def create_item(self, context: "AppContext") -> "QWidget":
        from .script_row import ScriptRow
        return ScriptRow(context)

    def to_item_state(self, widget: "QWidget") -> dict:
        return widget.to_state() if hasattr(widget, "to_state") else {}

    def restore_item(self, context: "AppContext", state: dict) -> "QWidget":
        from .script_row import ScriptRow
        row = ScriptRow(context)
        row.apply_state(state)
        return row

    def on_load(self, context: "AppContext") -> None:
        pass

    def on_unload(self, context: "AppContext") -> None:
        pass


def get_plugin() -> ScriptPlugin:
    return ScriptPlugin()