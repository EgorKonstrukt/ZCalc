from __future__ import annotations
from typing import List
from core.plugins.settings_page import SettingsPage

class SettingsRegistry:
    """
    Shared service that collects SettingsPage instances from plugins.

    Registered in AppContext under the key ``"settings_registry"``.
    SettingsDialog reads all registered pages and creates tabs for them.
    """
    def __init__(self) -> None:
        self._pages: List[SettingsPage] = []
    def register_page(self, page: SettingsPage) -> None:
        """Register a plugin settings page. Call this from on_load."""
        if page not in self._pages:
            self._pages.append(page)
    def unregister_page(self, page: SettingsPage) -> None:
        """Remove a previously registered page. Call from on_unload."""
        self._pages = [p for p in self._pages if p is not page]
    @property
    def pages(self) -> List[SettingsPage]:
        return list(self._pages)