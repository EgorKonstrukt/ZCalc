from __future__ import annotations
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
if TYPE_CHECKING:
    from PyQt5.QtWidgets import QMainWindow, QMenu, QDockWidget
    from pyqt5_chart_widget import ChartWidget
    from core.items import FunctionPanel
    from history import History
    from config import Config

class AppContext:
    """
    Shared service locator injected into every plugin.

    Plugins must never import MainWindow directly; they interact with the
    application exclusively through this interface.
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
        self._dock_registry: Dict[str, "QDockWidget"] = {}
        self._event_listeners: Dict[str, List[Callable]] = {}

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
        self._menu_registry[menu_name] = menu
    def get_menu(self, menu_name: str) -> Optional["QMenu"]:
        return self._menu_registry.get(menu_name)

    def register_service(self, key: str, service: Any) -> None:
        self._services[key] = service
    def get_service(self, key: str) -> Optional[Any]:
        return self._services.get(key)

    def register_dock(self, dock_id: str, dock: "QDockWidget") -> None:
        """Register a dock widget so other plugins can find it by id."""
        self._dock_registry[dock_id] = dock
    def get_dock(self, dock_id: str) -> Optional["QDockWidget"]:
        return self._dock_registry.get(dock_id)
    def all_docks(self) -> Dict[str, "QDockWidget"]:
        return dict(self._dock_registry)

    def emit_event(self, event: str, *args, **kwargs) -> None:
        """Broadcast an application event to all registered listeners."""
        for cb in self._event_listeners.get(event, []):
            try:
                cb(*args, **kwargs)
            except Exception:
                pass
    def on_event(self, event: str, callback: Callable) -> None:
        self._event_listeners.setdefault(event, []).append(callback)
    def off_event(self, event: str, callback: Callable) -> None:
        listeners = self._event_listeners.get(event, [])
        self._event_listeners[event] = [c for c in listeners if c is not callback]

    def request_replot(self) -> None:
        self._panel.update_requested.emit()
    def show_status(self, message: str, timeout_ms: int = 3000) -> None:
        sb = self._main_window.statusBar()
        if sb:
            sb.showMessage(message, timeout_ms)