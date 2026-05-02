from __future__ import annotations
import keyword
import builtins
from typing import Dict, Any, List, Optional, Tuple

_BUILTIN_NAMES = sorted(dir(builtins))
_KEYWORD_NAMES = sorted(keyword.kwlist)

def _attrs(obj: Any) -> List[str]:
    try:
        return [a for a in dir(obj) if not a.startswith("__")]
    except Exception:
        return []

def _complete_name(prefix: str, ns: Dict[str, Any]) -> List[str]:
    candidates = set(_BUILTIN_NAMES + _KEYWORD_NAMES + list(ns.keys()))
    return sorted(c for c in candidates if c.startswith(prefix))

def _complete_attr(expr: str, attr_prefix: str, ns: Dict[str, Any]) -> List[str]:
    try:
        obj = eval(expr, ns)
        return sorted(a for a in _attrs(obj) if a.startswith(attr_prefix))
    except Exception:
        return []

def get_completions(text: str, cursor_pos: int, ns: Dict[str, Any]) -> Tuple[List[str], str]:
    """
    Return (completions, prefix) for the token ending at cursor_pos in text.
    """
    fragment = text[:cursor_pos]
    dot_idx = fragment.rfind(".")
    space_idx = max(fragment.rfind(" "), fragment.rfind("\t"),
                    fragment.rfind("("), fragment.rfind(","),
                    fragment.rfind("["), fragment.rfind("="))
    if dot_idx > space_idx and dot_idx >= 0:
        expr_part = fragment[space_idx + 1:dot_idx]
        attr_prefix = fragment[dot_idx + 1:]
        completions = _complete_attr(expr_part, attr_prefix, ns)
        return completions, attr_prefix
    token_start = space_idx + 1
    prefix = fragment[token_start:]
    return _complete_name(prefix, ns), prefix

class InputHistory:
    """Persistent per-session command history with navigation."""
    def __init__(self, max_size: int = 500) -> None:
        self._entries: List[str] = []
        self._pos: int = -1
        self._draft: str = ""
        self._max = max_size
    def push(self, cmd: str) -> None:
        cmd = cmd.strip()
        if not cmd:
            return
        if self._entries and self._entries[-1] == cmd:
            self._pos = -1
            return
        self._entries.append(cmd)
        if len(self._entries) > self._max:
            self._entries.pop(0)
        self._pos = -1
    def up(self, current: str) -> Optional[str]:
        if not self._entries:
            return None
        if self._pos == -1:
            self._draft = current
            self._pos = len(self._entries) - 1
        elif self._pos > 0:
            self._pos -= 1
        return self._entries[self._pos]
    def down(self) -> Optional[str]:
        if self._pos == -1:
            return None
        if self._pos < len(self._entries) - 1:
            self._pos += 1
            return self._entries[self._pos]
        self._pos = -1
        return self._draft
    def all_entries(self) -> List[str]:
        return list(self._entries)