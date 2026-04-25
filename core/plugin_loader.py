from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
import zipimport
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type

from core.plugin_base import AnyPlugin, PluginMeta

log = logging.getLogger(__name__)

_ENTRY_SYMBOL = "get_plugin"
_META_SYMBOL = "PLUGIN_META"


class PluginLoadError(Exception):
    """Raised when a plugin cannot be loaded."""


class PluginRecord:
    """Runtime record for a discovered plugin."""

    def __init__(
        self,
        meta: PluginMeta,
        plugin: AnyPlugin,
        path: Path,
        enabled: bool = True,
    ) -> None:
        self.meta = meta
        self.plugin = plugin
        self.path = path
        self.enabled = enabled
        self.error: Optional[str] = None


class PluginLoader:
    """
    Discovers, loads, and unloads plugins from a plugins directory.

    Plugin distribution format (.dll on Windows, .so on Linux/macOS, but
    distributed as .dll by convention in ZCalc):

        A .dll file is actually a zip archive containing Python source.
        The archive must have a top-level __init__.py that exports:

            PLUGIN_META: PluginMeta  - static metadata
            get_plugin() -> AnyPlugin  - factory that returns the plugin instance

        This matches the structure used by zipimport, so Python can load
        the plugin without extracting it.  On platforms where .dll implies
        a native shared library, users simply rename a .zip/.pyz to .dll.

    Fallback:
        Plain directories inside the plugins folder are also supported for
        development convenience (same __init__.py contract).
    """

    def __init__(self, plugins_dir: str | Path) -> None:
        self._dir = Path(plugins_dir)
        self._records: Dict[str, PluginRecord] = {}

    @property
    def records(self) -> Dict[str, PluginRecord]:
        return self._records

    def discover(self) -> List[str]:
        """Scan the plugins directory and return plugin IDs found."""
        found: List[str] = []
        if not self._dir.exists():
            return found
        for entry in sorted(self._dir.iterdir()):
            if entry.suffix == ".dll" and entry.is_file():
                pid = self._load_dll(entry)
            elif entry.is_dir() and (entry / "__init__.py").exists():
                pid = self._load_dir(entry)
            else:
                continue
            if pid:
                found.append(pid)
        return found

    def enable(self, plugin_id: str, context) -> bool:
        """Enable a loaded plugin by calling its on_load hook."""
        rec = self._records.get(plugin_id)
        if rec is None or rec.enabled:
            return False
        try:
            rec.plugin.on_load(context)
            rec.enabled = True
            return True
        except Exception as exc:
            rec.error = str(exc)
            log.exception("on_load failed for %s", plugin_id)
            return False

    def disable(self, plugin_id: str, context) -> bool:
        """Disable a plugin by calling its on_unload hook."""
        rec = self._records.get(plugin_id)
        if rec is None or not rec.enabled:
            return False
        try:
            rec.plugin.on_unload(context)
            rec.enabled = False
            return True
        except Exception as exc:
            rec.error = str(exc)
            log.exception("on_unload failed for %s", plugin_id)
            return False

    def get(self, plugin_id: str) -> Optional[PluginRecord]:
        return self._records.get(plugin_id)

    def _load_dll(self, path: Path) -> Optional[str]:
        """Load a zip-packaged .dll plugin via zipimport."""
        try:
            importer = zipimport.zipimporter(str(path))
            stem = path.stem
            mod = importer.load_module(stem)
            return self._register(mod, path)
        except Exception as exc:
            log.warning("Failed to load dll plugin %s: %s", path.name, exc)
            return None

    def _load_dir(self, path: Path) -> Optional[str]:
        """Load a directory-based plugin (development mode)."""
        try:
            parent = str(path.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
            mod = importlib.import_module(path.name)
            return self._register(mod, path)
        except Exception as exc:
            log.warning("Failed to load dir plugin %s: %s", path.name, exc)
            return None

    def _register(self, mod, path: Path) -> Optional[str]:
        meta: Optional[PluginMeta] = getattr(mod, _META_SYMBOL, None)
        factory = getattr(mod, _ENTRY_SYMBOL, None)
        if meta is None or factory is None:
            log.warning("Plugin at %s missing PLUGIN_META or get_plugin()", path)
            return None
        if meta.id in self._records:
            return meta.id
        plugin = factory()
        rec = PluginRecord(meta=meta, plugin=plugin, path=path, enabled=False)
        self._records[meta.id] = rec
        return meta.id
