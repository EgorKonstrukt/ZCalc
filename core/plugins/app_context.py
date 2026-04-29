from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from PyQt5.QtWidgets import QMainWindow, QMenu
    from pyqt5_chart_widget import ChartWidget
    from core.items import FunctionPanel
    from history import History
    from config import Config


class AppContext:
    """
    Shared service locator injected into every plugin.

    Plugins must never import MainWindow directly; they interact with the
    application exclusively through this interface.  This keeps plugins
    decoupled from the host and allows the host to evolve independently.
    """

    def __init__(
        self,
        main_window: "QMainWindow",
        chart: "ChartWidget",
        panel: "FunctionPanel",
        history: "History",
        config: "Config",
    ) -> None:
        self._main_window = main_window
        self._chart = chart
        self._panel = panel
        self._history = history
        self._config = config
        self._menu_registry: Dict[str, "QMenu"] = {}
        self._services: Dict[str, Any] = {}

    @property
    def main_window(self) -> "QMainWindow":
        return self._main_window

    @property
    def chart(self) -> "ChartWidget":
        return self._chart

    @property
    def panel(self) -> "FunctionPanel":
        return self._panel

    @property
    def history(self) -> "History":
        return self._history

    @property
    def config(self) -> "Config":
        return self._config

    def register_menu(self, menu_name: str, menu: "QMenu") -> None:
        """Register a top-level menu by name so plugins can append to it."""
        self._menu_registry[menu_name] = menu

    def get_menu(self, menu_name: str) -> Optional["QMenu"]:
        """Return a registered QMenu by name, or None."""
        return self._menu_registry.get(menu_name)

    def register_service(self, key: str, service: Any) -> None:
        """Register an arbitrary shared service under a string key."""
        self._services[key] = service

    def get_service(self, key: str) -> Optional[Any]:
        """Return a shared service, or None if not registered."""
        return self._services.get(key)

    def request_replot(self) -> None:
        """Ask the main window to schedule a replot."""
        self._panel.update_requested.emit()

    def show_status(self, message: str, timeout_ms: int = 3000) -> None:
        """Show a temporary message in the main window status bar."""
        sb = self._main_window.statusBar()
        if sb:
            sb.showMessage(message, timeout_ms)
