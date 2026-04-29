from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from PyQt5.QtWidgets import QWidget
    from core.plugins.app_context import AppContext

class SettingsPage(ABC):
    """
    Base class for a plugin-provided settings tab.

    Subclasses must define ``tab_label`` as a class-level string and implement
    the three abstract methods.  Register instances via::

        registry = context.get_service("settings_registry")
        registry.register_page(MySettingsPage())

    Lifecycle:
        1. ``create_widget`` -- called once when the dialog opens.
        2. ``load``          -- called right after to populate controls.
        3. ``apply``         -- called when the user clicks Apply/OK.
        4. ``reset``         -- called when the user clicks Reset Defaults.
    """
    tab_label: str = "Plugin"
    @abstractmethod
    def create_widget(self, context: "AppContext") -> "QWidget":
        """Return the widget to embed in the tab."""
    @abstractmethod
    def load(self) -> None:
        """Populate UI controls from current config/state."""
    @abstractmethod
    def apply(self) -> None:
        """Persist UI control values to config/state."""
    def reset(self) -> None:
        """Restore defaults. No-op by default."""