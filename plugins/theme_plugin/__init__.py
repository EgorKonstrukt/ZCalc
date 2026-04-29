from __future__ import annotations
from core.plugins.plugin_base import SidebarPlugin, PluginMeta
from .theme_manager import ThemeManager
from .theme_panel import ThemePanel
from .theme_settings_page import ThemeSettingsPage

PLUGIN_META = PluginMeta(
    id="zarcalc.theme",
    name="Theme Manager",
    version="1.0.0",
    author="ZarCalc",
    description="Provides Light, Dark (Fusion), and High Contrast (JetBrains) themes.",
)

class ThemePlugin(SidebarPlugin):
    """Plugin that registers a theme selector in the sidebar and settings."""
    meta = PLUGIN_META
    def __init__(self) -> None:
        self._manager = ThemeManager()
        self._settings_page = ThemeSettingsPage(self._manager)
    def on_load(self, context) -> None:
        saved = context.config.get("theme_id") or "light"
        self._manager.apply(saved)
        context.register_service("theme_manager", self._manager)
        registry = context.get_service("settings_registry")
        if registry is not None:
            registry.register_page(self._settings_page)
    def create_panel(self, context) -> "ThemePanel":
        return ThemePanel(self._manager, context)
    def on_unload(self, context) -> None:
        registry = context.get_service("settings_registry")
        if registry is not None:
            registry.unregister_page(self._settings_page)
        self._manager.apply("light")

def get_plugin() -> ThemePlugin:
    return ThemePlugin()