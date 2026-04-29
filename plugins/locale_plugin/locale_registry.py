from __future__ import annotations
from typing import Callable, Dict, List, Optional

_TranslationMap = Dict[str, str]

class LocaleRegistry:
    """
    Central registry for all translatable strings.

    Plugins register their own namespace under a plugin_id key.
    Observers are notified when the active locale changes.
    """
    def __init__(self) -> None:
        self._locale: str = "en"
        self._strings: Dict[str, Dict[str, _TranslationMap]] = {}
        self._observers: List[Callable[[str], None]] = []
    @property
    def locale(self) -> str:
        return self._locale
    @property
    def available_locales(self) -> List[str]:
        locales: set[str] = {"en"}
        for ns_data in self._strings.values():
            locales.update(ns_data.keys())
        return sorted(locales)
    def register(self, plugin_id: str, locale: str, strings: _TranslationMap) -> None:
        """Register a translation map for a plugin namespace and locale."""
        ns = self._strings.setdefault(plugin_id, {})
        ns.setdefault(locale, {}).update(strings)
    def tr(self, plugin_id: str, key: str, **kwargs) -> str:
        """Return translated string; falls back to key if not found."""
        ns = self._strings.get(plugin_id, {})
        text = ns.get(self._locale, {}).get(key) or ns.get("en", {}).get(key) or key
        return text.format(**kwargs) if kwargs else text
    def set_locale(self, locale: str) -> None:
        """Change the active locale and notify all observers."""
        if locale == self._locale:
            return
        self._locale = locale
        for cb in self._observers:
            try:
                cb(locale)
            except Exception:
                pass
    def add_observer(self, cb: Callable[[str], None]) -> None:
        if cb not in self._observers:
            self._observers.append(cb)
    def remove_observer(self, cb: Callable[[str], None]) -> None:
        self._observers = [o for o in self._observers if o is not cb]