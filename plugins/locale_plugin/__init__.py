from __future__ import annotations
from core.plugins.plugin_base import SidebarPlugin, PluginMeta
from .locale_registry import LocaleRegistry
from .locale_panel import LocalePanel
from .locale_settings_page import LocaleSettingsPage
from .builtin_strings import LOCALE_PLUGIN_STRINGS

PLUGIN_META = PluginMeta(
    id="locale_plugin",
    name="Locale Manager",
    version="1.0.0",
    author="ZarCalc",
    description="Provides runtime locale switching and a translation registry for other plugins.",
)

class LocalePlugin(SidebarPlugin):
    """
    Plugin that bootstraps the shared LocaleRegistry service.

    Other plugins call::

        reg = context.get_service("locale_registry")
        reg.register("my_plugin", "ru", {"key": "value"})
        reg.tr("my_plugin", "key")
    """
    meta = PLUGIN_META
    def __init__(self) -> None:
        self._registry = LocaleRegistry()
        self._settings_page = LocaleSettingsPage(self._registry)
    def on_load(self, context) -> None:
        ns = "locale_plugin"
        for lang, strings in LOCALE_PLUGIN_STRINGS.items():
            self._registry.register(ns, lang, strings)
        saved = context.config.get("locale_id") or "en"
        self._registry.set_locale(saved)
        context.register_service("locale_registry", self._registry)
        registry = context.get_service("settings_registry")
        if registry is not None:
            registry.register_page(self._settings_page)
    def create_panel(self, context) -> "LocalePanel":
        return LocalePanel(self._registry, context)
    def on_unload(self, context) -> None:
        registry = context.get_service("settings_registry")
        if registry is not None:
            registry.unregister_page(self._settings_page)

def get_plugin() -> LocalePlugin:
    return LocalePlugin()