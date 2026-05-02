from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class ConsoleColors:
    bg: str = "#000000"
    fg: str = "#cdd6f4"
    stdout: str = "#cdd6f4"
    stderr: str = "#f38ba8"
    stdin: str = "#89dceb"
    warn: str = "#fab387"
    info: str = "#89b4fa"
    success: str = "#a6e3a1"
    debug: str = "#b4befe"
    timestamp: str = "#6c7086"
    prompt: str = "#a6e3a1"
    cursor: str = "#f5c2e7"
    selection_bg: str = "#313244"
    tab_active: str = "#313244"
    tab_inactive: str = "#181825"
    tab_text: str = "#cdd6f4"
    scrollbar: str = "#45475a"
    border: str = "#45475a"
    autocomplete_bg: str = "#313244"
    autocomplete_selected: str = "#89b4fa"
    autocomplete_text: str = "#cdd6f4"

ANSI_COLORS: Dict[int, str] = {
    30: "#1e1e2e", 31: "#f38ba8", 32: "#a6e3a1", 33: "#f9e2af",
    34: "#89b4fa", 35: "#cba6f7", 36: "#89dceb", 37: "#cdd6f4",
    90: "#6c7086", 91: "#f38ba8", 92: "#a6e3a1", 93: "#fab387",
    94: "#89b4fa", 95: "#f5c2e7", 96: "#94e2d5", 97: "#ffffff",
}

DEFAULT_COLORS = ConsoleColors()
FONT_FAMILY = "Consolas, 'Courier New', monospace"
FONT_SIZE_PT = 10
MAX_SCROLLBACK = 5000
INPUT_HISTORY_SIZE = 500
AUTOCOMPLETE_MAX_ITEMS = 20
AUTOCOMPLETE_MIN_CHARS = 1
DEBOUNCE_AUTOCOMPLETE_MS = 120