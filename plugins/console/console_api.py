from __future__ import annotations
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from PyQt5.QtCore import QObject, pyqtSignal
from .console_model import ConsoleBuffer, ConsoleLine, MsgKind, make_line
from .repl_executor import ReplExecutor
if TYPE_CHECKING:
    from .debug_tools import DebugTools

class ConsoleAPI(QObject):
    """
    Public API for the ZarCalc Python console.

    Other plugins and scripts interact with the console exclusively through
    this object, available via::

        api = context.get_service("console_api")

    Plugins can extend functionality by calling register_command() or
    register_formatter().
    """
    line_appended = pyqtSignal(object)
    cleared = pyqtSignal()
    tab_added = pyqtSignal(str, str)
    tab_removed = pyqtSignal(str)
    tab_focused = pyqtSignal(str)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._buffers: Dict[str, ConsoleBuffer] = {"__repl__": ConsoleBuffer()}
        self._active_tab: str = "__repl__"
        self._executor = ReplExecutor()
        self._custom_commands: Dict[str, Callable] = {}
        self._formatters: Dict[MsgKind, Callable[[str], str]] = {}
        self._watch_timers: list = []
        self._debug: Optional["DebugTools"] = None

    @property
    def debug(self) -> "DebugTools":
        if self._debug is None:
            from .debug_tools import DebugTools
            self._debug = DebugTools(self)
        return self._debug

    @property
    def executor(self) -> ReplExecutor:
        return self._executor

    def set_app_namespace(self, ns: Dict[str, Any]) -> None:
        """Inject application objects into the REPL namespace."""
        self._executor.update_namespace(ns)

    def register_command(self, name: str, handler: Callable[[List[str]], None]) -> None:
        """
        Register a slash-command callable as /name arg1 arg2 ...

        handler receives a list of string arguments.
        """
        self._custom_commands[name.lstrip("/")] = handler

    def unregister_command(self, name: str) -> None:
        self._custom_commands.pop(name.lstrip("/"), None)

    def register_formatter(self, kind: MsgKind, fn: Callable[[str], str]) -> None:
        """Register a text transform applied before lines of kind are displayed."""
        self._formatters[kind] = fn

    def add_script_tab(self, tab_id: str, label: str) -> None:
        """Create a named output tab for a script."""
        if tab_id not in self._buffers:
            self._buffers[tab_id] = ConsoleBuffer()
        self.tab_added.emit(tab_id, label)

    def remove_script_tab(self, tab_id: str) -> None:
        """Remove a script output tab."""
        self._buffers.pop(tab_id, None)
        self.tab_removed.emit(tab_id)

    def focus_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        self.tab_focused.emit(tab_id)

    def _buf(self, tab_id: Optional[str] = None) -> ConsoleBuffer:
        key = tab_id or self._active_tab
        if key not in self._buffers:
            self._buffers[key] = ConsoleBuffer()
        return self._buffers[key]

    def _emit(self, line: ConsoleLine, tab_id: Optional[str] = None) -> None:
        key = tab_id or self._active_tab
        self._buf(key).append(line)
        self.line_appended.emit((key, line))

    def _make(self, text: str, kind: MsgKind, source: str = "") -> ConsoleLine:
        fmt = self._formatters.get(kind)
        if fmt:
            text = fmt(text)
        return make_line(text, kind, source)

    def write(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        """Write plain stdout text to a tab."""
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.STDOUT, source), tab_id)

    def write_stderr(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        """Write stderr text to a tab."""
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.STDERR, source), tab_id)

    def log_info(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.INFO, source), tab_id)

    def log_warn(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.WARN, source), tab_id)

    def log_error(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.STDERR, source), tab_id)

    def log_success(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.SUCCESS, source), tab_id)

    def log_debug(self, text: str, tab_id: Optional[str] = None, source: str = "") -> None:
        for line in text.splitlines(keepends=False):
            self._emit(self._make(line, MsgKind.DEBUG, source), tab_id)

    def clear(self, tab_id: Optional[str] = None) -> None:
        """Clear all output in a tab."""
        key = tab_id or self._active_tab
        self._buf(key).clear()
        self.cleared.emit()

    def save_to_file(self, path: str, tab_id: Optional[str] = None, timestamps: bool = True) -> bool:
        """Save tab output to a text file. Returns True on success."""
        key = tab_id or self._active_tab
        buf = self._buf(key)
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(buf.export_text(timestamps), encoding="utf-8")
            self.log_success(f"Saved {len(buf)} lines to {path}")
            return True
        except Exception as exc:
            self.log_error(f"Save failed: {exc}")
            return False

    def get_buffer(self, tab_id: Optional[str] = None) -> ConsoleBuffer:
        """Return the ConsoleBuffer for a tab (read access)."""
        return self._buf(tab_id)

    def execute(self, source: str) -> None:
        """Execute source in the REPL. Slash-commands are dispatched first."""
        stripped = source.strip()
        if stripped.startswith("/"):
            self._dispatch_command(stripped)
            return
        self._emit(self._make(">>> " + source, MsgKind.STDIN), "__repl__")
        stdout, stderr, incomplete = self._executor.execute(source)
        if stdout:
            self.write(stdout, "__repl__")
        if stderr:
            self.write_stderr(stderr, "__repl__")
        if incomplete:
            self._emit(self._make("... (continue multi-line input)", MsgKind.SYSTEM), "__repl__")

    def _dispatch_command(self, text: str) -> None:
        parts = text.lstrip("/").split()
        if not parts:
            return
        name, args = parts[0], parts[1:]
        if name in self._custom_commands:
            try:
                self._custom_commands[name](args)
            except Exception as exc:
                self.log_error(f"Command /{name} error: {exc}")
        elif name == "clear":
            self.clear(args[0] if args else None)
        elif name == "save":
            path = args[0] if args else f"console_{int(time.time())}.txt"
            self.save_to_file(path)
        elif name == "help":
            self._print_help()
        else:
            self.log_warn(f"Unknown command: /{name}. Type /help for commands.")

    def _print_help(self) -> None:
        lines = [
            "Built-in commands:",
            "  /clear [tab_id]    Clear console output",
            "  /save [path]       Save output to file",
            "  /help              Show this message",
            "",
            "Registered plugin commands:",
        ]
        for name in sorted(self._custom_commands):
            lines.append(f"  /{name}")
        self.log_info("\n".join(lines))