from __future__ import annotations

from core.plugin_base import PanelPlugin, PluginMeta

PLUGIN_META = PluginMeta(
    id="zcalc.folders",
    name="Folders",
    version="1.0.0",
    author="ZCalc",
    description="Group expression items into collapsible named folders (Desmos-style).",
)


class FoldersPlugin(PanelPlugin):
    """PanelPlugin that inserts collapsible folder headers into the item list."""

    meta = PLUGIN_META

    @property
    def menu_label(self) -> str:
        return "Folder"

    def create_item(self, context):
        from plugins.folders_plugin.folder_item import FolderItem
        return FolderItem(context)

    def on_load(self, context) -> None:
        context.show_status("Folders plugin loaded.", 2000)

    def on_unload(self, context) -> None:
        pass


def get_plugin() -> FoldersPlugin:
    return FoldersPlugin()
