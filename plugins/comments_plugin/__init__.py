from __future__ import annotations

from core.plugins.plugin_base import PanelPlugin, PluginMeta

PLUGIN_META = PluginMeta(
    id="zarcalc.comments",
    name="Comments",
    version="1.0.0",
    author="ZarCalc",
    description="Add text comment items to the expression list.",
)


class CommentsPlugin(PanelPlugin):
    """PanelPlugin that inserts styled text comment widgets into the item list."""

    meta = PLUGIN_META

    @property
    def menu_label(self) -> str:
        return "Comment"

    def create_item(self, context):
        from plugins.comments_plugin.comment_item import CommentItem
        return CommentItem()

    def on_load(self, context) -> None:
        context.show_status("Comments plugin loaded.", 2000)

    def on_unload(self, context) -> None:
        pass


def get_plugin() -> CommentsPlugin:
    return CommentsPlugin()
