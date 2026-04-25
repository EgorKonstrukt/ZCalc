from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget
    from core.app_context import AppContext


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
    """
    Base class for plugins that contribute an item type to the expression list.

    Subclasses appear in the '+' menu of the function panel and can create
    widgets that are inserted into the scrollable item list.
    """

    meta: PluginMeta

    @abstractmethod
    def create_item(self, context: "AppContext") -> "QWidget":
        """Return a new item widget to insert into the expression list."""

    @property
    def menu_label(self) -> str:
        """Label shown in the toolbar '+' menu."""
        return self.meta.name

    def on_load(self, context: "AppContext") -> None:
        """Called once when the plugin is first loaded."""

    def on_unload(self, context: "AppContext") -> None:
        """Called when the plugin is disabled or the app is closing."""

    def to_item_state(self, widget: "QWidget") -> dict:
        """Serialise a single item widget to a plain dict."""
        if hasattr(widget, "to_state"):
            return widget.to_state()
        return {}

    def restore_item(self, context: "AppContext", state: dict) -> "QWidget":
        """Reconstruct an item widget from a saved state dict."""
        w = self.create_item(context)
        if hasattr(w, "apply_state"):
            w.apply_state(state)
        return w


class SidebarPlugin(ABC):
    """
    Base class for plugins that add a panel to the bottom sidebar area.
    """

    meta: PluginMeta

    @abstractmethod
    def create_panel(self, context: "AppContext") -> "QWidget":
        """Return the sidebar panel widget."""

    def on_load(self, context: "AppContext") -> None:
        """Called once when the plugin is first loaded."""

    def on_unload(self, context: "AppContext") -> None:
        """Called when the plugin is disabled or the app is closing."""


class MenuPlugin(ABC):
    """
    Base class for plugins that only contribute menu actions, no widgets.
    """

    meta: PluginMeta

    @abstractmethod
    def register_actions(self, context: "AppContext") -> None:
        """Register QActions via context.add_menu_action()."""

    def on_load(self, context: "AppContext") -> None:
        """Called once when the plugin is first loaded."""

    def on_unload(self, context: "AppContext") -> None:
        """Called when the plugin is disabled or the app is closing."""


AnyPlugin = Union[PanelPlugin, SidebarPlugin, MenuPlugin]
