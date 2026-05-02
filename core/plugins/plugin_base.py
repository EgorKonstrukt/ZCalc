from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Union
if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget, QDockWidget
    from core.plugins.app_context import AppContext

@dataclass
class PluginMeta:
    """Metadata descriptor embedded in every plugin."""
    id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)

class PanelPlugin(ABC):
    """Base class for plugins that contribute an item type to the expression list."""
    meta: PluginMeta
    @abstractmethod
    def create_item(self, context: "AppContext") -> "QWidget": ...
    @property
    def menu_label(self) -> str:
        return self.meta.name
    def on_load(self, context: "AppContext") -> None: ...
    def on_unload(self, context: "AppContext") -> None: ...
    def to_item_state(self, widget: "QWidget") -> dict:
        return widget.to_state() if hasattr(widget, "to_state") else {}
    def restore_item(self, context: "AppContext", state: dict) -> "QWidget":
        w = self.create_item(context)
        if hasattr(w, "apply_state"):
            w.apply_state(state)
        return w

class SidebarPlugin(ABC):
    """Base class for plugins that add a panel to the bottom sidebar area."""
    meta: PluginMeta
    @abstractmethod
    def create_panel(self, context: "AppContext") -> "QWidget": ...
    def on_load(self, context: "AppContext") -> None: ...
    def on_unload(self, context: "AppContext") -> None: ...

class MenuPlugin(ABC):
    """Base class for plugins that only contribute menu actions."""
    meta: PluginMeta
    @abstractmethod
    def register_actions(self, context: "AppContext") -> None: ...
    def on_load(self, context: "AppContext") -> None: ...
    def on_unload(self, context: "AppContext") -> None: ...

class DockPlugin(ABC):
    """Base class for plugins that contribute a QDockWidget to the main window."""
    meta: PluginMeta
    DOCK_ID: str = ""
    DEFAULT_AREA: int = 8
    DEFAULT_FLOATING: bool = False
    DEFAULT_VISIBLE: bool = True
    @abstractmethod
    def create_dock(self, context: "AppContext") -> "QDockWidget":
        """Return a configured QDockWidget. Called once on load."""
    def on_load(self, context: "AppContext") -> None: ...
    def on_unload(self, context: "AppContext") -> None: ...
    def dock_id(self) -> str:
        return self.DOCK_ID or self.meta.id
    def default_dock_state(self) -> dict:
        return {
            "area": self.DEFAULT_AREA,
            "floating": self.DEFAULT_FLOATING,
            "visible": self.DEFAULT_VISIBLE,
            "geometry": None,
        }

AnyPlugin = Union[PanelPlugin, SidebarPlugin, MenuPlugin, DockPlugin]