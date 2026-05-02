from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional
from .console_theme import MAX_SCROLLBACK

class MsgKind(Enum):
    STDOUT = auto()
    STDERR = auto()
    STDIN = auto()
    INFO = auto()
    WARN = auto()
    SUCCESS = auto()
    DEBUG = auto()
    SYSTEM = auto()

@dataclass
class Span:
    text: str
    color: Optional[str] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False

@dataclass
class ConsoleLine:
    spans: List[Span]
    kind: MsgKind
    source: str = ""
    timestamp: float = field(default_factory=time.time)
    raw: str = ""

_ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

_COLOR_MAP = {
    30: "#1e1e2e", 31: "#f38ba8", 32: "#a6e3a1", 33: "#f9e2af",
    34: "#89b4fa", 35: "#cba6f7", 36: "#89dceb", 37: "#cdd6f4",
    90: "#6c7086", 91: "#f38ba8", 92: "#a6e3a1", 93: "#fab387",
    94: "#89b4fa", 95: "#f5c2e7", 96: "#94e2d5", 97: "#ffffff",
    40: "#1e1e2e", 41: "#f38ba8", 42: "#a6e3a1", 43: "#f9e2af",
    44: "#89b4fa", 45: "#cba6f7", 46: "#89dceb", 47: "#cdd6f4",
}

_KIND_COLORS = {
    MsgKind.STDOUT:  "#cdd6f4",
    MsgKind.STDERR:  "#f38ba8",
    MsgKind.STDIN:   "#89dceb",
    MsgKind.INFO:    "#89b4fa",
    MsgKind.WARN:    "#fab387",
    MsgKind.SUCCESS: "#a6e3a1",
    MsgKind.DEBUG:   "#b4befe",
    MsgKind.SYSTEM:  "#6c7086",
}

def parse_ansi(text: str, base_color: Optional[str] = None) -> List[Span]:
    spans: List[Span] = []
    pos = 0
    cur_color = base_color
    bold = False
    italic = False
    underline = bool = False
    for m in _ANSI_RE.finditer(text):
        if m.start() > pos:
            chunk = text[pos:m.start()]
            if chunk:
                spans.append(Span(chunk, cur_color, bold, italic, underline))
        codes = [int(c) for c in m.group(1).split(";") if c] if m.group(1) else [0]
        i = 0
        while i < len(codes):
            c = codes[i]
            if c == 0:
                cur_color = base_color
                bold = italic = underline = False
            elif c == 1:
                bold = True
            elif c == 3:
                italic = True
            elif c == 4:
                underline = True
            elif c == 22:
                bold = False
            elif c == 38 and i + 2 < len(codes) and codes[i + 1] == 5:
                i += 2
                idx = codes[i]
                cur_color = f"#{idx:02x}{idx:02x}{idx:02x}"
            elif c == 38 and i + 4 < len(codes) and codes[i + 1] == 2:
                r, g, b = codes[i + 2], codes[i + 3], codes[i + 4]
                cur_color = f"#{r:02x}{g:02x}{b:02x}"
                i += 4
            elif c in _COLOR_MAP:
                cur_color = _COLOR_MAP[c]
            i += 1
        pos = m.end()
    tail = text[pos:]
    if tail:
        spans.append(Span(tail, cur_color, bold, italic, underline))
    return spans if spans else [Span(text, base_color)]

def make_line(text: str, kind: MsgKind, source: str = "") -> ConsoleLine:
    base = _KIND_COLORS.get(kind)
    spans = parse_ansi(text, base)
    return ConsoleLine(spans=spans, kind=kind, source=source, raw=text)

class ConsoleBuffer:
    """Thread-safe scrollback buffer for console output lines."""
    def __init__(self, max_lines: int = MAX_SCROLLBACK) -> None:
        self._lines: List[ConsoleLine] = []
        self._max = max_lines
    def append(self, line: ConsoleLine) -> None:
        self._lines.append(line)
        if len(self._lines) > self._max:
            del self._lines[:len(self._lines) - self._max]
    def lines(self) -> List[ConsoleLine]:
        return list(self._lines)
    def clear(self) -> None:
        self._lines.clear()
    def __len__(self) -> int:
        return len(self._lines)
    def export_text(self, include_timestamps: bool = False) -> str:
        parts = []
        for ln in self._lines:
            prefix = f"[{ln.source}] " if ln.source else ""
            ts = f"{time.strftime('%H:%M:%S', time.localtime(ln.timestamp))} " if include_timestamps else ""
            parts.append(ts + prefix + ln.raw)
        return "\n".join(parts)