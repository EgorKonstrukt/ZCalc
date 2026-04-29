from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from core.plugins.plugin_base import PanelPlugin, PluginMeta

if TYPE_CHECKING:
    from core import AppContext
    from PyQt5.QtWidgets import QWidget
    from .script_console import ScriptConsole

PLUGIN_META = PluginMeta(
    id="zarcalc.script",
    name="Script",
    version="1.2.0",
    author="ZarCalc",
    description=(
        "Python script items in the function list. "
        "Supports animation, chart access, parameter sliders, "
        "console output, and profiling. "
        "Protected against infinite loops via timeout."
    ),
    dependencies=[],
)


class ScriptPlugin(PanelPlugin):
    """
    PanelPlugin — adds 'Script' to the + Add menu.

    Each script row appears inline in the function list and can be
    nested inside Folder items.  All rows share one ScriptConsole
    docked to the main window.
    """

    meta = PLUGIN_META

    def __init__(self):
        self._console: Optional["ScriptConsole"] = None
        self._context: Optional["AppContext"] = None

    @property
    def menu_label(self) -> str:
        return "Script"

    def on_load(self, context: "AppContext") -> None:
        from .script_console import ScriptConsole
        from PyQt5.QtCore import Qt
        self._context = context
        mw = context.main_window
        self._console = ScriptConsole(mw)
        mw.addDockWidget(Qt.BottomDockWidgetArea, self._console)
        self._console.hide()
        context.register_service("script_console", self._console)
        self._add_console_button(context)

    def _add_console_button(self, context: "AppContext"):
        """Add a Console toggle button to the FunctionPanel toolbar."""
        from PyQt5.QtWidgets import QPushButton
        panel = context.panel
        toolbar = None
        for child in panel.children():
            if hasattr(child, "layout") and callable(child.layout):
                lay = child.layout()
                if lay and lay.count() > 2:
                    toolbar = child
                    break
        if toolbar is None:
            return
        tl = toolbar.layout()
        if tl is None:
            return
        console_btn = QPushButton("Console")
        console_btn.setCheckable(True)
        console_btn.setStyleSheet(
            "QPushButton{background:#2c3e50;color:white;border:none;"
            "border-radius:4px;font-size:11px;padding:3px 8px;}"
            "QPushButton:checked{background:#27ae60;}"
            "QPushButton:hover{background:#34495e;}"
        )
        console_btn.setFixedHeight(26)
        console_btn.toggled.connect(self._toggle_console)
        self._console_btn = console_btn
        tl.addWidget(console_btn)

    def _toggle_console(self, checked: bool):
        if self._console:
            if checked:
                self._console.show()
            else:
                self._console.hide()

    def create_item(self, context: "AppContext") -> "QWidget":
        from .script_row import ScriptRow
        row = ScriptRow(context)
        if self._console:
            row.set_console(self._console)
        return row

    def to_item_state(self, widget: "QWidget") -> dict:
        return widget.to_state() if hasattr(widget, "to_state") else {}

    def restore_item(self, context: "AppContext", state: dict) -> "QWidget":
        from .script_row import ScriptRow
        row = ScriptRow(context)
        if self._console:
            row.set_console(self._console)
        row.apply_state(state)
        return row

    def on_unload(self, context: "AppContext") -> None:
        if self._console:
            self._console.close()


def get_plugin() -> ScriptPlugin:
    return ScriptPlugin()
