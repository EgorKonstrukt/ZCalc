import json
import os
from typing import Any, Dict

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "zcalc_config.json"
)

_DEFAULTS: Dict[str, Any] = {
    "target_fps":       60,
    "anim_samples":     400,
    "static_samples":   800,
    "replot_delay_ms":  35,
    "theme":            "light",
    "show_fps":         True,
    "antialiasing":     True,
    "line_aa":          True,
    "panel_width":      440,
    "use_numpy":        True,
    "script_editor":    "",
    "script_timeout_s": 5,
}


class Config:
    """Singleton configuration backed by zcalc_config.json."""

    _instance: "Config" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = dict(_DEFAULTS)
            cls._instance._load()
        return cls._instance

    def _load(self):
        try:
            if os.path.exists(_CONFIG_PATH):
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    if k in _DEFAULTS:
                        self._data[k] = v
        except Exception:
            pass

    def save(self):
        try:
            with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass

    def get(self, key: str) -> Any:
        return self._data.get(key, _DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value

    def reset_defaults(self):
        self._data = dict(_DEFAULTS)

    @property
    def target_fps(self) -> int:        return self.get("target_fps")
    @property
    def anim_samples(self) -> int:      return self.get("anim_samples")
    @property
    def static_samples(self) -> int:    return self.get("static_samples")
    @property
    def replot_delay_ms(self) -> int:   return self.get("replot_delay_ms")
    @property
    def theme(self) -> str:             return self.get("theme")
    @property
    def show_fps(self) -> bool:         return self.get("show_fps")
    @property
    def antialiasing(self) -> bool:     return self.get("antialiasing")
    @property
    def line_aa(self) -> bool:          return self.get("line_aa")
    @property
    def panel_width(self) -> int:       return self.get("panel_width")
    @property
    def use_numpy(self) -> bool:        return self.get("use_numpy")
    @property
    def script_editor(self) -> str:     return self.get("script_editor")
    @property
    def script_timeout_s(self) -> int:  return int(self.get("script_timeout_s"))
    @property
    def anim_interval_ms(self) -> int:  return max(8, 1000 // self.target_fps)
